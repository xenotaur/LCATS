"""Dry-run scaffold for Gutenberg metadata genre prefiltering.

This experiment is intentionally no-network and read-only by default. It
discovers LCATS story buckets, records LCATS path identity as the primary story
ID, parses Gutenberg IDs only as provenance, and reports whether a local
Gutenberg metadata cache appears ready without importing the mutating
``lcats.gettenberg.cache`` module.
"""

from __future__ import annotations

import argparse
import collections
import datetime
import json
import os
import pathlib
import re
import sqlite3
import sys

from typing import Any, Iterable

# Allow running as `python experiments/.../run_prefilter.py` from the repo root
# without requiring a prior editable install.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lcats" / "src"))

from lcats.analysis.corpus import discovery


MANIFEST_FILENAME = "manifest.jsonl"
SUMMARY_FILENAME = "summary.json"
PIPELINE_NAME = "experiments/05_metadata_genre_prefilter"
PIPELINE_VERSION = "v1"

_GUTENBERG_ID_PATTERNS = (
    re.compile(r"gutenberg\.org/cache/epub/(\d+)", re.IGNORECASE),
    re.compile(r"gutenberg\.org/ebooks/(\d+)", re.IGNORECASE),
    re.compile(r"gutenberg\.org/files/(\d+)", re.IGNORECASE),
)


def default_cache_root() -> pathlib.Path:
    """Return the configured cache root without importing mutating cache code."""
    return pathlib.Path(os.environ.get("LCATS_CACHE_DIR", "cache"))


def default_cache_db_path() -> pathlib.Path:
    """Return the expected Gutenberg SQLite path for side-effect-free preflight."""
    return default_cache_root() / "gutenbergindex.db"


def parse_gutenberg_id(url: str | None) -> int | None:
    """Extract a Project Gutenberg ID from common LCATS source URLs."""
    if not url:
        return None
    for pattern in _GUTENBERG_ID_PATTERNS:
        match = pattern.search(url)
        if match:
            return int(match.group(1))
    return None


def is_gutenberg_url(url: str | None) -> bool:
    """Return whether a URL appears to point at Project Gutenberg."""
    return bool(url and re.search(r"gutenberg\.org", url, re.IGNORECASE))


def story_id_for_path(story_path: pathlib.Path, corpus_root: pathlib.Path) -> str:
    """Return the LCATS story ID as a corpus-root-relative story bucket path."""
    story_dir = story_path.parent
    return story_dir.relative_to(corpus_root).as_posix()


def story_row(story_path: pathlib.Path, corpus_root: pathlib.Path) -> dict[str, Any]:
    """Build one manifest row from a canonical story bucket file."""
    with story_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    url = metadata.get("url")
    if not isinstance(url, str):
        url = None
    return {
        "story_id": story_id_for_path(story_path, corpus_root),
        "story_path": story_path.relative_to(corpus_root).as_posix(),
        "collection": story_path.parent.parent.name,
        "story_slug": story_path.parent.name,
        "title": payload.get("name") or metadata.get("title") or metadata.get("name"),
        "author": metadata.get("author"),
        "year": metadata.get("year"),
        "gutenberg_id": parse_gutenberg_id(url),
        "gutenberg_url": url,
    }


