"""Tests for human-facing science-fiction sidecar rendering."""

from __future__ import annotations

import json
import pathlib
import unittest

from lcats.analysis.science_fiction import rendering


class ScienceFictionRenderingTest(unittest.TestCase):
    def setUp(self):
        path = pathlib.Path(
            "experimental/science_fiction_analysis_trial/results/worldcon_spike/"
            "opus_staged/canary-20260930T000426Z/lovecraft/"
            "the_colour_out_of_space/science-fiction.json"
        )
        self.data = json.loads(path.read_text(encoding="utf-8"))
        control_path = pathlib.Path(
            "experimental/science_fiction_analysis_trial/results/worldcon_spike/"
            "opus_staged/canary-20260930T000426Z/anderson/bell/science-fiction.json"
        )
        self.control_data = json.loads(control_path.read_text(encoding="utf-8"))

    def test_summary_uses_human_facing_scores(self):
        result = rendering.render_sidecar(
            self.data,
            title="The Colour out of Space",
            author="H. P. Lovecraft",
        )

        self.assertIn("The Colour out of Space — H. P. Lovecraft", result)
        self.assertIn("Knight Score:** Science Fiction (5 / 7 criteria)", result)
        self.assertIn("Suvin Score:** Novum Present — qualified and dominant", result)
        self.assertNotIn("Supporting evidence", result)

    def test_detailed_formats_include_scorecard_and_anchored_evidence(self):
        for output_format, markers in {
            "markdown": ("### Knight scorecard", "Supporting evidence", "sfev-"),
            "html": ("<h3>Knight scorecard</h3>", "<blockquote>", "sfev-"),
            "latex": ("\\subsection*{Knight scorecard}", "\\begin{quote}", "sfev-"),
        }.items():
            with self.subTest(output_format=output_format):
                result = rendering.render_sidecar(
                    self.data,
                    output_format=output_format,
                    detail="detailed",
                    title="The Colour out of Space",
                    author="H. P. Lovecraft",
                )
                for marker in markers:
                    self.assertIn(marker, result)

    def test_render_json_loads_a_sidecar(self):
        path = pathlib.Path(
            "experimental/science_fiction_analysis_trial/results/worldcon_spike/"
            "opus_staged/canary-20260930T000426Z/lovecraft/"
            "the_colour_out_of_space/science-fiction.json"
        )

        self.assertIn("Analysis status", rendering.render_json(path))

    def test_invalid_format_and_detail_are_rejected(self):
        with self.assertRaises(ValueError):
            rendering.render_sidecar(self.data, output_format="text")
        with self.assertRaises(ValueError):
            rendering.render_sidecar(self.data, detail="full")

    def test_html_and_latex_escape_story_text(self):
        data = json.loads(json.dumps(self.data))
        data["lcats_id"] = "a_<danger>_50%"

        html_result = rendering.render_sidecar(data, output_format="html")
        latex_result = rendering.render_sidecar(
            data, output_format="latex", title="a_<danger>_50%"
        )

        self.assertIn("&lt;Danger&gt;", html_result)
        self.assertIn(r"\_", latex_result)
        self.assertIn(r"\%", latex_result)

    def test_comparison_table_named_features_and_both_summaries(self):
        result = rendering.render_comparison_table(
            [
                {
                    "data": self.data,
                    "title": "The Colour out of Space",
                    "author": "H. P. Lovecraft",
                },
                {"data": self.control_data, "title": "The Bell", "author": "Anderson"},
            ]
        )

        self.assertIn("Criterion 1", result)
        self.assertIn("Cognitive validation", result)
        self.assertIn("Knight summary", result)
        self.assertIn("Suvin summary", result)
        self.assertIn("The Bell", result)

    def test_comparison_table_toggles_detail_and_summary_columns(self):
        items = [{"data": self.data, "title": "The Colour out of Space"}]
        detail_only = rendering.render_comparison_table(
            items, include_summary_columns=False
        )
        summary_only = rendering.render_comparison_table(
            items, include_detail_columns=False
        )
        names_off = rendering.render_comparison_table(
            items, named_feature_headers=False
        )
        neither = rendering.render_comparison_table(
            items, include_detail_columns=False, include_summary_columns=False
        )

        self.assertIn("Criterion 1", detail_only)
        self.assertNotIn("Knight summary", detail_only)
        self.assertIn("Knight summary", summary_only)
        self.assertNotIn("Criterion 1", summary_only)
        self.assertIn("K1", names_off)
        self.assertIn("N", names_off)
        self.assertNotIn("Criterion 1", names_off)
        self.assertIn("Story", neither)
        self.assertIn("Author", neither)
        self.assertNotIn("Knight summary", neither)


if __name__ == "__main__":
    unittest.main()
