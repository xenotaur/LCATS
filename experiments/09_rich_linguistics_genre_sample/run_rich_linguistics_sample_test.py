"""Tests for the rich linguistics sample pilot harness."""

from __future__ import annotations

import importlib.util
import csv
import json
import pathlib
import sys
import tempfile
import unittest

_RUNNER_PATH = pathlib.Path(__file__).resolve().parent / "run_rich_linguistics_sample.py"
_SPEC = importlib.util.spec_from_file_location("run_rich_linguistics_sample", _RUNNER_PATH)
assert _SPEC is not None and _SPEC.loader is not None
run_rich_linguistics_sample = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = run_rich_linguistics_sample
_SPEC.loader.exec_module(run_rich_linguistics_sample)


def _write_story(
    corpus_root: pathlib.Path,
    collection: str,
    slug: str,
    body: str = "Alice saw the brass Machine. The captain won't retreat.",
) -> pathlib.Path:
    story_dir = corpus_root / collection / slug
    story_dir.mkdir(parents=True)
    story_path = story_dir / "story.json"
    story_path.write_text(
        json.dumps(
            {
                "name": f"{collection} - {slug}",
                "body": body,
                "metadata": {"author": "Fixture Author", "year": 1901},
            }
        ),
        encoding="utf-8",
    )
    (story_dir / "notes.txt").write_text("preserved bucket file", encoding="utf-8")
    return story_path


