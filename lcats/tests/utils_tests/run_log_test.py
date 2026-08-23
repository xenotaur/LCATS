"""Tests for lcats.utils.run_log."""

import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch

from lcats.utils import checkpoint
from lcats.utils import run_log


class LogEventTest(unittest.TestCase):
    """Tests for the free-function form."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_dir = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _read_lines(self, path):
        return [json.loads(line) for line in path.read_text().splitlines()]

    def test_appends_one_json_line_per_call(self):
        log_path = self.tmp_dir / "run.jsonl"

        run_log.log_event(log_path, "run_start", story_count=3)
        run_log.log_event(log_path, "story_completed", story_id="a")

        lines = self._read_lines(log_path)
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0]["event"], "run_start")
        self.assertEqual(lines[0]["story_count"], 3)
        self.assertEqual(lines[1]["event"], "story_completed")
        self.assertEqual(lines[1]["story_id"], "a")

    def test_every_line_has_a_timestamp(self):
        log_path = self.tmp_dir / "run.jsonl"

        run_log.log_event(log_path, "run_start")

        lines = self._read_lines(log_path)
        self.assertIn("timestamp", lines[0])

    def test_each_call_is_flushed_and_closed_immediately(self):
        """No buffered-but-unflushed line -- readable on disk after each call.

        Simulates the crash-safety property directly: since log_event()
        opens, writes, and closes per call rather than holding a handle
        open, the file on disk must already reflect a call's write the
        moment that call returns, before any further call happens.
        """
        log_path = self.tmp_dir / "run.jsonl"

        run_log.log_event(log_path, "run_start")
        first_read = self._read_lines(log_path)

        run_log.log_event(log_path, "run_end")
        second_read = self._read_lines(log_path)

        self.assertEqual(len(first_read), 1)
        self.assertEqual(len(second_read), 2)


class FatalError(Exception):
    """A stand-in for a caller's own fatal-error type."""


