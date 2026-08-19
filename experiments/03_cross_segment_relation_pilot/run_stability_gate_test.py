"""Unit tests for run_stability_gate.py.

These tests cover the stability-gate helper's parsing, pricing, and
validation behavior without making real API calls.
"""

from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import run_stability_gate  # noqa: E402


class TestStorySet(unittest.TestCase):
    def test_committed_story_set_is_exactly_two_wellformed_stories(self):
        stories = run_stability_gate._load_story_set(run_stability_gate._fixtures_dir())

        self.assertEqual(
            [story.story_id for story in stories],
            list(run_stability_gate.EXPECTED_STORY_IDS),
        )
        self.assertEqual([story.genre for story in stories], ["science fiction"] * 2)

    def test_gate_manifest_does_not_replace_run_pilot_default_manifest(self):
        fixtures_dir = run_stability_gate._fixtures_dir()

        default_manifest = (fixtures_dir / "manifest.txt").read_text(encoding="utf-8")
        gate_manifest = (
            fixtures_dir / run_stability_gate.STABILITY_MANIFEST
        ).read_text(encoding="utf-8")

        self.assertIn("fixtures/five_o_clock_tea_farce:romance", default_manifest)
        self.assertNotIn("fixtures/unwelcomed_visitor", default_manifest)
        self.assertIn("fixtures/unwelcomed_visitor:science fiction", gate_manifest)


class TestPricing(unittest.TestCase):
    def test_compute_cost_usd_uses_input_and_output_rates(self):
        cost = run_stability_gate._compute_cost_usd(
            1_000_000, 1_000_000, "claude-opus-4-8"
        )

        self.assertEqual(cost, 30.0)

    def test_compute_cost_usd_returns_none_for_unknown_model(self):
        self.assertIsNone(
            run_stability_gate._compute_cost_usd(1, 1, "not-a-priced-model")
        )


