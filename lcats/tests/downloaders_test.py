"""Tests for the downloaders module."""

# Assuming convert_encoding is in this module
from lcats.gatherers import downloaders
import os
import unittest
from unittest.mock import patch, Mock
from lcats import constants
from lcats import test_utils

# import parameterized
import requests


class TestDetectUrlEncoding(unittest.TestCase):
    """Unit tests for the detect_url_encoding function."""

    @patch("requests.head")
    def test_detect_url_encoding_success(self, mock_head):
        """Test detecting the encoding of a URL with a successful response."""
        # Mock a successful response with a specified encoding
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.encoding = "utf-8"
        mock_head.return_value = mock_response

        url = "http://example.com"
        encoding = downloaders.detect_url_encoding(url)
        self.assertEqual(encoding, "utf-8")

    @patch("requests.head")
    def test_detect_url_encoding_failure(self, mock_head):
        """Test detecting the encoding of a URL with a failed response."""
        # Mock a failed response (e.g., 404 Not Found)
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.encoding = None
        mock_head.return_value = mock_response

        url = "http://example.com"
        encoding = downloaders.detect_url_encoding(url)
        self.assertIsNone(encoding)


class TestDetectEncoding(unittest.TestCase):
    """Unit tests for the detect_encoding function."""

    def test_detect_encoding_utf8(self):
        """Test detecting UTF-8 encoding."""
        text = "Some UTF-8 encoded text 麦蒂"
        encoding = downloaders.detect_encoding(text)
        self.assertEqual(encoding, "utf-8")

    def test_detect_encoding_latin1(self):
        """ "Text in Latin-1 encoding."""
        text = "quanto lhe é possive"
        encoding = downloaders.detect_encoding(text)
        self.assertEqual(encoding, "ISO-8859-1")

    def test_detect_encoding_ascii(self):
        """Test detecting ASCII encoding."""
        text = "Simple ASCII text"
        encoding = downloaders.detect_encoding(text)
        self.assertEqual(encoding, "ascii")

    def test_detect_encoding_unknown(self):
        """Test detecting an unknown encoding."""
        # A byte sequence that doesn't clearly match a known encoding
        text = b"\xff\xfe\xfd"
        encoding = downloaders.detect_encoding(text)
        # `chardet` might return None for unknown encodings, or call it UTF-16
        self.assertEqual(encoding, "UTF-16")


class TestConvertEncoding(unittest.TestCase):
    """Unit tests for the convert_encoding function."""

    def test_utf8_to_iso8859_1(self):
        """Test converting UTF-8 to ISO-8859-1 encoding."""
        text = "Café"  # UTF-8 text with a special character
        result = downloaders.convert_encoding(
            text, source_encoding="utf-8", target_encoding="ISO-8859-1"
        )
        expected_result = text.encode("ISO-8859-1")
        self.assertEqual(result, expected_result)

    def test_iso8859_1_to_utf8(self):
        """Test converting ISO-8859-1 to UTF-8 encoding."""
        text = "Café".encode("ISO-8859-1")  # Latin-1 encoded byte string
        result = downloaders.convert_encoding(
            text, source_encoding="ISO-8859-1", target_encoding="utf-8"
        )
        expected_result = "Café".encode("utf-8")
        self.assertEqual(result, expected_result)

    def test_ascii_to_utf8(self):
        """Test converting ASCII to UTF-8 encoding."""
        text = "Simple ASCII text"  # ASCII text
        result = downloaders.convert_encoding(
            text, source_encoding="ascii", target_encoding="utf-8"
        )
        expected_result = text.encode("utf-8")
        self.assertEqual(result, expected_result)

    def test_byte_input_utf8_to_iso8859_1(self):
        """Test converting a byte string from UTF-8 to ISO-8859-1 encoding."""
        # UTF-8 encoded byte string with an emoji
        text = "Text with emoji 😊".encode("utf-8")
        result = downloaders.convert_encoding(
            text, source_encoding="utf-8", target_encoding="ISO-8859-1"
        )
        # ISO-8859-1 cannot represent the emoji, should return None
        self.assertIsNone(result)

    def test_invalid_source_encoding(self):
        text = "Invalid encoding test"
        result = downloaders.convert_encoding(
            text, source_encoding="nonexistent-encoding", target_encoding="utf-8"
        )
        self.assertIsNone(result)

    def test_invalid_target_encoding(self):
        text = "Invalid encoding test"
        result = downloaders.convert_encoding(
            text, source_encoding="utf-8", target_encoding="nonexistent-encoding"
        )
        self.assertIsNone(result)

    def test_empty_string(self):
        text = ""
        result = downloaders.convert_encoding(
            text, source_encoding="utf-8", target_encoding="ISO-8859-1"
        )
        self.assertEqual(result, b"")

    def test_none_input(self):
        text = None
        with self.assertRaises(AttributeError):
            downloaders.convert_encoding(
                text, source_encoding="utf-8", target_encoding="ISO-8859-1"
            )


