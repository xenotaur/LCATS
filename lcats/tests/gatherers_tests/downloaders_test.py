"""Tests for the downloaders module."""

# Assuming convert_encoding is in this module
from lcats.gatherers import downloaders
import json
import os
import unittest
from unittest.mock import patch, Mock
from lcats import constants
from lcats import test_utils
from lcats.utils import env

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

    def test_detect_encoding_latin1_bytes(self):
        """ "Text in Latin-1 encoding."""
        data = "quanto lhe é possive".encode("iso-8859-1")
        enc = downloaders.detect_encoding(data)
        # These cannot be reliably distinguished at the byte level as
        # both encodings are valid for the same byte sequence.
        self.assertIn(enc.upper(), {"ISO-8859-1", "WINDOWS-1250", "WINDOWS-1252"})

    def test_detect_encoding_cp1252_distinguishing(self):
        # 0x80 is € in cp1252, control in iso-8859-1
        data = b"Price: \x80 10"
        enc = downloaders.detect_encoding(data)
        self.assertIn(enc.upper(), {"WINDOWS-1250", "WINDOWS-1252"})

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
            self.assertEqual(cache.root, env.cache_resources_dir())
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
            os.path.join(env.cache_resources_dir(), "foo.bar"),
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
            self.assertEqual(cache.root, env.cache_resources_dir())
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
            os.path.join(env.cache_resources_dir(), "foo.bar"),
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


class TestResourceCacheClearEdgeCases(test_utils.TestCaseWithData):
    """Tests for edge cases in ResourceCache.clear not covered by existing tests."""

    def test_clear_with_subdirectory(self):
        """Test clear when the cache root contains a subdirectory."""
        cache = downloaders.LambdaResourceCache(
            canonicalizer=lambda x: x,
            acquirer=lambda x: x,
            root=self.test_temp_dir,
        )
        subdir = os.path.join(self.test_temp_dir, "subdir")
        os.makedirs(subdir)
        with open(os.path.join(subdir, "file.txt"), "w") as f:
            f.write("content")

        cache.clear()
        self.assertFalse(os.path.exists(subdir))

    def test_clear_exception_handling(self):
        """Test clear when an exception is raised during deletion."""
        cache = downloaders.LambdaResourceCache(
            canonicalizer=lambda x: x,
            acquirer=lambda x: x,
            root=self.test_temp_dir,
        )
        file_path = os.path.join(self.test_temp_dir, "test.txt")
        with open(file_path, "w") as f:
            f.write("content")

        with patch(
            "lcats.gatherers.downloaders.os.unlink",
            side_effect=OSError("Permission denied"),
        ):
            # Should not raise even when deletion fails
            cache.clear()

    def test_clear_nonexistent_directory(self):
        """Test clear when the root directory does not exist."""
        cache = downloaders.LambdaResourceCache(
            canonicalizer=lambda x: x,
            acquirer=lambda x: x,
            root=os.path.join(self.test_temp_dir, "nonexistent"),
        )
        # Should complete without raising
        cache.clear()


