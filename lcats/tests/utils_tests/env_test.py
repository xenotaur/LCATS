"""Tests for lcats.utils.env functions."""

import pathlib
import unittest
from unittest.mock import patch

from lcats.utils import env


class TestCacheRoot(unittest.TestCase):
    """Tests for the cache_root function."""

    def test_cache_root_default(self):
        """cache_root returns 'cache' path when LCATS_CACHE_DIR is not set."""
        with patch.dict("os.environ", {}, clear=True):
            result = env.cache_root()
        self.assertEqual(result, pathlib.Path("cache"))

    def test_cache_root_env_override(self):
        """cache_root uses LCATS_CACHE_DIR when set."""
        with patch.dict("os.environ", {"LCATS_CACHE_DIR": "/tmp/my_cache"}):
            result = env.cache_root()
        self.assertEqual(result, pathlib.Path("/tmp/my_cache"))

    def test_cache_root_returns_path(self):
        """cache_root always returns a pathlib.Path instance."""
        self.assertIsInstance(env.cache_root(), pathlib.Path)


class TestCacheResourcesDir(unittest.TestCase):
    """Tests for the cache_resources_dir function."""

    def test_cache_resources_dir_default(self):
        """cache_resources_dir returns 'cache/resources' when LCATS_CACHE_DIR is not set."""
        with patch.dict("os.environ", {}, clear=True):
            result = env.cache_resources_dir()
        self.assertEqual(result, pathlib.Path("cache") / "resources")

    def test_cache_resources_dir_env_override(self):
        """cache_resources_dir uses LCATS_CACHE_DIR to build the resources path."""
        with patch.dict("os.environ", {"LCATS_CACHE_DIR": "/tmp/my_cache"}):
            result = env.cache_resources_dir()
        self.assertEqual(result, pathlib.Path("/tmp/my_cache") / "resources")

    def test_cache_resources_dir_returns_path(self):
        """cache_resources_dir always returns a pathlib.Path instance."""
        self.assertIsInstance(env.cache_resources_dir(), pathlib.Path)


class TestCorporaRoot(unittest.TestCase):
    """Tests for the corpora_root function."""

    def test_corpora_root_default(self):
        """corpora_root returns '../corpora' when LCATS_CORPORA_DIR is not set."""
        with patch.dict("os.environ", {}, clear=True):
            result = env.corpora_root()
        self.assertEqual(result, pathlib.Path("../corpora"))

    def test_corpora_root_env_override(self):
        """corpora_root uses LCATS_CORPORA_DIR when set."""
        with patch.dict("os.environ", {"LCATS_CORPORA_DIR": "/data/corpora"}):
            result = env.corpora_root()
        self.assertEqual(result, pathlib.Path("/data/corpora"))

    def test_corpora_root_returns_path(self):
        """corpora_root always returns a pathlib.Path instance."""
        self.assertIsInstance(env.corpora_root(), pathlib.Path)


class TestDataRoot(unittest.TestCase):
    """Tests for the data_root function."""

    def test_data_root_default(self):
        """data_root returns 'data' when LCATS_DATA_DIR is not set."""
        with patch.dict("os.environ", {}, clear=True):
            result = env.data_root()
        self.assertEqual(result, pathlib.Path("data"))

    def test_data_root_env_override(self):
        """data_root uses LCATS_DATA_DIR when set."""
        with patch.dict("os.environ", {"LCATS_DATA_DIR": "/tmp/my_data"}):
            result = env.data_root()
        self.assertEqual(result, pathlib.Path("/tmp/my_data"))

    def test_data_root_returns_path(self):
        """data_root always returns a pathlib.Path instance."""
        self.assertIsInstance(env.data_root(), pathlib.Path)


if __name__ == "__main__":
    unittest.main()
