#!/usr/bin/env python3
"""Compare the three historical genre-evidence inputs for the 146-story sample."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from lcats.analysis.corpus.genre_sidecar import validate_sidecar

COMPARISON_VERSION = "three-way-genre-comparison-v1"
EXPECTED_STORY_COUNT = 146
EXPECTED_MODELS = {
    "opus": "claude-opus-4-8",
    "local": "gpt-oss:20b",
}
MODEL_LABEL = "model_detect"

GENRE_ALIASES = {
    "sf": "science fiction",
    "sci-fi": "science fiction",
    "science-fiction": "science fiction",
    "science fiction": "science fiction",
    "fantasy": "fantasy",
    "horror": "horror",
    "mystery": "mystery",
    "adventure": "adventure",
    "western": "western",
    "romance": "romance",
    "humor": "humor",
    "humour": "humor",
    "humor / satire": "humor",
    "satire": "humor",
    "crime": "crime",
    "war": "war",
    "sea": "sea",
    "historical": "historical",
    "apocalyptic": "apocalyptic",
    "psychological": "psychological",
}


class InputValidationError(ValueError):
    """Raised when an input cannot safely participate in the comparison."""

    def __init__(self, diagnostics: list[str]):
        super().__init__("; ".join(diagnostics))
        self.diagnostics = diagnostics


def normalize_genre(value: str) -> str:
    """Return the stable comparison vocabulary for a genre label."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"genre label must be a non-empty string: {value!r}")
    key = " ".join(value.strip().lower().replace("_", " ").split())
    return GENRE_ALIASES.get(key, key)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _relative_or_absolute(path: Path, repository_root: Path) -> str:
    resolved = path.resolve(strict=False)
    try:
        return resolved.relative_to(repository_root).as_posix()
    except ValueError:
        return str(resolved)


def _preflight_outputs(output_dir: Path, input_paths: Iterable[Path]) -> list[str]:
    """Reject protected roots and destinations aliasing input evidence."""
    repository_root = _repository_root()
    resolved_output = output_dir.resolve(strict=False)
    corpus_root = (repository_root / "corpora").resolve()
    diagnostics: list[str] = []
    if output_dir.exists() and output_dir.is_symlink():
        diagnostics.append(f"output directory is a symlink: {output_dir}")
    try:
        if os.path.commonpath((str(resolved_output), str(corpus_root))) == str(
            corpus_root
        ):
            diagnostics.append(
                f"output directory is inside protected corpus root: {output_dir}"
            )
    except ValueError:
        pass
    input_paths = [path.resolve(strict=False) for path in input_paths]
    output_paths = [
        output_dir / "three_way_genre_comparison.jsonl",
        output_dir / "three_way_genre_comparison_summary.json",
        output_dir / "three_way_genre_comparison_report.md",
    ]
    for destination in output_paths:
        resolved_destination = destination.resolve(strict=False)
        if destination.exists() and destination.is_symlink():
            diagnostics.append(f"output destination is a symlink: {destination}")
        if resolved_destination in input_paths:
            diagnostics.append(
                f"output destination aliases an input file: {destination}"
            )
        if destination.exists() and any(
            input_path.exists() and os.path.samefile(destination, input_path)
            for input_path in input_paths
        ):
            diagnostics.append(
                f"output destination is hard-linked to an input file: {destination}"
            )
    return diagnostics


def _read_jsonl(path: Path, *, name: str) -> tuple[list[dict[str, Any]], list[str]]:
    records: list[dict[str, Any]] = []
    diagnostics: list[str] = []
    try:
        handle = path.open(encoding="utf-8")
    except OSError as exc:
        return [], [f"{name}: cannot read {path}: {exc}"]
    with handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                diagnostics.append(f"{name}: blank line at {line_number}")
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                diagnostics.append(
                    f"{name}: malformed JSON at line {line_number}: {exc.msg}"
                )
                continue
            if not isinstance(value, dict):
                diagnostics.append(f"{name}: line {line_number} is not a JSON object")
                continue
            records.append(value)
    return records, diagnostics


