"""Tests for the cli command-line interpreter module."""

import unittest
from unittest import mock

import parameterized

from lcats import cli
from lcats.utils import capture


class TestCli(unittest.TestCase):

    def test_usage_contains_top_level_help(self):
        usage = cli.usage()
        self.assertIn("usage: lcats", usage)
        self.assertIn("Run 'lcats <command> --help' for more information.", usage)

    def test_dispatch_info(self):
        """Ensure the dispatcher function is working."""
        result, response = cli.dispatch("info", [])
        self.assertEqual(result, "LCATS is a literary case based reasoning system.")
        self.assertEqual(response, 0)

        result, response = cli.dispatch("info", ["extra", "args"])
        self.assertEqual(result, "LCATS is a literary case based reasoning system.")
        self.assertEqual(response, 0)

    @mock.patch("lcats.gatherers.main.run")
    def test_dispatch_gather(self, mock_run):
        """Ensure the gather command is routed through the gather module."""
        expected_message = "Gathering complete."
        expected_status = 0
        mock_run.return_value = (expected_message, expected_status)

        actual_message, actual_status = cli.dispatch(
            "gather", ["--dry-run", "sherlock"]
        )
        self.assertEqual(expected_message, actual_message)
        self.assertEqual(expected_status, actual_status)
        mock_run.assert_called_once_with(["sherlock"], dry_run=True)

    @mock.patch("lcats.analysis.corpus.cli.run_survey")
    def test_dispatch_survey(self, mock_run_survey):
        """Ensure the survey command delegates to corpus cli."""
        mock_run_survey.return_value = 0

        actual_message, actual_status = cli.dispatch("survey", ["corpora/sherlock"])
        self.assertEqual("", actual_message)
        self.assertEqual(0, actual_status)
        mock_run_survey.assert_called_once()

    @mock.patch("lcats.analysis.corpus.cli.run_stats")
    def test_dispatch_stats(self, mock_run_stats):
        """Ensure the stats command delegates to corpus cli."""
        mock_run_stats.return_value = 0

        actual_message, actual_status = cli.dispatch("stats", ["corpora/sherlock"])
        self.assertEqual("", actual_message)
        self.assertEqual(0, actual_status)
        mock_run_stats.assert_called_once()

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
        """Ensure unknown commands are rejected by the top-level parser."""
        with capture.capture_output():
            with self.assertRaises(SystemExit) as cm:
                cli.dispatch("unknown", [])
        self.assertEqual(2, cm.exception.code)

    @parameterized.parameterized.expand(
        [
            (["--help"], 0),
            (["help"], 0),
        ]
    )
    def test_top_level_help(self, argv, expected_code):
        """Ensure top-level help works for both --help and help aliases."""
        with capture.capture_output() as captured:
            with self.assertRaises(SystemExit) as cm:
                cli.main(argv)
        self.assertEqual(expected_code, cm.exception.code)
        self.assertIn("usage: lcats", captured.stdout.getvalue())

    @parameterized.parameterized.expand(
        [
            (["survey", "--help"], "usage: lcats survey"),
            (["stats", "--help"], "usage: lcats stats"),
            (["help", "survey"], "usage: lcats survey"),
            (["help", "stats"], "usage: lcats stats"),
        ]
    )
    def test_command_help(self, argv, expected_usage):
        """Ensure command-level help is available from direct and alias paths."""
        with capture.capture_output() as captured:
            with self.assertRaises(SystemExit) as cm:
                cli.main(argv)
        self.assertEqual(0, cm.exception.code)
        self.assertIn(expected_usage, captured.stdout.getvalue())

    def test_survey_help_contains_examples(self):
        with capture.capture_output() as captured:
            with self.assertRaises(SystemExit):
                cli.main(["survey", "--help"])
        output = captured.stdout.getvalue()
        self.assertIn("Examples:", output)
        self.assertIn("lcats survey --mode specials corpora/sherlock", output)
        self.assertIn("lcats survey data/ --format tsv --output findings.tsv", output)

    def test_stats_help_contains_examples(self):
        with capture.capture_output() as captured:
            with self.assertRaises(SystemExit):
                cli.main(["stats", "--help"])
        output = captured.stdout.getvalue()
        self.assertIn("Examples:", output)
        self.assertIn("lcats stats data/ --no-dedupe", output)

    @parameterized.parameterized.expand(
        [
            (
                ["survey", "--format", "tsv", "--no-progress", "-foobar"],
                "usage: lcats survey",
            ),
            (["stats", "--story-output", "out.tsv", "-foobar"], "usage: lcats stats"),
        ]
    )
    def test_invalid_flags_show_subcommand_usage(self, argv, expected_usage):
        with capture.capture_output() as captured:
            with self.assertRaises(SystemExit) as cm:
                cli.main(argv)
        self.assertEqual(2, cm.exception.code)
        stderr = captured.stderr.getvalue()
        self.assertIn(expected_usage, stderr)


if __name__ == "__main__":
    unittest.main()
