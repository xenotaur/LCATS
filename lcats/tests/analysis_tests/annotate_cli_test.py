"""Unit tests for lcats.analysis.corpus.annotate_cli."""

import io
import json
import pathlib
import tempfile
import unittest
import unittest.mock

from lcats.analysis.corpus import annotate_cli


def _write_story(collection_dir: pathlib.Path, name: str, body: str) -> None:
    bucket_dir = collection_dir / name
    bucket_dir.mkdir(parents=True, exist_ok=True)
    (bucket_dir / "story.json").write_text(
        json.dumps({"name": name, "body": body, "metadata": {}}),
        encoding="utf-8",
    )


class BuildParserTest(unittest.TestCase):
    def test_defaults(self):
        parser = annotate_cli.build_parser()
        args = parser.parse_args([])
        self.assertEqual(pathlib.Path(".annotate_checkpoints"), args.checkpoint_dir)
        self.assertEqual("claude-opus-4-8", args.model)
        self.assertFalse(args.dry_run)


class AnnotateCliDryRunTest(unittest.TestCase):
    def test_dry_run_lists_story_buckets_without_api_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            source_root = pathlib.Path(tmp)
            _write_story(source_root / "collection_a", "story_one", "Body.")

            output = io.StringIO()
            with (
                unittest.mock.patch("sys.stdout", output),
                unittest.mock.patch.dict("os.environ", {}, clear=True),
            ):
                exit_code = annotate_cli.run(
                    ["--source", str(source_root), "--dry-run"]
                )

            self.assertEqual(0, exit_code)
            self.assertIn("collection_a/story_one", output.getvalue())


class AnnotateCliMissingApiKeyTest(unittest.TestCase):
    def test_missing_api_key_without_dry_run_reports_clean_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            source_root = pathlib.Path(tmp)

            error_output = io.StringIO()
            with (
                unittest.mock.patch("sys.stderr", error_output),
                unittest.mock.patch.dict("os.environ", {}, clear=True),
            ):
                exit_code = annotate_cli.run(["--source", str(source_root)])

            self.assertEqual(1, exit_code)
            self.assertIn("ANTHROPIC_API_KEY", error_output.getvalue())


class AnnotateCliRunLoggingTest(unittest.TestCase):
    """WI-RUNLOG-0082: annotate_cli.run() wraps annotate.annotate_collections()
    in a run_log.RunLog scope, log path under the existing --checkpoint-dir."""

    def test_run_writes_a_run_log_under_checkpoint_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            source_root = pathlib.Path(tmp) / "data"
            checkpoint_dir = pathlib.Path(tmp) / "checkpoints"
            _write_story(source_root / "collection_a", "story_one", "Body.")

            def fake_annotate_collections(
                source, *, backend, model, roots, log, collection_names=None
            ):
                # Exercises annotate_cli.py's own RunLog wiring in
                # isolation from the real LLM-backed annotation chain
                # (covered directly against annotate.annotate_collections
                # itself in annotate_test.py's TestRunLogging).
                log.event("story_annotated", story_id="collection_a__story_one")
                return {}

            with (
                unittest.mock.patch("lcats.llm.anthropic_backend.AnthropicBackend"),
                unittest.mock.patch(
                    "lcats.analysis.corpus.annotate.annotate_collections",
                    side_effect=fake_annotate_collections,
                ),
                unittest.mock.patch.dict(
                    "os.environ", {"ANTHROPIC_API_KEY": "fake-key"}, clear=True
                ),
            ):
                exit_code = annotate_cli.run(
                    [
                        "--source",
                        str(source_root),
                        "--checkpoint-dir",
                        str(checkpoint_dir),
                    ]
                )

            self.assertEqual(0, exit_code)
            log_path = checkpoint_dir / "annotate_run_log.jsonl"
            self.assertTrue(log_path.exists())
            events = [
                json.loads(line)
                for line in log_path.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(
                [e["event"] for e in events],
                ["run_start", "story_annotated", "run_end"],
            )
