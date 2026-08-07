"""Unit tests for lcats.analysis.corpus.cli.infer_story_title."""

import argparse
import json
import pathlib
import unittest

import pandas as pd

from lcats.analysis.corpus import cli
from lcats.utils import test_utils


class TestInferStoryTitle(unittest.TestCase):
    """Tests for cli.infer_story_title."""

    def test_bucket_layout_falls_back_to_directory_slug(self):
        data = {}
        path = pathlib.Path("collection/my_story/story.json")
        self.assertEqual(cli.infer_story_title(data, path), "my_story")

    def test_bucket_layout_prefers_directory_slug_over_name_field(self):
        """Regression test for Decision 2 of PROP-LCATS-STORY-BUCKET-LAYOUT:
        the directory slug is the primary identifier for a canonical
        story.json file, even when a (mutable, non-unique) name field is
        also present -- metadata must not override it."""
        data = {"name": "Mutable Metadata Title"}
        path = pathlib.Path("collection/my_story/story.json")
        self.assertEqual(cli.infer_story_title(data, path), "my_story")

    def test_bucket_layout_prefers_directory_slug_over_metadata_name(self):
        data = {"metadata": {"name": "Mutable Metadata Title"}}
        path = pathlib.Path("collection/my_story/story.json")
        self.assertEqual(cli.infer_story_title(data, path), "my_story")

    def test_data_argument_is_entirely_ignored(self):
        """Regression test for Decision 4 (dual-layout retraction):
        infer_story_title no longer has any conditional flat-vs-bucket
        logic -- it always returns the parent directory slug, regardless
        of story data content."""
        data = {"name": "Anything At All", "metadata": {"name": "Also Anything"}}
        path = pathlib.Path("collection/my_story/story.json")
        self.assertEqual(cli.infer_story_title(data, path), "my_story")

    def test_returns_parent_directory_name_regardless_of_leaf_filename(self):
        """infer_story_title no longer branches on the leaf filename at
        all -- every discoverable file is a bucket file post-retraction, so
        the parent directory name is returned unconditionally."""
        data = {}
        path = pathlib.Path("collection/my_story/anything.json")
        self.assertEqual(cli.infer_story_title(data, path), "my_story")


class TestRunStatsSelector(test_utils.TestCaseWithData):
    """Unit tests for run_stats's story-file selection.

    Regression coverage for WI-STATS-0049: run_stats must use the
    canonical, sidecar-excluding discovery.find_json_files selector
    (not the broad discovery.find_corpus_stories), while still excluding
    cache/ subdirectory contents, matching the pre-existing behavior."""

    def setUp(self):
        super().setUp()
        self.root = pathlib.Path(self.test_temp_dir) / "corpus"
        self.root.mkdir()

    def _write_story(self, relpath, name="Untitled"):
        p = self.root / relpath
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps({"name": name, "author": "Test Author", "body": "Body text."}),
            encoding="utf-8",
        )
        return p

    def _run_stats(self):
        story_output = self.root.parent / "story_stats.tsv"
        author_output = self.root.parent / "author_stats.tsv"
        args = argparse.Namespace(
            directories=[str(self.root)],
            dedupe=True,
            story_output=str(story_output),
            author_output=str(author_output),
        )
        exit_code = cli.run_stats(parsed_args=args)
        self.assertEqual(exit_code, 0)
        story_stats = pd.read_csv(story_output, sep="\t")
        return set(story_stats["path"])

    def test_sidecar_json_is_excluded(self):
        real = self._write_story("fantasy/story1/story.json", name="Real Story")
        sidecar = self.root / "fantasy" / "story1" / "analysis.json"
        sidecar.write_text(json.dumps({"unrelated": "data"}), encoding="utf-8")

        found = self._run_stats()

        self.assertIn(str(real), found)
        self.assertNotIn(str(sidecar), found)

    def test_cache_subdirectory_is_excluded(self):
        cached = self._write_story("cache/story1/story.json", name="Cached Story")
        real = self._write_story("fantasy/story2/story.json", name="Real Story")

        found = self._run_stats()

        self.assertIn(str(real), found)
        self.assertNotIn(str(cached), found)

    def test_real_bucket_layout_stories_are_found(self):
        s1 = self._write_story("fantasy/story1/story.json", name="Story One")
        s2 = self._write_story("horror/story2/story.json", name="Story Two")

        found = self._run_stats()

        self.assertEqual(found, {str(s1), str(s2)})


if __name__ == "__main__":
    unittest.main()
