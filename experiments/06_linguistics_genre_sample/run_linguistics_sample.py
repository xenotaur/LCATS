"""Run standalone linguistics over the WI-GENRE-0004 sample.

The shared linguistics runner writes sidecars beside its input story files.
This experiment therefore mirrors sampled story buckets into the experiment's
results directory before analysis, preserving the input state that produced
the output without writing generated files into ``corpora/``.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import pathlib
import shutil
import sys
from typing import Any, Iterable

# Allow `python experiments/.../run_linguistics_sample.py` from the repo root
# without requiring a prior editable install.
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "lcats" / "src"))

from lcats.analysis.linguistics import runner, sidecar  # noqa: E402

EXPERIMENT_NAME = "experiments/06_linguistics_genre_sample"
MANIFEST_PATH = (
    _REPO_ROOT
    / "experiments"
    / "05_metadata_genre_prefilter"
    / "results"
    / "full_scan"
    / "genre_balanced_manifest.jsonl"
)
CORPUS_ROOT = _REPO_ROOT / "corpora"
RESULTS_DIR = _REPO_ROOT / "experiments" / "06_linguistics_genre_sample" / "results"
COPIED_BUCKETS_DIRNAME = "copied_buckets"
STORY_LIST_FILENAME = "story-list.txt"
RUN_SUMMARY_FILENAME = "linguistics_run_summary.json"
REPORT_FILENAME = "experiment_report.json"
EXPECTED_SAMPLE_COUNT = 146


@dataclasses.dataclass(frozen=True)
class ManifestRow:
    """One selected sample row from the genre-balanced manifest."""

    story_id: str
    story_path: pathlib.Path
    selection_genre: str
    raw: dict[str, Any]


def load_manifest(
    path: pathlib.Path, *, expected_count: int | None
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
            story_path_text = _required_string(raw, "story_path", path, line_number)
            story_path = _validate_manifest_story_path(
                story_path_text, manifest_path=path, line_number=line_number
            )
            selection_genre = _required_string(
                raw, "selection_genre", path, line_number
            )
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
                    raw=raw,
                )
            )
    if expected_count is not None and len(rows) != expected_count:
        raise ValueError(
            f"{path}: expected {expected_count} manifest rows, found {len(rows)}"
        )
    return rows


def copy_sample_buckets(
    rows: Iterable[ManifestRow],
    *,
    corpus_root: pathlib.Path,
    mirror_root: pathlib.Path,
    overwrite: bool,
) -> list[pathlib.Path]:
    """Copy sampled story buckets and return copied story paths."""
    story_paths: list[pathlib.Path] = []
    corpus_root = corpus_root.resolve(strict=True)
    mirror_root = mirror_root.resolve(strict=False)
    if overwrite and mirror_root.exists():
        shutil.rmtree(mirror_root)
    for row in rows:
        source_story = _resolve_beneath(corpus_root, row.story_path)
        if not source_story.is_file():
            raise FileNotFoundError(f"source story not found: {source_story}")
        relative_bucket = row.story_path.parent
        destination_bucket = _resolve_beneath(mirror_root, relative_bucket)
        if destination_bucket.exists():
            if not overwrite:
                raise FileExistsError(
                    f"copied bucket already exists: {destination_bucket}; use --overwrite"
                )
            shutil.rmtree(destination_bucket)
        destination_bucket.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_story.parent, destination_bucket)
        story_paths.append(destination_bucket / "story.json")
    return story_paths


def write_story_list(paths: Iterable[pathlib.Path], path: pathlib.Path) -> None:
    """Write a deterministic story list."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(f"{_repo_relative(story_path)}\n" for story_path in paths)
    path.write_text(text, encoding="utf-8")


