"""Offline unit tests for the current LCATS mass_quantities parser.

Run from the LCATS repository root:
    python -m unittest discover -s tests -p '*_test.py' -v

Place this file in tests/ or another directory included in discovery.
The tests import the real LCATS parser, but never access the network.
"""

import dataclasses
import json
import pathlib
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from lcats.gatherers.mass_quantities import parser


MODULE = "lcats.gatherers.mass_quantities.parser"


def metadata(**changes):
    values = {
        "titles": ("The Example Story",),
        "authors": ("Author, Alice",),
        "aliases": ("A. Writer",),
        "subjects": ("PS", "Science fiction"),
        "languages": ("en",),
    }
    values.update(changes)
    return SimpleNamespace(**values)


def long_body():
    return "\n\n".join("This is narrative paragraph number %s." % n for n in range(12))


def source_with(meta=None, text=None):
    if meta is None:
        meta = metadata()
    if text is None:
        text = "THE EXAMPLE STORY\n\nBy Alice Author\n\n" + long_body()
    prepared = Mock()
    prepared.cleaned.text = text
    prepared.provenance.return_value = {
        "source_uri": "https://www.gutenberg.org/ebooks/42",
        "representation": "text/plain",
    }
    source = Mock()
    source.metadata.return_value = meta
    source.read.return_value = prepared
    return source


class MetadataPredicateTests(unittest.TestCase):
    def test_author_ok(self):
        self.assertTrue(parser.author_ok(["Author, Alice"]))
        self.assertFalse(parser.author_ok([]))

    def test_fiction_and_short_story(self):
        self.assertTrue(parser.fiction(["Science fiction"]))
        self.assertFalse(parser.fiction(["Poetry"]))
        self.assertTrue(parser.short_story(["Short stories, American"]))
        self.assertFalse(parser.short_story(["Novels"]))

    def test_loc_fiction(self):
        self.assertTrue(parser.loc_fiction(["PS"]))
        self.assertTrue(parser.loc_fiction(["PR"]))
        self.assertFalse(parser.loc_fiction(["PN"]))

    def test_subject_ok_requires_loc_and_fiction(self):
        self.assertTrue(parser.subject_ok(["PS", "Science fiction"]))
        self.assertTrue(parser.subject_ok(["PR", "Short stories"]))
        self.assertFalse(parser.subject_ok(["PS", "Biographies"]))
        self.assertFalse(parser.subject_ok(["PN", "Science fiction"]))

    def test_bad_subjects(self):
        self.assertTrue(parser.bad_subjects(["Epistolary fiction"]))
        self.assertTrue(parser.bad_subjects(["Zines"]))
        self.assertFalse(parser.bad_subjects(["Science fiction"]))

    def test_only_english(self):
        self.assertTrue(parser.only_english(["en"]))
        self.assertFalse(parser.only_english(["en", "fr"]))
        self.assertFalse(parser.only_english(["fr"]))
        self.assertFalse(parser.only_english([]))

    def test_only_english_custom_target(self):
        self.assertTrue(parser.only_english(["fr"], target="fr"))

    def test_title_ok(self):
        self.assertTrue(parser.title_ok(["A Good Story"]))
        self.assertFalse(parser.title_ok(["Index of the Project Gutenberg"]))
        self.assertFalse(parser.title_ok(["The Story, and Other Tales"]))
        self.assertFalse(parser.title_ok(["The Story; and Other Tales"]))
        self.assertFalse(parser.title_ok(["The Story Part 2"]))

    def test_multiple_titles_all_must_pass(self):
        self.assertTrue(parser.title_ok(["A Story", "Another Story"]))
        self.assertFalse(parser.title_ok(["A Story", "Part 2"]))

    def test_story_excluded(self):
        with patch.object(parser.storymap, "STORIES_TO_EXCLUDE", [17]):
            self.assertTrue(parser.story_excluded(17))
            self.assertFalse(parser.story_excluded(18))

    def test_metadata_missing(self):
        self.assertEqual(
            parser._metadata_rejection(None, 42), "No data for this story, skipping"
        )
        self.assertEqual(
            parser._metadata_rejection(metadata(subjects=()), 42),
            "No data for this story, skipping",
        )
        self.assertEqual(
            parser._metadata_rejection(metadata(titles=()), 42),
            "No title for this story, skipping",
        )

    def test_metadata_rejection_reasons(self):
        self.assertEqual(
            parser._metadata_rejection(metadata(languages=("fr",)), 42),
            "Metadata not suitable, skipping.",
        )
        self.assertEqual(
            parser._metadata_rejection(metadata(authors=()), 42),
            "Metadata not suitable, skipping.",
        )
        self.assertEqual(
            parser._metadata_rejection(metadata(subjects=("PN", "History")), 42),
            "Metadata not suitable, skipping.",
        )

    def test_metadata_exclusion(self):
        with patch.object(parser.storymap, "STORIES_TO_EXCLUDE", [42]):
            self.assertEqual(
                parser._metadata_rejection(metadata(), 42),
                "Story on exclusion list, skipping.",
            )

    def test_eligible_metadata(self):
        self.assertIsNone(parser._metadata_rejection(metadata(), 42))


