"""Review evidence stays immutable and separate from accepted corpus outputs."""

import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock

from lcats.gatherers import review_store


class ReviewStoreTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = pathlib.Path(temp.name)
        self.data = self.root / "data"
        self.directory = self.root / "reviews"
        patch = mock.patch.dict(
            os.environ,
            LCATS_DATA_DIR=str(self.data),
            LCATS_CORPORA_DIR=str(self.root / "corpora"),
        )
        patch.start()
        self.addCleanup(patch.stop)
        self.report = {
            "gutenberg_id": 1,
            "status": "needs_review",
            "body": "preserved candidate",
            "provenance": {"identity": "first"},
        }

    def save(self, report=None):
        return pathlib.Path(
            review_store.save(
                self.report if report is None else report,
                directory=self.directory,
                data_root=self.data,
            )
        )

    def test_repeated_evidence_reuses_equal_json_without_story_output(self):
        path = self.save()
        original = path.read_bytes()
        self.assertEqual(self.save(), path)
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(json.loads(original)["report"], self.report)
        self.assertTrue(path.name.endswith(".candidate.json"))
        self.assertEqual(list(self.root.rglob("story.json")), [])
        self.assertFalse(self.data.exists())

    def test_changed_source_or_findings_keep_distinct_evidence(self):
        original = self.save()
        new = self.save({**self.report, "provenance": {"identity": "second"}})
        self.assertNotEqual(new, original)
        self.assertEqual(len(list(self.directory.glob("*.candidate.json"))), 2)

    def test_corrupt_or_conflicting_existing_file_fails_without_overwrite(self):
        path = self.save()
        for text in ("broken json", '{"wrong":"report"}'):
            path.write_text(text, encoding="utf-8")
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.save()
            self.assertEqual(path.read_text(), text)

    def test_symlink_output_leaf_is_refused(self):
        path = self.save()
        path.unlink()
        target = self.root / "untouched"
        target.write_text("source", encoding="utf-8")
        path.symlink_to(target)
        with self.assertRaises(OSError):
            self.save()
        self.assertEqual(target.read_text(), "source")

    def test_ready_or_excluded_reports_are_not_queued(self):
        for status in ("ready", "ineligible", "unknown"):
            with self.subTest(status=status), self.assertRaises(ValueError):
                self.save({**self.report, "status": status})
        self.assertFalse(self.directory.exists())
