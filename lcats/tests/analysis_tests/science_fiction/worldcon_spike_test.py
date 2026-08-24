"""Tests for the bounded Worldcon Knight/Novum spike runner."""

from __future__ import annotations

import json
import pathlib
import tempfile
import unittest

from experimental.science_fiction_analysis_trial import run_worldcon_spike
from lcats.analysis.science_fiction import sidecar
from lcats.utils import checkpoint


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
