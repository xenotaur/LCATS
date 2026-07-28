# lcats/lcats/utils/env.py
import os
import pathlib


def cache_root() -> pathlib.Path:
    """
    Root directory for all LCATS caches.

    Override with LCATS_CACHE_DIR. Defaults to 'cache' relative to the current
    working directory (typically the lcats/ project directory).
    """
    return pathlib.Path(os.environ.get("LCATS_CACHE_DIR", "cache"))


def cache_resources_dir() -> pathlib.Path:
    """Root directory for cached dowloaded resources."""
    return cache_root() / "resources"


def corpora_root() -> pathlib.Path:
    """
    Root directory for corpora.
    Override with LCATS_CORPORA_DIR if needed.
    Defaults to '../corpora' relative to current working directory.
    """
    return pathlib.Path(os.environ.get("LCATS_CORPORA_DIR", "../corpora"))


def data_root() -> pathlib.Path:
    """
    Root directory for data files.
    Override with LCATS_DATA_DIR if needed.
    Defaults to 'data' relative to current working directory.
    """
    return pathlib.Path(os.environ.get("LCATS_DATA_DIR", "data"))
