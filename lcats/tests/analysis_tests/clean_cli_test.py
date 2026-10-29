"""Unit tests for lcats.analysis.corpus.clean_cli."""

import pathlib
import tempfile
import unittest
import unittest.mock

from lcats.analysis.corpus import clean_cli
from lcats.utils import capture


class CleanCliTest(unittest.TestCase):
    """Tests for the clean CLI's argument handling and clearing behavior."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_dir = pathlib.Path(self._tmp.name)

        self.data_root = self.tmp_dir / "data"
        self.cache_root = self.tmp_dir / "cache"
        self.texts_dir = self.cache_root / "texts"
        self.tmp_unpack = self.cache_root / "tmp"
        self.index_db = self.cache_root / "gutenbergindex.db"
        self.rdf_archive = self.cache_root / "rdf-files.tar.bz2"

        self.data_root.mkdir()
        (self.data_root / "sherlock").mkdir()
        (self.data_root / "sherlock" / "story.json").touch()
        (self.data_root / "mass_quantities").mkdir()
        (self.data_root / "mass_quantities" / "story.json").touch()

        (self.cache_root / "resources").mkdir(parents=True)
        (self.cache_root / "resources" / "page.html").touch()

        self.texts_dir.mkdir()
        (self.texts_dir / "30086.txt").touch()
        self.tmp_unpack.mkdir()
        (self.tmp_unpack / "leftover.tmp").touch()
        self.index_db.touch()
        self.rdf_archive.touch()

        self._p_env = unittest.mock.patch.dict(
            "os.environ",
            {
                "LCATS_DATA_DIR": str(self.data_root),
                "LCATS_CACHE_DIR": str(self.cache_root),
            },
        )
        self._p_env.start()
        self.addCleanup(self._p_env.stop)
        self.addCleanup(self._tmp.cleanup)
        self.managed = self.cache_root / "gettenberg"
        (self.managed / "generations" / "fixture").mkdir(parents=True)
        (self.managed / "generations" / "fixture" / "catalog.sqlite").touch()
        (self.managed / "active.json").write_text("{}")

    def test_no_args_clears_all_of_data_and_cache(self):
        with capture.suppress_output():
            exit_code = clean_cli.run([])

        self.assertEqual(0, exit_code)
        self.assertEqual(list(self.data_root.iterdir()), [])
        self.assertEqual(list((self.cache_root / "resources").iterdir()), [])
        self.assertEqual(list(self.texts_dir.iterdir()), [])
        self.assertEqual(list(self.tmp_unpack.iterdir()), [])
        self.assertFalse(self.index_db.exists())
        self.assertFalse(self.rdf_archive.exists())
        self.assertEqual(list(self.managed.iterdir()), [])
        # The directories themselves survive -- only contents are cleared.
        self.assertTrue(self.data_root.is_dir())
        self.assertTrue(self.cache_root.is_dir())

    def test_specific_gatherer_scopes_to_that_directory_only(self):
        with capture.suppress_output():
            exit_code = clean_cli.run(["sherlock"])

        self.assertEqual(0, exit_code)
        self.assertFalse((self.data_root / "sherlock").exists())
        self.assertTrue((self.data_root / "mass_quantities").exists())
        # Cache is untouched when specific gatherer names are given.
        self.assertTrue((self.cache_root / "resources" / "page.html").exists())

    def test_unknown_gatherer_name_warns_and_continues(self):
        with capture.capture_output() as captured:
            exit_code = clean_cli.run(["not_a_real_gatherer"])

        self.assertEqual(0, exit_code)
        self.assertIn(
            "Unknown gatherer: not_a_real_gatherer", captured.stderr.getvalue()
        )

    def test_data_only_leaves_cache_untouched(self):
        with capture.suppress_output():
            exit_code = clean_cli.run(["--data-only"])

        self.assertEqual(0, exit_code)
        self.assertEqual(list(self.data_root.iterdir()), [])
        self.assertTrue((self.cache_root / "resources" / "page.html").exists())
        self.assertTrue((self.texts_dir / "30086.txt").exists())

    def test_cache_only_leaves_data_untouched(self):
        with capture.suppress_output():
            exit_code = clean_cli.run(["--cache-only"])

        self.assertEqual(0, exit_code)
        self.assertTrue((self.data_root / "sherlock" / "story.json").exists())
        self.assertEqual(list((self.cache_root / "resources").iterdir()), [])
        self.assertEqual(list(self.texts_dir.iterdir()), [])
        self.assertFalse(self.index_db.exists())
        self.assertFalse(self.rdf_archive.exists())
        self.assertEqual(list(self.managed.iterdir()), [])

    def test_nested_links_are_unlinked_without_deleting_external_data(self):
        target = self.tmp_dir / "external"
        target.mkdir()
        preserved = target / "source.txt"
        preserved.write_text("immutable original")
        (self.managed / "external-link").symlink_to(target)
        with capture.suppress_output():
            self.assertEqual(clean_cli.run(["--cache-only"]), 0)
        self.assertEqual(preserved.read_text(), "immutable original")
        self.assertFalse((self.managed / "external-link").is_symlink())

    def test_symlinked_managed_root_survives_and_legacy_file_links_do_not_follow(self):
        target = self.tmp_dir / "managed-target"
        self.managed.rename(target)
        self.managed.symlink_to(target)
        external = self.tmp_dir / "original.db"
        external.write_bytes(b"original")
        self.index_db.unlink()
        self.index_db.symlink_to(external)
        with capture.suppress_output():
            self.assertEqual(clean_cli.run(["--cache-only"]), 0)
        self.assertTrue(self.managed.is_symlink())
        self.assertEqual(list(target.iterdir()), [])
        self.assertEqual(external.read_bytes(), b"original")
        self.assertFalse(self.index_db.is_symlink())

    def test_data_only_and_cache_only_are_mutually_exclusive(self):
        with capture.capture_output() as captured:
            exit_code = clean_cli.run(["--data-only", "--cache-only"])

        self.assertEqual(2, exit_code)
        self.assertIn("mutually exclusive", captured.stderr.getvalue())

    def test_gatherer_names_invalid_with_cache_only(self):
        with capture.capture_output() as captured:
            exit_code = clean_cli.run(["sherlock", "--cache-only"])

        self.assertEqual(2, exit_code)
        self.assertIn("not valid with --cache-only", captured.stderr.getvalue())

    def test_preserves_symlinked_data_and_cache(self):
        real_data_target = self.tmp_dir / "real_data_target"
        real_data_target.mkdir()
        (real_data_target / "sherlock").mkdir()
        (real_data_target / "sherlock" / "story.json").touch()
        data_link = self.tmp_dir / "data_link"
        data_link.symlink_to(real_data_target)

        with (
            unittest.mock.patch.dict("os.environ", {"LCATS_DATA_DIR": str(data_link)}),
            capture.suppress_output(),
        ):
            exit_code = clean_cli.run(["--data-only"])

        self.assertEqual(0, exit_code)
        self.assertTrue(data_link.is_symlink())
        self.assertEqual(list(real_data_target.iterdir()), [])

    def test_self_heals_dangling_data_symlink(self):
        """A dangling data/ is healed, not silently ignored (PR #131 review)."""
        real_data_target = self.tmp_dir / "healed_data_target"
        data_link = self.tmp_dir / "dangling_data"
        data_link.symlink_to(real_data_target)  # target does not exist yet
        self.assertFalse(data_link.exists())  # confirm genuinely dangling

        with (
            unittest.mock.patch.dict("os.environ", {"LCATS_DATA_DIR": str(data_link)}),
            capture.suppress_output(),
        ):
            exit_code = clean_cli.run(["--data-only"])

        self.assertEqual(0, exit_code)
        self.assertTrue(data_link.is_symlink(), "the symlink itself must survive")
        self.assertTrue(real_data_target.is_dir(), "the target must be healed")

    def test_self_heals_dangling_cache_resources_ancestor(self):
        """A dangling cache/ is healed for cache/resources too (PR #131 review)."""
        real_cache_target = self.tmp_dir / "healed_cache_target"
        cache_link = self.tmp_dir / "dangling_cache"
        cache_link.symlink_to(real_cache_target)
        self.assertFalse(cache_link.exists())

        with (
            unittest.mock.patch.dict(
                "os.environ", {"LCATS_CACHE_DIR": str(cache_link)}
            ),
            capture.suppress_output(),
        ):
            exit_code = clean_cli.run(["--cache-only"])

        self.assertEqual(0, exit_code)
        self.assertTrue(cache_link.is_symlink())
        self.assertTrue((real_cache_target / "resources").is_dir())


if __name__ == "__main__":
    unittest.main()
