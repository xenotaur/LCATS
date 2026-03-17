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
                cache=object(), field="title", book_id=2701
            )
            self.assertEqual(out, {"Moby-Dick"})
            p.assert_called_once_with(mock.ANY, 2701)

    def test_get_metadata_from_cache_dispatches_author(self):
        """get_metadata_from_cache uses authors_for for author/authors fields."""
        with mock.patch.object(
            metadata, "authors_for", return_value={"Melville, Herman"}
        ) as p:
            out = metadata.get_metadata_from_cache(
                cache=object(), field="authors", book_id=2701
            )
            self.assertEqual(out, {"Melville, Herman"})
            p.assert_called_once_with(mock.ANY, 2701)

    def test_get_metadata_from_cache_dispatches_language(self):
        """get_metadata_from_cache uses languages_for for language/languages fields."""
        with mock.patch.object(metadata, "languages_for", return_value={"en"}) as p:
            out = metadata.get_metadata_from_cache(
                cache=object(), field="language", book_id=2701
            )
            self.assertEqual(out, {"en"})
            p.assert_called_once_with(mock.ANY, 2701)

    def test_get_metadata_from_cache_dispatches_subject(self):
        """get_metadata_from_cache uses subjects_for for subject/subjects fields."""
        with mock.patch.object(
            metadata, "subjects_for", return_value={"Whaling -- Fiction"}
        ) as p:
            out = metadata.get_metadata_from_cache(
                cache=object(), field="subjects", book_id=2701
            )
            self.assertEqual(out, {"Whaling -- Fiction"})
            p.assert_called_once_with(mock.ANY, 2701)

    def test_get_metadata_from_cache_raises_on_unsupported_field(self):
        """get_metadata_from_cache raises ValueError for unsupported fields."""
        with self.assertRaises(ValueError):
            metadata.get_metadata_from_cache(
                cache=object(), field="publisher", book_id=2701
            )

    def test_get_metadata_from_cache_propagates_exceptions(self):
        """get_metadata_from_cache re-raises exceptions from helper calls."""
        with mock.patch.object(
            metadata, "titles_for", side_effect=RuntimeError("boom")
        ):
            with self.assertRaises(RuntimeError):
                metadata.get_metadata_from_cache(
                    cache=object(), field="title", book_id=1
                )

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
        self.assertEqual(metadata.get_metadata_from_header("title", header), set())
        self.assertEqual(metadata.get_metadata_from_header("subjects", header), set())

    def test_get_metadata_from_header_allows_colons_in_value(self):
        """Header parser keeps additional colons in the value part."""
        header = ["Title: Foo: Bar", "Author: Last, First: Extra"]
        self.assertEqual(
            metadata.get_metadata_from_header("title", header), {"Foo: Bar"}
        )
        self.assertEqual(
            metadata.get_metadata_from_header("author", header), {"Last, First: Extra"}
        )

    def test_get_metadata_from_header_raises_on_unsupported_field(self):
        """Header parser raises ValueError for unsupported fields."""
        with self.assertRaises(ValueError):
            metadata.get_metadata_from_header("publisher", ["Publisher: Unknown"])

    # ---------------- SQL helpers: titles_for / authors_for / languages_for / subjects_for ----------------

    def test_titles_for_builds_expected_sql_and_returns_strings(self):
        """titles_for emits correct SQL shape and returns normalized set."""
        rows = [("Moby-Dick",), ("Moby-Dick",)]  # duplicates deduped
        fc = _FakeCache(rows)
        out = metadata.titles_for(fc, 2701)
        self.assertEqual(out, ["Moby-Dick"])
        self.assertIn("FROM titles t", fc.last_sql)
        self.assertIn("JOIN books b ON t.bookid = b.id", fc.last_sql)
        self.assertIn("WHERE b.gutenbergbookid = 2701", fc.last_sql)

    def test_authors_for_builds_expected_sql_and_returns_strings(self):
        """authors_for emits correct SQL shape and returns normalized set."""
        rows = [("Melville, Herman",)]
        fc = _FakeCache(rows)
        out = metadata.authors_for(fc, 2701)
        self.assertEqual(out, ["Melville, Herman"])
        self.assertIn("FROM authors a", fc.last_sql)
        self.assertIn("JOIN book_authors ba ON a.id = ba.authorid", fc.last_sql)
        self.assertIn("JOIN books b         ON ba.bookid = b.id", fc.last_sql)
        self.assertIn("WHERE b.gutenbergbookid = 2701", fc.last_sql)

    def test_languages_for_builds_expected_sql_and_returns_strings(self):
        """languages_for emits expected SQL and returns normalized set."""
        rows = [("en",), ("fr",)]
        fc = _FakeCache(rows)
        out = metadata.languages_for(fc, 2701)
        self.assertEqual(out, ["en", "fr"])
        self.assertIn("FROM languages l", fc.last_sql)
        # assert the join shape used by your implementation
        self.assertIn("JOIN books b ON l.id = b.languageid", fc.last_sql)
        self.assertIn("WHERE b.gutenbergbookid = 2701", fc.last_sql)

    def test_subjects_for_builds_expected_sql_and_returns_strings(self):
        """subjects_for emits expected SQL and returns normalized set."""
        rows = [("Whaling -- Fiction",), ("Sea stories",)]
        fc = _FakeCache(rows)
        out = metadata.subjects_for(fc, 2701)
        self.assertEqual(out, ["Sea stories", "Whaling -- Fiction"])
        self.assertIn("FROM subjects s", fc.last_sql)
        self.assertIn("JOIN book_subjects bs ON s.id = bs.subjectid", fc.last_sql)
        self.assertIn("JOIN books b          ON bs.bookid = b.id", fc.last_sql)
        self.assertIn("WHERE b.gutenbergbookid = 2701", fc.last_sql)

    def test_aliases_for_builds_expected_sql_and_returns_strings(self):
        """aliases_for emits expected SQL shape and returns normalized set."""
        rows = [("Twain, Mark",)]
        fc = _FakeCache(rows)
        out = metadata.aliases_for(fc, 3176)
        self.assertEqual(out, ["Twain, Mark"])
        self.assertIn("FROM aliases a", fc.last_sql)
        self.assertIn("WHERE b.gutenbergbookid = 3176", fc.last_sql)

    def test_get_metadata_from_cache_dispatches_alias(self):
        """get_metadata_from_cache uses aliases_for for alias/aliases fields."""
        with mock.patch.object(
            metadata, "aliases_for", return_value={"Twain, Mark"}
        ) as p:
            out = metadata.get_metadata_from_cache(
                cache=object(), field="alias", book_id=3176
            )
            self.assertEqual(out, {"Twain, Mark"})
            p.assert_called_once_with(mock.ANY, 3176)

    def test_get_metadata_from_cache_dispatches_aliases(self):
        """get_metadata_from_cache uses aliases_for for aliases field."""
        with mock.patch.object(
            metadata, "aliases_for", return_value={"Twain, Mark"}
        ) as p:
            out = metadata.get_metadata_from_cache(
                cache=object(), field="aliases", book_id=3176
            )
            self.assertEqual(out, {"Twain, Mark"})
            p.assert_called_once_with(mock.ANY, 3176)


