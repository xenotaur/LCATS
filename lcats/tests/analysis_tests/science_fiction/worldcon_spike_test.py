"""Tests for the bounded Worldcon Knight/Novum spike runner."""

from __future__ import annotations

import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch

from experimental.science_fiction_analysis_trial import run_worldcon_spike
from lcats.analysis.science_fiction import preparation
from lcats.analysis.science_fiction import rendering
from lcats.analysis.science_fiction import sidecar
from lcats.llm import backend as llm_backend
from lcats.utils import compat
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


class _KnightUsageFailureBackend:
    def __init__(self):
        self.delegate = run_worldcon_spike.DeterministicSpikeBackend()

    def complete(self, **kwargs):
        if kwargs["tool"]["name"] == run_worldcon_spike.KNIGHT_TOOL_NAME:
            error = RuntimeError("Knight provider failure")
            error.input_tokens = 7
            error.output_tokens = 9
            error.raw_content = "partial Knight response"
            raise error
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


class _MalformedNoToolCallJsonBackend:
    def complete(self, **_kwargs):
        raise llm_backend.NoToolCallError(
            "local runtime returned malformed JSON content",
            input_tokens=2,
            output_tokens=3,
            raw_content="{malformed",
        )


class _EmptyNoToolCallBackend:
    def complete(self, **_kwargs):
        raise llm_backend.NoToolCallError(
            "local runtime returned no tool call or content",
            input_tokens=4,
            output_tokens=5,
            raw_content="",
        )


class _BackendErrorBackend:
    def complete(self, **_kwargs):
        error = RuntimeError("provider disconnected")
        error.input_tokens = 29
        error.output_tokens = 0
        error.raw_content = "partial provider content"
        raise error


class _FailOnceBackend:
    def __init__(self, failure: Exception, target_tool: str):
        self.delegate = run_worldcon_spike.DeterministicSpikeBackend()
        self.failure = failure
        self.target_tool = target_tool
        self.calls = []
        self.responses = []

    def complete(self, **kwargs):
        tool_name = kwargs["tool"]["name"]
        self.calls.append((tool_name, kwargs["max_tokens"]))
        if (
            tool_name == self.target_tool
            and sum(1 for name, _ in self.calls if name == tool_name) == 1
        ):
            raise self.failure
        response = self.delegate.complete(**kwargs)
        self.responses.append(response)
        return response


class _AlwaysTruncatedBackend:
    def __init__(self, target_tool: str):
        self.delegate = run_worldcon_spike.DeterministicSpikeBackend()
        self.target_tool = target_tool
        self.calls = []

    def complete(self, **kwargs):
        tool_name = kwargs["tool"]["name"]
        self.calls.append((tool_name, kwargs["max_tokens"]))
        if tool_name == self.target_tool:
            raise llm_backend.TruncatedResponseError(
                "truncated",
                stop_reason="max_tokens",
                max_tokens=kwargs["max_tokens"],
                input_tokens=5,
                output_tokens=7,
                raw_content="partial",
            )
        return self.delegate.complete(**kwargs)


class _UnexpectedBackend:
    def __init__(self):
        self.calls = 0

    def complete(self, **_kwargs):
        self.calls += 1
        raise AssertionError("backend should not be called for a reused checkpoint")


