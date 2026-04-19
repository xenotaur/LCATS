"""Tests for the downloaders module."""

import json
import os
import requests

import unittest
from unittest.mock import patch, Mock

from lcats import constants
from lcats.utils import test_utils
from lcats.gatherers import downloaders
from lcats.utils import capture
from lcats.utils import env
from lcats.utils import names


class TestLoadPage(unittest.TestCase):
    """Tests for the load_page function."""

    @patch("lcats.gatherers.downloaders.requests.get")
    def test_load_page_success_utf8(self, mock_get):
        """Test load_page with content that decodes using the preferred encoding."""
        mock_response = Mock()
        mock_response.content = "Mocked page content — with dash".encode("utf-8")
        mock_response.raise_for_status = Mock()
        mock_response.apparent_encoding = None
        mock_response.encoding = None
        mock_get.return_value = mock_response

        with capture.suppress_output():
            result = downloaders.load_page("http://example.com")

        self.assertEqual(result, "Mocked page content — with dash")
        mock_get.assert_called_once_with("http://example.com", timeout=10)
        mock_response.raise_for_status.assert_called_once_with()

    @patch("lcats.gatherers.downloaders.requests.get")
    def test_load_page_http_error(self, mock_get):
        """Test load_page propagates HTTP errors from raise_for_status."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404 Client Error"
        )
        mock_get.return_value = mock_response

        with self.assertRaises(requests.exceptions.HTTPError):
            with capture.suppress_output():
                downloaders.load_page("http://example.com")

        mock_get.assert_called_once_with("http://example.com", timeout=10)
        mock_response.raise_for_status.assert_called_once_with()

    @patch("lcats.gatherers.downloaders.requests.get")
    def test_load_page_timeout(self, mock_get):
        """Test load_page propagates timeout exceptions from requests.get."""
        mock_get.side_effect = requests.exceptions.Timeout

        with self.assertRaises(requests.exceptions.Timeout):
            with capture.suppress_output():
                downloaders.load_page("http://example.com")

        mock_get.assert_called_once_with("http://example.com", timeout=10)

    @patch("lcats.gatherers.downloaders.requests.get")
    def test_load_page_falls_back_to_apparent_encoding(self, mock_get):
        """Test load_page falls back to apparent_encoding when preferred decoding fails."""
        text = "café"
        raw = text.encode("cp1252")

        mock_response = Mock()
        mock_response.content = raw
        mock_response.raise_for_status = Mock()
        mock_response.apparent_encoding = "cp1252"
        mock_response.encoding = None
        mock_get.return_value = mock_response

        with capture.suppress_output():
            result = downloaders.load_page("http://example.com")

        self.assertEqual(result, text)
        mock_get.assert_called_once_with("http://example.com", timeout=10)
        mock_response.raise_for_status.assert_called_once_with()

    @patch("lcats.gatherers.downloaders.requests.get")
    def test_load_page_falls_back_to_response_encoding(self, mock_get):
        """Test load_page falls back to response.encoding when apparent_encoding is unavailable."""
        text = "café"
        raw = text.encode("cp1252")

        mock_response = Mock()
        mock_response.content = raw
        mock_response.raise_for_status = Mock()
        mock_response.apparent_encoding = None
        mock_response.encoding = "cp1252"
        mock_get.return_value = mock_response

        with capture.suppress_output():
            result = downloaders.load_page("http://example.com")

        self.assertEqual(result, text)
        mock_get.assert_called_once_with("http://example.com", timeout=10)
        mock_response.raise_for_status.assert_called_once_with()

    @patch("lcats.gatherers.downloaders.requests.get")
    def test_load_page_raises_when_no_encoding_can_be_determined(self, mock_get):
        """Test load_page raises UnicodeDecodeError if decoding fails and no fallback encoding exists."""
        mock_response = Mock()
        mock_response.content = b"\x81"
        mock_response.raise_for_status = Mock()
        mock_response.apparent_encoding = None
        mock_response.encoding = None
        mock_get.return_value = mock_response

        with self.assertRaises(UnicodeDecodeError):
            with capture.suppress_output():
                downloaders.load_page("http://example.com")

        mock_get.assert_called_once_with("http://example.com", timeout=10)
        mock_response.raise_for_status.assert_called_once_with()

    @patch("lcats.gatherers.downloaders.requests.get")
    def test_load_page_uses_custom_preferred_encoding(self, mock_get):
        """Test load_page uses a caller-supplied preferred encoding."""
        text = "café"
        raw = text.encode("cp1252")

        mock_response = Mock()
        mock_response.content = raw
        mock_response.raise_for_status = Mock()
        mock_response.apparent_encoding = None
        mock_response.encoding = None
        mock_get.return_value = mock_response

        with capture.suppress_output():
            result = downloaders.load_page(
                "http://example.com", preferred_encoding="cp1252"
            )

        self.assertEqual(result, text)
        mock_get.assert_called_once_with("http://example.com", timeout=10)
        mock_response.raise_for_status.assert_called_once_with()

    @patch("lcats.gatherers.downloaders.requests.get")
    def test_load_page_prefers_apparent_encoding_over_response_encoding(self, mock_get):
        """Test load_page prefers apparent_encoding over response.encoding."""
        raw = "Price €10".encode("cp1252")

        mock_response = Mock()
        mock_response.content = raw
        mock_response.raise_for_status = Mock()
        mock_response.apparent_encoding = "cp1252"
        mock_response.encoding = "iso-8859-1"
        mock_get.return_value = mock_response

        with capture.suppress_output():
            result = downloaders.load_page("http://example.com")

        self.assertEqual(result, "Price €10")
        mock_get.assert_called_once_with("http://example.com", timeout=10)
        mock_response.raise_for_status.assert_called_once_with()


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
        file_name = "foo.bar"
        self.assertEqual(
            cache.full_path(file_name),
            os.path.join(env.cache_resources_dir(), file_name),
            "Full path failed.",
        )

    def test_ensure(self):
        """Test the ensure method."""
        cache = downloaders.LambdaResourceCache(
            canonicalizer=lambda x: x, acquirer=lambda x: x, root=self.test_temp_dir
        )
        file_name = "bar.baz"
        full_path = cache.full_path(file_name)
        if os.path.exists(full_path):
            os.unlink(full_path)  # Remove the file or link
        with capture.suppress_output():
            file_exists, path = cache.ensure(file_name)
        self.assertFalse(file_exists, "File should not exist.")
        self.assertEqual(path, full_path, "Path is correct.")

        with open(full_path, "w", encoding=constants.TEXT_ENCODING) as file:
            file.write("contents")
        with capture.suppress_output():
            file_exists, path = cache.ensure(file_name)
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
        file_name = "baz.qux"
        with capture.suppress_output():
            acquired = cache.acquire(file_name)
        self.assertEqual(acquired, file_name, "Acquisition failed.")

    def test_store_with_root(self):
        """Test the store method."""
        cache = downloaders.LambdaResourceCache(
            canonicalizer=lambda x: x, acquirer=lambda x: x, root=self.test_temp_dir
        )
        file_name = "qux.hef"
        canonical = cache.canonicalize(file_name)
        full_path = cache.full_path(canonical)
        contents = "contents"
        with capture.suppress_output():
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
        rezource = "hef.alu"
        with capture.suppress_output():
            full_path = cache.cache(rezource)
        self.assertTrue(os.path.exists(full_path), "Cache failed to write a file.")
        with open(full_path, "r", encoding=constants.TEXT_ENCODING) as file:
            self.assertEqual(
                file.read(), rezource, "Contents of stored file are incorrect."
            )
        if os.path.exists(full_path):
            os.unlink(full_path)  # Remove the file or link

    def test_get(self):
        """Test the get method."""
        cache = downloaders.LambdaResourceCache(
            canonicalizer=lambda x: x, acquirer=lambda x: x, root=self.test_temp_dir
        )
        rezource = "alu.ump"
        with capture.suppress_output():
            full_path = cache.cache(rezource)
            got_stuff = cache.get(rezource)
        self.assertEqual(
            got_stuff, rezource, "Get failed to return the correct contents."
        )
        self.assertTrue(os.path.exists(full_path), "Get failed to write a file.")
        if os.path.exists(full_path):
            os.unlink(full_path)  # Remove the file or link

    def test_clear(self):
        """Test the clear method."""
        cache = downloaders.LambdaResourceCache(
            canonicalizer=lambda x: x, acquirer=lambda x: x, root=self.test_temp_dir
        )
        rezource = "ump.kin"
        with capture.suppress_output():
            full_path = cache.cache(rezource)
        self.assertTrue(os.path.exists(full_path), "Cache failed to write a file.")
        with capture.suppress_output():
            cache.clear()
        self.assertFalse(os.path.exists(full_path), "Clear failed to remove the file.")


class TestUrlResourceCache(test_utils.TestCaseWithData):
    """Tests for the UrlResourceCache class."""

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
            os.unlink(full_path)

        with capture.suppress_output():
            file_exists, path = cache.ensure("foo.bar")
        self.assertFalse(file_exists, "File should not exist.")
        self.assertEqual(path, full_path, "Path is correct.")

        with open(full_path, "w", encoding=constants.TEXT_ENCODING) as file:
            file.write("contents")

        with capture.suppress_output():
            file_exists, path = cache.ensure("foo.bar")
        self.assertTrue(file_exists, "File should exist.")
        self.assertEqual(path, full_path, "Path is correct.")

        if os.path.exists(full_path):
            os.unlink(full_path)

    def test_canonicalize(self):
        """Test the canonicalize method."""
        cache = downloaders.UrlResourceCache()
        self.assertEqual(
            cache.canonicalize("foo.bar"),
            names.url_to_filename("foo.bar"),
            "Canonicalization failed.",
        )

    @patch("lcats.gatherers.downloaders.requests.get")
    def test_acquire(self, mock_get):
        """Test the acquire method."""
        mock_response = Mock()
        mock_response.content = "Mocked page content".encode("utf-8")
        mock_response.raise_for_status = Mock()
        mock_response.apparent_encoding = None
        mock_response.encoding = None
        mock_get.return_value = mock_response

        resource = "http://example.com"
        cache = downloaders.UrlResourceCache()

        with capture.suppress_output():
            acquired = cache.acquire(resource)

        self.assertEqual(acquired, "Mocked page content", "Acquisition failed.")
        mock_get.assert_called_once_with(resource, timeout=10)
        mock_response.raise_for_status.assert_called_once_with()

    @patch("lcats.gatherers.downloaders.requests.get")
    def test_store_with_root(self, mock_get):
        """Test the store method."""
        mock_response = Mock()
        mock_response.content = "Mocked page content".encode("utf-8")
        mock_response.raise_for_status = Mock()
        mock_response.apparent_encoding = None
        mock_response.encoding = None
        mock_get.return_value = mock_response

        cache = downloaders.UrlResourceCache(root=self.test_temp_dir)
        resource = "http://example.com"
        canonical = cache.canonicalize(resource)
        full_path = cache.full_path(canonical)

        with capture.suppress_output():
            cache.store(resource, full_path)

        self.assertTrue(os.path.exists(full_path), "Store failed to write a file.")
        with open(full_path, "r", encoding=constants.TEXT_ENCODING) as file:
            self.assertEqual(
                file.read(),
                "Mocked page content",
                "Contents of stored file are incorrect.",
            )

        mock_get.assert_called_once_with(resource, timeout=10)
        mock_response.raise_for_status.assert_called_once_with()

        if os.path.exists(full_path):
            os.unlink(full_path)

    @patch("lcats.gatherers.downloaders.requests.get")
    def test_cache(self, mock_get):
        """Test the cache method."""
        mock_response = Mock()
        mock_response.content = "Mocked page content".encode("utf-8")
        mock_response.raise_for_status = Mock()
        mock_response.apparent_encoding = None
        mock_response.encoding = None
        mock_get.return_value = mock_response

        cache = downloaders.UrlResourceCache(root=self.test_temp_dir)
        resource = "http://example.com"

        with capture.suppress_output():
            full_path = cache.cache(resource)

        self.assertTrue(os.path.exists(full_path), "Cache failed to write a file.")
        with open(full_path, "r", encoding=constants.TEXT_ENCODING) as file:
            self.assertEqual(
                file.read(),
                "Mocked page content",
                "Contents of stored file are incorrect.",
            )

        mock_get.assert_called_once_with(resource, timeout=10)
        mock_response.raise_for_status.assert_called_once_with()

        if os.path.exists(full_path):
            os.unlink(full_path)

    @patch("lcats.gatherers.downloaders.requests.get")
    def test_get(self, mock_get):
        """Test the get method."""
        mock_response = Mock()
        mock_response.content = "Mocked page content".encode("utf-8")
        mock_response.raise_for_status = Mock()
        mock_response.apparent_encoding = None
        mock_response.encoding = None
        mock_get.return_value = mock_response

        cache = downloaders.UrlResourceCache(root=self.test_temp_dir)
        resource = "http://example.com"

        with capture.suppress_output():
            full_path = cache.cache(resource)
            cache_get = cache.get(resource)

        self.assertEqual(
            cache_get,
            "Mocked page content",
            "Get failed to return the correct contents.",
        )
        self.assertTrue(os.path.exists(full_path), "Get failed to write a file.")

        mock_get.assert_called_once_with(resource, timeout=10)
        mock_response.raise_for_status.assert_called_once_with()

        if os.path.exists(full_path):
            os.unlink(full_path)

    @patch("lcats.gatherers.downloaders.requests.get")
    def test_clear(self, mock_get):
        """Test the clear method."""
        mock_response = Mock()
        mock_response.content = "Mocked page content".encode("utf-8")
        mock_response.raise_for_status = Mock()
        mock_response.apparent_encoding = None
        mock_response.encoding = None
        mock_get.return_value = mock_response

        cache = downloaders.UrlResourceCache(root=self.test_temp_dir)
        resource = "http://example.com"

        with capture.suppress_output():
            full_path = cache.cache(resource)

        self.assertTrue(os.path.exists(full_path), "Cache failed to write a file.")

        with capture.suppress_output():
            cache.clear()

        self.assertFalse(os.path.exists(full_path), "Clear failed to remove the file.")

        mock_get.assert_called_once_with(resource, timeout=10)
        mock_response.raise_for_status.assert_called_once_with()


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
        with open(os.path.join(subdir, "file.txt"), "w", encoding="utf-8") as f:
            f.write("content")

        with capture.suppress_output():
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
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("content")

        with patch(
            "lcats.gatherers.downloaders.os.unlink",
            side_effect=OSError("Permission denied"),
        ):
            # Should not raise even when deletion fails
            with capture.suppress_output():
                cache.clear()

    def test_clear_nonexistent_directory(self):
        """Test clear when the root directory does not exist."""
        cache = downloaders.LambdaResourceCache(
            canonicalizer=lambda x: x,
            acquirer=lambda x: x,
            root=os.path.join(self.test_temp_dir, "nonexistent"),
        )
        # Should complete without raising
        with capture.suppress_output():
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
        file_exists, _ = self.gatherer.ensure("testfile")

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
        with capture.suppress_output():
            result = self.gatherer.resource("any_key")
        self.assertEqual(result, "hello")

    def test_download_creates_json_file(self):
        """Test that download writes a structured JSON file."""
        self.gatherer.resource_cache = self._make_lambda_cache()

        def handler(contents):
            del contents
            return "Test Name", "Test body text", {"key": "value"}

        with capture.suppress_output():
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
            del contents
            return "Test Name", None, {}

        with self.assertRaises(ValueError):
            with capture.suppress_output():
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
            del contents
            handler_called[0] = True
            return "New Name", "New body", {}

        self.gatherer.resource_cache = self._make_lambda_cache()
        with capture.suppress_output():
            self.gatherer.download("testfile", "test_resource", handler)

        self.assertFalse(handler_called[0])
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["name"], "Original")

    def test_download_force_overwrites(self):
        """Test that download with force=True overwrites an existing file."""
        self.gatherer.resource_cache = self._make_lambda_cache()

        def handler(contents):
            del contents
            return "Name", "Body", {}

        with capture.suppress_output():
            self.gatherer.download("testfile", "test_resource", handler)

        def handler2(contents):
            del contents
            return "New Name", "New Body", {}

        with capture.suppress_output():
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
        with capture.suppress_output():
            self.gatherer.clear()
        self.assertFalse(os.path.exists(self.gatherer.path))

    def test_clear_nonexistent_path(self):
        """Test that clear on a non-existent path does not raise."""
        self.assertFalse(os.path.exists(self.gatherer.path))
        with capture.suppress_output():
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
            with capture.suppress_output():
                self.gatherer.clear()

    def test_gather_raises_not_implemented(self):
        """Test that gather raises NotImplementedError."""
        with self.assertRaises(NotImplementedError):
            self.gatherer.gather(None)


if __name__ == "__main__":
    unittest.main()
