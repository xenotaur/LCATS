"""Behavior checks for offline release-qualification experiment evidence."""

import dataclasses
import gzip
import importlib.util
import json
import pathlib
import tempfile
import types
import unittest
from unittest import mock

from lcats.gettenberg import rdf
from tests.gettenberg_tests import catalog_test

SCRIPTS = (
    pathlib.Path(__file__).resolve().parents[3]
    / "experiments/10_gettenberg_qualification/scripts"
)


def load(name):
    """Load a durable experiment without invoking its CLI or historical imports."""
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class QualificationEvidenceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = pathlib.Path(temporary.name)

    def test_corpus_triage_never_labels_changed_or_refused_text_equal(self):
        module = load("summarize_corpus")
        row = {
            "status": "compared",
            "body_equal": False,
            "old_body_characters": 100,
            "first_difference": {
                "offset": 100,
                "after": "x" * 60 + "\nEnd of Gutenberg",
            },
        }
        self.assertEqual(module.classify(row), "appended_end_notice")
        row["first_difference"]["offset"] = 0
        self.assertEqual(module.classify(row), "earlier_body_difference")
        self.assertEqual(
            module.classify({"status": "cleanup_refused"}), "cleanup_refused"
        )
        self.assertEqual(
            module.classify({"status": "missing_cached_text"}), "missing_cached_text"
        )
        self.assertEqual(
            module.classify(
                {
                    "status": "compared",
                    "body_equal": True,
                    "retained_corpus_matches": False,
                }
            ),
            "retained_corpus_only",
        )

    def test_snapshot_checks_every_field_and_source_not_only_id(self):
        module = load("qualify_snapshot")
        raw = catalog_test.record(84, "Fixture")
        record = rdf.parse_record(raw, source_name="84.rdf")
        reader = types.SimpleNamespace(get=lambda _id: record)
        self.assertEqual(module.check_record(raw, "84.rdf", reader), record)
        changed = dataclasses.replace(
            record, ebook=dataclasses.replace(record.ebook, downloads=7)
        )
        with self.assertRaisesRegex(ValueError, "typed record mismatch"):
            module.check_record(
                raw, "84.rdf", types.SimpleNamespace(get=lambda _id: changed)
            )
        changed = dataclasses.replace(
            record, source=dataclasses.replace(record.source, source_name="other.rdf")
        )
        with self.assertRaisesRegex(ValueError, "source/diagnostic mismatch"):
            module.check_record(
                raw, "84.rdf", types.SimpleNamespace(get=lambda _id: changed)
            )

    def test_cached_text_is_bounded_utf8_and_missing_stays_missing(self):
        module = load("qualify_cached_corpus")
        self.assertIsNone(module.cached_text(self.root, 84))
        target = self.root / "84.txt.gz"
        target.write_bytes(gzip.compress("A café\r\n".encode()))
        text, compressed, decoded = module.cached_text(self.root, 84)
        self.assertEqual(text, "A café\r\n")
        self.assertEqual(compressed, module.digest(target.read_bytes()))
        self.assertEqual(decoded, module.digest(text))
        target.write_bytes(gzip.compress(b"x" * 1000))
        with mock.patch.object(module, "MAX_BYTES", 100):
            with self.assertRaisesRegex(ValueError, "expanded text exceeds"):
                module.cached_text(self.root, 84)
        target.write_bytes(gzip.compress(b"\xff"))
        with self.assertRaises(UnicodeDecodeError):
            module.cached_text(self.root, 84)

    def test_missing_cache_and_cleanup_refusal_are_not_comparison_passes(self):
        module = load("qualify_cached_corpus")
        path = self.root / "story.json"
        path.write_text(
            json.dumps({"metadata": {"url": "https://www.gutenberg.org/ebooks/84"}})
        )
        # Missing bytes return before metadata access; never try another source.
        missing = module.compare(path, self.root, None, None)
        self.assertEqual(missing["status"], "missing_cached_text")
        metadata = types.SimpleNamespace(
            titles=("Story",),
            authors=("Author",),
            aliases=(),
            languages=("en",),
            subjects=("Short stories",),
        )
        source = types.SimpleNamespace(metadata=lambda _id: metadata)
        (self.root / "84.txt.gz").write_bytes(
            gzip.compress(b"*** START OF THE PROJECT GUTENBERG EBOOK STORY ***\nBody")
        )
        with mock.patch.object(module, "extract", return_value="Body"):
            refused = module.compare(path, self.root, source, lambda data: data)
        self.assertEqual(refused["status"], "cleanup_refused")
        self.assertIsNone(refused["body_equal"])
        self.assertIn("incomplete_pair", refused["cleanup_diagnostics"])


if __name__ == "__main__":
    unittest.main()
