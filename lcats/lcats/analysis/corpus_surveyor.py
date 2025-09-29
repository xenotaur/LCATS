"""Survey and analyze a corpus of JSON story files."""

import ast
from datetime import datetime
import json
import os
import pathlib
import re
import sys
import typing

from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Union

import pandas as pd
from tqdm import tqdm

from lcats.analysis import story_analysis


def find_corpus_stories(
    root: Union[str, pathlib.Path],
    *,
    ignore_dir_names: Iterable[str] = ("cache",),
    follow_symlinks: bool = False,
    ignore_hidden: bool = False,
    sort: bool = True,
) -> List[pathlib.Path]:
    """
    Recursively list all .json files under `root`, pruning directories
    whose *name* is in `ignore_dir_names` (e.g., 'cache') anywhere in the tree.

    Args:
        root: Corpus root directory (string or Path).
        ignore_dir_names: Directory names to prune (case-insensitive).
        follow_symlinks: Whether to descend into symlinked directories.
        ignore_hidden: If True, skip dot-directories and dot-files.
        sort: If True, return paths in sorted order (stable/deterministic).

    Returns:
        A list of pathlib.Path objects for all discovered JSON files.

    Raises:
        FileNotFoundError: if `root` does not exist.
        NotADirectoryError: if `root` is not a directory.
    """
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
        # Prune ignored / hidden directories in-place so os.walk won't descend into them.
        pruned = []
        for d in dirnames:
            if d.casefold() in ignore_set:
                continue
            if ignore_hidden and d.startswith("."):
                continue
            pruned.append(d)
        dirnames[:] = pruned

        # Collect JSON files (optionally skipping hidden files).
        for fname in filenames:
            if ignore_hidden and fname.startswith("."):
                continue
            if fname.lower().endswith(".json"):
                results.append(pathlib.Path(dirpath) / fname)

    if sort:
        results.sort()
    return results