def _index_records(
    records: Iterable[dict[str, Any]], *, name: str
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    indexed: dict[str, dict[str, Any]] = {}
    diagnostics: list[str] = []
    for position, record in enumerate(records, start=1):
        story_id = record.get("story_id", record.get("lcats_id"))
        if not isinstance(story_id, str) or not story_id.strip():
            diagnostics.append(
                f"{name}: record {position} has no non-empty story_id/lcats_id"
            )
            continue
        story_id = story_id.strip()
        if story_id in indexed:
            diagnostics.append(f"{name}: duplicate story ID {story_id!r}")
            continue
        indexed[story_id] = record
    return indexed, diagnostics


def _model_assessment(
    record: dict[str, Any], *, name: str
) -> tuple[dict[str, Any] | None, list[str]]:
    assessments = record.get("assessments")
    if not isinstance(assessments, list):
        return None, [
            f"{name}: {record.get('lcats_id', record.get('story_id'))!r} has no assessments list"
        ]
    matches = [
        assessment
        for assessment in assessments
        if isinstance(assessment, dict) and assessment.get("label") == MODEL_LABEL
    ]
    if len(matches) != 1:
        return None, [
            f"{name}: {record.get('lcats_id', record.get('story_id'))!r} has {len(matches)} model_detect assessments, expected 1"
        ]
    assessment = matches[0]
    provenance = assessment.get("provenance")
    result = assessment.get("result")
    if not isinstance(provenance, dict) or not isinstance(result, dict):
        return None, [
            f"{name}: {record.get('lcats_id', record.get('story_id'))!r} model_detect lacks provenance/result objects"
        ]
    evidence = assessment.get("evidence")
    if not isinstance(evidence, dict):
        return None, [
            f"{name}: {record.get('lcats_id', record.get('story_id'))!r} model_detect lacks an evidence object"
        ]
    if evidence.get("error"):
        return None, [
            f"{name}: {record.get('lcats_id', record.get('story_id'))!r} model_detect contains evidence.error"
        ]
    model = provenance.get("backend_model")
    genre = result.get("detected_genre")
    if not isinstance(model, str) or not isinstance(genre, str) or not genre.strip():
        return None, [
            f"{name}: {record.get('lcats_id', record.get('story_id'))!r} model_detect lacks backend_model or detected_genre"
        ]
    return assessment, []


def _metadata_from_manifest(
    record: dict[str, Any], *, name: str
) -> tuple[dict[str, Any] | None, list[str]]:
    assessment = record.get("metadata_assessment")
    if not isinstance(assessment, dict):
        return None, [
            f"{name}: {record.get('story_id')!r} has no metadata_assessment object"
        ]
    result = assessment.get("result")
    if not isinstance(result, dict) or not isinstance(
        result.get("target_candidates"), list
    ):
        return None, [
            f"{name}: {record.get('story_id')!r} metadata_assessment lacks target_candidates"
        ]
    candidates = result["target_candidates"]
    if not candidates or not all(
        isinstance(candidate, str) and candidate.strip() for candidate in candidates
    ):
        return None, [
            f"{name}: {record.get('story_id')!r} has empty or invalid target_candidates"
        ]
    return assessment, []


def _metadata_from_validation(
    record: dict[str, Any], *, name: str
) -> tuple[dict[str, Any] | None, list[str]]:
    assessments = record.get("assessments")
    if not isinstance(assessments, list):
        return None, [f"{name}: {record.get('lcats_id')!r} has no assessments list"]
    matches = [
        assessment
        for assessment in assessments
        if isinstance(assessment, dict)
        and assessment.get("label") == "gutenberg_metadata_rules"
    ]
    if len(matches) != 1:
        return None, [
            f"{name}: {record.get('lcats_id')!r} has {len(matches)} metadata assessments, expected 1"
        ]
    result = matches[0].get("result")
    if not isinstance(result, dict) or not isinstance(
        result.get("target_candidates"), list
    ):
        return None, [
            f"{name}: {record.get('lcats_id')!r} metadata assessment lacks target_candidates"
        ]
    return matches[0], []


def _candidate_values(assessment: dict[str, Any]) -> list[str]:
    return [
        normalize_genre(value) for value in assessment["result"]["target_candidates"]
    ]


def _validate_model_input(path: Path, *, name: str, expected_model: str) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    list[str],
]:
    records, diagnostics = _read_jsonl(path, name=name)
    indexed, index_diagnostics = _index_records(records, name=name)
    diagnostics.extend(index_diagnostics)
    model_assessments: dict[str, dict[str, Any]] = {}
    metadata_assessments: dict[str, dict[str, Any]] = {}
    for story_id, record in indexed.items():
        validation = validate_sidecar(record)
        if not validation.valid:
            diagnostics.extend(
                f"{name}: {story_id!r} sidecar {finding.path}: {finding.message}"
                for finding in validation.findings
                if finding.severity == "error"
            )
        metadata_assessment, metadata_errors = _metadata_from_validation(
            record, name=name
        )
        diagnostics.extend(metadata_errors)
        if metadata_assessment is not None:
            metadata_assessments[story_id] = metadata_assessment
        assessment, errors = _model_assessment(record, name=name)
        diagnostics.extend(errors)
        if assessment is None:
            continue
        if assessment["provenance"].get("backend_model") != expected_model:
            diagnostics.append(
                f"{name}: {story_id!r} backend_model is {assessment['provenance'].get('backend_model')!r}, expected {expected_model!r}"
            )
        model_assessments[story_id] = assessment
    return indexed, metadata_assessments, model_assessments, diagnostics


