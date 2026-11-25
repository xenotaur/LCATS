"""Behavioral tests for publication-year sidecars during story gathering."""

import json
import pathlib
import tempfile
import types
import unittest
from unittest import mock

from lcats.gatherers.mass_quantities import parser


class PublicationYearWiringTest(unittest.TestCase):
    """Ensure year.json is produced only after a new successful publication."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.metadata = types.SimpleNamespace(
            titles=["A Story"],
            authors=["Writer, A."],
        )
        self.source = types.SimpleNamespace(
            metadata=mock.Mock(return_value=self.metadata),
            read=mock.Mock(
                return_value=types.SimpleNamespace(
                    cleaned=types.SimpleNamespace(
                        text="First published in May 1952\nA story."
                    ),
                )
            ),
        )
        self.target = self.root / "a_story__writer" / "story.json"
        self.gatherer = types.SimpleNamespace(
            path=str(self.root),
            ensure=mock.Mock(side_effect=self._ensure),
        )
        self.report = {
            "rejection": None,
            "body": "Narrative text " * 50,
            "confidence": "high",
            "raw_opening": ["A story"],
            "provenance": {"source_uri": "https://example.org/story"},
        }

        patches = [
            mock.patch.object(parser, "_metadata_rejection", return_value=None),
            mock.patch.object(
                parser.names,
                "title_and_author_to_filename",
                return_value="a_story__writer.txt",
                create=True,
            ),
            mock.patch.object(
                parser.registry, "check_story", return_value=False, create=True
            ),
            mock.patch.object(parser.registry, "add_story", create=True),
            mock.patch.object(
                parser.story_output, "existing", return_value=False, create=True
            ),
            mock.patch.object(
                parser.story_output, "publish", side_effect=self._publish, create=True
            ),
            mock.patch.object(parser, "_inspect_metadata", return_value=self.report),
            mock.patch.object(
                parser.extraction_records,
                "load_override",
                return_value=None,
                create=True,
            ),
            mock.patch.object(
                parser.extraction_records,
                "extraction_record",
                return_value={"status": "ok"},
                create=True,
            ),
            mock.patch.object(
                parser.extraction_records, "save_extraction_record", create=True
            ),
            mock.patch.object(
                parser.normalization, "normalize_story_dict", create=True
            ),
        ]
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)

    def _ensure(self, slug):
        """Create the expected publication directory for a fake gatherer."""
        directory = self.root / slug
        directory.mkdir(parents=True, exist_ok=True)
        return (directory, str(directory / "story.json"))

    def _publish(self, file_path, data):
        """Simulate a successful story publication."""
        pathlib.Path(file_path).write_text(json.dumps(data), encoding="utf-8")
        return True

    def test_new_publication_creates_year_json(self):
        """Write the publication year alongside a newly published story."""
        result = parser.gather_story_result(self.gatherer, 42, source=self.source)
        self.assertEqual(result.disposition, "written")
        destination = pathlib.Path(result.path).parent / "year.json"
        self.assertTrue(destination.exists())
        self.assertEqual(
            json.loads(destination.read_text(encoding="utf-8")),
            {
                "gutenberg_id": 42,
                "title": ["A Story"],
                "authors": ["Writer, A."],
                "deterministic_month": "May",
                "deterministic_year": "1952",
            },
        )

    def test_existing_story_does_not_replace_year_json(self):
        """Reusing an existing output must not modify an existing sidecar."""
        directory = self.root / "a_story__writer"
        directory.mkdir(parents=True)
        existing = directory / "story.json"
        existing.write_text("old story", encoding="utf-8")
        year_file = directory / "year.json"
        year_file.write_text('{"original": true}', encoding="utf-8")
        with mock.patch.object(parser.story_output, "existing", return_value=True):
            result = parser.gather_story_result(self.gatherer, 42, source=self.source)
        self.assertEqual(result.disposition, "reused")
        self.assertEqual(year_file.read_text(encoding="utf-8"), '{"original": true}')
        self.source.read.assert_not_called()

    def test_duplicate_registry_does_not_create_year_json(self):
        """Skip duplicate stories without any publication-year sidecar."""
        with mock.patch.object(parser.registry, "check_story", return_value=True):
            result = parser.gather_story_result(self.gatherer, 42, source=self.source)
        self.assertEqual(result.disposition, "skipped")
        self.assertEqual(list(self.root.rglob("year.json")), [])
        self.source.read.assert_not_called()

    def test_rejected_extraction_does_not_create_year_json(self):
        """Skip year output when extraction rejects an otherwise valid story."""
        with mock.patch.object(
            parser, "_inspect_metadata", return_value={"rejection": "too short"}
        ):
            result = parser.gather_story_result(self.gatherer, 42, source=self.source)
        self.assertEqual(result.disposition, "skipped")
        self.assertEqual(list(self.root.rglob("year.json")), [])

    def test_failed_publish_does_not_create_year_json(self):
        """An unsuccessful publish cannot produce or overwrite year.json."""
        year_file = self.root / "a_story__writer" / "year.json"
        with mock.patch.object(parser.story_output, "publish", return_value=False):
            result = parser.gather_story_result(self.gatherer, 42, source=self.source)
        self.assertEqual(result.disposition, "reused")
        self.assertFalse(year_file.exists())
        self.source.read.assert_not_called()

    def test_unsuccessful_publish_preserves_existing_year_json(self):
        """A false publication result never overwrites an existing year file."""
        directory = self.root / "a_story__writer"
        directory.mkdir(parents=True)
        year_file = directory / "year.json"
        year_file.write_text('{"previous": "unchanged"}', encoding="utf-8")
        with mock.patch.object(parser.story_output, "publish", return_value=False):
            result = parser.gather_story_result(self.gatherer, 42, source=self.source)
        self.assertEqual(result.disposition, "reused")
        self.assertEqual(
            year_file.read_text(encoding="utf-8"),
            '{"previous": "unchanged"}',
        )

    def test_success_without_known_year_writes_null_year(self):
        """A successful story is recorded even when publication year is unknown."""
        self.source.read.return_value.cleaned.text = "Narrative without a date."
        result = parser.gather_story_result(self.gatherer, 42, source=self.source)
        year_file = pathlib.Path(result.path).parent / "year.json"
        record = json.loads(year_file.read_text(encoding="utf-8"))
        self.assertIsNone(record["deterministic_month"])
        self.assertIsNone(record["deterministic_year"])

    def test_publish_exception_does_not_create_year_json(self):
        """Publication exceptions must not leave a publication-year sidecar."""
        with mock.patch.object(
            parser.story_output, "publish", side_effect=OSError("write failed")
        ):
            with self.assertRaises(OSError):
                parser.gather_story_result(self.gatherer, 42, source=self.source)
        self.assertEqual(list(self.root.rglob("year.json")), [])


if __name__ == "__main__":
    unittest.main()
