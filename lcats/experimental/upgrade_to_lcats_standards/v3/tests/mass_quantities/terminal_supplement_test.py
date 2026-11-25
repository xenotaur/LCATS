"""Conservative behavioral coverage for terminal publisher matter and footnotes."""

import json
import pathlib
import tempfile
import unittest

from lcats.gatherers.mass_quantities import parser


OPENING = "A long day passed in the observatory while the instruments warmed up."
ENDING = "The final signal faded, and the expedition returned safely home."


def _extract(*tail, authors=None, front_byline="Jane Example"):
    """Extract a short Gutenberg-formatted story with the supplied terminal lines."""
    lines = [
        "Title: The Expedition", "Author: Jane Example",
        "*** START OF THE PROJECT GUTENBERG EBOOK THE EXPEDITION ***",
        "", "The Expedition", f"By {front_byline}", "", OPENING, "", ENDING,
        "", *tail, "", "*** END OF THE PROJECT GUTENBERG EBOOK THE EXPEDITION ***",
    ]
    return parser.clean_gutenberg_story(
        "\n".join(lines), title="The Expedition",
        authors=authors if authors is not None else ["Example, Jane"],
        return_diagnostics=True,
    )


class TerminalSupplementTest(unittest.TestCase):
    """Only evidence-backed publishing matter may be trimmed."""

    def test_terminal_printed_by_imprint(self):
        body, _ = _extract("PRINTED BY BILLING AND SONS, LIMITED GUILDFORD, ENGLAND.")
        self.assertEqual(body.splitlines()[-1], ENDING)

    def test_terminal_press_of_imprint(self):
        body, _ = _extract("PRESS OF W. B. CONKEY COMPANY, CHICAGO.")
        self.assertEqual(body.splitlines()[-1], ENDING)

    def test_terminal_country_life_press(self):
        body, _ = _extract("THE END", "", "THE COUNTRY LIFE PRESS GARDEN CITY, N.Y.")
        self.assertEqual(body.splitlines()[-1], ENDING)

    def test_printed_in_usa(self):
        body, _ = _extract("THE END", "", "PRINTED IN U. S. A.")
        self.assertEqual(body.splitlines()[-1], ENDING)

    def test_publisher_hugo_listing(self):
        body, _ = _extract(
            "THE END", "", 'As a service to our readers, we list the "Hugo" award winners for 1960:',
            "", "Best Novel: An Example", "", "The prizes were presented in Seattle.",
        )
        self.assertEqual(body.splitlines()[-1], ENDING)

    def test_publisher_advertising(self):
        body, _ = _extract(
            "THE END.", "", "ILLUSTRATED WORKS BY L. FROLICH.", "",
            "A BOOK BY SOMEONE. Crown 4to. Cloth gilt.",
        )
        self.assertEqual(body.splitlines()[-1], ENDING)

    def test_labeled_footnotes_separated(self):
        body, report = _extract(
            "THE END", "", "FOOTNOTES:", "", "[1] The units are fictional.",
            "", "[2] A second explanatory note.",
        )
        self.assertEqual(body.splitlines()[-1], ENDING)
        self.assertIn("[1] The units", report["terminal_footnotes"])
        self.assertIn("[2] A second", report["terminal_footnotes"])

    def test_unlabeled_numbered_footnotes_separated(self):
        body, report = _extract(
            "The End", "", "[1] The letter was edited.",
            "", "[2] The original report was transcribed.",
        )
        self.assertEqual(body.splitlines()[-1], ENDING)
        self.assertIn("[2]", report["terminal_footnotes"])

    def test_unknown_trailing_prose_preserved(self):
        body, report = _extract(
            "THE END", "", "The traveler woke and began the next journey.",
        )
        self.assertIn("The traveler woke", body)
        self.assertIn("THE END", body)
        self.assertIsNone(report["terminal_footnotes"])

    def test_footnote_like_narrative_preserved_without_end_marker(self):
        body, report = _extract("[1] This is a scene in a fictional manuscript.")
        self.assertIn("[1] This is a scene", body)
        self.assertIsNone(report["terminal_footnotes"])

    def test_pseudonym_matched_to_explicit_front_byline(self):
        body, _ = _extract(
            "--PAUL FLEHR", authors=["Pohl, Frederik"], front_byline="PAUL FLEHR"
        )
        self.assertEqual(body.splitlines()[-1], ENDING)

    def test_other_pseudonym_matched_to_front_byline(self):
        body, _ = _extract(
            "--WIN MARKS", authors=["Marks, Winston K."], front_byline="WIN MARKS"
        )
        self.assertEqual(body.splitlines()[-1], ENDING)

    def test_unverified_signature_preserved(self):
        body, _ = _extract("--IMAGINARY PERSON", authors=["Pohl, Frederik"])
        self.assertIn("--IMAGINARY PERSON", body)

    def test_narrative_printer_reference_preserved(self):
        body, _ = _extract('The sign read "PRINTED BY THE KING" but it was a joke.')
        self.assertIn("PRINTED BY THE KING", body)

    def test_terminal_end_marker_after_cleanup(self):
        body, _ = _extract("The End")
        self.assertEqual(body.splitlines()[-1], ENDING)

    def test_footnotes_json_saved(self):
        with tempfile.TemporaryDirectory() as directory:
            parser._save_terminal_footnotes(
                pathlib.Path(directory), 27462, "The Last Evolution", "[1] Unit explained."
            )
            record = json.loads((pathlib.Path(directory) / "footnotes.json").read_text(
                encoding="utf-8"
            ))
            self.assertEqual(record["gutenberg_id"], 27462)
            self.assertEqual(record["footnotes"], "[1] Unit explained.")