def _validate_manifest(
    path: Path,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], list[str]]:
    records, diagnostics = _read_jsonl(path, name="metadata")
    indexed, index_diagnostics = _index_records(records, name="metadata")
    diagnostics.extend(index_diagnostics)
    metadata_assessments: dict[str, dict[str, Any]] = {}
    for story_id, record in indexed.items():
        assessment, errors = _metadata_from_manifest(record, name="metadata")
        diagnostics.extend(errors)
        if assessment is not None:
            metadata_assessments[story_id] = assessment
    return indexed, metadata_assessments, diagnostics


def _compare_sets(named_sets: dict[str, set[str]], diagnostics: list[str]) -> None:
    names = list(named_sets)
    first = named_sets[names[0]]
    for name in names[1:]:
        missing = sorted(first - named_sets[name])
        extra = sorted(named_sets[name] - first)
        if missing:
            diagnostics.append(f"{name}: missing story IDs: {', '.join(missing)}")
        if extra:
            diagnostics.append(f"{name}: unexpected story IDs: {', '.join(extra)}")


def validate_inputs(
    metadata_path: Path, opus_path: Path, local_path: Path
) -> dict[str, Any]:
    metadata, metadata_assessments, diagnostics = _validate_manifest(metadata_path)
    opus, opus_metadata, opus_assessments, opus_errors = _validate_model_input(
        opus_path, name="opus", expected_model=EXPECTED_MODELS["opus"]
    )
    local, local_metadata, local_assessments, local_errors = _validate_model_input(
        local_path, name="local", expected_model=EXPECTED_MODELS["local"]
    )
    diagnostics.extend(opus_errors)
    diagnostics.extend(local_errors)
    _compare_sets(
        {"metadata": set(metadata), "opus": set(opus), "local": set(local)}, diagnostics
    )
    for name, embedded in (("opus", opus_metadata), ("local", local_metadata)):
        for story_id in sorted(set(metadata) & set(embedded)):
            expected = _candidate_values(metadata_assessments[story_id])
            actual = _candidate_values(embedded[story_id])
            if actual != expected:
                diagnostics.append(
                    f"{name}: {story_id!r} embedded metadata candidates {actual!r} do not match manifest {expected!r}"
                )
            model_assessments = (
                opus_assessments if name == "opus" else local_assessments
            )
            if story_id in model_assessments:
                model_candidates = model_assessments[story_id]["result"].get(
                    "metadata_target_candidates"
                )
                if not isinstance(model_candidates, list):
                    diagnostics.append(
                        f"{name}: {story_id!r} model_detect lacks metadata_target_candidates"
                    )
                elif [normalize_genre(value) for value in model_candidates] != expected:
                    diagnostics.append(
                        f"{name}: {story_id!r} model metadata_target_candidates do not match manifest {expected!r}"
                    )
    if len(metadata) != EXPECTED_STORY_COUNT:
        diagnostics.append(
            f"metadata: expected {EXPECTED_STORY_COUNT} records, found {len(metadata)}"
        )
    if len(opus) != EXPECTED_STORY_COUNT:
        diagnostics.append(
            f"opus: expected {EXPECTED_STORY_COUNT} records, found {len(opus)}"
        )
    if len(local) != EXPECTED_STORY_COUNT:
        diagnostics.append(
            f"local: expected {EXPECTED_STORY_COUNT} records, found {len(local)}"
        )
    hashes: dict[str, str] = {}
    for name, path in (
        ("metadata", metadata_path),
        ("opus", opus_path),
        ("local", local_path),
    ):
        try:
            hashes[name] = _sha256(path)
        except OSError as exc:
            hashes[name] = ""
            diagnostics.append(f"{name}: cannot hash {path}: {exc}")
    if hashes["opus"] and hashes["opus"] == hashes["local"]:
        diagnostics.append("opus and local source hashes are identical")
    if diagnostics:
        raise InputValidationError(diagnostics)
    return {
        "metadata": metadata,
        "opus": opus,
        "local": local,
        "metadata_assessments": metadata_assessments,
        "opus_assessments": opus_assessments,
        "local_assessments": local_assessments,
        "hashes": hashes,
    }