class SplitIntoConsecutiveChunksTests(unittest.TestCase):
    """Unit tests for split_into_consecutive_chunks."""

    def test_empty_input_returns_empty_list(self):
        """Empty input returns an empty list."""
        self.assertEqual(metadata.split_into_consecutive_chunks([]), [])

    def test_single_element(self):
        """Single-element input returns one chunk containing that element."""
        self.assertEqual(metadata.split_into_consecutive_chunks([7]), [[7]])

    def test_all_consecutive_descending(self):
        """Fully consecutive descending sequence is one chunk."""
        self.assertEqual(
            metadata.split_into_consecutive_chunks([5, 4, 3]),
            [[5, 4, 3]],
        )

    def test_non_consecutive_splits_into_multiple_chunks(self):
        """Non-consecutive values each form their own chunk."""
        self.assertEqual(
            metadata.split_into_consecutive_chunks([10, 7, 6]),
            [[10], [7, 6]],
        )

    def test_all_non_consecutive_one_per_chunk(self):
        """Values with no consecutive relationships each produce a single chunk."""
        self.assertEqual(
            metadata.split_into_consecutive_chunks([9, 5, 1]),
            [[9], [5], [1]],
        )

    def test_mixed_consecutive_and_non_consecutive(self):
        """Mixed sequence splits at non-consecutive boundaries."""
        self.assertEqual(
            metadata.split_into_consecutive_chunks([8, 7, 5, 4, 3, 1]),
            [[8, 7], [5, 4, 3], [1]],
        )