if __name__ == "__main__":
    unittest.main()


class TerminalSupplementPublicationTest(unittest.TestCase):
    """Write footnotes only when a newly extracted story is published."""

    def setUp(self):
        """Supply a temporary publisher and deterministic extraction report."""
        import types
        from unittest import mock

        self.mock = mock
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = pathlib.Path(self.temp.name)
        self.story_directory = self.directory / "a_story__example"
        self.story_file = self.story_directory / "story.json"
        self.metadata = types.SimpleNamespace(
            titles=["A Story"], authors=["Example, Jane"]
        )
        self.source = types.SimpleNamespace(
            metadata=mock.Mock(return_value=self.metadata),
        )
        self.gatherer = types.SimpleNamespace(
            path=str(self.directory),
            ensure=mock.Mock(side_effect=self._ensure),
        )
        self.report = {
            "rejection": None,
            "body": "A narrative " * 60,
            "confidence": "high",
            "raw_opening": ["A story."],
            "provenance": {"source_uri": "https://example.org"},
            "terminal_footnotes": "[1] Original explanatory footnote.",
        }
        patches = [
            mock.patch.object(parser, "_metadata_rejection", return_value=None),
            mock.patch.object(
                parser.names, "title_and_author_to_filename",
                return_value="a_story__example.txt", create=True,
            ),
            mock.patch.object(parser.registry, "check_story", return_value=False, create=True),
            mock.patch.object(parser.registry, "add_story", create=True),
            mock.patch.object(parser.story_output, "existing", return_value=False, create=True),
            mock.patch.object(
                parser.story_output, "publish", side_effect=self._publish, create=True
            ),
            mock.patch.object(parser, "_inspect_metadata", return_value=self.report),
            mock.patch.object(
                parser.extraction_records, "load_override", return_value=None, create=True
            ),
            mock.patch.object(
                parser.extraction_records, "extraction_record",
                return_value={"status": "ok"}, create=True,
            ),
            mock.patch.object(
                parser.extraction_records, "save_extraction_record", create=True
            ),
            mock.patch.object(
                parser.normalization, "normalize_story_dict", create=True
            ),
            mock.patch.object(
                parser.publication_year, "get_publication_date_from_id", create=True
            ),
        ]
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)

    def _ensure(self, slug):
        """Provide a correctly located story output path."""
        directory = self.directory / slug
        directory.mkdir(parents=True, exist_ok=True)
        return directory, str(directory / "story.json")

    def _publish(self, path, data):
        """Simulate a successful new story publication."""
        pathlib.Path(path).write_text(json.dumps(data), encoding="utf-8")
        return True

    def test_new_publication_saves_footnotes(self):
        result = parser.gather_story_result(self.gatherer, 42, source=self.source)
        self.assertEqual(result.disposition, "written")
        record = json.loads(
            (self.story_directory / "footnotes.json").read_text(encoding="utf-8")
        )
        self.assertEqual(record["footnotes"], self.report["terminal_footnotes"])

    def test_unlabeled_story_does_not_create_sidecar(self):
        self.report["terminal_footnotes"] = None
        parser.gather_story_result(self.gatherer, 42, source=self.source)
        self.assertFalse((self.story_directory / "footnotes.json").exists())

    def test_existing_story_does_not_overwrite_sidecar(self):
        self.story_directory.mkdir(parents=True)
        sidecar = self.story_directory / "footnotes.json"
        sidecar.write_text('{"previous": true}', encoding="utf-8")
        with self.mock.patch.object(parser.story_output, "existing", return_value=True):
            result = parser.gather_story_result(self.gatherer, 42, source=self.source)
        self.assertEqual(result.disposition, "reused")
        self.assertEqual(sidecar.read_text(encoding="utf-8"), '{"previous": true}')

    def test_failed_publication_does_not_create_sidecar(self):
        with self.mock.patch.object(parser.story_output, "publish", return_value=False):
            result = parser.gather_story_result(self.gatherer, 42, source=self.source)
        self.assertEqual(result.disposition, "reused")
        self.assertFalse((self.story_directory / "footnotes.json").exists())

    def test_rejected_story_does_not_create_sidecar(self):
        self.report["rejection"] = "too short"
        result = parser.gather_story_result(self.gatherer, 42, source=self.source)
        self.assertEqual(result.disposition, "skipped")
        self.assertFalse((self.story_directory / "footnotes.json").exists())
