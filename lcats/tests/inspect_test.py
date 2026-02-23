"""Tests for lcats.lcats.inspect module."""

import io
import json
import os
import pathlib
import tempfile
import unittest
from unittest.mock import patch

from lcats import inspect as inspect_module


class TestInspectNoArgs(unittest.TestCase):
    """Tests for inspect() with no arguments."""

    def setUp(self):
        self._stderr_patcher = patch("sys.stderr", new_callable=io.StringIO)
        self._stderr_patcher.start()

    def tearDown(self):
        self._stderr_patcher.stop()

    def test_no_args_returns_code_2(self):
        """inspect() with no arguments returns exit code 2."""
        result = inspect_module.inspect()
        self.assertEqual(result, 2)

    def test_no_args_writes_usage_to_stderr(self):
        """inspect() with no arguments writes usage message to stderr."""
        buf = io.StringIO()
        with patch("sys.stderr", buf):
            inspect_module.inspect()
        self.assertIn("usage", buf.getvalue().lower())

    def test_path_resolve_exception_fallback(self):
        """inspect() falls back to raw path when Path.resolve raises."""
        buf = io.StringIO()
        with patch("pathlib.Path.resolve", side_effect=OSError("resolve failed")):
            with patch("sys.stderr", buf):
                inspect_module.inspect("/nonexistent/fallback.json")
        # The fallback path is the original raw string - error mentions the raw path
        self.assertIn("fallback.json", buf.getvalue())


class TestInspectMissingFile(unittest.TestCase):
    """Tests for inspect() with missing or invalid file paths."""

    def setUp(self):
        self._stderr_patcher = patch("sys.stderr", new_callable=io.StringIO)
        self._stderr_patcher.start()

    def tearDown(self):
        self._stderr_patcher.stop()

    def test_missing_file_returns_code_1(self):
        """inspect() with a missing file path returns exit code 1."""
        _message, code = inspect_module.inspect("/nonexistent/path/to/file.json")
        self.assertEqual(code, 1)

    def test_missing_file_writes_error_to_stderr(self):
        """inspect() with a missing file path writes error to stderr."""
        buf = io.StringIO()
        with patch("sys.stderr", buf):
            inspect_module.inspect("/nonexistent/path/file.json")
        self.assertIn("not found", buf.getvalue())

    def test_directory_path_returns_code_1(self):
        """inspect() with a directory path (not a file) returns exit code 1."""
        with tempfile.TemporaryDirectory() as tmp:
            _message, code = inspect_module.inspect(tmp)
        self.assertEqual(code, 1)

    def test_directory_path_writes_error_to_stderr(self):
        """inspect() with a directory path writes an error message to stderr."""
        with tempfile.TemporaryDirectory() as tmp:
            buf = io.StringIO()
            with patch("sys.stderr", buf):
                inspect_module.inspect(tmp)
            self.assertIn("not a file", buf.getvalue())


class TestInspectValidFile(unittest.TestCase):
    """Tests for inspect() with valid JSON files."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._stderr_patcher = patch("sys.stderr", new_callable=io.StringIO)
        self._print_patcher = patch("builtins.print")
        self._stderr_patcher.start()
        self._print_patcher.start()

    def tearDown(self):
        self._stderr_patcher.stop()
        self._print_patcher.stop()
        import shutil

        shutil.rmtree(self.tmp)

    def _write_json(self, filename, data):
        path = os.path.join(self.tmp, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return path

    def test_valid_json_returns_code_0(self):
        """inspect() with a valid JSON file returns exit code 0."""
        path = self._write_json(
            "story.json", {"name": "Test", "body": "Once.", "author": []}
        )
        _message, code = inspect_module.inspect(path)
        self.assertEqual(code, 0)

    def test_valid_json_message_includes_inspected_count(self):
        """inspect() message reports how many files were inspected."""
        path = self._write_json(
            "story.json", {"name": "Test", "body": "Once.", "author": []}
        )
        message, _code = inspect_module.inspect(path)
        self.assertIn("1", message)

    def test_multiple_valid_files_returns_code_0(self):
        """inspect() with multiple valid JSON files returns exit code 0."""
        path1 = self._write_json("s1.json", {"name": "S1", "body": "B1", "author": []})
        path2 = self._write_json("s2.json", {"name": "S2", "body": "B2", "author": []})
        message, code = inspect_module.inspect(path1, path2)
        self.assertEqual(code, 0)
        self.assertIn("2", message)

    def test_mixed_valid_and_missing_returns_code_1(self):
        """inspect() with one valid and one missing file returns exit code 1."""
        path = self._write_json("valid.json", {"name": "X", "body": "Y", "author": []})
        _message, code = inspect_module.inspect(path, "/nonexistent/z.json")
        self.assertEqual(code, 1)

    def test_invalid_json_returns_code_1(self):
        """inspect() with an invalid JSON file returns exit code 1."""
        bad_path = os.path.join(self.tmp, "bad.json")
        with open(bad_path, "w", encoding="utf-8") as f:
            f.write("not valid json {{{")
        _message, code = inspect_module.inspect(bad_path)
        self.assertEqual(code, 1)

    def test_invalid_json_writes_error_to_stderr(self):
        """inspect() with an invalid JSON file writes error to stderr."""
        bad_path = os.path.join(self.tmp, "bad.json")
        with open(bad_path, "w", encoding="utf-8") as f:
            f.write("not valid json {{{")
        buf = io.StringIO()
        with patch("sys.stderr", buf):
            inspect_module.inspect(bad_path)
        self.assertIn("error", buf.getvalue().lower())

    def test_unicode_decode_error_returns_code_1(self):
        """inspect() returns exit code 1 when a file can't be decoded as UTF-8."""
        bad_path = os.path.join(self.tmp, "binary.json")
        with open(bad_path, "wb") as f:
            f.write(b"\xff\xfe{invalid utf-8}")
        _message, code = inspect_module.inspect(bad_path)
        self.assertEqual(code, 1)

    def test_unicode_decode_error_writes_error_to_stderr(self):
        """inspect() writes error to stderr when a file can't be decoded."""
        bad_path = os.path.join(self.tmp, "binary2.json")
        with open(bad_path, "wb") as f:
            f.write(b"\xff\xfe{invalid utf-8}")
        buf = io.StringIO()
        with patch("sys.stderr", buf):
            inspect_module.inspect(bad_path)
        self.assertIn("error", buf.getvalue().lower())

    def test_general_exception_during_pretty_print_returns_code_1(self):
        """inspect() returns exit code 1 when pretty_print_story raises an unexpected error."""
        path = self._write_json("ok.json", {"name": "T", "body": "B"})
        with patch.object(
            inspect_module, "pretty_print_story", side_effect=RuntimeError("boom")
        ):
            _message, code = inspect_module.inspect(path)
        self.assertEqual(code, 1)


