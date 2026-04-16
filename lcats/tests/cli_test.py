"""Tests for the cli command-line interpreter module."""

import unittest
from unittest.mock import patch

import parameterized

from lcats import cli


class TestCli(unittest.TestCase):

    def test_usage(self):
        self.assertEqual(cli.usage(), cli.USAGE_MESSAGE)

    def test_dispatch_info(self):
        """Ensure the dispatcher function is working."""
        result, response = cli.dispatch("info", [])
        self.assertEqual(result, "LCATS is a literary case based reasoning system.")
        self.assertEqual(response, 0)

        result, response = cli.dispatch("info", ["extra", "args"])
        self.assertEqual(result, "LCATS is a literary case based reasoning system.")
        self.assertEqual(response, 0)

    @patch("lcats.gatherers.main.run")
    def test_dispatch_gather(self, mock_run):
        """Ensure the dispatcher function is working."""
        expected_message = "Gathering complete."
        expected_status = 0
        mock_run.return_value = (expected_message, expected_status)

        actual_message, actual_status = cli.dispatch("gather", [True])
        self.assertEqual(expected_message, actual_message)
        self.assertEqual(expected_status, actual_status)

    @patch("lcats.analysis.corpus_survey.main")
    def test_dispatch_survey(self, mock_main):
        """Ensure the survey command delegates to corpus_survey.main."""
        mock_main.return_value = 0

        actual_message, actual_status = cli.dispatch("survey", ["corpora/sherlock"])
        self.assertEqual("", actual_message)
        self.assertEqual(0, actual_status)
        mock_main.assert_called_once_with(["corpora/sherlock"])

    @parameterized.parameterized.expand(
        [
            ("index", "Indexing data files is not yet implemented."),
            ("advise", "Getting advice from LCATS is not yet implemented."),
            ("eval", "Evaluating LCATS is not yet implemented."),
        ]
    )
    def test_dispatch_unimplemented(self, command, message):
        """Ensure the dispatcher function rejects unimplemented commands."""
        result, response = cli.dispatch(command, [])
        self.assertEqual(result, message)
        self.assertEqual(response, 1)

    def test_dispatch_unknown(self):
        """Ensure the dispatcher function rejects unknown commands."""
        result, response = cli.dispatch("unknown", [])
        self.assertEqual(result, "Unknown command: unknown")
        self.assertEqual(response, 1)

    @patch("sys.argv", ["lcats", "survey", "corpora/sherlock"])
    @patch("lcats.analysis.corpus_survey.main")
    def test_main_survey_invocation(self, mock_main):
        """Ensure CLI main routes survey arguments via argparse."""
        mock_main.return_value = 0

        with self.assertRaises(SystemExit) as cm:
            cli.main()

        self.assertEqual(0, cm.exception.code)
        mock_main.assert_called_once_with(["corpora/sherlock"])

    @patch("sys.argv", ["lcats", "--help"])
    def test_main_help_flag_exits(self):
        """Ensure argparse handles the built-in help flag."""
        with self.assertRaises(SystemExit) as cm:
            cli.main()
        self.assertEqual(0, cm.exception.code)


if __name__ == "__main__":
    unittest.main()
