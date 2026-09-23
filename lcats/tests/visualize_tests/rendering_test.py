"""Unit tests for lcats.visualize.rendering."""

import copy
import dataclasses
import json
import os
import tempfile
import unittest

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")  # non-interactive backend for testing

from parameterized import parameterized

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


def _analysis_corpus():
    return comparison.ComparisonCorpus(
        documents=(
            comparison.ComparisonDocument(
                "a/one",
                "dragon dragon castle shared",
                candidate_genres=("fantasy",),
            ),
            comparison.ComparisonDocument(
                "b/two",
                "rocket rocket shared castle",
                candidate_genres=("science fiction", "fantasy"),
            ),
            comparison.ComparisonDocument(
                "c/three",
                "detective clue shared clue",
                candidate_genres=("mystery",),
            ),
            comparison.ComparisonDocument(
                "d/four",
                "ghost ghost shared dragon",
                candidate_genres=("horror",),
            ),
        )
    )


def _analysis_nway_result(genres=("fantasy", "mystery", "horror"), **overrides):
    fields = {
        "universe": comparison.UniverseSpec(),
        "reference": comparison.Selector(comparison.SelectorKind.ALL, label="U"),
        "panels": tuple(
            comparison.NWayPanelSpec(
                genre.replace(" ", "_"),
                comparison.Selector(
                    comparison.SelectorKind.GENRE, genre=genre, label=genre
                ),
            )
            for genre in genres
        ),
        "metric": comparison.MetricSpec(comparison.MetricName.PER_MILLION),
        "vocabulary": comparison.NWayVocabularySpec(top_k=5),
    }
    fields.update(overrides)
    fields.setdefault(
        "ordering",
        comparison.NWayOrderingSpec(
            by=comparison.NWayOrdering(fields["vocabulary"].policy.value)
        ),
    )
    return comparison.compare_many(
        _analysis_corpus(), comparison.NWayComparisonSpec(**fields)
    )


def _luminance(color):
    red, green, blue = matplotlib.colors.to_rgb(color)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


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
        self.assertEqual(rendering._compact_tick_label(-0.125, signed=True), "-0.125")
        self.assertEqual(rendering._compact_tick_label(0.125, signed=True), "+0.125")

    @parameterized.expand(
        [
            ("signed_thousands", 6000.0, True, "+6k"),
            ("signed_fractional_thousands", -1500.0, True, "-1.5k"),
            ("unsigned_thousands", 10_000.0, False, "10k"),
            ("zero", 0.0, True, "0"),
            ("small", 250.0, True, "+250"),
        ]
    )
    def test_compact_tick_labels_fit_narrow_panels(self, _name, value, signed, label):
        """N-way ticks abbreviate thousands so adjacent labels do not collide."""
        self.assertEqual(rendering._compact_tick_label(value, signed=signed), label)

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


class TestNWayRenderSpec(unittest.TestCase):
    """Rendering-spec presets and independent configuration fields."""

    def test_default_spec_preserves_standard_layout(self):
        """Defaults keep the original left reference and center word column."""
        spec = rendering.NWayRenderSpec()

        self.assertEqual(spec.preset, rendering.NWayLayoutPreset.STANDARD)
        self.assertEqual(spec.reference_direction, rendering.ReferenceDirection.LEFT)
        self.assertEqual(spec.term_labels, rendering.TermLabelPlacement.CENTER_COLUMN)
        self.assertEqual(spec.scale, rendering.ScalePolicy.SHARED)
        self.assertEqual(spec.highlight, rendering.ExtremaHighlight.PER_GENRE)
        self.assertTrue(spec.hatching)
        self.assertTrue(spec.legend)
        self.assertFalse(spec.row_guides)

    def test_kabob_preset_sets_independent_fields(self):
        """The kabob preset is composed from ordinary, overridable fields."""
        spec = rendering.NWayRenderSpec.from_preset("kabob")

        self.assertEqual(spec.preset, rendering.NWayLayoutPreset.KABOB)
        self.assertEqual(spec.reference_direction, rendering.ReferenceDirection.RIGHT)
        self.assertEqual(spec.term_labels, rendering.TermLabelPlacement.OUTSIDE_RIGHT)
        self.assertTrue(spec.row_guides)
        self.assertEqual(spec.scale, rendering.ScalePolicy.SHARED)

    def test_preset_fields_can_be_overridden(self):
        """Overrides win over preset values and string values are coerced."""
        spec = rendering.NWayRenderSpec.from_preset(
            "kabob", hatching=False, legend=False, highlight="global"
        )

        self.assertFalse(spec.hatching)
        self.assertFalse(spec.legend)
        self.assertEqual(spec.highlight, rendering.ExtremaHighlight.GLOBAL)
        self.assertEqual(spec.to_dict()["highlight"], "global")
        self.assertEqual(spec.to_dict()["preset"], "kabob")

    @parameterized.expand([("zero", 0), ("negative", -2), ("float", 2.5)])
    def test_invalid_max_columns_raise(self, _name, value):
        """Wrapping requires a positive integer column bound."""
        with self.assertRaises(ValueError):
            rendering.NWayRenderSpec(max_columns=value)

    def test_unknown_enum_value_raises(self):
        """Invalid preset or placement names fail fast."""
        with self.assertRaises(ValueError):
            rendering.NWayRenderSpec(term_labels="middle")
        with self.assertRaises(ValueError):
            rendering.NWayRenderSpec.from_preset("skewer")


