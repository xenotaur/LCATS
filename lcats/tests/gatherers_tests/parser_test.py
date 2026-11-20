"""Unit tests for LCATS using its actual package imports.

Run from the LCATS repository root:
    python -m unittest discover -s tests -p '*_test.py' -v
"""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from dataclasses import dataclass

from lcats.gatherers import downloaders, normalization, parser, registry, story_output
from lcats.gatherers.mass_quantities import storymap
from lcats.gettenberg import resources
from lcats.utils import names


class CaptureOutput:
    """Capture console output without relying on another test framework."""

    def __init__(self):
        self.stdout = io.StringIO()
        self.stderr = io.StringIO()

    def readouterr(self):
        result = SimpleNamespace(
            out=self.stdout.getvalue(),
            err=self.stderr.getvalue(),
        )

        self.stdout.seek(0)
        self.stdout.truncate(0)
        self.stderr.seek(0)
        self.stderr.truncate(0)

        return result


class LCATSTestCase(unittest.TestCase):
    """Provide the same temporary-file and mock cleanup as existing LCATS tests."""

    def setUp(self):
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary_directory.cleanup)

        self.tmp_path = Path(self._temporary_directory.name)
        self.capsys = CaptureOutput()

        self._stdout_capture = contextlib.redirect_stdout(self.capsys.stdout)
        self._stderr_capture = contextlib.redirect_stderr(self.capsys.stderr)

        self._stdout_capture.__enter__()
        self.addCleanup(self._stdout_capture.__exit__, None, None, None)

        self._stderr_capture.__enter__()
        self.addCleanup(self._stderr_capture.__exit__, None, None, None)

    def patch_attribute(self, target, name, replacement):
        """Patch a real module or object, restoring it after this test."""
        patcher = patch.object(target, name, replacement)
        patcher.start()
        self.addCleanup(patcher.stop)

        return replacement


@dataclass
class Metadata:
    titles: tuple = ("Sample Story",)
    authors: tuple = ("Author, Alice",)
    aliases: tuple = ()
    subjects: tuple = ("PS", "Short stories")
    languages: tuple = ("en",)


def source_fixture():
    metadata = Metadata()

    prepared = SimpleNamespace(
        cleaned=SimpleNamespace(text="Sample text"),
        provenance=Mock(return_value={"source_uri": "https://example.test/book"}),
    )

    return SimpleNamespace(
        metadata=Mock(return_value=metadata),
        read=Mock(return_value=prepared),
    )


def output_gatherer_fixture(tmp_path):
    return SimpleNamespace(
        path=str(tmp_path),
        ensure=Mock(return_value=(None, str(tmp_path / "story.json"))),
    )


SAMPLE_BOOK = "\n".join(
    [
        "Title: The Forgotten Island",
        "Author: Alice Author",
        "*** START OF THE PROJECT GUTENBERG EBOOK THE FORGOTTEN ISLAND",
        "The Forgotten Island",
        "By Alice Author",
        "",
        "The boat crossed the water as the late evening sun sank behind the hill.",
        "",
        "A second paragraph describes the island and its strange inhabitants.",
        "",
        "*** END OF THE PROJECT GUTENBERG EBOOK THE FORGOTTEN ISLAND",
    ]
)


