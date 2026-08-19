"""Read-only Gutenberg metadata genre prefilter pilot.

This experiment is intentionally no-network and read-only by default. It
discovers LCATS story buckets, records LCATS path identity as the primary story
ID, parses Gutenberg IDs only as provenance, and can enrich rows with
Gutenberg subject metadata from an explicitly supplied existing SQLite cache.
It writes experiment-local candidate and pilot manifest artifacts only.
"""

from __future__ import annotations

import argparse
import ast
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
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "lcats" / "src"))

from lcats.analysis.corpus import discovery  # noqa: E402


CANDIDATES_FILENAME = "candidates.jsonl"
PILOT_FILENAME = "pilot_40_manifest.jsonl"
SUMMARY_FILENAME = "summary.json"
PIPELINE_NAME = "experiments/05_metadata_genre_prefilter"
PIPELINE_VERSION = "v2"
ASSESSMENT_METHOD = "gutenberg_subject_rules"
ASSESSMENT_METHOD_VERSION = "v1"
ASSESSMENT_LABEL = "gutenberg_metadata_rules"
ASSESSMENT_SCOPE = "gutenberg_volume"
TARGET_GENRES = (
    "science fiction",
    "horror",
    "humor",
    "western",
    "romance",
    "mystery",
    "fantasy",
    "adventure",
)
TARGET_LABELS = {
    "SF": "science fiction",
    "Fantasy": "fantasy",
    "Horror": "horror",
    "Mystery": "mystery",
    "Western": "western",
    "Adventure": "adventure",
    "Romance": "romance",
    "Humor / satire": "humor",
}
SUGGESTIVE_LABELS = {"Crime": "mystery"}
PILOT_GROUPS = {
    "lovecraft": {"lovecraft"},
    "sherlock": {"sherlock"},
    "ohenry": {"ohenry-four_million", "ohenry-whirligigs"},
    "mass_quantities": {"mass_quantities"},
}
DEFAULT_PILOT_TARGET_PER_GROUP = 10

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