class ConvertToNameTests(unittest.TestCase):
    """Unit tests for convert_to_name and convert_to_names."""

    def _make_fetchall_cache(self, rows_by_id):
        """Return a fake cache where native_query(...).fetchall() returns rows."""

        class _FetchAllResult:
            def __init__(self, rows):
                self._rows = rows

            def fetchall(self):
                return self._rows

        class _FetchCache:
            def native_query(self, sql):
                for author_id, rows in rows_by_id.items():
                    if str(author_id) in sql:
                        return _FetchAllResult(rows)
                return _FetchAllResult([])

        return _FetchCache()

    def test_convert_to_name_returns_name_from_query(self):
        """convert_to_name returns the second column of the first row."""
        cache = self._make_fetchall_cache({42: [(42, "Clemens, Samuel")]})
        self.assertEqual(metadata.convert_to_name(cache, 42), "Clemens, Samuel")

    def test_convert_to_names_returns_list_of_names(self):
        """convert_to_names returns a list of names for each given id."""
        cache = self._make_fetchall_cache(
            {1: [(1, "Doe, Jane")], 2: [(2, "Doe, John")]}
        )
        result = metadata.convert_to_names(cache, [1, 2])
        self.assertEqual(result, ["Doe, Jane", "Doe, John"])

    def test_convert_to_names_empty_list(self):
        """convert_to_names with an empty list returns an empty list."""
        cache = self._make_fetchall_cache({})
        self.assertEqual(metadata.convert_to_names(cache, []), [])


class AuthorsSplitTests(unittest.TestCase):
    """Unit tests for authors_split."""

    def test_authors_split_returns_names_grouped_by_consecutive_ids(self):
        """authors_split groups consecutive author IDs and resolves them to names."""
        # Rows returned by the first query: author IDs 3, 1 (as strings in tuples).
        # IDs 3 and 1 are non-consecutive, so they form two chunks [[3], [1]].
        # Each chunk is resolved via convert_to_names.

        class _SmartCache:
            def __init__(self):
                self.call_count = 0
                self._names = {1: "Austen, Jane", 3: "Dickens, Charles"}

            def native_query(self, sql):
                self.call_count += 1

                class _Rows:
                    def __init__(self, rows):
                        self._rows = rows

                    def __iter__(self):
                        return iter(self._rows)

                    def fetchall(self):
                        return self._rows

                if "gutenbergbookid" in sql:
                    return _Rows([("3",), ("1",)])
                # author lookup by id
                for aid, name in self._names.items():
                    if str(aid) in sql:
                        return _Rows([(aid, name)])
                return _Rows([])

        cache = _SmartCache()
        result = metadata.authors_split(cache, 99)
        # IDs [3,1] sorted desc → [3,1]; chunks [[3],[1]]; names resolved
        self.assertIsInstance(result, list)
        flat = [name for chunk in result for name in chunk]
        self.assertIn("Dickens, Charles", flat)
        self.assertIn("Austen, Jane", flat)

    def test_authors_split_empty_returns_empty_list(self):
        """authors_split with no rows returns an empty list."""

        class _EmptyCache:
            def native_query(self, sql):
                class _Rows:
                    def __iter__(self):
                        return iter([])

                    def fetchall(self):
                        return []

                return _Rows()

        result = metadata.authors_split(_EmptyCache(), 0)
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
