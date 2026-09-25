"""Unit tests for lcats.visualize.sources."""

import json
import os
import tempfile
import unittest
from pathlib import Path

from lcats.visualize import sources


def _write_summary(tmp_path, *, primary_counts, no_usable_signal_count, story_count):
    summary_path = Path(tmp_path) / "summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "story_count": story_count,
                "genre_coverage": {
                    "primary_target_genre_counts": primary_counts,
                    "no_usable_signal_count": no_usable_signal_count,
                },
                "target_candidate_counts": {
                    label: count + 1 for label, count in primary_counts.items()
                },
            }
        ),
        encoding="utf-8",
    )
    return summary_path


class TestLoadFullScanGenreCounts(unittest.TestCase):
    """Tests for load_full_scan_genre_counts."""

    def test_reads_primary_target_genre_counts(self):
        """Counts come from primary_target_genre_counts, not target_candidate_counts."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = _write_summary(
                tmp_dir,
                primary_counts={"fantasy": 3, "horror": 2},
                no_usable_signal_count=1,
                story_count=6,
            )
            result = sources.load_full_scan_genre_counts(str(path))
        self.assertEqual(result.counts, {"fantasy": 3, "horror": 2})

    def test_total_matches_story_count(self):
        """counts plus no_usable_signal_count sum to story_count."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = _write_summary(
                tmp_dir,
                primary_counts={"fantasy": 3, "horror": 2},
                no_usable_signal_count=1,
                story_count=6,
            )
            result = sources.load_full_scan_genre_counts(str(path))
        self.assertEqual(
            sum(result.counts.values()) + result.no_usable_signal_count,
            result.total_stories,
        )

    def test_source_revision_is_content_hash(self):
        """source_revision changes when the file content changes."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            path_a = _write_summary(
                tmp_dir,
                primary_counts={"fantasy": 3},
                no_usable_signal_count=0,
                story_count=3,
            )
            result_a = sources.load_full_scan_genre_counts(str(path_a))

        with tempfile.TemporaryDirectory() as tmp_dir:
            path_b = _write_summary(
                tmp_dir,
                primary_counts={"fantasy": 4},
                no_usable_signal_count=0,
                story_count=4,
            )
            result_b = sources.load_full_scan_genre_counts(str(path_b))

        self.assertNotEqual(result_a.source_revision, result_b.source_revision)

    def test_source_path_recorded(self):
        """source_path reflects the path argument."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = _write_summary(
                tmp_dir,
                primary_counts={"fantasy": 1},
                no_usable_signal_count=0,
                story_count=1,
            )
            result = sources.load_full_scan_genre_counts(str(path))
        self.assertEqual(result.source_path, str(path))

    def test_raises_when_counts_do_not_match_story_count(self):
        """An inconsistent artifact (counts don't sum to story_count) raises."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = _write_summary(
                tmp_dir,
                primary_counts={"fantasy": 3},
                no_usable_signal_count=5,
                story_count=10,
            )
            with self.assertRaises(ValueError):
                sources.load_full_scan_genre_counts(str(path))

    def test_default_path_resolves_from_lcats_package_directory(self):
        """The default path resolves even when run from inside lcats/.

        AGENTS.md documents running lcats commands from inside the lcats/
        package directory, but the checked-in full-scan artifact is a
        repository-root-relative sibling of lcats/, not inside it. A
        naive CWD-relative default would raise FileNotFoundError in that
        documented usage.
        """
        lcats_package_dir = Path(__file__).resolve().parents[2]
        original_cwd = Path.cwd()
        try:
            os.chdir(lcats_package_dir)
            result = sources.load_full_scan_genre_counts()
        finally:
            os.chdir(original_cwd)
        self.assertEqual(result.total_stories, 1868)


def _write_story(corpora_root, collection, slug, *, body, name=None):
    story_dir = Path(corpora_root) / collection / slug
    story_dir.mkdir(parents=True, exist_ok=True)
    (story_dir / "story.json").write_text(
        json.dumps({"name": name or slug, "body": body, "metadata": {}}),
        encoding="utf-8",
    )


def _write_candidates_jsonl(tmp_path, rows):
    path = Path(tmp_path) / "candidates.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for story_id, target_candidates in rows.items():
            f.write(
                json.dumps(
                    {
                        "story_id": story_id,
                        "metadata_assessment": {
                            "result": {"target_candidates": target_candidates}
                        },
                    }
                )
                + "\n"
            )
    return path


class TestLoadCorpusStories(unittest.TestCase):
    """Tests for load_corpus_stories."""

    def test_story_id_derived_from_path(self):
        """story_id is <collection>/<slug>, not derived from title/metadata."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            _write_story(tmp_dir, "anderson", "bell", body="Once upon a time.")
            result = sources.load_corpus_stories(tmp_dir)
        self.assertEqual(result.texts, {"anderson/bell": "Once upon a time."})

    def test_multiple_collections_and_stories(self):
        """All stories across all collections are loaded."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            _write_story(tmp_dir, "anderson", "bell", body="Text A")
            _write_story(tmp_dir, "anderson", "fir_tree", body="Text B")
            _write_story(tmp_dir, "grimm", "rapunzel", body="Text C")
            result = sources.load_corpus_stories(tmp_dir)
        self.assertEqual(
            result.texts,
            {
                "anderson/bell": "Text A",
                "anderson/fir_tree": "Text B",
                "grimm/rapunzel": "Text C",
            },
        )

    def test_source_revision_changes_with_content(self):
        """source_revision changes when a story's text changes."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            _write_story(tmp_dir, "anderson", "bell", body="Version 1")
            result_a = sources.load_corpus_stories(tmp_dir)

        with tempfile.TemporaryDirectory() as tmp_dir:
            _write_story(tmp_dir, "anderson", "bell", body="Version 2")
            result_b = sources.load_corpus_stories(tmp_dir)

        self.assertNotEqual(result_a.source_revision, result_b.source_revision)

    def test_source_revision_stable_for_same_content(self):
        """source_revision is deterministic for identical content."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            _write_story(tmp_dir, "anderson", "bell", body="Same text")
            result_a = sources.load_corpus_stories(tmp_dir)
            result_b = sources.load_corpus_stories(tmp_dir)
        self.assertEqual(result_a.source_revision, result_b.source_revision)


class TestLoadCandidatesGenreMembership(unittest.TestCase):
    """Tests for load_candidates_genre_membership."""

    def test_reads_target_candidates_per_story(self):
        """story_genres maps story_id to its target_candidates list."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = _write_candidates_jsonl(
                tmp_dir,
                {
                    "anderson/bell": ["fantasy"],
                    "anderson/fir_tree": ["fantasy", "humor"],
                },
            )
            result = sources.load_candidates_genre_membership(str(path))
        self.assertEqual(
            result.story_genres,
            {
                "anderson/bell": ["fantasy"],
                "anderson/fir_tree": ["fantasy", "humor"],
            },
        )

    def test_multi_label_preserved(self):
        """A story with more than one candidate genre keeps every label."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = _write_candidates_jsonl(
                tmp_dir, {"anderson/fir_tree": ["fantasy", "humor"]}
            )
            result = sources.load_candidates_genre_membership(str(path))
        self.assertEqual(len(result.story_genres["anderson/fir_tree"]), 2)

    def test_source_revision_is_content_hash(self):
        """source_revision changes when the file content changes."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            path_a = _write_candidates_jsonl(tmp_dir, {"a/b": ["fantasy"]})
            result_a = sources.load_candidates_genre_membership(str(path_a))
        with tempfile.TemporaryDirectory() as tmp_dir:
            path_b = _write_candidates_jsonl(tmp_dir, {"a/b": ["horror"]})
            result_b = sources.load_candidates_genre_membership(str(path_b))
        self.assertNotEqual(result_a.source_revision, result_b.source_revision)

    def test_duplicate_story_id_raises(self):
        """A story_id appearing in more than one row raises ValueError."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "candidates.jsonl"
            path.write_text(
                "\n".join(
                    json.dumps(
                        {
                            "story_id": "anderson/bell",
                            "metadata_assessment": {
                                "result": {"target_candidates": genres}
                            },
                        }
                    )
                    for genres in (["fantasy"], ["horror"])
                )
                + "\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                sources.load_candidates_genre_membership(str(path))


class TestLoadManifestSelection(unittest.TestCase):
    """Tests for manifest selection loading."""

    def test_reads_story_ids_and_selection_genres(self):
        """Manifest rows expose ordered story IDs and selection labels."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "manifest.jsonl"
            path.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "story_id": "anderson/bell",
                                "selection_genre": "fantasy",
                            }
                        ),
                        json.dumps(
                            {
                                "story_id": "chesterton/blue_cross",
                                "selection_genre": "mystery",
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            result = sources.load_manifest_selection(str(path))

        self.assertEqual(result.story_ids, ("anderson/bell", "chesterton/blue_cross"))
        self.assertEqual(result.selection_genres["anderson/bell"], ["fantasy"])
        self.assertIn("source_revision", result.__dataclass_fields__)

    def test_duplicate_manifest_story_id_raises(self):
        """Duplicate manifest story IDs are rejected."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "manifest.jsonl"
            path.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "story_id": "anderson/bell",
                                "selection_genre": "fantasy",
                            }
                        ),
                        json.dumps(
                            {
                                "story_id": "anderson/bell",
                                "selection_genre": "mystery",
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                sources.load_manifest_selection(str(path))


class TestLoadComparisonCorpus(unittest.TestCase):
    """Tests for comparison corpus source adaptation."""

    def test_joins_corpus_candidates_and_manifest_selection(self):
        """Comparison documents carry candidate and selection genre facts."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            corpora_root = Path(tmp_dir) / "corpora"
            _write_story(corpora_root, "anderson", "bell", body="dragon castle")
            _write_story(corpora_root, "chesterton", "blue_cross", body="detective")
            candidates_path = _write_candidates_jsonl(
                tmp_dir,
                {
                    "anderson/bell": ["fantasy"],
                    "chesterton/blue_cross": ["mystery"],
                },
            )
            manifest_path = Path(tmp_dir) / "manifest.jsonl"
            manifest_path.write_text(
                json.dumps(
                    {
                        "story_id": "anderson/bell",
                        "selection_genre": "sample-fantasy",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = sources.load_comparison_corpus(
                corpora_root=str(corpora_root),
                candidates_jsonl_path=str(candidates_path),
                manifest_jsonl_path=str(manifest_path),
            )

        documents = {document.story_id: document for document in result.documents}
        self.assertEqual(documents["anderson/bell"].candidate_genres, ("fantasy",))
        self.assertEqual(
            documents["anderson/bell"].selection_genres, ("sample-fantasy",)
        )
        self.assertEqual(documents["chesterton/blue_cross"].selection_genres, ())

    def test_manifest_story_missing_from_corpus_raises(self):
        """A manifest cannot silently select a story outside the corpus."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            corpora_root = Path(tmp_dir) / "corpora"
            _write_story(corpora_root, "anderson", "bell", body="dragon castle")
            candidates_path = _write_candidates_jsonl(
                tmp_dir, {"anderson/bell": ["fantasy"]}
            )
            manifest_path = Path(tmp_dir) / "manifest.jsonl"
            manifest_path.write_text(
                json.dumps(
                    {
                        "story_id": "anderson/missing",
                        "selection_genre": "fantasy",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                sources.load_comparison_corpus(
                    corpora_root=str(corpora_root),
                    candidates_jsonl_path=str(candidates_path),
                    manifest_jsonl_path=str(manifest_path),
                )


if __name__ == "__main__":
    unittest.main()
