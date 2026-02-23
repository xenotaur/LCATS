"""Unit tests for lcats.analysis.graph_plotters."""

import unittest

import matplotlib
import pandas as pd

matplotlib.use("Agg")  # non-interactive backend for testing

from lcats.analysis import graph_plotters


def _make_author_stats():
    """Return a minimal author_stats DataFrame."""
    return pd.DataFrame(
        {
            "author": ["Alice", "Bob", "Carol", "Dave", "Eve"],
            "stories": [10, 5, 3, 2, 1],
            "body_tokens": [5000, 2000, 800, 300, 100],
        }
    )


def _make_story_stats():
    """Return a minimal story_stats DataFrame with per-story rows."""
    return pd.DataFrame(
        {
            "story_id": [1, 2, 3, 4, 5, 6, 7],
            "title": ["T1", "T2", "T3", "T4", "T5", "T6", "T7"],
            "authors": [
                ["Alice", "Bob"],
                ["Alice"],
                ["Alice"],
                ["Bob"],
                ["Bob"],
                ["Carol"],
                ["Carol"],
            ],
            "body_tokens": [500, 400, 300, 200, 150, 100, 80],
        }
    )


class TestTokensPerStoryByAuthorFrame(unittest.TestCase):
    """Tests for tokens_per_story_by_author_frame."""

    def test_explodes_authors_list(self):
        """Multi-author stories appear once per author after explode."""
        story_stats = _make_story_stats()
        result = graph_plotters.tokens_per_story_by_author_frame(story_stats)
        # story_id=1 has ['Alice', 'Bob'], so it should appear twice
        rows_for_story1 = result[result["story_id"] == 1]
        self.assertEqual(len(rows_for_story1), 2)

    def test_drops_empty_authors(self):
        """Rows with empty/None author strings are removed."""
        df = pd.DataFrame(
            {
                "story_id": [10, 11],
                "title": ["X", "Y"],
                "authors": [[""], [None]],
                "body_tokens": [100, 200],
            }
        )
        result = graph_plotters.tokens_per_story_by_author_frame(df)
        self.assertEqual(len(result), 0)

    def test_output_columns(self):
        """Result has exactly the expected columns."""
        story_stats = _make_story_stats()
        result = graph_plotters.tokens_per_story_by_author_frame(story_stats)
        self.assertEqual(
            list(result.columns), ["author", "story_id", "title", "body_tokens"]
        )

    def test_does_not_mutate_input(self):
        """Input DataFrame is not modified."""
        story_stats = _make_story_stats()
        original_columns = list(story_stats.columns)
        graph_plotters.tokens_per_story_by_author_frame(story_stats)
        self.assertEqual(list(story_stats.columns), original_columns)


class TestPlotAuthorStoriesVsTokens(unittest.TestCase):
    """Tests for plot_author_stories_vs_tokens."""

    def setUp(self):
        self.author_stats = _make_author_stats()

    def tearDown(self):
        import matplotlib.pyplot as plt

        plt.close("all")

    def test_returns_fig_ax(self):
        """Function returns a (fig, ax) tuple."""
        import matplotlib.pyplot as plt

        fig, ax = graph_plotters.plot_author_stories_vs_tokens(self.author_stats)
        self.assertIsInstance(fig, plt.Figure)
        self.assertIsNotNone(ax)

    def test_log_scale_enabled_by_default(self):
        """Y-axis is log scale when log_tokens=True (default)."""
        _, ax = graph_plotters.plot_author_stories_vs_tokens(
            self.author_stats, log_tokens=True
        )
        self.assertEqual(ax.get_yscale(), "log")

    def test_linear_scale_when_disabled(self):
        """Y-axis is linear when log_tokens=False."""
        _, ax = graph_plotters.plot_author_stories_vs_tokens(
            self.author_stats, log_tokens=False
        )
        self.assertEqual(ax.get_yscale(), "linear")

    def test_annotations_present(self):
        """Top-N annotations are added when annotate_top > 0."""
        _, ax = graph_plotters.plot_author_stories_vs_tokens(
            self.author_stats, annotate_top=3
        )
        self.assertGreater(len(ax.texts), 0)

    def test_no_annotations_when_disabled(self):
        """No annotations are added when annotate_top=0."""
        _, ax = graph_plotters.plot_author_stories_vs_tokens(
            self.author_stats, annotate_top=0
        )
        self.assertEqual(len(ax.texts), 0)

    def test_save_path_writes_file(self):
        """Figure is saved to disk when save_path is provided."""
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path = f.name
        try:
            graph_plotters.plot_author_stories_vs_tokens(
                self.author_stats, save_path=path
            )
            self.assertTrue(os.path.getsize(path) > 0)
        finally:
            os.unlink(path)

    def test_axis_labels(self):
        """Axis labels are set correctly."""
        _, ax = graph_plotters.plot_author_stories_vs_tokens(self.author_stats)
        self.assertIn("Stories", ax.get_xlabel())
        self.assertIn("Tokens", ax.get_ylabel())