def classify(
    metadata_candidates: list[str], opus_genre: str, local_genre: str
) -> tuple[str, bool]:
    candidates = [normalize_genre(value) for value in metadata_candidates]
    candidate_set = set(candidates)
    opus = normalize_genre(opus_genre)
    local = normalize_genre(local_genre)
    multi_label = len(candidate_set) > 1
    if (
        multi_label
        and opus != local
        and opus in candidate_set
        and local in candidate_set
    ):
        return "metadata_multi_label_models_split", multi_label
    opus_matches = opus in candidate_set
    local_matches = local in candidate_set
    if opus == local and not opus_matches:
        return "models_agree_metadata_differs", multi_label
    if opus_matches and local_matches and opus == local:
        return "all_three_agree", multi_label
    if opus_matches and not local_matches:
        return "metadata_opus_only", multi_label
    if local_matches and not opus_matches:
        return "metadata_local_only", multi_label
    return "all_three_differ", multi_label


def _derived_timestamp(inputs: dict[str, Any]) -> str:
    timestamps: list[str] = []
    for assessments in (
        inputs["opus_assessments"].values(),
        inputs["local_assessments"].values(),
    ):
        for assessment in assessments:
            timestamp = assessment.get("generated_at")
            if isinstance(timestamp, str):
                timestamps.append(timestamp)
    return max(timestamps) if timestamps else "unknown"