class ChapterDetectionTests(unittest.TestCase):
    def test_two_numbered_chapters(self):
        body = "CHAPTER I\n\nBeginning.\n\nCHAPTER II\n\nMiddle."
        self.assertTrue(parser.chaptered(body))

    def test_table_of_contents(self):
        self.assertTrue(parser.chaptered("Table of Contents\n\nA story."))

    def test_plain_prose_not_chaptered(self):
        self.assertFalse(parser.chaptered(long_body()))

    def test_all_caps_sentence_not_chapter_heading(self):
        self.assertFalse(parser.possible_internal_chapter_name('"LEAVE ME ALONE."'))

    def test_chapter_heading_recognized(self):
        self.assertTrue(parser.possible_internal_chapter_name("CHAPTER ONE"))


class TitleAndAuthorTests(unittest.TestCase):
    def test_normalization(self):
        self.assertEqual(parser._norm("_The Rose: Of Dawn!_"), "the rose of dawn")
        self.assertEqual(parser.normalize("_A-Title!_"), "a title")

    def test_title_variants_colon(self):
        variants = parser._title_variants(
            "The Last Christmas Tree: An Idyl of Immortality"
        )
        self.assertIn("The Last Christmas Tree", variants)
        self.assertIn("Last Christmas Tree", variants)

    def test_title_variants_marc_subtitle(self):
        variants = parser._title_variants(
            "Obil, Keeper of Camels : $b being the parable"
        )
        self.assertIn("Obil, Keeper of Camels", variants)

    def test_title_variants_leading_article(self):
        variants = parser._title_variants("The Devil's Asteroid")
        self.assertIn("Devil's Asteroid", variants)

    def test_title_variant_does_not_accept_arbitrary_prefix(self):
        variants = parser._title_variants("Short: a subtitle")
        self.assertNotIn("Short", variants)

    def test_title_line_standalone(self):
        self.assertTrue(parser._title_line("DEVIL'S ASTEROID", "The Devil's Asteroid"))
        self.assertFalse(
            parser._title_line(
                "The devil's asteroid appeared overhead.", "The Devil's Asteroid"
            )
        )

    def test_multiline_title_span(self):
        lines = ["THE ROSE OF DAWN", "A TALE OF THE SOUTH SEA", "", "Body"]
        last = parser._title_span(
            lines, 0, len(lines), "The Rose of Dawn: A Tale of the South Sea"
        )
        self.assertEqual(last, 1)

    def test_author_reverse_bibliographic_name(self):
        self.assertEqual(
            parser._author_line("By James Lane Allen", ["Allen, James Lane"]),
            "Allen, James Lane",
        )

    def test_author_pseudonym(self):
        self.assertEqual(
            parser._author_line("By A. Writer", ["A. Writer"]), "A. Writer"
        )

    def test_author_name_not_in_prose(self):
        self.assertIsNone(
            parser._author_line(
                "Alice Author entered the room and looked around.", ["Author, Alice"]
            )
        )

    def test_terminal_signature(self):
        self.assertEqual(
            parser._terminal_author_signature("--ALICE AUTHOR", ["Alice Author"]),
            "Alice Author",
        )
        self.assertIsNone(
            parser._terminal_author_signature("Alice Author spoke.", ["Alice Author"])
        )


