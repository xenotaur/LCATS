"""Unit tests for lcats.gettenberg.metadata functions."""

import unittest
import unittest.mock as mock

from lcats.gettenberg import metadata


class _FakeCache:
    """Minimal fake cache exposing native_query and capturing last SQL."""

    def __init__(self, rows):
        self._rows = rows
        self.last_sql = None

    def native_query(self, sql):
        self.last_sql = sql
        # Return whatever rows were injected for this fake
        return self._rows


class GettenbergApiMetadataTests(unittest.TestCase):
    """Unit tests for metadata extraction helpers in lcats.gettenberg.api."""

    # ---------------- get_metadata_from_cache ----------------

    def test_get_metadata_from_cache_dispatches_title(self):
        """get_metadata_from_cache uses titles_for for title/titles fields."""
        with mock.patch.object(metadata, "titles_for", return_value={"Moby-Dick"}) as p:
            out = metadata.get_metadata_from_cache(
                cache=object(), field="title", book_id=2701)
            self.assertEqual(out, {"Moby-Dick"})
            p.assert_called_once_with(mock.ANY, 2701)

    def test_get_metadata_from_cache_dispatches_author(self):
        """get_metadata_from_cache uses authors_for for author/authors fields."""
        with mock.patch.object(metadata, "authors_for", return_value={"Melville, Herman"}) as p:
            out = metadata.get_metadata_from_cache(
                cache=object(), field="authors", book_id=2701)
            self.assertEqual(out, {"Melville, Herman"})
            p.assert_called_once_with(mock.ANY, 2701)

    def test_get_metadata_from_cache_dispatches_language(self):
        """get_metadata_from_cache uses languages_for for language/languages fields."""
        with mock.patch.object(metadata, "languages_for", return_value={"en"}) as p:
            out = metadata.get_metadata_from_cache(
                cache=object(), field="language", book_id=2701)
            self.assertEqual(out, {"en"})
            p.assert_called_once_with(mock.ANY, 2701)

    def test_get_metadata_from_cache_dispatches_subject(self):
        """get_metadata_from_cache uses subjects_for for subject/subjects fields."""
        with mock.patch.object(metadata, "subjects_for", return_value={"Whaling -- Fiction"}) as p:
            out = metadata.get_metadata_from_cache(
                cache=object(), field="subjects", book_id=2701)
            self.assertEqual(out, {"Whaling -- Fiction"})
            p.assert_called_once_with(mock.ANY, 2701)

    def test_get_metadata_from_cache_raises_on_unsupported_field(self):
        """get_metadata_from_cache raises ValueError for unsupported fields."""
        with self.assertRaises(ValueError):
            metadata.get_metadata_from_cache(
                cache=object(), field="publisher", book_id=2701)

    def test_get_metadata_from_cache_propagates_exceptions(self):
        """get_metadata_from_cache re-raises exceptions from helper calls."""
        with mock.patch.object(metadata, "titles_for", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                metadata.get_metadata_from_cache(
                    cache=object(), field="title", book_id=1)

    # ---------------- get_metadata_from_header ----------------

    def test_get_metadata_from_header_parses_all_supported_fields(self):
        """Header parser extracts title/author/language/subject (case-insensitive)."""
        header = [
            "Title: Moby-Dick; or, The Whale",
            "AUTHOR: Melville, Herman",
            "Language: en",
            "Subject: Whaling -- Fiction",
            "SUBJECT: Sea stories",
            "Random: ignore me",
        ]
        self.assertEqual(
            metadata.get_metadata_from_header("title", header),
            {"Moby-Dick; or, The Whale"},
        )
        self.assertEqual(
            metadata.get_metadata_from_header("authors", header),
            {"Melville, Herman"},
        )
        self.assertEqual(
            metadata.get_metadata_from_header("languages", header),
            {"en"},
        )
        self.assertEqual(
            metadata.get_metadata_from_header("subjects", header),
            {"Whaling -- Fiction", "Sea stories"},
        )

    def test_get_metadata_from_header_returns_empty_set_when_missing(self):
        """Header parser returns empty set when no matching lines are present."""
        header = ["Not a field: value", "Another: value"]
        self.assertEqual(metadata.get_metadata_from_header(
            "title", header), set())
        self.assertEqual(metadata.get_metadata_from_header(
            "subjects", header), set())

    def test_get_metadata_from_header_allows_colons_in_value(self):
        """Header parser keeps additional colons in the value part."""
        header = ["Title: Foo: Bar", "Author: Last, First: Extra"]
        self.assertEqual(metadata.get_metadata_from_header(
            "title", header), {"Foo: Bar"})
        self.assertEqual(metadata.get_metadata_from_header(
            "author", header), {"Last, First: Extra"})

    def test_get_metadata_from_header_raises_on_unsupported_field(self):
        """Header parser raises ValueError for unsupported fields."""
        with self.assertRaises(ValueError):
            metadata.get_metadata_from_header(
                "publisher", ["Publisher: Unknown"])

    # ---------------- SQL helpers: titles_for / authors_for / languages_for / subjects_for ----------------

    def test_titles_for_builds_expected_sql_and_returns_strings(self):
        """titles_for emits correct SQL shape and returns normalized set."""
        rows = [("Moby-Dick",), ("Moby-Dick",)]  # duplicates deduped
        fc = _FakeCache(rows)
        out = metadata.titles_for(fc, 2701)
        self.assertEqual(out, {"Moby-Dick"})
        self.assertIn("FROM titles t", fc.last_sql)
        self.assertIn("JOIN books b ON t.bookid = b.id", fc.last_sql)
        self.assertIn("WHERE b.gutenbergbookid = 2701", fc.last_sql)

    def test_authors_for_builds_expected_sql_and_returns_strings(self):
        """authors_for emits correct SQL shape and returns normalized set."""
        rows = [("Melville, Herman",)]
        fc = _FakeCache(rows)
        out = metadata.authors_for(fc, 2701)
        self.assertEqual(out, {"Melville, Herman"})
        self.assertIn("FROM authors a", fc.last_sql)
        self.assertIn(
            "JOIN book_authors ba ON a.id = ba.authorid", fc.last_sql)
        self.assertIn("JOIN books b         ON ba.bookid = b.id", fc.last_sql)
        self.assertIn("WHERE b.gutenbergbookid = 2701", fc.last_sql)

    def test_languages_for_builds_expected_sql_and_returns_strings(self):
        """languages_for emits expected SQL and returns normalized set."""
        rows = [("en",), ("fr",)]
        fc = _FakeCache(rows)
        out = metadata.languages_for(fc, 2701)
        self.assertEqual(out, {"en", "fr"})
        self.assertIn("FROM languages l", fc.last_sql)
        # assert the join shape used by your implementation
        self.assertIn("JOIN books b ON l.id = b.languageid", fc.last_sql)
        self.assertIn("WHERE b.gutenbergbookid = 2701", fc.last_sql)

    def test_subjects_for_builds_expected_sql_and_returns_strings(self):
        """subjects_for emits expected SQL and returns normalized set."""
        rows = [("Whaling -- Fiction",), ("Sea stories",)]
        fc = _FakeCache(rows)
        out = metadata.subjects_for(fc, 2701)
        self.assertEqual(out, {"Whaling -- Fiction", "Sea stories"})
        self.assertIn("FROM subjects s", fc.last_sql)
        self.assertIn(
            "JOIN book_subjects bs ON s.id = bs.subjectid", fc.last_sql)
        self.assertIn("JOIN books b          ON bs.bookid = b.id", fc.last_sql)
        self.assertIn("WHERE b.gutenbergbookid = 2701", fc.last_sql)


if __name__ == "__main__":
    unittest.main()
