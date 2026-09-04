"""Tests for lcats.gatherers.mass_quantities.gatherer."""

import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from lcats.gatherers.mass_quantities import gatherer
from lcats.gatherers.mass_quantities import storymap
from lcats.utils import capture


class TestGatherStories(unittest.TestCase):
    """Tests for gatherer.gather_stories."""

    def setUp(self):
        # gather_stories() now writes a run_log.RunLog by default -- point
        # it at a throwaway directory rather than the real default
        # (logs/gather/ relative to cwd), so these unit tests don't leave
        # real files behind in whatever directory happens to run them
        # (WI-GATHER-0105, mirroring WI-RUNLOG-0082's own precedent).
        self._tmp = tempfile.TemporaryDirectory()
        self.log_dir = pathlib.Path(self._tmp.name) / "gather_logs"

    def tearDown(self):
        self._tmp.cleanup()

    @patch("lcats.gatherers.mass_quantities.gatherer.tqdm")
    @patch("lcats.gatherers.mass_quantities.gatherer.parser")
    @patch("lcats.gatherers.mass_quantities.gatherer.downloaders")
    def test_successful_story_added_to_gathered(
        self, mock_downloaders, mock_parser, mock_tqdm
    ):
        """A story with a filename is added to gathered_stories."""
        del mock_downloaders
        mock_tqdm.side_effect = lambda x: x
        mock_parser.gather_story.return_value = (42, "/path/to/story.json", None)

        with capture.suppress_output():
            gathered, failed = gatherer.gather_stories([42], log_dir=self.log_dir)

        self.assertIn(42, gathered)
        self.assertEqual(gathered[42], "/path/to/story.json")
        self.assertEqual(failed, {})

    @patch("lcats.gatherers.mass_quantities.gatherer.tqdm")
    @patch("lcats.gatherers.mass_quantities.gatherer.parser")
    @patch("lcats.gatherers.mass_quantities.gatherer.downloaders")
    def test_failed_story_added_to_failed(
        self, mock_downloaders, mock_parser, mock_tqdm
    ):
        """A story with an error is added to failed_stories."""
        del mock_downloaders
        mock_tqdm.side_effect = lambda x: x
        mock_parser.gather_story.return_value = (99, None, "No data for this story")

        with capture.suppress_output():
            gathered, failed = gatherer.gather_stories([99], log_dir=self.log_dir)

        self.assertEqual(gathered, {})
        self.assertIn(99, failed)
        self.assertEqual(failed[99], "No data for this story")

    @patch("lcats.gatherers.mass_quantities.gatherer.tqdm")
    @patch("lcats.gatherers.mass_quantities.gatherer.parser")
    @patch("lcats.gatherers.mass_quantities.gatherer.downloaders")
    def test_empty_stories_list(self, mock_downloaders, mock_parser, mock_tqdm):
        """An empty story list returns two empty dicts."""
        del mock_downloaders
        mock_tqdm.side_effect = lambda x: x

        with capture.suppress_output():
            gathered, failed = gatherer.gather_stories([], log_dir=self.log_dir)

        self.assertEqual(gathered, {})
        self.assertEqual(failed, {})
        mock_parser.gather_story.assert_not_called()

    @patch("lcats.gatherers.mass_quantities.gatherer.tqdm")
    @patch("lcats.gatherers.mass_quantities.gatherer.parser")
    @patch("lcats.gatherers.mass_quantities.gatherer.downloaders")
    def test_multiple_stories_mixed_results(
        self, mock_downloaders, mock_parser, mock_tqdm
    ):
        """Mix of successes and failures are partitioned correctly."""
        del mock_downloaders
        mock_tqdm.side_effect = lambda x: x
        mock_parser.gather_story.side_effect = [
            (1, "/path/1.json", None),
            (2, None, "skipped"),
            (3, "/path/3.json", None),
        ]

        with capture.suppress_output():
            gathered, failed = gatherer.gather_stories([1, 2, 3], log_dir=self.log_dir)

        self.assertEqual(gathered, {1: "/path/1.json", 3: "/path/3.json"})
        self.assertEqual(failed, {2: "skipped"})

    @patch("lcats.gatherers.mass_quantities.gatherer.tqdm")
    @patch("lcats.gatherers.mass_quantities.gatherer.parser")
    @patch("lcats.gatherers.mass_quantities.gatherer.downloaders")
    def test_data_gatherer_created_with_correct_directory(
        self, mock_downloaders, mock_parser, mock_tqdm
    ):
        """DataGatherer is instantiated with TARGET_DIRECTORY."""
        mock_tqdm.side_effect = lambda x: x
        mock_parser.gather_story.return_value = (1, "/path/1.json", None)
        mock_instance = MagicMock()
        mock_downloaders.DataGatherer.return_value = mock_instance

        with capture.suppress_output():
            gatherer.gather_stories([1], log_dir=self.log_dir)

        args, _ = mock_downloaders.DataGatherer.call_args
        self.assertEqual(args[0], storymap.TARGET_DIRECTORY)

    @patch("lcats.gatherers.mass_quantities.gatherer.tqdm")
    @patch("lcats.gatherers.mass_quantities.gatherer.parser")
    @patch("lcats.gatherers.mass_quantities.gatherer.downloaders")
    def test_gather_story_called_with_gatherer_and_story(
        self, mock_downloaders, mock_parser, mock_tqdm
    ):
        """parser.gather_story is called once per story with the DataGatherer instance."""
        mock_tqdm.side_effect = lambda x: x
        mock_instance = MagicMock()
        mock_downloaders.DataGatherer.return_value = mock_instance
        mock_parser.gather_story.return_value = (7, "/path/7.json", None)

        with capture.suppress_output():
            gatherer.gather_stories([7], log_dir=self.log_dir)

        mock_parser.gather_story.assert_called_once_with(mock_instance, 7)