def build_rows(inputs: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for story_id in sorted(inputs["metadata"]):
        metadata_record = inputs["metadata"][story_id]
        metadata_assessment = inputs["metadata_assessments"][story_id]
        opus_assessment = inputs["opus_assessments"][story_id]
        local_assessment = inputs["local_assessments"][story_id]
        candidates = [
            normalize_genre(value)
            for value in metadata_assessment["result"]["target_candidates"]
        ]
        opus_genre = normalize_genre(opus_assessment["result"]["detected_genre"])
        local_genre = normalize_genre(local_assessment["result"]["detected_genre"])
        category, multi_label = classify(candidates, opus_genre, local_genre)
        candidate_set = set(candidates)
        row = {
            "story_id": story_id,
            "story_path": metadata_record.get("story_path"),
            "title": metadata_record.get("title"),
            "gutenberg_id": metadata_record.get("gutenberg_id"),
            "metadata_candidates": candidates,
            "metadata_primary": candidates[0],
            "metadata_multi_label": multi_label,
            "opus_genre": opus_genre,
            "opus_confidence": opus_assessment["result"].get(
                "detected_genre_confidence"
            ),
            "local_genre": local_genre,
            "local_confidence": local_assessment["result"].get(
                "detected_genre_confidence"
            ),
            "metadata_opus_agree": opus_genre in candidate_set,
            "metadata_local_agree": local_genre in candidate_set,
            "models_agree": opus_genre == local_genre,
            "all_three_agree": category == "all_three_agree",
            "agreement_category": category,
        }
        rows.append(row)
    return rows


def _rate(count: int, total: int) -> float:
    return round(count / total, 6) if total else 0.0


def build_summary(
    rows: list[dict[str, Any]], inputs: dict[str, Any], paths: dict[str, Path]
) -> dict[str, Any]:
    total = len(rows)
    category_counts = Counter(row["agreement_category"] for row in rows)
    multi_label_count = sum(row["metadata_multi_label"] for row in rows)
    pairwise = {
        "metadata_opus": sum(row["metadata_opus_agree"] for row in rows),
        "metadata_local": sum(row["metadata_local_agree"] for row in rows),
        "models": sum(row["models_agree"] for row in rows),
        "all_three": sum(row["all_three_agree"] for row in rows),
    }
    per_genre: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"stories": 0, "category_counts": {}}
    )
    for row in rows:
        genre = row["metadata_primary"]
        per_genre[genre]["stories"] += 1
        counts = per_genre[genre]["category_counts"]
        counts[row["agreement_category"]] = counts.get(row["agreement_category"], 0) + 1
    return {
        "comparison_version": COMPARISON_VERSION,
        "generated_at": _derived_timestamp(inputs),
        "input_record_counts": {
            "metadata": len(inputs["metadata"]),
            "opus": len(inputs["opus"]),
            "local": len(inputs["local"]),
        },
        "matched_story_count": total,
        "category_counts": dict(sorted(category_counts.items())),
        "pairwise_agreement": {
            name: {"count": count, "rate": _rate(count, total)}
            for name, count in pairwise.items()
        },
        "metadata_multi_label": {
            "count": multi_label_count,
            "rate": _rate(multi_label_count, total),
        },
        "per_metadata_primary_genre": {
            genre: per_genre[genre] for genre in sorted(per_genre)
        },
        "input_validation": {"status": "passed", "diagnostics": []},
        "provenance": {
            "metadata_label": "gutenberg_metadata_rules",
            "opus_model": EXPECTED_MODELS["opus"],
            "local_model": EXPECTED_MODELS["local"],
            "opus_run_ids": sorted(
                {
                    a.get("run_id")
                    for a in inputs["opus_assessments"].values()
                    if a.get("run_id")
                }
            ),
            "local_run_ids": sorted(
                {
                    a.get("run_id")
                    for a in inputs["local_assessments"].values()
                    if a.get("run_id")
                }
            ),
        },
        "source_paths": {
            name: _relative_or_absolute(path, _repository_root())
            for name, path in paths.items()
        },
        "source_sha256": inputs["hashes"],
    }