class TestDecodePossibleBytesLiteral(unittest.TestCase):
    """Tests for _decode_possible_bytes_literal()."""

    def test_plain_string_returned_unchanged(self):
        """A plain string is returned as-is."""
        s = "Hello, world!"
        result = inspect_module._decode_possible_bytes_literal(s)
        self.assertEqual(result, s)

    def test_bytes_literal_single_quotes_decoded(self):
        """A bytes literal with single quotes is decoded to a string."""
        b = b"hello bytes"
        s = repr(b)  # produces "b'hello bytes'"
        result = inspect_module._decode_possible_bytes_literal(s)
        self.assertEqual(result, "hello bytes")

    def test_bytes_literal_double_quotes_decoded(self):
        """A bytes literal with double quotes is decoded to a string."""
        s = 'b"decoded text"'
        result = inspect_module._decode_possible_bytes_literal(s)
        self.assertEqual(result, "decoded text")

    def test_empty_string_returns_empty(self):
        """Empty string returns empty string."""
        result = inspect_module._decode_possible_bytes_literal("")
        self.assertEqual(result, "")

    def test_invalid_bytes_literal_returns_original(self):
        """A string that starts with b' but is not a valid literal is returned as-is."""
        s = "b'not a valid \\x literal \\xzz'"
        result = inspect_module._decode_possible_bytes_literal(s)
        self.assertEqual(result, s)

    def test_short_string_starting_with_b_returned_unchanged(self):
        """A short string like 'b' (no quote) is returned as-is."""
        s = "b"
        result = inspect_module._decode_possible_bytes_literal(s)
        self.assertEqual(result, s)

    def test_whitespace_only_string(self):
        """Whitespace-only string returns the original (whitespace)."""
        s = "   "
        result = inspect_module._decode_possible_bytes_literal(s)
        self.assertEqual(result, s)

    def test_b_prefix_without_quote_returned_unchanged(self):
        """A string starting with 'b' but not followed by a quote is returned as-is."""
        s = "bXYZ"
        result = inspect_module._decode_possible_bytes_literal(s)
        self.assertEqual(result, s)

    def test_none_input_returns_empty(self):
        """None input is treated as empty and returns empty string."""
        result = inspect_module._decode_possible_bytes_literal(None)
        self.assertEqual(result, "")