def run_sample(
    *,
    manifest_path: pathlib.Path = MANIFEST_PATH,
    corpus_root: pathlib.Path = CORPUS_ROOT,
    output_dir: pathlib.Path = RESULTS_DIR,
    backend_name: str = "spacy",
    model_name: str = "",
    smoke_count: int | None = None,
    expected_count: int | None = EXPECTED_SAMPLE_COUNT,
    overwrite: bool = False,
    existing: str = runner.EXISTING_SKIP,
    include_token_detail: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Mirror sampled buckets, run linguistics, and write summary artifacts."""
    rows = load_manifest(manifest_path, expected_count=expected_count)
    selected_rows = rows[:smoke_count] if smoke_count is not None else rows
    output_dir.mkdir(parents=True, exist_ok=True)
    mirror_root = output_dir / COPIED_BUCKETS_DIRNAME
    copied_story_paths = copy_sample_buckets(
        selected_rows,
        corpus_root=corpus_root,
        mirror_root=mirror_root,
        overwrite=overwrite,
    )
    analysis_story_paths = [_invocation_path(path) for path in copied_story_paths]
    story_list_path = output_dir / STORY_LIST_FILENAME
    write_story_list(analysis_story_paths, story_list_path)

    resolved_model_name = model_name or ("en" if backend_name == "stanza" else "")
    options = sidecar.LinguisticsOptions(
        backend_name=backend_name,
        model_name=resolved_model_name,
        include_token_detail=include_token_detail,
    )
    backend = runner.make_backend(backend_name, resolved_model_name)
    run_summary = runner.run(
        analysis_story_paths,
        backend=backend,
        options=options,
        existing=existing,
        dry_run=dry_run,
    )
    run_summary_path = output_dir / RUN_SUMMARY_FILENAME
    sidecar.write_json_atomic(run_summary_path, run_summary.to_dict())

    report = build_report(
        manifest_path=manifest_path,
        manifest_rows=rows,
        selected_rows=selected_rows,
        copied_story_paths=copied_story_paths,
        corpus_root=corpus_root,
        output_dir=output_dir,
        story_list_path=story_list_path,
        run_summary_path=run_summary_path,
        run_summary=run_summary,
        backend_name=backend_name,
        model_name=resolved_model_name,
        smoke_count=smoke_count,
        dry_run=dry_run,
    )
    sidecar.write_json_atomic(output_dir / REPORT_FILENAME, report)
    return report


def build_report(
    *,
    manifest_path: pathlib.Path,
    manifest_rows: list[ManifestRow],
    selected_rows: list[ManifestRow],
    copied_story_paths: list[pathlib.Path],
    corpus_root: pathlib.Path,
    output_dir: pathlib.Path,
    story_list_path: pathlib.Path,
    run_summary_path: pathlib.Path,
    run_summary: runner.RunSummary,
    backend_name: str,
    model_name: str,
    smoke_count: int | None,
    dry_run: bool,
) -> dict[str, Any]:
    """Build the script-level experiment report."""
    genre_counts: dict[str, int] = {}
    for row in selected_rows:
        genre_counts[row.selection_genre] = genre_counts.get(row.selection_genre, 0) + 1
    corpus_sidecars = _selected_source_sidecars(corpus_root, selected_rows)
    copied_sidecars = sorted(output_dir.glob("copied_buckets/**/linguistics.json"))
    return {
        "schema_version": "linguistics-genre-sample-report-v1",
        "experiment": EXPERIMENT_NAME,
        "manifest_path": _repo_relative(manifest_path),
        "manifest_row_count": len(manifest_rows),
        "selected_story_count": len(selected_rows),
        "smoke_count": smoke_count,
        "selection_genre_counts": dict(sorted(genre_counts.items())),
        "backend_name": backend_name,
        "model_name": model_name,
        "dry_run": dry_run,
        "copied_bucket_root": _repo_relative(output_dir / COPIED_BUCKETS_DIRNAME),
        "copied_story_count": len(copied_story_paths),
        "copied_sidecar_count": len(copied_sidecars),
        "story_list_path": _repo_relative(story_list_path),
        "run_summary_path": _repo_relative(run_summary_path),
        "run_clean": run_summary.clean,
        "run_counts": run_summary.to_dict()["counts"],
        "corpus_linguistics_sidecars_found": [
            _repo_relative(path) for path in corpus_sidecars
        ],
        "corpora_modified": bool(corpus_sidecars),
    }


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
    parser.add_argument(
        "--existing",
        choices=[
            runner.EXISTING_SKIP,
            runner.EXISTING_VALIDATE,
            runner.EXISTING_OVERWRITE,
        ],
        default=runner.EXISTING_SKIP,
    )
    parser.add_argument("--include-token-detail", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the experiment CLI."""
    args = build_parser().parse_args(argv)
    try:
        report = run_sample(
            manifest_path=args.manifest,
            corpus_root=args.corpus_root,
            output_dir=args.output_dir,
            backend_name=args.backend,
            model_name=args.model,
            smoke_count=args.smoke_count,
            expected_count=args.expected_count,
            overwrite=args.overwrite,
            existing=args.existing,
            include_token_detail=args.include_token_detail,
            dry_run=args.dry_run,
        )
    except Exception as error:  # noqa: BLE001
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["run_clean"] else 1


def _required_string(
    data: dict[str, Any], key: str, path: pathlib.Path, line_number: int
) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{path}:{line_number}: missing string field {key!r}")
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


def _selected_source_sidecars(
    corpus_root: pathlib.Path, selected_rows: Iterable[ManifestRow]
) -> list[pathlib.Path]:
    corpus_root = corpus_root.resolve(strict=True)
    paths: list[pathlib.Path] = []
    for row in selected_rows:
        source_story = _resolve_beneath(corpus_root, row.story_path)
        source_bucket = source_story.parent
        for filename in (sidecar.SIDECAR_FILENAME, sidecar.TOKEN_DETAIL_FILENAME):
            candidate = source_bucket / filename
            if candidate.exists():
                paths.append(candidate)
    return sorted(paths)


def _repo_relative(path: pathlib.Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(_REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _invocation_path(path: pathlib.Path) -> pathlib.Path:
    resolved = path.resolve()
    try:
        return pathlib.Path(resolved.relative_to(_REPO_ROOT))
    except ValueError:
        return path


if __name__ == "__main__":
    raise SystemExit(main())