def cache_readiness(cache_db: pathlib.Path) -> dict[str, Any]:
    """Inspect a Gutenberg cache database without creating or modifying it."""
    status = {
        "cache_db_path": str(cache_db),
        "cache_root": str(cache_db.parent),
        "ready": False,
        "status": "missing",
        "warnings": [],
    }
    if not cache_db.exists():
        return status
    if not cache_db.is_file():
        status["status"] = "not_file"
        status["warnings"].append("Cache database path exists but is not a file.")
        return status
    if cache_db.stat().st_size == 0:
        status["status"] = "empty"
        status["warnings"].append("Cache database exists but is empty.")
        return status

    try:
        with sqlite3.connect(f"file:{cache_db}?mode=ro", uri=True) as con:
            tables = {
                row[0]
                for row in con.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
    except sqlite3.Error as exc:
        status["status"] = "unreadable"
        status["warnings"].append(f"Cache database could not be read: {exc}")
        return status

    has_books = "books" in tables
    has_subjects = bool({"subjects", "book_subjects"} & tables)
    status["ready"] = has_books and has_subjects
    status["status"] = "ready" if status["ready"] else "missing_tables"
    if not has_books:
        status["warnings"].append("Cache database is missing the books table.")
    if not has_subjects:
        status["warnings"].append(
            "Cache database is missing subjects or book_subjects table."
        )
    return status


def discover_rows(corpus_root: pathlib.Path) -> list[dict[str, Any]]:
    """Discover canonical corpus story files and build deterministic rows."""
    story_files = list(discovery.find_json_files([corpus_root]))
    story_files.sort()
    return [story_row(path, corpus_root) for path in story_files]


def repeated_gutenberg_ids(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return repeated Gutenberg-ID diagnostics, largest groups first."""
    buckets: dict[int, list[str]] = collections.defaultdict(list)
    for row in rows:
        gutenberg_id = row["gutenberg_id"]
        if gutenberg_id is not None:
            buckets[gutenberg_id].append(row["story_id"])
    repeated = [
        {
            "gutenberg_id": gutenberg_id,
            "story_count": len(story_ids),
            "story_ids": sorted(story_ids),
        }
        for gutenberg_id, story_ids in buckets.items()
        if len(story_ids) > 1
    ]
    repeated.sort(key=lambda item: (-item["story_count"], item["gutenberg_id"]))
    return repeated


def build_summary(
    rows: list[dict[str, Any]], cache_status: dict[str, Any], corpus_root: pathlib.Path
) -> dict[str, Any]:
    """Build a deterministic summary for the dry-run artifact."""
    parse_failures = [
        row["story_id"]
        for row in rows
        if row["gutenberg_id"] is None and is_gutenberg_url(row["gutenberg_url"])
    ]
    collection_counts = collections.Counter(row["collection"] for row in rows)
    return {
        "pipeline": PIPELINE_NAME,
        "pipeline_version": PIPELINE_VERSION,
        "created_at": datetime.datetime.now(datetime.timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        "dry_run": True,
        "corpus_root": str(corpus_root),
        "story_count": len(rows),
        "collection_counts": dict(sorted(collection_counts.items())),
        "gutenberg_id_parse_failure_count": len(parse_failures),
        "gutenberg_id_parse_failures": sorted(parse_failures),
        "repeated_gutenberg_ids": repeated_gutenberg_ids(rows),
        "cache": cache_status,
    }


def write_outputs(
    rows: list[dict[str, Any]], summary: dict[str, Any], output_dir: pathlib.Path
) -> dict[str, str]:
    """Write manifest and summary under the experiment-local output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / MANIFEST_FILENAME
    summary_path = output_dir / SUMMARY_FILENAME
    outputs = {"manifest": str(manifest_path), "summary": str(summary_path)}
    summary["outputs"] = outputs
    with manifest_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return outputs


def _is_relative_to(path: pathlib.Path, parent: pathlib.Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def validate_corpus_rows(
    corpus_root: pathlib.Path, rows: list[dict[str, Any]]
) -> None:
    """Reject missing, invalid, or empty corpus roots before writing artifacts."""
    if not corpus_root.exists():
        raise ValueError(f"Corpus root does not exist: {corpus_root}")
    if not corpus_root.is_dir():
        raise ValueError(f"Corpus root is not a directory: {corpus_root}")
    if not rows:
        raise ValueError(f"No story.json files discovered under corpus root: {corpus_root}")


def validate_output_dir(
    output_dir: pathlib.Path, corpus_root: pathlib.Path, cache_db: pathlib.Path
) -> None:
    """Refuse output locations that could mutate corpus or development data."""
    resolved_output = output_dir.resolve()
    protected_roots = [
        corpus_root.resolve(),
        cache_db.parent.resolve(),
        pathlib.Path("corpora").resolve(),
        pathlib.Path("data").resolve(),
        pathlib.Path("lcats/data").resolve(),
    ]
    for root in protected_roots:
        if _is_relative_to(resolved_output, root):
            raise ValueError(f"Refusing to write prefilter output under {root}")


def run(
    *,
    corpus_root: pathlib.Path,
    output_dir: pathlib.Path,
    cache_db: pathlib.Path,
) -> dict[str, Any]:
    """Run the dry-run prefilter scaffold and return the summary."""
    validate_output_dir(output_dir, corpus_root, cache_db)
    rows = discover_rows(corpus_root)
    validate_corpus_rows(corpus_root, rows)
    cache_status = cache_readiness(cache_db)
    summary = build_summary(rows, cache_status, corpus_root)
    summary["outputs"] = write_outputs(rows, summary, output_dir)
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Run the no-network/read-only scaffold. This is currently always on.",
    )
    parser.add_argument(
        "--corpus-root",
        type=pathlib.Path,
        default=pathlib.Path("corpora"),
        help="Corpus root containing LCATS collection/story buckets.",
    )
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=pathlib.Path(__file__).resolve().parent / "results",
        help="Experiment-local output directory.",
    )
    parser.add_argument(
        "--cache-db",
        type=pathlib.Path,
        default=default_cache_db_path(),
        help="Existing Gutenberg metadata SQLite DB to inspect read-only.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.dry_run:
        raise RuntimeError("Only dry-run mode is supported by this scaffold.")
    summary = run(
        corpus_root=args.corpus_root,
        output_dir=args.output,
        cache_db=args.cache_db,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
