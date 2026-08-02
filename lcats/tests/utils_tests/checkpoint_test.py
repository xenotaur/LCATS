"""Tests for lcats.utils.checkpoint."""

import json
import os
import pathlib
import tempfile
import unittest
from unittest.mock import patch

from lcats.utils import checkpoint


class ResolveRootsTest(unittest.TestCase):
    """Tests for resolve_roots's dual-root defaulting and write-guard."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_dir = pathlib.Path(self._tmp.name).resolve()
        # Anchor the protected-root computation at a controlled, fake
        # project root instead of this repo's real pyproject.toml, so the
        # guard tests are independent of this checkout's actual state and
        # of the real data/ and corpora/ directories existing on disk.
        self._patch = patch(
            "lcats.utils.checkpoint.paths.find_pyproject_root",
            return_value=self.tmp_dir,
        )
        self._patch.start()

    def tearDown(self):
        self._patch.stop()
        self._tmp.cleanup()

    def test_source_root_defaults_to_working_root(self):
        """Omitting source_root implies in-place checkpointing."""
        working = self.tmp_dir / "results"

        roots = checkpoint.resolve_roots(working)

        self.assertEqual(roots.working_root, working)
        self.assertEqual(roots.source_root, working)

    def test_explicit_source_root_is_kept_distinct(self):
        """An explicit source_root is not overwritten by the default."""
        working = self.tmp_dir / "results"
        source = self.tmp_dir / "data" / "some_collection"

        roots = checkpoint.resolve_roots(working, source_root=source)

        self.assertEqual(roots.working_root, working)
        self.assertEqual(roots.source_root, source)

    def test_working_root_under_data_root_is_rejected(self):
        """working_root resolving under the canonical data/ root is refused."""
        working = self.tmp_dir / "data" / "mycollection" / "mystory"

        with self.assertRaises(checkpoint.ProtectedRootError):
            checkpoint.resolve_roots(working)

    def test_working_root_under_corpora_root_is_rejected(self):
        """working_root resolving under the canonical corpora/ root is refused."""
        working = (self.tmp_dir / ".." / "corpora" / "mycollection").resolve()

        with self.assertRaises(checkpoint.ProtectedRootError):
            checkpoint.resolve_roots(working)

    def test_working_root_equal_to_protected_root_is_rejected(self):
        """The protected root itself, not just something nested inside it, is refused."""
        working = self.tmp_dir / "data"

        with self.assertRaises(checkpoint.ProtectedRootError):
            checkpoint.resolve_roots(working)

    def test_override_flag_allows_protected_root(self):
        """allow_protected_root=True is a deliberate, explicit opt-in."""
        working = self.tmp_dir / "data" / "mycollection"

        roots = checkpoint.resolve_roots(working, allow_protected_root=True)

        self.assertEqual(roots.working_root, working)

    def test_source_root_pointed_at_data_is_never_guarded(self):
        """Only working_root is guarded -- reading data/ as input is legitimate."""
        working = self.tmp_dir / "results"
        source = self.tmp_dir / "data" / "mycollection"

        roots = checkpoint.resolve_roots(working, source_root=source)

        self.assertEqual(roots.source_root, source)

    def test_working_root_outside_protected_roots_is_allowed(self):
        """An ordinary working directory outside data/corpora is unaffected."""
        working = self.tmp_dir / "experiments" / "03_pilot" / "results"

        roots = checkpoint.resolve_roots(working)

        self.assertEqual(roots.working_root, working)

    def test_guard_fires_regardless_of_process_cwd(self):
        """The guard is anchored to a fixed location, not the caller's CWD.

        Confirms the review finding this module's docstring documents:
        env.data_root()/corpora_root() resolve relative to CWD, which
        made the original guard design silently ineffective. Here, the
        anchor is patched to a fixed directory, so changing CWD to
        somewhere unrelated must not change the outcome.
        """
        working = self.tmp_dir / "data" / "mycollection"
        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as elsewhere:
            try:
                os.chdir(elsewhere)
                with self.assertRaises(checkpoint.ProtectedRootError):
                    checkpoint.resolve_roots(working)
            finally:
                os.chdir(original_cwd)

    def test_undetermined_protected_roots_raises_runtime_error(self):
        """A FileNotFoundError from find_pyproject_root (e.g. a non-editable
        install with no source tree) is wrapped into an actionable
        RuntimeError, not left as an undocumented, unactionable exception
        (review finding, PR #213)."""
        working = self.tmp_dir / "somewhere"
        with patch(
            "lcats.utils.checkpoint.paths.find_pyproject_root",
            side_effect=FileNotFoundError("no pyproject.toml found"),
        ):
            with self.assertRaises(RuntimeError):
                checkpoint.resolve_roots(working)


class CheckpointPathTest(unittest.TestCase):
    """Tests for checkpoint_path's directory-slug convention."""

    def test_uses_item_id_as_subdirectory(self):
        path = checkpoint.checkpoint_path("/working", "my_story", "segment")

        self.assertEqual(path, pathlib.Path("/working/my_story/segment.json"))

    def test_rejects_item_id_containing_path_separator(self):
        """item_id must not be able to escape working_root (review finding, PR #213)."""
        with self.assertRaises(ValueError):
            checkpoint.checkpoint_path("/working", "../escape", "segment")

    def test_rejects_absolute_item_id(self):
        with self.assertRaises(ValueError):
            checkpoint.checkpoint_path("/working", "/tmp", "segment")

    def test_rejects_dotdot_item_id(self):
        with self.assertRaises(ValueError):
            checkpoint.checkpoint_path("/working", "..", "segment")

    def test_rejects_stage_containing_path_separator(self):
        with self.assertRaises(ValueError):
            checkpoint.checkpoint_path("/working", "my_story", "sub/stage")


class WriteAndReadCheckpointTest(unittest.TestCase):
    """Tests for write_checkpoint/read_checkpoint's predicate and fingerprinting."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.working_root = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_read_before_any_write_is_not_done(self):
        result = checkpoint.read_checkpoint(
            self.working_root, "story_a", "segment", fingerprint={"model": "x"}
        )

        self.assertFalse(result.done)

    def test_write_then_read_round_trips_success(self):
        checkpoint.write_checkpoint(
            self.working_root,
            "story_a",
            "segment",
            outcome="success",
            fingerprint={"model": "x"},
            data={"segments": ["a", "b"]},
        )

        result = checkpoint.read_checkpoint(
            self.working_root, "story_a", "segment", fingerprint={"model": "x"}
        )

        self.assertTrue(result.done)
        self.assertEqual(result.outcome, "success")
        self.assertEqual(result.data, {"segments": ["a", "b"]})

    def test_predicate_distinguishes_success_from_failure(self):
        """A recorded failure is NOT 'done' -- the governing design requires
        a failed stage to be recomputed on resume, not silently skipped
        just because a checkpoint file exists (review finding, PR #213).
        Its outcome is still surfaced, distinguishing it from a checkpoint
        that doesn't exist at all."""
        checkpoint.write_checkpoint(
            self.working_root,
            "story_a",
            "segment",
            outcome="failure",
            fingerprint={"model": "x"},
        )

        result = checkpoint.read_checkpoint(
            self.working_root, "story_a", "segment", fingerprint={"model": "x"}
        )

        self.assertFalse(result.done)
        self.assertEqual(result.outcome, "failure")

    def test_malformed_utf8_is_treated_as_not_done(self):
        """Invalid UTF-8 bytes raise UnicodeDecodeError from read_text,
        which must be treated as an incomplete checkpoint like any other
        parse failure, not propagated as a crash (review finding, PR #213)."""
        item_dir = self.working_root / "story_a"
        item_dir.mkdir(parents=True)
        (item_dir / "segment.json").write_bytes(b"\xff\xfe not valid utf-8")

        result = checkpoint.read_checkpoint(
            self.working_root, "story_a", "segment", fingerprint={"model": "x"}
        )

        self.assertFalse(result.done)

    def test_fingerprint_with_tuple_value_round_trips_as_matching(self):
        """A fingerprint containing a tuple must still match its own
        just-written form after JSON round-tripping (tuple -> list),
        or every resume would recompute unnecessarily (review finding,
        PR #213)."""
        fingerprint = {"model": "x", "versions": (1, 2, 3)}
        checkpoint.write_checkpoint(
            self.working_root,
            "story_a",
            "segment",
            outcome="success",
            fingerprint=fingerprint,
        )

        result = checkpoint.read_checkpoint(
            self.working_root, "story_a", "segment", fingerprint=fingerprint
        )

        self.assertTrue(result.done)

    def test_non_json_serializable_fingerprint_does_not_raise(self):
        """A fingerprint containing a non-JSON-serializable value (e.g. a
        set) must not crash read_checkpoint -- normalization falls back
        to the raw value instead of raising, preserving the module's
        never-raises-on-comparison contract (independent review finding
        after PR #213's own fix round)."""
        checkpoint.write_checkpoint(
            self.working_root,
            "story_a",
            "segment",
            outcome="success",
            fingerprint={"model": "x"},
        )

        result = checkpoint.read_checkpoint(
            self.working_root,
            "story_a",
            "segment",
            fingerprint={"model": "x", "tags": {1, 2, 3}},
        )

        self.assertFalse(result.done)

    def test_fingerprint_with_int_dict_key_round_trips_as_matching(self):
        """A fingerprint containing an int dict key must still match its
        own just-written form after JSON round-tripping (int key ->
        string key)."""
        fingerprint = {"model": "x", "stage_versions": {1: "v1"}}
        checkpoint.write_checkpoint(
            self.working_root,
            "story_a",
            "segment",
            outcome="success",
            fingerprint=fingerprint,
        )

        result = checkpoint.read_checkpoint(
            self.working_root, "story_a", "segment", fingerprint=fingerprint
        )

        self.assertTrue(result.done)

    def test_fingerprint_mismatch_invalidates_checkpoint(self):
        checkpoint.write_checkpoint(
            self.working_root,
            "story_a",
            "segment",
            outcome="success",
            fingerprint={"model": "old-model"},
        )

        result = checkpoint.read_checkpoint(
            self.working_root,
            "story_a",
            "segment",
            fingerprint={"model": "new-model"},
        )

        self.assertFalse(result.done)

    def test_empty_fingerprint_opts_out_of_mismatch_check(self):
        """A caller that writes with no fingerprint gets it honored under
        any fingerprint on resume, since there is nothing to compare."""
        checkpoint.write_checkpoint(
            self.working_root,
            "story_a",
            "segment",
            outcome="success",
            fingerprint=None,
        )

        result = checkpoint.read_checkpoint(
            self.working_root,
            "story_a",
            "segment",
            fingerprint={"model": "anything"},
        )

        self.assertTrue(result.done)

    def test_malformed_json_is_treated_as_not_done(self):
        """A torn/corrupt checkpoint file is 'not done', not a hard failure."""
        item_dir = self.working_root / "story_a"
        item_dir.mkdir(parents=True)
        (item_dir / "segment.json").write_text("{not valid json", encoding="utf-8")

        result = checkpoint.read_checkpoint(
            self.working_root, "story_a", "segment", fingerprint={"model": "x"}
        )

        self.assertFalse(result.done)

    def test_missing_outcome_field_is_treated_as_not_done(self):
        """An unexpected shape (no recognizable outcome) is 'not done', not raised."""
        item_dir = self.working_root / "story_a"
        item_dir.mkdir(parents=True)
        (item_dir / "segment.json").write_text(
            json.dumps({"something_else": True}), encoding="utf-8"
        )

        result = checkpoint.read_checkpoint(
            self.working_root, "story_a", "segment", fingerprint={"model": "x"}
        )

        self.assertFalse(result.done)

    def test_invalid_outcome_value_raises(self):
        with self.assertRaises(ValueError):
            checkpoint.write_checkpoint(
                self.working_root,
                "story_a",
                "segment",
                outcome="maybe",
                fingerprint={"model": "x"},
            )

    def test_per_stage_granularity_is_independent(self):
        """Two stages for the same item checkpoint independently."""
        checkpoint.write_checkpoint(
            self.working_root,
            "story_a",
            "segment",
            outcome="success",
            fingerprint={"model": "x"},
        )

        segment_result = checkpoint.read_checkpoint(
            self.working_root, "story_a", "segment", fingerprint={"model": "x"}
        )
        extraction_result = checkpoint.read_checkpoint(
            self.working_root, "story_a", "extraction", fingerprint={"model": "x"}
        )

        self.assertTrue(segment_result.done)
        self.assertFalse(extraction_result.done)


class AtomicPublicationTest(unittest.TestCase):
    """Tests for write_checkpoint's atomic temp-file + os.replace behavior."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.working_root = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_no_temp_file_survives_a_successful_write(self):
        checkpoint.write_checkpoint(
            self.working_root,
            "story_a",
            "segment",
            outcome="success",
            fingerprint={"model": "x"},
        )

        item_dir = self.working_root / "story_a"
        leftovers = [p for p in item_dir.iterdir() if p.name != "segment.json"]
        self.assertEqual(leftovers, [])

    def test_interruption_mid_write_leaves_no_target_file(self):
        """A KeyboardInterrupt during the write never produces a torn target.

        KeyboardInterrupt is deliberately used here, not a plain Exception:
        it is a BaseException, matching the real interruption this
        checkpoint helper exists to survive (see WI-PIPELINE-0041's own
        review finding that a fake-backend test using an ordinary
        Exception does not exercise the real Ctrl-C escape path).
        """
        with patch("lcats.utils.checkpoint.json.dump", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                checkpoint.write_checkpoint(
                    self.working_root,
                    "story_a",
                    "segment",
                    outcome="success",
                    fingerprint={"model": "x"},
                )

        target = self.working_root / "story_a" / "segment.json"
        self.assertFalse(target.exists())
        item_dir = self.working_root / "story_a"
        self.assertEqual(list(item_dir.iterdir()), [])

    def test_interruption_mid_write_preserves_prior_checkpoint(self):
        """An interrupted re-write does not destroy an existing valid checkpoint."""
        checkpoint.write_checkpoint(
            self.working_root,
            "story_a",
            "segment",
            outcome="success",
            fingerprint={"model": "old"},
        )

        with patch("lcats.utils.checkpoint.json.dump", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                checkpoint.write_checkpoint(
                    self.working_root,
                    "story_a",
                    "segment",
                    outcome="success",
                    fingerprint={"model": "new"},
                )

        result = checkpoint.read_checkpoint(
            self.working_root, "story_a", "segment", fingerprint={"model": "old"}
        )
        self.assertTrue(result.done)


if __name__ == "__main__":
    unittest.main()
