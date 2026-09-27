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
        self.assertEqual(
            "transient",
            run_worldcon_spike._classify_stage_failure(
                RuntimeError("overloaded_error")
            ),
        )

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
