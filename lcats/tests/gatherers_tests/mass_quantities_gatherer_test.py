"""Unit tests for LCATS using its actual package imports.

Run from the LCATS repository root:
    python -m unittest discover -s tests -p '*_test.py' -v
"""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from lcats.gatherers import downloaders, normalization, parser, registry, story_output
from lcats.gatherers.mass_quantities import storymap
from lcats.gettenberg import resources
from lcats.utils import env, names, paths, run_log

from lcats.gatherers.mass_quantities import gatherer


class CaptureOutput:
    """Capture console output without relying on another test framework."""

    def __init__(self):
        self.stdout = io.StringIO()
        self.stderr = io.StringIO()

    def readouterr(self):
        result = SimpleNamespace(
            out=self.stdout.getvalue(),
            err=self.stderr.getvalue(),
        )

        self.stdout.seek(0)
        self.stdout.truncate(0)
        self.stderr.seek(0)
        self.stderr.truncate(0)

        return result


class LCATSTestCase(unittest.TestCase):
    """Provide the same temporary-file and mock cleanup as existing LCATS tests."""

    def setUp(self):
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary_directory.cleanup)

        self.tmp_path = Path(self._temporary_directory.name)
        self.capsys = CaptureOutput()

        self._stdout_capture = contextlib.redirect_stdout(self.capsys.stdout)
        self._stderr_capture = contextlib.redirect_stderr(self.capsys.stderr)

        self._stdout_capture.__enter__()
        self.addCleanup(self._stdout_capture.__exit__, None, None, None)

        self._stderr_capture.__enter__()
        self.addCleanup(self._stderr_capture.__exit__, None, None, None)

    def patch_attribute(self, target, name, replacement):
        """Patch a real module or object, restoring it after this test."""
        patcher = patch.object(target, name, replacement)
        patcher.start()
        self.addCleanup(patcher.stop)

        return replacement