class _ValidationConnectionBackend:
    def __init__(self):
        self.calls = 0

    def complete(self, **_kwargs):
        self.calls += 1
        raise ValueError("invalid structured output: connection field is malformed")


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

    def test_paid_canary_writes_approval_snapshot_and_decision(self):
        output_root = self.root / "paid-canary"

        with patch.object(
            run_worldcon_spike,
            "_make_backend",
            return_value=run_worldcon_spike.DeterministicSpikeBackend(),
        ):
            summary = run_worldcon_spike.run_spike(
                run_worldcon_spike.RunnerOptions(
                    manifest_path=self.manifest_path,
                    output_root=output_root,
                    mode=run_worldcon_spike.CANARY_MODE,
                    backend_kind=run_worldcon_spike.ANTHROPIC_BACKEND,
                    model="claude-opus-4-8",
                    approve_paid=True,
                )
            )

        snapshot = json.loads(
            (output_root / "approval_snapshot.json").read_text(encoding="utf-8")
        )
        self.assertEqual("pending", snapshot["decision"])
        self.assertEqual(5.0, snapshot["budget_usd"])
        self.assertEqual(5.0, snapshot["cumulative_budget_usd"])
        self.assertEqual(146, snapshot["source_manifest"]["story_count"])
        self.assertIn("schema_sha256", snapshot["configuration"])
        self.assertEqual("proceed", summary["decision"])

        with patch.object(
            run_worldcon_spike,
            "_make_backend",
            return_value=run_worldcon_spike.DeterministicSpikeBackend(),
        ):
            with self.assertRaisesRegex(ValueError, "does not match"):
                run_worldcon_spike.run_spike(
                    run_worldcon_spike.RunnerOptions(
                        manifest_path=self.manifest_path,
                        output_root=output_root,
                        mode=run_worldcon_spike.CANARY_MODE,
                        backend_kind=run_worldcon_spike.ANTHROPIC_BACKEND,
                        model="claude-opus-4-8",
                        approve_paid=True,
                        prior_spend_usd=1.0,
                    )
                )

    def test_paid_gate_rejects_missing_prior_spend_and_bad_source(self):
        sample_manifest = self._manifest_with_gate(
            run_worldcon_spike.SAMPLE_MODE,
            requires_smoke_success=False,
        )
        with self.assertRaisesRegex(ValueError, "prior-spend-usd"):
            run_worldcon_spike.run_spike(
                run_worldcon_spike.RunnerOptions(
                    manifest_path=sample_manifest,
                    output_root=self.root / "missing-prior",
                    mode=run_worldcon_spike.SAMPLE_MODE,
                    backend_kind=run_worldcon_spike.ANTHROPIC_BACKEND,
                    model="claude-opus-4-8",
                    approve_paid=True,
                )
            )

        bad_data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        bad_data["source_worldcon_manifest_sha256"] = "0" * 64
        bad_manifest = self.root / "bad-source-manifest.json"
        bad_manifest.write_text(json.dumps(bad_data), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "sha256"):
            run_worldcon_spike.run_spike(
                run_worldcon_spike.RunnerOptions(
                    manifest_path=bad_manifest,
                    output_root=self.root / "bad-source",
                    mode=run_worldcon_spike.CANARY_MODE,
                    backend_kind=run_worldcon_spike.ANTHROPIC_BACKEND,
                    model="claude-opus-4-8",
                    approve_paid=True,
                )
            )

    def test_budget_stop_preserves_completed_stories_and_records_decision(self):
        manifest_path = self._manifest_with_gate(
            run_worldcon_spike.SMOKE_MODE,
            estimated_cost_usd=3.0,
            estimated_story_cost_usd=2.0,
            cumulative_budget_usd=3.0,
        )
        summary = run_worldcon_spike.run_spike(
            run_worldcon_spike.RunnerOptions(
                manifest_path=manifest_path,
                output_root=self.root / "budget-stop",
            )
        )

        self.assertEqual("budget_stopped", summary["status"])
        self.assertEqual("stop_for_budget", summary["decision"])
        self.assertEqual(1, summary["totals"]["complete"])

    def test_cumulative_budget_stop_uses_prior_stage_spend(self):
        manifest_path = self._manifest_with_gate(
            run_worldcon_spike.SMOKE_MODE,
            estimated_cost_usd=10.0,
            estimated_story_cost_usd=2.0,
            cumulative_budget_usd=10.0,
        )
        summary = run_worldcon_spike.run_spike(
            run_worldcon_spike.RunnerOptions(
                manifest_path=manifest_path,
                output_root=self.root / "cumulative-budget-stop",
                prior_spend_usd=9.0,
            )
        )

        self.assertEqual("budget_stopped", summary["status"])
        self.assertEqual(0, summary["totals"]["complete"])
        self.assertEqual(9.0, summary["totals"]["prior_spend_usd"])

    def test_resume_after_budget_stop_reuses_completed_story(self):
        manifest_path = self._manifest_with_gate(
            run_worldcon_spike.SMOKE_MODE,
            estimated_cost_usd=3.0,
            estimated_story_cost_usd=2.0,
            cumulative_budget_usd=3.0,
        )
        output_root = self.root / "resume-budget-stop"
        first = run_worldcon_spike.run_spike(
            run_worldcon_spike.RunnerOptions(
                manifest_path=manifest_path,
                output_root=output_root,
            )
        )
        self.assertEqual("budget_stopped", first["status"])
        resumed_backend = _UnexpectedBackend()
        with patch.object(
            run_worldcon_spike, "_make_backend", return_value=resumed_backend
        ):
            resumed = run_worldcon_spike.run_spike(
                run_worldcon_spike.RunnerOptions(
                    manifest_path=manifest_path,
                    output_root=output_root,
                    resume=True,
                )
            )
        self.assertEqual("budget_stopped", resumed["status"])
        self.assertEqual(1, resumed["totals"]["complete"])
        self.assertEqual(0, resumed_backend.calls)
        self.assertTrue((output_root / "worldcon_spike_story_results.jsonl").exists())

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
                story["run_id"], data["analyses"]["knight"][0]["provenance"]["run_id"]
            )
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
            [
                item["stage"]
                for item in sidecar_data["partial_success"]["failed_stages"]
            ],
        )
        self.assertIsNone(sidecar_data["current"]["suvin_novum_analysis_id"])
        raw_stage_path = pathlib.Path(story["raw_response_path"]) / (
            f"{run_worldcon_spike.SUVIN_STAGE}.json"
        )
        quarantine_stage_path = (
            output_root
            / "_quarantine"
            / story["run_id"]
            / raw_stage_path.parent.name
            / (f"{run_worldcon_spike.SUVIN_STAGE}.json")
        )
        self.assertTrue(raw_stage_path.exists())
        self.assertTrue(quarantine_stage_path.exists())

    def test_failed_knight_provenance_preserves_backend_usage(self):
        output_root = self.root / "knight-usage-failure"

        with patch.object(
            run_worldcon_spike,
            "_make_backend",
            return_value=_KnightUsageFailureBackend(),
        ):
            summary = run_worldcon_spike.run_spike(
                run_worldcon_spike.RunnerOptions(
                    manifest_path=self.manifest_path,
                    output_root=output_root,
                    max_stories=1,
                )
            )

        story = summary["stories"][0]
        data = sidecar.load_json(pathlib.Path(story["sidecar_path"]))
        knight = data["analyses"]["knight"][0]
        self.assertEqual("failed", knight["status"])
        self.assertEqual(
            {"input": 7, "output": 9},
            knight["provenance"]["token_usage"],
        )

    def test_evidence_failure_quarantine_references_exact_raw_file(self):
        output_root = self.root / "evidence-quarantine-path"

        with patch.object(
            run_worldcon_spike,
            "_make_backend",
            return_value=_MalformedToolBackend(),
        ):
            summary = run_worldcon_spike.run_spike(
                run_worldcon_spike.RunnerOptions(
                    manifest_path=self.manifest_path,
                    output_root=output_root,
                    max_stories=1,
                    stop_on_first_failure=True,
                )
            )

        story = summary["stories"][0]
        raw_path = pathlib.Path(story["raw_response_path"])
        quarantine = pathlib.Path(story["quarantine_path"])
        self.assertTrue(raw_path.is_file())
        self.assertEqual(
            story["raw_response_path"],
            json.loads(quarantine.read_text())["raw_response_path"],
        )

    def test_run_ids_isolate_raw_artifacts_and_jsonl_rows(self):
        output_root = self.root / "reruns"

        first = run_worldcon_spike.run_spike(
            run_worldcon_spike.RunnerOptions(
                manifest_path=self.manifest_path,
                output_root=output_root,
                max_stories=1,
            )
        )
        second = run_worldcon_spike.run_spike(
            run_worldcon_spike.RunnerOptions(
                manifest_path=self.manifest_path,
                output_root=output_root,
                max_stories=1,
            )
        )

        self.assertNotEqual(first["run_id"], second["run_id"])
        self.assertNotEqual(
            first["stories"][0]["raw_response_path"],
            second["stories"][0]["raw_response_path"],
        )
        rows = (
            (output_root / "worldcon_spike_story_results.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        )
        self.assertEqual(2, len(rows))
        self.assertEqual(
            {first["run_id"], second["run_id"]},
            {json.loads(row)["run_id"] for row in rows},
        )

    def test_backend_construction_failure_is_logged_as_run_abort(self):
        output_root = self.root / "backend-construction-failure"

        with patch.object(
            run_worldcon_spike,
            "_make_backend",
            side_effect=RuntimeError("backend unavailable"),
        ):
            with self.assertRaisesRegex(RuntimeError, "backend unavailable"):
                run_worldcon_spike.run_spike(
                    run_worldcon_spike.RunnerOptions(
                        manifest_path=self.manifest_path,
                        output_root=output_root,
                        max_stories=1,
                    )
                )

        events = [
            json.loads(line)
            for line in (output_root / "worldcon_spike_run_log.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        self.assertEqual("run_start", events[0]["event"])
        self.assertEqual("run_aborted_unexpected", events[-1]["event"])
        self.assertEqual(events[0]["run_id"], events[-1]["run_id"])

    def test_final_artifact_failure_is_logged_as_run_abort(self):
        output_root = self.root / "final-artifact-failure"

        with patch.object(
            run_worldcon_spike,
            "_write_report",
            side_effect=OSError("report destination unavailable"),
        ):
            with self.assertRaisesRegex(OSError, "report destination unavailable"):
                run_worldcon_spike.run_spike(
                    run_worldcon_spike.RunnerOptions(
                        manifest_path=self.manifest_path,
                        output_root=output_root,
                        max_stories=1,
                    )
                )

        events = [
            json.loads(line)
            for line in (output_root / "worldcon_spike_run_log.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        self.assertEqual("run_aborted_unexpected", events[-1]["event"])
        self.assertNotIn("run_end", [event["event"] for event in events])

    def test_backend_stage_failure_persists_raw_error_before_quarantine(self):
        output_root = self.root / "backend-stage-failure"
        with patch.object(
            run_worldcon_spike,
            "_make_backend",
            return_value=_BackendErrorBackend(),
        ):
            summary = run_worldcon_spike.run_spike(
                run_worldcon_spike.RunnerOptions(
                    manifest_path=self.manifest_path,
                    output_root=output_root,
                    max_stories=1,
                    stop_on_first_failure=True,
                )
            )

        story = summary["stories"][0]
        raw_error = pathlib.Path(story["raw_response_path"])
        self.assertTrue(raw_error.exists())
        self.assertEqual(
            "partial provider content",
            json.loads(raw_error.read_text(encoding="utf-8"))["raw_content"],
        )
        quarantine = (
            output_root
            / "_quarantine"
            / story["run_id"]
            / pathlib.Path(story["raw_response_path"]).parent.name
            / "story.json"
        )
        self.assertEqual(
            raw_error.parent.resolve(),
            (output_root / "_raw" / story["run_id"] / raw_error.parent.name).resolve(),
        )
        self.assertTrue(quarantine.exists())

    def test_protected_root_consent_is_forwarded_to_logging_and_pipeline(self):
        output_root = self.root / "forwarding"
        real_run_log = run_worldcon_spike.run_log.RunLog
        real_assembly = run_worldcon_spike.pipeline.run_checkpointed_assembly
        real_publish = run_worldcon_spike.pipeline.publish_sidecar
        with (
            patch.object(
                run_worldcon_spike.run_log,
                "RunLog",
                wraps=real_run_log,
            ) as log_factory,
            patch.object(
                run_worldcon_spike.pipeline,
                "run_checkpointed_assembly",
                wraps=real_assembly,
            ) as assembly,
            patch.object(
                run_worldcon_spike.pipeline,
                "publish_sidecar",
                wraps=real_publish,
            ) as publish,
        ):
            run_worldcon_spike.run_spike(
                run_worldcon_spike.RunnerOptions(
                    manifest_path=self.manifest_path,
                    output_root=output_root,
                    max_stories=1,
                    allow_protected_root=True,
                )
            )

        self.assertTrue(log_factory.call_args.kwargs["allow_protected_root"])
        self.assertTrue(assembly.call_args.kwargs["allow_protected_root"])
        self.assertTrue(publish.call_args.kwargs["allow_protected_root"])

    def test_sidecar_provenance_matches_current_code_commit(self):
        output_root = self.root / "commit-match"
        summary = run_worldcon_spike.run_spike(
            run_worldcon_spike.RunnerOptions(
                manifest_path=self.manifest_path,
                output_root=output_root,
                max_stories=1,
            )
        )
        story = summary["stories"][0]
        data = sidecar.load_json(pathlib.Path(story["sidecar_path"]))
        self.assertEqual(run_worldcon_spike._git_commit(), summary["code_commit"])
        self.assertEqual(
            summary["code_commit"],
            data["analyses"]["knight"][0]["provenance"]["code_commit"],
        )

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
        evidence_raw = json.loads(
            (raw_root / "sf_evidence.json").read_text(encoding="utf-8")
        )
        self.assertIsInstance(evidence_raw["tool_result"], dict)
        resumed_backend = _UnexpectedBackend()
        with patch.object(
            run_worldcon_spike, "_make_backend", return_value=resumed_backend
        ):
            resumed = run_worldcon_spike.run_spike(
                run_worldcon_spike.RunnerOptions(
                    manifest_path=self.manifest_path,
                    output_root=output_root,
                    max_stories=1,
                    resume=True,
                )
            )
        self.assertEqual("complete", resumed["status"])
        self.assertEqual(0, resumed_backend.calls)
        events = [
            json.loads(line)["event"]
            for line in (output_root / "worldcon_spike_run_log.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        self.assertEqual(3, events.count("no_tool_call_json_fallback"))

    def test_malformed_no_tool_call_preserves_raw_path_and_usage(self):
        output_root = self.root / "malformed-no-tool-call"

        with patch.object(
            run_worldcon_spike,
            "_make_backend",
            return_value=_MalformedNoToolCallJsonBackend(),
        ):
            summary = run_worldcon_spike.run_spike(
                run_worldcon_spike.RunnerOptions(
                    manifest_path=self.manifest_path,
                    output_root=output_root,
                    max_stories=1,
                    stop_on_first_failure=True,
                )
            )

        story = summary["stories"][0]
        self.assertEqual("failed", story["status"])
        self.assertEqual(2, story["input_tokens"])
        self.assertEqual(3, story["output_tokens"])
        raw_path = pathlib.Path(story["raw_response_path"])
        self.assertEqual(
            run_worldcon_spike.EVIDENCE_STAGE,
            raw_path.stem,
        )
        self.assertEqual("{malformed", json.loads(raw_path.read_text())["text"])
        quarantine = pathlib.Path(story["quarantine_path"])
        self.assertEqual(
            story["raw_response_path"],
            json.loads(quarantine.read_text())["raw_response_path"],
        )

    def test_empty_no_tool_call_persists_backend_failure_and_usage(self):
        output_root = self.root / "empty-no-tool-call"

        with patch.object(
            run_worldcon_spike,
            "_make_backend",
            return_value=_EmptyNoToolCallBackend(),
        ):
            summary = run_worldcon_spike.run_spike(
                run_worldcon_spike.RunnerOptions(
                    manifest_path=self.manifest_path,
                    output_root=output_root,
                    max_stories=1,
                    stop_on_first_failure=True,
                )
            )

        story = summary["stories"][0]
        self.assertEqual("failed", story["status"])
        self.assertEqual(4, story["input_tokens"])
        self.assertEqual(5, story["output_tokens"])
        raw_path = pathlib.Path(story["raw_response_path"])
        self.assertTrue(raw_path.exists())
        self.assertEqual(
            "NoToolCallError",
            json.loads(raw_path.read_text())["backend_error"],
        )

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
        story_rows = (
            (output_root / "worldcon_spike_story_results.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        )
        self.assertEqual(1, len(story_rows))
        events = [
            json.loads(line)["event"]
            for line in (output_root / "worldcon_spike_run_log.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        self.assertIn("story_quarantined", events)
        self.assertIn("run_stopped", events)

    def test_truncation_retries_once_with_higher_limit_and_persists_attempts(self):
        output_root = self.root / "truncation-retry"
        backend = _FailOnceBackend(
            llm_backend.TruncatedResponseError(
                "truncated",
                stop_reason="max_tokens",
                max_tokens=4096,
                input_tokens=5,
                output_tokens=7,
                raw_content="partial",
            ),
            run_worldcon_spike.EVIDENCE_TOOL_NAME,
        )

        with patch.object(run_worldcon_spike, "_make_backend", return_value=backend):
            summary = run_worldcon_spike.run_spike(
                run_worldcon_spike.RunnerOptions(
                    manifest_path=self.manifest_path,
                    output_root=output_root,
                    max_stories=1,
                )
            )

        self.assertEqual("complete", summary["status"])
        evidence_calls = [
            max_tokens
            for name, max_tokens in backend.calls
            if name == run_worldcon_spike.EVIDENCE_TOOL_NAME
        ]
        self.assertEqual([4096, 8192], evidence_calls)
        raw_root = pathlib.Path(summary["stories"][0]["raw_response_path"])
        self.assertTrue((raw_root / "sf_evidence-backend-error.json").exists())
        self.assertTrue((raw_root / "sf_evidence-attempt-2.json").exists())

        retry_payload = json.loads(
            (raw_root / "sf_evidence-attempt-2.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            backend.responses[0].input_tokens, retry_payload["input_tokens"]
        )
        self.assertEqual(
            backend.responses[0].output_tokens, retry_payload["output_tokens"]
        )
        self.assertEqual(8192, retry_payload["effective_max_tokens"])

        resumed_backend = _UnexpectedBackend()
        with patch.object(
            run_worldcon_spike, "_make_backend", return_value=resumed_backend
        ):
            resumed = run_worldcon_spike.run_spike(
                run_worldcon_spike.RunnerOptions(
                    manifest_path=self.manifest_path,
                    output_root=output_root,
                    max_stories=1,
                    resume=True,
                )
            )
        self.assertEqual("complete", resumed["status"])
        self.assertEqual(0, resumed_backend.calls)
        self.assertEqual(0, resumed["totals"]["input_tokens"])

    def test_failed_truncation_preserves_effective_retry_limit(self):
        output_root = self.root / "failed-truncation-retry"
        backend = _AlwaysTruncatedBackend(run_worldcon_spike.KNIGHT_TOOL_NAME)

        with patch.object(run_worldcon_spike, "_make_backend", return_value=backend):
            summary = run_worldcon_spike.run_spike(
                run_worldcon_spike.RunnerOptions(
                    manifest_path=self.manifest_path,
                    output_root=output_root,
                    max_stories=1,
                    stop_on_first_failure=True,
                )
            )

        self.assertEqual("complete", summary["status"])
        story = summary["stories"][0]
        data = sidecar.load_json(pathlib.Path(story["sidecar_path"]))
        knight = data["analyses"]["knight"][0]
        self.assertEqual("failed", knight["status"])
        self.assertEqual(
            8192, knight["provenance"]["generation_parameters"]["max_tokens"]
        )
        raw_root = pathlib.Path(story["raw_response_path"])
        failed_payload = json.loads(
            (raw_root / "sf_knight-backend-error-attempt-2.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(8192, failed_payload["effective_max_tokens"])

    def test_transient_failure_retries_once_and_content_filter_does_not(self):
        output_root = self.root / "typed-retries"
        transient = _FailOnceBackend(
            llm_backend.TransientProviderError(
                "temporary provider failure", input_tokens=3, output_tokens=4
            ),
            run_worldcon_spike.EVIDENCE_TOOL_NAME,
        )
        with patch.object(run_worldcon_spike, "_make_backend", return_value=transient):
            summary = run_worldcon_spike.run_spike(
                run_worldcon_spike.RunnerOptions(
                    manifest_path=self.manifest_path,
                    output_root=output_root,
                    max_stories=1,
                )
            )
        self.assertEqual("complete", summary["status"])
        self.assertEqual(
            2,
            sum(
                1
                for name, _ in transient.calls
                if name == run_worldcon_spike.EVIDENCE_TOOL_NAME
            ),
        )

        class ContentFilterBackend:
            def __init__(self):
                self.calls = 0

            def complete(self, **_kwargs):
                self.calls += 1
                raise RuntimeError("provider content filter rejected request")

        filtered = ContentFilterBackend()
        with patch.object(run_worldcon_spike, "_make_backend", return_value=filtered):
            failed = run_worldcon_spike.run_spike(
                run_worldcon_spike.RunnerOptions(
                    manifest_path=self.manifest_path,
                    output_root=self.root / "content-filter",
                    max_stories=1,
                    stop_on_first_failure=True,
                )
            )
        self.assertEqual("failed", failed["status"])
        self.assertEqual(1, filtered.calls)

    def test_resume_reuses_matching_model_stage_checkpoints(self):
        output_root = self.root / "resume-stages"
        first_backend = run_worldcon_spike.DeterministicSpikeBackend()
        with patch.object(
            run_worldcon_spike, "_make_backend", return_value=first_backend
        ):
            first = run_worldcon_spike.run_spike(
                run_worldcon_spike.RunnerOptions(
                    manifest_path=self.manifest_path,
                    output_root=output_root,
                    max_stories=1,
                    resume=True,
                )
            )
        self.assertEqual("complete", first["status"])

        second_backend = _UnexpectedBackend()
        with patch.object(
            run_worldcon_spike, "_make_backend", return_value=second_backend
        ):
            second = run_worldcon_spike.run_spike(
                run_worldcon_spike.RunnerOptions(
                    manifest_path=self.manifest_path,
                    output_root=output_root,
                    max_stories=1,
                    resume=True,
                )
            )
        self.assertEqual("complete", second["status"])
        self.assertEqual(0, second_backend.calls)
        self.assertEqual(0, second["totals"]["input_tokens"])
        self.assertEqual(0, second["totals"]["output_tokens"])
        second_data = sidecar.load_json(
            pathlib.Path(second["stories"][0]["sidecar_path"])
        )
        self.assertTrue(
            second_data["analyses"]["knight"][0]["provenance"]["generation_parameters"][
                "reused_from_checkpoint"
            ]
        )
        self.assertTrue(
            pathlib.Path(second["stories"][0]["raw_response_path"]).exists()
        )
        self.assertTrue(
            pathlib.Path(second["stories"][0]["raw_response_path"])
            .joinpath("index.json")
            .exists()
        )

    def test_non_resume_run_persists_model_checkpoints_for_later_resume(self):
        output_root = self.root / "ordinary-checkpoints"
        first_backend = run_worldcon_spike.DeterministicSpikeBackend()
        with patch.object(
            run_worldcon_spike, "_make_backend", return_value=first_backend
        ):
            first = run_worldcon_spike.run_spike(
                run_worldcon_spike.RunnerOptions(
                    manifest_path=self.manifest_path,
                    output_root=output_root,
                    max_stories=1,
                )
            )
        self.assertEqual("complete", first["status"])

        second_backend = _UnexpectedBackend()
        with patch.object(
            run_worldcon_spike, "_make_backend", return_value=second_backend
        ):
            second = run_worldcon_spike.run_spike(
                run_worldcon_spike.RunnerOptions(
                    manifest_path=self.manifest_path,
                    output_root=output_root,
                    max_stories=1,
                    resume=True,
                )
            )
        self.assertEqual("complete", second["status"])
        self.assertEqual(0, second_backend.calls)
        events = [
            json.loads(line)["event"]
            for line in (output_root / "worldcon_spike_run_log.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        self.assertGreaterEqual(events.count("stage_reused"), 3)

    def test_resume_reuses_package_relative_raw_paths(self):
        package_root = run_worldcon_spike.paths.find_pyproject_root(
            run_worldcon_spike.__file__
        ).resolve()
        with tempfile.TemporaryDirectory(dir=package_root) as temp_dir:
            output_root = pathlib.Path(temp_dir)
            first = run_worldcon_spike.run_spike(
                run_worldcon_spike.RunnerOptions(
                    manifest_path=self.manifest_path,
                    output_root=output_root,
                    max_stories=1,
                    resume=True,
                )
            )
            self.assertEqual("complete", first["status"])
            second_backend = _UnexpectedBackend()
            with patch.object(
                run_worldcon_spike, "_make_backend", return_value=second_backend
            ):
                second = run_worldcon_spike.run_spike(
                    run_worldcon_spike.RunnerOptions(
                        manifest_path=self.manifest_path,
                        output_root=output_root,
                        max_stories=1,
                        resume=True,
                    )
                )
            self.assertEqual("complete", second["status"])
            self.assertEqual(0, second_backend.calls)

    def test_validation_error_with_transport_word_is_not_retried(self):
        output_root = self.root / "validation-no-retry"
        backend = _ValidationConnectionBackend()
        with patch.object(run_worldcon_spike, "_make_backend", return_value=backend):
            summary = run_worldcon_spike.run_spike(
                run_worldcon_spike.RunnerOptions(
                    manifest_path=self.manifest_path,
                    output_root=output_root,
                    max_stories=1,
                    stop_on_first_failure=True,
                )
            )
        self.assertEqual("failed", summary["status"])
        self.assertEqual(1, backend.calls)

    def test_provider_status_codes_and_overloaded_errors_are_transient(self):
        for status in (429, 500, 502, 503, 504, 529):
            error = RuntimeError(f"provider failure {status}")
            error.status_code = status
            self.assertEqual(
                "transient", run_worldcon_spike._classify_stage_failure(error)
            )
        http_status_error = RuntimeError("provider failure")
        http_status_error.status_code = None
        http_status_error.http_status = 503
        self.assertEqual(
            "transient",
            run_worldcon_spike._classify_stage_failure(http_status_error),
        )
        self.assertEqual(
            "transient",
            run_worldcon_spike._classify_stage_failure(
                RuntimeError("overloaded_error")
            ),
        )

    def test_checkpoint_response_requires_structured_tool_result(self):
        self.assertFalse(
            run_worldcon_spike._valid_checkpoint_response(
                {
                    "model": "fake",
                    "tool_result": None,
                    "raw_response_path": str(self.root / "raw.json"),
                },
                self.root,
            )
        )

    def test_checkpoint_response_rejects_artifact_outside_output_root(self):
        outside = self.root.parent / "outside-raw.json"
        outside.write_text("{}", encoding="utf-8")
        try:
            self.assertFalse(
                run_worldcon_spike._valid_checkpoint_response(
                    {
                        "model": "fake",
                        "tool_result": {},
                        "raw_response_path": str(outside),
                    },
                    self.root,
                )
            )
        finally:
            outside.unlink()

    def test_truncation_retry_records_effective_token_limit_in_provenance(self):
        output_root = self.root / "truncation-provenance"
        backend = _FailOnceBackend(
            llm_backend.TruncatedResponseError(
                "truncated",
                stop_reason="max_tokens",
                max_tokens=4096,
                input_tokens=5,
                output_tokens=7,
            ),
            run_worldcon_spike.KNIGHT_TOOL_NAME,
        )
        with patch.object(run_worldcon_spike, "_make_backend", return_value=backend):
            summary = run_worldcon_spike.run_spike(
                run_worldcon_spike.RunnerOptions(
                    manifest_path=self.manifest_path,
                    output_root=output_root,
                    max_stories=1,
                )
            )
        data = sidecar.load_json(pathlib.Path(summary["stories"][0]["sidecar_path"]))
        self.assertEqual(
            8192,
            data["analyses"]["knight"][0]["provenance"]["generation_parameters"][
                "max_tokens"
            ],
        )

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

    def test_contract_canary_manifest_selects_exact_two_stories(self):
        manifest = run_worldcon_spike.load_manifest(
            run_worldcon_spike.pathlib.Path(
                "experimental/science_fiction_analysis_trial/manifests/contract_canary_manifest.json"
            )
        )
        stories = run_worldcon_spike.select_stories(
            manifest, run_worldcon_spike.CANARY_MODE
        )
        self.assertEqual(
            (
                "mass_quantities/a_case_of_sunburn__fontenay",
                "anderson/bell",
            ),
            tuple(story.story_id for story in stories),
        )
        summary = run_worldcon_spike.run_spike(
            run_worldcon_spike.RunnerOptions(
                manifest_path=manifest.manifest_path,
                output_root=self.root / "canary",
                mode=run_worldcon_spike.CANARY_MODE,
                dry_run=True,
            )
        )
        self.assertEqual(2, summary["plan"]["story_count"])
        self.assertEqual(2, summary["plan"]["max_stories"])

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


class _HeinleinOverrideBackend:
    """Delegate to the deterministic backend, overriding the Heinlein stage."""

    def __init__(self, override=None):
        self.delegate = run_worldcon_spike.DeterministicSpikeBackend()
        self.override = override
        self.tools = []

    def complete(self, **kwargs):
        name = kwargs["tool"]["name"]
        self.tools.append(name)
        response = self.delegate.complete(**kwargs)
        if name == run_worldcon_spike.HEINLEIN_TOOL_NAME and self.override:
            response.tool_result = self.override(response.tool_result)
        return response


def _heinlein_options(root, **updates):
    return run_worldcon_spike.RunnerOptions(
        manifest_path=run_worldcon_spike.DEFAULT_MANIFEST,
        output_root=root,
        max_stories=1,
        include_heinlein=True,
        **updates,
    )


class WorldconSpikeHeinleinStageTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, name, backend=None, **updates):
        backend = backend or _HeinleinOverrideBackend()
        with patch.object(run_worldcon_spike, "_make_backend", return_value=backend):
            summary = run_worldcon_spike.run_spike(
                _heinlein_options(self.root / name, **updates)
            )
        story = summary["stories"][0]
        data = sidecar.load_json(pathlib.Path(story["sidecar_path"]))
        return summary, story, data, backend

    def test_stage_is_off_by_default_and_leaves_outputs_unchanged(self):
        summary = run_worldcon_spike.run_spike(
            run_worldcon_spike.RunnerOptions(
                manifest_path=run_worldcon_spike.DEFAULT_MANIFEST,
                output_root=self.root / "off",
                max_stories=1,
            )
        )
        story = summary["stories"][0]
        data = sidecar.load_json(pathlib.Path(story["sidecar_path"]))

        self.assertNotIn("heinlein_verdict", story)
        self.assertNotIn("heinlein_interval", story)
        self.assertNotIn("heinlein_verdicts", summary["totals"])
        self.assertNotIn("include_heinlein", summary["plan"])
        self.assertNotIn("heinlein", data["analyses"])
        self.assertNotIn("heinlein_analysis_id", data["current"])
        self.assertNotIn("heinlein_prompt_version", str(data["current"]))
        report = (self.root / "off" / "worldcon_spike_report.md").read_text("utf-8")
        self.assertNotIn("Heinlein", report)

    def test_enabled_stage_publishes_valid_sidecar_summary_and_report(self):
        summary, story, data, backend = self._run("on")

        self.assertEqual("complete", summary["status"])
        self.assertEqual("qualifies", story["heinlein_verdict"])
        self.assertEqual(
            {"definite_count": 5, "possible_count": 5, "total_count": 5},
            story["heinlein_interval"],
        )
        self.assertEqual(
            {
                "does_not_qualify": 0,
                "indeterminate": 0,
                "qualifies": 1,
                "unavailable": 0,
            },
            summary["totals"]["heinlein_verdicts"],
        )
        self.assertTrue(summary["plan"]["include_heinlein"])
        self.assertTrue(sidecar.validate_sidecar(data).valid)
        analysis = data["analyses"]["heinlein"][0]
        self.assertEqual("complete", analysis["status"])
        self.assertEqual("qualifies", analysis["verdict"])
        self.assertEqual(
            analysis["analysis_id"], data["current"]["heinlein_analysis_id"]
        )
        self.assertIsNone(data["partial_success"])
        report = (self.root / "on" / "worldcon_spike_report.md").read_text("utf-8")
        self.assertIn("Heinlein verdict: `qualifies`", report)
        self.assertEqual(1, backend.tools.count(run_worldcon_spike.HEINLEIN_TOOL_NAME))
        raw_dir = pathlib.Path(story["raw_response_path"])
        self.assertTrue(
            (raw_dir / f"{run_worldcon_spike.HEINLEIN_STAGE}.json").exists()
        )
        index = json.loads((raw_dir / "index.json").read_text("utf-8"))
        self.assertIn(run_worldcon_spike.HEINLEIN_STAGE, index["stages"])

    def test_dependency_violation_is_quarantined_without_repair(self):
        def violate(result):
            for item in result["heinlein_criteria"]:
                if item["criterion_id"] == "different":
                    item["status"] = "absent"
                    item["supporting_evidence_ids"] = []
            return result

        summary, story, data, _ = self._run(
            "dependency", _HeinleinOverrideBackend(violate)
        )

        self.assertEqual("complete", story["status"])
        self.assertNotIn("heinlein_verdict", story)
        analysis = data["analyses"]["heinlein"][0]
        self.assertEqual("failed", analysis["status"])
        self.assertIn("cannot be present", analysis["failures"][0]["message"])
        self.assertNotIn("heinlein_analysis_id", data["current"])
        self.assertEqual(
            {"unavailable": 1},
            {k: v for k, v in summary["totals"]["heinlein_verdicts"].items() if v},
        )
        quarantine = (
            self.root
            / "dependency"
            / "_quarantine"
            / story["run_id"]
            / pathlib.Path(story["raw_response_path"]).name
            / f"{run_worldcon_spike.HEINLEIN_STAGE}.json"
        )
        self.assertTrue(quarantine.exists())

    def test_present_without_valid_evidence_is_rejected_not_filled_in(self):
        def strip_support(result):
            for item in result["heinlein_criteria"]:
                item["supporting_evidence_ids"] = ["not-a-real-evidence-id"]
            return result

        _, story, data, _ = self._run(
            "no-evidence", _HeinleinOverrideBackend(strip_support)
        )

        analysis = data["analyses"]["heinlein"][0]
        self.assertEqual("failed", analysis["status"])
        self.assertIn("supporting evidence", analysis["failures"][0]["message"])
        self.assertEqual("complete", story["status"])

    def test_missing_criteria_fail_the_heinlein_stage_loudly(self):
        def drop_plausible(result):
            result["heinlein_criteria"] = [
                item
                for item in result["heinlein_criteria"]
                if item["criterion_id"] != "plausible"
            ]
            return result

        _, story, data, _ = self._run(
            "missing", _HeinleinOverrideBackend(drop_plausible)
        )

        analysis = data["analyses"]["heinlein"][0]
        self.assertEqual("failed", analysis["status"])
        self.assertIn("missing criteria: plausible", analysis["failures"][0]["message"])
        self.assertEqual("complete", story["status"])
        self.assertEqual("complete", data["analyses"]["knight"][0]["status"])

    def test_heinlein_failure_does_not_affect_knight_or_suvin(self):
        _, story, data, _ = self._run(
            "isolation", _HeinleinOverrideBackend(lambda result: "not an object")
        )

        self.assertEqual("complete", story["status"])
        self.assertEqual("complete", data["analyses"]["knight"][0]["status"])
        self.assertEqual("complete", data["analyses"]["suvin_novum"][0]["status"])
        self.assertEqual("failed", data["analyses"]["heinlein"][0]["status"])
        self.assertEqual(
            [run_worldcon_spike.HEINLEIN_RECORD_STAGE],
            [f["stage"] for f in data["partial_success"]["failed_stages"]],
        )
        self.assertEqual(
            [
                run_worldcon_spike.EVIDENCE_RECORD_STAGE,
                run_worldcon_spike.KNIGHT_RECORD_STAGE,
                run_worldcon_spike.SUVIN_RECORD_STAGE,
            ],
            data["partial_success"]["completed_stages"],
        )
        self.assertIsNotNone(data["current"]["knight_analysis_id"])
        self.assertIsNotNone(data["current"]["suvin_novum_analysis_id"])
        self.assertTrue(sidecar.validate_sidecar(data).valid)

    def test_enabling_heinlein_reuses_existing_knight_and_suvin_checkpoints(self):
        root = self.root / "reuse"
        first = _HeinleinOverrideBackend()
        with patch.object(run_worldcon_spike, "_make_backend", return_value=first):
            run_worldcon_spike.run_spike(
                run_worldcon_spike.RunnerOptions(
                    manifest_path=run_worldcon_spike.DEFAULT_MANIFEST,
                    output_root=root,
                    max_stories=1,
                    resume=True,
                )
            )
        self.assertNotIn(run_worldcon_spike.HEINLEIN_TOOL_NAME, first.tools)

        second = _HeinleinOverrideBackend()
        with patch.object(run_worldcon_spike, "_make_backend", return_value=second):
            summary = run_worldcon_spike.run_spike(_heinlein_options(root, resume=True))

        self.assertEqual("complete", summary["status"])
        self.assertEqual([run_worldcon_spike.HEINLEIN_TOOL_NAME], second.tools)

    def test_heinlein_stage_is_rejected_for_paid_backends(self):
        with self.assertRaisesRegex(ValueError, "Heinlein stage"):
            run_worldcon_spike.run_spike(
                run_worldcon_spike.RunnerOptions(
                    manifest_path=run_worldcon_spike.DEFAULT_MANIFEST,
                    output_root=self.root / "paid",
                    backend_kind=run_worldcon_spike.ANTHROPIC_BACKEND,
                    include_heinlein=True,
                    dry_run=True,
                )
            )

    def test_prompt_and_schema_track_the_resolved_rubric(self):
        prompt = run_worldcon_spike._heinlein_system_prompt()
        schema = run_worldcon_spike._heinlein_tool_schema()

        for slot in run_worldcon_spike.rubric_definitions.HEINLEIN_FIVE.text_slots:
            self.assertIn(slot.governing_text, prompt)
        self.assertIn("indispensably affected", prompt)
        self.assertIn("Python derives the result", prompt)
        self.assertEqual(run_worldcon_spike.HEINLEIN_TOOL_NAME, schema["name"])
        criteria = schema["input_schema"]["properties"]["heinlein_criteria"]["items"]
        self.assertEqual(
            list(run_worldcon_spike.models.HEINLEIN_CRITERION_IDS),
            criteria["properties"]["criterion_id"]["enum"],
        )
        self.assertNotIn("verdict", json.dumps(schema))

    def test_stage_payload_does_not_change_knight_or_suvin_prompt_version(self):
        self.assertEqual(
            "worldcon-knight-novum-spike-prompt-v3",
            run_worldcon_spike.PROMPT_VERSION,
        )
        self.assertNotEqual(
            run_worldcon_spike.PROMPT_VERSION,
            run_worldcon_spike.HEINLEIN_PROMPT_VERSION,
        )


HEINLEIN_CANARY_MANIFEST = (
    run_worldcon_spike.DEFAULT_MANIFEST.parent / "heinlein_canary_manifest.json"
)
# Fingerprints recorded before expectations existed; they must never change, or
# approval snapshots that compare them would be invalidated.
RECORDED_MANIFEST_FINGERPRINTS = {
    "contract_canary_manifest.json": (
        "00d68d725355f7b077456eab29278758da18a5dfcfafb0b4287e25745086039e"
    ),
    "worldcon_spike_manifest.json": (
        "582e99655cf896469277ce9fd90b2df29419e1f965e50e90408552ee61b52454"
    ),
}


class _StageOverrideBackend:
    """Delegate to the deterministic backend, overriding one stage's tool result."""

    def __init__(self, tool_name, override):
        self.delegate = run_worldcon_spike.DeterministicSpikeBackend()
        self.tool_name = tool_name
        self.override = override

    def complete(self, **kwargs):
        response = self.delegate.complete(**kwargs)
        if kwargs["tool"]["name"] == self.tool_name:
            response.tool_result = self.override(response.tool_result)
        return response


class _StageTextBackend:
    """Return text instead of a tool call for one stage, as a local runtime can."""

    def __init__(self, tool_name, text_for):
        self.delegate = run_worldcon_spike.DeterministicSpikeBackend()
        self.tool_name = tool_name
        self.text_for = text_for

    def complete(self, **kwargs):
        if kwargs["tool"]["name"] != self.tool_name:
            return self.delegate.complete(**kwargs)
        payload = json.loads(kwargs["messages"][-1]["content"])
        result = run_worldcon_spike._fake_stage_result(payload, kwargs["tool"])
        raise llm_backend.NoToolCallError(
            "local runtime returned text without a tool call",
            input_tokens=7,
            output_tokens=11,
            raw_content=self.text_for(result),
        )


def _rendered_heinlein_verdict(data):
    """Return the Heinlein verdict word the detailed rendering shows."""

    text = rendering.render_sidecar(data, detail="detailed")
    line = next(item for item in text.splitlines() if "Heinlein Verdict" in item)
    return line.split("**Heinlein Verdict:**", 1)[1].split("(", 1)[0].strip()


def _wrong_heinlein_keys(result):
    """Rename the schema keys the way the WI-SF-0113 canary saw the model do."""

    return {
        "heinlein_criteria": [
            {
                "criterion": item["criterion_id"],
                "decision_state": item["status"],
                "evidence_ids": item["supporting_evidence_ids"],
                "rationale": item["rationale"],
            }
            for item in result["heinlein_criteria"]
        ]
    }


def _all_not_assessable(result):
    return {
        "heinlein_criteria": [
            {
                "criterion_id": item["criterion_id"],
                "status": "not_assessable",
                "supporting_evidence_ids": [],
                "counterevidence_ids": [],
                "rationale": "",
                "confidence": 0.0,
            }
            for item in result["heinlein_criteria"]
        ]
    }


class WorldconStructuredOutputFailLoudTest(unittest.TestCase):
    """WI-SF-0114: mismatched or empty model output fails loudly, not silently."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, name, backend):
        output_root = self.root / name
        with patch.object(run_worldcon_spike, "_make_backend", return_value=backend):
            summary = run_worldcon_spike.run_spike(_heinlein_options(output_root))
        story = summary["stories"][0]
        data = (
            sidecar.load_json(pathlib.Path(story["sidecar_path"]))
            if story.get("sidecar_path")
            else None
        )
        return output_root, summary, story, data

    def _events(self, output_root):
        log_path = output_root / "worldcon_spike_run_log.jsonl"
        return [
            json.loads(line)
            for line in log_path.read_text(encoding="utf-8").splitlines()
            if line
        ]

    def _assert_heinlein_failed_but_story_complete(self, story, data, fragment):
        self.assertEqual("complete", story["status"])
        analysis = data["analyses"]["heinlein"][0]
        self.assertEqual("failed", analysis["status"])
        self.assertIn(fragment, analysis["failures"][0]["message"])
        self.assertEqual("complete", data["analyses"]["knight"][0]["status"])
        self.assertEqual("complete", data["analyses"]["suvin_novum"][0]["status"])
        return analysis

    def test_wrong_heinlein_keys_are_quarantined_not_defaulted(self):
        _, _, story, data = self._run(
            "wrong-keys",
            _StageOverrideBackend(
                run_worldcon_spike.HEINLEIN_TOOL_NAME, _wrong_heinlein_keys
            ),
        )

        analysis = self._assert_heinlein_failed_but_story_complete(
            story, data, "criterion_id"
        )
        self.assertEqual("Unavailable", _rendered_heinlein_verdict(data))
        self.assertTrue(
            all(c["status"] == "not_assessable" for c in analysis["criteria"])
        )

    def test_missing_heinlein_criteria_key_is_quarantined(self):
        _, _, story, data = self._run(
            "no-key",
            _StageOverrideBackend(
                run_worldcon_spike.HEINLEIN_TOOL_NAME,
                lambda result: {"items": result["heinlein_criteria"]},
            ),
        )

        self._assert_heinlein_failed_but_story_complete(
            story, data, "'heinlein_criteria' list"
        )

    def test_missing_required_fields_are_quarantined(self):
        cases = {
            "counterevidence_ids": "counterevidence_ids must be a list",
            "confidence": "confidence must be a number",
            "status": "missing or invalid status",
        }
        for field, fragment in cases.items():
            with self.subTest(field=field):

                def drop_field(result, field=field):
                    del result["heinlein_criteria"][0][field]
                    return result

                _, _, story, data = self._run(
                    f"drop-{field}",
                    _StageOverrideBackend(
                        run_worldcon_spike.HEINLEIN_TOOL_NAME, drop_field
                    ),
                )

                self._assert_heinlein_failed_but_story_complete(story, data, fragment)

    def test_unknown_and_duplicate_criteria_are_quarantined(self):
        def unknown(result):
            result["heinlein_criteria"][0]["criterion_id"] = "decision"
            return result

        def duplicate(result):
            result["heinlein_criteria"][1]["criterion_id"] = "different"
            return result

        for name, override, fragment in (
            ("unknown", unknown, "unknown criterion_id"),
            ("duplicate", duplicate, "duplicate criterion"),
        ):
            with self.subTest(name=name):
                _, _, story, data = self._run(
                    name,
                    _StageOverrideBackend(
                        run_worldcon_spike.HEINLEIN_TOOL_NAME, override
                    ),
                )

                self._assert_heinlein_failed_but_story_complete(story, data, fragment)

    def test_a_genuine_all_not_assessable_response_is_still_accepted(self):
        _, _, story, data = self._run(
            "genuine",
            _StageOverrideBackend(
                run_worldcon_spike.HEINLEIN_TOOL_NAME, _all_not_assessable
            ),
        )

        self.assertEqual("complete", story["status"])
        analysis = data["analyses"]["heinlein"][0]
        self.assertEqual("complete", analysis["status"])
        self.assertEqual("indeterminate", analysis["verdict"])
        self.assertEqual([], analysis["failures"])

    def test_one_fenced_json_block_is_unwrapped_and_logged(self):
        output_root, _, story, data = self._run(
            "fenced",
            _StageTextBackend(
                run_worldcon_spike.HEINLEIN_TOOL_NAME,
                lambda result: "```json\n" + json.dumps(result) + "\n```",
            ),
        )

        self.assertEqual("complete", story["status"])
        self.assertEqual("complete", data["analyses"]["heinlein"][0]["status"])
        events = [(e["event"], e.get("stage")) for e in self._events(output_root)]
        self.assertIn(("no_tool_call_json_fallback", "sf_heinlein"), events)
        self.assertIn(("fenced_json_unwrapped", "sf_heinlein"), events)

    def test_a_fenced_block_with_wrong_keys_is_still_quarantined(self):
        output_root, _, story, data = self._run(
            "fenced-wrong-keys",
            _StageTextBackend(
                run_worldcon_spike.HEINLEIN_TOOL_NAME,
                lambda result: "```json\n"
                + json.dumps(_wrong_heinlein_keys(result))
                + "\n```",
            ),
        )

        self._assert_heinlein_failed_but_story_complete(story, data, "criterion_id")
        events = [e["event"] for e in self._events(output_root)]
        self.assertIn("fenced_json_unwrapped", events)

    def test_prose_around_the_fence_is_a_failure_that_keeps_its_metadata(self):
        output_root, _, story, data = self._run(
            "prose",
            _StageTextBackend(
                run_worldcon_spike.HEINLEIN_TOOL_NAME,
                lambda result: "Here you go:\n```json\n" + json.dumps(result) + "\n```",
            ),
        )

        self.assertEqual("complete", story["status"])
        analysis = data["analyses"]["heinlein"][0]
        self.assertEqual("failed", analysis["status"])
        self.assertEqual("ValueError", analysis["failures"][0]["kind"])
        quarantine = next((output_root / "_quarantine").rglob("sf_heinlein.json"))
        record = json.loads(quarantine.read_text(encoding="utf-8"))
        self.assertTrue(
            pathlib.Path(record["raw_response_path"]).exists(),
            record["raw_response_path"],
        )
        events = [e["event"] for e in self._events(output_root)]
        self.assertNotIn("fenced_json_unwrapped", events)

    def _evidence_story_failure(self, name, override):
        output_root, summary, story, _ = self._run(
            name,
            _StageOverrideBackend(run_worldcon_spike.EVIDENCE_TOOL_NAME, override),
        )
        self.assertEqual("failed", story["status"])
        self.assertIsNone(story.get("sidecar_path"))
        quarantine = json.loads(
            pathlib.Path(story["quarantine_path"]).read_text(encoding="utf-8")
        )
        self.assertEqual("story", quarantine["stage"])
        return output_root, quarantine

    def test_a_missing_evidence_list_fails_the_story(self):
        _, quarantine = self._evidence_story_failure(
            "no-evidence-key", lambda result: {"items": result["evidence"]}
        )

        self.assertIn("'evidence' list", quarantine["failure_message"])

    def test_all_quarantined_evidence_fails_the_story_with_the_reasons(self):
        def schema_mismatch(result):
            return {
                "evidence": [
                    {
                        "raw_id": item["raw_id"],
                        "quotation": item["quote"],
                        "paraphrase": item["paraphrase"],
                        "confidence": item["confidence"],
                    }
                    for item in result["evidence"]
                ]
            }

        _, quarantine = self._evidence_story_failure("all-quarantined", schema_mismatch)

        self.assertIn("produced no usable evidence", quarantine["failure_message"])
        self.assertIn("evidence_type is required", quarantine["failure_message"])

    def test_an_explicit_empty_evidence_list_is_accepted_with_a_warning(self):
        output_root, _, story, _ = self._run(
            "empty-list",
            _StageOverrideBackend(
                run_worldcon_spike.EVIDENCE_TOOL_NAME,
                lambda _result: {"evidence": []},
            ),
        )

        self.assertNotEqual("failed", story["status"], story)
        events = [e["event"] for e in self._events(output_root)]
        self.assertIn("evidence_empty_list", events)


CANARY_FIXTURES = (
    pathlib.Path(__file__).parent / "fixtures" / "canary_raw_responses.json"
)


class WorldconCanaryFixtureTest(unittest.TestCase):
    """Replay the WI-SF-0113 canary's raw responses through the real validators."""

    @classmethod
    def setUpClass(cls):
        data = json.loads(CANARY_FIXTURES.read_text(encoding="utf-8"))
        cls.responses = data["responses"]
        cls.prepared = {}
        for story_path in {item["story_path"] for item in cls.responses}:
            story_file = run_worldcon_spike._repo_root() / "corpora" / story_path
            if not story_file.is_file():
                raise unittest.SkipTest(f"corpus story is not available: {story_path}")
            cls.prepared[story_path] = preparation.prepare_story_file(story_file)

    def _find(self, run, story, stage):
        return next(
            item
            for item in self.responses
            if (item["run"], item["story"], item["stage"]) == (run, story, stage)
        )

    def _evidence_set(self, run, story):
        item = self._find(run, story, "sf_evidence")
        return run_worldcon_spike._build_evidence_set(
            self.prepared[item["story_path"]],
            item["tool_result"],
            backend="openai-compatible",
        )

    def test_fixtures_hold_no_absolute_paths(self):
        text = CANARY_FIXTURES.read_text(encoding="utf-8")

        self.assertNotIn("/Users/", text)

    def test_vonnegut_evidence_from_the_trials_now_fails_the_stage(self):
        for run in ("trial-1", "trial-2", "trial-3"):
            with self.subTest(run=run):
                with self.assertRaises(ValueError) as caught:
                    self._evidence_set(run, "vonnegut")

                message = str(caught.exception)
                self.assertIn("produced no usable evidence", message)
                self.assertIn("evidence_type is required", message)

    def test_vonnegut_baseline_evidence_still_builds(self):
        evidence_set = self._evidence_set("baseline", "vonnegut")

        self.assertEqual(7, len(evidence_set.records))

    def test_bell_trial_evidence_still_builds(self):
        for run in ("trial-1", "trial-2", "trial-3"):
            with self.subTest(run=run):
                self.assertEqual(4, len(self._evidence_set(run, "bell").records))

    def test_every_canary_heinlein_response_is_rejected_for_its_keys(self):
        bell_evidence = self._evidence_set("trial-2", "bell")
        heinlein = [item for item in self.responses if item["stage"] == "sf_heinlein"]
        self.assertEqual(6, len(heinlein))
        for item in heinlein:
            with self.subTest(run=item["run"], story=item["story"]):
                result = item["tool_result"]
                if result is None:
                    result = compat.extract_json(item["text"], strict_fence=True)
                with self.assertRaises(ValueError) as caught:
                    run_worldcon_spike._heinlein_decisions(result, bell_evidence)

                self.assertIn("criterion_id", str(caught.exception))

    def test_canary_fenced_text_is_unwrapped_by_the_strict_helper(self):
        item = self._find("trial-1", "bell", "sf_heinlein")

        self.assertTrue(item["text"].lstrip().startswith("```json"))
        result = compat.extract_json(item["text"], strict_fence=True)

        self.assertEqual(5, len(result["heinlein_criteria"]))


class WorldconStructuredOutputPromptTest(unittest.TestCase):
    """The evidence and Heinlein prompts use the tool schema's own key names."""

    @staticmethod
    def _item_keys(tool_schema, array_key):
        item = tool_schema["input_schema"]["properties"][array_key]["items"]
        return list(item["properties"])

    def test_evidence_prompt_names_every_schema_key(self):
        prompt = run_worldcon_spike._evidence_system_prompt()
        keys = self._item_keys(run_worldcon_spike._evidence_tool_schema(), "evidence")

        for key in keys:
            self.assertIn(key, prompt)
        self.assertIn("not quotation", prompt)
        self.assertIn("no Markdown fences", prompt)
        self.assertIn('{"evidence": []}', prompt)

    def test_heinlein_prompt_names_every_schema_key_and_drops_rubric_id(self):
        prompt = run_worldcon_spike._heinlein_system_prompt()
        keys = self._item_keys(
            run_worldcon_spike._heinlein_tool_schema(), "heinlein_criteria"
        )

        for key in keys:
            self.assertIn(key, prompt)
        self.assertIn("not criterion or decision", prompt)
        self.assertNotIn("rubric_id", prompt)
        self.assertNotIn("Decision states", prompt)
        self.assertIn("no Markdown fences", prompt)
        self.assertIn("the status absent", prompt)

    def test_prompt_text_changes_the_stage_fingerprints(self):
        options = _heinlein_options(pathlib.Path("unused"))
        payload = {"stage": "x"}

        def fingerprint(prompt):
            return run_worldcon_spike._model_stage_fingerprint(
                stage="sf_heinlein",
                options=options,
                system_prompt=prompt,
                payload=payload,
                tool_schema=run_worldcon_spike._heinlein_tool_schema(),
            )["sha256"]

        current = run_worldcon_spike._heinlein_system_prompt()
        self.assertNotEqual(
            fingerprint(current), fingerprint(current.replace("status", "decision"))
        )

    def test_only_the_heinlein_prompt_version_changed(self):
        self.assertEqual(
            "worldcon-knight-novum-spike-prompt-v3", run_worldcon_spike.PROMPT_VERSION
        )
        self.assertEqual(
            "worldcon-heinlein-spike-prompt-v2",
            run_worldcon_spike.HEINLEIN_PROMPT_VERSION,
        )


class WorldconHeinleinCanaryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _manifest_copy(self, name: str, mutate=None) -> pathlib.Path:
        data = json.loads(HEINLEIN_CANARY_MANIFEST.read_text(encoding="utf-8"))
        if mutate is not None:
            mutate(data)
        path = self.root / name
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def _options(self, name, mode, manifest=HEINLEIN_CANARY_MANIFEST, **updates):
        return run_worldcon_spike.RunnerOptions(
            manifest_path=manifest,
            output_root=self.root / name,
            mode=mode,
            include_heinlein=True,
            **updates,
        )

    def test_manifest_has_required_gates_caps_and_no_paid_calls(self):
        manifest = run_worldcon_spike.load_manifest(HEINLEIN_CANARY_MANIFEST)

        self.assertEqual({"smoke", "sample", "canary", "full"}, set(manifest.gates))
        canary = manifest.gates["canary"]
        self.assertEqual(2, canary.max_stories)
        self.assertFalse(canary.paid_model_calls_authorized)
        self.assertEqual(0.0, canary.estimated_cost_usd)
        self.assertEqual(2, len(manifest.canary_stories))
        self.assertGreater(len(manifest.smoke_stories), 0)
        for story in manifest.canary_stories:
            self.assertEqual(
                "operational_check_not_gold_label", story.expectations["kind"]
            )
            self.assertTrue(story.expectations["rationale"])
            self.assertTrue(story.expectations["heinlein_verdict_in"])

    def test_existing_manifest_fingerprints_are_unchanged(self):
        for name, expected in RECORDED_MANIFEST_FINGERPRINTS.items():
            with self.subTest(manifest=name):
                manifest = run_worldcon_spike.load_manifest(
                    run_worldcon_spike.DEFAULT_MANIFEST.parent / name
                )
                self.assertEqual(
                    expected, run_worldcon_spike._manifest_fingerprint(manifest)
                )

    def test_changing_an_expectation_changes_the_fingerprint(self):
        original = run_worldcon_spike._manifest_fingerprint(
            run_worldcon_spike.load_manifest(HEINLEIN_CANARY_MANIFEST)
        )

        def edit(data):
            data["canary_stories"][0]["expectations"]["heinlein_verdict_in"] = [
                "qualifies"
            ]

        changed = run_worldcon_spike._manifest_fingerprint(
            run_worldcon_spike.load_manifest(self._manifest_copy("edited.json", edit))
        )

        self.assertNotEqual(original, changed)

        def drop(data):
            for story in data["canary_stories"]:
                story.pop("expectations")

        dropped = run_worldcon_spike._manifest_fingerprint(
            run_worldcon_spike.load_manifest(self._manifest_copy("dropped.json", drop))
        )
        self.assertNotEqual(original, dropped)

    def test_non_object_expectations_are_rejected(self):
        def bad(data):
            data["canary_stories"][0]["expectations"] = ["not", "an", "object"]

        with self.assertRaisesRegex(ValueError, "expectations must be an object"):
            run_worldcon_spike.load_manifest(self._manifest_copy("bad.json", bad))

    def test_dry_run_plan_shows_the_heinlein_flag_in_smoke_and_canary(self):
        for mode in ("smoke", "canary"):
            with self.subTest(mode=mode):
                summary = run_worldcon_spike.run_spike(
                    self._options(f"dry-{mode}", mode, dry_run=True)
                )
                self.assertTrue(summary["plan"]["include_heinlein"])
                self.assertGreater(summary["plan"]["story_count"], 0)

    def test_fake_smoke_processes_the_manifest_stories_with_heinlein_verdicts(self):
        summary = run_worldcon_spike.run_spike(self._options("smoke", "smoke"))

        self.assertEqual("complete", summary["status"])
        self.assertEqual(2, len(summary["stories"]))
        self.assertEqual(2, summary["totals"]["complete"])
        for story in summary["stories"]:
            self.assertEqual("qualifies", story["heinlein_verdict"])
            data = sidecar.load_json(pathlib.Path(story["sidecar_path"]))
            self.assertTrue(sidecar.validate_sidecar(data).valid)
            self.assertEqual("complete", data["analyses"]["heinlein"][0]["status"])

    def test_fake_canary_completes_and_persists_the_manifest_snapshot(self):
        summary = run_worldcon_spike.run_spike(self._options("canary", "canary"))

        self.assertEqual("complete", summary["status"])
        self.assertEqual(2, len(summary["stories"]))
        snapshot = self.root / "canary" / run_worldcon_spike.MANIFEST_SNAPSHOT_FILENAME
        self.assertEqual(
            HEINLEIN_CANARY_MANIFEST.read_text(encoding="utf-8"),
            snapshot.read_text(encoding="utf-8"),
        )
        recorded = json.loads(snapshot.read_text(encoding="utf-8"))
        self.assertTrue(
            all(item["expectations"] for item in recorded["canary_stories"])
        )

    def test_dry_run_writes_no_snapshot_or_output(self):
        run_worldcon_spike.run_spike(self._options("dry-quiet", "canary", dry_run=True))

        self.assertFalse((self.root / "dry-quiet").exists())

    def test_snapshot_is_the_text_the_manifest_was_loaded_from(self):
        manifest = run_worldcon_spike.load_manifest(HEINLEIN_CANARY_MANIFEST)

        self.assertEqual(
            HEINLEIN_CANARY_MANIFEST.read_text(encoding="utf-8"), manifest.source_text
        )

    def test_manifest_without_expectations_writes_no_snapshot(self):
        run_worldcon_spike.run_spike(
            run_worldcon_spike.RunnerOptions(
                manifest_path=run_worldcon_spike.DEFAULT_MANIFEST,
                output_root=self.root / "legacy",
                max_stories=1,
            )
        )

        self.assertFalse(
            (
                self.root / "legacy" / run_worldcon_spike.MANIFEST_SNAPSHOT_FILENAME
            ).exists()
        )

    def test_resume_refuses_a_manifest_that_dropped_every_expectation(self):
        first = self._manifest_copy("first-keep.json")
        run_worldcon_spike.run_spike(
            self._options("dropped", "canary", manifest=first, resume=True)
        )

        def drop(data):
            for story in data["canary_stories"]:
                story.pop("expectations")

        stripped = self._manifest_copy("stripped.json", drop)
        with self.assertRaisesRegex(ValueError, "manifest_snapshot.json"):
            run_worldcon_spike.run_spike(
                self._options("dropped", "canary", manifest=stripped, resume=True)
            )

    def test_snapshot_is_never_written_through_a_symlink(self):
        manifest = run_worldcon_spike.load_manifest(HEINLEIN_CANARY_MANIFEST)
        outside = self.root / "outside.txt"
        dangling_root = self.root / "dangling"
        dangling_root.mkdir()
        (dangling_root / run_worldcon_spike.MANIFEST_SNAPSHOT_FILENAME).symlink_to(
            outside
        )
        existing_root = self.root / "existing"
        existing_root.mkdir()
        victim = self.root / "victim.txt"
        victim.write_text("keep me", encoding="utf-8")
        (existing_root / run_worldcon_spike.MANIFEST_SNAPSHOT_FILENAME).symlink_to(
            victim
        )

        for root in (dangling_root, existing_root):
            with self.subTest(root=root.name):
                with self.assertRaisesRegex(ValueError, "must not be a symlink"):
                    run_worldcon_spike._write_manifest_snapshot(root, manifest)

        self.assertFalse(outside.exists())
        self.assertEqual("keep me", victim.read_text(encoding="utf-8"))

    def test_snapshot_write_leaves_no_temporary_files(self):
        manifest = run_worldcon_spike.load_manifest(HEINLEIN_CANARY_MANIFEST)
        root = self.root / "clean"

        run_worldcon_spike._write_manifest_snapshot(root, manifest)

        self.assertEqual(
            [run_worldcon_spike.MANIFEST_SNAPSHOT_FILENAME],
            sorted(item.name for item in root.iterdir()),
        )

    def test_resume_refuses_a_manifest_edited_after_the_first_run(self):
        first = self._manifest_copy("first.json")
        run_worldcon_spike.run_spike(
            self._options("resume", "canary", manifest=first, resume=True)
        )

        def edit(data):
            data["canary_stories"][1]["expectations"]["heinlein_verdict_in"] = [
                "qualifies"
            ]

        edited = self._manifest_copy("edited.json", edit)
        with self.assertRaisesRegex(ValueError, "manifest_snapshot.json"):
            run_worldcon_spike.run_spike(
                self._options("resume", "canary", manifest=edited, resume=True)
            )

    def test_only_loopback_endpoints_count_as_no_cost(self):
        manifest = run_worldcon_spike.load_manifest(HEINLEIN_CANARY_MANIFEST)
        gate = manifest.gates["canary"]
        cases = {
            "http://localhost:11434/v1": False,
            "http://LOCALHOST:11434/v1": False,
            "http://127.0.0.1:11434/v1": False,
            "http://127.0.0.2:11434/v1": False,
            "http://[::1]:11434/v1": False,
            "http://[::ffff:127.0.0.1]:11434/v1": False,
            "http://[::ffff:7f00:1]:11434/v1": False,
            "http://[::ffff:8.8.8.8]:11434/v1": True,
            "http://[::ffff:192.168.1.5]:11434/v1": True,
            "http://localhost.:11434/v1": True,
            "http://localhost@evil.example/v1": True,
            "http://127.0.0.1.evil.example/v1": True,
            "https://api.example.com/v1": True,
            "http://192.168.1.20:11434/v1": True,
            "http://localhost.evil.example/v1": True,
            "http://user@evil.example/v1": True,
            "not a url": True,
            "": True,
            None: True,
        }
        for base_url, paid in cases.items():
            with self.subTest(base_url=base_url):
                options = run_worldcon_spike.RunnerOptions(
                    backend_kind=run_worldcon_spike.OPENAI_COMPATIBLE_BACKEND,
                    base_url=base_url,
                )
                self.assertEqual(
                    paid, run_worldcon_spike._paid_call_requested(options, gate)
                )

    def test_heinlein_flag_is_rejected_for_a_remote_compatible_endpoint(self):
        with self.assertRaisesRegex(ValueError, "Heinlein stage"):
            run_worldcon_spike.run_spike(
                self._options(
                    "remote",
                    "canary",
                    backend_kind=run_worldcon_spike.OPENAI_COMPATIBLE_BACKEND,
                    base_url="https://api.example.com/v1",
                    dry_run=True,
                )
            )

    def test_heinlein_flag_is_accepted_for_a_loopback_endpoint(self):
        summary = run_worldcon_spike.run_spike(
            self._options(
                "loopback",
                "canary",
                backend_kind=run_worldcon_spike.OPENAI_COMPATIBLE_BACKEND,
                base_url="http://localhost:11434/v1",
                model="gpt-oss:20b",
                dry_run=True,
            )
        )

        self.assertTrue(summary["plan"]["include_heinlein"])
        self.assertEqual("http://localhost:11434/v1", summary["plan"]["base_url"])


if __name__ == "__main__":
    unittest.main()