class TestDataGatherer(test_utils.TestCaseWithData):
    """Tests for the DataGatherer class."""

    def setUp(self):
        super().setUp()
        self.gatherer = downloaders.DataGatherer(
            name="test_gatherer",
            root=self.test_temp_dir,
            cache=self.test_temp_dir,
        )

    def _make_lambda_cache(self, content="resource content"):
        """Return a LambdaResourceCache with a fixed acquirer for testing."""
        return downloaders.LambdaResourceCache(
            canonicalizer=lambda x: x,
            acquirer=lambda x: content,
            root=self.test_temp_dir,
        )

    def test_instantiation(self):
        """Test that DataGatherer initialises correctly."""
        self.assertIsInstance(self.gatherer, downloaders.DataGatherer)
        self.assertEqual(self.gatherer.name, "test_gatherer")
        self.assertEqual(self.gatherer.root, self.test_temp_dir)
        self.assertEqual(self.gatherer.cache, self.test_temp_dir)
        self.assertEqual(self.gatherer.suffix, ".json")
        self.assertIsNone(self.gatherer.license)
        self.assertIsNone(self.gatherer.description)
        self.assertEqual(self.gatherer.resources, {})
        self.assertEqual(self.gatherer.downloads, {})

    def test_instantiation_with_optional_args(self):
        """Test DataGatherer with description, suffix and license."""
        gatherer = downloaders.DataGatherer(
            name="test_gatherer",
            description="A test gatherer",
            root=self.test_temp_dir,
            cache=self.test_temp_dir,
            suffix=".txt",
            license="MIT License",
        )
        self.assertEqual(gatherer.description, "A test gatherer")
        self.assertEqual(gatherer.suffix, ".txt")
        self.assertEqual(gatherer.license, "MIT License")

    def test_path_property(self):
        """Test that path returns root joined with name."""
        expected = os.path.join(self.test_temp_dir, "test_gatherer")
        self.assertEqual(self.gatherer.path, expected)

    def test_ensure_creates_directories_and_license(self):
        """Test that ensure creates the directory tree and writes a license file."""
        file_exists, file_path = self.gatherer.ensure("testfile")

        self.assertFalse(file_exists)
        self.assertTrue(os.path.isdir(self.gatherer.path))
        license_path = os.path.join(self.gatherer.path, constants.LICENSE_FILE)
        self.assertTrue(os.path.exists(license_path))
        with open(license_path, encoding="utf-8") as f:
            self.assertEqual(f.read(), "No license provided.")

    def test_ensure_writes_custom_license(self):
        """Test that ensure writes the provided license text."""
        gatherer = downloaders.DataGatherer(
            name="licensed",
            root=self.test_temp_dir,
            cache=self.test_temp_dir,
            license="MIT License",
        )
        gatherer.ensure("testfile")
        license_path = os.path.join(gatherer.path, constants.LICENSE_FILE)
        with open(license_path, encoding="utf-8") as f:
            self.assertEqual(f.read(), "MIT License")

    def test_ensure_returns_true_when_file_exists(self):
        """Test that ensure returns True for an already-present file."""
        self.gatherer.ensure("testfile")
        file_path = os.path.join(self.gatherer.path, "testfile" + self.gatherer.suffix)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("content")

        file_exists, returned_path = self.gatherer.ensure("testfile")
        self.assertTrue(file_exists)
        self.assertEqual(returned_path, file_path)

    def test_resource_delegates_to_cache(self):
        """Test that resource returns content from the resource cache."""
        self.gatherer.resource_cache = self._make_lambda_cache("hello")
        result = self.gatherer.resource("any_key")
        self.assertEqual(result, "hello")

    def test_download_creates_json_file(self):
        """Test that download writes a structured JSON file."""
        self.gatherer.resource_cache = self._make_lambda_cache()

        def handler(contents):
            return "Test Name", "Test body text", {"key": "value"}

        self.gatherer.download("testfile", "test_resource", handler)

        file_path = os.path.join(self.gatherer.path, "testfile" + self.gatherer.suffix)
        self.assertTrue(os.path.exists(file_path))
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["name"], "Test Name")
        self.assertEqual(data["body"], "Test body text")
        self.assertEqual(data["metadata"], {"key": "value"})
        self.assertIn("testfile", self.gatherer.downloads)

    def test_download_raises_on_none_body(self):
        """Test that download raises ValueError when handler returns None body."""
        self.gatherer.resource_cache = self._make_lambda_cache()

        def handler(contents):
            return "Test Name", None, {}

        with self.assertRaises(ValueError):
            self.gatherer.download("testfile", "test_resource", handler)

    def test_download_skips_existing_file(self):
        """Test that download does not overwrite an existing file."""
        self.gatherer.ensure("testfile")
        file_path = os.path.join(self.gatherer.path, "testfile" + self.gatherer.suffix)
        original_data = {"name": "Original", "body": "original", "metadata": {}}
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(original_data, f)

        handler_called = [False]

        def handler(contents):
            handler_called[0] = True
            return "New Name", "New body", {}

        self.gatherer.resource_cache = self._make_lambda_cache()
        self.gatherer.download("testfile", "test_resource", handler)

        self.assertFalse(handler_called[0])
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["name"], "Original")

    def test_download_force_overwrites(self):
        """Test that download with force=True overwrites an existing file."""
        self.gatherer.resource_cache = self._make_lambda_cache()

        def handler(contents):
            return "Name", "Body", {}

        self.gatherer.download("testfile", "test_resource", handler)

        def handler2(contents):
            return "New Name", "New Body", {}

        self.gatherer.download("testfile", "test_resource", handler2, force=True)

        file_path = os.path.join(self.gatherer.path, "testfile" + self.gatherer.suffix)
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["name"], "New Name")

    def test_get_returns_existing_file(self):
        """Test that get reads and returns an existing JSON file."""
        self.gatherer.ensure("testfile")
        file_path = os.path.join(self.gatherer.path, "testfile" + self.gatherer.suffix)
        saved = {"name": "Test", "body": "content", "metadata": {}}
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(saved, f)

        result = self.gatherer.get("testfile", None)
        self.assertEqual(result, saved)

    def test_clear_removes_path(self):
        """Test that clear removes the gatherer's directory."""
        self.gatherer.ensure("testfile")
        self.assertTrue(os.path.isdir(self.gatherer.path))
        self.gatherer.clear()
        self.assertFalse(os.path.exists(self.gatherer.path))

    def test_clear_nonexistent_path(self):
        """Test that clear on a non-existent path does not raise."""
        self.assertFalse(os.path.exists(self.gatherer.path))
        self.gatherer.clear()

    def test_ensure_creates_root_when_missing(self):
        """Test that ensure creates the root directory when it does not exist."""
        new_root = os.path.join(self.test_temp_dir, "new_root")
        gatherer = downloaders.DataGatherer(
            name="sub", root=new_root, cache=self.test_temp_dir
        )
        self.assertFalse(os.path.exists(new_root))
        gatherer.ensure("testfile")
        self.assertTrue(os.path.isdir(gatherer.path))

    def test_get_when_file_missing_delegates_to_download(self):
        """Test that get calls download when the file does not yet exist."""
        with patch.object(self.gatherer, "download") as mock_download:
            self.gatherer.get("missing", "some_resource")
            mock_download.assert_called_once()

    def test_clear_exception_during_removal(self):
        """Test that clear catches exceptions raised while removing items."""
        self.gatherer.ensure("testfile")
        with patch(
            "lcats.gatherers.downloaders.shutil.rmtree",
            side_effect=OSError("Permission denied"),
        ):
            # Should not propagate the exception
            self.gatherer.clear()

    def test_gather_raises_not_implemented(self):
        """Test that gather raises NotImplementedError."""
        with self.assertRaises(NotImplementedError):
            self.gatherer.gather(None)


if __name__ == "__main__":
    unittest.main()