class TestMassQuantitiesGatherer(LCATSTestCase):

    def modules(self, tmp_path):
        """Mock the parser and run log while exercising the actual batch loop."""
        events = []
        logs = []

        class FakeRunLog:
            def __init__(self, *args, **kwargs):
                logs.append((args, kwargs))

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                return False

            def event(self, event, **kwargs):
                events.append((event, kwargs))

        class ResourceTransportError(Exception):
            def __init__(self, code, status=None):
                self.code = code
                self.status = status
                self.source_uri = "source://example"
                self.request_url = "https://example.test/request"
                self.final_url = "https://example.test/final"

                super().__init__(f"{code}: {status}")

        class ResourceDecodeError(Exception):
            def __init__(self, code):
                self.code = code
                super().__init__(code)

        self.patch_attribute(downloaders, "DataGatherer", Mock())
        self.patch_attribute(parser, "gather_story_result", Mock())
        self.patch_attribute(gatherer, "tqdm", lambda iterable: iterable)
        self.patch_attribute(run_log, "RunLog", FakeRunLog)
        self.patch_attribute(env, "data_root", Mock(return_value=tmp_path / "data"))
        self.patch_attribute(
            env, "corpora_root", Mock(return_value=tmp_path / "corpora")
        )
        self.patch_attribute(
            paths,
            "find_pyproject_root",
            Mock(side_effect=FileNotFoundError),
        )
        self.patch_attribute(
            resources, "ResourceTransportError", ResourceTransportError
        )
        self.patch_attribute(resources, "ResourceDecodeError", ResourceDecodeError)

        return SimpleNamespace(
            parser=parser,
            gatherer=gatherer,
            storymap=storymap,
            names=names,
            normalization=normalization,
            story_output=story_output,
            registry=registry,
            downloaders=downloaders,
            resources=resources,
            events=events,
            logs=logs,
            env=env,
            paths=paths,
            tmp_path=tmp_path,
        )

    def test_batch_result_properties(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        result = modules.gatherer.BatchResult(
            ready={1: "new.json", 2: "old.json"},
            skipped={3: "bad metadata"},
            refused={4: "cleanup refused"},
            unavailable={5: "not found"},
            reused={2: "old.json"},
        )

        self.assertEqual(result.written, {1: "new.json"})

        self.assertTrue(result.incomplete)

        self.assertIn("1 newly written", result.summary)

        self.assertIn("1 existing outputs reused", result.summary)

        self.assertIn("1 download attempts returning HTTP 404", result.summary)

    def test_empty_batch_is_complete(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        result = modules.gatherer.BatchResult({}, {}, {})

        self.assertFalse(result.incomplete)

        self.assertEqual(result.written, {})

    def test_log_directory_rejects_protected_roots(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        with self.assertRaisesRegex(ValueError, "outside data/corpora"):
            modules.gatherer._log_directory(modules.tmp_path / "data" / "sub")
        with self.assertRaisesRegex(ValueError, "outside data/corpora"):
            modules.gatherer._log_directory(modules.tmp_path / "corpora")

    def test_log_directory_accepts_unprotected_root(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        expected = (modules.tmp_path / "logs").resolve()

        self.assertEqual(modules.gatherer._log_directory(expected), expected)

    def test_batch_requires_source(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        with self.assertRaisesRegex(ValueError, "explicit GutenbergStorySource"):
            modules.gatherer.gather_batch([1], source=None)

    def test_batch_ready_skipped_reused_and_summary(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        results = {
            1: modules.parser.StoryGatherResult(1, "new.json", None, "written"),
            2: modules.parser.StoryGatherResult(2, "old.json", None, "reused"),
            3: modules.parser.StoryGatherResult(3, None, "Rejected", "skipped"),
        }
        worker = Mock(side_effect=lambda gatherer, story, source: results[story])
        self.patch_attribute(modules.parser, "gather_story_result", worker)
        outcome = modules.gatherer.gather_batch(
            [1, 2, 3], log_dir=modules.tmp_path / "logs", source=object()
        )

        self.assertEqual(outcome.ready, {1: "new.json", 2: "old.json"})

        self.assertEqual(outcome.skipped, {3: "Rejected"})

        self.assertEqual(outcome.reused, {2: "old.json"})

        self.assertEqual(outcome.written, {1: "new.json"})

        self.assertFalse(outcome.incomplete)

        self.assertTrue(any((event == "batch_summary" for event, _ in modules.events)))

        self.assertEqual(modules.logs[0][1]["story_count"], 3)

    def test_batch_generator_has_unknown_story_count(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        self.patch_attribute(
            modules.parser,
            "gather_story_result",
            Mock(
                return_value=modules.parser.StoryGatherResult(
                    1, "one.json", None, "written"
                )
            ),
        )
        outcome = modules.gatherer.gather_batch(
            (number for number in [1]),
            log_dir=modules.tmp_path / "logs",
            source=object(),
        )

        self.assertEqual(outcome.ready, {1: "one.json"})

        self.assertIs(modules.logs[0][1]["story_count"], None)

    def test_batch_404_continues(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)

        def worker(gatherer, story, *, source):
            if story == 1:
                raise modules.resources.ResourceTransportError(
                    "http_status", status=404
                )
            return modules.parser.StoryGatherResult(story, "two.json", None, "written")

        self.patch_attribute(modules.parser, "gather_story_result", worker)
        outcome = modules.gatherer.gather_batch(
            [1, 2], log_dir=modules.tmp_path / "logs", source=object()
        )

        self.assertIn(1, outcome.unavailable)

        self.assertEqual(outcome.ready, {2: "two.json"})

        self.assertEqual(outcome.http_404_attempts, 1)

        self.assertTrue(outcome.incomplete)

        self.assertTrue(
            any((event == "story_source_unavailable" for event, _ in modules.events))
        )

    def test_batch_cleanup_refusal_continues(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)

        def worker(gatherer, story, *, source):
            if story == 1:
                raise modules.resources.ResourceDecodeError("cleanup_refused")
            return modules.parser.StoryGatherResult(story, "two.json", None, "written")

        self.patch_attribute(modules.parser, "gather_story_result", worker)
        outcome = modules.gatherer.gather_batch(
            [1, 2], log_dir=modules.tmp_path / "logs", source=object()
        )

        self.assertIn(1, outcome.refused)

        self.assertEqual(outcome.ready, {2: "two.json"})

        self.assertTrue(outcome.incomplete)

    def test_batch_non_404_error_propagates(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        self.patch_attribute(
            modules.parser,
            "gather_story_result",
            Mock(
                side_effect=modules.resources.ResourceTransportError(
                    "http_status", status=500
                )
            ),
        )
        with self.assertRaises(modules.resources.ResourceTransportError):
            modules.gatherer.gather_batch(
                [1], log_dir=modules.tmp_path / "logs", source=object()
            )

    def test_batch_non_refusal_decode_error_propagates(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        self.patch_attribute(
            modules.parser,
            "gather_story_result",
            Mock(side_effect=modules.resources.ResourceDecodeError("bad_encoding")),
        )
        with self.assertRaises(modules.resources.ResourceDecodeError):
            modules.gatherer.gather_batch(
                [1], log_dir=modules.tmp_path / "logs", source=object()
            )

    def test_repeated_id_written_then_reused_stays_written(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        results = iter(
            [
                modules.parser.StoryGatherResult(1, "one.json", None, "written"),
                modules.parser.StoryGatherResult(1, "one.json", None, "reused"),
            ]
        )
        self.patch_attribute(
            modules.parser,
            "gather_story_result",
            Mock(side_effect=lambda gatherer, story, source: next(results)),
        )
        outcome = modules.gatherer.gather_batch(
            [1, 1], log_dir=modules.tmp_path / "logs", source=object()
        )

        self.assertEqual(outcome.written, {1: "one.json"})

        self.assertEqual(outcome.reused, {})

    def test_gather_uses_configured_story_ids(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        worker = Mock(return_value="result")
        self.patch_attribute(modules.gatherer, "gather_batch", worker)
        result = modules.gatherer.gather(source="source")

        self.assertEqual(result, "result")
        worker.assert_called_once_with(modules.storymap.SINGLE_STORIES, source="source")

    def test_gather_stories_combines_failure_categories(self):
        tmp_path = self.tmp_path
        modules = self.modules(tmp_path)
        result = modules.gatherer.BatchResult(
            ready={1: "one.json"},
            skipped={2: "skip"},
            refused={3: "refuse"},
            unavailable={4: "missing"},
        )
        self.patch_attribute(
            modules.gatherer, "gather_batch", Mock(return_value=result)
        )
        ready, errors = modules.gatherer.gather_stories([1, 2, 3, 4], source="source")

        self.assertEqual(ready, {1: "one.json"})

        self.assertEqual(errors, {2: "skip", 3: "refuse", 4: "missing"})


if __name__ == "__main__":
    unittest.main()
