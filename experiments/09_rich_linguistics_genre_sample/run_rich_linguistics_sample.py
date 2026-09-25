"""Run and audit rich linguistics over the 146-story genre sample.

This experiment reuses the fixed experiment-05 balanced manifest, mirrors
sampled story buckets into the experiment results tree, writes v2 token-detail
and derived lexical artifacts there, and prepares/scored the preregistered
noun-family POS audit without writing generated sidecars into ``corpora/``.
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import hashlib
import json
import pathlib
import resource
import shutil
import subprocess
import sys
import time
from typing import Any, Iterable, Optional

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "lcats" / "src"))

from lcats.analysis.corpus import cli as corpus_cli  # noqa: E402
from lcats.analysis.linguistics import lexicon, runner, sidecar  # noqa: E402

EXPERIMENT_NAME = "experiments/09_rich_linguistics_genre_sample"
MANIFEST_PATH = (
    _REPO_ROOT
    / "experiments"
    / "05_metadata_genre_prefilter"
    / "results"
    / "full_scan"
    / "genre_balanced_manifest.jsonl"
)
CORPUS_ROOT = _REPO_ROOT / "corpora"
RESULTS_DIR = _REPO_ROOT / "experiments" / "09_rich_linguistics_genre_sample" / "results"
COPIED_BUCKETS_DIRNAME = "copied_buckets"
SNAPSHOT_MANIFEST_FILENAME = "sample_snapshot_manifest.json"
STORY_LIST_FILENAME = "story-list.txt"
RUN_SUMMARY_FILENAME = "linguistics_run_summary.json"
REPORT_FILENAME = "experiment_report.json"
AUDIT_FILENAME = "pos_audit.json"
AUDIT_SAMPLE_FILENAME = "pos_audit_sample.csv"
EXPECTED_SAMPLE_COUNT = 146
AUDIT_ROWS_PER_GENRE = 24
AUDIT_MIN_GENRE_ROWS = 10
OVERALL_GATE = 0.90
SEVERE_GENRE_GATE = 0.80
AUDIT_FIELDS = (
    "story_id",
    "selection_genre",
    "audit_bucket",
    "audit_features",
    "token_key",
    "sentence_index",
    "token_index",
    "global_token_index",
    "text",
    "lemma",
    "machine_upos",
    "context",
    "gold_upos",
    "notes",
)


@dataclasses.dataclass(frozen=True)
class ManifestRow:
    """One selected sample row from the experiment-05 manifest."""

    story_id: str
    story_path: pathlib.Path
    selection_genre: str
    author: str
    raw: dict[str, Any]


@dataclasses.dataclass(frozen=True)
class StorySnapshot:
    """Source and copied story identity for one sampled bucket."""

    manifest_row: ManifestRow
    source_story_path: pathlib.Path
    copied_story_path: pathlib.Path
    source_story_sha256: str
    copied_story_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "story_id": self.manifest_row.story_id,
            "selection_genre": self.manifest_row.selection_genre,
            "author": self.manifest_row.author,
            "source_story_path": _repo_relative(self.source_story_path),
            "copied_story_path": _repo_relative(self.copied_story_path),
            "source_story_sha256": self.source_story_sha256,
            "copied_story_sha256": self.copied_story_sha256,
            "manifest_row": self.manifest_row.raw,
        }


def run_pilot(
    *,
    manifest_path: pathlib.Path = MANIFEST_PATH,
    corpus_root: pathlib.Path = CORPUS_ROOT,
    output_dir: pathlib.Path = RESULTS_DIR,
    backend_name: str = "spacy",
    model_name: str = "",
    smoke_count: Optional[int] = None,
    expected_count: Optional[int] = EXPECTED_SAMPLE_COUNT,
    overwrite: bool = False,
    resume: bool = False,
    existing: str = runner.EXISTING_SKIP,
    dry_run: bool = False,
    audit_labels_path: Optional[pathlib.Path] = None,
) -> dict[str, Any]:
    """Mirror the sample, run rich linguistics, and write pilot artifacts."""
    if overwrite and resume:
        raise ValueError("choose either --overwrite or --resume, not both")
    started = time.perf_counter()
    start_rss = _max_rss_bytes()
    rows = load_manifest(manifest_path, expected_count=expected_count)
    selected_rows = rows[:smoke_count] if smoke_count is not None else rows
    output_dir.mkdir(parents=True, exist_ok=True)
    mirror_root = output_dir / COPIED_BUCKETS_DIRNAME
    snapshot_path = output_dir / SNAPSHOT_MANIFEST_FILENAME

    if resume:
        snapshot_manifest = load_and_validate_snapshot(
            snapshot_path,
            corpus_root=corpus_root,
            mirror_root=mirror_root,
            expected_smoke_count=smoke_count,
            expected_story_count=len(selected_rows),
        )
        copied_story_paths = [
            _repo_path(item["copied_story_path"])
            for item in snapshot_manifest["stories"]
        ]
    else:
        if snapshot_path.exists() or mirror_root.exists():
            if not overwrite:
                raise FileExistsError(
                    f"existing snapshot found under {output_dir}; use --resume "
                    "to continue it or --overwrite to rebuild it"
                )
            prune_results(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        snapshot_manifest, copied_story_paths = copy_sample_buckets_and_snapshot(
            selected_rows,
            manifest_path=manifest_path,
            corpus_root=corpus_root,
            mirror_root=mirror_root,
            smoke_count=smoke_count,
            manifest_row_count=len(rows),
        )
        sidecar.write_json_atomic(snapshot_path, snapshot_manifest)

    analysis_story_paths = [_invocation_path(path) for path in copied_story_paths]
    story_list_path = output_dir / STORY_LIST_FILENAME
    write_story_list(analysis_story_paths, story_list_path)

    resolved_model_name = model_name or ("en" if backend_name == "stanza" else "")
    options = sidecar.LinguisticsOptions(
        backend_name=backend_name,
        model_name=resolved_model_name,
        include_token_detail=True,
        token_detail_version=sidecar.TOKEN_DETAIL_VERSION_V2,
    )
    backend = runner.make_backend(backend_name, resolved_model_name)
    run_summary = runner.run(
        analysis_story_paths,
        backend=backend,
        options=options,
        existing=existing,
        dry_run=dry_run,
        include_lexicon=True,
    )
    run_summary_path = output_dir / RUN_SUMMARY_FILENAME
    sidecar.write_json_atomic(run_summary_path, run_summary.to_dict())

    validation_summary = validate_generated_artifacts(copied_story_paths)
    audit = build_pos_audit(
        snapshot_manifest=snapshot_manifest,
        copied_story_paths=copied_story_paths,
        output_dir=output_dir,
        labels_path=audit_labels_path,
    )
    sidecar.write_json_atomic(output_dir / AUDIT_FILENAME, audit)

    elapsed_seconds = time.perf_counter() - started
    report = build_report(
        snapshot_manifest=snapshot_manifest,
        manifest_path=manifest_path,
        output_dir=output_dir,
        story_list_path=story_list_path,
        run_summary_path=run_summary_path,
        run_summary=run_summary,
        validation_summary=validation_summary,
        audit=audit,
        corpus_root=corpus_root,
        backend_name=backend_name,
        model_name=resolved_model_name,
        smoke_count=smoke_count,
        resume=resume,
        overwrite=overwrite,
        dry_run=dry_run,
        elapsed_seconds=elapsed_seconds,
        peak_memory_bytes=max(0, _max_rss_bytes() - start_rss) or _max_rss_bytes(),
    )
    sidecar.write_json_atomic(output_dir / REPORT_FILENAME, report)
    return report


def load_manifest(
    path: pathlib.Path, *, expected_count: Optional[int]
) -> list[ManifestRow]:
    """Load and validate the selected-sample manifest."""
    rows: list[ManifestRow] = []
    seen_ids: set[str] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"{path}:{line_number}: invalid JSON: {error}"
                ) from error
            story_id = _required_string(raw, "story_id", path, line_number)
            story_path = _validate_manifest_story_path(
                _required_string(raw, "story_path", path, line_number),
                manifest_path=path,
                line_number=line_number,
            )
            selection_genre = _required_string(
                raw, "selection_genre", path, line_number
            )
            author = raw.get("author", "")
            if not isinstance(author, str):
                author = ""
            if story_id in seen_ids:
                raise ValueError(
                    f"{path}:{line_number}: duplicate story_id {story_id!r}"
                )
            seen_ids.add(story_id)
            rows.append(
                ManifestRow(
                    story_id=story_id,
                    story_path=story_path,
                    selection_genre=selection_genre,
                    author=author,
                    raw=raw,
                )
            )
    if expected_count is not None and len(rows) != expected_count:
        raise ValueError(
            f"{path}: expected {expected_count} manifest rows, found {len(rows)}"
        )
    return rows


def copy_sample_buckets_and_snapshot(
    rows: Iterable[ManifestRow],
    *,
    manifest_path: pathlib.Path,
    corpus_root: pathlib.Path,
    mirror_root: pathlib.Path,
    smoke_count: Optional[int],
    manifest_row_count: int,
) -> tuple[dict[str, Any], list[pathlib.Path]]:
    """Copy sampled buckets and return snapshot manifest data."""
    corpus_root = corpus_root.resolve(strict=True)
    mirror_root = mirror_root.resolve(strict=False)
    copied_story_paths: list[pathlib.Path] = []
    snapshots: list[StorySnapshot] = []
    rows = list(rows)
    for row in rows:
        source_story = _resolve_beneath(corpus_root, row.story_path)
        if not source_story.is_file():
            raise FileNotFoundError(f"source story not found: {source_story}")
        destination_bucket = _resolve_beneath(mirror_root, row.story_path.parent)
        destination_bucket.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_story.parent, destination_bucket)
        copied_story = destination_bucket / "story.json"
        copied_story_paths.append(copied_story)
        snapshots.append(
            StorySnapshot(
                manifest_row=row,
                source_story_path=source_story,
                copied_story_path=copied_story,
                source_story_sha256=_sha256_file(source_story),
                copied_story_sha256=_sha256_file(copied_story),
            )
        )
    return (
        {
            "schema_version": "rich-linguistics-sample-snapshot-v1",
            "experiment": EXPERIMENT_NAME,
            "source_commit": _git_commit(),
            "manifest_path": _repo_relative(manifest_path),
            "manifest_sha256": _sha256_file(manifest_path),
            "manifest_row_count": manifest_row_count,
            "corpus_root": _repo_relative(corpus_root),
            "copied_bucket_root": _repo_relative(mirror_root),
            "selected_story_count": len(rows),
            "smoke_count": smoke_count,
            "stories": [snapshot.to_dict() for snapshot in snapshots],
        },
        copied_story_paths,
    )


def load_and_validate_snapshot(
    snapshot_path: pathlib.Path,
    *,
    corpus_root: pathlib.Path,
    mirror_root: pathlib.Path,
    expected_smoke_count: Optional[int],
    expected_story_count: int,
) -> dict[str, Any]:
    """Load an existing snapshot and verify copied-story provenance."""
    data = sidecar.load_json(snapshot_path)
    if not isinstance(data, dict):
        raise ValueError(f"{snapshot_path}: expected JSON object")
    if data.get("schema_version") != "rich-linguistics-sample-snapshot-v1":
        raise ValueError(f"{snapshot_path}: unsupported snapshot schema")
    if data.get("experiment") != EXPERIMENT_NAME:
        raise ValueError(f"{snapshot_path}: snapshot belongs to another experiment")
    if data.get("smoke_count") != expected_smoke_count:
        raise ValueError(f"{snapshot_path}: smoke_count differs from requested resume")
    if data.get("copied_bucket_root") != _repo_relative(mirror_root):
        raise ValueError(f"{snapshot_path}: copied bucket root differs")
    if data.get("corpus_root") != _repo_relative(corpus_root.resolve(strict=True)):
        raise ValueError(f"{snapshot_path}: corpus root differs")
    stories = data.get("stories")
    if not isinstance(stories, list):
        raise ValueError(f"{snapshot_path}: stories must be a list")
    if len(stories) != expected_story_count:
        raise ValueError(f"{snapshot_path}: selected story count differs")
    for index, item in enumerate(stories):
        if not isinstance(item, dict):
            raise ValueError(f"{snapshot_path}: stories[{index}] must be an object")
        copied_story_path = _repo_path(_required_string_simple(item, "copied_story_path"))
        copied_hash = _required_string_simple(item, "copied_story_sha256")
        source_hash = _required_string_simple(item, "source_story_sha256")
        if not copied_story_path.is_file():
            raise FileNotFoundError(f"copied story missing: {copied_story_path}")
        if _sha256_file(copied_story_path) != copied_hash:
            raise ValueError(f"copied story hash mismatch: {copied_story_path}")
        if copied_hash != source_hash:
            raise ValueError(
                f"copied story no longer matches source snapshot: {copied_story_path}"
            )
    return data


def validate_generated_artifacts(story_paths: Iterable[pathlib.Path]) -> dict[str, Any]:
    """Validate compact, v2 token detail, and lexical artifacts."""
    results: list[dict[str, Any]] = []
    counts = {
        "compact_valid": 0,
        "token_detail_valid": 0,
        "lexicon_valid": 0,
        "compact_invalid": 0,
        "token_detail_invalid": 0,
        "lexicon_invalid": 0,
        "missing_outputs": 0,
    }
    token_total = 0
    lexical_row_total = 0
    for story_path in story_paths:
        story_path = pathlib.Path(story_path)
        compact_path = story_path.parent / sidecar.SIDECAR_FILENAME
        detail_path = story_path.parent / sidecar.TOKEN_DETAIL_FILENAME
        lexicon_path = story_path.parent / lexicon.LEXICON_FILENAME
        row: dict[str, Any] = {
            "story_path": _repo_relative(story_path),
            "compact_path": _repo_relative(compact_path),
            "token_detail_path": _repo_relative(detail_path),
            "lexicon_path": _repo_relative(lexicon_path),
        }
        if not compact_path.exists() or not detail_path.exists() or not lexicon_path.exists():
            counts["missing_outputs"] += 1
            row["valid"] = False
            row["findings"] = [
                {
                    "artifact": "outputs",
                    "severity": "error",
                    "message": "missing one or more generated outputs",
                }
            ]
            results.append(row)
            continue
        story_data = corpus_cli.read_story_data(story_path)
        body = corpus_cli.coerce_story_text(story_data.get("body", ""))
        compact = sidecar.load_json(compact_path)
        detail = sidecar.load_json(detail_path)
        lexicon_data = sidecar.load_json(lexicon_path)
        compact_validation = sidecar.validate_sidecar(compact)
        detail_validation = sidecar.validate_token_detail(
            detail, source_body=body, compact_sidecar=compact
        )
        lexicon_validation = lexicon.validate_lexicon(
            lexicon_data, source_token_detail=detail
        )
        validations = {
            "compact": compact_validation,
            "token_detail": detail_validation,
            "lexicon": lexicon_validation,
        }
        findings = [
            {"artifact": name, **dataclasses.asdict(finding)}
            for name, validation in validations.items()
            for finding in validation.findings
        ]
        for name, validation in validations.items():
            counts[f"{name}_valid" if validation.valid else f"{name}_invalid"] += 1
        denominators = lexicon_data.get("denominators", {})
        if isinstance(denominators, dict):
            token_total += _int_or_zero(denominators.get("token_count"))
            lexical_row_total += _int_or_zero(denominators.get("lexical_row_count"))
        row["valid"] = not findings
        row["findings"] = findings
        results.append(row)
    return {
        "schema_version": "rich-linguistics-validation-summary-v1",
        "counts": counts,
        "token_total": token_total,
        "lexical_row_total": lexical_row_total,
        "results": results,
    }


def build_pos_audit(
    *,
    snapshot_manifest: dict[str, Any],
    copied_story_paths: Iterable[pathlib.Path],
    output_dir: pathlib.Path,
    labels_path: Optional[pathlib.Path],
) -> dict[str, Any]:
    """Create or score the preregistered noun-family POS audit."""
    samples = select_audit_rows(snapshot_manifest, copied_story_paths)
    sample_path = output_dir / AUDIT_SAMPLE_FILENAME
    preregistration = audit_preregistration()
    if labels_path is None:
        write_audit_sample(samples, sample_path)
        return {
            "schema_version": "rich-linguistics-pos-audit-v1",
            "status": "manual_audit_pending",
            "preregistration": preregistration,
            "sample_path": _repo_relative(sample_path),
            "sample_row_count": len(samples),
            "scoring": None,
            "decisions": pending_decisions(),
        }
    if not samples:
        raise ValueError("no audit sample rows are available to score")
    labels = load_audit_labels(labels_path)
    scoring = score_audit(samples, labels)
    write_audit_sample(_apply_audit_labels(samples, labels), sample_path)
    return {
        "schema_version": "rich-linguistics-pos-audit-v1",
        "status": "scored",
        "preregistration": preregistration,
        "sample_path": _repo_relative(sample_path),
        "labels_path": _repo_relative(labels_path),
        "sample_row_count": len(samples),
        "scoring": scoring,
        "decisions": scored_decisions(scoring),
    }


def select_audit_rows(
    snapshot_manifest: dict[str, Any], copied_story_paths: Iterable[pathlib.Path]
) -> list[dict[str, Any]]:
    """Select deterministic audit rows across genres and POS outcomes."""
    story_meta = {
        item["story_id"]: item
        for item in snapshot_manifest.get("stories", [])
        if isinstance(item, dict) and isinstance(item.get("story_id"), str)
    }
    by_genre: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for story_path in copied_story_paths:
        story_id = sidecar.story_identity(story_path)
        meta = story_meta.get(story_id, {})
        genre = meta.get("selection_genre", "unknown")
        detail_path = pathlib.Path(story_path).parent / sidecar.TOKEN_DETAIL_FILENAME
        if not detail_path.exists():
            continue
        detail = sidecar.load_json(detail_path)
        body = corpus_cli.coerce_story_text(
            corpus_cli.read_story_data(pathlib.Path(story_path)).get("body", "")
        )
        for sentence in detail.get("sentences", []):
            if not isinstance(sentence, dict):
                continue
            context = _sentence_context(body, sentence)
            for token in sentence.get("tokens", []):
                if not isinstance(token, dict):
                    continue
                text = str(token.get("text", ""))
                upos = str(token.get("upos", ""))
                if not _has_letter(text) or upos in {"PUNCT", "SPACE"}:
                    continue
                bucket = _audit_bucket(upos)
                row = {
                    "story_id": story_id,
                    "selection_genre": genre,
                    "audit_bucket": bucket,
                    "audit_features": ",".join(_audit_features(text, upos)),
                    "token_key": (
                        f"{story_id}#g{token.get('global_token_index', 0)}"
                    ),
                    "sentence_index": token.get("sentence_index")
                    or sentence.get("sentence_index"),
                    "token_index": token.get("token_index"),
                    "global_token_index": token.get("global_token_index"),
                    "text": text,
                    "lemma": str(token.get("lemma", "")),
                    "machine_upos": upos,
                    "context": context,
                    "gold_upos": "",
                    "notes": "",
                }
                by_genre.setdefault(str(genre), {}).setdefault(bucket, []).append(row)
    selected: list[dict[str, Any]] = []
    for genre in sorted(by_genre):
        selected.extend(select_genre_audit_rows(by_genre[genre]))
    return selected


def select_genre_audit_rows(
    buckets: dict[str, list[dict[str, Any]]],
    *,
    rows_per_genre: int = AUDIT_ROWS_PER_GENRE,
) -> list[dict[str, Any]]:
    """Select balanced rows for one genre across machine POS outcomes."""
    bucket_order = ("NOUN", "PROPN", "OTHER")
    base_quota = rows_per_genre // len(bucket_order)
    quotas = {bucket: base_quota for bucket in bucket_order}
    for bucket in bucket_order[: rows_per_genre % len(bucket_order)]:
        quotas[bucket] += 1
    sorted_buckets = {
        bucket: sorted(
            rows,
            key=lambda row: (
                _audit_priority(
                    str(row["text"]),
                    str(row["machine_upos"]),
                    str(row.get("audit_features", "")),
                ),
                str(row["story_id"]),
                int(row.get("global_token_index") or 0),
            ),
        )
        for bucket, rows in buckets.items()
    }
    selected: list[dict[str, Any]] = []
    selected_keys: set[str] = set()
    for bucket in bucket_order:
        for row in _select_bucket_rows(
            sorted_buckets.get(bucket, []), limit=quotas[bucket]
        ):
            selected.append(row)
            selected_keys.add(str(row["token_key"]))
    if len(selected) < rows_per_genre:
        leftovers = [
            row
            for bucket in bucket_order
            for row in sorted_buckets.get(bucket, [])
            if str(row["token_key"]) not in selected_keys
        ]
        selected.extend(leftovers[: rows_per_genre - len(selected)])
    return sorted(
        selected,
        key=lambda row: (
            str(row["selection_genre"]),
            str(row["audit_bucket"]),
            str(row["story_id"]),
            int(row.get("global_token_index") or 0),
        ),
    )


def _select_bucket_rows(rows: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    """Select rows from one POS bucket while preserving feature variety."""
    feature_order = (
        "contraction_or_possessive",
        "hyphenated",
        "archaic_candidate",
        "noun_verb_ambiguous",
        "proper_name_candidate",
        "ordinary",
    )
    selected: list[dict[str, Any]] = []
    selected_keys: set[str] = set()
    text_counts: dict[str, int] = {}
    while len(selected) < limit:
        made_progress = False
        for feature in feature_order:
            for row in rows:
                token_key = str(row["token_key"])
                text_key = str(row["text"]).casefold()
                if token_key in selected_keys or text_counts.get(text_key, 0) >= 2:
                    continue
                if feature not in str(row.get("audit_features", "")).split(","):
                    continue
                selected.append(row)
                selected_keys.add(token_key)
                text_counts[text_key] = text_counts.get(text_key, 0) + 1
                made_progress = True
                break
            if len(selected) >= limit:
                break
        if not made_progress:
            break
    if len(selected) < limit:
        for row in rows:
            token_key = str(row["token_key"])
            if token_key in selected_keys:
                continue
            selected.append(row)
            selected_keys.add(token_key)
            if len(selected) >= limit:
                break
    return selected


def write_audit_sample(rows: list[dict[str, Any]], path: pathlib.Path) -> None:
    """Write deterministic human-label audit CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=AUDIT_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in AUDIT_FIELDS})


