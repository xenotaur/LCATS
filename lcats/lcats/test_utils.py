"""Unit test utilities for the lcats package."""

import os
import shutil
import tempfile
import unittest


class TestCaseWithData(unittest.TestCase):

    def setUp(self):
        """Find the local test data directory, and create a temp dir."""
        # Assumes tests are being run from the root of the workspace.
        self.test_data_dir = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "../tests/data")
        )
        self.test_temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Remove the temporary directory."""
        shutil.rmtree(self.test_temp_dir)

    def get_test_path(self, path=None):
        """Gets a path relative to the test data directory."""
        return os.path.join(self.test_data_dir, path) if path else self.test_data_dir