class TestFormatStoryJson(unittest.TestCase):
    """Tests for format_story_json()."""

    def test_full_data_contains_title(self):
        """format_story_json includes the title."""
        data = {"name": "My Story", "body": "Once upon a time.", "author": ["Alice"]}
        result = inspect_module.format_story_json(data)
        self.assertIn("My Story", result)

    def test_full_data_contains_author(self):
        """format_story_json includes the author name."""
        data = {"name": "Story", "body": "Text.", "author": ["Bob"]}
        result = inspect_module.format_story_json(data)
        self.assertIn("Bob", result)

    def test_string_author_included(self):
        """format_story_json handles a string (not list) author."""
        data = {"name": "Story", "body": "Text.", "author": "Carol"}
        result = inspect_module.format_story_json(data)
        self.assertIn("Carol", result)

    def test_empty_author_list_no_author_section(self):
        """format_story_json with empty author list shows no author section."""
        data = {"name": "Story", "body": "Text.", "author": []}
        result = inspect_module.format_story_json(data)
        self.assertNotIn("Author", result)

    def test_missing_name_uses_default(self):
        """format_story_json uses '<Untitled>' when name is missing."""
        data = {"body": "Text."}
        result = inspect_module.format_story_json(data)
        self.assertIn("<Untitled>", result)

    def test_metadata_included(self):
        """format_story_json includes metadata key-value pairs."""
        data = {"name": "Story", "body": "Text.", "metadata": {"year": 1900}}
        result = inspect_module.format_story_json(data)
        self.assertIn("year", result)
        self.assertIn("1900", result)

    def test_body_truncated_when_long(self):
        """format_story_json truncates the body when it exceeds max_body_chars."""
        long_body = "x" * 2000
        data = {"name": "LongStory", "body": long_body}
        result = inspect_module.format_story_json(data, max_body_chars=100)
        self.assertIn("[truncated]", result)

    def test_body_not_truncated_when_short(self):
        """format_story_json does not truncate short body text."""
        data = {"name": "ShortStory", "body": "Short text."}
        result = inspect_module.format_story_json(data)
        self.assertNotIn("[truncated]", result)
        self.assertIn("Short text.", result)

    def test_bytes_body_decoded(self):
        """format_story_json decodes a bytes body."""
        data = {"name": "ByteStory", "body": b"bytes content"}
        result = inspect_module.format_story_json(data)
        self.assertIn("bytes content", result)

    def test_non_string_body_converted(self):
        """format_story_json converts a non-string body using str()."""
        data = {"name": "IntBody", "body": 12345}
        result = inspect_module.format_story_json(data)
        self.assertIn("12345", result)

    def test_bytes_literal_body_decoded(self):
        """format_story_json decodes a bytes-literal string body."""
        data = {"name": "ByteLit", "body": "b'decoded content'"}
        result = inspect_module.format_story_json(data)
        self.assertIn("decoded content", result)

    def test_result_is_string(self):
        """format_story_json always returns a string."""
        data = {"name": "T", "body": "B"}
        result = inspect_module.format_story_json(data)
        self.assertIsInstance(result, str)

    def test_separator_present(self):
        """format_story_json includes separator lines."""
        data = {"name": "Sep", "body": "Body."}
        result = inspect_module.format_story_json(data, width=40)
        self.assertIn("=" * 40, result)

    def test_custom_width(self):
        """format_story_json respects the width parameter for separators."""
        data = {"name": "W", "body": "Body."}
        result = inspect_module.format_story_json(data, width=60)
        self.assertIn("=" * 60, result)

    def test_whitespace_string_author_not_shown(self):
        """format_story_json does not show author section for whitespace-only string author."""
        data = {"name": "Story", "body": "Text.", "author": "   "}
        result = inspect_module.format_story_json(data)
        self.assertNotIn("Author:", result)

    def test_none_author_no_author_section(self):
        """format_story_json with explicit None author shows no author section."""
        data = {"name": "Story", "body": "Text.", "author": None}
        result = inspect_module.format_story_json(data)
        self.assertNotIn("Author", result)

    def test_bytearray_body_decoded(self):
        """format_story_json decodes a bytearray body."""
        data = {"name": "ByteArrayStory", "body": bytearray(b"bytearray content")}
        result = inspect_module.format_story_json(data)
        self.assertIn("bytearray content", result)

    def test_empty_metadata_no_metadata_section(self):
        """format_story_json with empty metadata dict shows no metadata section."""
        data = {"name": "Story", "body": "Text.", "metadata": {}}
        result = inspect_module.format_story_json(data)
        self.assertNotIn("Metadata", result)


class TestPrettyPrintStory(unittest.TestCase):
    """Tests for pretty_print_story()."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp)

    def _write_json(self, filename, data):
        path = os.path.join(self.tmp, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return path

    def test_pretty_print_produces_output(self):
        """pretty_print_story prints non-empty output for a valid JSON file."""
        path = self._write_json(
            "story.json",
            {"name": "PrintStory", "body": "Body text.", "author": ["Alice"]},
        )
        buf = io.StringIO()
        with patch("builtins.print", side_effect=lambda x: buf.write(x + "\n")):
            inspect_module.pretty_print_story(path)
        self.assertIn("PrintStory", buf.getvalue())

    def test_pretty_print_accepts_pathlib_path(self):
        """pretty_print_story accepts a pathlib.Path object."""
        path = self._write_json(
            "p.json",
            {"name": "PathLib", "body": "Body.", "author": []},
        )
        buf = io.StringIO()
        with patch("builtins.print", side_effect=lambda x: buf.write(x + "\n")):
            inspect_module.pretty_print_story(pathlib.Path(path))
        self.assertIn("PathLib", buf.getvalue())

    def test_pretty_print_custom_max_body_chars(self):
        """pretty_print_story respects max_body_chars parameter."""
        long_body = "z" * 500
        path = self._write_json("long.json", {"name": "LongPrint", "body": long_body})
        buf = io.StringIO()
        with patch("builtins.print", side_effect=lambda x: buf.write(x + "\n")):
            inspect_module.pretty_print_story(path, max_body_chars=10)
        self.assertIn("[truncated]", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
