import unittest
import unittest.mock as mock

from lcats.gettenberg import headers


class GettenbergHeadersTests(unittest.TestCase):
    """Unit tests for header processing helpers in lcats.gettenberg.headers."""

    # ---------------- strip_headers ----------------

    def test_strip_headers_passes_bytes_through_to_backend_and_returns_bytes(self):
        """strip_headers forwards bytes to textget.strip_headers and returns bytes."""
        data = b"Some header\n\n*** START OF THE PROJECT GUTENBERG EBOOK\nBody..."
        with mock.patch.object(headers.textget, "strip_headers", return_value=b"Body") as p:
            out = headers.strip_headers(data)
            self.assertEqual(out, b"Body")
            p.assert_called_once_with(data)

    def test_strip_headers_encodes_str_input_utf8(self):
        """strip_headers encodes str to UTF-8 before calling backend."""
        s = "Title: Moby-Dick 🐋\n\n*** START OF THE PROJECT GUTENBERG EBOOK\nBody..."
        with mock.patch.object(headers.textget, "strip_headers", return_value=b"Body") as p:
            out = headers.strip_headers(s)
            self.assertEqual(out, b"Body")
            # Ensure the backend saw bytes (UTF-8 encoded)
            arg = p.call_args[0][0]
            self.assertIsInstance(arg, (bytes, bytearray))
            self.assertIn("Moby-Dick", arg.decode("utf-8", errors="ignore"))

    # ---------------- get_text_header_lines ----------------

    def test_get_text_header_lines_yields_nonblank_trimmed_lines_until_marker(self):
        """get_text_header_lines yields non-empty, trimmed lines before '*** START' marker."""
        text = (
            b"Title: Something  \n"
            b"\n"
            b"Author: Someone\n"
            b"  \n"
            b"*** START OF THE PROJECT GUTENBERG EBOOK\n"
            b"Body starts here"
        )
        got = list(headers.get_text_header_lines(text))
        self.assertEqual(got, ["Title: Something", "Author: Someone"])

    def test_get_text_header_lines_uses_entire_text_when_marker_missing(self):
        """If no '*** START' marker exists, treat whole text as header region."""
        text = b"Line A\n\nLine B\n"  # no marker
        got = list(headers.get_text_header_lines(text))
        self.assertEqual(got, ["Line A", "Line B"])

    def test_get_text_header_lines_decodes_with_ignore_on_invalid_utf8(self):
        """Invalid UTF-8 bytes are ignored while decoding."""
        # \xff and \x80 are invalid starters in UTF-8; decoding with 'ignore' drops them.
        text = b"\xffBad\x80Line\nOK\n*** START OF THE PROJECT GUTENBERG EBOOK\nBody"
        got = list(headers.get_text_header_lines(text))
        self.assertEqual(got, ["BadLine", "OK"])

    def test_get_text_header_lines_raises_typeerror_on_str_input_current_behavior(self):
        """Current implementation expects bytes; str input raises TypeError."""
        # Note: this documents current behavior—which contradicts the docstring.
        # If you decide to support str here, update implementation and this test.
        with self.assertRaises(TypeError):
            list(headers.get_text_header_lines("Title: X\n*** START\nBody"))


if __name__ == "__main__":
    unittest.main()
