"""Unit tests for resolve_baseline_story_list.py.

Not part of the installed lcats package - run explicitly:

    python -m unittest experiments/03_cross_segment_relation_pilot/resolve_baseline_story_list_test.py
"""

from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import resolve_baseline_story_list  # noqa: E402


class TestResolveStoryIds(unittest.TestCase):
    def test_resolves_unique_slug_to_its_collection_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            corpora = tmp_path / "corpora"
            (corpora / "collection_a" / "story_one").mkdir(parents=True)
            (corpora / "collection_b" / "story_two").mkdir(parents=True)

            pilot_stories = tmp_path / "pilot_stories.jsonl"
            pilot_stories.write_text(
                json.dumps({"story_id": "story_one"})
                + "\n"
                + json.dumps({"story_id": "story_two"})
                + "\n"
            )

            resolved = resolve_baseline_story_list.resolve_story_ids(
                pilot_stories, corpora
            )

            self.assertEqual(
                resolved,
                [
                    corpora / "collection_a" / "story_one",
                    corpora / "collection_b" / "story_two",
                ],
            )

    def test_raises_on_zero_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            corpora = tmp_path / "corpora"
            corpora.mkdir()

            pilot_stories = tmp_path / "pilot_stories.jsonl"
            pilot_stories.write_text(json.dumps({"story_id": "missing_story"}) + "\n")

            with self.assertRaises(ValueError) as ctx:
                resolve_baseline_story_list.resolve_story_ids(pilot_stories, corpora)
            self.assertIn(":1:", str(ctx.exception))
            self.assertIn("missing_story", str(ctx.exception))

    def test_raises_on_malformed_json_line_with_line_number(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            corpora = tmp_path / "corpora"
            (corpora / "collection_a" / "story_one").mkdir(parents=True)

            pilot_stories = tmp_path / "pilot_stories.jsonl"
            pilot_stories.write_text(
                json.dumps({"story_id": "story_one"}) + "\n" + "{not valid json\n"
            )

            with self.assertRaises(ValueError) as ctx:
                resolve_baseline_story_list.resolve_story_ids(pilot_stories, corpora)
            self.assertIn(":2:", str(ctx.exception))

    def test_raises_on_row_missing_story_id_with_line_number(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            corpora = tmp_path / "corpora"
            corpora.mkdir()

            pilot_stories = tmp_path / "pilot_stories.jsonl"
            pilot_stories.write_text(json.dumps({"genre": "horror"}) + "\n")

            with self.assertRaises(ValueError) as ctx:
                resolve_baseline_story_list.resolve_story_ids(pilot_stories, corpora)
            self.assertIn(":1:", str(ctx.exception))
            self.assertIn("story_id", str(ctx.exception))

    def test_raises_on_ambiguous_multiple_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            corpora = tmp_path / "corpora"
            (corpora / "collection_a" / "dup_slug").mkdir(parents=True)
            (corpora / "collection_b" / "dup_slug").mkdir(parents=True)

            pilot_stories = tmp_path / "pilot_stories.jsonl"
            pilot_stories.write_text(json.dumps({"story_id": "dup_slug"}) + "\n")

            with self.assertRaises(ValueError):
                resolve_baseline_story_list.resolve_story_ids(pilot_stories, corpora)

    def test_preserves_input_row_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            corpora = tmp_path / "corpora"
            (corpora / "collection_a" / "z_story").mkdir(parents=True)
            (corpora / "collection_a" / "a_story").mkdir(parents=True)

            pilot_stories = tmp_path / "pilot_stories.jsonl"
            pilot_stories.write_text(
                json.dumps({"story_id": "z_story"})
                + "\n"
                + json.dumps({"story_id": "a_story"})
                + "\n"
            )

            resolved = resolve_baseline_story_list.resolve_story_ids(
                pilot_stories, corpora
            )

            self.assertEqual(
                resolved,
                [
                    corpora / "collection_a" / "z_story",
                    corpora / "collection_a" / "a_story",
                ],
            )


if __name__ == "__main__":
    unittest.main()
