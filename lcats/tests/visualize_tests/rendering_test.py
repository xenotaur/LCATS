"""Unit tests for lcats.visualize.rendering."""

import os
import tempfile
import unittest

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")  # non-interactive backend for testing

from lcats.utils import capture
from lcats.visualize import comparison
from lcats.visualize import rendering


def _make_counts():
    return {"fantasy": 5, "horror": 3, "science fiction": 12}


def _comparison_result(
    *,
    metric_name="raw_count",
    left_metric=None,
    right_metric=None,
):
    metric = (
        {
            "name": metric_name,
            "denominator": "auto",
            "effective_denominator": "none",
        }
        if left_metric is None or right_metric is None
        else None
    )
    left_metric = left_metric or metric
    right_metric = right_metric or metric
    return comparison.ComparisonResult(
        rows=(
            comparison.ComparisonRow(
                term="dragon",
                display_order=1,
                left_value=2.0,
                right_value=5.0,
                left_raw_count=2,
                right_raw_count=5,
                left_document_count=1,
                right_document_count=2,
                left_token_denominator=10,
                right_token_denominator=12,
                left_document_denominator=1,
                right_document_denominator=2,
                signed_difference=-3.0,
                absolute_difference=3.0,
            ),
            comparison.ComparisonRow(
                term="rocket",
                display_order=2,
                left_value=4.0,
                right_value=1.0,
                left_raw_count=4,
                right_raw_count=1,
                left_document_count=1,
                right_document_count=1,
                left_token_denominator=10,
                right_token_denominator=12,
                left_document_denominator=1,
                right_document_denominator=2,
                signed_difference=3.0,
                absolute_difference=3.0,
            ),
        ),
        manifest={
            "left": {"label": "reference"},
            "right": {"label": "target"},
            "metrics": {"left": left_metric, "right": right_metric},
            "preprocessing": {"term_form": "surface"},
        },
    )


def _nway_result():
    def cell(key, label, value, deviation):
        return comparison.NWayPanelValue(
            panel_key=key,
            panel_label=label,
            value=value,
            deviation=deviation,
            raw_count=int(value),
            document_count=1,
            token_denominator=10,
            document_denominator=2,
        )

    return comparison.NWayComparisonResult(
        rows=(
            comparison.NWayComparisonRow(
                term="dragon",
                display_order=1,
                reference_value=4.0,
                reference_raw_count=4,
                reference_document_count=2,
                reference_token_denominator=20,
                reference_document_denominator=3,
                panels=(
                    cell("fantasy", "Fantasy", 7.0, 3.0),
                    cell("mystery", "Mystery", 2.0, -2.0),
                ),
            ),
            comparison.NWayComparisonRow(
                term="rocket",
                display_order=2,
                reference_value=3.0,
                reference_raw_count=3,
                reference_document_count=2,
                reference_token_denominator=20,
                reference_document_denominator=3,
                panels=(
                    cell("fantasy", "Fantasy", 2.0, -1.0),
                    cell("mystery", "Mystery", 8.0, 5.0),
                ),
            ),
        ),
        manifest={
            "reference": {"label": "Whole corpus"},
            "panels": [
                {"key": "fantasy", "label": "Fantasy"},
                {"key": "mystery", "label": "Mystery"},
            ],
            "metric": {
                "name": "per_million",
                "denominator": "auto",
                "effective_denominator": "included_tokens",
            },
        },
    )


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


class TestPlotWordFrequencyBarChart(unittest.TestCase):
    """Tests for plot_word_frequency_bar_chart."""

    def tearDown(self):
        plt.close("all")

    def test_returns_fig_ax(self):
        """Function returns a (fig, ax) tuple."""
        with capture.suppress_output():
            fig, ax = rendering.plot_word_frequency_bar_chart(_make_counts())
        self.assertIsInstance(fig, plt.Figure)
        self.assertIsNotNone(ax)

    def test_title_and_labels(self):
        """Title and axis labels are word-frequency-specific, not genre-specific."""
        with capture.suppress_output():
            _, ax = rendering.plot_word_frequency_bar_chart(_make_counts())
        self.assertEqual(ax.get_title(), "Word Frequency")
        self.assertEqual(ax.get_xlabel(), "Word")
        self.assertEqual(ax.get_ylabel(), "Frequency")