def build_markdown(rows: list[dict[str, Any]], summary: dict[str, Any]) -> str:
    lines = [
        "# Three-way genre evidence comparison",
        "",
        "This report compares the existing Gutenberg metadata-rule candidates, Claude Opus `model_detect` assessments, and local `gpt-oss:20b` `model_detect` assessments for the same 146 stories. No source is treated as ground truth; disagreement is evidence for later review, not an adjudication.",
        "",
        "## Methodology and limitations",
        "",
        "Records are joined by LCATS story ID after strict validation of JSONL structure, duplicate IDs, matching ID sets, model provenance, and distinct source hashes. Genre aliases are normalized to a stable lowercase vocabulary. Multi-label metadata remains an orthogonal flag; its candidate set is used for agreement checks.",
        "",
        "## Inputs",
        "",
        f"- Matched stories: **{summary['matched_story_count']}**",
        f"- Metadata source: `{summary['source_paths']['metadata']}`",
        f"- Claude Opus source (`{summary['provenance']['opus_model']}`): `{summary['source_paths']['opus']}`",
        f"- Local source (`{summary['provenance']['local_model']}`): `{summary['source_paths']['local']}`",
        "",
        "## Aggregate results",
        "",
        "| Category | Count |",
        "| --- | ---: |",
    ]
    for category, count in summary["category_counts"].items():
        lines.append(f"| `{category}` | {count} |")
    lines.extend(["", "| Pairwise measure | Count | Rate |", "| --- | ---: | ---: |"])
    for name, value in summary["pairwise_agreement"].items():
        lines.append(f"| `{name}` | {value['count']} | {value['rate']:.2%} |")
    lines.extend(
        [
            "",
            f"Metadata multi-label stories: **{summary['metadata_multi_label']['count']}** ({summary['metadata_multi_label']['rate']:.2%}).",
            "",
            "## Per-metadata-primary genre",
            "",
            "| Genre | Stories | Category counts |",
            "| --- | ---: | --- |",
        ]
    )
    for genre, value in summary["per_metadata_primary_genre"].items():
        counts = ", ".join(
            f"`{key}`={count}"
            for key, count in sorted(value["category_counts"].items())
        )
        lines.append(f"| {genre} | {value['stories']} | {counts} |")
    lines.extend(["", "## Disagreements", ""])
    disagreements = [row for row in rows if not row["all_three_agree"]]
    if not disagreements:
        lines.append("No disagreements.")
    else:
        lines.extend(
            [
                "| Story | Metadata candidates | Opus | Local | Category |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for row in disagreements:
            lines.append(
                f"| `{row['story_id']}` | {', '.join(row['metadata_candidates'])} | {row['opus_genre']} | {row['local_genre']} | `{row['agreement_category']}` |"
            )
    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            "These results describe agreement and disagreement among evidence sources. They do not select a ground-truth genre, adjudicate individual stories, or replace the underlying historical evidence files.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(
    inputs: dict[str, Any], paths: dict[str, Path], output_dir: Path
) -> None:
    rows = build_rows(inputs)
    summary = build_summary(rows, inputs, paths)
    output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = output_dir / "three_way_genre_comparison.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
    (output_dir / "three_way_genre_comparison_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "three_way_genre_comparison_report.md").write_text(
        build_markdown(rows, summary), encoding="utf-8"
    )


def write_failure_summary(
    paths: dict[str, Path], output_dir: Path, diagnostics: list[str]
) -> None:
    summary = {
        "comparison_version": COMPARISON_VERSION,
        "input_validation": {"status": "failed", "diagnostics": diagnostics},
        "matched_story_count": 0,
        "source_paths": {
            name: _relative_or_absolute(path, _repository_root())
            for name, path in paths.items()
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "three_way_genre_comparison_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    root = Path(__file__).resolve().parent / "results" / "full_scan"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--metadata", type=Path, default=root / "genre_balanced_manifest.jsonl"
    )
    parser.add_argument("--opus", type=Path, default=root / "validation_results.jsonl")
    parser.add_argument(
        "--local",
        type=Path,
        default=root / "validation_gpt_oss_20b_http_localhost_11434_v1_results.jsonl",
    )
    parser.add_argument("--output-dir", type=Path, default=root)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    paths = {"metadata": args.metadata, "opus": args.opus, "local": args.local}
    output_diagnostics = _preflight_outputs(args.output_dir, paths.values())
    if output_diagnostics:
        print("output validation failed:", file=sys.stderr)
        for diagnostic in output_diagnostics:
            print(f"- {diagnostic}", file=sys.stderr)
        return 2
    try:
        inputs = validate_inputs(args.metadata, args.opus, args.local)
        write_outputs(inputs, paths, args.output_dir)
    except InputValidationError as exc:
        write_failure_summary(paths, args.output_dir, exc.diagnostics)
        print("input validation failed:", file=sys.stderr)
        for diagnostic in exc.diagnostics:
            print(f"- {diagnostic}", file=sys.stderr)
        return 2
    print(
        f"wrote three-way comparison for {EXPECTED_STORY_COUNT} stories to {args.output_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
