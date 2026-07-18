"""Tests for lcats.utils.paths functions."""

import os
import pathlib
import tempfile
import unittest

from lcats.utils import paths


class MakedirsTest(unittest.TestCase):
    """Tests for the makedirs function."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_dir = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_creates_missing_path(self):
        """A path that doesn't exist at all is created normally."""
        target = self.tmp_dir / "fresh"

        paths.makedirs(target)

        self.assertTrue(target.is_dir())

    def test_creates_missing_nested_path(self):
        """Missing intermediate parents are created too, like os.makedirs."""
        target = self.tmp_dir / "a" / "b" / "c"

        paths.makedirs(target)

        self.assertTrue(target.is_dir())

    def test_noop_on_existing_directory(self):
        """An already-valid directory is left alone."""
        target = self.tmp_dir / "existing"
        target.mkdir()
        marker = target / "keepme.txt"
        marker.touch()

        paths.makedirs(target)

        self.assertTrue(marker.exists())

    def test_noop_on_existing_directory_via_live_symlink(self):
        """A live symlink to a real directory is left alone, not replaced."""
        real_target = self.tmp_dir / "real_target"
        real_target.mkdir()
        link = self.tmp_dir / "data"
        link.symlink_to(real_target)

        paths.makedirs(link)

        self.assertTrue(link.is_symlink())
        self.assertEqual(link.resolve(), real_target.resolve())

    def test_heals_dangling_symlink_leaf(self):
        """A dangling symlink as the target itself is healed, not destroyed."""
        real_target = self.tmp_dir / "real_target"
        link = self.tmp_dir / "data"
        link.symlink_to(real_target)  # real_target does not exist yet
        self.assertFalse(link.exists())  # confirm it's genuinely dangling

        paths.makedirs(link)

        self.assertTrue(link.is_symlink(), "the symlink itself must survive")
        self.assertTrue(real_target.is_dir())
        self.assertTrue(link.is_dir())

    def test_heals_dangling_symlink_ancestor(self):
        """A dangling symlink ancestor of a nested path is healed.

        This is the realistic failure mode for cache/resources,
        cache/texts, cache/tmp: cache/ itself is symlinked, not these
        subdirectories, and a dangling cache/ raises a different
        exception (FileNotFoundError) than a dangling leaf does
        (FileExistsError) from plain os.makedirs.
        """
        real_target = self.tmp_dir / "real_cache_target"
        link = self.tmp_dir / "cache"
        link.symlink_to(real_target)
        nested = link / "resources"

        paths.makedirs(nested)

        self.assertTrue(link.is_symlink(), "the symlink itself must survive")
        self.assertTrue(real_target.is_dir())
        self.assertTrue((real_target / "resources").is_dir())
        self.assertTrue(nested.is_dir())

    def test_raises_when_blocked_by_plain_file(self):
        """A plain file occupying the target path raises, not FileExistsError."""
        blocker = self.tmp_dir / "data"
        blocker.touch()

        with self.assertRaises(NotADirectoryError):
            paths.makedirs(blocker)

    def test_raises_when_symlink_resolves_to_a_file(self):
        """A symlink to an existing file is not dangling and not healable.

        This is a different case from a dangling symlink: is_dir() is
        False either way, but exists() distinguishes "nothing there yet"
        (heal it) from "something real, just not a directory" (refuse).
        """
        blocker_file = self.tmp_dir / "blocker_file.txt"
        blocker_file.touch()
        link = self.tmp_dir / "data"
        link.symlink_to(blocker_file)

        with self.assertRaises(NotADirectoryError):
            paths.makedirs(link)

    def test_raises_when_ancestor_blocked_by_plain_file(self):
        """A plain file occupying an ancestor of the target path raises."""
        blocker = self.tmp_dir / "cache"
        blocker.touch()
        nested = blocker / "resources"

        with self.assertRaises(NotADirectoryError):
            paths.makedirs(nested)

    def test_dangling_symlink_matches_documented_exception_shapes(self):
        """Confirms the exact os.makedirs failures this function fixes.

        Grounds the whole module: without paths.makedirs, a dangling
        leaf symlink raises FileExistsError, and a dangling ancestor
        symlink raises FileNotFoundError -- two different exceptions,
        not variants of one.
        """
        leaf_target = self.tmp_dir / "leaf_target"
        leaf_link = self.tmp_dir / "leaf"
        leaf_link.symlink_to(leaf_target)
        with self.assertRaises(FileExistsError):
            os.makedirs(leaf_link)

        ancestor_target = self.tmp_dir / "ancestor_target"
        ancestor_link = self.tmp_dir / "ancestor"
        ancestor_link.symlink_to(ancestor_target)
        with self.assertRaises(FileNotFoundError):
            os.makedirs(ancestor_link / "nested")


class ClearDirectoryContentsTest(unittest.TestCase):
    """Tests for the clear_directory_contents function."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_dir = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_removes_files_and_subdirectories(self):
        """Clears files, dotfiles, and nested directories."""
        real_dir = self.tmp_dir / "real_dir"
        real_dir.mkdir()
        (real_dir / "keepme.txt").touch()
        (real_dir / ".hidden_file").touch()
        nested = real_dir / "subdir" / "nested"
        nested.mkdir(parents=True)
        (nested / "deep.json").touch()

        paths.clear_directory_contents(real_dir)

        self.assertEqual(list(real_dir.iterdir()), [])

    def test_preserves_symlink_when_clearing_through_it(self):
        """The directory (or symlink) passed in is never removed itself."""
        real_target = self.tmp_dir / "real_target"
        real_target.mkdir()
        (real_target / "keepme.txt").touch()
        link = self.tmp_dir / "data"
        link.symlink_to(real_target)

        paths.clear_directory_contents(link)

        self.assertTrue(link.is_symlink())
        self.assertTrue(real_target.is_dir())
        self.assertEqual(list(real_target.iterdir()), [])

    def test_noop_on_missing_path(self):
        """A missing directory is a silent no-op, not an error."""
        missing = self.tmp_dir / "does_not_exist"

        paths.clear_directory_contents(missing)  # must not raise

        self.assertFalse(missing.exists())

    def test_does_not_follow_nested_symlink_into_its_target(self):
        """A symlink found inside the cleared directory is unlinked, not followed."""
        outside_target = self.tmp_dir / "outside_target"
        outside_target.mkdir()
        (outside_target / "precious.txt").touch()

        real_dir = self.tmp_dir / "real_dir"
        real_dir.mkdir()
        nested_link = real_dir / "nested_link"
        nested_link.symlink_to(outside_target)

        paths.clear_directory_contents(real_dir)

        self.assertEqual(list(real_dir.iterdir()), [])
        self.assertTrue((outside_target / "precious.txt").exists())


if __name__ == "__main__":
    unittest.main()
