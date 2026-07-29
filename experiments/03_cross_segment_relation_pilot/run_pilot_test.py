"""Unit tests for run_pilot.py.

Not part of the installed lcats package (this script lives under
experiments/, not lcats/lcats/), so it is not discovered by lcats'
scripts/test (which only walks tests/) - run explicitly:

    python -m unittest experiments/03_cross_segment_relation_pilot/run_pilot_test.py

or:

    python -m pytest experiments/03_cross_segment_relation_pilot/run_pilot_test.py
"""

from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import unittest

from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import run_pilot  # noqa: E402 - see sys.path.insert above


class TestMainUnexpectedPerStoryException(unittest.TestCase):
    """WI-EVENT-0032 (audit's Category B update finding): main()'s per-story
    loop previously caught only FatalPilotError - any other exception
    propagated straight out of main(), skipping the write block entirely
    and discarding every already-completed, already-paid-for story's
    results, not just the one that failed."""

    def _write_story(self, data_dir: pathlib.Path, name: str, body: str) -> None:
        (data_dir / f"{name}.json").write_text(
            json.dumps({"name": name, "author": "Test Author", "body": body}),
            encoding="utf-8",
        )

    def test_unexpected_exception_on_one_story_preserves_other_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = pathlib.Path(tmp) / "data"
            data_dir.mkdir()
            output_dir = pathlib.Path(tmp) / "results"
            self._write_story(data_dir, "story_a", "Story A body text.")
            self._write_story(data_dir, "story_b", "Story B body text.")

            real_row = {
                "path": str(data_dir / "story_a.json"),
                "story_id": "story_a",
                "genre": "science fiction",
                "excluded": False,
                "exclude_reason": "",
                "word_count": 3,
                "segment_count": 1,
                "cross_segment_density_per_1000_words": 0.0,
                "weakly_inferred_cross_segment_density_per_1000_words": 0.0,
                "folded_relations_per_1000_words": 0.0,
                "folded_weakly_inferred_relations_per_1000_words": 0.0,
            }

            def fake_run_story(path, genre, *args, **kwargs):
                if path.stem == "story_b":
                    raise RuntimeError("simulated unexpected per-story failure")
                return dict(real_row), []

            argv = [
                "run_pilot.py",
                "--dry-run",
                "--data-dir",
                str(data_dir),
                "--sample-size",
                "1",
                "--output",
                str(output_dir),
            ]
            with patch.object(sys, "argv", argv), patch.object(
                run_pilot, "run_story", side_effect=fake_run_story
            ):
                exit_code = run_pilot.main()

            self.assertEqual(exit_code, 0)

            stories_path = output_dir / "pilot_stories.jsonl"
            self.assertTrue(stories_path.exists())
            rows = [
                json.loads(line)
                for line in stories_path.read_text(encoding="utf-8").splitlines()
            ]
            rows_by_story_id = {row["story_id"]: row for row in rows}

            # story_a's real, already-completed result must still be
            # written - not discarded because story_b crashed later.
            self.assertIn("story_a", rows_by_story_id)
            self.assertFalse(rows_by_story_id["story_a"]["excluded"])

            # story_b is recorded as excluded with the unexpected error,
            # not silently dropped and not aborting the whole run.
            self.assertIn("story_b", rows_by_story_id)
            self.assertTrue(rows_by_story_id["story_b"]["excluded"])
            self.assertIn(
                "unexpected error", rows_by_story_id["story_b"]["exclude_reason"]
            )
            self.assertIn(
                "simulated unexpected per-story failure",
                rows_by_story_id["story_b"]["exclude_reason"],
            )


if __name__ == "__main__":
    unittest.main()
