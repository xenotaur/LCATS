"""Unit tests for lcats.visualize.rendering."""

import os
import tempfile
import unittest

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")  # non-interactive backend for testing

from lcats.utils import capture
from lcats.visualize import rendering


def _make_counts():
    return {"fantasy": 5, "horror": 3, "science fiction": 12}


class TestPlotGenreBarChart(unittest.TestCase):
    """Tests for plot_genre_bar_chart."""

    def tearDown(self):
        plt.close("all")

    def test_returns_fig_ax(self):
        """Function returns a (fig, ax) tuple."""
        with capture.suppress_output():
            fig, ax = rendering.plot_genre_bar_chart(_make_counts())
        self.assertIsInstance(fig, plt.Figure)
        self.assertIsNotNone(ax)

    def test_save_path_writes_file(self):
        """Figure is saved to disk when save_path is provided."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path = f.name
        try:
            with capture.suppress_output():
                rendering.plot_genre_bar_chart(_make_counts(), save_path=path)
            self.assertTrue(os.path.getsize(path) > 0)
        finally:
            os.unlink(path)


class TestPlotGenreWordcloud(unittest.TestCase):
    """Tests for plot_genre_wordcloud."""

    def tearDown(self):
        plt.close("all")

    def test_returns_fig_ax(self):
        """Function returns a (fig, ax) tuple."""
        with capture.suppress_output():
            fig, ax = rendering.plot_genre_wordcloud(_make_counts())
        self.assertIsInstance(fig, plt.Figure)
        self.assertIsNotNone(ax)

    def test_save_path_writes_file(self):
        """Figure is saved to disk when save_path is provided."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path = f.name
        try:
            with capture.suppress_output():
                rendering.plot_genre_wordcloud(_make_counts(), save_path=path)
            self.assertTrue(os.path.getsize(path) > 0)
        finally:
            os.unlink(path)

    def test_seed_is_deterministic(self):
        """The same seed produces the same rendered word-cloud layout."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f1:
            path1 = f1.name
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f2:
            path2 = f2.name
        try:
            with capture.suppress_output():
                rendering.plot_genre_wordcloud(_make_counts(), seed=7, save_path=path1)
                rendering.plot_genre_wordcloud(_make_counts(), seed=7, save_path=path2)
            with open(path1, "rb") as f:
                bytes1 = f.read()
            with open(path2, "rb") as f:
                bytes2 = f.read()
            self.assertEqual(bytes1, bytes2)
        finally:
            os.unlink(path1)
            os.unlink(path2)


if __name__ == "__main__":
    unittest.main()