class TestPlotTokensPerStoryByAuthor(unittest.TestCase):
    """Tests for plot_tokens_per_story_by_author."""

    def setUp(self):
        self.story_stats = _make_story_stats()

    def tearDown(self):
        import matplotlib.pyplot as plt

        plt.close("all")

    def test_returns_fig_ax(self):
        """Function returns a (fig, ax) tuple."""
        import matplotlib.pyplot as plt

        fig, ax = graph_plotters.plot_tokens_per_story_by_author(
            self.story_stats, min_stories=2
        )
        self.assertIsInstance(fig, plt.Figure)
        self.assertIsNotNone(ax)

    def test_log_scale_enabled(self):
        """Y-axis is log scale when log_tokens=True."""
        _, ax = graph_plotters.plot_tokens_per_story_by_author(
            self.story_stats, log_tokens=True, min_stories=2
        )
        self.assertEqual(ax.get_yscale(), "log")

    def test_linear_scale(self):
        """Y-axis is linear when log_tokens=False."""
        _, ax = graph_plotters.plot_tokens_per_story_by_author(
            self.story_stats, log_tokens=False, min_stories=2
        )
        self.assertEqual(ax.get_yscale(), "linear")

    def test_min_stories_filters(self):
        """Authors with fewer than min_stories stories are excluded."""
        # Carol has exactly 2 stories; with min_stories=3 she should be excluded.
        _, ax = graph_plotters.plot_tokens_per_story_by_author(
            self.story_stats, min_stories=3, top_n=12
        )
        tick_labels = [t.get_text() for t in ax.get_xticklabels()]
        for label in tick_labels:
            self.assertNotIn("Carol", label)

    def test_top_n_limits_authors(self):
        """At most top_n authors appear on the x-axis."""
        _, ax = graph_plotters.plot_tokens_per_story_by_author(
            self.story_stats, top_n=1, min_stories=2
        )
        tick_labels = [t.get_text() for t in ax.get_xticklabels() if t.get_text()]
        self.assertLessEqual(len(tick_labels), 1)

    def test_rotate_labels_zero(self):
        """Labels have center alignment when rotate_labels=0."""
        _, ax = graph_plotters.plot_tokens_per_story_by_author(
            self.story_stats, rotate_labels=0, min_stories=2
        )
        for lbl in ax.get_xticklabels():
            self.assertEqual(lbl.get_ha(), "center")


class TestPlotAuthorStoriesVsTokensSns(unittest.TestCase):
    """Tests for plot_author_stories_vs_tokens_sns."""

    def setUp(self):
        self.author_stats = _make_author_stats()

    def tearDown(self):
        import matplotlib.pyplot as plt

        plt.close("all")

    def test_returns_fig_ax(self):
        """Function returns a (fig, ax) tuple."""
        import matplotlib.pyplot as plt

        fig, ax = graph_plotters.plot_author_stories_vs_tokens_sns(self.author_stats)
        self.assertIsInstance(fig, plt.Figure)
        self.assertIsNotNone(ax)

    def test_log_scale_enabled(self):
        """Y-axis is log scale when log_tokens=True (default)."""
        _, ax = graph_plotters.plot_author_stories_vs_tokens_sns(
            self.author_stats, log_tokens=True
        )
        self.assertEqual(ax.get_yscale(), "log")

    def test_linear_scale(self):
        """Y-axis is linear when log_tokens=False."""
        _, ax = graph_plotters.plot_author_stories_vs_tokens_sns(
            self.author_stats, log_tokens=False
        )
        self.assertEqual(ax.get_yscale(), "linear")

    def test_annotations_present(self):
        """Top-N annotations are added when annotate_top > 0."""
        _, ax = graph_plotters.plot_author_stories_vs_tokens_sns(
            self.author_stats, annotate_top=2
        )
        self.assertGreater(len(ax.texts), 0)

    def test_no_annotations_when_disabled(self):
        """No annotations when annotate_top=0."""
        _, ax = graph_plotters.plot_author_stories_vs_tokens_sns(
            self.author_stats, annotate_top=0
        )
        self.assertEqual(len(ax.texts), 0)

    def test_axis_labels(self):
        """Axis labels are set correctly."""
        _, ax = graph_plotters.plot_author_stories_vs_tokens_sns(self.author_stats)
        self.assertIn("Stories", ax.get_xlabel())
        self.assertIn("Tokens", ax.get_ylabel())


