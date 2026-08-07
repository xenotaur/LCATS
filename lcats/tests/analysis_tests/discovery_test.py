"""Unit tests for lcats.analysis.corpus.discovery."""

import pathlib
import unittest

from lcats.utils import test_utils
from lcats.analysis.corpus import discovery


class TestIterCollectionStoryFiles(test_utils.TestCaseWithData):
    """Unit tests for discovery.iter_collection_story_files."""

    def setUp(self):
        super().setUp()
        self.root = pathlib.Path(self.test_temp_dir) / "collection"
        self.root.mkdir()

    def _write(self, relpath):
        p = self.root / relpath
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{}", encoding="utf-8")
        return p

    def test_rejects_flat_story_any_name(self):
        """Regression test for Decision 4 (dual-layout retraction): a flat
        <story>.json file directly in a collection is no longer a valid
        story source, now that the production corpora/ snapshot is
        confirmed fully migrated to the bucket layout."""
        self._write("story1.json")
        found = list(discovery.iter_collection_story_files(self.root))
        self.assertEqual(found, [])

    def test_finds_nested_bucket_story(self):
        p = self._write("story1/story.json")
        found = list(discovery.iter_collection_story_files(self.root))
        self.assertEqual(found, [p])

    def test_ignores_flat_sibling_and_finds_bucket(self):
        """A flat file alongside a real bucket story: the flat file is
        rejected, the bucket story is still found."""
        self._write("flat_story.json")
        bucket = self._write("bucket_story/story.json")
        found = list(discovery.iter_collection_story_files(self.root))
        self.assertEqual(found, [bucket])

    def test_ignores_sidecar_json_in_bucket_dir(self):
        self._write("story1/story.json")
        self._write("story1/analysis.json")
        found = list(discovery.iter_collection_story_files(self.root))
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].name, "story.json")

    def test_skips_subdir_without_canonical_file(self):
        self._write("empty_dir/notes.txt")
        found = list(discovery.iter_collection_story_files(self.root))
        self.assertEqual(found, [])

    def test_ignores_non_json_flat_files(self):
        self._write("readme.txt")
        found = list(discovery.iter_collection_story_files(self.root))
        self.assertEqual(found, [])

    def test_does_not_recurse_past_one_level(self):
        self._write("a/b/story.json")
        found = list(discovery.iter_collection_story_files(self.root))
        self.assertEqual(found, [])

    def test_nonexistent_dir_yields_nothing(self):
        found = list(discovery.iter_collection_story_files(self.root / "nonexistent"))
        self.assertEqual(found, [])

    def test_rejects_flat_file_literally_named_story_json(self):
        """A flat file directly in a collection, even if literally named
        story.json, is not a bucket -- story.json only counts when nested
        one level inside its own story subdirectory."""
        self._write("story.json")
        found = list(discovery.iter_collection_story_files(self.root))
        self.assertEqual(found, [])

    def test_skips_symlinked_directories(self):
        real_target = self.root.parent / "outside_target"
        real_target.mkdir()
        (real_target / "story.json").write_text("{}", encoding="utf-8")
        link = self.root / "linked_story"
        try:
            link.symlink_to(real_target)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks not supported in this environment")
        found = list(discovery.iter_collection_story_files(self.root))
        self.assertEqual(found, [])

    def test_rejects_symlinked_flat_files(self):
        """A symlinked flat file is still a flat file -- rejected the same
        as any other flat file, not a special case."""
        real_target = self.root.parent / "real_story.json"
        real_target.write_text("{}", encoding="utf-8")
        link = self.root / "linked_story.json"
        try:
            link.symlink_to(real_target)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks not supported in this environment")
        found = list(discovery.iter_collection_story_files(self.root))
        self.assertEqual(found, [])