class TestPlotWordFrequencyWordcloud(unittest.TestCase):
    """Tests for plot_word_frequency_wordcloud."""

    def tearDown(self):
        plt.close("all")

    def test_returns_fig_ax(self):
        """Function returns a (fig, ax) tuple."""
        with capture.suppress_output():
            fig, ax = rendering.plot_word_frequency_wordcloud(_make_counts())
        self.assertIsInstance(fig, plt.Figure)
        self.assertIsNotNone(ax)

    def test_title_is_word_frequency_specific(self):
        """Title is word-frequency-specific, not genre-specific."""
        with capture.suppress_output():
            _, ax = rendering.plot_word_frequency_wordcloud(_make_counts())
        self.assertEqual(ax.get_title(), "Word Frequency Word Cloud")


class TestPlotTfidfBarChart(unittest.TestCase):
    """Tests for plot_tfidf_bar_chart."""

    def tearDown(self):
        plt.close("all")

    def test_returns_fig_ax(self):
        """Function returns a (fig, ax) tuple."""
        with capture.suppress_output():
            fig, ax = rendering.plot_tfidf_bar_chart({"dragon": 0.5, "castle": 0.3})
        self.assertIsInstance(fig, plt.Figure)
        self.assertIsNotNone(ax)

    def test_title_and_labels(self):
        """Title and axis labels are TF-IDF-specific."""
        with capture.suppress_output():
            _, ax = rendering.plot_tfidf_bar_chart({"dragon": 0.5})
        self.assertEqual(ax.get_title(), "TF-IDF Top Terms")
        self.assertEqual(ax.get_xlabel(), "Term")
        self.assertEqual(ax.get_ylabel(), "Mean TF-IDF score")


class TestPlotTopicBarChart(unittest.TestCase):
    """Tests for plot_topic_bar_chart."""

    def tearDown(self):
        plt.close("all")

    def test_returns_fig_ax(self):
        """Function returns a (fig, ax) tuple."""
        with capture.suppress_output():
            fig, ax = rendering.plot_topic_bar_chart(
                {"dragon": 0.5, "castle": 0.3}, topic_label="topic_0"
            )
        self.assertIsInstance(fig, plt.Figure)
        self.assertIsNotNone(ax)

    def test_title_includes_topic_label(self):
        """Title and axis labels are topic-specific."""
        with capture.suppress_output():
            _, ax = rendering.plot_topic_bar_chart(
                {"dragon": 0.5}, topic_label="topic_0"
            )
        self.assertEqual(ax.get_title(), "Topic: topic_0")
        self.assertEqual(ax.get_xlabel(), "Term")
        self.assertEqual(ax.get_ylabel(), "Weight")


class TestPlotBarChartGeneric(unittest.TestCase):
    """Tests for the shared plot_bar_chart primitive."""

    def tearDown(self):
        plt.close("all")

    def test_custom_title_and_labels(self):
        """Custom title/labels are applied, confirming genre/word wrappers share this primitive."""
        with capture.suppress_output():
            _, ax = rendering.plot_bar_chart(
                _make_counts(), title="Custom", xlabel="X", ylabel="Y"
            )
        self.assertEqual(ax.get_title(), "Custom")
        self.assertEqual(ax.get_xlabel(), "X")
        self.assertEqual(ax.get_ylabel(), "Y")


class TestPlotWordcloudGeneric(unittest.TestCase):
    """Tests for the shared plot_wordcloud primitive."""

    def tearDown(self):
        plt.close("all")

    def test_custom_title(self):
        """Custom title is applied, confirming genre/word wrappers share this primitive."""
        with capture.suppress_output():
            _, ax = rendering.plot_wordcloud(_make_counts(), title="Custom Cloud")
        self.assertEqual(ax.get_title(), "Custom Cloud")