def compute_corpus_stats(
    json_paths: Iterable[Union[str, pathlib.Path]],
    *,
    dedupe: bool = True,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Given an iterable of JSON file paths, produce:
      - story_stats: one row per unique story
      - author_stats: one row per author, aggregated across their stories

    Uniqueness key (if dedupe=True): (normalized_title, tuple(sorted(lowercased_authors)))

    Columns in story_stats:
        path, story_id, title, authors, n_authors,
        title_words, title_chars, title_tokens,
        body_words, body_chars, body_tokens

    Columns in author_stats:
        author, stories, body_words, body_chars, body_tokens
    """
    enc = story_analysis.get_encoder()
    seen_keys = set()

    story_rows: List[Dict[str, Any]] = []

    for p in tqdm(json_paths):
        path = pathlib.Path(p)
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"warn: skipping unreadable JSON {path}: {e}", file=sys.stderr)
            continue

        title, authors, body = story_analysis.extract_title_authors_body(data)

        # Uniqueness key
        key = (story_analysis.normalize_title(title), tuple(sorted(a.lower() for a in authors)))
        if dedupe and key in seen_keys:
            continue
        seen_keys.add(key)

        # Metrics
        title_chars = len(title)
        title_words = story_analysis.word_count(title)
        title_tokens = story_analysis.token_count(title, enc)

        body_chars = len(body)
        body_words = story_analysis.word_count(body)
        body_tokens = story_analysis.token_count(body, enc)

        story_rows.append(
            {
                "path": str(path),
                "story_id": f"{key[0]}::{';'.join(key[1])}" if key[1] else key[0],
                "title": title,
                "authors": authors,
                "n_authors": len(authors),

                "title_words": title_words,
                "title_chars": title_chars,
                "title_tokens": title_tokens,

                "body_words": body_words,
                "body_chars": body_chars,
                "body_tokens": body_tokens,
            }
        )

    story_stats = pd.DataFrame(story_rows)

    if story_stats.empty:
        # Return empty frames with expected columns
        story_cols = [
            "path","story_id","title","authors","n_authors",
            "title_words","title_chars","title_tokens",
            "body_words","body_chars","body_tokens",
        ]
        author_cols = ["author","stories","body_words","body_chars","body_tokens"]
        return pd.DataFrame(columns=story_cols), pd.DataFrame(columns=author_cols)

    # Build author_stats by exploding authors and aggregating body metrics.
    # (We aggregate body metrics, as requested; titles are usually small and not counted here.)
    exploded = story_stats.explode("authors", ignore_index=True)
    exploded["authors"] = exploded["authors"].fillna("")

    # Drop rows with no author string (optional; comment out to keep)
    exploded = exploded[exploded["authors"].str.len() > 0].copy()

    grp = exploded.groupby("authors", as_index=False).agg(
        stories=("story_id", "nunique"),
        body_words=("body_words", "sum"),
        body_chars=("body_chars", "sum"),
        body_tokens=("body_tokens", "sum"),
    )
    grp = grp.rename(columns={"authors": "author"}).sort_values(
        ["stories", "body_words"], ascending=[False, False]
    )

    author_stats = grp.reset_index(drop=True)

    return story_stats, author_stats


def process_corpora(
    corpora_root: Union[str, pathlib.Path],
    output_root: Union[str, pathlib.Path],
    processor_function: Callable[[Any], Any],
    *,
    job_label: Optional[str] = None,
    force: bool = False,
    ignore_dir_names: Iterable[str] = ("cache",),
    follow_symlinks: bool = False,
    ignore_hidden: bool = False,
    sort: bool = True,
    encoding: str = "utf-8",
    indent: int = 2,
    verbose: bool = False,
) -> Dict[str, Any]:
    """Process corpus JSON files into a mirrored output directory tree.

    Discovers all JSON files under `corpora_root` (using find_corpus_stories),
    computes an output path that preserves the same relative structure beneath
    `output_root/<job_dir>`, and for each file:
      - if the output does not exist (or `force=True`), loads the input JSON,
        calls `processor_function(data)`, and writes the returned JSON to the
        output path;
      - otherwise, skips processing.

    The job directory is `output_root/job_<YYYY_MM_DD_HH_MM_SS>` if `job_label`
    is not provided. If provided, `job_label` is sanitized to a safe path
    component and used as `output_root/<job_label>`.

    Args:
        corpora_root: Root directory of the corpus to scan.
        output_root: Root directory under which the job directory is created.
        processor_function: Callable that accepts an input JSON object and
            returns a JSON-serializable object to be written.
        job_label: Optional label for the job directory. If None, a timestamped
            label is generated.
        force: Recompute and overwrite outputs even if output files exist.
        ignore_dir_names: Directory names to prune during discovery (case-insensitive).
        follow_symlinks: Whether to descend into symlinked directories.
        ignore_hidden: If True, skip dot-dirs and dot-files during discovery.
        sort: If True, process files in sorted order (stable/deterministic).
        encoding: Text encoding used to read/write JSON.
        indent: Indentation level for pretty JSON output.
        verbose: If True, print per-file status lines.

    Returns:
        A dict with:
            {
              "job_dir": pathlib.Path,
              "total": int,
              "processed": int,
              "skipped": int,
              "errors": List[Dict[str, Any]],
              "results": List[Dict[str, Any]]
            }

        Each entry in "results" has:
            {
              "input": pathlib.Path,
              "output": pathlib.Path,
              "status": "processed" | "skipped" | "error",
              "error": Optional[str]
            }

    Raises:
        FileNotFoundError: If `corpora_root` does not exist.
        NotADirectoryError: If `corpora_root` is not a directory.
    """
    corpora_root_path = pathlib.Path(corpora_root).expanduser().resolve()
    output_root_path = pathlib.Path(output_root).expanduser().resolve()

    # Validate corpus root; find_corpus_stories will also sanity-check.
    if not corpora_root_path.exists():
        raise FileNotFoundError(f"Root path not found: {corpora_root_path}")
    if not corpora_root_path.is_dir():
        raise NotADirectoryError(f"Root is not a directory: {corpora_root_path}")

    # Compute/sanitize job directory name.
    if job_label:
        # Keep alnum, dash, underscore; collapse spaces to underscore.
        safe = re.sub(r"\s+", "_", job_label.strip())
        safe = re.sub(r"[^A-Za-z0-9._-]", "_", safe)
        job_dir = output_root_path / safe
    else:
        stamp = datetime.now().strftime("job_%Y_%m_%d_%H_%M_%S")
        job_dir = output_root_path / stamp

    # Ensure job directory exists.
    job_dir.mkdir(parents=True, exist_ok=True)

    # Discover input files.
    inputs = find_corpus_stories(
        corpora_root_path,
        ignore_dir_names=ignore_dir_names,
        follow_symlinks=follow_symlinks,
        ignore_hidden=ignore_hidden,
        sort=sort,
    )

    processed = 0
    skipped = 0
    errors: List[Dict[str, Any]] = []
    results: List[Dict[str, Any]] = []

    for in_path in inputs:
        # Compute path relative to corpus root, mirror under job_dir.
        try:
            rel = in_path.resolve().relative_to(corpora_root_path)
        except ValueError:
            # Should not happen if discovery was rooted correctly; fallback.
            rel = in_path.name

        out_path = job_dir / rel
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if out_path.exists() and not force:
            skipped += 1
            results.append({
                "input": in_path,
                "output": out_path,
                "status": "skipped",
                "error": None,
            })
            if verbose:
                print(f"SKIP  {rel}")
            continue

        # Process one file.
        try:
            with in_path.open("r", encoding=encoding) as f:
                data = json.load(f)

            transformed = processor_function(data)

            with out_path.open("w", encoding=encoding, newline="\n") as f:
                json.dump(transformed, f, ensure_ascii=False, indent=indent)
                f.write("\n")

            processed += 1
            results.append({
                "input": in_path,
                "output": out_path,
                "status": "processed",
                "error": None,
            })
            if verbose:
                print(f"OK    {rel} -> {out_path.relative_to(job_dir)}")

        except Exception as exc:  # noqa: BLE001
            err_msg = f"{type(exc).__name__}: {exc}"
            errors.append({
                "input": str(in_path),
                "output": str(out_path),
                "error": err_msg,
            })
            results.append({
                "input": in_path,
                "output": out_path,
                "status": "error",
                "error": err_msg,
            })
            if verbose:
                print(f"ERROR {rel} :: {err_msg}")

    return {
        "job_dir": job_dir,
        "total": len(inputs),
        "processed": processed,
        "skipped": skipped,
        "errors": errors,
        "results": results,
    }


