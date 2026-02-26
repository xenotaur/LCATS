"""Tests for lcats.gatherers.mass_quantities.gatherer."""

import unittest
from unittest.mock import patch, MagicMock

from lcats.gatherers.mass_quantities import gatherer


class TestGatherStories(unittest.TestCase):
    """Tests for gatherer.gather_stories."""

    @patch("lcats.gatherers.mass_quantities.gatherer.tqdm")
    @patch("lcats.gatherers.mass_quantities.gatherer.parser")
    @patch("lcats.gatherers.mass_quantities.gatherer.downloaders")
    def test_successful_story_added_to_gathered(
        self, mock_downloaders, mock_parser, mock_tqdm
    ):
        """A story with a filename is added to gathered_stories."""
        mock_tqdm.side_effect = lambda x: x
        mock_parser.gather_story.return_value = (42, "/path/to/story.json", None)

        gathered, failed = gatherer.gather_stories([42])

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
        mock_tqdm.side_effect = lambda x: x
        mock_parser.gather_story.return_value = (99, None, "No data for this story")

        gathered, failed = gatherer.gather_stories([99])

        self.assertEqual(gathered, {})
        self.assertIn(99, failed)
        self.assertEqual(failed[99], "No data for this story")

    @patch("lcats.gatherers.mass_quantities.gatherer.tqdm")
    @patch("lcats.gatherers.mass_quantities.gatherer.parser")
    @patch("lcats.gatherers.mass_quantities.gatherer.downloaders")
    def test_empty_stories_list(self, mock_downloaders, mock_parser, mock_tqdm):
        """An empty story list returns two empty dicts."""
        mock_tqdm.side_effect = lambda x: x

        gathered, failed = gatherer.gather_stories([])

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
        mock_tqdm.side_effect = lambda x: x
        mock_parser.gather_story.side_effect = [
            (1, "/path/1.json", None),
            (2, None, "skipped"),
            (3, "/path/3.json", None),
        ]

        gathered, failed = gatherer.gather_stories([1, 2, 3])

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

        from lcats.gatherers.mass_quantities import storymap

        gatherer.gather_stories([1])

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

        gatherer.gather_stories([7])

        mock_parser.gather_story.assert_called_once_with(mock_instance, 7)


class TestGather(unittest.TestCase):
    """Tests for gatherer.gather."""

    @patch("lcats.gatherers.mass_quantities.gatherer.gather_stories")
    def test_gather_returns_only_successful_stories(self, mock_gather_stories):
        """gather() returns only the successful-stories dict."""
        expected = {10: "/data/10.json"}
        mock_gather_stories.return_value = (expected, {20: "error"})

        result = gatherer.gather()

        self.assertIs(result, expected)

    @patch("lcats.gatherers.mass_quantities.gatherer.gather_stories")
    def test_gather_passes_single_stories(self, mock_gather_stories):
        """gather() calls gather_stories with storymap.SINGLE_STORIES."""
        mock_gather_stories.return_value = ({}, {})

        from lcats.gatherers.mass_quantities import storymap

        gatherer.gather()

        mock_gather_stories.assert_called_once_with(storymap.SINGLE_STORIES)

    @patch("lcats.gatherers.mass_quantities.gatherer.gather_stories")
    def test_gather_returns_empty_on_all_failures(self, mock_gather_stories):
        """gather() returns an empty dict when all stories fail."""
        mock_gather_stories.return_value = ({}, {1: "error"})

        result = gatherer.gather()

        self.assertEqual(result, {})


class TestMain(unittest.TestCase):
    """Tests for gatherer.main."""

    @patch("lcats.gatherers.mass_quantities.gatherer.gather_stories")
    def test_main_calls_gather_stories_with_single_stories(self, mock_gather_stories):
        """main() calls gather_stories with storymap.SINGLE_STORIES."""
        mock_gather_stories.return_value = ({}, {})

        from lcats.gatherers.mass_quantities import storymap

        gatherer.main()

        mock_gather_stories.assert_called_once_with(storymap.SINGLE_STORIES)

    @patch("builtins.print")
    @patch("lcats.gatherers.mass_quantities.gatherer.gather_stories")
    def test_main_prints_download_count(self, mock_gather_stories, mock_print):
        """main() prints the number of successfully downloaded stories."""
        mock_gather_stories.return_value = ({1: "/a.json", 2: "/b.json"}, {})

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

        gatherer.main()

        error_line = any(
            "errors encountered: 2" in str(c) for c in mock_print.call_args_list
        )
        self.assertTrue(error_line)


if __name__ == "__main__":
    unittest.main()
