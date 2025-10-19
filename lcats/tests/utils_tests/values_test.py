"""Tests for lcats.utils.values functions."""

import unittest
from lcats.utils import values


class ValuesUtilsTests(unittest.TestCase):
    """Tests for lcats.utils.values functions."""

    def test_strings_from_sql_empty_iterable(self):
        """Test that an empty iterable returns an empty set."""
        self.assertEqual(values.strings_from_sql([]), set())

    def test_strings_from_sql_tuple_rows(self):
        """Test tuple rows with various cases, including None and numeric."""
        rows = [
            (123,),                # numeric → "123"
            ("hello", "ignored"),  # only first element is used
            (None,),               # None is ignored
            ["world"],             # list row also supported
        ]
        got = values.strings_from_sql(rows)
        self.assertEqual(got, {"123", "hello", "world"})

    def test_strings_from_sql_dict_rows(self):
        """Test dict rows with various cases, including missing/None 'v'."""
        rows = [
            {"v": "alpha"},
            {"v": 42},               # numeric → "42"
            {"v": None},             # ignored
            {"other": "beta"},       # missing 'v' → ignored
            {"v": "alpha"},          # duplicate
        ]
        got = values.strings_from_sql(rows)
        self.assertEqual(got, {"alpha", "42"})

    def test_strings_from_sql_mixed_rows(self):
        """Test mixed tuple and dict rows, including bytes."""
        rows = [
            {"v": "x"},
            (b"y",),                 # bytes in tuple → "b'y'"
            ["z", "extra"],
            {"other": "ignored"},
        ]
        self.assertEqual(values.strings_from_sql(rows), {"x", "b'y'", "z"})

    # ---------- strings_as_list ----------

    def test_strings_as_list_none(self):
        """Test that None input returns None."""
        self.assertIsNone(values.strings_as_list(None))

    def test_strings_as_list_with_string(self):
        """Test that a single string input returns a single-item list."""
        self.assertEqual(values.strings_as_list("hello"), ["hello"])

    def test_strings_as_list_with_list(self):
        """Test that a list input returns a list."""
        self.assertEqual(values.strings_as_list(["a", "b"]), ["a", "b"])

    def test_strings_as_list_with_tuple(self):
        """Test that a tuple input returns a list."""
        self.assertEqual(values.strings_as_list(("a", "b")), ["a", "b"])

    def test_strings_as_list_with_set(self):
        """Test that a set input returns a list."""
        # Note order is not guaranteed for sets; compare as sets.
        out = values.strings_as_list({"a", "b"})
        self.assertEqual(set(out), {"a", "b"})

    def test_strings_as_list_coerces_non_string_scalar(self):
        """Test that a non-string scalar input is coerced to string in a list."""
        # Function coerces non-string scalars via str(x) when x is not a list/tuple/set.
        self.assertEqual(values.strings_as_list(5), ["5"])


if __name__ == "__main__":
    unittest.main()
