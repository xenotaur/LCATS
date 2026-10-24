"""Narrow candidate integration safeguards, without editorial review policy."""

import contextlib
import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock

from lcats.gatherers.mass_quantities import gatherer
from lcats.gettenberg import resources
from lcats.utils import capture


class NarrowIntegrationTests(unittest.TestCase):
    def test_installed_runtime_log_roots_and_symlink_alias_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary).resolve()
            data, corpus = root / "data", root / "released"
            data.mkdir()
            corpus.mkdir()
            alias = root / "alias"
            alias.symlink_to(data, target_is_directory=True)
            with mock.patch.dict(
                os.environ, LCATS_DATA_DIR=str(data), LCATS_CORPORA_DIR=str(corpus)
            ):
                for forbidden in (data, data / "nested", corpus / "log", alias / "log"):
                    with self.subTest(path=forbidden):
                        with self.assertRaisesRegex(ValueError, "outside data/corpora"):
                            gatherer.gather_stories(
                                [], log_dir=forbidden, source=object()
                            )
                self.assertEqual(list(data.iterdir()), [])
                self.assertEqual(list(corpus.iterdir()), [])

    def test_cleanup_refusal_is_distinct_and_returns_incomplete_result(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary).resolve()
            log = root / "log"
            error = resources.ResourceDecodeError(
                "cleanup_refused", "ambiguous envelope"
            )
            with (
                contextlib.chdir(root),
                mock.patch.dict(
                    os.environ,
                    LCATS_DATA_DIR=str(root / "data"),
                    LCATS_CORPORA_DIR=str(root / "corpora"),
                ),
            ):
                # The boundary raises the public source exception; real batch and
                # RunLog code must retain the refusal instead of reporting success.
                with (
                    mock.patch.object(
                        gatherer.parser, "gather_story", side_effect=error
                    ),
                    capture.capture_output(),
                ):
                    result = gatherer.gather_batch([84], log_dir=log, source=object())
                    self.assertEqual(set(result.refused), {84})
                    self.assertEqual(result.ready, {})
                    self.assertEqual(result.skipped, {})
            rows = [
                json.loads(line)
                for line in (log / gatherer.GATHER_LOG_FILENAME)
                .read_text()
                .splitlines()
            ]
            refusal = next(
                row for row in rows if row["event"] == "story_cleanup_refused"
            )
            self.assertEqual(refusal["story"], 84)
            self.assertIn("cleanup_refused", refusal["reason"])
            self.assertEqual(rows[-1]["event"], "run_end")
            self.assertTrue(rows[-2]["incomplete"])
            self.assertFalse(any(row["event"] == "story_ready" for row in rows))