class TestLoadPage(unittest.TestCase):
    """Tests for the load_page function."""

    @patch("lcats.gatherers.downloaders.requests.get")
    def test_load_page_success(self, mock_get):
        """Test the load_page function with a successful response."""
        # Create a mock response object with the desired properties
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Mocked page content"
        mock_get.return_value = mock_response

        # Call the function
        result = downloaders.load_page("http://example.com")

        # Assert the expected behavior
        self.assertEqual(result, "Mocked page content")
        mock_get.assert_called_once_with("http://example.com", timeout=10)

    @patch("lcats.gatherers.downloaders.requests.get")
    def test_load_page_failure(self, mock_get):
        """Test the load_page function with a failed response."""
        # Create a mock response object with a failure status code
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_get.return_value = mock_response

        # Call the function
        result = downloaders.load_page("http://example.com")

        # Assert the expected behavior
        self.assertIsNone(result)
        mock_get.assert_called_once_with("http://example.com", timeout=10)

    @patch("lcats.gatherers.downloaders.requests.get")
    def test_load_page_timeout(self, mock_get):
        """Test the load_page function with a timeout exception."""
        # Simulate a timeout exception
        mock_get.side_effect = requests.exceptions.Timeout

        # Call the function
        with self.assertRaises(requests.exceptions.Timeout):
            downloaders.load_page("http://example.com")


class TestFilenameFromUrl(unittest.TestCase):
    """Tests for the filename_from_url function."""

    def test_basic_url(self):
        """Test generating a filename from a basic URL."""
        url = "http://example.com/file.txt"
        expected_extension = ".txt"
        filename = downloaders.filename_from_url(url)

        # Ensure the filename ends with the correct extension
        self.assertTrue(filename.endswith(expected_extension))

        # Ensure the filename is correctly hashed and unique
        self.assertEqual(len(filename), 64 + len(expected_extension))

    def test_url_with_query(self):
        """Test generating a filename from a URL with a query parameter."""
        url = "http://example.com/file.txt?param=value"
        filename = downloaders.filename_from_url(url)

        # Ensure the filename is unique even with a query parameter
        # 64 for the hash + 4 for ".txt"
        self.assertEqual(len(filename), 64 + 4)

    def test_url_without_extension(self):
        """Test generating a filename from a URL without an extension."""
        url = "http://example.com/file"
        filename = downloaders.filename_from_url(url)

        # Ensure the filename has no extension
        self.assertEqual(len(filename), 64)
        self.assertTrue("." not in filename)

    def test_url_with_no_path(self):
        """Test generating a filename from a URL with no path."""
        url = "http://example.com"
        filename = downloaders.filename_from_url(url)

        # Ensure the filename has no extension and is hashed correctly
        self.assertEqual(len(filename), 64)

    def test_empty_url(self):
        """Test generating a filename from an empty URL."""
        url = ""
        filename = downloaders.filename_from_url(url)

        # Ensure the filename is still a valid hash with no extension
        self.assertEqual(len(filename), 64)