class TestFindJsonFiles(test_utils.TestCaseWithData):
    """Unit tests for discovery.find_json_files."""

    def setUp(self):
        super().setUp()
        self.root = pathlib.Path(self.test_temp_dir) / "corpus"
        self.root.mkdir()

    def _write(self, relpath):
        p = self.root / relpath
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{}", encoding="utf-8")
        return p

    def test_rejects_flat_story_at_collection_root(self):
        p = self._write("fantasy/story1.json")
        found = list(discovery.find_json_files([self.root]))
        self.assertNotIn(p, found)

    def test_finds_nested_bucket_story(self):
        p = self._write("fantasy/story1/story.json")
        found = list(discovery.find_json_files([self.root]))
        self.assertIn(p, found)

    def test_ignores_sidecar_json_in_bucket_dir(self):
        self._write("fantasy/story1/story.json")
        sidecar = self._write("fantasy/story1/analysis.json")
        found = list(discovery.find_json_files([self.root]))
        self.assertNotIn(sidecar, found)

    def test_only_bucket_layout_survives_mixed_collections(self):
        flat = self._write("fantasy/story1.json")
        bucket = self._write("horror/story2/story.json")
        found = set(discovery.find_json_files([self.root]))
        self.assertEqual(found, {bucket})
        self.assertNotIn(flat, found)

    def test_rejects_literal_flat_file_path(self):
        """A literal file path passed directly is only accepted if it is
        literally named story.json -- there is no caller-knows-best
        exception once dual-layout support is retracted."""
        p = self._write("standalone.json")
        found = list(discovery.find_json_files([p]))
        self.assertEqual(found, [])

    def test_finds_literal_story_json_path(self):
        """A literal path directly naming story.json is still accepted,
        unlike an arbitrarily-named literal path."""
        p = self._write("fantasy/story1/story.json")
        found = list(discovery.find_json_files([p]))
        self.assertEqual(found, [p])

    def test_nonexistent_directory_is_skipped_with_warning(self):
        found = list(discovery.find_json_files([self.root / "nonexistent"]))
        self.assertEqual(found, [])

    def test_bucket_layout_survives_pointing_directly_at_collection_dir(self):
        p = self._write("fantasy/story1/story.json")
        found = list(discovery.find_json_files([self.root / "fantasy"]))
        self.assertEqual(found, [p])

    def test_flat_layout_rejected_when_pointed_directly_at_collection_dir(self):
        self._write("fantasy/story1.json")
        found = list(discovery.find_json_files([self.root / "fantasy"]))
        self.assertEqual(found, [])

    def test_works_when_pointed_directly_at_story_bucket_dir(self):
        p = self._write("fantasy/story1/story.json")
        found = list(discovery.find_json_files([self.root / "fantasy" / "story1"]))
        self.assertEqual(found, [p])

    def test_pointed_directly_at_bucket_dir_excludes_sidecar(self):
        """Regression test: pointing find_json_files directly at a bucket
        directory that also holds a sidecar JSON file must yield only the
        canonical story file, not the sidecar."""
        p = self._write("fantasy/story1/story.json")
        self._write("fantasy/story1/analysis.json")
        found = list(discovery.find_json_files([self.root / "fantasy" / "story1"]))
        self.assertEqual(found, [p])

    def test_flat_filenames_are_rejected_at_every_scan_depth(self):
        """Regression test for Decision 4 (dual-layout retraction): plainly
        named flat stories, with no reserved-name collision, are still
        rejected at every scan depth (root, collection, direct file) --
        confirming the retraction is not just a narrow special case."""
        s1 = self._write("sherlock/story1.json")
        s2 = self._write("sherlock/story2.json")
        found = set(discovery.find_json_files([self.root]))
        self.assertEqual(found, set())
        self.assertNotIn(s1, found)
        self.assertNotIn(s2, found)

    def test_stray_collection_story_json_does_not_mask_nested_buckets(self):
        """Regression test: a collection directory with a stray flat file
        literally named story.json alongside real nested <story>/story.json
        buckets must not be mistaken for a single story's own bucket -- the
        real buckets underneath must still be found, when the collection
        directory itself is the scan target. Since Decision 4's retraction,
        the stray file is simply ignored (it's an ordinary rejected flat
        file, not a reserved name needing a warning)."""
        self._write("fantasy/story.json")
        s1 = self._write("fantasy/story1/story.json")
        s2 = self._write("fantasy/story2/story.json")
        found = set(discovery.find_json_files([self.root / "fantasy"]))
        self.assertEqual(found, {s1, s2})

    def test_stray_collection_story_json_does_not_mask_nested_buckets_from_corpus_root(
        self,
    ):
        """Same ambiguity as above, but reached by recursion from a corpus
        root that contains multiple collections -- the realistic call
        pattern (e.g. scanning the whole corpora/ directory)."""
        self._write("fantasy/story.json")
        s1 = self._write("fantasy/story1/story.json")
        s2 = self._write("fantasy/story2/story.json")
        other = self._write("horror/story3/story.json")
        found = set(discovery.find_json_files([self.root]))
        self.assertEqual(found, {s1, s2, other})