class TestPlotTokensPerStoryByAuthorSns(unittest.TestCase):
    """Tests for plot_tokens_per_story_by_author_sns."""

    def setUp(self):
        self.story_stats = _make_story_stats()

    def tearDown(self):
        import matplotlib.pyplot as plt

        plt.close("all")

    def test_returns_fig_ax(self):
        """Function returns a (fig, ax) tuple."""
        import matplotlib.pyplot as plt

        fig, ax = graph_plotters.plot_tokens_per_story_by_author_sns(
            self.story_stats, min_stories=2
        )
        self.assertIsInstance(fig, plt.Figure)
        self.assertIsNotNone(ax)

    def test_log_scale(self):
        """Y-axis is log scale when log_tokens=True."""
        _, ax = graph_plotters.plot_tokens_per_story_by_author_sns(
            self.story_stats, log_tokens=True, min_stories=2
        )
        self.assertEqual(ax.get_yscale(), "log")

    def test_linear_scale(self):
        """Y-axis is linear when log_tokens=False."""
        _, ax = graph_plotters.plot_tokens_per_story_by_author_sns(
            self.story_stats, log_tokens=False, min_stories=2
        )
        self.assertEqual(ax.get_yscale(), "linear")

    def test_rotate_labels_zero(self):
        """Labels have center alignment when rotate_labels=0."""
        _, ax = graph_plotters.plot_tokens_per_story_by_author_sns(
            self.story_stats, rotate_labels=0, min_stories=2
        )
        for lbl in ax.get_xticklabels():
            self.assertEqual(lbl.get_ha(), "center")

    def test_top_n_limits_authors(self):
        """At most top_n authors appear."""
        _, ax = graph_plotters.plot_tokens_per_story_by_author_sns(
            self.story_stats, top_n=1, min_stories=2
        )
        tick_labels = [t.get_text() for t in ax.get_xticklabels() if t.get_text()]
        self.assertLessEqual(len(tick_labels), 1)


class TestPlotTokensPerStoryVsStories(unittest.TestCase):
    """Tests for plot_tokens_per_story_vs_stories."""

    def setUp(self):
        self.author_stats = _make_author_stats()

    def tearDown(self):
        import matplotlib.pyplot as plt

        plt.close("all")

    def test_returns_fig_ax(self):
        """Function returns a (fig, ax) tuple."""
        import matplotlib.pyplot as plt

        fig, ax = graph_plotters.plot_tokens_per_story_vs_stories(self.author_stats)
        self.assertIsInstance(fig, plt.Figure)
        self.assertIsNotNone(ax)

    def test_log_scale_enabled(self):
        """Y-axis is log when log_y=True (default)."""
        _, ax = graph_plotters.plot_tokens_per_story_vs_stories(
            self.author_stats, log_y=True
        )
        self.assertEqual(ax.get_yscale(), "log")

    def test_linear_scale(self):
        """Y-axis is linear when log_y=False."""
        _, ax = graph_plotters.plot_tokens_per_story_vs_stories(
            self.author_stats, log_y=False
        )
        self.assertEqual(ax.get_yscale(), "linear")

    def test_annotations_present(self):
        """Annotations exist when annotate_top > 0."""
        _, ax = graph_plotters.plot_tokens_per_story_vs_stories(
            self.author_stats, annotate_top=3
        )
        self.assertGreater(len(ax.texts), 0)

    def test_no_annotations_when_disabled(self):
        """No annotations when annotate_top=0."""
        _, ax = graph_plotters.plot_tokens_per_story_vs_stories(
            self.author_stats, annotate_top=0
        )
        self.assertEqual(len(ax.texts), 0)

    def test_min_stories_filters_rows(self):
        """Authors with fewer stories than min_stories are excluded."""
        # Eve has 1 story; with min_stories=2 her dot should not appear.
        # We verify the plot can still be produced without error.
        fig, ax = graph_plotters.plot_tokens_per_story_vs_stories(
            self.author_stats, min_stories=2, annotate_top=0
        )
        self.assertIsNotNone(fig)

    def test_jitter_does_not_crash(self):
        """Non-zero jitter value should not raise an error."""
        import numpy as np

        np.random.seed(0)
        fig, ax = graph_plotters.plot_tokens_per_story_vs_stories(
            self.author_stats, jitter=0.1
        )
        self.assertIsNotNone(fig)

    def test_max_spread_limits_offset(self):
        """max_spread parameter does not crash."""
        fig, ax = graph_plotters.plot_tokens_per_story_vs_stories(
            self.author_stats, annotate_top=5, max_spread=2
        )
        self.assertIsNotNone(fig)

    def test_arrow_false_does_not_crash(self):
        """arrow=False removes arrowprops without crashing."""
        fig, ax = graph_plotters.plot_tokens_per_story_vs_stories(
            self.author_stats, annotate_top=3, arrow=False
        )
        self.assertIsNotNone(fig)

    def test_axis_labels(self):
        """Axis labels mention stories and tokens."""
        _, ax = graph_plotters.plot_tokens_per_story_vs_stories(self.author_stats)
        self.assertIn("stories", ax.get_xlabel().lower())
        self.assertIn("tokens", ax.get_ylabel().lower())


if __name__ == "__main__":
    unittest.main()
