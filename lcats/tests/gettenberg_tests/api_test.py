"""Unit tests for the compatibility API in lcats.gettenberg.api."""

import pathlib
import tempfile
import unittest
import unittest.mock as mock

from lcats.gettenberg import api
from lcats.gettenberg import cache
from gutenbergpy import textget


class GettenbergApiTests(unittest.TestCase):
    """Unit tests for the compatibility API in lcats.gettenberg.api."""

    def setUp(self):
        """Isolate the text cache path and common patches per test."""
        self._td = tempfile.TemporaryDirectory()
        self.tmp_dir = pathlib.Path(self._td.name)
        self.texts_dir = self.tmp_dir / "texts"
        self.texts_dir.mkdir(parents=True, exist_ok=True)

        # Patch where the module reads the text cache path
        self.p_texts = mock.patch.object(cache, "GUTENBERG_TEXTS", self.texts_dir)
        self.p_texts.start()

    def tearDown(self):
        """Undo patches & cleanup."""
        self.p_texts.stop()
        self._td.cleanup()

    # ---------------- load_etext ----------------

    def test_load_etext_reads_from_local_cache_when_present(self):
        """If the file exists in text cache, load_etext returns it and does not hit network."""
        bid = 2701
        fp = self.texts_dir / f"{bid}.txt"
        fp.write_bytes(b"CACHED")

        with mock.patch.object(textget, "get_text_by_id") as p_get, mock.patch.object(
            cache, "download_raw_text"
        ) as p_raw:
            out = api.load_etext(bid)
            self.assertEqual(out, b"CACHED")
            p_get.assert_not_called()
            p_raw.assert_not_called()

    def test_load_etext_fetches_via_gutenbergpy_then_caches_bytes(self):
        """When not cached, load_etext uses textget.get_text_by_id and caches the bytes."""
        bid = 100
        expect = b"BODY"
        fp = self.texts_dir / f"{bid}.txt"

        with mock.patch.object(
            textget, "get_text_by_id", return_value=expect
        ) as p_get, mock.patch.object(cache, "download_raw_text") as p_raw:
            out = api.load_etext(bid)
            self.assertEqual(out, expect)
            p_get.assert_called_once_with(bid)
            p_raw.assert_not_called()
            self.assertTrue(fp.exists())
            self.assertEqual(fp.read_bytes(), expect)

    def test_load_etext_fetches_via_gutenbergpy_when_str_then_encodes_and_caches(self):
        """If gutenbergpy returns str, load_etext re-encodes to UTF-8 bytes and caches."""
        bid = 101
        fp = self.texts_dir / f"{bid}.txt"

        with mock.patch.object(
            textget, "get_text_by_id", return_value="héllo"
        ) as p_get, mock.patch.object(cache, "download_raw_text") as p_raw:
            out = api.load_etext(bid)
            self.assertIsInstance(out, (bytes, bytearray))
            self.assertIn(b"h\xc3\xa9llo", out)  # UTF-8 encoding
            p_get.assert_called_once_with(bid)
            p_raw.assert_not_called()
            self.assertEqual(fp.read_bytes(), out)

    def test_load_etext_falls_back_to_raw_when_gutenbergpy_raises(self):
        """If gutenbergpy raises, load_etext uses download_raw_text and caches it."""
        bid = 102
        fp = self.texts_dir / f"{bid}.txt"

        with mock.patch.object(
            textget, "get_text_by_id", side_effect=RuntimeError("boom")
        ) as p_get, mock.patch.object(
            cache, "download_raw_text", return_value=b"RAW"
        ) as p_raw:
            out = api.load_etext(bid)
            self.assertEqual(out, b"RAW")
            p_get.assert_called_once_with(bid)
            p_raw.assert_called_once_with(bid)
            self.assertTrue(fp.exists())
            self.assertEqual(fp.read_bytes(), b"RAW")

    # ---------------- get_matching_rows ----------------

    def test_get_matching_rows_happy_path_and_query_args(self):
        """get_matching_rows calls ensure_gutenberg_cache().query with normalized lists."""

        class _FakeCache:
            def __init__(self):
                self.last_kwargs = None

            def query(self, **kwargs):
                self.last_kwargs = kwargs
                return [{"gutenbergbookid": 1}, {"gutenbergbookid": 2}]

        fake = _FakeCache()
        with mock.patch.object(
            cache, "ensure_gutenberg_cache", return_value=fake
        ) as p_ensure:
            rows = api.get_matching_rows(
                authors="Mark Twain",
                titles=["Moby Dick"],
                languages="en",
                subjects={"Short stories"},
                bookshelves=("Fiction",),
                downloadtype=None,
            )
            p_ensure.assert_called_once()
            self.assertIsInstance(rows, list)
            self.assertTrue(all(isinstance(r, dict) for r in rows))
            # verify normalization (strings_as_list applied)
            kw = fake.last_kwargs
            self.assertEqual(kw["authors"], ["Mark Twain"])
            self.assertEqual(kw["titles"], ["Moby Dick"])
            self.assertEqual(kw["languages"], ["en"])
            self.assertEqual(set(kw["subjects"]), {"Short stories"})
            self.assertEqual(set(kw["bookshelves"]), {"Fiction"})
            self.assertEqual(kw["downloadtype"], "text")

    def test_get_matching_rows_raises_typeerror_if_non_mapping_row(self):
        """Rows must be mapping; a tuple row triggers a TypeError with index info."""

        class _FakeCache:
            def query(self, **kwargs):
                return [("not-a-mapping",)]

        with mock.patch.object(
            cache, "ensure_gutenberg_cache", return_value=_FakeCache()
        ):
            with self.assertRaises(TypeError) as ctx:
                api.get_matching_rows(authors="A")
            self.assertIn("non-mapping row at index 0", str(ctx.exception))

    # ---------------- extract_book_id ----------------

    def test_extract_book_id_accepts_str_or_int(self):
        """extract_book_id returns int for both str and int values."""
        self.assertEqual(api.extract_book_id({"gutenbergbookid": "2701"}), 2701)
        self.assertEqual(api.extract_book_id({"gutenbergbookid": 2701}), 2701)

    def test_extract_book_id_raises_on_missing_key(self):
        """extract_book_id raises KeyError if key is missing."""
        with self.assertRaises(KeyError):
            api.extract_book_id({})

    def test_extract_book_id_raises_on_invalid_value(self):
        """extract_book_id raises ValueError when value cannot be parsed as int."""
        with self.assertRaises(ValueError):
            api.extract_book_id({"gutenbergbookid": "not-an-int"})

    # ---------------- get_etexts ----------------

    def test_get_etexts_returns_unique_id_set_from_rows(self):
        """get_etexts deduplicates IDs from matching rows."""
        rows = [
            {"gutenbergbookid": 1},
            {"gutenbergbookid": 2},
            {"gutenbergbookid": "2"},
            {"gutenbergbookid": 1},
        ]
        with mock.patch.object(api, "get_matching_rows", return_value=rows) as p_rows:
            out = api.get_etexts(authors="A")
            self.assertEqual(out, {1, 2})
            p_rows.assert_called_once()


if __name__ == "__main__":
    unittest.main()