def _apply_audit_labels(
    rows: list[dict[str, Any]], labels: dict[str, str]
) -> list[dict[str, Any]]:
    return [{**row, "gold_upos": labels.get(row["token_key"], "")} for row in rows]


def load_audit_labels(path: pathlib.Path) -> dict[str, str]:
    """Load human audit labels keyed by token key."""
    labels: dict[str, str] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            token_key = row.get("token_key", "")
            label = row.get("gold_upos", "").strip().upper()
            if not token_key:
                continue
            if label not in {"NOUN", "PROPN", "OTHER"}:
                raise ValueError(
                    f"{path}: gold_upos for {token_key!r} must be NOUN, PROPN, or OTHER"
                )
            labels[token_key] = label
    return labels


def score_audit(rows: list[dict[str, Any]], labels: dict[str, str]) -> dict[str, Any]:
    """Score machine POS labels against human labels."""
    missing = [row["token_key"] for row in rows if row["token_key"] not in labels]
    if missing:
        raise ValueError(
            f"audit labels missing {len(missing)} sampled token keys; first: {missing[0]}"
        )
    confusion: dict[str, dict[str, int]] = {}
    by_genre_rows: dict[str, list[dict[str, Any]]] = {}
    scored_rows: list[dict[str, Any]] = []
    for row in rows:
        gold = labels[row["token_key"]]
        machine = row["machine_upos"] if row["machine_upos"] in {"NOUN", "PROPN"} else "OTHER"
        confusion.setdefault(gold, {})
        confusion[gold][machine] = confusion[gold].get(machine, 0) + 1
        scored = {**row, "gold_upos": gold}
        scored_rows.append(scored)
        by_genre_rows.setdefault(row["selection_genre"], []).append(scored)
    return {
        "overall": metrics_for_rows(scored_rows),
        "by_genre": {
            genre: metrics_for_rows(genre_rows)
            for genre, genre_rows in sorted(by_genre_rows.items())
        },
        "confusion": confusion,
        "row_count": len(scored_rows),
    }


