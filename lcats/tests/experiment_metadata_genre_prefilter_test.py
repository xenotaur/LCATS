"""Bridge tests for the top-level metadata genre prefilter experiment."""

from __future__ import annotations

import importlib.util
import pathlib


_TEST_PATH = (
    pathlib.Path(__file__).resolve().parents[2]
    / "experiments"
    / "05_metadata_genre_prefilter"
    / "run_prefilter_test.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "experiment_05_metadata_genre_prefilter_test", _TEST_PATH
)
assert _SPEC is not None and _SPEC.loader is not None
experiment_tests = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(experiment_tests)


def load_tests(loader, tests, pattern):
    del tests, pattern
    return loader.loadTestsFromModule(experiment_tests)