class TestLambdaResourceCache(test_utils.TestCaseWithData):

    def test_instantiation(self):
        """Test instantiating a LocalTreeReader with no parameters."""
        try:
            cache = downloaders.LambdaResourceCache(
                canonicalizer=lambda x: x, acquirer=lambda x: x
            )
            self.assertIsInstance(
                cache,
                downloaders.LambdaResourceCache,
                "LambdaResourceCache instance was not created correctly.",
            )
            self.assertEqual(cache.root, constants.CACHE_ROOT)
        except Exception as e:
            self.fail(f"Instantiation of LambdaResourceCache failed: {e}")

    def test_instantiation_with_root(self):
        """Test instantiating a LocalTreeReader with a root parameter."""
        try:
            cache = downloaders.LambdaResourceCache(
                canonicalizer=lambda x: x, acquirer=lambda x: x, root=self.test_temp_dir
            )
            self.assertIsInstance(
                cache,
                downloaders.LambdaResourceCache,
                "LambdaResourceCache instance was not created correctly.",
            )
            self.assertEqual(cache.root, self.test_temp_dir)
        except Exception as e:
            self.fail(f"Instantiation of LambdaResourceCache failed: {e}")

    def test_full_path(self):
        """Test the full_path method."""
        cache = downloaders.LambdaResourceCache(
            canonicalizer=lambda x: x, acquirer=lambda x: x
        )
        self.assertEqual(
            cache.full_path("foo.bar"),
            os.path.join(constants.CACHE_ROOT, "foo.bar"),
            "Full path failed.",
        )

    def test_ensure(self):
        """Test the ensure method."""
        cache = downloaders.LambdaResourceCache(
            canonicalizer=lambda x: x, acquirer=lambda x: x
        )

        full_path = cache.full_path("foo.bar")
        if os.path.exists(full_path):
            os.unlink(full_path)  # Remove the file or link
        file_exists, path = cache.ensure("foo.bar")
        self.assertFalse(file_exists, "File should not exist.")
        self.assertEqual(path, full_path, "Path is correct.")

        with open(full_path, "w", encoding=constants.TEXT_ENCODING) as file:
            file.write("contents")
        file_exists, path = cache.ensure("foo.bar")
        self.assertTrue(file_exists, "File should exist.")
        self.assertEqual(path, full_path, "Path is correct.")
        if os.path.exists(full_path):
            os.unlink(full_path)  # Remove the file or link

    def test_canonicalize(self):
        """Test the canonicalize method."""
        cache = downloaders.LambdaResourceCache(
            canonicalizer=lambda x: x, acquirer=lambda x: x
        )
        self.assertEqual(
            cache.canonicalize("foo.bar"), "foo.bar", "Canonicalization failed."
        )

    def test_acquire(self):
        """Test the acquire method."""
        cache = downloaders.LambdaResourceCache(
            canonicalizer=lambda x: x, acquirer=lambda x: x
        )
        self.assertEqual(cache.acquire("foo.bar"), "foo.bar", "Acquisition failed.")

    def test_store_with_root(self):
        """Test the store method."""
        cache = downloaders.LambdaResourceCache(
            canonicalizer=lambda x: x, acquirer=lambda x: x, root=self.test_temp_dir
        )
        canonical = cache.canonicalize("foo.bar")
        full_path = cache.full_path(canonical)
        contents = "contents"
        cache.store(contents, full_path)
        self.assertTrue(os.path.exists(full_path), "Store failed to write a file.")
        with open(full_path, "r", encoding=constants.TEXT_ENCODING) as file:
            self.assertEqual(
                file.read(), contents, "Contents of stored file are incorrect."
            )

    def test_cache(self):
        """Test the cache method."""
        cache = downloaders.LambdaResourceCache(
            canonicalizer=lambda x: x, acquirer=lambda x: x, root=self.test_temp_dir
        )
        resource = "foo.bar"
        full_path = cache.cache(resource)
        self.assertTrue(os.path.exists(full_path), "Cache failed to write a file.")
        with open(full_path, "r", encoding=constants.TEXT_ENCODING) as file:
            self.assertEqual(
                file.read(), resource, "Contents of stored file are incorrect."
            )
        if os.path.exists(full_path):
            os.unlink(full_path)  # Remove the file or link

    def test_get(self):
        """Test the get method."""
        cache = downloaders.LambdaResourceCache(
            canonicalizer=lambda x: x, acquirer=lambda x: x, root=self.test_temp_dir
        )
        resource = "foo.bar"
        full_path = cache.cache(resource)
        self.assertEqual(
            cache.get(resource), resource, "Get failed to return the correct contents."
        )
        self.assertTrue(os.path.exists(full_path), "Get failed to write a file.")
        if os.path.exists(full_path):
            os.unlink(full_path)  # Remove the file or link

    def test_clear(self):
        """Test the clear method."""
        cache = downloaders.LambdaResourceCache(
            canonicalizer=lambda x: x, acquirer=lambda x: x, root=self.test_temp_dir
        )
        resource = "foo.bar"
        full_path = cache.cache(resource)
        self.assertTrue(os.path.exists(full_path), "Cache failed to write a file.")
        cache.clear()
        self.assertFalse(os.path.exists(full_path), "Clear failed to remove the file.")