class TestParser(LCATSTestCase):

    def modules(self, tmp_path):
        """Use real LCATS imports, mocking only external effects."""
        file_namer = Mock(return_value="sample__author.json")

        self.patch_attribute(names, "title_and_author_to_filename", file_namer)
        self.patch_attribute(normalization, "normalize_story_dict", Mock())
        self.patch_attribute(story_output, "existing", Mock(return_value=False))
        self.patch_attribute(story_output, "publish", Mock(return_value=True))
        self.patch_attribute(registry, "check_story", Mock(return_value=False))
        self.patch_attribute(registry, "add_story", Mock(return_value=True))

        return SimpleNamespace(
            parser=parser,
            storymap=storymap,
            names=names,
            normalization=normalization,
            story_output=story_output,
            registry=registry,
            downloaders=downloaders,
            resources=resources,
            tmp_path=tmp_path,
        )

    def test_normalization(self):
        for _case_index, (raw, expected) in enumerate(
            [
                ("The _Lost_ Story!", "the lost story"),
                ("  A---B  ", "a b"),
                ("Café", "cafe"),
            ]
        ):
            with self.subTest(raw=raw, expected=expected):
                tmp_path = self.tmp_path / str(_case_index)
                tmp_path.mkdir(parents=True, exist_ok=True)
                modules = self.modules(tmp_path)
                self.assertEqual(modules.parser._norm(raw), expected)

    def test_title_variants_include_article_and_subtitle(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        variants = modules.parser._title_variants(
            "The Forgotten Island: A Curious Tale"
        )

        self.assertIn("The Forgotten Island: A Curious Tale", variants)

        self.assertIn("Forgotten Island: A Curious Tale", variants)

        self.assertIn("The Forgotten Island", variants)

        self.assertIn("Forgotten Island", variants)

    def test_title_line_matching(self):
        for _case_index, (display, expected) in enumerate(
            [
                ("THE FORGOTTEN ISLAND", True),
                ("The Forgotten Island by", True),
                ("The Forgotten Island by Alice Author", True),
                ("A different story entirely", False),
            ]
        ):
            with self.subTest(display=display, expected=expected):
                tmp_path = self.tmp_path / str(_case_index)
                tmp_path.mkdir(parents=True, exist_ok=True)
                modules = self.modules(tmp_path)
                actual = modules.parser._title_line(display, "The Forgotten Island")
                self.assertIs(actual, expected)

    def test_multiline_title_span_with_one_blank(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        lines = ["The Forgotten", "", "Island", "Start of narrative"]

        self.assertEqual(
            modules.parser._title_span(lines, 0, len(lines), "The Forgotten Island"), 2
        )

    def test_multiline_title_rejects_leading_blank(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        lines = ["", "The Forgotten", "Island"]

        self.assertIs(
            modules.parser._title_span(lines, 0, len(lines), "The Forgotten Island"),
            None,
        )

    def test_author_reversed_catalog_name(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        actual = modules.parser._author_line("By Alice Author", ["Author, Alice"])

        self.assertEqual(actual, "Author, Alice")

    def test_author_middle_initial(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        actual = modules.parser._author_line(
            "By Raymond Z. Gallun", ["Raymond Zinke Gallun"]
        )

        self.assertEqual(actual, "Raymond Zinke Gallun")

    def test_author_does_not_match_unrelated_name(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)

        self.assertIs(
            modules.parser._author_line("By Someone Else", ["Author, Alice"]), None
        )

    def test_editorial_markers(self):
        for _case_index, line in enumerate(
            [
                "[Transcriber's Note: corrected spelling]",
                "[Transcriber’s Note: corrected spelling]",
                "[Illustration]",
            ]
        ):
            with self.subTest(line=line):
                tmp_path = self.tmp_path / str(_case_index)
                tmp_path.mkdir(parents=True, exist_ok=True)
                modules = self.modules(tmp_path)
                self.assertTrue(modules.parser._editor_marker(line))

    def test_editorial_headings(self):
        for _case_index, line in enumerate(
            ["Transcriber's Note", "Transcriber’s Note:", "Proofreader's Notes"]
        ):
            with self.subTest(line=line):
                tmp_path = self.tmp_path / str(_case_index)
                tmp_path.mkdir(parents=True, exist_ok=True)
                modules = self.modules(tmp_path)
                self.assertTrue(modules.parser._editor_heading(line))

    def test_editorial_markers_do_not_match_normal_prose(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)

        self.assertFalse(
            modules.parser._editor_marker("The transcriber entered the room.")
        )

        self.assertFalse(
            modules.parser._editor_heading("A transcriber's note was found.")
        )

    def test_terminal_signature(self):
        for _case_index, (line, expected) in enumerate(
            [
                ("--ALICE AUTHOR", "Alice Author"),
                ("By Alice Author", "Alice Author"),
                ("Alice Author wrote a letter.", None),
            ]
        ):
            with self.subTest(line=line, expected=expected):
                tmp_path = self.tmp_path / str(_case_index)
                tmp_path.mkdir(parents=True, exist_ok=True)
                modules = self.modules(tmp_path)
                actual = modules.parser._terminal_author_signature(
                    line, ["Alice Author"]
                )
                self.assertEqual(actual, expected)

    def test_diagnostics_to_dict(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        diagnostics = modules.parser.ExtractionDiagnostics(
            title_found=True, warnings=("very_short_extraction",)
        )
        result = diagnostics.to_dict()

        self.assertIs(result["title_found"], True)

        self.assertEqual(result["warnings"], ("very_short_extraction",))

    def test_identify_boundaries_with_metadata(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        start, end, details = modules.parser.identify_story_boundaries(
            SAMPLE_BOOK, title="The Forgotten Island", authors=["Alice Author"]
        )
        lines = SAMPLE_BOOK.splitlines()

        self.assertTrue(details.start_marker_found)

        self.assertTrue(details.end_marker_found)

        self.assertTrue(details.title_found)

        self.assertTrue(lines[start].startswith("The boat crossed"))

        self.assertTrue(all((not line.strip() for line in lines[end:-1])))

        self.assertTrue(lines[-1].startswith("*** END"))

    def test_identify_boundaries_with_header_fallback(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        start, end, details = modules.parser.identify_story_boundaries(SAMPLE_BOOK)

        self.assertTrue(details.title_found)

        self.assertEqual(details.matched_author, "Alice Author")

        self.assertLess(start, end)

    def test_identify_boundaries_without_wrappers_warns(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        text = (
            "The Forgotten Island\nBy Alice Author\n\n"
            + "There were several people aboard the boat that morning. " * 2
        )
        _, _, details = modules.parser.identify_story_boundaries(
            text, title="The Forgotten Island", authors=["Alice Author"]
        )

        self.assertIn("no_standard_start_marker", details.warnings)

        self.assertIn("no_standard_end_marker", details.warnings)

    def test_clean_gutenberg_story_extracts_narrative(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        story, details = modules.parser.clean_gutenberg_story(
            SAMPLE_BOOK,
            title="The Forgotten Island",
            authors=["Alice Author"],
            return_diagnostics=True,
        )

        self.assertTrue(story.startswith("The boat crossed"))

        self.assertIn("A second paragraph", story)

        self.assertNotIn("START OF", story)

        self.assertNotIn("END OF", story)

        self.assertIs(details["title_found"], True)

    def test_clean_gutenberg_story_strips_terminal_author(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        text = SAMPLE_BOOK.replace(
            "*** END OF THE PROJECT GUTENBERG",
            "--ALICE AUTHOR\n\n*** END OF THE PROJECT GUTENBERG",
        )
        story, details = modules.parser.clean_gutenberg_story(
            text,
            title="The Forgotten Island",
            authors=["Alice Author"],
            return_diagnostics=True,
        )

        self.assertNotIn("--ALICE AUTHOR", story)

        self.assertEqual(details["removed_terminal_signature"], "Alice Author")

    def test_clean_gutenberg_story_reports_short_extraction(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        _, details = modules.parser.clean_gutenberg_story(
            SAMPLE_BOOK,
            title="The Forgotten Island",
            authors=["Alice Author"],
            return_diagnostics=True,
        )

        self.assertIn("very_short_extraction", details["warnings"])

    def test_clean_story_text_unwraps_physical_lines(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        result = modules.parser.clean_story_text(
            "The sky was clear\nand the wind was cold.\n\nThe next day arrived."
        )

        self.assertEqual(
            result,
            "The sky was clear and the wind was cold.\n\nThe next day arrived.\n",
        )

    def test_clean_story_text_preserves_physical_lines_if_requested(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        result = modules.parser.clean_story_text(
            "one line\nsecond line", unwrap_lines=False
        )

        self.assertEqual(result, "one line\nsecond line\n")

    def test_clean_story_text_scene_break_toggle(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        text = "First scene.\n\n* * *\n\nSecond scene."
        removed = modules.parser.clean_story_text(text)
        retained = modules.parser.clean_story_text(text, remove_scene_breaks=False)

        self.assertNotIn("***", removed)

        self.assertIn("***", retained)

        self.assertIn("First scene.", retained)

        self.assertIn("Second scene.", retained)

    def test_clean_story_text_italic_toggle(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        text = "She read the _old_ letter."

        self.assertIn("old", modules.parser.clean_story_text(text))

        self.assertNotIn("_old_", modules.parser.clean_story_text(text))

        self.assertIn(
            "_old_", modules.parser.clean_story_text(text, strip_italics=False)
        )

    def test_clean_story_text_removes_only_terminal_the_end(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        text = "The end was almost visible.\n\nTHE END."
        cleaned = modules.parser.clean_story_text(text, remove_the_end=True)

        self.assertIn("The end was almost visible.", cleaned)

        self.assertNotIn("THE END.", cleaned)

    def test_clean_story_text_keeps_the_end_by_default(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)

        self.assertIn("THE END.", modules.parser.clean_story_text("THE END."))

    def test_clean_story_text_removes_editorial_block_and_counts(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        cleaned, count = modules.parser.clean_story_text(
            "A first line.\n\n[Illustration: a boat]\n\nA final line.",
            return_removed_count=True,
        )

        self.assertNotIn("Illustration", cleaned)

        self.assertIn("A first line.", cleaned)

        self.assertIn("A final line.", cleaned)

        self.assertEqual(count, 1)

    def test_chaptered_detects_contents(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)

        self.assertTrue(
            modules.parser.chaptered("Table of Contents\n\nA story follows")
        )

    def test_chaptered_detects_sequential_chapters(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)

        self.assertTrue(
            modules.parser.chaptered("Chapter I\n\nStory text\n\nChapter II")
        )

    def test_chaptered_accepts_ordinary_prose(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)

        self.assertFalse(
            modules.parser.chaptered(
                "The first person entered the room.\n\nThe second person followed."
            )
        )

    def test_possible_internal_chapter_heading(self):
        for _case_index, (line, expected) in enumerate(
            [
                ("THE DARK ROOM", True),
                ("THE END", False),
                ('"A STRANGE STATEMENT"', False),
                ("THE CLOCK:", False),
            ]
        ):
            with self.subTest(line=line, expected=expected):
                tmp_path = self.tmp_path / str(_case_index)
                tmp_path.mkdir(parents=True, exist_ok=True)
                modules = self.modules(tmp_path)
                self.assertIs(
                    modules.parser.possible_internal_chapter_name(line), expected
                )

    def test_subject_accepts_short_fiction(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)

        self.assertTrue(modules.parser.subject_ok(("PS", "Short stories")))

        self.assertTrue(modules.parser.subject_ok(("PR", "Fiction")))

    def test_subject_rejects_epistolary(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)

        self.assertFalse(
            modules.parser.subject_ok(("PS", "Short stories", "Epistolary fiction"))
        )

    def test_subject_requires_loc_classification(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)

        self.assertFalse(modules.parser.subject_ok(("Short stories",)))

    def test_english_only_check(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)

        self.assertTrue(modules.parser.only_english(("en",)))

        self.assertFalse(modules.parser.only_english(("en", "fr")))

        self.assertFalse(modules.parser.only_english(("fr",)))

    def test_title_and_author_metadata_rules(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        parser = modules.parser

        self.assertTrue(parser.title_ok(["The Forgotten Island"]))

        self.assertFalse(parser.title_ok(["An Anthology; and Other Stories"]))

        self.assertFalse(parser.title_ok(["Volume 2"]))

        self.assertTrue(parser.author_ok(["Author, Alice"]))

        self.assertFalse(parser.author_ok([]))

    def test_metadata_rejection_for_missing_metadata(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)

        self.assertEqual(
            modules.parser._metadata_rejection(None, 123),
            "No data for this story, skipping",
        )

    def test_metadata_rejection_for_missing_title(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        metadata = Metadata(titles=())

        self.assertEqual(
            modules.parser._metadata_rejection(metadata, 123),
            "No title for this story, skipping",
        )

    def test_metadata_rejection_for_non_english(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        metadata = Metadata(languages=("fr",))

        self.assertEqual(
            modules.parser._metadata_rejection(metadata, 123),
            "Metadata not suitable, skipping.",
        )

    def test_metadata_rejection_for_excluded_story(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)

        self.assertEqual(
            modules.parser._metadata_rejection(Metadata(), 64092),
            "Story on exclusion list, skipping.",
        )

    def test_inspect_rejected_story_does_not_read_text(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        source = source_fixture()
        source.metadata.return_value = Metadata(languages=("fr",))
        report = modules.parser.inspect_story(123, source=source)

        self.assertIs(report["body"], None)

        self.assertEqual(report["rejection"], "Metadata not suitable, skipping.")
        source.read.assert_not_called()

    def test_inspect_uses_correct_title_author_keyword_mapping(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        source = source_fixture()
        clean = Mock(return_value="A narrative body")
        self.patch_attribute(modules.parser, "clean_gutenberg_story", clean)
        self.patch_attribute(modules.parser, "chaptered", Mock(return_value=False))
        report = modules.parser.inspect_story(123, source=source)

        self.assertEqual(report["body"], "A narrative body")

        self.assertEqual(report["rejection"], "Story is too short, skipping.")

        self.assertEqual(
            clean.call_args.kwargs,
            {"title": ["Sample Story"], "authors": ["Author, Alice"], "pseudonyms": []},
        )

    def test_inspect_detects_chaptered_body(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        source = source_fixture()
        self.patch_attribute(
            modules.parser,
            "clean_gutenberg_story",
            Mock(return_value="Chapter I\n\nStory\n\nChapter II"),
        )
        report = modules.parser.inspect_story(123, source=source)

        self.assertEqual(report["rejection"], "Story has chapters, skipping.")

        self.assertIn("Chapter I", report["body"])

    def test_inspect_accepts_long_story(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        source = source_fixture()
        paragraphs = [f"Paragraph {index} has narrative prose." for index in range(12)]
        body = "\n\n".join(paragraphs)
        self.patch_attribute(
            modules.parser, "clean_gutenberg_story", Mock(return_value=body)
        )
        self.patch_attribute(modules.parser, "chaptered", Mock(return_value=False))
        report = modules.parser.inspect_story(123, source=source)

        self.assertIs(report["rejection"], None)

        self.assertEqual(report["body"], body)

        self.assertEqual(
            report["provenance"]["source_uri"], "https://example.test/book"
        )

    def test_story_result_skips_bad_metadata(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        source = source_fixture()
        output_gatherer = output_gatherer_fixture(tmp_path)
        source.metadata.return_value = Metadata(languages=("fr",))
        result = modules.parser.gather_story_result(output_gatherer, 123, source=source)

        self.assertEqual(result.disposition, "skipped")

        self.assertIs(result.path, None)
        source.read.assert_not_called()
        modules.registry.check_story.assert_not_called()
        modules.registry.add_story.assert_not_called()

    def test_story_result_registry_duplicate_skips_acquisition(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        source = source_fixture()
        output_gatherer = output_gatherer_fixture(tmp_path)
        modules.registry.check_story.return_value = True
        result = modules.parser.gather_story_result(output_gatherer, 123, source=source)

        self.assertIs(result.path, None)

        self.assertEqual(result.disposition, "skipped")

        self.assertIn("already appears", result.rejection)
        modules.registry.add_story.assert_not_called()
        source.read.assert_not_called()

    def test_story_result_reuses_existing_path(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        source = source_fixture()
        output_gatherer = output_gatherer_fixture(tmp_path)
        modules.story_output.existing.return_value = True
        result = modules.parser.gather_story_result(output_gatherer, 123, source=source)

        self.assertEqual(result.disposition, "reused")

        self.assertTrue(result.path.endswith("sample__author/story.json"))
        source.read.assert_not_called()
        modules.story_output.publish.assert_not_called()
        modules.registry.add_story.assert_called_once_with(
            "sample", "author", source="Gutenberg mass retrieval"
        )

    def test_story_result_rejects_short_body_without_publish(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        source = source_fixture()
        output_gatherer = output_gatherer_fixture(tmp_path)
        self.patch_attribute(
            modules.parser,
            "_inspect_metadata",
            Mock(return_value={"rejection": "Story is too short, skipping."}),
        )
        result = modules.parser.gather_story_result(output_gatherer, 123, source=source)

        self.assertEqual(result.disposition, "skipped")
        modules.story_output.publish.assert_not_called()
        output_gatherer.ensure.assert_not_called()
        modules.registry.add_story.assert_not_called()

    def test_story_result_publishes_normalized_story(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        source = source_fixture()
        output_gatherer = output_gatherer_fixture(tmp_path)
        self.patch_attribute(
            modules.parser,
            "_inspect_metadata",
            Mock(
                return_value={
                    "rejection": None,
                    "body": "Story prose",
                    "provenance": {"source_uri": "https://example.test/book"},
                }
            ),
        )
        result = modules.parser.gather_story_result(output_gatherer, 123, source=source)

        self.assertEqual(result.disposition, "written")

        self.assertEqual(result.path, str(modules.tmp_path / "story.json"))

        self.assertEqual(
            modules.story_output.publish.call_args.args[1]["body"], "Story prose"
        )

        self.assertEqual(
            modules.story_output.publish.call_args.args[1]["metadata"]["gettenberg"],
            {"source_uri": "https://example.test/book"},
        )
        modules.normalization.normalize_story_dict.assert_called_once()
        output_gatherer.ensure.assert_called_once_with("sample__author")
        modules.registry.add_story.assert_called_once_with(
            "sample", "author", source="Gutenberg mass retrieval"
        )

    def test_story_result_reports_reused_when_publish_declines(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        source = source_fixture()
        output_gatherer = output_gatherer_fixture(tmp_path)
        modules.story_output.publish.return_value = False
        self.patch_attribute(
            modules.parser,
            "_inspect_metadata",
            Mock(
                return_value={
                    "rejection": None,
                    "body": "Body",
                    "provenance": {"source_uri": "source://example"},
                }
            ),
        )
        result = modules.parser.gather_story_result(output_gatherer, 123, source=source)

        self.assertEqual(result.disposition, "reused")
        modules.registry.add_story.assert_not_called()

    def test_historical_gather_story_tuple(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        source = source_fixture()
        output_gatherer = output_gatherer_fixture(tmp_path)
        self.patch_attribute(
            modules.parser,
            "gather_story_result",
            Mock(
                return_value=modules.parser.StoryGatherResult(
                    123, "path", None, "written"
                )
            ),
        )
        result = modules.parser.gather_story(output_gatherer, 123, source=source)

        self.assertEqual(result, (123, "path", None))

    def test_registry_check_is_read_only_before_extraction(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        source = source_fixture()
        output_gatherer = output_gatherer_fixture(tmp_path)

        def inspect(story, metadata, story_source):
            modules.registry.check_story.assert_called_once_with("sample", "author")
            modules.registry.add_story.assert_not_called()
            return {"rejection": "Story has chapters, skipping."}

        self.patch_attribute(modules.parser, "_inspect_metadata", inspect)
        result = modules.parser.gather_story_result(output_gatherer, 123, source=source)

        self.assertEqual(result.disposition, "skipped")
        modules.registry.add_story.assert_not_called()

    def test_registry_add_happens_after_successful_publish(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        source = source_fixture()
        output_gatherer = output_gatherer_fixture(tmp_path)

        def inspect(story, metadata, story_source):
            modules.registry.add_story.assert_not_called()
            return {
                "rejection": None,
                "body": "Narrative",
                "provenance": {"source_uri": "source://example"},
            }

        def publish(path, data):
            modules.registry.add_story.assert_not_called()
            return True

        self.patch_attribute(modules.parser, "_inspect_metadata", inspect)
        modules.story_output.publish.side_effect = publish
        result = modules.parser.gather_story_result(output_gatherer, 123, source=source)

        self.assertEqual(result.disposition, "written")
        modules.registry.add_story.assert_called_once()

    def test_failures_leave_registry_unchanged(self):
        for _case_index, failing_operation in enumerate(
            ["read", "normalize", "ensure", "publish"]
        ):
            with self.subTest(failing_operation=failing_operation):
                tmp_path = self.tmp_path / str(_case_index)
                tmp_path.mkdir(parents=True, exist_ok=True)
                modules = self.modules(tmp_path)
                source = source_fixture()
                output_gatherer = output_gatherer_fixture(tmp_path)
                if failing_operation == "read":
                    source.read.side_effect = OSError("download failed")
                else:
                    self.patch_attribute(
                        modules.parser,
                        "_inspect_metadata",
                        Mock(
                            return_value={
                                "rejection": None,
                                "body": "Narrative",
                                "provenance": {"source_uri": "source://example"},
                            }
                        ),
                    )
                if failing_operation == "normalize":
                    modules.normalization.normalize_story_dict.side_effect = OSError(
                        "normalization failed"
                    )
                if failing_operation == "ensure":
                    output_gatherer.ensure.side_effect = OSError("ensure failed")
                if failing_operation == "publish":
                    modules.story_output.publish.side_effect = OSError("publish failed")
                with self.assertRaises(OSError):
                    modules.parser.gather_story_result(
                        output_gatherer, 123, source=source
                    )
                modules.registry.add_story.assert_not_called()

    def test_registry_add_error_propagates_after_publication(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        source = source_fixture()
        output_gatherer = output_gatherer_fixture(tmp_path)
        self.patch_attribute(
            modules.parser,
            "_inspect_metadata",
            Mock(
                return_value={
                    "rejection": None,
                    "body": "Narrative",
                    "provenance": {"source_uri": "source://example"},
                }
            ),
        )
        modules.registry.add_story.side_effect = OSError("registry unavailable")
        with self.assertRaisesRegex(OSError, "registry unavailable"):
            modules.parser.gather_story_result(output_gatherer, 123, source=source)
        modules.story_output.publish.assert_called_once()

    def test_failed_extraction_does_not_poison_later_retry(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        source = source_fixture()
        output_gatherer = output_gatherer_fixture(tmp_path)
        rejection = {"rejection": "Story is too short, skipping."}
        accepted = {
            "rejection": None,
            "body": "Narrative",
            "provenance": {"source_uri": "source://example"},
        }
        inspect = Mock(side_effect=[rejection, accepted])
        self.patch_attribute(modules.parser, "_inspect_metadata", inspect)
        first = modules.parser.gather_story_result(output_gatherer, 123, source=source)
        second = modules.parser.gather_story_result(output_gatherer, 123, source=source)

        self.assertEqual(first.disposition, "skipped")

        self.assertEqual(second.disposition, "written")

        self.assertEqual(modules.registry.check_story.call_count, 2)
        modules.registry.add_story.assert_called_once()


if __name__ == "__main__":
    unittest.main()