class TextCleanupTests(unittest.TestCase):
    def test_unwrap_lines(self):
        result = parser.clean_story_text("First physical\nline.\n\nSecond paragraph.")
        self.assertEqual(result, "First physical line.\n\nSecond paragraph.\n")

    def test_preserve_lines_when_requested(self):
        result = parser.clean_story_text("Line one\nLine two", unwrap_lines=False)
        self.assertEqual(result, "Line one\nLine two\n")

    def test_strip_italics(self):
        self.assertEqual(parser.clean_story_text("A _quiet_ word."), "A quiet word.\n")
        self.assertEqual(
            parser.clean_story_text("A _quiet_ word.", strip_italics=False),
            "A _quiet_ word.\n",
        )

    def test_remove_the_end_optional(self):
        self.assertIn("THE END", parser.clean_story_text("Story ending.\n\nTHE END"))
        self.assertEqual(
            parser.clean_story_text("Story ending.\n\nTHE END", remove_the_end=True),
            "Story ending.\n",
        )

    def test_the_end_inside_narrative_retained(self):
        result = parser.clean_story_text(
            "THE END\n\nThere was another scene.", remove_the_end=True
        )
        self.assertIn("THE END", result)

    def test_scene_break_default_removal(self):
        result = parser.clean_story_text("One.\n\n* * *\n\nTwo.")
        self.assertNotIn("***", result)
        self.assertIn("Two.", result)

    def test_scene_break_preservation_option(self):
        result = parser.clean_story_text(
            "One.\n\n* * *\n\nTwo.", remove_scene_breaks=False
        )
        self.assertIn("***", result)

    def test_bracketed_editorial_block(self):
        result = parser.clean_story_text(
            "[Transcriber's Note: corrected a typo]\n\nNarrative line."
        )
        self.assertNotIn("Transcriber", result)
        self.assertIn("Narrative line.", result)

    def test_removed_editorial_count(self):
        result, count = parser.clean_story_text(
            "[Transcriber's Note: text]\n\nBody.", return_removed_count=True
        )
        self.assertEqual(count, 1)
        self.assertEqual(result, "Body.\n")

    def test_unicode_apostrophe_editorial(self):
        self.assertTrue(parser._editor_marker("[Transcriber’s Note: corrected]"))
        self.assertTrue(parser._editor_heading("Transcriber’s Note"))

    def test_boundary_diagnostics_structure(self):
        text = "*** START OF THE PROJECT GUTENBERG EBOOK A STORY\n\nA STORY\n\nBy Alice Author\n\nA real narrative begins here and continues.\n\n*** END OF THE PROJECT GUTENBERG EBOOK A STORY"
        start, end, diagnostics = parser.identify_story_boundaries(
            text, "A Story", ["Author, Alice"]
        )
        self.assertIsInstance(start, int)
        self.assertIsInstance(end, int)
        self.assertLess(start, end)
        self.assertTrue(diagnostics.start_marker_found)
        self.assertTrue(diagnostics.end_marker_found)

    def test_diagnostics_serializable(self):
        text = "THE EXAMPLE STORY\n\nBy Alice Author\n\nThis narrative paragraph continues beyond the headings and title."
        body, diagnostics = parser.clean_gutenberg_story(
            text, "The Example Story", ["Author, Alice"], return_diagnostics=True
        )
        self.assertIsInstance(body, str)
        self.assertIsInstance(diagnostics, dict)
        self.assertIn("warnings", diagnostics)
        json.dumps(diagnostics)

    def test_terminal_limited_edition(self):
        lines = [
            "Narrative ending.",
            "",
            "NINE HUNDRED AND FIFTY COPIES OF THIS BOOK PRINTED ON PAPER",
        ]
        warnings = []
        end = parser._trim_terminal_imprint(lines, 0, len(lines), [], [], warnings)
        self.assertEqual(end, 1)
        self.assertIn("terminal_limited_edition_colophon_removed", warnings)

    def test_terminal_imprint_not_narrative(self):
        lines = ["Narrative ending.", "", "The University Press, Cambridge"]
        warnings = []
        end = parser._trim_terminal_imprint(lines, 0, len(lines), [], [], warnings)
        self.assertEqual(end, 1)

    def test_terminal_prose_not_trimmed(self):
        lines = ["Narrative ending.", "", "The captain went home and slept."]
        warnings = []
        end = parser._trim_terminal_imprint(lines, 0, len(lines), [], [], warnings)
        self.assertEqual(end, len(lines))


