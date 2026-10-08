"""Tests for human-facing science-fiction sidecar rendering."""

from __future__ import annotations

import json
import pathlib
import unittest
from copy import deepcopy

from lcats.analysis.science_fiction import models
from lcats.analysis.science_fiction import rendering
from lcats.analysis.science_fiction import sidecar


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


def _with_heinlein(data, **statuses):
    """Return a copy of ``data`` with a current Heinlein analysis injected."""

    data = deepcopy(data)
    evidence_set_id = data["current"]["evidence_set_id"]
    evidence_set = next(
        item
        for item in data["evidence_sets"]
        if item["evidence_set_id"] == evidence_set_id
    )
    evidence_id = evidence_set["records"][0]["evidence_id"]
    criteria = []
    for criterion_id in models.HEINLEIN_CRITERION_IDS:
        status = statuses.get(criterion_id, "present")
        criteria.append(
            {
                "criterion_id": criterion_id,
                "status": status,
                "supporting_evidence": (
                    [{"evidence_set_id": evidence_set_id, "evidence_id": evidence_id}]
                    if status == "present"
                    else []
                ),
                "counterevidence": [],
                "rationale": f"Rationale for {criterion_id}.",
                "confidence": 0.8,
            }
        )
    by_status = {item["criterion_id"]: item["status"] for item in criteria}
    data["analyses"]["heinlein"] = [
        {
            "analysis_id": "heinlein-1",
            "story_hash": data["story_hash"],
            "evidence_set_id": evidence_set_id,
            "criteria": criteria,
            "interval": {
                "definite_count": sum(v == "present" for v in by_status.values()),
                "possible_count": sum(
                    v in {"present", "ambiguous"} for v in by_status.values()
                ),
                "total_count": 5,
            },
            "verdict": models.heinlein_verdict(by_status),
            "provenance": {
                "run_id": "run-1",
                "rubric_version": models.HEINLEIN_RUBRIC_VERSION,
                "model": "fixture-model",
            },
            "status": "complete",
            "failures": [],
        }
    ]
    data["current"]["heinlein_analysis_id"] = "heinlein-1"
    return data, evidence_id