class TestNWayRenderPlan(unittest.TestCase):
    """Deterministic layout and scale decisions computed before drawing."""

    def test_bands_wrap_in_declared_order(self):
        """Panels fill bands left to right without reordering."""
        self.assertEqual(
            rendering.nway_panel_bands(["a", "b", "c", "d", "e"], 2),
            (("a", "b"), ("c", "d"), ("e",)),
        )
        self.assertEqual(rendering.nway_panel_bands(["a", "b"], 8), (("a", "b"),))

    def test_shared_scale_gives_identical_symmetric_limits(self):
        """The default shared scale makes every panel's limits identical."""
        plan = rendering.build_nway_render_plan(_analysis_nway_result())
        limits = set(plan.panel_limits.values())

        self.assertEqual(len(limits), 1)
        low, high = limits.pop()
        self.assertAlmostEqual(-low, high)
        self.assertEqual(
            plan.to_manifest(_analysis_nway_result())["scale"]["kind"],
            "joint_symmetric",
        )

    def test_independent_scale_is_explicit_in_manifest(self):
        """Independent panel scales are an opt-in that the manifest discloses."""
        result = _analysis_nway_result()
        plan = rendering.build_nway_render_plan(
            result, rendering.NWayRenderSpec(scale="independent")
        )
        scale = plan.to_manifest(result)["scale"]

        self.assertEqual(scale["kind"], "independent_per_panel")
        self.assertIn("not comparable", scale["note"])
        self.assertGreater(len(set(plan.panel_limits.values())), 1)

    def test_layout_manifest_records_positions_and_term_order(self):
        """Wrapping decisions are recorded per panel."""
        result = _analysis_nway_result()
        plan = rendering.build_nway_render_plan(
            result, rendering.NWayRenderSpec(max_columns=2)
        )
        layout = plan.to_manifest(result)["layout"]

        self.assertEqual(layout["bands"], [["fantasy", "mystery"], ["horror"]])
        self.assertEqual(layout["panel_positions"]["horror"], {"band": 2, "column": 1})
        self.assertEqual(layout["term_order"], [row.term for row in result.rows])
        json.dumps(plan.to_manifest(result))

    def test_incommensurate_panel_metric_raises(self):
        """A panel whose metric differs from the shared metric is rejected."""
        result = _analysis_nway_result()
        manifest = copy.deepcopy(result.manifest)
        manifest["panels"][1]["metric"] = {
            "name": "raw_count",
            "denominator": "auto",
            "effective_denominator": "none",
        }
        tampered = comparison.NWayComparisonResult(rows=result.rows, manifest=manifest)

        with self.assertRaisesRegex(ValueError, "incommensurate"):
            rendering.build_nway_render_plan(tampered)

    def test_misaligned_panel_order_raises(self):
        """Rows must carry exactly the manifest panels in declared order."""
        result = _analysis_nway_result()
        rows = tuple(
            dataclasses.replace(row, panels=tuple(reversed(row.panels)))
            for row in result.rows
        )

        with self.assertRaisesRegex(ValueError, "declared order"):
            rendering.build_nway_render_plan(
                comparison.NWayComparisonResult(rows=rows, manifest=result.manifest)
            )

    def test_no_reference_plan_plots_nonnegative_values(self):
        """Without a reference, panels show values on a shared zero-based scale."""
        result = _analysis_nway_result(
            reference=None,
            reference_policy=comparison.NWayReferencePolicy.NONE,
            vocabulary=comparison.NWayVocabularySpec(
                policy=comparison.NWayVocabularyPolicy.MAX_PANEL_VALUE, top_k=5
            ),
        )
        plan = rendering.build_nway_render_plan(result)

        self.assertEqual(plan.plotted_quantity, "value")
        self.assertFalse(plan.has_common_reference)
        self.assertTrue(all(low == 0.0 for low, _ in plan.panel_limits.values()))