def _write_manifest(path: pathlib.Path, story_paths: list[pathlib.Path]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for index, story_path in enumerate(story_paths, start=1):
        relative = story_path.relative_to(story_path.parents[2])
        genre = "fantasy" if index == 1 else "mystery"
        lines.append(
            json.dumps(
                {
                    "author": f"Author {index}",
                    "story_id": relative.parent.as_posix(),
                    "story_path": relative.as_posix(),
                    "selection_genre": genre,
                    "title": f"Fixture {index}",
                },
                sort_keys=True,
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class RichPilotHarnessTest(unittest.TestCase):
    def test_fake_backend_run_writes_v2_lexicon_and_pending_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            corpus_root = root / "corpora"
            output_dir = root / "results"
            stories = [
                _write_story(corpus_root, "alpha", "one"),
                _write_story(corpus_root, "beta", "two"),
            ]
            manifest = root / "manifest.jsonl"
            _write_manifest(manifest, stories)

            report = run_rich_linguistics_sample.run_pilot(
                manifest_path=manifest,
                corpus_root=corpus_root,
                output_dir=output_dir,
                backend_name="fake",
                expected_count=2,
                overwrite=True,
            )

            self.assertTrue(report["run_clean"])
            self.assertEqual(report["selected_story_count"], 2)
            self.assertEqual(report["projected_full_corpus"]["story_count"], 2)
            self.assertEqual(report["compact_sidecar_count"], 2)
            self.assertEqual(report["token_detail_count"], 2)
            self.assertEqual(report["lexicon_count"], 2)
            self.assertEqual(report["pos_audit_status"], "manual_audit_pending")
            self.assertEqual(report["decisions"]["sample_pos_figures"]["decision"], "defer")
            self.assertFalse(report["corpora_modified"])
            self.assertTrue(
                (
                    output_dir
                    / "copied_buckets"
                    / "alpha"
                    / "one"
                    / "linguistics.tokens.json"
                ).exists()
            )
            self.assertTrue(
                (
                    output_dir
                    / "copied_buckets"
                    / "alpha"
                    / "one"
                    / "linguistics.lexicon.json"
                ).exists()
            )
            self.assertTrue((output_dir / "pos_audit_sample.csv").exists())
            audit = json.loads((output_dir / "pos_audit.json").read_text())
            self.assertEqual(audit["status"], "manual_audit_pending")

    def test_missing_output_findings_use_dict_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            story_path = _write_story(root / "corpora", "alpha", "one")

            summary = run_rich_linguistics_sample.validate_generated_artifacts(
                [story_path]
            )

            [row] = summary["results"]
            self.assertFalse(row["valid"])
            self.assertEqual(
                [
                    {
                        "artifact": "outputs",
                        "severity": "error",
                        "message": "missing one or more generated outputs",
                    }
                ],
                row["findings"],
            )

    def test_prune_results_removes_stale_parquet_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = pathlib.Path(tmp) / "results"
            stale_parquet = output_dir / "parquet"
            stale_parquet.mkdir(parents=True)
            (stale_parquet / "parquet_manifest.json").write_text(
                "{}", encoding="utf-8"
            )

            run_rich_linguistics_sample.prune_results(output_dir)

            self.assertFalse(stale_parquet.exists())

    def test_resume_validates_snapshot_and_skips_existing_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            corpus_root = root / "corpora"
            output_dir = root / "results"
            stories = [_write_story(corpus_root, "alpha", "one")]
            manifest = root / "manifest.jsonl"
            _write_manifest(manifest, stories)

            first = run_rich_linguistics_sample.run_pilot(
                manifest_path=manifest,
                corpus_root=corpus_root,
                output_dir=output_dir,
                backend_name="fake",
                expected_count=1,
                overwrite=True,
            )
            resumed = run_rich_linguistics_sample.run_pilot(
                manifest_path=manifest,
                corpus_root=corpus_root,
                output_dir=output_dir,
                backend_name="fake",
                expected_count=1,
                resume=True,
            )

            self.assertEqual(first["run_counts"], {"written": 1})
            self.assertEqual(resumed["run_counts"], {"skipped": 1})

    def test_scored_audit_produces_go_decisions_when_gate_passes(self):
        rows = []
        labels = {}
        for genre in ("fantasy", "mystery"):
            for index in range(12):
                upos = "NOUN" if index % 2 == 0 else "PROPN"
                token_key = f"{genre}-{index}"
                rows.append(
                    {
                        "story_id": f"{genre}/story",
                        "selection_genre": genre,
                        "token_key": token_key,
                        "machine_upos": upos,
                        "gold_upos": upos,
                    }
                )
                labels[token_key] = upos

        scoring = run_rich_linguistics_sample.score_audit(rows, labels)
        decisions = run_rich_linguistics_sample.scored_decisions(scoring)

        self.assertEqual(decisions["quality_recommendation"], "proceed")
        self.assertEqual(decisions["sample_pos_figures"]["decision"], "proceed")
        self.assertEqual(scoring["overall"]["noun_family"]["precision"], 1.0)

    def test_scoring_preserves_labels_when_labels_path_is_output_sample(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            output_dir = root / "results"
            sample_rows = [
                {
                    "story_id": "alpha/one",
                    "selection_genre": "fantasy",
                    "audit_bucket": "NOUN",
                    "audit_features": "ordinary",
                    "token_key": "alpha/one#g1",
                    "sentence_index": 0,
                    "token_index": 0,
                    "global_token_index": 1,
                    "text": "machine",
                    "lemma": "machine",
                    "machine_upos": "NOUN",
                    "context": "The machine hums.",
                    "gold_upos": "",
                    "notes": "",
                }
            ]
            sample_path = output_dir / "pos_audit_sample.csv"
            output_dir.mkdir(parents=True)
            with sample_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle, fieldnames=run_rich_linguistics_sample.AUDIT_FIELDS
                )
                writer.writeheader()
                writer.writerow({**sample_rows[0], "gold_upos": "NOUN"})

            original_select = run_rich_linguistics_sample.select_audit_rows
            try:
                run_rich_linguistics_sample.select_audit_rows = (
                    lambda _snapshot, _paths: sample_rows
                )
                audit = run_rich_linguistics_sample.build_pos_audit(
                    snapshot_manifest={"stories": []},
                    copied_story_paths=[],
                    output_dir=output_dir,
                    labels_path=sample_path,
                )
            finally:
                run_rich_linguistics_sample.select_audit_rows = original_select

            self.assertEqual("scored", audit["status"])
            with sample_path.open("r", encoding="utf-8", newline="") as handle:
                scored_rows = list(csv.DictReader(handle))
            self.assertEqual("NOUN", scored_rows[0]["gold_upos"])

    def test_genre_audit_selection_balances_machine_positive_and_negative_rows(self):
        buckets = {"NOUN": [], "PROPN": [], "OTHER": []}
        for bucket in buckets:
            for index in range(12):
                text = f"{bucket.title()}{index}"
                row = {
                    "story_id": f"story/{bucket.casefold()}",
                    "selection_genre": "fantasy",
                    "audit_bucket": bucket,
                    "audit_features": ",".join(
                        run_rich_linguistics_sample._audit_features(text, bucket)
                    ),
                    "token_key": f"{bucket}-{index}",
                    "machine_upos": bucket,
                    "global_token_index": index,
                    "text": text,
                }
                buckets[bucket].append(row)

        selected = run_rich_linguistics_sample.select_genre_audit_rows(
            buckets, rows_per_genre=24
        )

        selected_by_bucket = {}
        for row in selected:
            selected_by_bucket[row["audit_bucket"]] = (
                selected_by_bucket.get(row["audit_bucket"], 0) + 1
            )
        self.assertEqual({"NOUN": 8, "PROPN": 8, "OTHER": 8}, selected_by_bucket)

    def test_rejects_incomplete_audit_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            corpus_root = root / "corpora"
            output_dir = root / "results"
            stories = [_write_story(corpus_root, "alpha", "one")]
            manifest = root / "manifest.jsonl"
            _write_manifest(manifest, stories)
            run_rich_linguistics_sample.run_pilot(
                manifest_path=manifest,
                corpus_root=corpus_root,
                output_dir=output_dir,
                backend_name="fake",
                expected_count=1,
                overwrite=True,
            )
            labels_path = root / "labels.csv"
            with labels_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["token_key", "gold_upos"])
                writer.writeheader()
                writer.writerow({"token_key": "not-the-token", "gold_upos": "NOUN"})

            with self.assertRaisesRegex(ValueError, "no audit sample rows"):
                run_rich_linguistics_sample.run_pilot(
                    manifest_path=manifest,
                    corpus_root=corpus_root,
                    output_dir=output_dir,
                    backend_name="fake",
                    expected_count=1,
                    resume=True,
                    audit_labels_path=labels_path,
                )

    def test_resume_rejects_copied_story_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            corpus_root = root / "corpora"
            output_dir = root / "results"
            stories = [_write_story(corpus_root, "alpha", "one")]
            manifest = root / "manifest.jsonl"
            _write_manifest(manifest, stories)
            run_rich_linguistics_sample.run_pilot(
                manifest_path=manifest,
                corpus_root=corpus_root,
                output_dir=output_dir,
                backend_name="fake",
                expected_count=1,
                overwrite=True,
            )
            copied_story = output_dir / "copied_buckets" / "alpha" / "one" / "story.json"
            copied_story.write_text('{"body": "changed"}', encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                run_rich_linguistics_sample.run_pilot(
                    manifest_path=manifest,
                    corpus_root=corpus_root,
                    output_dir=output_dir,
                    backend_name="fake",
                    expected_count=1,
                    resume=True,
                )


if __name__ == "__main__":
    unittest.main()
