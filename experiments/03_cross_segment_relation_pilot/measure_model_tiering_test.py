"""Tests for WI-PILOT-0060's bounded model-tiering measurement script."""

from __future__ import annotations

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import measure_model_tiering  # noqa: E402 - see sys.path.insert above


class _InvalidAssessmentBackend:
    def complete(self, **kwargs):
        tool = kwargs.get("tool") or {}
        if tool.get("name") == "record_story_assessment":
            tool_result = {
                "verdict": "include",
                "wellformed": True,
                "detected_genre": "science fiction",
                "detected_genre_confidence": 0.9,
                "genre_verdict": "detected",
                "secondary_genre": "",
                "specials_verdict": "none",
                "summary": "Invalid raw result.",
                "issues": "not a list",
            }
        else:
            tool_result = {
                "segments": [
                    {
                        "segment_id": 1,
                        "segment_type": "narrative_scene",
                        "start_par_id": 1,
                        "end_par_id": 1,
                        "start_exact": "",
                        "end_exact": "",
                        "start_prefix": "",
                        "end_suffix": "",
                        "start_char": 0,
                        "end_char": 1,
                        "summary": "Dry-run placeholder.",
                        "cohesion": {"time": "", "place": "", "characters": []},
                        "gacd": None,
                        "erac": None,
                        "reason": "dry-run",
                        "confidence": 0.8,
                    }
                ]
            }
        return measure_model_tiering.llm_backend.BackendResponse(
            text="",
            tool_result=tool_result,
            model=kwargs.get("model", "fake-1.0"),
            input_tokens=10,
            output_tokens=3,
            raw=None,
        )


class TestMeasureModelTiering(unittest.TestCase):
    def test_dry_run_comparison_is_limited_to_two_stages_per_model(self):
        report = measure_model_tiering.run_comparison(
            baseline_model="baseline-model",
            candidate_model="candidate-model",
            fixture_root=measure_model_tiering._fixtures_dir(),
            dry_run=True,
        )

        self.assertEqual(
            report["stories"],
            ["fixtures__five_o_clock_tea_farce", "fixtures__king_of_the_hill"],
        )
        self.assertEqual(report["runs"]["baseline"]["calls"], 4)
        self.assertEqual(report["runs"]["candidate"]["calls"], 4)
        self.assertEqual(
            [call["tool_name"] for call in report["runs"]["baseline"]["backend_calls"]],
            [
                "record_story_assessment",
                "record_segments",
                "record_story_assessment",
                "record_segments",
            ],
        )
        self.assertEqual(
            {
                call["requested_model"]
                for call in report["runs"]["candidate"]["backend_calls"]
            },
            {"candidate-model"},
        )

    def test_report_paths_are_repo_relative_for_committed_fixtures(self):
        report = measure_model_tiering.run_comparison(
            baseline_model="baseline-model",
            candidate_model="candidate-model",
            fixture_root=measure_model_tiering._fixtures_dir(),
            dry_run=True,
        )

        self.assertEqual(
            report["fixture_root"],
            "experiments/03_cross_segment_relation_pilot/fixtures",
        )
        self.assertEqual(
            report["ground_truth_path"],
            "experiments/03_cross_segment_relation_pilot/fixtures/genre_ground_truth.json",
        )

    def test_raw_assessment_schema_invalidates_genre_stage(self):
        report = measure_model_tiering.run_comparison(
            baseline_model="baseline-model",
            candidate_model="candidate-model",
            fixture_root=measure_model_tiering._fixtures_dir(),
            dry_run=True,
            backend_factory=_InvalidAssessmentBackend,
        )

        genre_results = [
            row
            for row in report["runs"]["baseline"]["results"]
            if row["stage"] == "genre_detect"
        ]

        self.assertFalse(genre_results[0]["schema_valid"])
        self.assertFalse(genre_results[0]["raw_schema_valid"])
        self.assertIn("issues expected array", genre_results[0]["raw_schema_errors"][0])
        self.assertEqual(
            report["runs"]["baseline"]["stages"]["genre_detect"][
                "secondary_genre_sanitized_count"
            ],
            0,
        )

    def test_pricing_returns_none_for_unverified_model(self):
        self.assertIsNone(
            measure_model_tiering._compute_cost_usd(
                input_tokens=10, output_tokens=3, model="unknown-model"
            )
        )

    def test_known_pricing_uses_input_and_output_rates(self):
        cost = measure_model_tiering._compute_cost_usd(
            input_tokens=1_000_000,
            output_tokens=1_000_000,
            model="claude-haiku-4-5-20251001",
        )

        self.assertEqual(cost, 6.0)


if __name__ == "__main__":
    unittest.main()