class HeinleinRenderingTest(unittest.TestCase):
    def setUp(self):
        root = pathlib.Path(
            "experimental/science_fiction_analysis_trial/results/worldcon_spike/"
            "opus_staged/canary-20260930T000426Z"
        )
        self.data = json.loads(
            (root / "lovecraft/the_colour_out_of_space/science-fiction.json").read_text(
                encoding="utf-8"
            )
        )
        self.control_data = json.loads(
            (root / "anderson/bell/science-fiction.json").read_text(encoding="utf-8")
        )
        self.heinlein_data, self.evidence_id = _with_heinlein(
            self.data, plausible="ambiguous"
        )

    def test_fixture_is_a_valid_sidecar(self):
        self.assertTrue(sidecar.validate_sidecar(self.heinlein_data).valid)

    def test_sidecars_without_heinlein_render_without_any_heinlein_text(self):
        for output_format in ("markdown", "html", "latex"):
            for detail in ("summary", "detailed"):
                with self.subTest(output_format=output_format, detail=detail):
                    result = rendering.render_sidecar(
                        self.data, output_format=output_format, detail=detail
                    )
                    self.assertNotIn("Heinlein", result)
        table = rendering.render_comparison_table(
            [{"data": self.data}, {"data": self.control_data}]
        )
        self.assertNotIn("Heinlein", table)

    def test_summary_shows_verdict_in_every_format(self):
        expectations = {
            "markdown": "**Heinlein Verdict:** Indeterminate (4–5 / 5 conditions)",
            "html": "<strong>Heinlein Verdict:</strong> Indeterminate (4–5 / 5 conditions)",
            "latex": "\\textbf{Heinlein Verdict:} Indeterminate (4–5 / 5 conditions)",
        }
        for output_format, expected in expectations.items():
            with self.subTest(output_format=output_format):
                result = rendering.render_sidecar(
                    self.heinlein_data, output_format=output_format
                )
                self.assertIn(expected, result)

    def test_existing_header_lines_are_unchanged_when_heinlein_is_added(self):
        before = rendering.render_sidecar(self.data).splitlines()
        after = rendering.render_sidecar(self.heinlein_data).splitlines()

        self.assertEqual(before, [line for line in after if "Heinlein" not in line])

    def test_detailed_output_lists_conditions_rationale_and_evidence(self):
        for output_format in ("markdown", "html", "latex"):
            with self.subTest(output_format=output_format):
                result = rendering.render_sidecar(
                    self.heinlein_data, output_format=output_format, detail="detailed"
                )
                self.assertIn("Heinlein conditions", result)
                self.assertIn("Rationale for causal.", result.replace("\\_", "_"))
                self.assertIn("Heinlein: Indeterminate; 4–5 of 5 conditions.", result)
                self.assertIn(
                    (
                        self.evidence_id.replace("_", "\\_")
                        if output_format == "latex"
                        else self.evidence_id
                    ),
                    result,
                )
        markdown = rendering.render_sidecar(self.heinlein_data, detail="detailed")
        self.assertIn("| Plausible | ambiguous | 0.80 | 0 |", markdown)
        self.assertIn("- Heinlein: fixture-model; rubric `heinlein-five-v1`", markdown)

    def test_all_present_is_labelled_as_meeting_every_condition(self):
        data, _ = _with_heinlein(self.data)

        result = rendering.render_sidecar(data)

        self.assertIn("Meets all five conditions (5 / 5 conditions)", result)

    def test_absent_condition_reads_as_not_meeting_all_five(self):
        data, _ = _with_heinlein(
            self.data, different="absent", essential="absent", causal="absent"
        )

        result = rendering.render_sidecar(data)

        self.assertIn("Does not meet all five conditions (2 / 5 conditions)", result)

    def _failed_unpointed(self):
        """The shape the runner publishes after a Heinlein stage failure."""

        data, _ = _with_heinlein(self.data)
        analysis = data["analyses"]["heinlein"][0]
        analysis["status"] = "failed"
        analysis["failures"] = [
            {
                "stage": "heinlein",
                "kind": "Timeout",
                "message": "t",
                "recoverable": True,
            }
        ]
        for criterion in analysis["criteria"]:
            criterion["status"] = "not_assessable"
            criterion["supporting_evidence"] = []
        analysis["verdict"] = "indeterminate"
        analysis["interval"] = {
            "definite_count": 0,
            "possible_count": 0,
            "total_count": 5,
        }
        del data["current"]["heinlein_analysis_id"]
        return data

    def test_failed_unpointed_heinlein_is_unavailable_with_a_warning(self):
        data = self._failed_unpointed()
        self.assertTrue(sidecar.validate_sidecar(data).valid)

        for output_format in ("markdown", "html", "latex"):
            with self.subTest(output_format=output_format):
                result = rendering.render_sidecar(
                    data, output_format=output_format, detail="detailed"
                )
                self.assertIn("Heinlein Verdict:", result)
                self.assertIn("Unavailable", result)
                self.assertNotIn("conditions)", result)
                self.assertNotIn("Heinlein conditions", result)
                self.assertNotIn("Meets all five", result)
        markdown = rendering.render_sidecar(data, detail="detailed")
        self.assertIn("Heinlein: Unavailable.", markdown)
        self.assertIn("heinlein-1 contains failure records.", markdown)
        self.assertIn(
            "Heinlein analysis is not current and is not shown as a verdict.",
            markdown,
        )

    def test_failed_unpointed_heinlein_shows_unavailable_in_comparisons(self):
        data = self._failed_unpointed()

        table = rendering.render_comparison_table([{"data": data, "title": "Failed"}])
        header, _, row = table.splitlines()[:3]

        self.assertIn("Heinlein summary", header)
        self.assertTrue(row.rstrip(" |").endswith("Heinlein unavailable"))
        self.assertNotIn("Indeterminate", row)

    def test_ambiguity_keeps_the_possible_bound_in_every_summary(self):
        data, _ = _with_heinlein(self.data, human="ambiguous")

        for output_format in ("markdown", "html", "latex"):
            with self.subTest(output_format=output_format):
                result = rendering.render_sidecar(data, output_format=output_format)
                self.assertIn("4–5 / 5 conditions", result)
        clean, _ = _with_heinlein(self.data)
        self.assertIn("(5 / 5 conditions)", rendering.render_sidecar(clean))

    def test_partial_heinlein_without_verdict_has_no_misleading_counts(self):
        data, _ = _with_heinlein(self.data)
        analysis = data["analyses"]["heinlein"][0]
        del analysis["verdict"]
        analysis["criteria"] = analysis["criteria"][:2]

        for output_format in ("markdown", "html", "latex"):
            with self.subTest(output_format=output_format):
                result = rendering.render_sidecar(data, output_format=output_format)
                self.assertIn("Unavailable", result)
                self.assertNotIn("conditions)", result)

    def test_default_comparison_adds_heinlein_columns_only_when_present(self):
        table = rendering.render_comparison_table(
            [
                {"data": self.heinlein_data, "title": "With"},
                {"data": self.control_data, "title": "Without"},
            ]
        )
        header = table.splitlines()[0]

        for name in ("Different", "Essential", "Human", "Causal", "Plausible"):
            self.assertIn(name, header)
        self.assertIn("Heinlein summary", header)
        with_row, without_row = table.splitlines()[2:4]
        self.assertIn("Indeterminate (4/5; interval 4–5)", with_row)
        self.assertTrue(without_row.rstrip(" |").endswith("Heinlein unavailable"))
        compact = rendering.render_comparison_table(
            [{"data": self.heinlein_data}], named_feature_headers=False
        ).splitlines()[0]
        self.assertIn("Dif", compact)
        self.assertNotIn("Different", compact)

    def test_comparison_without_heinlein_is_identical_to_before(self):
        items = [{"data": self.data}, {"data": self.control_data}]

        default = rendering.render_comparison_table(items)

        self.assertNotIn("Heinlein", default)
        self.assertEqual(
            default,
            rendering.render_comparison_table(
                [{"data": deepcopy(self.data)}, {"data": deepcopy(self.control_data)}]
            ),
        )

    def test_explicit_heinlein_column_sets_work_with_and_without_data(self):
        table = rendering.render_comparison_table(
            [
                {"data": self.heinlein_data, "title": "With"},
                {"data": self.data, "title": "Without"},
            ],
            column_sets=("identity", "heinlein_evaluation", "heinlein_detail"),
        )
        lines = table.splitlines()

        self.assertIn("Heinlein Verdict", lines[0])
        self.assertIn("Indeterminate", lines[2])
        self.assertIn("Unavailable", lines[3])
        self.assertIn("P | P | P | P | ?", lines[2])

    def test_comparison_renders_heinlein_in_html_and_latex(self):
        for output_format in ("html", "latex"):
            with self.subTest(output_format=output_format):
                table = rendering.render_comparison_table(
                    [{"data": self.heinlein_data}], output_format=output_format
                )
                self.assertIn("Heinlein summary", table)
                self.assertIn("Indeterminate", table)


if __name__ == "__main__":
    unittest.main()