def load_genre_rules() -> list[tuple[str, list[str]]]:
    """Load GENRE_RULES from source without importing lcats.utils.genre."""
    genre_path = _REPO_ROOT / "lcats" / "src" / "lcats" / "utils" / "genre.py"
    tree = ast.parse(genre_path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "GENRE_RULES":
                    rules = ast.literal_eval(node.value)
                    return [(str(label), list(patterns)) for label, patterns in rules]
    raise RuntimeError(f"GENRE_RULES not found in {genre_path}")


GENRE_RULES = load_genre_rules()


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
    """Build one candidate row from a canonical story bucket file."""
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


def cache_readiness(cache_db: pathlib.Path | None) -> dict[str, Any]:
    """Inspect a Gutenberg cache database without creating or modifying it."""
    if cache_db is None:
        return {
            "cache_db_path": None,
            "cache_root": None,
            "ready": False,
            "status": "not_supplied",
            "warnings": ["No --cache-db supplied; metadata subjects were not read."],
        }
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
            tables = table_names(con)
            has_books = "books" in tables
            has_subjects = has_supported_subject_schema(con, tables)
    except sqlite3.Error as exc:
        status["status"] = "unreadable"
        status["warnings"].append(f"Cache database could not be read: {exc}")
        return status

    status["ready"] = has_books and has_subjects
    status["status"] = "ready" if status["ready"] else "missing_tables"
    if not has_books:
        status["warnings"].append("Cache database is missing the books table.")
    if not has_subjects:
        status["warnings"].append(
            "Cache database is missing a supported subjects schema."
        )
    return status


def table_names(con: sqlite3.Connection) -> set[str]:
    """Return table names present in a SQLite database."""
    return {
        row[0]
        for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }


def column_names(con: sqlite3.Connection, table_name: str) -> set[str]:
    """Return column names for a SQLite table."""
    return {row[1] for row in con.execute(f"PRAGMA table_info({table_name})")}


def has_normalized_subject_schema(tables: set[str]) -> bool:
    """Return whether gutenbergpy's normalized subject tables are present."""
    return {"subjects", "book_subjects"}.issubset(tables)


def has_flat_subject_schema(tables: set[str]) -> bool:
    """Return whether a simple fixture-style subject table is present."""
    return "subjects" in tables


def has_supported_subject_schema(con: sqlite3.Connection, tables: set[str]) -> bool:
    """Return whether the database has a subject schema this runner can read."""
    if "subjects" not in tables:
        return False
    subject_columns = column_names(con, "subjects")
    if has_normalized_subject_schema(tables):
        book_columns = column_names(con, "books") if "books" in tables else set()
        join_columns = column_names(con, "book_subjects")
        return (
            {"id", "gutenbergbookid"}.issubset(book_columns)
            and {
                "id",
                "name",
            }.issubset(subject_columns)
            and {"bookid", "subjectid"}.issubset(join_columns)
        )
    return has_flat_subject_schema(tables) and {"bookid", "subject"}.issubset(
        subject_columns
    )


def read_subjects_from_cache(
    cache_db: pathlib.Path,
    book_id: int | None,
    *,
    cache_ready: bool,
) -> list[str]:
    """Read Gutenberg subjects for one ID from an existing cache in read-only mode."""
    if book_id is None:
        return []
    if not cache_ready:
        return []
    with sqlite3.connect(f"file:{cache_db}?mode=ro", uri=True) as con:
        tables = table_names(con)
        book_columns = column_names(con, "books")
        subject_columns = column_names(con, "subjects")
        if (
            has_normalized_subject_schema(tables)
            and {"id", "gutenbergbookid"}.issubset(book_columns)
            and {"id", "name"}.issubset(subject_columns)
        ):
            rows = con.execute(
                """
                SELECT s.name AS subject
                FROM subjects s
                JOIN book_subjects bs ON s.id = bs.subjectid
                JOIN books b ON bs.bookid = b.id
                WHERE b.gutenbergbookid = ?
                ORDER BY s.name
                """,
                (int(book_id),),
            ).fetchall()
            return sorted({row[0] for row in rows if row[0]})
        if {"bookid", "subject"}.issubset(subject_columns):
            rows = con.execute(
                """
                SELECT subject
                FROM subjects
                WHERE bookid = ?
                ORDER BY subject
                """,
                (int(book_id),),
            ).fetchall()
            return sorted({row[0] for row in rows if row[0]})
    return []


def has_phrase(subjects: Iterable[str], phrase: str) -> bool:
    """Return whether phrase occurs in the joined subject metadata."""
    text = "; ".join(subjects).lower()
    pattern = r"(?<!\w)" + re.escape(phrase.lower()) + r"(?!\w)"
    return re.search(pattern, text) is not None


def rule_matches(subjects: Iterable[str]) -> list[dict[str, Any]]:
    """Return every metadata genre-rule match with pattern evidence."""
    subject_list = list(subjects)
    matches = []
    for label, patterns in GENRE_RULES:
        matched_patterns = [
            pattern for pattern in patterns if has_phrase(subject_list, pattern)
        ]
        if matched_patterns:
            matches.append(
                {
                    "label": label,
                    "patterns": matched_patterns,
                }
            )
    return matches


def normalize_matches(matches: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Normalize metadata labels into target candidates and secondary evidence."""
    target_candidates = []
    secondary_signals = []
    suggestive_targets = []
    seen_targets = set()
    seen_suggestive = set()
    for match in matches:
        label = match["label"]
        if label in TARGET_LABELS:
            target = TARGET_LABELS[label]
            if target not in seen_targets:
                target_candidates.append(target)
                seen_targets.add(target)
        elif label in SUGGESTIVE_LABELS:
            target = SUGGESTIVE_LABELS[label]
            if target not in seen_suggestive:
                suggestive_targets.append(target)
                seen_suggestive.add(target)
            secondary_signals.append(label)
        else:
            secondary_signals.append(label)
    return {
        "target_candidates": target_candidates,
        "suggestive_target_candidates": suggestive_targets,
        "secondary_signals": secondary_signals,
    }


def build_metadata_assessment(
    row: dict[str, Any],
    subjects: list[str],
    matches: list[dict[str, Any]],
    normalized: dict[str, Any],
    generated_at: str,
    cache_status: dict[str, Any],
) -> dict[str, Any]:
    """Build an append-only assessment-shaped metadata evidence object."""
    return {
        "assessment_id": (
            f"{ASSESSMENT_LABEL}:"
            f"{row['story_id'].replace('/', '__')}:{generated_at}"
        ),
        "label": ASSESSMENT_LABEL,
        "generated_at": generated_at,
        "scope": ASSESSMENT_SCOPE,
        "method": {
            "name": ASSESSMENT_METHOD,
            "version": ASSESSMENT_METHOD_VERSION,
            "pipeline": PIPELINE_NAME,
            "pipeline_version": PIPELINE_VERSION,
        },
        "provenance": {
            "story_id": row["story_id"],
            "story_path": row["story_path"],
            "gutenberg_id": row["gutenberg_id"],
            "gutenberg_url": row["gutenberg_url"],
            "cache_db_path": cache_status["cache_db_path"],
            "cache_status": cache_status["status"],
        },
        "evidence": {
            "raw_subjects": subjects,
            "raw_rule_matches": matches,
        },
        "result": normalized,
    }


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


def collection_group(collection: str) -> str | None:
    """Return the pilot collection group for a collection, if any."""
    for group, collections_for_group in PILOT_GROUPS.items():
        if collection in collections_for_group:
            return group
    return None


def select_pilot_rows(
    rows: list[dict[str, Any]],
    *,
    target_per_group: int = DEFAULT_PILOT_TARGET_PER_GROUP,
    max_per_gutenberg_id: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Select a deterministic heterogeneous 40-story pilot manifest."""
    selected = []
    selected_counts = {group: 0 for group in PILOT_GROUPS}
    skipped_by_cap = collections.Counter()
    gutenberg_counts: collections.Counter[int] = collections.Counter()

    for row in rows:
        group = collection_group(row["collection"])
        if group is None or selected_counts[group] >= target_per_group:
            continue
        gutenberg_id = row["gutenberg_id"]
        if (
            max_per_gutenberg_id is not None
            and gutenberg_id is not None
            and gutenberg_counts[gutenberg_id] >= max_per_gutenberg_id
        ):
            skipped_by_cap[group] += 1
            continue
        pilot_row = dict(row)
        pilot_row["pilot_group"] = group
        selected.append(pilot_row)
        selected_counts[group] += 1
        if gutenberg_id is not None:
            gutenberg_counts[gutenberg_id] += 1

    target_counts = {group: target_per_group for group in PILOT_GROUPS}
    shortfalls = {
        group: target_counts[group] - selected_counts[group]
        for group in PILOT_GROUPS
        if selected_counts[group] < target_counts[group]
    }
    diagnostics = {
        "target_counts": target_counts,
        "selected_counts": selected_counts,
        "selected_count": len(selected),
        "shortfalls": shortfalls,
        "max_per_gutenberg_id": max_per_gutenberg_id,
        "skipped_by_gutenberg_cap": dict(sorted(skipped_by_cap.items())),
        "selected_repeated_gutenberg_ids": repeated_gutenberg_ids(selected),
    }
    return selected, diagnostics


def enrich_rows(
    rows: list[dict[str, Any]],
    cache_db: pathlib.Path | None,
    cache_status: dict[str, Any],
) -> list[dict[str, Any]]:
    """Add subjects and metadata-rule assessment evidence to candidate rows."""
    generated_at = (
        datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    )
    enriched = []
    for row in rows:
        subjects = (
            read_subjects_from_cache(
                cache_db,
                row["gutenberg_id"],
                cache_ready=cache_status["ready"],
            )
            if cache_db is not None
            else []
        )
        matches = rule_matches(subjects)
        normalized = normalize_matches(matches)
        enriched_row = dict(row)
        enriched_row["gutenberg_subjects"] = subjects
        enriched_row["metadata_assessment"] = build_metadata_assessment(
            row,
            subjects,
            matches,
            normalized,
            generated_at,
            cache_status,
        )
        enriched.append(enriched_row)
    return enriched


def build_summary(
    rows: list[dict[str, Any]],
    cache_status: dict[str, Any],
    corpus_root: pathlib.Path,
    pilot_diagnostics: dict[str, Any],
) -> dict[str, Any]:
    """Build a deterministic summary for the dry-run artifact."""
    parse_failures = [
        row["story_id"]
        for row in rows
        if row["gutenberg_id"] is None and is_gutenberg_url(row["gutenberg_url"])
    ]
    collection_counts = collections.Counter(row["collection"] for row in rows)
    target_counts = collections.Counter()
    secondary_counts = collections.Counter()
    for row in rows:
        result = row["metadata_assessment"]["result"]
        target_counts.update(result["target_candidates"])
        secondary_counts.update(result["secondary_signals"])
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
        "target_candidate_counts": dict(sorted(target_counts.items())),
        "secondary_signal_counts": dict(sorted(secondary_counts.items())),
        "gutenberg_id_parse_failure_count": len(parse_failures),
        "gutenberg_id_parse_failures": sorted(parse_failures),
        "repeated_gutenberg_ids": repeated_gutenberg_ids(rows),
        "pilot": pilot_diagnostics,
        "cache": cache_status,
    }


def write_jsonl(path: pathlib.Path, rows: Iterable[dict[str, Any]]) -> None:
    """Write rows to a deterministic JSONL artifact."""
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")


def write_outputs(
    rows: list[dict[str, Any]],
    pilot_rows: list[dict[str, Any]],
    summary: dict[str, Any],
    output_dir: pathlib.Path,
) -> dict[str, str]:
    """Write candidates, pilot manifest, and summary under output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)
    candidates_path = output_dir / CANDIDATES_FILENAME
    pilot_path = output_dir / PILOT_FILENAME
    summary_path = output_dir / SUMMARY_FILENAME
    outputs = {
        "candidates": str(candidates_path),
        "pilot_40_manifest": str(pilot_path),
        "summary": str(summary_path),
    }
    summary["outputs"] = outputs
    write_jsonl(candidates_path, rows)
    write_jsonl(pilot_path, pilot_rows)
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


def validate_corpus_rows(corpus_root: pathlib.Path, rows: list[dict[str, Any]]) -> None:
    """Reject missing, invalid, or empty corpus roots before writing artifacts."""
    if not corpus_root.exists():
        raise ValueError(f"Corpus root does not exist: {corpus_root}")
    if not corpus_root.is_dir():
        raise ValueError(f"Corpus root is not a directory: {corpus_root}")
    if not rows:
        raise ValueError(
            f"No story.json files discovered under corpus root: {corpus_root}"
        )


def validate_output_dir(
    output_dir: pathlib.Path, corpus_root: pathlib.Path, cache_db: pathlib.Path | None
) -> None:
    """Refuse output locations that could mutate corpus or development data."""
    resolved_output = output_dir.resolve()
    protected_roots = [
        corpus_root.resolve(),
        pathlib.Path("corpora").resolve(),
        pathlib.Path("data").resolve(),
        pathlib.Path("lcats/data").resolve(),
    ]
    if cache_db is not None:
        protected_roots.append(cache_db.parent.resolve())
    for root in protected_roots:
        if _is_relative_to(resolved_output, root):
            raise ValueError(f"Refusing to write prefilter output under {root}")


def run(
    *,
    corpus_root: pathlib.Path,
    output_dir: pathlib.Path,
    cache_db: pathlib.Path | None,
    max_per_gutenberg_id: int | None = None,
) -> dict[str, Any]:
    """Run the metadata genre prefilter pilot and return the summary."""
    validate_output_dir(output_dir, corpus_root, cache_db)
    rows = discover_rows(corpus_root)
    validate_corpus_rows(corpus_root, rows)
    cache_status = cache_readiness(cache_db)
    enriched_rows = enrich_rows(rows, cache_db, cache_status)
    pilot_rows, pilot_diagnostics = select_pilot_rows(
        enriched_rows,
        max_per_gutenberg_id=max_per_gutenberg_id,
    )
    summary = build_summary(
        enriched_rows,
        cache_status,
        corpus_root,
        pilot_diagnostics,
    )
    summary["outputs"] = write_outputs(enriched_rows, pilot_rows, summary, output_dir)
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Run the no-network/read-only pilot. This is currently always on.",
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
        default=None,
        help="Existing Gutenberg metadata SQLite DB to read in read-only mode.",
    )
    parser.add_argument(
        "--max-per-gutenberg-id",
        type=int,
        default=None,
        help="Optional pilot sampling cap per repeated Gutenberg volume ID.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.dry_run:
        raise RuntimeError("Only dry-run mode is supported by this experiment.")
    summary = run(
        corpus_root=args.corpus_root,
        output_dir=args.output,
        cache_db=args.cache_db,
        max_per_gutenberg_id=args.max_per_gutenberg_id,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
