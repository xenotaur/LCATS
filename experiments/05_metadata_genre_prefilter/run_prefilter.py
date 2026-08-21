"""Read-only Gutenberg metadata genre prefilter (pilot + full-corpus modes).

This experiment is intentionally no-network and read-only by default. It
discovers LCATS story buckets, records LCATS path identity as the primary story
ID, parses Gutenberg IDs only as provenance, and can enrich rows with
Gutenberg subject metadata from an explicitly supplied existing SQLite cache.
It writes experiment-local candidate and manifest artifacts only.

Three modes, mutually exclusive:
- (default) a 4-collection, 40-story pilot manifest.
- --full-scan: a full-corpus metadata scan plus a genre-balanced 100-200
  story selection. No API calls; free.
- --validate: a real, gated Claude Opus validation pass against an
  already-selected --full-scan manifest. Estimate-only unless
  --run-real-validation is also passed (WI-GENRE-0004).
"""

from __future__ import annotations

import argparse
import ast
import collections
import datetime
import hashlib
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
from lcats.analysis.corpus import genre_sidecar  # noqa: E402
from lcats.utils import checkpoint  # noqa: E402

CANDIDATES_FILENAME = "candidates.jsonl"
PILOT_FILENAME = "pilot_40_manifest.jsonl"
SUMMARY_FILENAME = "summary.json"
GENRE_BALANCED_MANIFEST_FILENAME = "genre_balanced_manifest.jsonl"
VALIDATION_RESULTS_FILENAME = "validation_results.jsonl"
VALIDATION_SUMMARY_FILENAME = "validation_summary.json"
VALIDATION_RUN_LOG_FILENAME = "validation_run_log.jsonl"
PIPELINE_NAME = "experiments/05_metadata_genre_prefilter"
PIPELINE_VERSION = "v2"

# Total selection target for the genre-balanced full-corpus sample
# (WI-GENRE-0004 acceptance: 100-200 stories). Not the same target as
# DEFAULT_PILOT_TARGET_PER_GROUP/PILOT_GROUPS below, which remain scoped to
# the existing 4-collection 40-story pilot and must not be repurposed.
DEFAULT_GENRE_BALANCED_TARGET_TOTAL = 160

MODEL_ASSESSMENT_LABEL = "model_detect"
MODEL_ASSESSMENT_METHOD = "lcats.analysis.corpus.assess.assess_story"
MODEL_ASSESSMENT_METHOD_VERSION = "v1"

# Approximate USD price per 1M tokens, as of when this was written (2026-08)
# - NOT a durable pricing source of truth. Mirrors
# experiments/04_genre_census/run_census.py's own local, script-scoped
# pricing constant rather than sharing one - see that script's Risk Notes
# on why no shared pricing module exists in this codebase
# (PROP-LCATS-PIPELINE-CHECKPOINTING's Category E1, deferred, unbuilt).
_PRICING_USD_PER_MILLION_TOKENS: dict[str, tuple[float, float]] = {
    "claude-opus-4": (15.0, 75.0),
    "claude-sonnet-4": (3.0, 15.0),
    "claude-haiku-4": (0.8, 4.0),
}
_DEFAULT_PRICING_USD_PER_MILLION_TOKENS: tuple[float, float] = (15.0, 75.0)

VALIDATION_CHECKPOINT_STAGE = "validation"
VALIDATION_FINGERPRINT_VERSION = "v1"

# Same rationale as experiments/04_genre_census/run_census.py's own
# _FATAL_ERROR_SUBSTRINGS: continuing after a bad key/exhausted quota just
# burns real money for no new information, since every remaining story
# would fail identically. Duplicated locally rather than imported - each
# experiment script here is deliberately independent (no shared module),
# same reasoning as the pricing table above.
_FATAL_ERROR_SUBSTRINGS = (
    "credit balance",
    "insufficient_quota",
    "quota",
    "api key",
    "authentication",
)


class FatalValidationError(RuntimeError):
    """Raised to abort the whole --validate run on a non-retryable,
    account-level API error - mirrors run_census.py's FatalCensusError
    and run_pilot.py's FatalPilotError."""


def _check_fatal(message: str, context: str) -> None:
    lowered = message.lower()
    if any(s in lowered for s in _FATAL_ERROR_SUBSTRINGS):
        raise FatalValidationError(f"{context}: {message}")


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