class TestUrlResourceCache(test_utils.TestCaseWithData):

    def test_instantiation(self):
        """Test instantiating a LocalTreeReader with no parameters."""
        try:
            cache = downloaders.UrlResourceCache()
            self.assertIsInstance(
                cache,
                downloaders.UrlResourceCache,
                "UrlResourceCache instance was not created correctly.",
            )
            self.assertEqual(cache.root, constants.CACHE_ROOT)
        except Exception as e:
            self.fail(f"Instantiation of UrlResourceCache failed: {e}")

    def test_instantiation_with_root(self):
        """Test instantiating a LocalTreeReader with a root parameter."""
        try:
            cache = downloaders.UrlResourceCache(root=self.test_temp_dir)
            self.assertIsInstance(
                cache,
                downloaders.UrlResourceCache,
                "UrlResourceCache instance was not created correctly.",
            )
            self.assertEqual(cache.root, self.test_temp_dir)
        except Exception as e:
            self.fail(f"Instantiation of UrlResourceCache failed: {e}")

    def test_full_path(self):
        """Test the full_path method."""
        cache = downloaders.UrlResourceCache()
        self.assertEqual(
            cache.full_path("foo.bar"),
            os.path.join(constants.CACHE_ROOT, "foo.bar"),
            "Full path failed.",
        )

    def test_ensure(self):
        """Test the ensure method."""
        cache = downloaders.UrlResourceCache(root=self.test_temp_dir)

        full_path = cache.full_path("foo.bar")
        if os.path.exists(full_path):
            os.unlink(full_path)  # Remove the file.
        file_exists, path = cache.ensure("foo.bar")
        self.assertFalse(file_exists, "File should not exist.")
        self.assertEqual(path, full_path, "Path is correct.")

        with open(full_path, "w", encoding=constants.TEXT_ENCODING) as file:
            file.write("contents")
        file_exists, path = cache.ensure("foo.bar")
        self.assertTrue(file_exists, "File should exist.")
        self.assertEqual(path, full_path, "Path is correct.")
        if os.path.exists(full_path):
            os.unlink(full_path)  # Remove the file.

    def test_canonicalize(self):
        """Test the canonicalize method."""
        cache = downloaders.UrlResourceCache()
        self.assertEqual(
            cache.canonicalize("foo.bar"),
            downloaders.filename_from_url("foo.bar"),
            "Canonicalization failed.",
        )

    @patch("lcats.gatherers.downloaders.requests.get")
    def test_acquire(self, mock_get):
        """Test the acquire method."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Mocked page content"
        mock_get.return_value = mock_response

        resource = "http://example.com"
        cache = downloaders.UrlResourceCache()
        self.assertEqual(
            cache.acquire(resource), mock_response.text, "Acquisition failed."
        )
        mock_get.assert_called_once_with(resource, timeout=10)

    @patch("lcats.gatherers.downloaders.requests.get")
    def test_store_with_root(self, mock_get):
        """Test the store method."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Mocked page content"
        mock_get.return_value = mock_response

        cache = downloaders.UrlResourceCache(root=self.test_temp_dir)
        resource = "http://example.com"
        canonical = cache.canonicalize(resource)
        full_path = cache.full_path(canonical)

        contents = "contents"
        cache.store(contents, full_path)
        self.assertTrue(os.path.exists(full_path), "Store failed to write a file.")
        with open(full_path, "r", encoding=constants.TEXT_ENCODING) as file:
            self.assertEqual(
                file.read(),
                mock_response.text,
                "Contents of stored file are incorrect.",
            )
        if os.path.exists(full_path):
            os.unlink(full_path)  # Remove the file

    @patch("lcats.gatherers.downloaders.requests.get")
    def test_cache(self, mock_get):
        """Test the cache method."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Mocked page content"
        mock_get.return_value = mock_response

        cache = downloaders.UrlResourceCache(root=self.test_temp_dir)
        resource = "http://example.com"
        full_path = cache.cache(resource)
        self.assertTrue(os.path.exists(full_path), "Cache failed to write a file.")
        with open(full_path, "r", encoding=constants.TEXT_ENCODING) as file:
            self.assertEqual(
                file.read(),
                mock_response.text,
                "Contents of stored file are incorrect.",
            )
        if os.path.exists(full_path):
            os.unlink(full_path)

    @patch("lcats.gatherers.downloaders.requests.get")
    def test_get(self, mock_get):
        """Test the get method."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Mocked page content"
        mock_get.return_value = mock_response

        cache = downloaders.UrlResourceCache(root=self.test_temp_dir)
        resource = "http://example.com"
        full_path = cache.cache(resource)
        self.assertEqual(
            cache.get(resource),
            mock_response.text,
            "Get failed to return the correct contents.",
        )
        self.assertTrue(os.path.exists(full_path), "Get failed to write a file.")
        if os.path.exists(full_path):
            os.unlink(full_path)  # Remove the file

    def test_clear(self):
        """Test the clear method."""
        cache = downloaders.UrlResourceCache(root=self.test_temp_dir)
        resource = "http://example.com"
        full_path = cache.cache(resource)
        self.assertTrue(os.path.exists(full_path), "Cache failed to write a file.")
        cache.clear()
        self.assertFalse(os.path.exists(full_path), "Clear failed to remove the file.")


if __name__ == "__main__":
    unittest.main()
