"""Unit tests for lcats.analysis.corpus.processing."""

import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch

from lcats.analysis.corpus import processing

_REAL_RESOLVE = pathlib.Path.resolve


def _write_json(path: pathlib.Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _identity_processor(data):
    return data


class TestProcessFileResolveGuard(unittest.TestCase):
    """process_file must not crash on a resolve() failure -- it must
    return its normal status="error" result shape instead (WI-PROCESSING-0057)."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.root = pathlib.Path(self.tmpdir.name)
        self.corpora_root = self.root / "corpora"
        self.output_root = self.root / "output"
        self.input_path = self.corpora_root / "fantasy" / "story1" / "story.json"
        _write_json(self.input_path, {"name": "story1", "body": "text"})

    @patch("pathlib.Path.resolve", side_effect=OSError("permission denied"))
    def test_returns_error_status_on_oserror(self, _mock_resolve):
        result = processing.process_file(
            self.input_path,
            corpora_root=self.corpora_root,
            job_dir=self.output_root,
            processor_function=_identity_processor,
        )
        self.assertEqual(result["status"], "error")
        self.assertIsNone(result["output"])
        self.assertIn("OSError", result["error"])

    @patch("pathlib.Path.resolve", side_effect=RuntimeError("symlink loop"))
    def test_returns_error_status_on_runtimeerror(self, _mock_resolve):
        result = processing.process_file(
            self.input_path,
            corpora_root=self.corpora_root,
            job_dir=self.output_root,
            processor_function=_identity_processor,
        )
        self.assertEqual(result["status"], "error")
        self.assertIsNone(result["output"])
        self.assertIn("RuntimeError", result["error"])

    @patch("pathlib.Path.resolve", side_effect=OSError("permission denied"))
    def test_error_result_input_is_expanded_not_raw(self, _mock_resolve):
        """Regression test (Copilot review, PR #262): the error result's
        "input" field must be the expanded (~-substituted) path, matching
        every other code path in this function, not the raw unexpanded
        in_path argument -- expanduser() can't fail, so it must always
        run before the guarded resolve() calls, not be skipped on error."""
        result = processing.process_file(
            "~/story.json",
            corpora_root=self.corpora_root,
            job_dir=self.output_root,
            processor_function=_identity_processor,
        )
        self.assertEqual(result["status"], "error")
        self.assertNotIn("~", str(result["input"]))
        self.assertEqual(result["input"], pathlib.Path("~/story.json").expanduser())

    def test_normal_processing_unaffected(self):
        """Sanity check: the guard doesn't break the real success path."""
        result = processing.process_file(
            self.input_path,
            corpora_root=self.corpora_root,
            job_dir=self.output_root,
            processor_function=_identity_processor,
        )
        self.assertEqual(result["status"], "processed")


class TestProcessFilesBatchFaultIsolation(unittest.TestCase):
    """process_files must not let one file's unresolvable path abort the
    whole batch before the per-file loop starts (WI-PROCESSING-0057)."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.root = pathlib.Path(self.tmpdir.name)
        self.corpora_root = self.root / "corpora"
        self.output_root = self.root / "output"

    def test_one_unresolvable_file_does_not_block_the_others(self):
        good1 = self.corpora_root / "fantasy" / "story1" / "story.json"
        good2 = self.corpora_root / "fantasy" / "story2" / "story.json"
        bad = self.corpora_root / "fantasy" / "bad_story" / "story.json"
        _write_json(good1, {"name": "story1", "body": "text"})
        _write_json(good2, {"name": "story2", "body": "text"})
        _write_json(bad, {"name": "bad_story", "body": "text"})

        def _resolve_side_effect(self_path, *args, **kwargs):
            if "bad_story" in str(self_path):
                raise OSError("permission denied")
            return _REAL_RESOLVE(self_path, *args, **kwargs)

        with patch(
            "pathlib.Path.resolve", autospec=True, side_effect=_resolve_side_effect
        ):
            result = processing.process_files(
                [good1, good2, bad],
                corpora_root=self.corpora_root,
                output_root=self.output_root,
                processor_function=_identity_processor,
                verbose=False,
            )

        self.assertEqual(result["processed"], 2)
        self.assertEqual(len(result["errors"]), 1)
        self.assertIn("bad_story", result["errors"][0]["input"])

    def test_all_files_process_successfully_without_mocking(self):
        """Sanity check: normal batch processing is unaffected by the
        expanduser()-only normalization change."""
        good1 = self.corpora_root / "fantasy" / "story1" / "story.json"
        good2 = self.corpora_root / "fantasy" / "story2" / "story.json"
        _write_json(good1, {"name": "story1", "body": "text"})
        _write_json(good2, {"name": "story2", "body": "text"})

        result = processing.process_files(
            [good1, good2],
            corpora_root=self.corpora_root,
            output_root=self.output_root,
            processor_function=_identity_processor,
        )

        self.assertEqual(result["processed"], 2)
        self.assertEqual(result["errors"], [])


if __name__ == "__main__":
    unittest.main()