class InspectionTests(unittest.TestCase):
    def setUp(self):
        self.meta = metadata()
        self.source = source_with(self.meta)

    def test_inspect_story_uses_explicit_source(self):
        with patch.object(
            parser, "clean_gutenberg_story", return_value=long_body()
        ) as clean:
            report = parser.inspect_story(42, source=self.source)
        self.source.metadata.assert_called_once_with(42)
        self.source.read.assert_called_once_with(self.meta)
        self.assertEqual(report["gutenberg_id"], 42)
        self.assertIsNone(report["rejection"])
        self.assertEqual(report["metadata"]["aliases"], ["A. Writer"])
        self.assertEqual(
            report["provenance"]["source_uri"], "https://www.gutenberg.org/ebooks/42"
        )
        self.assertEqual(clean.call_args.kwargs["title"], ["The Example Story"])
        self.assertEqual(clean.call_args.kwargs["authors"], ["Author, Alice"])
        self.assertEqual(clean.call_args.kwargs["pseudonyms"], ["A. Writer"])

    def test_ineligible_does_not_read_source(self):
        source = source_with(metadata(languages=("fr",)))
        report = parser.inspect_story(42, source=source)
        self.assertEqual(report["rejection"], "Metadata not suitable, skipping.")
        source.read.assert_not_called()

    def test_missing_metadata_does_not_read_source(self):
        source = source_with()
        source.metadata.return_value = None
        report = parser.inspect_story(42, source=source)
        self.assertEqual(report["rejection"], "No data for this story, skipping")
        source.read.assert_not_called()

    def test_normalizes_physical_line_endings(self):
        self.source.read.return_value.cleaned.text = "a\r\nb\rc"
        with patch.object(
            parser, "clean_gutenberg_story", return_value=long_body()
        ) as clean:
            parser.inspect_story(42, source=self.source)
        self.assertEqual(clean.call_args.args[0], "a\nb\nc")

    def test_recovery_is_called_after_extraction(self):
        with patch.object(parser, "clean_gutenberg_story", return_value="before"):
            with patch.object(
                parser, "_repair_verified_opening", return_value=long_body()
            ) as repair:
                report = parser.inspect_story(65347, source=self.source)
        self.assertEqual(report["body"], long_body())
        self.assertEqual(repair.call_args.args[0], 65347)
        self.assertEqual(repair.call_args.args[-1], "before")

    def test_rejected_short_still_in_report(self):
        with patch.object(parser, "clean_gutenberg_story", return_value="Short text."):
            report = parser.inspect_story(42, source=self.source)
        self.assertEqual(report["rejection"], "Story is too short, skipping.")
        self.assertEqual(report["body"], "Short text.")

    def test_chaptered_rejection_retains_body(self):
        body = "CHAPTER I\n\nSome narrative.\n\nCHAPTER II\n\nMore narrative."
        with patch.object(parser, "clean_gutenberg_story", return_value=body):
            report = parser.inspect_story(42, source=self.source)
        self.assertEqual(report["rejection"], "Story has chapters, skipping.")
        self.assertEqual(report["body"], body)

    def test_read_error_propagates(self):
        self.source.read.side_effect = RuntimeError("failure")
        with self.assertRaisesRegex(RuntimeError, "failure"):
            parser.inspect_story(42, source=self.source)

    def test_parser_does_not_write_during_inspection(self):
        with patch.object(parser, "clean_gutenberg_story", return_value=long_body()):
            with patch.object(parser.story_output, "publish") as publish:
                parser.inspect_story(42, source=self.source)
        publish.assert_not_called()