class TestFindJsonFilesIgnoreDirNames(test_utils.TestCaseWithData):
    """Unit tests for discovery.find_json_files's ignore_dir_names parameter."""

    def setUp(self):
        super().setUp()
        self.root = pathlib.Path(self.test_temp_dir) / "corpus"
        self.root.mkdir()

    def _write(self, relpath):
        p = self.root / relpath
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{}", encoding="utf-8")
        return p

    def test_prunes_matching_subdirectory(self):
        cached = self._write("cache/story1/story.json")
        real = self._write("fantasy/story2/story.json")
        found = set(discovery.find_json_files([self.root], ignore_dir_names=("cache",)))
        self.assertEqual(found, {real})
        self.assertNotIn(cached, found)

    def test_prune_is_case_insensitive(self):
        cached = self._write("Cache/story1/story.json")
        found = set(discovery.find_json_files([self.root], ignore_dir_names=("cache",)))
        self.assertNotIn(cached, found)

    def test_omitting_ignore_dir_names_leaves_behavior_unchanged(self):
        cached = self._write("cache/story1/story.json")
        real = self._write("fantasy/story2/story.json")
        found = set(discovery.find_json_files([self.root]))
        self.assertEqual(found, {cached, real})

    def test_top_level_directory_itself_is_not_pruned(self):
        """ignore_dir_names prunes descendants encountered during traversal,
        not the top-level directory passed in directly -- matching
        os.walk's own root-vs-children pruning semantics."""
        story = self._write("cache/story1/story.json")
        found = set(
            discovery.find_json_files(
                [self.root / "cache"], ignore_dir_names=("cache",)
            )
        )
        self.assertEqual(found, {story})

    def test_ignored_child_does_not_mask_a_real_leaf_bucket(self):
        """Regression test (Codex review, PR #238): a real story bucket
        that happens to contain an ignored subdirectory with its own
        nested story.json (e.g. story1/cache/story.json) must still be
        recognized as a leaf bucket -- the ignored child must not count
        as nested-story-bucket evidence disqualifying story1 itself."""
        real = self._write("fantasy/story1/story.json")
        self._write("fantasy/story1/cache/story.json")
        found = set(discovery.find_json_files([self.root], ignore_dir_names=("cache",)))
        self.assertEqual(found, {real})

    def test_generator_input_prunes_at_every_recursion_depth(self):
        """Regression test (Codex review, PR #238): ignore_dir_names must
        be safe to pass as a one-shot iterable (e.g. a generator) -- it
        must not be exhausted after the first use, which would silently
        stop pruning below the first traversal level."""
        cached_shallow = self._write("cache/story1/story.json")
        cached_deep = self._write("fantasy/cache/story2/story.json")
        real = self._write("fantasy/story3/story.json")

        found = set(
            discovery.find_json_files(
                [self.root], ignore_dir_names=(name for name in ["cache"])
            )
        )

        self.assertEqual(found, {real})
        self.assertNotIn(cached_shallow, found)
        self.assertNotIn(cached_deep, found)


if __name__ == "__main__":
    unittest.main()