class TestPlotMirroredComparison(unittest.TestCase):
    """Tests for mirrored comparative charts."""

    def tearDown(self):
        plt.close("all")

    def test_preserves_term_order_and_labels_axes(self):
        """Mirrored bars use the authoritative row order and metric labels."""
        with capture.suppress_output():
            _, ax = rendering.plot_mirrored_comparison(_comparison_result())

        self.assertEqual(
            [label.get_text() for label in ax.get_yticklabels()], ["dragon", "rocket"]
        )
        self.assertIn("Left: raw count", ax.get_xlabel())
        self.assertIn("Right: raw count", ax.get_xlabel())

    def test_save_path_writes_file(self):
        """Mirrored comparison figures can be written to disk."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path = f.name
        try:
            with capture.suppress_output():
                rendering.plot_mirrored_comparison(_comparison_result(), save_path=path)
            self.assertTrue(os.path.getsize(path) > 0)
        finally:
            os.unlink(path)

    def test_mixed_metrics_use_independent_scales(self):
        """Mixed mirrored metrics get separately labeled and scaled axes."""
        result = _comparison_result(
            left_metric={
                "name": "raw_count",
                "denominator": "auto",
                "effective_denominator": "none",
            },
            right_metric={
                "name": "per_million",
                "denominator": "auto",
                "effective_denominator": "included_tokens",
            },
        )

        with capture.suppress_output():
            fig, ax = rendering.plot_mirrored_comparison(result)

        self.assertIs(ax, fig.axes[0])
        self.assertEqual(len(fig.axes), 2)
        self.assertIn("Left: raw count", fig.axes[0].get_xlabel())
        self.assertIn("Right: per million", fig.axes[1].get_xlabel())
        self.assertGreater(fig.axes[0].get_xlim()[0], fig.axes[0].get_xlim()[1])
        self.assertNotEqual(fig.axes[0].get_xlim(), fig.axes[1].get_xlim())


class TestPlotReferenceOverlayComparison(unittest.TestCase):
    """Tests for reference-overlay comparative charts."""

    def tearDown(self):
        plt.close("all")

    def test_draws_reference_target_and_difference_layers(self):
        """Overlay charts expose reference, overlap, excess, and deficit marks."""
        with capture.suppress_output():
            _, ax = rendering.plot_reference_overlay_comparison(_comparison_result())

        self.assertEqual(
            [label.get_text() for label in ax.get_yticklabels()], ["dragon", "rocket"]
        )
        self.assertGreaterEqual(len(ax.patches), 8)
        legend_labels = [text.get_text() for text in ax.get_legend().get_texts()]
        self.assertIn("target excess", legend_labels)
        self.assertIn("target deficit", legend_labels)

    def test_mismatched_metrics_raise_before_plotting(self):
        """Reference overlays reject incommensurate metric provenance."""
        result = _comparison_result()
        result.manifest["metrics"]["right"] = {
            "name": "per_million",
            "denominator": "auto",
            "effective_denominator": "included_tokens",
        }

        with self.assertRaises(ValueError):
            rendering.plot_reference_overlay_comparison(result)


class TestPlotNWayDeviationComparison(unittest.TestCase):
    """Tests for the reusable reference-to-many deviation grid."""

    def tearDown(self):
        plt.close("all")

    def test_joint_symmetric_scale_is_shared_by_all_panels(self):
        """Every genre panel uses the same negative-to-positive scale."""
        with capture.suppress_output():
            _, axes = rendering.plot_nway_deviation_comparison(_nway_result())

        limits = [axis.get_xlim() for axis in axes["panels"].values()]
        self.assertTrue(all(limit == limits[0] for limit in limits))
        self.assertAlmostEqual(abs(limits[0][0]), limits[0][1])

    def test_extrema_modes_select_expected_cells(self):
        """Off, per-genre, and global scopes implement distinct selections."""
        result = _nway_result()

        self.assertEqual(rendering.nway_extrema_cells(result, "off"), set())
        self.assertEqual(
            rendering.nway_extrema_cells(result, "per-genre"),
            {
                ("fantasy", "dragon"),
                ("fantasy", "rocket"),
                ("mystery", "dragon"),
                ("mystery", "rocket"),
            },
        )
        self.assertEqual(
            rendering.nway_extrema_cells(result, "global"),
            {("mystery", "dragon"), ("mystery", "rocket")},
        )

    def test_fractional_tick_labels_preserve_nonzero_values(self):
        """Normalized fractional metrics do not render as misleading zeros."""
        self.assertEqual(rendering._unsigned_tick_label(10_000), "10,000")
        self.assertEqual(rendering._unsigned_tick_label(0.125), "0.125")
        self.assertEqual(rendering._signed_tick_label(-0.125), "-0.125")
        self.assertEqual(rendering._signed_tick_label(0.125), "+0.125")

    def test_highlight_off_omits_extrema_legend_entries(self):
        """The disabled mode does not advertise dark extrema marks."""
        with capture.suppress_output():
            fig, _ = rendering.plot_nway_deviation_comparison(
                _nway_result(), highlight="off"
            )

        labels = [text.get_text() for text in fig.legends[0].get_texts()]
        self.assertFalse(any(label.startswith("Most ") for label in labels))
        self.assertEqual(len(labels), 3)

    def test_save_path_writes_file(self):
        """The N-way figure can be written for handoff."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path = f.name
        try:
            with capture.suppress_output():
                rendering.plot_nway_deviation_comparison(_nway_result(), save_path=path)
            self.assertTrue(os.path.getsize(path) > 0)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