def build_model_assessment(
    row: dict[str, Any],
    assessment_result: Any,
    run_id: str,
    generated_at: str,
) -> dict[str, Any]:
    """Build a genre-sidecar-v1 model_detect assessment from an AssessmentResult.

    run_id must be unique per assessment within the sidecar it is written
    into (genre_sidecar.py's _validate_model_run_identity) - each row gets
    its own sidecar file here, so a run_id shared across one validation
    batch is safe: it is never repeated within any single row's own
    assessments[] array.
    """
    metadata_result = row["metadata_assessment"]["result"]
    detected_genre = assessment_result.detected_genre
    agreement = (
        None
        if assessment_result.error
        else detected_genre in metadata_result["target_candidates"]
    )
    return {
        "assessment_id": f"{MODEL_ASSESSMENT_LABEL}:{row['story_id'].replace('/', '__')}:{run_id}",
        "label": MODEL_ASSESSMENT_LABEL,
        "generated_at": generated_at,
        "scope": "story",
        "method": {
            "name": MODEL_ASSESSMENT_METHOD,
            "version": MODEL_ASSESSMENT_METHOD_VERSION,
        },
        "run_id": run_id,
        "provenance": {
            "story_id": row["story_id"],
            "story_path": row["story_path"],
            "run_id": run_id,
            "backend_model": assessment_result.backend_model,
            "input_tokens": assessment_result.input_tokens,
            "output_tokens": assessment_result.output_tokens,
        },
        "evidence": {
            "error": assessment_result.error,
        },
        "result": {
            "detected_genre": detected_genre,
            "detected_genre_confidence": assessment_result.detected_genre_confidence,
            "agrees_with_metadata_rules": agreement,
            "metadata_target_candidates": metadata_result["target_candidates"],
        },
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


def _primary_target_genre(row: dict[str, Any]) -> str | None:
    """Return a row's primary metadata-rule target genre, or None.

    A row with zero target_candidates has no usable metadata signal for
    genre-balanced selection - excluded, not defaulted to any genre.
    """
    candidates = row["metadata_assessment"]["result"]["target_candidates"]
    return candidates[0] if candidates else None


def select_genre_balanced_rows(
    rows: list[dict[str, Any]],
    *,
    target_total: int = DEFAULT_GENRE_BALANCED_TARGET_TOTAL,
    max_per_gutenberg_id: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Select a deterministic genre-balanced sample across all TARGET_GENRES.

    Unlike select_pilot_rows (grouped by source collection, scoped to the
    existing 4-collection 40-story pilot), this groups by each row's
    primary metadata-rule target genre and distributes target_total evenly
    across the 8 TARGET_GENRES - not corpus-proportional, since the corpus
    is heavily skewed toward a small number of collections/genres and a
    proportional sample would under-represent the smaller target genres
    the Worldcon paper needs balanced coverage of.
    """
    # Distribute target_total across TARGET_GENRES deterministically, even
    # when it doesn't divide evenly by 8 - the base//remainder split below
    # (rather than plain integer division) ensures selected_count matches
    # target_total exactly whenever enough candidates exist, instead of
    # silently under-selecting by up to 7 stories (review finding: Codex
    # P2 + Copilot, this PR - --target-total 100 previously selected only
    # 96). Remainder genres (first `remainder` in TARGET_GENRES' own fixed
    # order) get one extra story each - deterministic, not data-dependent.
    base_per_genre = target_total // len(TARGET_GENRES)
    remainder = target_total % len(TARGET_GENRES)
    target_counts = {
        genre: base_per_genre + (1 if index < remainder else 0)
        for index, genre in enumerate(TARGET_GENRES)
    }
    selected: list[dict[str, Any]] = []
    selected_counts = {genre: 0 for genre in TARGET_GENRES}
    skipped_by_cap: collections.Counter[str] = collections.Counter()
    gutenberg_counts: collections.Counter[int] = collections.Counter()
    unclassified_count = 0

    for row in rows:
        genre = _primary_target_genre(row)
        if genre is None:
            unclassified_count += 1
            continue
        if selected_counts[genre] >= target_counts[genre]:
            continue
        gutenberg_id = row["gutenberg_id"]
        if (
            max_per_gutenberg_id is not None
            and gutenberg_id is not None
            and gutenberg_counts[gutenberg_id] >= max_per_gutenberg_id
        ):
            skipped_by_cap[genre] += 1
            continue
        selected_row = dict(row)
        selected_row["selection_genre"] = genre
        selected.append(selected_row)
        selected_counts[genre] += 1
        if gutenberg_id is not None:
            gutenberg_counts[gutenberg_id] += 1

    shortfalls = {
        genre: target_counts[genre] - selected_counts[genre]
        for genre in TARGET_GENRES
        if selected_counts[genre] < target_counts[genre]
    }
    diagnostics = {
        "target_total": target_total,
        "per_genre_target": base_per_genre,
        "target_counts": target_counts,
        "selected_counts": selected_counts,
        "selected_count": len(selected),
        "shortfalls": shortfalls,
        "unclassified_count": unclassified_count,
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


def build_genre_coverage(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Report explicit per-genre candidate coverage across all 8 TARGET_GENRES.

    Distinct from target_candidate_counts (which counts every multi-label
    candidate a row matched): this counts, per genre, how many rows have
    that genre as their *primary* (first) target candidate - the same
    grouping select_genre_balanced_rows() uses for selection - plus the
    count of rows with no usable metadata signal at all (zero candidates).
    """
    primary_counts = {genre: 0 for genre in TARGET_GENRES}
    unclassified_count = 0
    for row in rows:
        genre = _primary_target_genre(row)
        if genre is None:
            unclassified_count += 1
        else:
            primary_counts[genre] += 1
    return {
        "primary_target_genre_counts": primary_counts,
        "no_usable_signal_count": unclassified_count,
    }


def build_summary(
    rows: list[dict[str, Any]],
    cache_status: dict[str, Any],
    corpus_root: pathlib.Path,
    pilot_diagnostics: dict[str, Any],
    genre_balanced_diagnostics: dict[str, Any] | None = None,
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
    summary = {
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
        "genre_coverage": build_genre_coverage(rows),
        "gutenberg_id_parse_failure_count": len(parse_failures),
        "gutenberg_id_parse_failures": sorted(parse_failures),
        "repeated_gutenberg_ids": repeated_gutenberg_ids(rows),
        "pilot": pilot_diagnostics,
        "cache": cache_status,
    }
    if genre_balanced_diagnostics is not None:
        summary["genre_balanced_selection"] = genre_balanced_diagnostics
    return summary


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


def write_genre_balanced_outputs(
    rows: list[dict[str, Any]],
    selected_rows: list[dict[str, Any]],
    summary: dict[str, Any],
    output_dir: pathlib.Path,
) -> dict[str, str]:
    """Write candidates, the genre-balanced selection manifest, and summary.

    Written BEFORE any paid model call - this is a separate, no-cost step
    from run_validation()/write_validation_outputs() below, so a human can
    review the selection and its rationale between them.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    candidates_path = output_dir / CANDIDATES_FILENAME
    manifest_path = output_dir / GENRE_BALANCED_MANIFEST_FILENAME
    summary_path = output_dir / SUMMARY_FILENAME
    outputs = {
        "candidates": str(candidates_path),
        "genre_balanced_manifest": str(manifest_path),
        "summary": str(summary_path),
    }
    summary["outputs"] = outputs
    write_jsonl(candidates_path, rows)
    write_jsonl(manifest_path, selected_rows)
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return outputs


def _price_for_model(model: str) -> tuple[float, float]:
    for prefix, price in _PRICING_USD_PER_MILLION_TOKENS.items():
        if model.startswith(prefix):
            return price
    return _DEFAULT_PRICING_USD_PER_MILLION_TOKENS


def estimate_validation_cost_usd(
    selected_count: int,
    model: str,
    avg_input_tokens: int = 13_449,
    avg_output_tokens: int = 416,
) -> float:
    """Rough pre-call cost estimate for the validation pass.

    Default per-story token averages are the real measured values from
    experiments/04_genre_census/results/census_sample_summary.json
    (WI-ASSESS-0051's 20-story claude-opus-4-8 sample: 268,975 input /
    8,310 output tokens total, i.e. 13,448.75/415.5 per story, rounded)
    rather than invented placeholders - a review finding (Codex, P1, this
    PR) caught an earlier draft understating the estimate by ~3.5x, which
    would have defeated the whole point of this being the human review
    gate before real billed calls.
    """
    input_price, output_price = _price_for_model(model)
    per_story = (avg_input_tokens / 1_000_000) * input_price + (
        avg_output_tokens / 1_000_000
    ) * output_price
    return per_story * selected_count


class _UnexpectedFailureResult:
    """Minimal AssessmentResult-shaped stand-in for build_model_assessment()
    when an unexpected (non-FatalValidationError) exception is caught -
    lets the same assessment-building/sidecar path handle this case
    uniformly rather than hand-building a differently-shaped record."""

    def __init__(self, error: str):
        self.detected_genre = "other"
        self.detected_genre_confidence = 0.0
        self.error = f"unexpected error: {error}"
        self.backend_model = ""
        self.input_tokens = 0
        self.output_tokens = 0


def _log_run_event(log_path: pathlib.Path, event: str, **fields: Any) -> None:
    """Append one timestamped JSON line to the run log, then close.

    Distinct from per-item checkpointing (which answers "is this item
    done and resume-safe?"): this answers "what actually happened, when,
    and in what order, including why the run stopped?" - a single place
    to `tail -f`/`cat` for a human, not a resume mechanism.

    Opens, writes, and closes per call rather than holding a long-lived
    handle across the whole run, so a hard interruption (kill -9, power
    loss) never loses a buffered-but-unflushed line - the exact failure
    mode this log exists to survive. The per-call open/close cost is
    negligible next to a real API call's own latency.
    """
    record = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        "event": event,
        **fields,
    }
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")


def _validation_item_id(story_id: str) -> str:
    """Checkpoint-safe item_id for a story - mirrors the collection__slug
    identity convention run_census.py's _story_identity and this file's
    own assessment_id construction already use."""
    return story_id.replace("/", "__")


def _validation_fingerprint(
    model: str, row: dict[str, Any], corpus_root: pathlib.Path
) -> dict[str, Any]:
    """Fingerprint hashes the row's own metadata-assessment content plus
    the actual story file assess_story() reads (not just model/config), so
    either a re-selected/edited manifest row or a story corrected in place
    invalidates its own cached validation - a resumed run must never
    silently describe an earlier version of the story text (review
    finding: Codex P1, this PR). Also carries a version marker so a future
    change to how validation records are built invalidates every cached
    one - same "hash actual input, not just config" principle as
    run_census.py's own _fingerprint."""
    row_hash = hashlib.sha256(
        json.dumps(row["metadata_assessment"], sort_keys=True).encode("utf-8")
    ).hexdigest()
    story_bytes = (corpus_root / row["story_path"]).read_bytes()
    story_hash = hashlib.sha256(story_bytes).hexdigest()
    return {
        "model": model,
        "validation_version": VALIDATION_FINGERPRINT_VERSION,
        "row_hash": row_hash,
        "story_content_hash": story_hash,
    }


def _rows_not_yet_checkpointed(
    selected_rows: list[dict[str, Any]],
    model: str,
    roots: checkpoint.CheckpointRoots,
    corpus_root: pathlib.Path,
) -> list[dict[str, Any]]:
    """Return the subset of selected_rows with no matching done checkpoint.

    Read-only, no API calls (reading each story file to fingerprint it is
    cheap local I/O, not a network/model call) - used both to scope the
    cost estimate to what a real run would actually spend (not the full
    sample size, which would over-report on a resume) and by
    run_validation() itself to decide, per story, whether to skip the
    real call.
    """
    remaining = []
    for row in selected_rows:
        item_id = _validation_item_id(row["story_id"])
        try:
            fingerprint = _validation_fingerprint(model, row, corpus_root)
            cached = checkpoint.read_checkpoint(
                roots.working_root, item_id, VALIDATION_CHECKPOINT_STAGE, fingerprint
            )
        except OSError:
            # Story file missing/unreadable - can't fingerprint it to check
            # for a cached result. Conservatively counted as remaining
            # work (never as already-done) rather than crashing what's
            # documented as a free, side-effect-free estimate preview
            # (review finding: Codex, this PR) - a real run surfaces the
            # same missing file as a normal, isolated per-story failure
            # instead (see run_validation()'s own OSError handling below).
            remaining.append(row)
            continue
        if not (cached.done and isinstance(cached.data, dict)):
            remaining.append(row)
    return remaining


def run_validation(
    selected_rows: list[dict[str, Any]],
    *,
    corpus_root: pathlib.Path,
    backend: Any,
    model: str,
    roots: checkpoint.CheckpointRoots,
    log_path: pathlib.Path,
) -> tuple[list[dict[str, Any]], dict[str, Any], bool]:
    """Run a real, gated Claude Opus validation pass over the selected sample.

    Never called on the full corpus - only the already-selected sample.
    Caller is responsible for the explicit-go-ahead gate; this function
    itself makes real, billed API calls unconditionally once invoked
    (except for stories already checkpointed as done - see below).

    row["story_path"] is corpus-root-relative (story_row()'s deliberate
    portable-manifest shape) - resolved back to a real path via
    corpus_root here, the same way the manifest's own reader must.

    Each story is checkpointed individually under roots.working_root
    (stage VALIDATION_CHECKPOINT_STAGE), success or failure, before
    moving to the next - mirrors run_census.py's/run_pilot.py's own
    per-item checkpoint discipline, so re-running this exact command
    after an interruption resumes rather than re-pays for already-done
    stories. Any exception other than FatalValidationError is caught
    per-story (logged, checkpointed as a failure, loop continues) rather
    than propagating out and discarding every already-completed story's
    results - this is the exact failure mode run_pilot.py's own
    _run_stories docstring documents fixing after a real incident
    (WI-EVENT-0032): an unexpected per-story exception must never cost
    more than that one story's own results.

    Returns (results, summary, aborted) - aborted is True only on a
    FatalValidationError (account-level failure); results/summary are
    still populated with whatever completed before the abort, since the
    caller must write those out regardless (never silently discard
    already-paid-for work).

    Also appends one event per story (plus a run-start and run-end event)
    to log_path via _log_run_event() - a human-readable, append-and-flush
    record of what happened and when, distinct from the per-item
    checkpoints above: checkpoints answer "is this item done and
    resume-safe?", this log answers "what happened, in order, including
    why the run stopped?" (see _log_run_event()'s own docstring).
    """
    from lcats.analysis.corpus import assess as corpus_assess

    run_id = (
        datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    )
    _log_run_event(
        log_path,
        "run_start",
        run_id=run_id,
        model=model,
        story_count=len(selected_rows),
    )
    results = []
    agreement_count = 0
    error_count = 0
    total_input_tokens = 0
    total_output_tokens = 0
    aborted = False
    total = len(selected_rows)
    for index, row in enumerate(selected_rows, start=1):
        item_id = _validation_item_id(row["story_id"])
        # fingerprint is computed inside the try block below (not here,
        # ahead of it) because it reads the story file off disk - a
        # missing/unreadable story must be isolated as this one story's
        # failure by the same except Exception branch below, not crash
        # the whole run before any per-story handling begins (review
        # finding: Codex, this PR).
        fingerprint = None
        try:
            fingerprint = _validation_fingerprint(model, row, corpus_root)
            cached = checkpoint.read_checkpoint(
                roots.working_root, item_id, VALIDATION_CHECKPOINT_STAGE, fingerprint
            )
        except OSError:
            cached = None
        if cached is not None and cached.done and isinstance(cached.data, dict):
            model_assessment = cached.data["model_assessment"]
            total_input_tokens += cached.data.get("input_tokens", 0)
            total_output_tokens += cached.data.get("output_tokens", 0)
            print(f"  [{index}/{total}] {row['story_id']} (cached)")
            _log_run_event(
                log_path,
                "story_cached",
                story_id=row["story_id"],
                index=index,
                total=total,
            )
        else:
            try:
                if fingerprint is None:
                    raise FileNotFoundError(
                        f"story file not found or unreadable: "
                        f"{corpus_root / row['story_path']}"
                    )
                generated_at = (
                    datetime.datetime.now(datetime.timezone.utc)
                    .isoformat()
                    .replace("+00:00", "Z")
                )
                assessment_result = corpus_assess.assess_story(
                    corpus_root / row["story_path"],
                    genre="",
                    backend=backend,
                    model=model,
                )
                if assessment_result.error:
                    _check_fatal(
                        assessment_result.error,
                        context=f"validation {row['story_id']}",
                    )
                model_assessment = build_model_assessment(
                    row, assessment_result, run_id, generated_at
                )
                total_input_tokens += assessment_result.input_tokens
                total_output_tokens += assessment_result.output_tokens
                checkpoint.write_checkpoint(
                    roots.working_root,
                    item_id,
                    VALIDATION_CHECKPOINT_STAGE,
                    outcome="failure" if assessment_result.error else "success",
                    fingerprint=fingerprint,
                    data={
                        "model_assessment": model_assessment,
                        "input_tokens": assessment_result.input_tokens,
                        "output_tokens": assessment_result.output_tokens,
                    },
                )
                print(
                    f"  [{index}/{total}] {row['story_id']} -> "
                    f"{model_assessment['result']['detected_genre']}"
                )
                _log_run_event(
                    log_path,
                    "story_completed",
                    story_id=row["story_id"],
                    index=index,
                    total=total,
                    detected_genre=model_assessment["result"]["detected_genre"],
                    error=model_assessment["evidence"].get("error"),
                )
            except FatalValidationError as exc:
                print(f"\nfatal: {exc}", file=sys.stderr)
                print(
                    "Aborting - this looks like a bad/expired API key or "
                    "an exhausted account balance/quota, not a per-story "
                    "problem. Every remaining story would fail "
                    "identically. Results and checkpoints gathered so "
                    "far are preserved and written out below.",
                    file=sys.stderr,
                )
                _log_run_event(
                    log_path,
                    "run_aborted_fatal",
                    story_id=row["story_id"],
                    index=index,
                    total=total,
                    error=str(exc),
                )
                aborted = True
                break
            except Exception as exc:  # noqa: BLE001 - see docstring above
                print(
                    f"  error: unexpected failure on {row['story_id']}: {exc!r}",
                    file=sys.stderr,
                )
                # fingerprint is None when the failure happened computing
                # the fingerprint itself (e.g. a missing story file) -
                # nothing to checkpoint against yet, so skip writing one;
                # the next resume simply retries this same story, same as
                # any other never-checkpointed row.
                if fingerprint is not None:
                    checkpoint.write_checkpoint(
                        roots.working_root,
                        item_id,
                        VALIDATION_CHECKPOINT_STAGE,
                        outcome="failure",
                        fingerprint=fingerprint,
                        data={"error": f"unexpected error: {exc!r}"},
                    )
                model_assessment = build_model_assessment(
                    row,
                    _UnexpectedFailureResult(str(exc)),
                    run_id,
                    datetime.datetime.now(datetime.timezone.utc)
                    .isoformat()
                    .replace("+00:00", "Z"),
                )
                _log_run_event(
                    log_path,
                    "story_unexpected_error",
                    story_id=row["story_id"],
                    index=index,
                    total=total,
                    error=repr(exc),
                )
        if model_assessment["evidence"].get("error"):
            error_count += 1
        if model_assessment["result"]["agrees_with_metadata_rules"]:
            agreement_count += 1
        results.append(
            {
                "story_id": row["story_id"],
                "story_path": row["story_path"],
                "selection_genre": row["selection_genre"],
                "metadata_assessment": row["metadata_assessment"],
                "model_assessment": model_assessment,
            }
        )

    input_price, output_price = _price_for_model(model)
    real_cost = (total_input_tokens / 1_000_000) * input_price + (
        total_output_tokens / 1_000_000
    ) * output_price
    validated_count = len(results) - error_count
    summary = {
        "run_id": run_id,
        "model": model,
        "selected_count": total,
        "processed_count": len(results),
        "aborted": aborted,
        "error_count": error_count,
        "agreement_count": agreement_count,
        "disagreement_count": max(validated_count - agreement_count, 0),
        "agreement_rate": (
            (agreement_count / validated_count) if validated_count else None
        ),
        # Per-genre breakdown, not just the aggregate above - an aggregate
        # rate can conceal one genre's poor coverage behind seven good
        # ones, exactly the gap this balanced validation exists to measure
        # (review finding: Codex P2, this PR).
        "agreement_by_genre": build_agreement_by_genre(results),
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "total_estimated_cost_usd": real_cost,
    }
    _log_run_event(
        log_path,
        "run_end",
        run_id=run_id,
        aborted=aborted,
        processed_count=len(results),
        error_count=error_count,
        agreement_count=agreement_count,
        total_estimated_cost_usd=real_cost,
    )
    return results, summary, aborted


def build_agreement_by_genre(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate validated/error/agreement/disagreement counts per selection_genre."""
    by_genre: dict[str, dict[str, Any]] = {}
    for result in results:
        genre = result["selection_genre"]
        bucket = by_genre.setdefault(
            genre,
            {"validated_count": 0, "error_count": 0, "agreement_count": 0},
        )
        agreement = result["model_assessment"]["result"]["agrees_with_metadata_rules"]
        if agreement is None:
            bucket["error_count"] += 1
        else:
            bucket["validated_count"] += 1
            if agreement:
                bucket["agreement_count"] += 1
    for genre, bucket in by_genre.items():
        validated = bucket["validated_count"]
        bucket["disagreement_count"] = max(validated - bucket["agreement_count"], 0)
        bucket["agreement_rate"] = (
            (bucket["agreement_count"] / validated) if validated else None
        )
    return dict(sorted(by_genre.items()))


def build_sidecar_records(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build one genre-sidecar-v1 record per story, validating each before return."""
    sidecars = []
    for result in results:
        sidecar = {
            "schema_version": genre_sidecar.SCHEMA_VERSION,
            "lcats_id": result["story_id"],
            "story_path": result["story_path"],
            "assessments": [
                result["metadata_assessment"],
                result["model_assessment"],
            ],
            "current_adjudication": None,
        }
        validation = genre_sidecar.validate_sidecar(sidecar)
        if not validation.valid:
            findings = "; ".join(
                f"{f.path}: {f.kind}: {f.message}"
                for f in validation.findings
                if f.severity == "error"
            )
            raise ValueError(
                f"Built an invalid genre-sidecar-v1 record for {result['story_id']!r}: "
                f"{findings}"
            )
        sidecars.append(sidecar)
    return sidecars


def write_validation_outputs(
    results: list[dict[str, Any]],
    validation_summary: dict[str, Any],
    output_dir: pathlib.Path,
) -> dict[str, str]:
    """Write per-story sidecar-shaped validation results and a summary."""
    output_dir.mkdir(parents=True, exist_ok=True)
    results_path = output_dir / VALIDATION_RESULTS_FILENAME
    summary_path = output_dir / VALIDATION_SUMMARY_FILENAME
    sidecars = build_sidecar_records(results)
    write_jsonl(results_path, sidecars)
    summary_path.write_text(
        json.dumps(validation_summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "validation_results": str(results_path),
        "validation_summary": str(summary_path),
    }


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


def run_full_scan(
    *,
    corpus_root: pathlib.Path,
    output_dir: pathlib.Path,
    cache_db: pathlib.Path | None,
    target_total: int = DEFAULT_GENRE_BALANCED_TARGET_TOTAL,
    max_per_gutenberg_id: int | None = None,
    validation_model: str = "claude-opus-4-8",
) -> dict[str, Any]:
    """Full-corpus metadata scan + genre-balanced selection. No paid calls.

    Writes the selected sample manifest and its selection rationale, plus
    a cost estimate for the separate, explicitly-gated validation step
    (run_validation(), invoked only via --validate --run-real-validation
    in a later, human-reviewed invocation).
    """
    validate_output_dir(output_dir, corpus_root, cache_db)
    rows = discover_rows(corpus_root)
    validate_corpus_rows(corpus_root, rows)
    cache_status = cache_readiness(cache_db)
    enriched_rows = enrich_rows(rows, cache_db, cache_status)
    # select_pilot_rows' own 4-collection pilot is orthogonal to full-scan
    # mode - report empty pilot diagnostics rather than reusing/repurposing it.
    empty_pilot_diagnostics = {
        "target_counts": {},
        "selected_counts": {},
        "selected_count": 0,
        "shortfalls": {},
        "max_per_gutenberg_id": None,
        "skipped_by_gutenberg_cap": {},
        "selected_repeated_gutenberg_ids": [],
    }
    selected_rows, selection_diagnostics = select_genre_balanced_rows(
        enriched_rows,
        target_total=target_total,
        max_per_gutenberg_id=max_per_gutenberg_id,
    )
    summary = build_summary(
        enriched_rows,
        cache_status,
        corpus_root,
        empty_pilot_diagnostics,
        genre_balanced_diagnostics=selection_diagnostics,
    )
    summary["estimated_validation_cost_usd"] = estimate_validation_cost_usd(
        len(selected_rows), validation_model
    )
    summary["outputs"] = write_genre_balanced_outputs(
        enriched_rows, selected_rows, summary, output_dir
    )
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
    parser.add_argument(
        "--full-scan",
        action="store_true",
        help=(
            "Run a full-corpus metadata scan and genre-balanced selection "
            "instead of the 4-collection 40-story pilot. No API calls; free."
        ),
    )
    parser.add_argument(
        "--target-total",
        type=int,
        default=DEFAULT_GENRE_BALANCED_TARGET_TOTAL,
        help="Total genre-balanced selection size for --full-scan (100-200).",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help=(
            "Estimate (or, with --run-real-validation, actually run) the "
            "Opus validation pass against an existing --full-scan manifest "
            "already written under --output. A separate invocation from "
            "--full-scan by design, so the manifest can be reviewed first."
        ),
    )
    parser.add_argument(
        "--run-real-validation",
        action="store_true",
        help=(
            "Required alongside --validate to actually spend real money. "
            "Without it, --validate only prints the cost estimate and "
            "makes no API calls - this repo's established cost-gate "
            "convention (see experiments/04_genre_census/run_census.py)."
        ),
    )
    parser.add_argument(
        "--model",
        default="claude-opus-4-8",
        help=(
            "Anthropic model used for --validate's real or estimated "
            "validation pass, and for --full-scan's own "
            "estimated_validation_cost_usd preview of that same estimate."
        ),
    )
    if "--full-scan" in (argv or sys.argv[1:]) and "--validate" in (
        argv or sys.argv[1:]
    ):
        parser.error("--full-scan and --validate are separate invocations; pass one.")
    return parser.parse_args(argv)


def _run_validate_mode(args: argparse.Namespace) -> dict[str, Any]:
    # Same guard run()/run_full_scan() apply before writing anything -
    # --validate's real mode is the one path that writes genre-sidecar-v1
    # records, so it must refuse a --output pointed at corpora/, data/,
    # lcats/data/, or the corpus root just as those other modes do.
    validate_output_dir(args.output, args.corpus_root, cache_db=None)
    manifest_path = args.output / GENRE_BALANCED_MANIFEST_FILENAME
    if not manifest_path.exists():
        raise ValueError(
            f"No genre-balanced manifest found at {manifest_path} - run "
            "--full-scan first and review its selection before --validate."
        )
    selected_rows = [
        json.loads(line)
        for line in manifest_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    # Checkpoint working_root is --output itself (already validated above,
    # never corpora/data/) - source_root is the real corpus, matching
    # run_census.py's own resolve_roots(working_root=output, source_root=
    # data_dir) call shape. Resolved (and the estimate below scoped to it)
    # regardless of --run-real-validation, since resolving is itself a
    # cheap, read-only, no-API-call operation - guarding it only on the
    # real path would leave the estimate-only path reporting a stale full
    # cost on a resume, when some stories are already checkpointed done.
    try:
        roots = checkpoint.resolve_roots(
            working_root=args.output, source_root=args.corpus_root
        )
    except (checkpoint.ProtectedRootError, RuntimeError) as exc:
        raise ValueError(f"checkpoint working_root rejected: {exc}") from exc

    remaining_rows = _rows_not_yet_checkpointed(
        selected_rows, args.model, roots, args.corpus_root
    )
    estimate = estimate_validation_cost_usd(len(remaining_rows), args.model)
    if not args.run_real_validation:
        return {
            "mode": "validate-estimate-only",
            "selected_count": len(selected_rows),
            "already_checkpointed_count": len(selected_rows) - len(remaining_rows),
            "remaining_count": len(remaining_rows),
            "model": args.model,
            "estimated_cost_usd": estimate,
            "note": (
                "No API calls made. estimated_cost_usd covers only "
                "remaining_count stories not yet checkpointed under "
                "--output - re-run with --run-real-validation to spend "
                "this amount for real."
            ),
        }

    from lcats.llm import anthropic_backend

    backend = anthropic_backend.AnthropicBackend()
    print(
        f"Validating {len(selected_rows)} stories with {args.model} "
        "(resuming from any checkpoints)."
    )
    log_path = args.output / VALIDATION_RUN_LOG_FILENAME
    results, validation_summary, aborted = run_validation(
        selected_rows,
        corpus_root=args.corpus_root,
        backend=backend,
        model=args.model,
        roots=roots,
        log_path=log_path,
    )
    # Always write whatever completed, aborted or not - never silently
    # discard already-paid-for results (see run_validation()'s own
    # docstring / run_pilot.py's WI-EVENT-0032 precedent).
    validation_summary["outputs"] = write_validation_outputs(
        results, validation_summary, args.output
    )
    validation_summary["outputs"]["validation_run_log"] = str(log_path)
    return validation_summary


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.dry_run:
        raise RuntimeError("Only dry-run mode is supported by this experiment.")
    if args.validate:
        summary = _run_validate_mode(args)
    elif args.full_scan:
        summary = run_full_scan(
            corpus_root=args.corpus_root,
            output_dir=args.output,
            cache_db=args.cache_db,
            target_total=args.target_total,
            max_per_gutenberg_id=args.max_per_gutenberg_id,
            validation_model=args.model,
        )
    else:
        summary = run(
            corpus_root=args.corpus_root,
            output_dir=args.output,
            cache_db=args.cache_db,
            max_per_gutenberg_id=args.max_per_gutenberg_id,
        )
    print(json.dumps(summary, indent=2, sort_keys=True))
    # A fatal validation abort (bad/expired key, exhausted quota) leaves
    # only the completed subset of the paid sample - the exit status must
    # say so, matching run_census.py's own return 3 in the equivalent
    # case, so a caller (shell script, CI) doesn't mistake a partial run
    # for a complete one (review finding: Codex P1, this PR).
    if summary.get("aborted"):
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
