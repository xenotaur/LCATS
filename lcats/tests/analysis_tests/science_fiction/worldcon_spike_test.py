"""Tests for the bounded Worldcon Knight/Novum spike runner."""

from __future__ import annotations

import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch

from experimental.science_fiction_analysis_trial import run_worldcon_spike
from lcats.analysis.science_fiction import sidecar
from lcats.llm import backend as llm_backend
from lcats.utils import checkpoint


class _MalformedToolBackend:
    def complete(self, **_kwargs):
        return llm_backend.BackendResponse(
            text="",
            tool_result="not an object",
            model="malformed-tool",
            input_tokens=11,
            output_tokens=7,
        )


class _MalformedNestedBackend:
    def complete(self, **kwargs):
        payload = json.loads(kwargs["messages"][-1]["content"])
        result = run_worldcon_spike._fake_tool_result(payload)
        result["knight_criteria"].append("not a criterion object")
        result["novum_candidates"].append("not a candidate object")
        result["novum_candidates"][0]["novelty"] = "present but malformed"
        result["novum_candidates"][0]["reader_facing_evidence_ids"] = "evidence-1"
        return llm_backend.BackendResponse(
            text="",
            tool_result=result,
            model="malformed-nested",
            input_tokens=13,
            output_tokens=17,
        )


class _SuvinFailureBackend:
    def __init__(self):
        self.delegate = run_worldcon_spike.DeterministicSpikeBackend()

    def complete(self, **kwargs):
        if kwargs["tool"]["name"] == run_worldcon_spike.SUVIN_TOOL_NAME:
            return llm_backend.BackendResponse(
                text="",
                tool_result="malformed Suvin result",
                model="suvin-failure",
                input_tokens=19,
                output_tokens=5,
            )
        return self.delegate.complete(**kwargs)


class _NoToolCallJsonBackend:
    def complete(self, **kwargs):
        payload = json.loads(kwargs["messages"][-1]["content"])
        result = run_worldcon_spike._fake_stage_result(payload, kwargs["tool"])
        raise llm_backend.NoToolCallError(
            "local runtime returned JSON content without a tool call",
            input_tokens=23,
            output_tokens=31,
            raw_content=json.dumps(result),
        )


class WorldconSpikeRunnerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.manifest_path = run_worldcon_spike.DEFAULT_MANIFEST

    def tearDown(self):
        self.tmp.cleanup()

    def _manifest_with_gate(self, mode: str, **updates) -> pathlib.Path:
        data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        data["gates"][mode].update(updates)
        manifest_path = self.root / f"{mode}-manifest.json"
        manifest_path.write_text(json.dumps(data), encoding="utf-8")
        return manifest_path

    def test_dry_run_reports_smoke_plan_without_outputs(self):
        output_root = self.root / "dry"

        summary = run_worldcon_spike.run_spike(
            run_worldcon_spike.RunnerOptions(
                manifest_path=self.manifest_path,
                output_root=output_root,
                dry_run=True,
            )
        )

        self.assertEqual("dry_run", summary["status"])
        self.assertEqual("smoke", summary["mode"])
        self.assertEqual(3, summary["plan"]["story_count"])
        self.assertEqual([], summary["stories"])
        self.assertFalse((output_root / "worldcon_spike_summary.json").exists())

    def test_fake_smoke_publishes_valid_sidecars_and_report(self):
        output_root = self.root / "smoke"

        summary = run_worldcon_spike.run_spike(
            run_worldcon_spike.RunnerOptions(
                manifest_path=self.manifest_path,
                output_root=output_root,
            )
        )

        self.assertEqual("complete", summary["status"])
        self.assertEqual(3, len(summary["stories"]))
        self.assertTrue((output_root / "worldcon_spike_report.md").exists())
        self.assertTrue((output_root / "worldcon_spike_summary.json").exists())
        for story in summary["stories"]:
            data = sidecar.load_json(pathlib.Path(story["sidecar_path"]))
            self.assertTrue(sidecar.validate_sidecar(data).valid)
            self.assertEqual(story["story_id"], data["lcats_id"])
            self.assertEqual(
                {"definite_count": 3, "possible_count": 3, "total_count": 7},
                story["knight_interval"],
            )
            self.assertEqual(1, story["qualified_novum_count"])

    def test_sample_requires_successful_smoke_summary(self):
        with self.assertRaisesRegex(ValueError, "smoke-summary"):
            run_worldcon_spike.run_spike(
                run_worldcon_spike.RunnerOptions(
                    manifest_path=self.manifest_path,
                    output_root=self.root / "sample",
                    mode=run_worldcon_spike.SAMPLE_MODE,
                )
            )

        smoke_summary_path = self.root / "failed-smoke.json"
        smoke_summary_path.write_text(
            json.dumps({"status": "failed"}),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "successful smoke"):
            run_worldcon_spike.run_spike(
                run_worldcon_spike.RunnerOptions(
                    manifest_path=self.manifest_path,
                    output_root=self.root / "sample",
                    mode=run_worldcon_spike.SAMPLE_MODE,
                    smoke_summary=smoke_summary_path,
                )
            )

    def test_sample_runs_after_smoke_success(self):
        smoke = run_worldcon_spike.run_spike(
            run_worldcon_spike.RunnerOptions(
                manifest_path=self.manifest_path,
                output_root=self.root / "smoke",
            )
        )
        smoke_path = self.root / "smoke" / "worldcon_spike_summary.json"
        self.assertEqual("complete", smoke["status"])

        summary = run_worldcon_spike.run_spike(
            run_worldcon_spike.RunnerOptions(
                manifest_path=self.manifest_path,
                output_root=self.root / "sample",
                mode=run_worldcon_spike.SAMPLE_MODE,
                smoke_summary=smoke_path,
            )
        )

        self.assertEqual("complete", summary["status"])
        self.assertEqual(10, len(summary["stories"]))

    def test_stage_schemas_are_small_strict_provider_contracts(self):
        schemas = (
            (
                run_worldcon_spike._evidence_tool_schema,
                run_worldcon_spike.EVIDENCE_TOOL_NAME,
                "evidence",
                "evidence_type",
            ),
            (
                run_worldcon_spike._knight_tool_schema,
                run_worldcon_spike.KNIGHT_TOOL_NAME,
                "knight_criteria",
                "criterion_id",
            ),
            (
                run_worldcon_spike._suvin_tool_schema,
                run_worldcon_spike.SUVIN_TOOL_NAME,
                "novum_candidates",
                "cognitive_validation",
            ),
        )
        for schema_factory, tool_name, top_key, nested_key in schemas:
            with self.subTest(tool_name=tool_name):
                schema = schema_factory()
                self.assertEqual(tool_name, schema["name"])
                self.assertTrue(schema["strict"])
                self.assertEqual(
                    {"name", "description", "input_schema", "strict"},
                    set(schema),
                )
                item = schema["input_schema"]["properties"][top_key]["items"]
                self.assertIn(nested_key, item["properties"])
                self.assertFalse(item["additionalProperties"])

    def test_suvin_failure_preserves_evidence_and_knight_partial_success(self):
        output_root = self.root / "partial-success"

        with patch.object(
            run_worldcon_spike,
            "_make_backend",
            return_value=_SuvinFailureBackend(),
        ):
            summary = run_worldcon_spike.run_spike(
                run_worldcon_spike.RunnerOptions(
                    manifest_path=self.manifest_path,
                    output_root=output_root,
                    max_stories=1,
                )
            )

        self.assertEqual("complete", summary["status"])
        story = summary["stories"][0]
        self.assertEqual("complete", story["status"])
        self.assertIsNotNone(story["knight_interval"])
        self.assertIsNone(story["qualified_novum_count"])
        sidecar_data = sidecar.load_json(pathlib.Path(story["sidecar_path"]))
        self.assertTrue(sidecar.validate_sidecar(sidecar_data).valid)
        self.assertEqual(1, len(sidecar_data["evidence_sets"]))
        self.assertEqual("complete", sidecar_data["analyses"]["knight"][0]["status"])
        self.assertEqual("failed", sidecar_data["analyses"]["suvin_novum"][0]["status"])
        self.assertEqual(
            [run_worldcon_spike.SUVIN_RECORD_STAGE],
            [item["stage"] for item in sidecar_data["partial_success"]["failed_stages"]],
        )
        self.assertIsNone(sidecar_data["current"]["suvin_novum_analysis_id"])
        raw_stage_path = pathlib.Path(story["raw_response_path"]) / (
            f"{run_worldcon_spike.SUVIN_STAGE}.json"
        )
        quarantine_stage_path = output_root / "_quarantine" / raw_stage_path.parent.name / (
            f"{run_worldcon_spike.SUVIN_STAGE}.json"
        )
        self.assertTrue(raw_stage_path.exists())
        self.assertTrue(quarantine_stage_path.exists())

    def test_no_tool_call_json_fallback_persists_and_completes(self):
        output_root = self.root / "no-tool-call-json"

        with patch.object(
            run_worldcon_spike,
            "_make_backend",
            return_value=_NoToolCallJsonBackend(),
        ):
            summary = run_worldcon_spike.run_spike(
                run_worldcon_spike.RunnerOptions(
                    manifest_path=self.manifest_path,
                    output_root=output_root,
                    max_stories=1,
                )
            )

        self.assertEqual("complete", summary["status"])
        story = summary["stories"][0]
        self.assertEqual("complete", story["status"])
        raw_root = pathlib.Path(story["raw_response_path"])
        self.assertEqual(
            3,
            len(tuple(raw_root.glob("sf_*.json"))),
        )
        events = [
            json.loads(line)["event"]
            for line in (output_root / "worldcon_spike_run_log.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        self.assertEqual(3, events.count("no_tool_call_json_fallback"))

    def test_stop_on_first_failure_flushes_story_artifacts(self):
        output_root = self.root / "stop-first"

        with patch.object(
            run_worldcon_spike,
            "_make_backend",
            return_value=_MalformedToolBackend(),
        ):
            summary = run_worldcon_spike.run_spike(
                run_worldcon_spike.RunnerOptions(
                    manifest_path=self.manifest_path,
                    output_root=output_root,
                    stop_on_first_failure=True,
                )
            )

        self.assertEqual("failed", summary["status"])
        self.assertEqual(1, len(summary["stories"]))
        story = summary["stories"][0]
        self.assertEqual("failed", story["status"])
        self.assertEqual("ValueError", story["failure_kind"])
        self.assertTrue(pathlib.Path(story["raw_response_path"]).exists())
        self.assertTrue(pathlib.Path(story["quarantine_path"]).exists())
        story_rows = (output_root / "worldcon_spike_story_results.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
        self.assertEqual(1, len(story_rows))
        events = [
            json.loads(line)["event"]
            for line in (output_root / "worldcon_spike_run_log.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        self.assertIn("story_quarantined", events)
        self.assertIn("run_stopped", events)

    def test_malformed_nested_tool_output_is_quarantined_not_crashing(self):
        output_root = self.root / "malformed-nested"

        with patch.object(
            run_worldcon_spike,
            "_make_backend",
            return_value=_MalformedNestedBackend(),
        ):
            summary = run_worldcon_spike.run_spike(
                run_worldcon_spike.RunnerOptions(
                    manifest_path=self.manifest_path,
                    output_root=output_root,
                    max_stories=1,
                )
            )

        self.assertEqual("complete", summary["status"])
        self.assertEqual(1, len(summary["stories"]))
        story = summary["stories"][0]
        self.assertEqual("complete", story["status"])
        self.assertTrue(pathlib.Path(story["raw_response_path"]).exists())
        self.assertIsNone(story["quarantine_path"])

    def test_paid_backend_requires_both_manifest_and_cli_approval(self):
        with self.assertRaisesRegex(ValueError, "approve-paid"):
            run_worldcon_spike.run_spike(
                run_worldcon_spike.RunnerOptions(
                    manifest_path=self.manifest_path,
                    output_root=self.root / "paid",
                    backend_kind=run_worldcon_spike.ANTHROPIC_BACKEND,
                    dry_run=True,
                )
            )

        with self.assertRaisesRegex(ValueError, "manifest does not authorize"):
            run_worldcon_spike.run_spike(
                run_worldcon_spike.RunnerOptions(
                    manifest_path=self.manifest_path,
                    output_root=self.root / "paid",
                    backend_kind=run_worldcon_spike.ANTHROPIC_BACKEND,
                    approve_paid=True,
                    dry_run=True,
                )
            )

    def test_paid_backend_requires_pinned_approval_metadata(self):
        missing_pins = self._manifest_with_gate(
            run_worldcon_spike.SMOKE_MODE,
            paid_model_calls_authorized=True,
            estimated_cost_usd=1.0,
            estimated_wall_clock_minutes=5.0,
        )
        with self.assertRaisesRegex(ValueError, "approved_backend"):
            run_worldcon_spike.run_spike(
                run_worldcon_spike.RunnerOptions(
                    manifest_path=missing_pins,
                    output_root=self.root / "paid-missing-pins",
                    backend_kind=run_worldcon_spike.ANTHROPIC_BACKEND,
                    model="claude-opus-4-1",
                    approve_paid=True,
                    dry_run=True,
                )
            )

        mismatch = self._manifest_with_gate(
            run_worldcon_spike.SMOKE_MODE,
            paid_model_calls_authorized=True,
            estimated_cost_usd=1.0,
            approved_backend=run_worldcon_spike.OPENAI_BACKEND,
            approved_model="gpt-5",
            estimated_wall_clock_minutes=5.0,
        )
        with self.assertRaisesRegex(ValueError, "approved_backend"):
            run_worldcon_spike.run_spike(
                run_worldcon_spike.RunnerOptions(
                    manifest_path=mismatch,
                    output_root=self.root / "paid-mismatch",
                    backend_kind=run_worldcon_spike.ANTHROPIC_BACKEND,
                    model="claude-opus-4-1",
                    approve_paid=True,
                    dry_run=True,
                )
            )

        missing_budget = self._manifest_with_gate(
            run_worldcon_spike.SMOKE_MODE,
            paid_model_calls_authorized=True,
            approved_backend=run_worldcon_spike.ANTHROPIC_BACKEND,
            approved_model="claude-opus-4-1",
            estimated_wall_clock_minutes=5.0,
        )
        with self.assertRaisesRegex(ValueError, "estimated_cost_usd"):
            run_worldcon_spike.run_spike(
                run_worldcon_spike.RunnerOptions(
                    manifest_path=missing_budget,
                    output_root=self.root / "paid-missing-budget",
                    backend_kind=run_worldcon_spike.ANTHROPIC_BACKEND,
                    model="claude-opus-4-1",
                    approve_paid=True,
                    dry_run=True,
                )
            )

    def test_full_mode_requires_explicit_full_approval(self):
        smoke_path = self.root / "smoke.json"
        smoke_path.write_text(json.dumps({"status": "complete"}), encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "smoke-summary"):
            run_worldcon_spike.run_spike(
                run_worldcon_spike.RunnerOptions(
                    manifest_path=self.manifest_path,
                    output_root=self.root / "full",
                    mode=run_worldcon_spike.FULL_MODE,
                    approve_full_sample=True,
                    dry_run=True,
                )
            )

        with self.assertRaisesRegex(ValueError, "approve-full-sample"):
            run_worldcon_spike.run_spike(
                run_worldcon_spike.RunnerOptions(
                    manifest_path=self.manifest_path,
                    output_root=self.root / "full",
                    mode=run_worldcon_spike.FULL_MODE,
                    smoke_summary=smoke_path,
                    dry_run=True,
                )
            )

        summary = run_worldcon_spike.run_spike(
            run_worldcon_spike.RunnerOptions(
                manifest_path=self.manifest_path,
                output_root=self.root / "full",
                mode=run_worldcon_spike.FULL_MODE,
                smoke_summary=smoke_path,
                approve_full_sample=True,
                dry_run=True,
            )
        )
        self.assertEqual(146, summary["plan"]["story_count"])

    def test_output_root_guard_rejects_protected_roots(self):
        protected = pathlib.Path(__file__).resolve().parents[4] / "corpora"

        with self.assertRaises(checkpoint.ProtectedRootError):
            run_worldcon_spike.run_spike(
                run_worldcon_spike.RunnerOptions(
                    manifest_path=self.manifest_path,
                    output_root=protected,
                    dry_run=True,
                )
            )


if __name__ == "__main__":
    unittest.main()
