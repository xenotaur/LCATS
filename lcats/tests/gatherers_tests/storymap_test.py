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
from unittest.mock import patch
from lcats.gatherers.mass_quantities import storymap


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


class TestStorymap(LCATSTestCase):
    def test_storymap_target_directory(self):
        modules = SimpleNamespace(storymap=storymap)

        self.assertEqual(modules.storymap.TARGET_DIRECTORY, "mass_quantities")

    def test_storymap_ids_are_sorted_positive_integers(self):
        modules = SimpleNamespace(storymap=storymap)
        ids = modules.storymap.SINGLE_STORIES

        self.assertTrue(ids)

        self.assertEqual(ids, sorted(ids))

        self.assertTrue(all((isinstance(story_id, int) for story_id in ids)))

        self.assertTrue(all((story_id > 0 for story_id in ids)))

    def test_storymap_exclusion_and_aliases(self):
        modules = SimpleNamespace(storymap=storymap)

        self.assertIn(64092, modules.storymap.STORIES_TO_EXCLUDE)

        self.assertIn("Flehr, Paul", modules.storymap.PEN_NAMES["Pohl, Frederik"])

        self.assertIn("epistolary", modules.storymap.EXCLUDED_SUBJECTS)

    def test_storymap_title_exclusions(self):
        modules = SimpleNamespace(storymap=storymap)

        self.assertIn("volume", modules.storymap.EXCLUDED_TITLE_PART_WORDS)

        self.assertIn("poem", modules.storymap.EXCLUDED_TITLE_WORDS)

        self.assertIn("THE END", modules.storymap.TITLE_EXCEPTIONS)


if __name__ == "__main__":
    unittest.main()
