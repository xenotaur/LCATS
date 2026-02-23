"""Unit tests for lcats.gettenberg.cache functions and classes."""

import pathlib
import sqlite3
import tempfile
import time
import unittest
from unittest import mock

from lcats.gettenberg import cache


class GettenbergCacheTests(unittest.TestCase):
    """Unit tests for lcats.gettenberg.cache."""

    def setUp(self):
        """Set up a temporary cache area and patch settings to point there."""
        self.td = tempfile.TemporaryDirectory()
        self.tmp_dir = pathlib.Path(self.td.name)

        # Point GutenbergCacheSettings at a temp DB path (no actual open).
        self.db_path = self.tmp_dir / "gutenbergindex.db"
        self.rdf_path = self.tmp_dir / "rdf-files.tar.bz2"
        self.texts_dir = self.tmp_dir / "texts"
        self.tmp_unpack = self.tmp_dir / "tmp"

        # Patch the settings constants the module reads.
        self._p_cache_filename = mock.patch.object(
            cache.gc.GutenbergCacheSettings, "CACHE_FILENAME", str(self.db_path)
        )
        self._p_archive_name = mock.patch.object(
            cache.gc.GutenbergCacheSettings,
            "CACHE_RDF_ARCHIVE_NAME",
            str(self.rdf_path),
        )
        self._p_texts_folder = mock.patch.object(
            cache.gc.GutenbergCacheSettings,
            "TEXT_FILES_CACHE_FOLDER",
            str(self.texts_dir),
        )
        self._p_unpack_dir = mock.patch.object(
            cache.gc.GutenbergCacheSettings,
            "CACHE_RDF_UNPACK_DIRECTORY",
            str(self.tmp_unpack),
        )

        self._p_cache_filename.start()
        self._p_archive_name.start()
        self._p_texts_folder.start()
        self._p_unpack_dir.start()

        # Keep original flags to restore later.
        self.orig_auto = cache.GUTENBERG_CACHE_AUTO_CREATE
        self.orig_skip = cache.GUTENBERG_CACHE_SKIP_MODE
        cache.GUTENBERG_CACHE_AUTO_CREATE = True
        cache.GUTENBERG_CACHE_SKIP_MODE = False

    def tearDown(self):
        """Restore patches and cleanup."""
        cache.GUTENBERG_CACHE_AUTO_CREATE = self.orig_auto
        cache.GUTENBERG_CACHE_SKIP_MODE = self.orig_skip

        self._p_unpack_dir.stop()
        self._p_texts_folder.stop()
        self._p_archive_name.stop()
        self._p_cache_filename.stop()

        self.td.cleanup()

    # ----------- gutenberg_cache_path -----------

    def test_gutenberg_cache_path_uses_settings(self):
        """gutenberg_cache_path returns the Path based on GutenbergCacheSettings.CACHE_FILENAME."""
        p = cache.gutenberg_cache_path()
        self.assertIsInstance(p, pathlib.Path)
        self.assertEqual(p, self.db_path)

    # ----------- gutenberg_cache_ready -----------

    def test_gutenberg_cache_ready_false_when_missing_or_zero_byte(self):
        """gutenberg_cache_ready is False for missing or 0-byte files."""
        self.assertFalse(cache.gutenberg_cache_ready(self.db_path))
        self.db_path.touch()  # create zero-byte file
        self.assertFalse(cache.gutenberg_cache_ready(self.db_path))

    def test_gutenberg_cache_ready_true_with_subjects_table(self):
        """gutenberg_cache_ready is True when 'books' and 'subjects' tables exist."""
        with sqlite3.connect(self.db_path) as con:
            con.execute(
                "CREATE TABLE books (id INTEGER PRIMARY KEY, gutenbergbookid INTEGER)"
            )
            con.execute("CREATE TABLE subjects (id INTEGER PRIMARY KEY, name TEXT)")
        self.assertTrue(cache.gutenberg_cache_ready(self.db_path))

    def test_gutenberg_cache_ready_true_with_book_subjects_join(self):
        """gutenberg_cache_ready is True when 'books' + 'book_subjects' exist (join schema)."""
        with sqlite3.connect(self.db_path) as con:
            con.execute(
                "CREATE TABLE books (id INTEGER PRIMARY KEY, gutenbergbookid INTEGER)"
            )
            con.execute(
                "CREATE TABLE book_subjects (bookid INTEGER, subjectid INTEGER)"
            )
        self.assertTrue(cache.gutenberg_cache_ready(self.db_path))

    def test_gutenberg_cache_ready_false_if_books_missing(self):
        """gutenberg_cache_ready is False when 'books' table is missing."""
        with sqlite3.connect(self.db_path) as con:
            con.execute("CREATE TABLE subjects (id INTEGER PRIMARY KEY, name TEXT)")
        self.assertFalse(cache.gutenberg_cache_ready(self.db_path))

    def test_gutenberg_cache_ready_false_on_sqlite_error(self):
        """gutenberg_cache_ready returns False when the file is not a valid SQLite DB."""
        # Write garbage bytes so the file is non-empty but unparseable by SQLite.
        self.db_path.write_bytes(b"this is not a SQLite database file\x00\x01\x02")
        self.assertFalse(cache.gutenberg_cache_ready(self.db_path))

    # ----------- ensure_gutenberg_cache -----------

    def test_ensure_gutenberg_cache_calls_create_when_not_ready(self):
        """ensure_gutenberg_cache calls GutenbergCache.create when ready=False then returns handle."""
        with mock.patch.object(
            cache, "gutenberg_cache_ready", side_effect=[False, True]
        ) as p_ready, mock.patch.object(
            cache.gc.GutenbergCache, "create", autospec=True
        ) as p_create, mock.patch.object(
            cache.gc.GutenbergCache, "get_cache", autospec=True
        ) as p_get:
            fake_handle = object()
            p_get.return_value = fake_handle

            handle = cache.ensure_gutenberg_cache()

            self.assertIs(handle, fake_handle)
            # one pre-check + one post-create check
            self.assertEqual(p_ready.call_count, 2)
            p_create.assert_called_once()
            p_get.assert_called_once()

    def test_ensure_gutenberg_cache_skips_create_when_already_ready(self):
        """ensure_gutenberg_cache does not call create when DB is ready."""
        with mock.patch.object(
            cache, "gutenberg_cache_ready", return_value=True
        ) as p_ready, mock.patch.object(
            cache.gc.GutenbergCache, "create", autospec=True
        ) as p_create, mock.patch.object(
            cache.gc.GutenbergCache, "get_cache", autospec=True
        ) as p_get:
            fake_handle = object()
            p_get.return_value = fake_handle

            handle = cache.ensure_gutenberg_cache()

            self.assertIs(handle, fake_handle)
            p_ready.assert_called_once()
            p_create.assert_not_called()
            p_get.assert_called_once()

    def test_ensure_gutenberg_cache_raises_if_still_not_ready_after_create(self):
        """ensure_gutenberg_cache raises RuntimeError if cache remains unready after create."""
        with mock.patch.object(
            cache, "gutenberg_cache_ready", side_effect=[False, False]
        ) as p_ready, mock.patch.object(
            cache.gc.GutenbergCache, "create", autospec=True
        ) as p_create:
            with self.assertRaises(RuntimeError):
                cache.ensure_gutenberg_cache()
            self.assertEqual(p_ready.call_count, 2)
            p_create.assert_called_once()

    def test_ensure_gutenberg_cache_deletes_zero_byte_before_create(self):
        """ensure_gutenberg_cache unlinks zero-byte DB so create() won't early-exit."""
        # Create a zero-byte file at the expected DB path
        self.db_path.touch()
        self.assertTrue(self.db_path.exists())
        self.assertEqual(self.db_path.stat().st_size, 0)

        with mock.patch.object(
            cache, "gutenberg_cache_ready", side_effect=[False, True]
        ), mock.patch.object(cache.gc.GutenbergCache, "create", autospec=True):
            cache.ensure_gutenberg_cache()
        # Since we mocked create(), no one recreates the file; it should be gone.
        self.assertFalse(
            self.db_path.exists(), "Zero-byte DB should be unlinked before create()"
        )

    # ----------- download_raw_text -----------

    def test_download_raw_text_success_on_first_pattern(self):
        """download_raw_text returns bytes and sets User-Agent header."""
        # Mock urlopen to return an object with read()
        m_resp = mock.MagicMock()
        m_resp.read.return_value = b"abc"
        m_cm = mock.MagicMock()
        m_cm.__enter__.return_value = m_resp
        m_cm.__exit__.return_value = False

        with mock.patch.object(
            cache, "urlopen", return_value=m_cm
        ) as p_open, mock.patch.object(time, "sleep") as p_sleep:
            data = cache.download_raw_text(123)
            self.assertEqual(data, b"abc")

            # Check the URL
            req = p_open.call_args[0][0]
            self.assertIn("/123/pg123.txt", req.full_url)

            # Check the User-Agent header (case-insensitive)
            hdrs = {k.lower(): v for k, v in req.header_items()}
            self.assertEqual(hdrs.get("user-agent"), cache.USER_AGENT)
            p_sleep.assert_not_called()

    def test_download_raw_text_tries_multiple_patterns_then_succeeds(self):
        """download_raw_text tries subsequent URL patterns after failures."""

        # First call raises, second returns data
        def side_effect(_req, timeout=30):
            if side_effect.counter == 0:
                side_effect.counter += 1
                raise cache.URLError("nope")
            m_resp = mock.MagicMock()
            m_resp.read.return_value = b"OK"
            m_cm = mock.MagicMock()
            m_cm.__enter__.return_value = m_resp
            m_cm.__exit__.return_value = False
            return m_cm

        side_effect.counter = 0

        with mock.patch.object(
            cache, "urlopen", side_effect=side_effect
        ) as p_open, mock.patch.object(time, "sleep") as p_sleep:
            out = cache.download_raw_text(456)
            self.assertEqual(out, b"OK")
            self.assertGreaterEqual(p_open.call_count, 2)
            p_sleep.assert_called()  # backoff between patterns

    def test_download_raw_text_raises_after_all_patterns_fail(self):
        """download_raw_text raises RuntimeError if all URL patterns fail."""
        with mock.patch.object(
            cache, "urlopen", side_effect=cache.URLError("nope")
        ), mock.patch.object(time, "sleep"):
            with self.assertRaises(RuntimeError) as ctx:
                cache.download_raw_text(789)
            self.assertIn("Could not download book 789", str(ctx.exception))

    # ----------- get_metadata_cache / RefreshableMetadataCache -----------

    def test_get_metadata_cache_returns_refreshable_instance(self):
        """get_metadata_cache returns a RefreshableMetadataCache object with repr."""
        obj = cache.get_metadata_cache()
        self.assertIsInstance(obj, cache.RefreshableMetadataCache)
        self.assertIn("RefreshableMetadataCache", repr(obj))

    def test_refreshable_metadata_cache_rebuild_calls_create(self):
        """RefreshableMetadataCache.rebuild delegates to GutenbergCache.create()."""
        with mock.patch.object(
            cache.gc.GutenbergCache, "create", autospec=True
        ) as p_create:
            cache.RefreshableMetadataCache().rebuild()
            p_create.assert_called_once()


if __name__ == "__main__":
    unittest.main()