class RunLogTest(unittest.TestCase):
    """Tests for the RunLog context manager."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_dir = pathlib.Path(self._tmp.name).resolve()
        # Anchor the protected-root computation at a controlled, fake
        # project root, matching checkpoint_test.py's own pattern -- so
        # these tests are independent of this checkout's real data/ and
        # corpora/ directories.
        self._patch = patch(
            "lcats.utils.checkpoint.paths.find_pyproject_root",
            return_value=self.tmp_dir,
        )
        self._patch.start()

    def tearDown(self):
        self._patch.stop()
        self._tmp.cleanup()

    def _read_lines(self, path):
        return [json.loads(line) for line in path.read_text().splitlines()]

    def test_log_path_is_derived_under_working_root(self):
        working = self.tmp_dir / "results"

        log = run_log.RunLog(working, "run.jsonl")

        self.assertEqual(log.log_path, working / "run.jsonl")

    def test_accepts_a_checkpoint_roots_instance(self):
        working = self.tmp_dir / "results"
        roots = checkpoint.resolve_roots(working)

        log = run_log.RunLog(roots, "run.jsonl")

        self.assertEqual(log.log_path, working / "run.jsonl")

    def test_rejects_bare_working_root_under_protected_data_root(self):
        working = self.tmp_dir / "data" / "mycollection"

        with self.assertRaises(checkpoint.ProtectedRootError):
            run_log.RunLog(working, "run.jsonl")

    def test_rejects_directly_constructed_checkpoint_roots_under_protected_root(self):
        """A hand-built CheckpointRoots is never trusted as pre-validated.

        This is the specific gap review flagged on PR #352:
        CheckpointRoots is a bare frozen dataclass with only two Path
        fields, so nothing distinguishes a genuine resolve_roots()
        result from one a caller assembled by hand pointed at a
        protected root. RunLog must re-run the guard regardless.
        """
        working = (self.tmp_dir / ".." / "corpora" / "mycollection").resolve()
        hand_built_roots = checkpoint.CheckpointRoots(
            working_root=working, source_root=working
        )

        with self.assertRaises(checkpoint.ProtectedRootError):
            run_log.RunLog(hand_built_roots, "run.jsonl")

    def test_clean_exit_emits_run_start_and_run_end(self):
        working = self.tmp_dir / "results"

        with run_log.RunLog(working, "run.jsonl", model="x") as log:
            log.event("story_completed", story_id="a")

        lines = self._read_lines(working / "run.jsonl")
        events = [line["event"] for line in lines]
        self.assertEqual(events, ["run_start", "story_completed", "run_end"])
        self.assertEqual(lines[0]["model"], "x")

    def test_manually_logged_run_end_suppresses_the_automatic_one(self):
        """A caller-supplied, richer run_end is not followed by a bare one.

        Lets a caller emit its own run_end with custom summary fields
        (e.g. aggregate counts) as the last statement in the `with`
        block, instead of the bare event __exit__ would otherwise add.
        """
        working = self.tmp_dir / "results"

        with run_log.RunLog(working, "run.jsonl") as log:
            log.event("run_end", processed_count=3, aborted=False)

        lines = self._read_lines(working / "run.jsonl")
        events = [line["event"] for line in lines]
        self.assertEqual(events, ["run_start", "run_end"])
        self.assertEqual(lines[1]["processed_count"], 3)

    def test_fatal_exception_emits_run_aborted_fatal(self):
        working = self.tmp_dir / "results"

        with self.assertRaises(FatalError):
            with run_log.RunLog(working, "run.jsonl", fatal_exceptions=(FatalError,)):
                raise FatalError("account exhausted")

        lines = self._read_lines(working / "run.jsonl")
        events = [line["event"] for line in lines]
        self.assertEqual(events, ["run_start", "run_aborted_fatal"])

    def test_unclassified_exception_emits_run_aborted_unexpected(self):
        working = self.tmp_dir / "results"

        with self.assertRaises(RuntimeError):
            with run_log.RunLog(working, "run.jsonl", fatal_exceptions=(FatalError,)):
                raise RuntimeError("boom")

        lines = self._read_lines(working / "run.jsonl")
        events = [line["event"] for line in lines]
        self.assertEqual(events, ["run_start", "run_aborted_unexpected"])

    def test_exception_with_no_fatal_exceptions_configured_is_unexpected(self):
        working = self.tmp_dir / "results"

        with self.assertRaises(FatalError):
            with run_log.RunLog(working, "run.jsonl"):
                raise FatalError("would be fatal if classified")

        lines = self._read_lines(working / "run.jsonl")
        events = [line["event"] for line in lines]
        self.assertEqual(events, ["run_start", "run_aborted_unexpected"])

    def test_exception_still_propagates(self):
        working = self.tmp_dir / "results"

        with self.assertRaises(RuntimeError):
            with run_log.RunLog(working, "run.jsonl"):
                raise RuntimeError("boom")

    def test_rejects_absolute_filename(self):
        working = self.tmp_dir / "results"

        with self.assertRaises(ValueError):
            run_log.RunLog(working, "/etc/passwd")

    def test_rejects_filename_containing_parent_traversal(self):
        working = self.tmp_dir / "results"

        with self.assertRaises(ValueError):
            run_log.RunLog(working, "../escaped.jsonl")

    def test_rejects_filename_containing_a_path_separator(self):
        working = self.tmp_dir / "results"

        with self.assertRaises(ValueError):
            run_log.RunLog(working, "subdir/run.jsonl")

    def test_terminal_log_write_failure_does_not_mask_body_exception(self):
        """A failure writing the abort event must not replace the real error.

        Regression test for the exact gap review flagged on PR #359:
        without protection, __exit__'s own self.event() call raising
        (e.g. because the output directory vanished) would propagate
        instead of the original body exception, hiding the real failure.
        Calls __enter__/__exit__ directly (rather than via a `with`
        block) so the patch only takes effect during __exit__, not
        __enter__'s own unrelated run_start call.
        """
        working = self.tmp_dir / "results"
        log = run_log.RunLog(working, "run.jsonl")
        log.__enter__()

        with patch.object(run_log, "log_event", side_effect=OSError("disk full")):
            try:
                raise RuntimeError("the real failure")
            except RuntimeError as body_exc:
                suppressed = log.__exit__(
                    RuntimeError, body_exc, body_exc.__traceback__
                )

        self.assertFalse(suppressed)

    def test_refuses_to_follow_a_symlinked_log_path(self):
        """A symlink at the log path must not redirect writes elsewhere.

        Regression test for the review finding on PR #359: a plain
        Path.open("a") follows symlinks, so a run.jsonl symlink pointing
        outside the validated working_root would silently defeat the
        protected-root guard.
        """
        working = self.tmp_dir / "results"
        working.mkdir(parents=True)
        target = self.tmp_dir / "outside.jsonl"
        (working / "run.jsonl").symlink_to(target)

        with self.assertRaises(OSError):
            run_log.log_event(working / "run.jsonl", "run_start")

        self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
