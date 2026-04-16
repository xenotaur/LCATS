"""Corpus file discovery helpers."""

import os
import pathlib
import sys
import typing

from typing import Iterable, Iterator, Union


def find_corpus_stories(
    root: Union[str, pathlib.Path],
    *,
    ignore_dir_names: Iterable[str] = ("cache",),
    follow_symlinks: bool = False,
    ignore_hidden: bool = False,
    sort: bool = True,
) -> list[pathlib.Path]:
    """Recursively list all JSON files under root."""
    root_path = pathlib.Path(root).expanduser()
    if not root_path.exists():
        raise FileNotFoundError(f"Root path not found: {root_path}")
    if not root_path.is_dir():
        raise NotADirectoryError(f"Root is not a directory: {root_path}")

    ignore_set = {name.casefold() for name in ignore_dir_names}
    results: typing.List[pathlib.Path] = []

    for dirpath, dirnames, filenames in os.walk(
        root_path, topdown=True, followlinks=follow_symlinks
    ):
        pruned = []
        for directory_name in dirnames:
            if directory_name.casefold() in ignore_set:
                continue
            if ignore_hidden and directory_name.startswith("."):
                continue
            pruned.append(directory_name)
        dirnames[:] = pruned

        for filename in filenames:
            if ignore_hidden and filename.startswith("."):
                continue
            if filename.lower().endswith(".json"):
                results.append(pathlib.Path(dirpath) / filename)

    if sort:
        results.sort()
    return results


def find_json_files(
    directories: Iterable[Union[str, pathlib.Path]],
) -> Iterator[pathlib.Path]:
    """Yield JSON files from provided paths in deterministic order."""
    for directory in directories:
        path = pathlib.Path(directory)
        if not path.exists():
            print(f"warning: directory does not exist: {directory}", file=sys.stderr)
            continue
        if path.is_file():
            if path.suffix == ".json":
                yield path
            continue
        for file_path in sorted(path.rglob("*.json")):
            if file_path.is_file():
                yield file_path
