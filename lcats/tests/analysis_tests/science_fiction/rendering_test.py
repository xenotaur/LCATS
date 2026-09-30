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


if __name__ == "__main__":
    unittest.main()
