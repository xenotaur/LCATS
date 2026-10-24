"""Bridge tests for the genre-evidence checkpoint archive tool (WI-PROMOTE-0124)."""

from __future__ import annotations

import importlib.util
import pathlib


_TEST_PATH = (
    pathlib.Path(__file__).resolve().parents[2]
    / "experiments"
    / "05_metadata_genre_prefilter"
    / "archive_checkpoints_test.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "experiment_05_archive_checkpoints_test", _TEST_PATH
)
assert _SPEC is not None and _SPEC.loader is not None
experiment_tests = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(experiment_tests)


def load_tests(loader, tests, pattern):
    del tests, pattern
    return loader.loadTestsFromModule(experiment_tests)