class TestGatherStoriesRunLogging(unittest.TestCase):
    """WI-GATHER-0105: gather_stories()'s loop gets a crash-safe,
    incremental run-event log via lcats.utils.run_log.RunLog, written
    outside the protected data/ tree gathered stories live under."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.log_dir = pathlib.Path(self._tmp.name) / "gather_logs"

    def tearDown(self):
        self._tmp.cleanup()

    def _read_log_lines(self):
        log_path = self.log_dir / gatherer.GATHER_LOG_FILENAME
        with open(log_path, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    @patch("lcats.gatherers.mass_quantities.gatherer.tqdm")
    @patch("lcats.gatherers.mass_quantities.gatherer.parser")
    @patch("lcats.gatherers.mass_quantities.gatherer.downloaders")
    def test_run_log_records_start_and_per_story_and_end_in_order(
        self, mock_downloaders, mock_parser, mock_tqdm
    ):
        """A clean run logs run_start, one event per story, then run_end,
        in that order, at the expected log path."""
        del mock_downloaders
        mock_tqdm.side_effect = lambda x: x
        mock_parser.gather_story.side_effect = [
            (1, "/path/1.json", None),
            (2, None, "skipped"),
        ]

        with capture.suppress_output():
            gatherer.gather_stories([1, 2], log_dir=self.log_dir)

        events = self._read_log_lines()
        self.assertEqual(
            [e["event"] for e in events],
            ["run_start", "story_downloaded", "story_failed", "run_end"],
        )
        self.assertEqual(events[1]["story"], 1)
        self.assertEqual(events[2]["story"], 2)

    @patch("lcats.gatherers.mass_quantities.gatherer.tqdm")
    @patch("lcats.gatherers.mass_quantities.gatherer.parser")
    @patch("lcats.gatherers.mass_quantities.gatherer.downloaders")
    def test_crash_mid_run_leaves_a_readable_partial_log(
        self, mock_downloaders, mock_parser, mock_tqdm
    ):
        """An unhandled parser.gather_story() failure partway through
        must not lose the events already written -- run_start plus the
        one completed story's event, then run_aborted_unexpected."""
        del mock_downloaders
        mock_tqdm.side_effect = lambda x: x
        mock_parser.gather_story.side_effect = [
            (1, "/path/1.json", None),
            RuntimeError("simulated crash"),
        ]

        with capture.suppress_output():
            with self.assertRaises(RuntimeError):
                gatherer.gather_stories([1, 2], log_dir=self.log_dir)

        events = self._read_log_lines()
        self.assertEqual(
            [e["event"] for e in events],
            ["run_start", "story_downloaded", "run_aborted_unexpected"],
        )

    @patch("lcats.gatherers.mass_quantities.gatherer.tqdm")
    @patch("lcats.gatherers.mass_quantities.gatherer.parser")
    @patch("lcats.gatherers.mass_quantities.gatherer.downloaders")
    def test_log_written_to_configured_directory_and_filename(
        self, mock_downloaders, mock_parser, mock_tqdm
    ):
        """The log lands at <log_dir>/mass_quantities_gather_run_log.jsonl."""
        del mock_downloaders
        mock_tqdm.side_effect = lambda x: x
        mock_parser.gather_story.return_value = (1, "/path/1.json", None)

        with capture.suppress_output():
            gatherer.gather_stories([1], log_dir=self.log_dir)

        expected_path = self.log_dir / "mass_quantities_gather_run_log.jsonl"
        self.assertTrue(expected_path.exists())

    @patch("lcats.gatherers.mass_quantities.gatherer.tqdm")
    @patch("lcats.gatherers.mass_quantities.gatherer.parser")
    @patch("lcats.gatherers.mass_quantities.gatherer.downloaders")
    def test_accepts_a_non_sized_iterable(
        self, mock_downloaders, mock_parser, mock_tqdm
    ):
        """A generator (no len()) doesn't raise before any work starts
        (review finding, PR #426) -- story_count is logged as None."""
        del mock_downloaders
        mock_tqdm.side_effect = lambda x: x
        mock_parser.gather_story.return_value = (1, "/path/1.json", None)

        def story_ids():
            yield 1

        with capture.suppress_output():
            gathered, _failed = gatherer.gather_stories(
                story_ids(), log_dir=self.log_dir
            )

        self.assertEqual(gathered, {1: "/path/1.json"})
        events = self._read_log_lines()
        self.assertIsNone(events[0]["story_count"])