def metrics_for_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Return NOUN, PROPN, and combined noun-family precision/recall."""
    return {
        "row_count": len(rows),
        "NOUN": binary_metrics(rows, {"NOUN"}, {"NOUN"}),
        "PROPN": binary_metrics(rows, {"PROPN"}, {"PROPN"}),
        "noun_family": binary_metrics(rows, {"NOUN", "PROPN"}, {"NOUN", "PROPN"}),
    }


def binary_metrics(
    rows: list[dict[str, Any]], machine_positive: set[str], gold_positive: set[str]
) -> dict[str, Any]:
    """Return binary precision and recall counts for a POS grouping."""
    tp = fp = fn = tn = 0
    for row in rows:
        machine = row["machine_upos"] in machine_positive
        gold = row["gold_upos"] in gold_positive
        if machine and gold:
            tp += 1
        elif machine and not gold:
            fp += 1
        elif not machine and gold:
            fn += 1
        else:
            tn += 1
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    return {
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "true_negative": tn,
        "precision": precision,
        "recall": recall,
    }


def audit_preregistration() -> dict[str, Any]:
    """Return the preregistered POS audit protocol."""
    return {
        "schema_version": "rich-linguistics-pos-audit-preregistration-v1",
        "labels": ["NOUN", "PROPN", "OTHER"],
        "noun_family": ["NOUN", "PROPN"],
        "sample_rows_per_genre": AUDIT_ROWS_PER_GENRE,
        "selection_policy": (
            "deterministic stratified rows by genre with per-genre quotas for "
            "machine NOUN, machine PROPN, and machine-negative OTHER candidates; "
            "non-letter tokens are excluded, and rows within each bucket prioritize "
            "proper names, contractions, hyphenation, archaic endings, and "
            "noun/verb ambiguity"
        ),
        "overall_gate": {
            "combined_noun_family_min_precision": OVERALL_GATE,
            "combined_noun_family_min_recall": OVERALL_GATE,
        },
        "severe_genre_slice_failure_rule": {
            "minimum_audited_rows": AUDIT_MIN_GENRE_ROWS,
            "combined_noun_family_min_precision": SEVERE_GENRE_GATE,
            "combined_noun_family_min_recall": SEVERE_GENRE_GATE,
        },
        "stanza_comparison_policy": (
            "spaCy alone satisfies the pilot when the scored human audit passes "
            "the overall and genre-slice gates; Stanza comparison is warranted "
            "only for a missed or inconclusive spaCy gate."
        ),
    }


def pending_decisions() -> dict[str, Any]:
    """Return downstream decisions before manual labels are available."""
    return {
        "quality_recommendation": "manual_audit_pending",
        "sample_pos_figures": {
            "decision": "defer",
            "reason": "human POS audit labels have not been supplied",
        },
        "full_corpus_run": {
            "decision": "defer",
            "reason": "pilot quality gate cannot be evaluated before human audit",
        },
    }


def scored_decisions(scoring: dict[str, Any]) -> dict[str, Any]:
    """Return downstream decisions from scored audit metrics."""
    overall = scoring["overall"]["noun_family"]
    precision = overall["precision"]
    recall = overall["recall"]
    severe_failures = []
    inconclusive_genres = []
    for genre, metrics in scoring["by_genre"].items():
        family = metrics["noun_family"]
        if metrics["row_count"] < AUDIT_MIN_GENRE_ROWS:
            inconclusive_genres.append(genre)
            continue
        if (
            family["precision"] is not None
            and family["precision"] < SEVERE_GENRE_GATE
        ) or (family["recall"] is not None and family["recall"] < SEVERE_GENRE_GATE):
            severe_failures.append(genre)
    passes_overall = (
        precision is not None
        and recall is not None
        and precision >= OVERALL_GATE
        and recall >= OVERALL_GATE
    )
    passes = passes_overall and not severe_failures and not inconclusive_genres
    quality = "proceed" if passes else "no_go"
    reason = (
        "human POS audit passed preregistered gates"
        if passes
        else "human POS audit did not satisfy all preregistered gates"
    )
    return {
        "quality_recommendation": quality,
        "overall_gate_passed": passes_overall,
        "severe_genre_failures": severe_failures,
        "inconclusive_genres": inconclusive_genres,
        "sample_pos_figures": {"decision": quality, "reason": reason},
        "full_corpus_run": {"decision": quality, "reason": reason},
    }


def build_report(
    *,
    snapshot_manifest: dict[str, Any],
    manifest_path: pathlib.Path,
    output_dir: pathlib.Path,
    story_list_path: pathlib.Path,
    run_summary_path: pathlib.Path,
    run_summary: runner.RunSummary,
    validation_summary: dict[str, Any],
    audit: dict[str, Any],
    corpus_root: pathlib.Path,
    backend_name: str,
    model_name: str,
    smoke_count: Optional[int],
    resume: bool,
    overwrite: bool,
    dry_run: bool,
    elapsed_seconds: float,
    peak_memory_bytes: int,
) -> dict[str, Any]:
    """Build the pilot experiment report."""
    copied_root = output_dir / COPIED_BUCKETS_DIRNAME
    copied_stories = sorted(copied_root.glob("**/story.json"))
    compact_paths = sorted(copied_root.glob(f"**/{sidecar.SIDECAR_FILENAME}"))
    detail_paths = sorted(copied_root.glob(f"**/{sidecar.TOKEN_DETAIL_FILENAME}"))
    lexicon_paths = sorted(copied_root.glob(f"**/{lexicon.LEXICON_FILENAME}"))
    copied_bytes = _directory_size(copied_root)
    token_total = validation_summary["token_total"]
    lexical_row_total = validation_summary["lexical_row_total"]
    validation_clean = not any(
        count
        for key, count in validation_summary["counts"].items()
        if key.endswith("_invalid") or key == "missing_outputs"
    )
    per_story_bytes = copied_bytes / len(copied_stories) if copied_stories else None
    per_token_bytes = copied_bytes / token_total if token_total else None
    return {
        "schema_version": "rich-linguistics-sample-report-v1",
        "experiment": EXPERIMENT_NAME,
        "source_commit": snapshot_manifest["source_commit"],
        "manifest_path": _repo_relative(manifest_path),
        "manifest_sha256": snapshot_manifest["manifest_sha256"],
        "snapshot_manifest_path": _repo_relative(output_dir / SNAPSHOT_MANIFEST_FILENAME),
        "manifest_row_count": snapshot_manifest["manifest_row_count"],
        "selected_story_count": snapshot_manifest["selected_story_count"],
        "smoke_count": smoke_count,
        "backend_name": backend_name,
        "model_name": model_name,
        "resume": resume,
        "overwrite": overwrite,
        "dry_run": dry_run,
        "elapsed_seconds": round(elapsed_seconds, 3),
        "peak_memory_bytes": peak_memory_bytes,
        "copied_bucket_root": _repo_relative(copied_root),
        "copied_story_count": len(copied_stories),
        "compact_sidecar_count": len(compact_paths),
        "token_detail_count": len(detail_paths),
        "lexicon_count": len(lexicon_paths),
        "copied_bucket_bytes": copied_bytes,
        "bytes_per_story": per_story_bytes,
        "bytes_per_token": per_token_bytes,
        "token_total": token_total,
        "lexical_row_total": lexical_row_total,
        "projected_full_corpus": project_full_corpus_cost(
            corpus_root=corpus_root,
            sample_story_count=len(copied_stories),
            sample_bytes=copied_bytes,
            sample_elapsed_seconds=elapsed_seconds,
        ),
        "story_list_path": _repo_relative(story_list_path),
        "run_summary_path": _repo_relative(run_summary_path),
        "run_clean": run_summary.clean,
        "validation_clean": validation_clean,
        "pilot_clean": run_summary.clean and validation_clean,
        "run_counts": run_summary.to_dict()["counts"],
        "validation": validation_summary,
        "pos_audit_path": _repo_relative(output_dir / AUDIT_FILENAME),
        "pos_audit_status": audit["status"],
        "parquet_export": parquet_export_summary(output_dir / "parquet"),
        "decisions": audit["decisions"],
        "corpora_modified": bool(_corpus_linguistics_sidecars(corpus_root)),
        "retention_options": [
            "checked_in_experiment_results",
            "compressed_release_or_external_archive",
            "derived_lexicon_only_plus_regeneration_manifest",
        ],
    }


def project_full_corpus_cost(
    *,
    corpus_root: pathlib.Path,
    sample_story_count: int,
    sample_bytes: int,
    sample_elapsed_seconds: float,
) -> dict[str, Any]:
    """Project full-corpus cost from the pilot sample."""
    corpus_root = pathlib.Path(corpus_root)
    full_count = len(list(corpus_root.rglob("story.json"))) if corpus_root.exists() else None
    if not full_count or not sample_story_count:
        return {"story_count": full_count, "basis": "insufficient_sample"}
    scale = full_count / sample_story_count
    return {
        "story_count": full_count,
        "scale_factor": scale,
        "estimated_bytes": int(sample_bytes * scale),
        "estimated_elapsed_seconds": round(sample_elapsed_seconds * scale, 3),
        "basis": "linear_projection_from_pilot_story_count",
    }


def parquet_export_summary(parquet_dir: pathlib.Path) -> Optional[dict[str, Any]]:
    """Return metadata for an existing experiment Parquet export."""
    manifest_path = parquet_dir / "parquet_manifest.json"
    if not manifest_path.exists():
        return None
    manifest = sidecar.load_json(manifest_path)
    if not isinstance(manifest, dict):
        return None
    files = manifest.get("files", {})
    byte_count = 0
    if isinstance(files, dict):
        for item in files.values():
            if isinstance(item, dict):
                byte_count += _int_or_zero(item.get("bytes"))
    return {
        "manifest_path": _repo_relative(manifest_path),
        "byte_count": byte_count,
        "story_count": manifest.get("story_count"),
        "sentence_count": manifest.get("sentence_count"),
        "token_count": manifest.get("token_count"),
    }


def prune_results(output_dir: pathlib.Path) -> None:
    """Remove stale generated artifacts before rebuilding the sample."""
    for path in (
        output_dir / COPIED_BUCKETS_DIRNAME,
        output_dir / STORY_LIST_FILENAME,
        output_dir / SNAPSHOT_MANIFEST_FILENAME,
        output_dir / RUN_SUMMARY_FILENAME,
        output_dir / REPORT_FILENAME,
        output_dir / AUDIT_FILENAME,
        output_dir / AUDIT_SAMPLE_FILENAME,
        output_dir / "parquet",
    ):
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()


def write_story_list(paths: Iterable[pathlib.Path], path: pathlib.Path) -> None:
    """Write a deterministic story list."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(f"{_repo_relative(story_path)}\n" for story_path in paths)
    path.write_text(text, encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    """Build the experiment CLI parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=pathlib.Path, default=MANIFEST_PATH)
    parser.add_argument("--corpus-root", type=pathlib.Path, default=CORPUS_ROOT)
    parser.add_argument("--output-dir", type=pathlib.Path, default=RESULTS_DIR)
    parser.add_argument(
        "--backend", choices=["spacy", "stanza", "fake"], default="spacy"
    )
    parser.add_argument("--model", default="")
    parser.add_argument("--smoke-count", type=int)
    parser.add_argument("--expected-count", type=int, default=EXPECTED_SAMPLE_COUNT)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--existing",
        choices=[
            runner.EXISTING_SKIP,
            runner.EXISTING_VALIDATE,
            runner.EXISTING_OVERWRITE,
        ],
        default=runner.EXISTING_SKIP,
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--audit-labels", type=pathlib.Path)
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    """Run the experiment CLI."""
    args = build_parser().parse_args(argv)
    try:
        report = run_pilot(
            manifest_path=args.manifest,
            corpus_root=args.corpus_root,
            output_dir=args.output_dir,
            backend_name=args.backend,
            model_name=args.model,
            smoke_count=args.smoke_count,
            expected_count=args.expected_count,
            overwrite=args.overwrite,
            resume=args.resume,
            existing=args.existing,
            dry_run=args.dry_run,
            audit_labels_path=args.audit_labels,
        )
    except Exception as error:  # noqa: BLE001
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["pilot_clean"] else 1


def _audit_bucket(upos: str) -> str:
    return upos if upos in {"NOUN", "PROPN"} else "OTHER"


def _audit_features(text: str, upos: str) -> list[str]:
    features = []
    if upos == "PROPN" or text[:1].isupper():
        features.append("proper_name_candidate")
    if "'" in text:
        features.append("contraction_or_possessive")
    if "-" in text:
        features.append("hyphenated")
    if text.casefold().endswith(("eth", "est", "th")):
        features.append("archaic_candidate")
    if text.casefold() in {"watch", "light", "train", "ship", "house", "saw", "rose"}:
        features.append("noun_verb_ambiguous")
    if not features:
        features.append("ordinary")
    return features


def _audit_priority(text: str, upos: str, features: str) -> tuple[int, str]:
    if "contraction_or_possessive" in features:
        bucket = 0
    elif "hyphenated" in features:
        bucket = 1
    elif "archaic_candidate" in features:
        bucket = 2
    elif "noun_verb_ambiguous" in features:
        bucket = 3
    elif "proper_name_candidate" in features:
        bucket = 4
    elif upos == "NOUN":
        bucket = 5
    elif upos == "PROPN":
        bucket = 6
    else:
        bucket = 7
    return bucket, text.casefold()


def _has_letter(text: str) -> bool:
    return any(character.isalpha() for character in text)


def _sentence_context(body: str, sentence: dict[str, Any]) -> str:
    start = sentence.get("start_char")
    end = sentence.get("end_char")
    if isinstance(start, int) and isinstance(end, int) and 0 <= start <= end:
        return " ".join(body[start:end].split())[:240]
    return ""


def _required_string(
    data: dict[str, Any], key: str, path: pathlib.Path, line_number: int
) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{path}:{line_number}: missing string field {key!r}")
    return value


def _required_string_simple(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"missing string field {key!r}")
    return value


def _validate_manifest_story_path(
    story_path_text: str, *, manifest_path: pathlib.Path, line_number: int
) -> pathlib.Path:
    story_path = pathlib.PurePosixPath(story_path_text)
    if story_path.is_absolute() or ".." in story_path.parts:
        raise ValueError(
            f"{manifest_path}:{line_number}: story_path must be relative and stay "
            f"within the corpus root: {story_path_text!r}"
        )
    path = pathlib.Path(story_path_text)
    if path.name != "story.json":
        raise ValueError(
            f"{manifest_path}:{line_number}: manifest story_path must end in "
            f"story.json: {story_path_text}"
        )
    return path


def _resolve_beneath(root: pathlib.Path, relative_path: pathlib.Path) -> pathlib.Path:
    resolved = (root / relative_path).resolve(strict=False)
    if resolved != root and root not in resolved.parents:
        raise ValueError(f"path escapes configured root: {relative_path}")
    return resolved


def _repo_relative(path: pathlib.Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(_REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _repo_path(path_text: str) -> pathlib.Path:
    path = pathlib.Path(path_text)
    if path.is_absolute():
        return path
    return _REPO_ROOT / path


def _invocation_path(path: pathlib.Path) -> pathlib.Path:
    resolved = path.resolve()
    try:
        return pathlib.Path(resolved.relative_to(_REPO_ROOT))
    except ValueError:
        return path


def _sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _directory_size(path: pathlib.Path) -> int:
    if not path.exists():
        return 0
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def _corpus_linguistics_sidecars(corpus_root: pathlib.Path) -> list[pathlib.Path]:
    if not corpus_root.exists():
        return []
    paths = [
        path
        for path in corpus_root.rglob("linguistics*.json")
        if path.name
        in (sidecar.SIDECAR_FILENAME, sidecar.TOKEN_DETAIL_FILENAME, lexicon.LEXICON_FILENAME)
    ]
    return sorted(paths, key=lambda path: path.relative_to(corpus_root).as_posix())


def _git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            cwd=_REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return result.stdout.strip()


def _max_rss_bytes() -> int:
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return usage if sys.platform == "darwin" else usage * 1024


def _int_or_zero(value: Any) -> int:
    return value if type(value) is int and value >= 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
