"""Tests for the full-corpus linguistics experiment harness."""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest

_RUNNER_PATH = pathlib.Path(__file__).resolve().parent / "run_linguistics_corpora.py"
_SPEC = importlib.util.spec_from_file_location("run_linguistics_corpora", _RUNNER_PATH)
assert _SPEC is not None and _SPEC.loader is not None
run_linguistics_corpora = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = run_linguistics_corpora
_SPEC.loader.exec_module(run_linguistics_corpora)


def _write_story(
    corpus_root: pathlib.Path,
    collection: str,
    slug: str,
    body: str = "One short sentence. Another sentence follows.",
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


class DiscoveryTest(unittest.TestCase):
    def test_discovers_story_paths_deterministically(self):
        with tempfile.TemporaryDirectory() as tmp:
            corpus_root = pathlib.Path(tmp) / "corpora"
            beta = _write_story(corpus_root, "beta", "two")
            alpha = _write_story(corpus_root, "alpha", "one")

            discovered = run_linguistics_corpora.discover_story_paths(corpus_root)

            self.assertEqual(discovered, [alpha.resolve(), beta.resolve()])


class ExperimentHarnessTest(unittest.TestCase):
    def test_fake_backend_run_copies_buckets_and_writes_sidecars(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            corpus_root = root / "corpora"
            output_dir = root / "results"
            _write_story(corpus_root, "alpha", "one")
            _write_story(corpus_root, "beta", "two", "Unicode quote: “hello.”")

            report = run_linguistics_corpora.run_corpora(
                corpus_root=corpus_root,
                output_dir=output_dir,
                backend_name="fake",
                overwrite=True,
            )

            self.assertTrue(report["run_clean"])
            self.assertEqual(report["source_story_count"], 2)
            self.assertEqual(report["selected_story_count"], 2)
            self.assertEqual(report["analysis_story_count"], 2)
            self.assertEqual(report["analysis_exclusion_count"], 0)
            self.assertEqual(report["copied_story_count"], 2)
            self.assertEqual(report["copied_sidecar_count"], 2)
            self.assertFalse(report["corpora_modified"])
            self.assertEqual(report["run_counts"], {"written": 2})
            self.assertTrue(
                (output_dir / "copied_buckets" / "alpha" / "one" / "notes.txt").exists()
            )
            self.assertTrue(
                (
                    output_dir / "copied_buckets" / "alpha" / "one" / "linguistics.json"
                ).exists()
            )
            self.assertFalse(
                (corpus_root / "alpha" / "one" / "linguistics.json").exists()
            )
            story_list = (output_dir / "story-list.txt").read_text(encoding="utf-8")
            self.assertIn("copied_buckets/alpha/one/story.json", story_list)
            snapshot = json.loads(
                (output_dir / "snapshot_manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(snapshot["source_story_count"], 2)
            self.assertEqual(snapshot["selected_story_count"], 2)
            self.assertEqual(snapshot["analysis_story_count"], 2)
            self.assertEqual(len(snapshot["stories"]), 2)

    def test_smoke_count_limits_selected_stories(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            corpus_root = root / "corpora"
            output_dir = root / "results"
            _write_story(corpus_root, "alpha", "one")
            _write_story(corpus_root, "beta", "two")

            report = run_linguistics_corpora.run_corpora(
                corpus_root=corpus_root,
                output_dir=output_dir,
                backend_name="fake",
                smoke_count=1,
                overwrite=True,
            )

            self.assertEqual(report["source_story_count"], 2)
            self.assertEqual(report["selected_story_count"], 1)
            self.assertEqual(report["analysis_story_count"], 1)
            self.assertEqual(report["run_counts"], {"written": 1})
            self.assertTrue((output_dir / "copied_buckets" / "alpha" / "one").exists())
            self.assertFalse((output_dir / "copied_buckets" / "beta" / "two").exists())

    def test_empty_body_stories_are_copied_but_excluded_from_analysis(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            corpus_root = root / "corpora"
            output_dir = root / "results"
            _write_story(corpus_root, "alpha", "one")
            empty_story = _write_story(corpus_root, "beta", "empty", "")

            report = run_linguistics_corpora.run_corpora(
                corpus_root=corpus_root,
                output_dir=output_dir,
                backend_name="fake",
                overwrite=True,
            )

            copied_empty = output_dir / "copied_buckets" / "beta" / "empty"
            self.assertTrue(report["run_clean"])
            self.assertEqual(report["source_story_count"], 2)
            self.assertEqual(report["selected_story_count"], 2)
            self.assertEqual(report["analysis_story_count"], 1)
            self.assertEqual(report["analysis_exclusion_count"], 1)
            self.assertEqual(report["copied_story_count"], 2)
            self.assertEqual(report["copied_sidecar_count"], 1)
            self.assertEqual(report["run_counts"], {"written": 1})
            self.assertTrue((copied_empty / "story.json").exists())
            self.assertFalse((copied_empty / "linguistics.json").exists())
            self.assertEqual(
                report["analysis_exclusions"],
                [
                    {
                        "story_id": "beta/empty",
                        "story_path": (copied_empty / "story.json").resolve().as_posix(),
                        "reason": "empty_body",
                    }
                ],
            )
            story_list = (output_dir / "story-list.txt").read_text(encoding="utf-8")
            self.assertIn("copied_buckets/alpha/one/story.json", story_list)
            self.assertNotIn("copied_buckets/beta/empty/story.json", story_list)
            self.assertFalse((empty_story.parent / "linguistics.json").exists())

    def test_default_refuses_existing_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            corpus_root = root / "corpora"
            output_dir = root / "results"
            _write_story(corpus_root, "alpha", "one")

            run_linguistics_corpora.run_corpora(
                corpus_root=corpus_root,
                output_dir=output_dir,
                backend_name="fake",
                overwrite=True,
            )

            with self.assertRaisesRegex(FileExistsError, "use --resume"):
                run_linguistics_corpora.run_corpora(
                    corpus_root=corpus_root,
                    output_dir=output_dir,
                    backend_name="fake",
                )

    def test_resume_skips_existing_sidecars_and_preserves_snapshot_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            corpus_root = root / "corpora"
            output_dir = root / "results"
            _write_story(corpus_root, "alpha", "one")

            first = run_linguistics_corpora.run_corpora(
                corpus_root=corpus_root,
                output_dir=output_dir,
                backend_name="fake",
                overwrite=True,
            )
            snapshot_before = json.loads(
                (output_dir / "snapshot_manifest.json").read_text(encoding="utf-8")
            )
            snapshot_before["source_commit"] = "fixture-original-commit"
            (output_dir / "snapshot_manifest.json").write_text(
                json.dumps(snapshot_before, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

            resumed = run_linguistics_corpora.run_corpora(
                corpus_root=corpus_root,
                output_dir=output_dir,
                backend_name="fake",
                resume=True,
            )

            self.assertEqual(first["run_counts"], {"written": 1})
            self.assertEqual(resumed["run_counts"], {"skipped": 1})
            self.assertEqual(resumed["source_commit"], "fixture-original-commit")

    def test_resume_rejects_copied_story_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            corpus_root = root / "corpora"
            output_dir = root / "results"
            _write_story(corpus_root, "alpha", "one")

            run_linguistics_corpora.run_corpora(
                corpus_root=corpus_root,
                output_dir=output_dir,
                backend_name="fake",
                overwrite=True,
            )
            copied_story = output_dir / "copied_buckets" / "alpha" / "one" / "story.json"
            copied_story.write_text('{"body": "changed"}', encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                run_linguistics_corpora.run_corpora(
                    corpus_root=corpus_root,
                    output_dir=output_dir,
                    backend_name="fake",
                    resume=True,
                )

    def test_overwrite_prunes_stale_buckets_from_prior_larger_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            corpus_root = root / "corpora"
            output_dir = root / "results"
            _write_story(corpus_root, "alpha", "one")
            _write_story(corpus_root, "beta", "two")

            full_report = run_linguistics_corpora.run_corpora(
                corpus_root=corpus_root,
                output_dir=output_dir,
                backend_name="fake",
                overwrite=True,
            )
            smoke_report = run_linguistics_corpora.run_corpora(
                corpus_root=corpus_root,
                output_dir=output_dir,
                backend_name="fake",
                smoke_count=1,
                overwrite=True,
            )

            self.assertEqual(full_report["copied_sidecar_count"], 2)
            self.assertEqual(smoke_report["selected_story_count"], 1)
            self.assertEqual(smoke_report["copied_sidecar_count"], 1)
            self.assertTrue((output_dir / "copied_buckets" / "alpha" / "one").exists())
            self.assertFalse((output_dir / "copied_buckets" / "beta" / "two").exists())

    def test_reports_per_story_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            corpus_root = root / "corpora"
            output_dir = root / "results"
            _write_story(corpus_root, "alpha", "one")
            broken_dir = corpus_root / "beta" / "broken"
            broken_dir.mkdir(parents=True)
            (broken_dir / "story.json").write_text("{broken", encoding="utf-8")

            report = run_linguistics_corpora.run_corpora(
                corpus_root=corpus_root,
                output_dir=output_dir,
                backend_name="fake",
                overwrite=True,
            )

            self.assertFalse(report["run_clean"])
            self.assertEqual(report["run_counts"], {"failed": 1, "written": 1})
            self.assertEqual(len(report["failures"]), 1)
            self.assertIn("Expecting property name", report["failures"][0]["message"])

    def test_no_corpus_write_check_detects_source_sidecars(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            corpus_root = root / "corpora"
            output_dir = root / "results"
            selected_story = _write_story(corpus_root, "alpha", "one")
            (selected_story.parent / "linguistics.tokens.json").write_text(
                "{}", encoding="utf-8"
            )

            report = run_linguistics_corpora.run_corpora(
                corpus_root=corpus_root,
                output_dir=output_dir,
                backend_name="fake",
                overwrite=True,
            )

            self.assertTrue(report["corpora_modified"])
            self.assertEqual(
                report["corpus_linguistics_sidecars_found"],
                [
                    (selected_story.parent / "linguistics.tokens.json")
                    .resolve()
                    .as_posix()
                ],
            )


if __name__ == "__main__":
    unittest.main()
