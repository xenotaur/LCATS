"""Unittests for lcats.gatherers.gutenberg module."""

import os
import tempfile
from pathlib import Path
import unittest
from unittest import mock

import lcats.gatherers.gutenberg as gb

class FakeCache:
    """A fake cache object to simulate the behavior of the real cache."""

    def __init__(self):
        """A fake cache object to simulate the behavior of the real cache."""
        self.last_query_kwargs = None
        self.query_rows = []
        self.native_rows = []
        self.raise_on_native = False  # NEW: let tests simulate “not ready”

    def query(self, *, authors=None, titles=None, languages=None,
              subjects=None, bookshelves=None, downloadtype=None):
        """Simulate a filtered query; just record the args and return preset rows."""
        self.last_query_kwargs = dict(
            authors=authors, titles=titles, languages=languages,
            subjects=subjects, bookshelves=bookshelves, downloadtype=downloadtype
        )
        return list(self.query_rows)

    def native_query(self, sql):
        """Simulate native SQL query; raise if configured to do so."""
        if self.raise_on_native:
            raise RuntimeError("cache not initialized")
        return list(self.native_rows)


class GutenbergWrapperTests(unittest.TestCase):
    def setUp(self):
        # isolate text cache per test
        self.tmpdir = tempfile.TemporaryDirectory()
        self._old_cache_env = os.environ.get("LCATS_GUTENBERG_TEXT_CACHE")
        os.environ["LCATS_GUTENBERG_TEXT_CACHE"] = self.tmpdir.name
        # if your wrapper exposes _TEXT_CACHE, sync it; safe if it doesn't exist:
        if hasattr(gb, "_TEXT_CACHE"):
            gb._GUTENBERG_TEXTS = Path(self.tmpdir.name)
            gb._GUTENBERG_TEXTS.mkdir(parents=True, exist_ok=True)

        # disable auto-create by default
        self._old_auto = os.environ.get("GUTENBERGPY_AUTO_CREATE")
        os.environ["GUTENBERGPY_AUTO_CREATE"] = "0"
        if hasattr(gb, "_AUTO_CREATE"):
            gb._AUTO_CREATE = False
        if hasattr(gb, "_CACHE"):
            gb._CACHE = None

        # --- PATCH WHERE USED: on gb.gc.GutenbergCache ---
        self.p_create = mock.patch.object(
            gb.gc.GutenbergCache, "create", autospec=True
        )
        self.p_get_cache = mock.patch.object(
            gb.gc.GutenbergCache, "get_cache", autospec=True
        )
        self.m_create = self.p_create.start()
        self.m_get_cache = self.p_get_cache.start()

        # fake cache handle returned by get_cache()
        self.fake_cache = FakeCache()
        self.m_get_cache.return_value = self.fake_cache

        # --- backend text functions now live under gb.textget ---
        self.p_get_text = mock.patch.object(
            gb.textget, "get_text_by_id", autospec=True
        )
        self.p_strip = mock.patch.object(
            gb.textget, "strip_headers", autospec=True
        )
        self.m_get_text = self.p_get_text.start()
        self.m_strip = self.p_strip.start()

    def tearDown(self):
        self.p_strip.stop()
        self.p_get_text.stop()
        self.p_get_cache.stop()
        self.p_create.stop()

        if hasattr(gb, "_CACHE"):
            gb._CACHE = None
        if hasattr(gb, "_AUTO_CREATE"):
            gb._AUTO_CREATE = False

        # restore env
        if self._old_auto is None:
            os.environ.pop("GUTENBERGPY_AUTO_CREATE", None)
        else:
            os.environ["GUTENBERGPY_AUTO_CREATE"] = self._old_auto

        if self._old_cache_env is None:
            os.environ.pop("LCATS_GUTENBERG_TEXT_CACHE", None)
        else:
            os.environ["LCATS_GUTENBERG_TEXT_CACHE"] = self._old_cache_env

        self.tmpdir.cleanup()


    def test_load_etext_calls_backend_and_returns_bytes(self):
        # Ensure cache file doesn't exist so backend path is taken
        bid = 2701
        (gb._GUTENBERG_TEXTS / f"{bid}.txt").unlink(missing_ok=True)
        self.m_get_text.return_value = b"Hello"

        out = gb.load_etext(bid)

        self.m_get_text.assert_called_once_with(bid)
        self.assertEqual(out, b"Hello")
        # and it should now be cached on disk
        self.assertTrue((gb._GUTENBERG_TEXTS / f"{bid}.txt").exists())

    def test_get_etexts_passes_filters_and_returns_ids(self):
        # Make cache look "not ready" so _ensure_cache() triggers create()
        gb._AUTO_CREATE = True
        self.fake_cache.raise_on_native = True  # native_query will raise → not ready

        # rows returned by .query
        self.fake_cache.query_rows = [
            {"gutenberg_book_id": "2701"},
            {"book_id": "42"},
            {"id": "3"},
            {"id": "NaN"},
            {"gutenberg_book_id": 2701},  # dup
        ]

        result = gb.get_etexts(
            authors="Mark Twain",
            titles=["Moby Dick"],
            languages=("en",),
            subjects=None,
            bookshelves={"Classics"},
            downloadtype=None,
        )

        self.assertEqual(result, {2701, 42, 3})
        k = self.fake_cache.last_query_kwargs
        self.assertEqual(k["authors"], ["Mark Twain"])
        self.assertEqual(k["titles"], ["Moby Dick"])
        self.assertEqual(k["languages"], ["en"])
        self.assertIsNone(k["subjects"])
        self.assertEqual(k["bookshelves"], ["Classics"])
        self.assertEqual(k["downloadtype"], "text")

        # NOW create() should have been called because cache looked missing
        self.m_create.assert_called()

    def test_get_metadata_header_parse_when_cache_empty(self):
        # No cache results → header-parse fallback path
        self.fake_cache.native_rows = []
        header = (
            b"Title: Moby-Dick; or, The Whale\n"
            b"Author: Herman Melville\n"
            b"Language: en\n"
            b"Subject: Whaling -- Fiction\n"
            b"\n*** START OF THE PROJECT GUTENBERG EBOOK MOBY-DICK ***\n"
            b"Call me Ishmael.\n"
        )

        # Patch load_etext since _header_lines() now uses it
        with mock.patch.object(gb, "load_etext", return_value=header) as m_load:
            got_title  = gb.get_metadata("title", 2701)
            got_author = gb.get_metadata("author", 2701)
            got_lang   = gb.get_metadata("language", 2701)
            got_subj   = gb.get_metadata("subject", 2701)

        self.assertEqual(got_title,  {"Moby-Dick; or, The Whale"})
        self.assertEqual(got_author, {"Herman Melville"})
        self.assertEqual(got_lang,   {"en"})
        self.assertEqual(got_subj,   {"Whaling -- Fiction"})