class TestValidation(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.output_dir = pathlib.Path(self._tmp.name)
        self.stories = [
            run_stability_gate.FixtureStory(
                "fixtures__king_of_the_hill",
                "fixtures/king_of_the_hill",
                "science fiction",
                pathlib.Path("king/story.json"),
            ),
            run_stability_gate.FixtureStory(
                "fixtures__unwelcomed_visitor",
                "fixtures/unwelcomed_visitor",
                "science fiction",
                pathlib.Path("visitor/story.json"),
            ),
        ]

    def tearDown(self):
        self._tmp.cleanup()

    def _write_outputs(self):
        story_rows = [
            {
                "story_id": story.story_id,
                "genre": story.genre,
                "path": str(story.path),
                "excluded": False,
                "exclude_reason": "",
                "word_count": 100,
                "segment_count": 2,
                "cross_segment_relation_count": 1,
                "weakly_inferred_cross_segment_relation_count": 0,
                "cross_segment_density_per_1000_words": 10.0,
                "weakly_inferred_cross_segment_density_per_1000_words": 0.0,
                "folded_relations_per_1000_words": 10.0,
                "folded_weakly_inferred_relations_per_1000_words": 0.0,
            }
            for story in self.stories
        ]
        (self.output_dir / "pilot_stories.jsonl").write_text(
            "\n".join(json.dumps(row) for row in story_rows) + "\n",
            encoding="utf-8",
        )
        usage_rows = []
        for story in self.stories:
            for stage in run_stability_gate.EXPECTED_STAGES:
                usage_rows.append(
                    {
                        "story_id": story.story_id,
                        "pass_name": stage,
                        "input_tokens": 10,
                        "output_tokens": 2,
                        "is_llm_backed": True,
                        "model": "claude-opus-4-8",
                    }
                )
        (self.output_dir / "pilot_usage.jsonl").write_text(
            "\n".join(json.dumps(row) for row in usage_rows) + "\n",
            encoding="utf-8",
        )
        (self.output_dir / "pilot_summary.json").write_text(
            json.dumps(
                {
                    "backend": "anthropic",
                    "by_genre": {
                        genre: {
                            "included_count": 0,
                            "excluded_count": 0,
                            "mean_cross_segment_density_per_1000_words": 0.0,
                            "mean_weakly_inferred_cross_segment_density_per_1000_words": 0.0,
                            "mean_folded_relations_per_1000_words": 0.0,
                            "mean_folded_weakly_inferred_relations_per_1000_words": 0.0,
                        }
                        for genre in run_stability_gate.run_pilot.GENRES
                    },
                    "candidates_scanned": 0,
                    "dry_run": False,
                    "model": "claude-opus-4-8",
                    "sample_size_target": 5,
                    "stage_models": {
                        "cross_segment_relation": "claude-opus-4-8",
                        "discourse": "claude-opus-4-8",
                        "entity": "claude-opus-4-8",
                        "event": "claude-opus-4-8",
                        "genre_detect": "claude-opus-4-8",
                        "relation": "claude-opus-4-8",
                        "segment": "claude-opus-4-8",
                    },
                }
            ),
            encoding="utf-8",
        )

    def test_validate_outputs_passes_clean_artifacts(self):
        self._write_outputs()
        genre_results = {
            "results": [
                {
                    "story_id": story.story_id,
                    "expected_genre": story.genre,
                    "detected_genre": story.genre,
                    "genre_correct": True,
                    "schema_valid": True,
                    "truncation_marked": False,
                    "wellformed": True,
                }
                for story in self.stories
            ],
            "total_input_tokens": 20,
            "total_output_tokens": 6,
        }

        results = run_stability_gate._validate_outputs(
            self.output_dir,
            self.stories,
            {"returncode": 0},
            genre_results,
            "claude-opus-4-8",
            False,
        )

        self.assertTrue(results["mechanical_validation"]["mechanical_pass"])
        self.assertEqual(results["usage_totals"]["total_input_tokens"], 160)

    def test_validate_outputs_fails_genre_mismatch(self):
        self._write_outputs()
        genre_results = {
            "results": [
                {
                    "story_id": "fixtures__king_of_the_hill",
                    "expected_genre": "science fiction",
                    "detected_genre": "western",
                    "genre_correct": False,
                    "schema_valid": True,
                    "truncation_marked": False,
                    "wellformed": True,
                }
            ],
            "total_input_tokens": 10,
            "total_output_tokens": 3,
        }

        results = run_stability_gate._validate_outputs(
            self.output_dir,
            self.stories,
            {"returncode": 0},
            genre_results,
            "claude-opus-4-8",
            False,
        )

        self.assertFalse(results["mechanical_validation"]["mechanical_pass"])
        self.assertEqual(results["final_recommendation"], "fail_no_go")
        self.assertIn(
            "1 genre-detection result(s) failed",
            results["mechanical_validation"]["errors"],
        )

    def test_validate_outputs_allows_dry_run_segment_stub(self):
        self._write_outputs()
        usage_rows = []
        for story in self.stories:
            for stage in run_stability_gate.EXPECTED_STAGES - {
                "segment",
                "story_relation",
            }:
                usage_rows.append(
                    {
                        "story_id": story.story_id,
                        "pass_name": stage,
                        "input_tokens": 10,
                        "output_tokens": 2,
                        "is_llm_backed": True,
                        "model": "claude-opus-4-8",
                    }
                )
        (self.output_dir / "pilot_usage.jsonl").write_text(
            "\n".join(json.dumps(row) for row in usage_rows) + "\n",
            encoding="utf-8",
        )
        genre_results = {
            "results": [
                {
                    "story_id": story.story_id,
                    "expected_genre": story.genre,
                    "detected_genre": story.genre,
                    "genre_correct": True,
                    "schema_valid": True,
                    "truncation_marked": False,
                    "wellformed": True,
                }
                for story in self.stories
            ],
            "total_input_tokens": 20,
            "total_output_tokens": 6,
        }

        results = run_stability_gate._validate_outputs(
            self.output_dir,
            self.stories,
            {"returncode": 0},
            genre_results,
            "claude-opus-4-8",
            True,
        )

        self.assertTrue(results["mechanical_validation"]["mechanical_pass"])

    def test_validate_outputs_requires_cross_segment_stage_in_real_run(self):
        self._write_outputs()
        usage_rows = []
        for story in self.stories:
            for stage in run_stability_gate.EXPECTED_STAGES - {"story_relation"}:
                usage_rows.append(
                    {
                        "story_id": story.story_id,
                        "pass_name": stage,
                        "input_tokens": 10,
                        "output_tokens": 2,
                        "is_llm_backed": True,
                        "model": "claude-opus-4-8",
                    }
                )
        (self.output_dir / "pilot_usage.jsonl").write_text(
            "\n".join(json.dumps(row) for row in usage_rows) + "\n",
            encoding="utf-8",
        )
        genre_results = {
            "results": [
                {
                    "story_id": story.story_id,
                    "expected_genre": story.genre,
                    "detected_genre": story.genre,
                    "genre_correct": True,
                    "schema_valid": True,
                    "truncation_marked": False,
                    "wellformed": True,
                }
                for story in self.stories
            ],
            "total_input_tokens": 20,
            "total_output_tokens": 6,
        }

        results = run_stability_gate._validate_outputs(
            self.output_dir,
            self.stories,
            {"returncode": 0},
            genre_results,
            "claude-opus-4-8",
            False,
        )

        self.assertFalse(results["mechanical_validation"]["mechanical_pass"])
        self.assertIn(
            "fixtures__king_of_the_hill: missing usage stages ['story_relation']",
            results["mechanical_validation"]["errors"],
        )

    def test_validate_outputs_reports_cached_completed_stage_with_partial_spend(self):
        self._write_outputs()
        usage_rows = []
        for story in self.stories:
            for stage in run_stability_gate.EXPECTED_STAGES - {"segment"}:
                usage_rows.append(
                    {
                        "story_id": story.story_id,
                        "pass_name": stage,
                        "input_tokens": 10,
                        "output_tokens": 2,
                        "is_llm_backed": True,
                        "model": "claude-opus-4-8",
                    }
                )
            checkpoint_dir = self.output_dir / story.story_id
            checkpoint_dir.mkdir()
            (checkpoint_dir / "segment.json").write_text(
                json.dumps(
                    {
                        "outcome": "success",
                        "fingerprint": {
                            "model": "claude-opus-4-8",
                            "backend": "anthropic",
                        },
                    }
                ),
                encoding="utf-8",
            )
        (self.output_dir / "pilot_usage.jsonl").write_text(
            "\n".join(json.dumps(row) for row in usage_rows) + "\n",
            encoding="utf-8",
        )
        genre_results = {
            "results": [
                {
                    "story_id": story.story_id,
                    "expected_genre": story.genre,
                    "detected_genre": story.genre,
                    "genre_correct": True,
                    "schema_valid": True,
                    "truncation_marked": False,
                    "wellformed": True,
                }
                for story in self.stories
            ],
            "total_input_tokens": 20,
            "total_output_tokens": 6,
        }

        results = run_stability_gate._validate_outputs(
            self.output_dir,
            self.stories,
            {"returncode": 0},
            genre_results,
            "claude-opus-4-8",
            False,
        )

        self.assertFalse(results["mechanical_validation"]["mechanical_pass"])
        self.assertEqual(
            results["mechanical_validation"]["checkpointed_stages_by_story"][
                "fixtures__king_of_the_hill"
            ],
            ["segment"],
        )
        self.assertFalse(results["mechanical_validation"]["spend_evidence_complete"])
        self.assertIn(
            "actual spend evidence is incomplete because 2 required stage(s) "
            "were satisfied by cached checkpoints without current usage rows",
            results["mechanical_validation"]["errors"],
        )

    def test_validate_outputs_rejects_cached_stage_with_wrong_fingerprint(self):
        self._write_outputs()
        usage_rows = []
        for story in self.stories:
            for stage in run_stability_gate.EXPECTED_STAGES - {"segment"}:
                usage_rows.append(
                    {
                        "story_id": story.story_id,
                        "pass_name": stage,
                        "input_tokens": 10,
                        "output_tokens": 2,
                        "is_llm_backed": True,
                        "model": "claude-opus-4-8",
                    }
                )
            checkpoint_dir = self.output_dir / story.story_id
            checkpoint_dir.mkdir()
            (checkpoint_dir / "segment.json").write_text(
                json.dumps(
                    {
                        "outcome": "success",
                        "fingerprint": {"model": "fake-1.0", "backend": "anthropic"},
                    }
                ),
                encoding="utf-8",
            )
        (self.output_dir / "pilot_usage.jsonl").write_text(
            "\n".join(json.dumps(row) for row in usage_rows) + "\n",
            encoding="utf-8",
        )
        genre_results = {
            "results": [
                {
                    "story_id": story.story_id,
                    "expected_genre": story.genre,
                    "detected_genre": story.genre,
                    "genre_correct": True,
                    "schema_valid": True,
                    "truncation_marked": False,
                    "wellformed": True,
                }
                for story in self.stories
            ],
            "total_input_tokens": 20,
            "total_output_tokens": 6,
        }

        results = run_stability_gate._validate_outputs(
            self.output_dir,
            self.stories,
            {"returncode": 0},
            genre_results,
            "claude-opus-4-8",
            False,
        )

        self.assertFalse(results["mechanical_validation"]["mechanical_pass"])
        self.assertEqual(
            results["mechanical_validation"]["checkpointed_stages_by_story"][
                "fixtures__king_of_the_hill"
            ],
            [],
        )
        self.assertIn(
            "fixtures__king_of_the_hill: missing usage stages ['segment']",
            results["mechanical_validation"]["errors"],
        )

    def test_validate_outputs_reports_malformed_story_id_instead_of_crashing(self):
        self._write_outputs()
        row = {
            "genre": "science fiction",
            "path": "fixtures/broken/story.json",
            "word_count": 1,
            "excluded": False,
            "exclude_reason": "",
        }
        (self.output_dir / "pilot_stories.jsonl").write_text(
            json.dumps(row) + "\n", encoding="utf-8"
        )
        genre_results = {
            "results": [
                {
                    "story_id": story.story_id,
                    "expected_genre": story.genre,
                    "detected_genre": story.genre,
                    "genre_correct": True,
                    "schema_valid": True,
                    "truncation_marked": False,
                    "wellformed": True,
                }
                for story in self.stories
            ],
            "total_input_tokens": 20,
            "total_output_tokens": 6,
        }

        results = run_stability_gate._validate_outputs(
            self.output_dir,
            self.stories,
            {"returncode": 0},
            genre_results,
            "claude-opus-4-8",
            False,
        )

        self.assertFalse(results["mechanical_validation"]["mechanical_pass"])
        self.assertIn(
            "1 story row(s) have invalid story_id",
            results["mechanical_validation"]["errors"],
        )

    def test_validate_outputs_fails_incomplete_summary_shape(self):
        self._write_outputs()
        (self.output_dir / "pilot_summary.json").write_text(
            json.dumps({"dry_run": False}), encoding="utf-8"
        )
        genre_results = {
            "results": [
                {
                    "story_id": story.story_id,
                    "expected_genre": story.genre,
                    "detected_genre": story.genre,
                    "genre_correct": True,
                    "schema_valid": True,
                    "truncation_marked": False,
                    "wellformed": True,
                }
                for story in self.stories
            ],
            "total_input_tokens": 20,
            "total_output_tokens": 6,
        }

        results = run_stability_gate._validate_outputs(
            self.output_dir,
            self.stories,
            {"returncode": 0},
            genre_results,
            "claude-opus-4-8",
            False,
        )

        self.assertFalse(results["mechanical_validation"]["mechanical_pass"])
        self.assertIn(
            "pilot_summary.json: missing required field 'backend'",
            results["mechanical_validation"]["errors"],
        )

    def test_missing_artifact_marks_parseable_artifacts_false(self):
        self._write_outputs()
        (self.output_dir / "pilot_summary.json").unlink()
        genre_results = {
            "results": [
                {
                    "story_id": story.story_id,
                    "expected_genre": story.genre,
                    "detected_genre": story.genre,
                    "genre_correct": True,
                    "schema_valid": True,
                    "truncation_marked": False,
                    "wellformed": True,
                }
                for story in self.stories
            ],
            "total_input_tokens": 20,
            "total_output_tokens": 6,
        }

        results = run_stability_gate._validate_outputs(
            self.output_dir,
            self.stories,
            {"returncode": 0},
            genre_results,
            "claude-opus-4-8",
            False,
        )

        self.assertFalse(results["mechanical_validation"]["parseable_artifacts"])
        self.assertEqual(
            results["mechanical_validation"]["missing_artifacts"],
            ["pilot_summary.json"],
        )

    def test_render_report_uses_recorded_semantic_review(self):
        results = {
            "dry_run": False,
            "model": "claude-opus-4-8",
            "mechanical_validation": {
                "mechanical_pass": False,
                "completed_story_count": 1,
                "genre_correct_count": 2,
                "genre_total_count": 2,
                "wellformed_count": 2,
                "fatal_pilot_errors": 0,
                "schema_invalid_or_truncation_marked_final_artifacts": 0,
                "excluded_story_reasons": {},
                "checkpointed_stages_by_story": {},
                "spend_evidence_complete": True,
                "errors": [],
            },
            "usage_totals": {
                "total_input_tokens": 1,
                "total_output_tokens": 2,
                "actual_cost_usd": 0.01,
            },
            "semantic_review": {
                "status": "reviewed_fail",
                "source_supported_semantic_output": False,
                "intended_purpose_fit": False,
                "notes": ["Concrete note."],
            },
            "final_recommendation": "fail_no_go",
        }
        genre_results = {"results": []}

        report = run_stability_gate._render_report(results, genre_results)

        self.assertIn("Status: `reviewed_fail`", report)
        self.assertIn("Concrete note.", report)
        self.assertNotIn("pending real-output review", report)


if __name__ == "__main__":
    unittest.main()
