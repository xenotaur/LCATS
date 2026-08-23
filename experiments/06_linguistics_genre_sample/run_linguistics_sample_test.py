"""Tests for the linguistics genre-sample experiment harness."""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest

_RUNNER_PATH = pathlib.Path(__file__).resolve().parent / "run_linguistics_sample.py"
_SPEC = importlib.util.spec_from_file_location("run_linguistics_sample", _RUNNER_PATH)
assert _SPEC is not None and _SPEC.loader is not None
run_linguistics_sample = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = run_linguistics_sample
_SPEC.loader.exec_module(run_linguistics_sample)


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


def _write_manifest(path: pathlib.Path, story_paths: list[pathlib.Path]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for index, story_path in enumerate(story_paths, start=1):
        relative = story_path.relative_to(story_path.parents[2])
        lines.append(
            json.dumps(
                {
                    "story_id": relative.parent.as_posix(),
                    "story_path": relative.as_posix(),
                    "selection_genre": "fantasy" if index == 1 else "mystery",
                    "title": f"Fixture {index}",
                },
                sort_keys=True,
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class ManifestLoadingTest(unittest.TestCase):
    def test_rejects_duplicate_story_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = pathlib.Path(tmp) / "manifest.jsonl"
            row = {
                "story_id": "collection/story",
                "story_path": "collection/story/story.json",
                "selection_genre": "fantasy",
            }
            manifest.write_text(
                json.dumps(row) + "\n" + json.dumps(row) + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "duplicate story_id"):
                run_linguistics_sample.load_manifest(manifest, expected_count=2)

    def test_rejects_story_paths_that_escape_corpus_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = pathlib.Path(tmp) / "manifest.jsonl"
            rows = [
                {
                    "story_id": "absolute",
                    "story_path": "/tmp/outside/story.json",
                    "selection_genre": "fantasy",
                },
                {
                    "story_id": "parent",
                    "story_path": "../outside/story.json",
                    "selection_genre": "mystery",
                },
            ]

            for row in rows:
                manifest.write_text(json.dumps(row) + "\n", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "within the corpus root"):
                    run_linguistics_sample.load_manifest(manifest, expected_count=1)


class ExperimentHarnessTest(unittest.TestCase):
    def test_fake_backend_run_copies_buckets_and_writes_sidecars(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            corpus_root = root / "corpora"
            output_dir = root / "results"
            story_paths = [
                _write_story(corpus_root, "alpha", "one"),
                _write_story(corpus_root, "beta", "two", "Unicode quote: “hello.”"),
            ]
            manifest = root / "manifest.jsonl"
            _write_manifest(manifest, story_paths)

            report = run_linguistics_sample.run_sample(
                manifest_path=manifest,
                corpus_root=corpus_root,
                output_dir=output_dir,
                backend_name="fake",
                expected_count=2,
                overwrite=True,
            )

            self.assertTrue(report["run_clean"])
            self.assertEqual(report["manifest_row_count"], 2)
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

    def test_report_checks_only_selected_source_buckets_for_corpus_sidecars(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            corpus_root = root / "corpora"
            output_dir = root / "results"
            selected_story = _write_story(corpus_root, "alpha", "one")
            unrelated_story = _write_story(corpus_root, "beta", "two")
            manifest = root / "manifest.jsonl"
            _write_manifest(manifest, [selected_story])
            (unrelated_story.parent / "linguistics.json").write_text(
                "{}", encoding="utf-8"
            )

            report = run_linguistics_sample.run_sample(
                manifest_path=manifest,
                corpus_root=corpus_root,
                output_dir=output_dir,
                backend_name="fake",
                expected_count=1,
                overwrite=True,
            )

            self.assertFalse(report["corpora_modified"])
            self.assertEqual(report["corpus_linguistics_sidecars_found"], [])

            (selected_story.parent / "linguistics.tokens.json").write_text(
                "{}", encoding="utf-8"
            )
            report = run_linguistics_sample.run_sample(
                manifest_path=manifest,
                corpus_root=corpus_root,
                output_dir=output_dir,
                backend_name="fake",
                expected_count=1,
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

    def test_smoke_count_limits_selected_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            corpus_root = root / "corpora"
            output_dir = root / "results"
            story_paths = [
                _write_story(corpus_root, "alpha", "one"),
                _write_story(corpus_root, "beta", "two"),
            ]
            manifest = root / "manifest.jsonl"
            _write_manifest(manifest, story_paths)

            report = run_linguistics_sample.run_sample(
                manifest_path=manifest,
                corpus_root=corpus_root,
                output_dir=output_dir,
                backend_name="fake",
                smoke_count=1,
                expected_count=2,
                overwrite=True,
            )

            self.assertEqual(report["manifest_row_count"], 2)
            self.assertEqual(report["selected_story_count"], 1)
            self.assertEqual(report["run_counts"], {"written": 1})
            self.assertTrue((output_dir / "copied_buckets" / "alpha" / "one").exists())
            self.assertFalse((output_dir / "copied_buckets" / "beta" / "two").exists())

    def test_overwrite_prunes_stale_buckets_from_prior_larger_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            corpus_root = root / "corpora"
            output_dir = root / "results"
            story_paths = [
                _write_story(corpus_root, "alpha", "one"),
                _write_story(corpus_root, "beta", "two"),
            ]
            manifest = root / "manifest.jsonl"
            _write_manifest(manifest, story_paths)

            full_report = run_linguistics_sample.run_sample(
                manifest_path=manifest,
                corpus_root=corpus_root,
                output_dir=output_dir,
                backend_name="fake",
                expected_count=2,
                overwrite=True,
            )
            smoke_report = run_linguistics_sample.run_sample(
                manifest_path=manifest,
                corpus_root=corpus_root,
                output_dir=output_dir,
                backend_name="fake",
                smoke_count=1,
                expected_count=2,
                overwrite=True,
            )

            self.assertEqual(full_report["copied_sidecar_count"], 2)
            self.assertEqual(smoke_report["selected_story_count"], 1)
            self.assertEqual(smoke_report["copied_sidecar_count"], 1)
            self.assertTrue((output_dir / "copied_buckets" / "alpha" / "one").exists())
            self.assertFalse((output_dir / "copied_buckets" / "beta" / "two").exists())

    def test_existing_copied_bucket_requires_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            corpus_root = root / "corpora"
            output_dir = root / "results"
            story_paths = [_write_story(corpus_root, "alpha", "one")]
            manifest = root / "manifest.jsonl"
            _write_manifest(manifest, story_paths)

            run_linguistics_sample.run_sample(
                manifest_path=manifest,
                corpus_root=corpus_root,
                output_dir=output_dir,
                backend_name="fake",
                expected_count=1,
                overwrite=True,
            )

            with self.assertRaisesRegex(FileExistsError, "use --overwrite"):
                run_linguistics_sample.run_sample(
                    manifest_path=manifest,
                    corpus_root=corpus_root,
                    output_dir=output_dir,
                    backend_name="fake",
                    expected_count=1,
                    overwrite=False,
                )


if __name__ == "__main__":
    unittest.main()
