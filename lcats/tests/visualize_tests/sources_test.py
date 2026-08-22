"""Unit tests for lcats.visualize.sources."""

import json
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


if __name__ == "__main__":
    unittest.main()