class TestGather(unittest.TestCase):
    """Tests for gatherer.gather."""

    @patch("lcats.gatherers.mass_quantities.gatherer.gather_stories")
    def test_gather_returns_only_successful_stories(self, mock_gather_stories):
        """gather() returns only the successful-stories dict."""
        expected = {10: "/data/10.json"}
        mock_gather_stories.return_value = (expected, {20: "error"})

        with capture.suppress_output():
            result = gatherer.gather()

        self.assertIs(result, expected)

    @patch("lcats.gatherers.mass_quantities.gatherer.gather_stories")
    def test_gather_passes_single_stories(self, mock_gather_stories):
        """gather() calls gather_stories with storymap.SINGLE_STORIES."""
        mock_gather_stories.return_value = ({}, {})
        with capture.suppress_output():
            gatherer.gather()

        mock_gather_stories.assert_called_once_with(storymap.SINGLE_STORIES)

    @patch("lcats.gatherers.mass_quantities.gatherer.gather_stories")
    def test_gather_returns_empty_on_all_failures(self, mock_gather_stories):
        """gather() returns an empty dict when all stories fail."""
        mock_gather_stories.return_value = ({}, {1: "error"})

        with capture.suppress_output():
            result = gatherer.gather()

        self.assertEqual(result, {})


class TestMain(unittest.TestCase):
    """Tests for gatherer.main."""

    @patch("lcats.gatherers.mass_quantities.gatherer.gather_stories")
    def test_main_calls_gather_stories_with_single_stories(self, mock_gather_stories):
        """main() calls gather_stories with storymap.SINGLE_STORIES."""
        mock_gather_stories.return_value = ({}, {})
        with capture.suppress_output():
            gatherer.main()

        mock_gather_stories.assert_called_once_with(storymap.SINGLE_STORIES)

    @patch("builtins.print")
    @patch("lcats.gatherers.mass_quantities.gatherer.gather_stories")
    def test_main_prints_download_count(self, mock_gather_stories, mock_print):
        """main() prints the number of successfully downloaded stories."""
        mock_gather_stories.return_value = ({1: "/a.json", 2: "/b.json"}, {})

        with capture.suppress_output():
            gatherer.main()

        corpus_line = any(
            "single corpus: 2" in str(c) for c in mock_print.call_args_list
        )
        self.assertTrue(corpus_line)

    @patch("builtins.print")
    @patch("lcats.gatherers.mass_quantities.gatherer.gather_stories")
    def test_main_prints_error_count(self, mock_gather_stories, mock_print):
        """main() prints the number of errors encountered."""
        mock_gather_stories.return_value = ({}, {5: "err", 6: "err"})

        with capture.suppress_output():
            gatherer.main()

        error_line = any(
            "errors encountered: 2" in str(c) for c in mock_print.call_args_list
        )
        self.assertTrue(error_line)


if __name__ == "__main__":
    unittest.main()
