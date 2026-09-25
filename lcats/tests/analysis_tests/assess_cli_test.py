"""Unit tests for lcats.analysis.corpus.assess_cli's run-event logging.

WI-RUNLOG-0082: assess_cli.py's per-file loop gets a crash-safe,
incremental run-event log via lcats.utils.run_log.RunLog, gated behind
the new --log-dir option (assess has no other durable working directory
to default to).
"""

import io
import json
import pathlib
import tempfile
import unittest
import unittest.mock

from lcats.analysis.corpus import assess
from lcats.analysis.corpus import assess_cli


def _write_story(collection_dir: pathlib.Path, name: str, body: str) -> None:
    # Bucket layout (PROP-LCATS-STORY-BUCKET-LAYOUT): a story is
    # <collection>/<story>/story.json, the only filename
    # discovery.find_json_files recognizes - a flat <name>.json file is
    # silently skipped.
    bucket_dir = collection_dir / name
    bucket_dir.mkdir(parents=True, exist_ok=True)
    (bucket_dir / "story.json").write_text(
        json.dumps({"name": name, "body": body}),
        encoding="utf-8",
    )


def _fake_result(file_path) -> assess.AssessmentResult:
    return assess.AssessmentResult(
        file_path=str(file_path),
        title="Title",
        author="Author",
        url="",
        target_genre="",
        verdict="include",
        detected_genre="other",
    )


class TestLogDirOmitted(unittest.TestCase):
    """--log-dir is optional; omitted, no log is written at all."""

    def test_no_log_dir_writes_no_log_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = pathlib.Path(tmp) / "data"
            _write_story(data_dir, "story_a", "Body text.")

            with (
                unittest.mock.patch.object(
                    assess_cli,
                    "assess_story",
                    side_effect=lambda **kw: _fake_result(kw["file_path"]),
                ),
                unittest.mock.patch.dict(
                    "os.environ", {"ANTHROPIC_API_KEY": "fake-key"}, clear=True
                ),
            ):
                exit_code = assess_cli.run(
                    [str(data_dir), "--format", "jsonl", "--no-progress"]
                )

            self.assertEqual(0, exit_code)
            # No --log-dir given, so nothing under tmp besides data/ exists.
            self.assertEqual(
                sorted(p.name for p in pathlib.Path(tmp).iterdir()), ["data"]
            )


class TestRunLogging(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_dir = pathlib.Path(self._tmp.name)
        self.data_dir = self.tmp_dir / "data"
        self.log_dir = self.tmp_dir / "assess_logs"
        _write_story(self.data_dir, "story_a", "Body text.")

    def tearDown(self):
        self._tmp.cleanup()

    def test_run_log_records_start_and_per_story_and_end_in_order(self):
        with (
            unittest.mock.patch.object(
                assess_cli,
                "assess_story",
                side_effect=lambda **kw: _fake_result(kw["file_path"]),
            ),
            unittest.mock.patch.dict(
                "os.environ", {"ANTHROPIC_API_KEY": "fake-key"}, clear=True
            ),
            unittest.mock.patch("sys.stdout", io.StringIO()),
        ):
            exit_code = assess_cli.run(
                [
                    str(self.data_dir),
                    "--format",
                    "jsonl",
                    "--no-progress",
                    "--log-dir",
                    str(self.log_dir),
                ]
            )

        self.assertEqual(0, exit_code)
        log_path = self.log_dir / "assess_run_log.jsonl"
        self.assertTrue(log_path.exists())
        events = [
            json.loads(line)
            for line in log_path.read_text(encoding="utf-8").splitlines()
        ]
        event_names = [e["event"] for e in events]
        self.assertEqual(event_names[0], "run_start")
        self.assertEqual(event_names[-1], "run_end")
        story_events = [e for e in events if e["event"] == "story_assessed"]
        self.assertEqual(len(story_events), 1)
        self.assertEqual(story_events[0]["verdict"], "include")

    def test_dry_run_logs_no_story_events(self):
        """--dry-run never calls assess_story, so only run_start/run_end
        should appear - nothing was actually assessed to log."""
        with (
            unittest.mock.patch.dict("os.environ", {}, clear=True),
            unittest.mock.patch("sys.stdout", io.StringIO()),
        ):
            exit_code = assess_cli.run(
                [
                    str(self.data_dir),
                    "--dry-run",
                    "--no-progress",
                    "--log-dir",
                    str(self.log_dir),
                ]
            )

        self.assertEqual(0, exit_code)
        log_path = self.log_dir / "assess_run_log.jsonl"
        events = [
            json.loads(line)
            for line in log_path.read_text(encoding="utf-8").splitlines()
        ]
        event_names = [e["event"] for e in events]
        self.assertNotIn("story_assessed", event_names)
        self.assertEqual(event_names, ["run_start", "run_end"])


if __name__ == "__main__":
    unittest.main()
