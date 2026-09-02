"""Tests for the bounded Worldcon Knight/Novum spike runner."""

from __future__ import annotations

import json
import pathlib
import tempfile
import unittest
from unittest.mock import MagicMock, patch

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


class _MalformedJsonBackend:
    def complete(self, **_kwargs):
        return llm_backend.BackendResponse(
            text="{malformed",
            tool_result=None,
            model="malformed-json",
            input_tokens=19,
            output_tokens=23,
        )


class _BackendError(RuntimeError):
    input_tokens = 29
    output_tokens = 31
    raw_content = '{"partial":'


class _RaisedBackend:
    def complete(self, **_kwargs):
        raise _BackendError("backend failed")


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


class _MalformedCollectionBackend:
    def complete(self, **kwargs):
        payload = json.loads(kwargs["messages"][-1]["content"])
        result = run_worldcon_spike._fake_tool_result(payload)
        result["knight_criteria"] = None
        return llm_backend.BackendResponse(
            text="",
            tool_result=result,
            model="malformed-collection",
            input_tokens=13,
            output_tokens=17,
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
                story["run_id"],
                data["analyses"]["knight"][0]["provenance"]["run_id"],
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

    def test_tool_schema_uses_provider_accepted_top_level_fields(self):
        schema = run_worldcon_spike._tool_schema()

        self.assertEqual(
            {"name", "description", "input_schema", "strict"},
            set(schema),
        )
        self.assertNotIn("decision_states", schema)

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
        records = [
            json.loads(line)
            for line in (output_root / "worldcon_spike_run_log.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        events = [record["event"] for record in records]
        self.assertIn("story_quarantined", events)
        self.assertIn("run_stopped", events)
        self.assertTrue(
            next(record for record in records if record["event"] == "run_stopped")[
                "run_id"
            ]
        )

    def test_malformed_nested_tool_output_is_normalized_without_crashing(self):
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

    def test_malformed_required_collection_is_quarantined(self):
        output_root = self.root / "malformed-collection"

        with patch.object(
            run_worldcon_spike,
            "_make_backend",
            return_value=_MalformedCollectionBackend(),
        ):
            summary = run_worldcon_spike.run_spike(
                run_worldcon_spike.RunnerOptions(
                    manifest_path=self.manifest_path,
                    output_root=output_root,
                    max_stories=1,
                )
            )

        story = summary["stories"][0]
        self.assertEqual("failed", story["status"])
        self.assertEqual("ValueError", story["failure_kind"])
        self.assertIn("knight_criteria must be a list", story["failure_message"])
        self.assertTrue(pathlib.Path(story["quarantine_path"]).exists())

    def test_malformed_json_persists_raw_and_quarantine(self):
        output_root = self.root / "malformed-json"

        with patch.object(
            run_worldcon_spike,
            "_make_backend",
            return_value=_MalformedJsonBackend(),
        ):
            summary = run_worldcon_spike.run_spike(
                run_worldcon_spike.RunnerOptions(
                    manifest_path=self.manifest_path,
                    output_root=output_root,
                    max_stories=1,
                )
            )

        story = summary["stories"][0]
        self.assertEqual("failed", story["status"])
        raw_path = pathlib.Path(story["raw_response_path"])
        quarantine_path = pathlib.Path(story["quarantine_path"])
        self.assertTrue(raw_path.exists())
        self.assertTrue(quarantine_path.exists())
        self.assertEqual("{malformed", json.loads(raw_path.read_text())["text"])
        self.assertEqual(
            "JSONDecodeError",
            json.loads(quarantine_path.read_text())["failure_kind"],
        )

    def test_backend_exception_persists_raw_content_and_usage(self):
        output_root = self.root / "backend-error"

        with patch.object(
            run_worldcon_spike,
            "_make_backend",
            return_value=_RaisedBackend(),
        ):
            summary = run_worldcon_spike.run_spike(
                run_worldcon_spike.RunnerOptions(
                    manifest_path=self.manifest_path,
                    output_root=output_root,
                    max_stories=1,
                )
            )

        story = summary["stories"][0]
        raw = json.loads(pathlib.Path(story["raw_response_path"]).read_text())
        self.assertEqual("_BackendError", raw["backend_error"])
        self.assertEqual('{"partial":', raw["raw_content"])
        self.assertEqual(29, story["input_tokens"])
        self.assertEqual(31, story["output_tokens"])

    def test_raw_and_quarantine_artifacts_reject_symlinked_directories(self):
        outside = self.root / "outside"
        outside.mkdir()
        for directory_name in ("_raw", "_quarantine"):
            output_root = self.root / f"symlink-{directory_name}"
            output_root.mkdir()
            (output_root / directory_name).symlink_to(outside, target_is_directory=True)

            with self.assertRaisesRegex(OSError, "must not be a symlink"):
                run_worldcon_spike._write_json_atomic(
                    output_root / directory_name / "run" / "story.json",
                    {"ok": True},
                    output_root=output_root,
                )

        self.assertEqual((), tuple(outside.iterdir()))

    def test_reruns_use_distinct_attempt_artifacts(self):
        output_root = self.root / "reruns"
        options = run_worldcon_spike.RunnerOptions(
            manifest_path=self.manifest_path,
            output_root=output_root,
            max_stories=1,
        )

        first = run_worldcon_spike.run_spike(options)
        second = run_worldcon_spike.run_spike(options)

        self.assertNotEqual(first["run_id"], second["run_id"])
        first_path = first["stories"][0]["raw_response_path"]
        second_path = second["stories"][0]["raw_response_path"]
        self.assertNotEqual(first_path, second_path)
        self.assertTrue(pathlib.Path(first_path).exists())
        self.assertTrue(pathlib.Path(second_path).exists())
        rows = (
            (output_root / "worldcon_spike_story_results.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        )
        self.assertEqual(2, len(rows))

    def test_final_artifact_failure_logs_abort_without_run_end(self):
        output_root = self.root / "report-failure"

        with patch.object(
            run_worldcon_spike,
            "_write_report",
            side_effect=OSError("report write failed"),
        ):
            with self.assertRaisesRegex(OSError, "report write failed"):
                run_worldcon_spike.run_spike(
                    run_worldcon_spike.RunnerOptions(
                        manifest_path=self.manifest_path,
                        output_root=output_root,
                        max_stories=0,
                    )
                )

        events = [
            json.loads(line)["event"]
            for line in (output_root / "worldcon_spike_run_log.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        self.assertIn("run_aborted_unexpected", events)
        self.assertNotIn("run_end", events)

    def test_backend_construction_failure_logs_abort(self):
        output_root = self.root / "backend-construction-failure"

        with patch.object(
            run_worldcon_spike,
            "_make_backend",
            side_effect=RuntimeError("backend setup failed"),
        ):
            with self.assertRaisesRegex(RuntimeError, "backend setup failed"):
                run_worldcon_spike.run_spike(
                    run_worldcon_spike.RunnerOptions(
                        manifest_path=self.manifest_path,
                        output_root=output_root,
                        max_stories=0,
                    )
                )

        records = [
            json.loads(line)
            for line in (output_root / "worldcon_spike_run_log.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        events = [record["event"] for record in records]
        self.assertIn("run_start", events)
        self.assertIn("run_aborted_unexpected", events)
        self.assertNotIn("run_end", events)

    def test_allow_protected_root_is_forwarded_to_run_log(self):
        output_root = self.root / "protected-opt-in"
        log = MagicMock()
        log.__enter__.return_value = log

        with (
            patch.object(
                run_worldcon_spike.run_log, "RunLog", return_value=log
            ) as factory,
            patch.object(
                run_worldcon_spike.pipeline,
                "run_checkpointed_assembly",
                wraps=run_worldcon_spike.pipeline.run_checkpointed_assembly,
            ) as assemble,
            patch.object(
                run_worldcon_spike.pipeline,
                "publish_sidecar",
                wraps=run_worldcon_spike.pipeline.publish_sidecar,
            ) as publish,
        ):
            run_worldcon_spike.run_spike(
                run_worldcon_spike.RunnerOptions(
                    manifest_path=self.manifest_path,
                    output_root=output_root,
                    allow_protected_root=True,
                    max_stories=1,
                )
            )

        self.assertTrue(factory.call_args.kwargs["allow_protected_root"])
        self.assertTrue(assemble.call_args.kwargs["allow_protected_root"])
        self.assertTrue(publish.call_args.kwargs["allow_protected_root"])

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

    def test_story_result_log_rejects_symlink(self):
        output_root = self.root / "symlink"
        output_root.mkdir()
        target = self.root / "outside.jsonl"
        (output_root / "worldcon_spike_story_results.jsonl").symlink_to(target)

        with self.assertRaises(OSError):
            run_worldcon_spike._append_story_result(
                output_root,
                run_worldcon_spike.StoryResult(
                    run_id="run-1",
                    story_id="horror_col/story_a",
                    title="Story",
                    story_path="horror_col/story_a.txt",
                    status="failed",
                    sidecar_path=None,
                    input_tokens=0,
                    output_tokens=0,
                    latency_seconds=0.0,
                    knight_interval=None,
                    qualified_novum_count=None,
                    dominant_novum_id=None,
                ),
            )


if __name__ == "__main__":
    unittest.main()