class VerifiedOpeningTests(unittest.TestCase):
    def test_verified_id_set(self):
        expected = {65347, 24566, 50940, 31964, 60393, 65241}
        self.assertEqual(set(parser._VERIFIED_NARRATIVE_OPENINGS), expected)

    def test_unlisted_id_unchanged(self):
        body = "Previously extracted text"
        result = parser._repair_verified_opening(
            42, "text", ["Title"], ["Author"], [], body
        )
        self.assertEqual(result, body)

    def test_missing_anchor_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "anchor"):
            parser._repair_verified_opening(
                65347, "No recognizable text", ["Title"], ["Author"], [], "Old text"
            )

    def test_duplicate_anchor_fails_closed(self):
        anchor = "El outer-thought I've had all I want of it haven't you"
        text = anchor + "\n" + anchor
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            parser._repair_verified_opening(
                65347, text, ["Title"], ["Author"], [], "Old text"
            )

    def test_anchor_after_existing_boundary_is_noop(self):
        anchor = "El outer-thought I've had all I want of it haven't you"
        with patch.object(
            parser, "identify_story_boundaries", return_value=(0, 4, None)
        ):
            with patch.object(parser, "_refine_front_boundary", return_value=0):
                with patch.object(
                    parser, "_refine_repeated_display_heading", return_value=0
                ):
                    result = parser._repair_verified_opening(
                        65347,
                        anchor + "\nMore",
                        ["Title"],
                        ["Author"],
                        [],
                        "Already good",
                    )
        self.assertEqual(result, "Already good")


class PublishAndRegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.meta = metadata()
        self.source = source_with(self.meta)
        self.gatherer = Mock()
        self.gatherer.path = self.temp.name
        self.gatherer.ensure.return_value = (
            "bucket",
            str(pathlib.Path(self.temp.name) / "story.json"),
        )
        self.filename = "the_example_story__author.json"
        self.registry_check = patch.object(
            parser.registry, "check_story", return_value=False
        )
        self.registry_add = patch.object(parser.registry, "add_story")
        self.names = patch.object(
            parser.names, "title_and_author_to_filename", return_value=self.filename
        )
        self.existing = patch.object(
            parser.story_output, "existing", return_value=False
        )
        self.publish = patch.object(parser.story_output, "publish", return_value=True)
        self.normalize = patch.object(parser.normalization, "normalize_story_dict")
        self.inspection = patch.object(
            parser,
            "_inspect_metadata",
            return_value={
                "rejection": None,
                "body": long_body(),
                "provenance": {"source_uri": "https://www.gutenberg.org/ebooks/42"},
            },
        )
        self.check_mock = self.registry_check.start()
        self.add_mock = self.registry_add.start()
        self.names_mock = self.names.start()
        self.existing_mock = self.existing.start()
        self.publish_mock = self.publish.start()
        self.normalize_mock = self.normalize.start()
        self.inspect_mock = self.inspection.start()
        for patcher in (
            self.registry_check,
            self.registry_add,
            self.names,
            self.existing,
            self.publish,
            self.normalize,
            self.inspection,
        ):
            self.addCleanup(patcher.stop)

    def test_new_story_published(self):
        result = parser.gather_story_result(self.gatherer, 42, source=self.source)
        self.assertEqual(result.disposition, "written")
        self.assertIsNone(result.rejection)
        self.assertEqual(result.path, self.gatherer.ensure.return_value[1])
        self.source.metadata.assert_called_once_with(42)
        self.inspect_mock.assert_called_once_with(42, self.meta, self.source)
        self.gatherer.ensure.assert_called_once_with("the_example_story__author")
        self.publish_mock.assert_called_once()
        self.add_mock.assert_called_once_with(
            "the_example_story", "author", source="Gutenberg mass retrieval"
        )

    def test_published_document_contents(self):
        parser.gather_story_result(self.gatherer, 42, source=self.source)
        document = self.publish_mock.call_args.args[1]
        self.assertEqual(document["name"], "The Example Story")
        self.assertEqual(document["author"], ["Author, Alice"])
        self.assertEqual(document["body"], long_body())
        self.assertEqual(
            document["metadata"]["gettenberg"]["source_uri"],
            "https://www.gutenberg.org/ebooks/42",
        )
        self.assertEqual(document["metadata"]["name"], self.filename)

    def test_normalization_before_publication(self):
        calls = Mock()
        self.normalize_mock.side_effect = lambda *args, **kwargs: calls.normalize(
            *args, **kwargs
        )
        self.publish_mock.side_effect = lambda *args, **kwargs: calls.publish(
            *args, **kwargs
        )
        parser.gather_story_result(self.gatherer, 42, source=self.source)
        self.assertEqual(calls.mock_calls[0][0], "normalize")
        self.assertEqual(calls.mock_calls[1][0], "publish")
        self.assertEqual(
            self.normalize_mock.call_args.kwargs["story_id"],
            "the_example_story__author",
        )

    def test_registry_duplicate_skips_before_read(self):
        self.check_mock.return_value = True
        result = parser.gather_story_result(self.gatherer, 42, source=self.source)
        self.assertEqual(result.disposition, "skipped")
        self.assertIn("already appears", result.rejection)
        self.source.read.assert_not_called()
        self.inspect_mock.assert_not_called()
        self.existing_mock.assert_not_called()
        self.add_mock.assert_not_called()

    def test_existing_output_reused_and_registered(self):
        self.existing_mock.return_value = True
        result = parser.gather_story_result(self.gatherer, 42, source=self.source)
        self.assertEqual(result.disposition, "reused")
        self.assertIsNone(result.rejection)
        self.assertEqual(
            pathlib.Path(result.path).name, parser.discovery.CANONICAL_STORY_FILENAME
        )
        self.inspect_mock.assert_not_called()
        self.publish_mock.assert_not_called()
        self.add_mock.assert_called_once()

    def test_metadata_rejection_before_registry(self):
        self.source.metadata.return_value = metadata(languages=("fr",))
        result = parser.gather_story_result(self.gatherer, 42, source=self.source)
        self.assertEqual(result.disposition, "skipped")
        self.check_mock.assert_not_called()
        self.add_mock.assert_not_called()
        self.publish_mock.assert_not_called()

    def test_chaptered_or_short_rejects_without_registration(self):
        self.inspect_mock.return_value = {
            "rejection": "Story has chapters, skipping.",
            "body": "Short",
            "provenance": None,
        }
        result = parser.gather_story_result(self.gatherer, 42, source=self.source)
        self.assertEqual(result.disposition, "skipped")
        self.add_mock.assert_not_called()
        self.publish_mock.assert_not_called()

    def test_publication_false_does_not_register(self):
        self.publish_mock.return_value = False
        result = parser.gather_story_result(self.gatherer, 42, source=self.source)
        self.assertEqual(result.disposition, "reused")
        self.add_mock.assert_not_called()

    def test_publication_error_does_not_register(self):
        self.publish_mock.side_effect = OSError("disk full")
        with self.assertRaisesRegex(OSError, "disk full"):
            parser.gather_story_result(self.gatherer, 42, source=self.source)
        self.add_mock.assert_not_called()

    def test_acquisition_error_does_not_register(self):
        self.inspect_mock.side_effect = RuntimeError("download failed")
        with self.assertRaisesRegex(RuntimeError, "download failed"):
            parser.gather_story_result(self.gatherer, 42, source=self.source)
        self.add_mock.assert_not_called()

    def test_registration_error_propagates(self):
        self.add_mock.side_effect = OSError("registry unavailable")
        with self.assertRaisesRegex(OSError, "registry unavailable"):
            parser.gather_story_result(self.gatherer, 42, source=self.source)
        self.publish_mock.assert_called_once()

    def test_gather_story_legacy_tuple(self):
        result = parser.gather_story(self.gatherer, 42, source=self.source)
        self.assertEqual(result, (42, self.gatherer.ensure.return_value[1], None))

    def test_result_dataclass_is_frozen(self):
        result = parser.StoryGatherResult(42, None, "skipped", "skipped")
        with self.assertRaises(dataclasses.FrozenInstanceError):
            result.disposition = "written"


if __name__ == "__main__":
    unittest.main()
