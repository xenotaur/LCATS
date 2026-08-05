"""Unit tests for run_comparison.py and smoke_test.py's shared file selection.

Not part of the installed lcats package (these scripts live under
experiments/, not lcats/src/lcats/), so this is not discovered by lcats'
scripts/test (which only walks tests/) - run explicitly:

    python -m unittest experiments/02_llm_backend_comparison/run_comparison_test.py

or:

    python -m pytest experiments/02_llm_backend_comparison/run_comparison_test.py
"""

from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import run_comparison  # noqa: E402 - see sys.path.insert above
import smoke_test  # noqa: E402


def _write_bucket_story(collection_dir: pathlib.Path, slug: str) -> None:
    story_dir = collection_dir / slug
    story_dir.mkdir(parents=True)
    (story_dir / "story.json").write_text(
        json.dumps({"name": slug, "author": "Test Author", "body": "Body text."}),
        encoding="utf-8",
    )


class TestRunComparisonFindsBucketStories(unittest.TestCase):
    """run()'s story_files selection must find real bucket-layout stories
    (<collection>/<story>/story.json), not the retracted flat
    <collection>/<story>.json layout."""

    def test_finds_bucket_story_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            corpus_dir = pathlib.Path(tmp) / "lovecraft"
            _write_bucket_story(corpus_dir, "story_one")
            _write_bucket_story(corpus_dir, "story_two")

            found = sorted(
                run_comparison.discovery.iter_collection_story_files(corpus_dir)
            )

            self.assertEqual(len(found), 2)
            self.assertTrue(all(f.name == "story.json" for f in found))

    def test_flat_layout_file_is_not_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            corpus_dir = pathlib.Path(tmp) / "lovecraft"
            corpus_dir.mkdir(parents=True)
            _write_bucket_story(corpus_dir, "real_story")
            # A flat, retracted-layout file directly in the collection dir
            # -- the old corpus_dir.iterdir() selector would have found
            # this; the canonical selector must not.
            (corpus_dir / "flat_story.json").write_text(
                json.dumps({"name": "flat_story", "body": "Body."}), encoding="utf-8"
            )

            found = sorted(
                run_comparison.discovery.iter_collection_story_files(corpus_dir)
            )

            self.assertEqual(len(found), 1)
            self.assertEqual(found[0].parent.name, "real_story")


class TestSmokeTestActualSampleFindsBucketStories(unittest.TestCase):
    """smoke_test._actual_sample must use the same canonical selector as
    run_comparison, not a raw corpus_dir.glob("*.json")."""

    def test_actual_sample_counts_bucket_stories(self):
        with tempfile.TemporaryDirectory() as tmp:
            corpus_dir = pathlib.Path(tmp) / "lovecraft"
            _write_bucket_story(corpus_dir, "story_one")
            _write_bucket_story(corpus_dir, "story_two")
            _write_bucket_story(corpus_dir, "story_three")

            self.assertEqual(smoke_test._actual_sample(corpus_dir, requested=2), 2)
            self.assertEqual(smoke_test._actual_sample(corpus_dir, requested=10), 3)

    def test_actual_sample_ignores_flat_layout_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            corpus_dir = pathlib.Path(tmp) / "lovecraft"
            corpus_dir.mkdir(parents=True)
            _write_bucket_story(corpus_dir, "real_story")
            (corpus_dir / "flat_story.json").write_text(
                json.dumps({"name": "flat_story", "body": "Body."}), encoding="utf-8"
            )

            self.assertEqual(smoke_test._actual_sample(corpus_dir, requested=10), 1)


class TestSmokeTestRunsPointAtTrackedCorpora(unittest.TestCase):
    """_RUNS must point at the always-present corpora/ snapshot, not the
    gitignored, gather-populated data/ directory."""

    def test_runs_subdirs_do_not_reference_data_dir(self):
        for run_cfg in smoke_test._RUNS:
            self.assertFalse(
                run_cfg["corpus_subdir"].startswith("data/"),
                f"corpus_subdir {run_cfg['corpus_subdir']!r} still points at data/",
            )

    def test_runs_resolve_to_existing_tracked_corpora(self):
        for run_cfg in smoke_test._RUNS:
            corpus_dir = smoke_test._REPO_ROOT / "corpora" / run_cfg["corpus_subdir"]
            self.assertTrue(
                corpus_dir.is_dir(),
                f"{corpus_dir} does not exist -- smoke test would fail the "
                "corpus_dir.is_dir() precondition check",
            )


if __name__ == "__main__":
    unittest.main()
