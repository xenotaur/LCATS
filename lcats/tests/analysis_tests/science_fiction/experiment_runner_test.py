"""Tests for the science-fiction fixture experiment runner."""

from __future__ import annotations

import json
import pathlib
import tempfile
import unittest

from experimental.science_fiction_analysis_trial import run_trial
from lcats.analysis.science_fiction import sidecar
from lcats.utils import checkpoint


class ScienceFictionExperimentRunnerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.manifest_path = run_trial.DEFAULT_MANIFEST

    def tearDown(self):
        self.tmp.cleanup()

    def test_dry_run_reports_manifest_without_publishing(self):
        summary = run_trial.run_trial(
            run_trial.RunnerOptions(
                manifest_path=self.manifest_path,
                output_root=self.root / "dry-run",
                dry_run=True,
            )
        )

        self.assertEqual("dry_run", summary["status"])
        self.assertEqual(12, summary["plan"]["case_count"])
        self.assertEqual([], summary["cases"])
        self.assertFalse((self.root / "dry-run" / "run_summary.json").exists())

    def test_fixture_coverage_matches_expected_tags(self):
        manifest = run_trial.load_manifest(self.manifest_path)
        expected = json.loads(
            (run_trial.FIXTURE_DIR / "expected_coverage.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertTrue(
            set(expected["required_tags"]).issubset(
                run_trial.fixture_coverage(manifest)
            )
        )

    def test_fixture_mode_publishes_valid_sidecars_and_expected_failures(self):
        output_root = self.root / "trial"

        summary = run_trial.run_trial(
            run_trial.RunnerOptions(
                manifest_path=self.manifest_path,
                output_root=output_root,
                max_retries=1,
                concurrency=2,
            )
        )

        self.assertEqual("complete", summary["status"])
        published = [case for case in summary["cases"] if case["status"] == "published"]
        expected_failures = [
            case for case in summary["cases"] if case["status"] == "expected_failure"
        ]
        self.assertEqual(10, len(published))
        self.assertEqual(
            {"interrupted_stage", "story_hash_mismatch"},
            {case["failure_kind"] for case in expected_failures},
        )
        for case in published:
            data = sidecar.load_json(pathlib.Path(case["sidecar_path"]))
            self.assertTrue(sidecar.validate_sidecar(data).valid)
            self.assertEqual(case["lcats_id"], data["lcats_id"])
        self.assertTrue((output_root / "run_summary.json").exists())

    def test_cross_chunk_fixture_uses_multiple_chunks_and_paragraphs(self):
        output_root = self.root / "cross-chunk"

        summary = run_trial.run_trial(
            run_trial.RunnerOptions(
                manifest_path=self.manifest_path,
                output_root=output_root,
            )
        )

        cross_chunk = next(
            case for case in summary["cases"] if case["case_id"] == "cross-chunk"
        )
        data = sidecar.load_json(pathlib.Path(cross_chunk["sidecar_path"]))
        records = data["evidence_sets"][0]["records"]
        paragraph_sets = {
            tuple(record["anchor"]["paragraph_ids"]) for record in records
        }
        source_chunks = {
            provenance["source_chunk_id"]
            for record in records
            for provenance in record["provenance"]
        }

        self.assertGreaterEqual(len(paragraph_sets), 2)
        self.assertGreaterEqual(len(source_chunks), 2)

    def test_resume_reuses_existing_checkpoint(self):
        output_root = self.root / "resume"
        options = run_trial.RunnerOptions(
            manifest_path=self.manifest_path,
            output_root=output_root,
            resume=True,
        )

        first = run_trial.run_trial(options)
        second = run_trial.run_trial(options)

        self.assertTrue(any(case["status"] == "published" for case in first["cases"]))
        self.assertTrue(
            all(
                case["reused_checkpoint"]
                for case in second["cases"]
                if case["status"] == "published"
            )
        )

    def test_published_sidecar_is_byte_stable_for_repeated_fixture_run(self):
        output_root = self.root / "stable"
        options = run_trial.RunnerOptions(
            manifest_path=self.manifest_path,
            output_root=output_root,
            resume=True,
        )

        first = run_trial.run_trial(options)
        first_sidecar = pathlib.Path(first["cases"][0]["sidecar_path"]).read_text(
            encoding="utf-8"
        )
        second = run_trial.run_trial(options)
        second_sidecar = pathlib.Path(second["cases"][0]["sidecar_path"]).read_text(
            encoding="utf-8"
        )

        self.assertEqual(first_sidecar, second_sidecar)

    def test_output_root_guard_rejects_protected_roots(self):
        protected = pathlib.Path(__file__).resolve().parents[3] / "data" / "sf-trial"

        with self.assertRaises(checkpoint.ProtectedRootError):
            run_trial.run_trial(
                run_trial.RunnerOptions(
                    manifest_path=self.manifest_path,
                    output_root=protected,
                    dry_run=True,
                )
            )

    def test_runner_rejects_non_fixture_or_paid_manifest(self):
        paid_manifest = self.root / "paid.json"
        paid_manifest.write_text(
            json.dumps(
                {
                    "version": run_trial.MANIFEST_VERSION,
                    "backend": "model",
                    "estimated_cost_usd": 1.25,
                    "cases": [],
                }
            ),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "fixture backend"):
            run_trial.run_trial(
                run_trial.RunnerOptions(
                    manifest_path=paid_manifest,
                    output_root=self.root / "paid",
                    dry_run=True,
                )
            )

    def test_retry_and_concurrency_bounds_are_enforced(self):
        with self.assertRaisesRegex(ValueError, "concurrency"):
            run_trial.run_trial(
                run_trial.RunnerOptions(
                    manifest_path=self.manifest_path,
                    output_root=self.root / "bad-concurrency",
                    dry_run=True,
                    concurrency=run_trial.MAX_CONCURRENCY + 1,
                )
            )
        with self.assertRaisesRegex(ValueError, "max_retries"):
            run_trial.run_trial(
                run_trial.RunnerOptions(
                    manifest_path=self.manifest_path,
                    output_root=self.root / "bad-retries",
                    dry_run=True,
                    max_retries=run_trial.MAX_RETRIES + 1,
                )
            )


if __name__ == "__main__":
    unittest.main()