class TestPlotNWayLayouts(unittest.TestCase):
    """Figure-level checks for wrapping, presets, and accessible encodings."""

    def tearDown(self):
        plt.close("all")

    def test_wrapping_repeats_reference_and_keeps_one_scale(self):
        """Three panels with two columns wrap into two aligned bands."""
        with capture.suppress_output():
            fig, axes = rendering.plot_nway_deviation_comparison(
                _analysis_nway_result(),
                render_spec=rendering.NWayRenderSpec(max_columns=2),
            )

        self.assertEqual(len(axes["bands"]), 2)
        self.assertTrue(all(band["reference"] is not None for band in axes["bands"]))
        limits = {axis.get_xlim() for axis in axes["panels"].values()}
        self.assertEqual(len(limits), 1)
        fig.canvas.draw()
        self.assertAlmostEqual(
            axes["bands"][0]["panels"][0].get_position().x0,
            axes["bands"][1]["panels"][0].get_position().x0,
            places=3,
        )

    def test_kabob_points_reference_right_with_outside_right_labels(self):
        """The kabob preset reproduces the compact reference-deviation layout."""
        with capture.suppress_output():
            fig, axes = rendering.plot_nway_deviation_comparison(
                _analysis_nway_result(),
                render_spec=rendering.NWayRenderSpec.from_preset("kabob"),
            )
        fig.canvas.draw()
        reference = axes["reference"]
        terms = axes["terms"]
        last_panel = axes["bands"][0]["panels"][-1]

        self.assertEqual(reference.get_xlim()[0], 0)
        self.assertGreater(reference.get_xlim()[1], 0)
        self.assertTrue(all(patch.get_width() >= 0 for patch in reference.patches))
        self.assertGreater(terms.get_position().x0, last_panel.get_position().x1)
        self.assertTrue(all(t.get_ha() == "left" for t in terms.texts))
        self.assertEqual(terms.get_title(), "")
        self.assertGreater(len(last_panel.lines), len(_analysis_nway_result().rows))

    def test_standard_reference_points_left(self):
        """The default reference direction is unchanged."""
        with capture.suppress_output():
            _, axes = rendering.plot_nway_deviation_comparison(_analysis_nway_result())

        self.assertEqual(axes["reference"].get_xlim()[1], 0)
        self.assertTrue(
            all(patch.get_width() <= 0 for patch in axes["reference"].patches)
        )
        self.assertEqual(axes["terms"].get_title(), "Word")

    def test_hatching_off_keeps_direction_as_non_color_sign_cue(self):
        """Without hatching, sign is still encoded by bar direction."""
        with capture.suppress_output():
            _, axes = rendering.plot_nway_deviation_comparison(
                _analysis_nway_result(),
                render_spec=rendering.NWayRenderSpec(hatching=False),
            )
        patches = [p for axis in axes["panels"].values() for p in axis.patches]

        self.assertTrue(all(not patch.get_hatch() for patch in patches))
        self.assertTrue(any(patch.get_width() < 0 for patch in patches))
        self.assertTrue(any(patch.get_width() > 0 for patch in patches))

    def test_grayscale_distinctions_survive_without_color(self):
        """Sign uses distinct hatches; highlights are darker in grayscale."""
        result = _analysis_nway_result()
        plan = rendering.build_nway_render_plan(result)
        with capture.suppress_output():
            _, axes = rendering.plot_nway_deviation_comparison(result)

        hatches = {"below": set(), "above": set()}
        highlighted_luminance = []
        plain_luminance = []
        for key, axis in axes["panels"].items():
            for row, patch in zip(result.rows, axis.patches):
                width = patch.get_width()
                if width < 0:
                    hatches["below"].add(patch.get_hatch())
                elif width > 0:
                    hatches["above"].add(patch.get_hatch())
                if width == 0:
                    continue
                luminance = _luminance(patch.get_facecolor())
                if (key, row.term) in plan.highlighted:
                    highlighted_luminance.append(luminance)
                else:
                    plain_luminance.append(luminance)

        self.assertEqual(len(hatches["below"]), 1)
        self.assertEqual(len(hatches["above"]), 1)
        self.assertNotEqual(hatches["below"], hatches["above"])
        self.assertLess(max(highlighted_luminance), min(plain_luminance) - 0.2)

    def test_independent_scale_is_labeled_on_every_panel(self):
        """Independent scales cannot be mistaken for the shared default."""
        with capture.suppress_output():
            fig, axes = rendering.plot_nway_deviation_comparison(
                _analysis_nway_result(),
                render_spec=rendering.NWayRenderSpec(scale="independent"),
            )

        for axis in axes["panels"].values():
            self.assertIn("independent", axis.get_title().replace("\n", " "))
            self.assertIn("own scale", axis.get_xlabel())
        self.assertIn("Independent panel scales", fig._suptitle.get_text())

    def test_legend_and_row_guides_are_independent_toggles(self):
        """Legend visibility and row guides are separately controllable."""
        with capture.suppress_output():
            fig, axes = rendering.plot_nway_deviation_comparison(
                _analysis_nway_result(),
                render_spec=rendering.NWayRenderSpec(legend=False, row_guides=True),
            )

        self.assertEqual(fig.legends, [])
        rows = len(_analysis_nway_result().rows)
        self.assertEqual(len(axes["panels"]["fantasy"].lines), rows + 1)

    def test_highlight_and_render_spec_together_raise(self):
        """Highlight has one source of truth when a render spec is given."""
        with self.assertRaises(ValueError):
            rendering.plot_nway_deviation_comparison(
                _analysis_nway_result(),
                highlight="global",
                render_spec=rendering.NWayRenderSpec(),
            )

    def test_per_panel_complement_labels_each_panels_reference(self):
        """Per-panel references are named on the panel they apply to."""
        result = _analysis_nway_result(
            reference=None,
            reference_policy=comparison.NWayReferencePolicy.PER_PANEL_COMPLEMENT,
            vocabulary=comparison.NWayVocabularySpec(
                policy=comparison.NWayVocabularyPolicy.MAX_ABSOLUTE_DEVIATION,
                top_k=5,
            ),
        )
        with capture.suppress_output():
            _, axes = rendering.plot_nway_deviation_comparison(result)

        self.assertIsNone(axes["reference"])
        self.assertIn(
            "U - fantasy", axes["panels"]["fantasy"].get_xlabel().replace("\n", " ")
        )

    def test_no_reference_figure_omits_reference_panel(self):
        """The no-reference policy draws values only."""
        result = _analysis_nway_result(
            reference=None,
            reference_policy=comparison.NWayReferencePolicy.NONE,
            vocabulary=comparison.NWayVocabularySpec(
                policy=comparison.NWayVocabularyPolicy.MAX_PANEL_VALUE, top_k=5
            ),
        )
        with capture.suppress_output():
            fig, axes = rendering.plot_nway_deviation_comparison(result)

        self.assertIsNone(axes["reference"])
        self.assertTrue(
            all(
                patch.get_width() >= 0
                for axis in axes["panels"].values()
                for patch in axis.patches
            )
        )
        labels = [text.get_text() for text in fig.legends[0].get_texts()]
        self.assertFalse(any("reference" in label.lower() for label in labels))


if __name__ == "__main__":
    unittest.main()
