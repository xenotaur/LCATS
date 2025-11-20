"""Unit tests for the test_utils module."""

import os
import unittest

from lcats import test_utils


class TestTestCaseWithTestData(test_utils.TestCaseWithData):
    """Ensure the test_utils module works as expected."""

    def test_get_test_path_default(self):
        """Make sure we can locate the test data dir."""
        self.assertEqual(
            self.get_test_path(), os.path.join(os.path.dirname(__file__), "data")
        )

    def test_get_test_path_filename(self):
        """Make sure we can get an example file in the test data dir."""
        self.assertEqual(
            self.get_test_path("example.txt"),
            os.path.join(os.path.dirname(__file__), "data/example.txt"),
        )

    def test_get_test_temp_dir(self):
        """Make sure we can get the temporary directory."""
        self.assertTrue(os.path.exists(self.test_temp_dir))


if __name__ == "__main__":
    unittest.main()
