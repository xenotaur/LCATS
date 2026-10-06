"""Tests for human-facing science-fiction sidecar rendering."""

from __future__ import annotations

import json
import pathlib
import unittest
from copy import deepcopy

from lcats.analysis.science_fiction import rendering


FIXTURES_DIR = pathlib.Path(__file__).parents[1] / "fixtures" / "science_fiction"


class ScienceFictionRenderingTest(unittest.TestCase):
    def setUp(self):
        path = FIXTURES_DIR / "colour_out_of_space.json"
        self.data = json.loads(path.read_text(encoding="utf-8"))
        control_path = FIXTURES_DIR / "unavailable.json"
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
        path = FIXTURES_DIR / "colour_out_of_space.json"

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

        self.assertIn("Knight criterion 1", result)
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

        self.assertIn("Knight criterion 1", detail_only)
        self.assertNotIn("Knight summary", detail_only)
        self.assertIn("Knight summary", summary_only)
        self.assertNotIn("| Knight criterion 1 |", summary_only)
        self.assertIn("K1", names_off)
        self.assertIn("N", names_off)
        self.assertNotIn("| Knight criterion 1 |", names_off)
        self.assertIn("Title", neither)
        self.assertIn("Author", neither)
        self.assertNotIn("Knight summary", neither)

    def test_comparison_table_accepts_explicit_columns_and_sets(self):
        items = [{"data": self.data, "title": "The Colour out of Space"}]
        explicit = rendering.render_comparison_table(
            items,
            columns=(
                "identity",
                "knight_label",
                "knight_score",
                "knight_interval",
                "suvin_novum",
                "suvin_evidence",
            ),
        )
        sets = rendering.render_comparison_table(
            items,
            column_sets=("identity", "knight_evaluation", "suvin_evaluation"),
        )

        for result in (explicit, sets):
            self.assertIn("Knight Label", result)
            self.assertIn("Knight Score", result)
            self.assertIn("Knight Interval", result)
            self.assertIn("Suvin Novum", result)
            self.assertIn("Suvin Evidence", result)
        self.assertNotIn("| Science |", explicit)
        self.assertNotIn("Knight summary", explicit)

    def test_comparison_table_rejects_unknown_or_duplicate_columns(self):
        items = [{"data": self.data}]
        with self.assertRaises(ValueError):
            rendering.render_comparison_table(items, columns=("unknown",))
        with self.assertRaises(ValueError):
            rendering.render_comparison_table(
                items, columns=("identity",), column_sets=("summaries",)
            )
        with self.assertRaises(ValueError):
            rendering.render_comparison_table(items, columns=("story", "story"))

    def test_qualified_without_dominant_is_not_promoted(self):
        data = deepcopy(self.data)
        data["analyses"]["suvin_novum"][0]["dominant_novum_id"] = None

        result = rendering.render_sidecar(data, detail="detailed")

        self.assertIn("Novum Present — qualified", result)
        self.assertNotIn("qualified and dominant", result)
        self.assertNotIn("Dominant Novum", result)
        self.assertIn("no dominant Novum was designated", result)

    def test_comparison_columns_follow_criterion_ids(self):
        data = deepcopy(self.data)
        criteria = data["analyses"]["knight"][0]["criteria"]
        data["analyses"]["knight"][0]["criteria"] = list(reversed(criteria))

        result = rendering.render_comparison_table(
            [{"data": data}], column_sets=("knight_detail",)
        )
        row = result.splitlines()[2]
        cells = [cell.strip() for cell in row.strip("|").split("|")]

        self.assertEqual(cells[0], "P")
        self.assertEqual(cells[6], "P")

    def test_detailed_outputs_include_rationales_and_estrangement_evidence(self):
        for output_format in ("markdown", "html", "latex"):
            with self.subTest(output_format=output_format):
                result = rendering.render_sidecar(
                    self.data, output_format=output_format, detail="detailed"
                )
                self.assertIn("spectroscopy", result)
                self.assertIn("sfev-fixture-estrangement", result)

    def test_unavailable_current_analyses_are_not_rendered_as_negative_or_complete(
        self,
    ):
        data = deepcopy(self.data)
        data["current"] = {
            "evidence_set_id": None,
            "knight_analysis_id": None,
            "suvin_novum_analysis_id": None,
        }

        result = rendering.render_sidecar(data)

        self.assertIn("Analysis status:** Unavailable", result)
        self.assertIn("Knight Score:** Unavailable (0 / 0 criteria)", result)
        self.assertIn("Suvin Score:** Unavailable", result)
        self.assertNotIn("Analysis status:** Complete", result)
        self.assertNotIn("Novum Absent", result)

    def test_latex_escapes_backslashes_in_one_pass(self):
        result = rendering.render_sidecar(
            self.data, output_format="latex", title=r"Title \\ with slash"
        )

        self.assertIn(r"\textbackslash{}", result)
        self.assertNotIn(r"\textbackslash\{\}", result)


if __name__ == "__main__":
    unittest.main()
