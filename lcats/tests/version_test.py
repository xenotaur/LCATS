"""Tests for the lcats.version module."""

import importlib.metadata
import unittest
from unittest import mock

from lcats import version


class TestVersion(unittest.TestCase):

    def test_get_installed_version_returns_metadata_version(self):
        with mock.patch(
            "importlib.metadata.version", return_value="1.2.3"
        ) as mock_version:
            result = version.get_installed_version()
        self.assertEqual("1.2.3", result)
        mock_version.assert_called_once_with(version.DISTRIBUTION_NAME)

    def test_get_installed_version_returns_none_when_not_installed(self):
        with mock.patch(
            "importlib.metadata.version",
            side_effect=importlib.metadata.PackageNotFoundError,
        ):
            result = version.get_installed_version()
        self.assertIsNone(result)

    def test_format_cli_version_includes_version_number(self):
        with mock.patch("lcats.version.get_installed_version", return_value="1.2.3"):
            result = version.format_cli_version()
        self.assertEqual("lcats 1.2.3", result)

    def test_format_cli_version_reports_unknown_when_not_installed(self):
        with mock.patch("lcats.version.get_installed_version", return_value=None):
            result = version.format_cli_version()
        self.assertEqual("lcats unknown", result)


if __name__ == "__main__":
    unittest.main()
