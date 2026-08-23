"""Run standalone linguistics over the current LCATS corpora.

The shared linguistics runner writes sidecars beside its input story files.
This experiment therefore snapshots corpus story buckets into the experiment's
results directory before analysis, preserving the input state that produced the
output without writing generated files into ``corpora/``.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import time
from typing import Any, Iterable

# Allow `python experiments/.../run_linguistics_corpora.py` from the repo root
# without requiring a prior editable install.
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "lcats" / "src"))

from lcats.analysis.corpus import cli as corpus_cli  # noqa: E402
from lcats.analysis.linguistics import runner, sidecar  # noqa: E402

EXPERIMENT_NAME = "experiments/07_linguistics_corpora"
CORPUS_ROOT = _REPO_ROOT / "corpora"
RESULTS_DIR = _REPO_ROOT / "experiments" / "07_linguistics_corpora" / "results"
COPIED_BUCKETS_DIRNAME = "copied_buckets"
STORY_LIST_FILENAME = "story-list.txt"
SNAPSHOT_MANIFEST_FILENAME = "snapshot_manifest.json"
RUN_SUMMARY_FILENAME = "linguistics_run_summary.json"
REPORT_FILENAME = "experiment_report.json"


@dataclasses.dataclass(frozen=True)
class StorySnapshot:
    """One source story and its copied experiment-local counterpart."""

    story_id: str
    source_story_path: pathlib.Path
    copied_story_path: pathlib.Path
    source_story_sha256: str
    copied_story_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "story_id": self.story_id,
            "source_story_path": _repo_relative(self.source_story_path),
            "copied_story_path": _repo_relative(self.copied_story_path),
            "source_story_sha256": self.source_story_sha256,
            "copied_story_sha256": self.copied_story_sha256,
        }


@dataclasses.dataclass(frozen=True)
class AnalysisExclusion:
    """One copied story excluded from linguistic analysis."""

    story_id: str
    story_path: pathlib.Path
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "story_id": self.story_id,
            "story_path": _repo_relative(self.story_path),
            "reason": self.reason,
        }


def discover_story_paths(corpus_root: pathlib.Path) -> list[pathlib.Path]:
    """Discover corpus story files deterministically."""
    corpus_root = corpus_root.resolve(strict=True)
    paths = [
        path
        for path in corpus_root.rglob("story.json")
        if path.is_file() and "cache" not in path.relative_to(corpus_root).parts
    ]
    return sorted(paths, key=lambda path: path.relative_to(corpus_root).as_posix())


def run_corpora(
    *,
    corpus_root: pathlib.Path = CORPUS_ROOT,
    output_dir: pathlib.Path = RESULTS_DIR,
    backend_name: str = "spacy",
    model_name: str = "",
    smoke_count: int | None = None,
    overwrite: bool = False,
    resume: bool = False,
    existing: str = runner.EXISTING_SKIP,
    include_token_detail: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Snapshot corpus buckets, run linguistics, and write summary artifacts."""
    if overwrite and resume:
        raise ValueError("choose either --overwrite or --resume, not both")
    if include_token_detail:
        raise ValueError(
            "token-detail artifacts are outside this experiment's default scope"
        )

    started = time.perf_counter()
    output_dir.mkdir(parents=True, exist_ok=True)
    mirror_root = output_dir / COPIED_BUCKETS_DIRNAME
    snapshot_path = output_dir / SNAPSHOT_MANIFEST_FILENAME
    source_story_paths = discover_story_paths(corpus_root)
    discovered_source_story_count = len(source_story_paths)
    selected_story_paths = (
        source_story_paths[:smoke_count] if smoke_count is not None else source_story_paths
    )

    if resume:
        snapshot_manifest = load_and_validate_snapshot(
            snapshot_path,
            corpus_root=corpus_root,
            mirror_root=mirror_root,
            expected_smoke_count=smoke_count,
        )
        copied_story_paths = [
            _repo_path(item["copied_story_path"])
            for item in snapshot_manifest["stories"]
        ]
        analysis_exclusions = find_analysis_exclusions(copied_story_paths)
    else:
        if snapshot_path.exists() or mirror_root.exists():
            if not overwrite:
                raise FileExistsError(
                    f"existing snapshot found under {output_dir}; use --resume "
                    "to continue it or --overwrite to rebuild it"
                )
            prune_results(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        snapshot_manifest, copied_story_paths = copy_story_buckets_and_snapshot(
            selected_story_paths,
            corpus_root=corpus_root,
            mirror_root=mirror_root,
            discovered_source_story_count=discovered_source_story_count,
            smoke_count=smoke_count,
        )
        analysis_exclusions = find_analysis_exclusions(copied_story_paths)
        snapshot_manifest["analysis_exclusions"] = [
            exclusion.to_dict() for exclusion in analysis_exclusions
        ]
        snapshot_manifest["analysis_story_count"] = len(copied_story_paths) - len(
            analysis_exclusions
        )
        sidecar.write_json_atomic(snapshot_path, snapshot_manifest)

    excluded_paths = {exclusion.story_path.resolve() for exclusion in analysis_exclusions}
    analysis_story_paths = [
        _invocation_path(path)
        for path in copied_story_paths
        if path.resolve() not in excluded_paths
    ]
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

    elapsed_seconds = time.perf_counter() - started
    report = build_report(
        snapshot_manifest=snapshot_manifest,
        corpus_root=corpus_root,
        output_dir=output_dir,
        story_list_path=story_list_path,
        run_summary_path=run_summary_path,
        run_summary=run_summary,
        backend_name=backend_name,
        model_name=resolved_model_name,
        smoke_count=smoke_count,
        resume=resume,
        overwrite=overwrite,
        dry_run=dry_run,
        elapsed_seconds=elapsed_seconds,
    )
    sidecar.write_json_atomic(output_dir / REPORT_FILENAME, report)
    return report


def copy_story_buckets_and_snapshot(
    story_paths: Iterable[pathlib.Path],
    *,
    corpus_root: pathlib.Path,
    mirror_root: pathlib.Path,
    discovered_source_story_count: int,
    smoke_count: int | None,
) -> tuple[dict[str, Any], list[pathlib.Path]]:
    """Copy story buckets and return snapshot manifest data."""
    corpus_root = corpus_root.resolve(strict=True)
    mirror_root = mirror_root.resolve(strict=False)
    copied_story_paths: list[pathlib.Path] = []
    snapshots: list[StorySnapshot] = []
    story_paths = list(story_paths)
    for source_story in story_paths:
        source_story = source_story.resolve(strict=True)
        relative_story = source_story.relative_to(corpus_root)
        destination_bucket = _resolve_beneath(mirror_root, relative_story.parent)
        destination_bucket.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_story.parent, destination_bucket)
        copied_story = destination_bucket / "story.json"
        copied_story_paths.append(copied_story)
        snapshots.append(
            StorySnapshot(
                story_id=relative_story.parent.as_posix(),
                source_story_path=source_story,
                copied_story_path=copied_story,
                source_story_sha256=_sha256_file(source_story),
                copied_story_sha256=_sha256_file(copied_story),
            )
        )

    manifest = {
        "schema_version": "linguistics-corpora-snapshot-v1",
        "experiment": EXPERIMENT_NAME,
        "source_commit": _git_commit(),
        "corpus_root": _repo_relative(corpus_root),
        "copied_bucket_root": _repo_relative(mirror_root),
        "source_story_count": discovered_source_story_count,
        "selected_story_count": len(story_paths),
        "smoke_count": smoke_count,
        "analysis_story_count": len(story_paths),
        "analysis_exclusions": [],
        "stories": [snapshot.to_dict() for snapshot in snapshots],
    }
    return manifest, copied_story_paths


def load_and_validate_snapshot(
    snapshot_path: pathlib.Path,
    *,
    corpus_root: pathlib.Path,
    mirror_root: pathlib.Path,
    expected_smoke_count: int | None,
) -> dict[str, Any]:
    """Load an existing snapshot and verify copied-story provenance."""
    if not snapshot_path.exists():
        raise FileNotFoundError(f"snapshot manifest not found: {snapshot_path}")
    data = sidecar.load_json(snapshot_path)
    if not isinstance(data, dict):
        raise ValueError(f"{snapshot_path}: expected JSON object")
    if data.get("schema_version") != "linguistics-corpora-snapshot-v1":
        raise ValueError(f"{snapshot_path}: unsupported snapshot schema")
    if data.get("experiment") != EXPERIMENT_NAME:
        raise ValueError(f"{snapshot_path}: snapshot belongs to another experiment")
    if data.get("smoke_count") != expected_smoke_count:
        raise ValueError(
            f"{snapshot_path}: smoke_count differs from requested resume mode"
        )
    if data.get("copied_bucket_root") != _repo_relative(mirror_root):
        raise ValueError(f"{snapshot_path}: copied bucket root differs")
    if data.get("corpus_root") != _repo_relative(corpus_root.resolve(strict=True)):
        raise ValueError(f"{snapshot_path}: corpus root differs")
    stories = data.get("stories")
    if not isinstance(stories, list):
        raise ValueError(f"{snapshot_path}: stories must be a list")
    for index, item in enumerate(stories):
        if not isinstance(item, dict):
            raise ValueError(f"{snapshot_path}: stories[{index}] must be an object")
        copied_story_path = _repo_path(_required_string(item, "copied_story_path"))
        copied_hash = _required_string(item, "copied_story_sha256")
        if not copied_story_path.is_file():
            raise FileNotFoundError(f"copied story missing: {copied_story_path}")
        if _sha256_file(copied_story_path) != copied_hash:
            raise ValueError(f"copied story hash mismatch: {copied_story_path}")
        source_hash = _required_string(item, "source_story_sha256")
        if copied_hash != source_hash:
            raise ValueError(
                f"copied story no longer matches source snapshot: {copied_story_path}"
            )
    if data.get("selected_story_count") != len(stories):
        raise ValueError(f"{snapshot_path}: selected_story_count differs from stories")
    exclusions = [exclusion.to_dict() for exclusion in find_analysis_exclusions(
        [_repo_path(item["copied_story_path"]) for item in stories]
    )]
    if data.get("analysis_exclusions", []) != exclusions:
        raise ValueError(f"{snapshot_path}: analysis exclusions differ")
    if data.get("analysis_story_count") != len(stories) - len(exclusions):
        raise ValueError(f"{snapshot_path}: analysis_story_count differs")
    return data


def find_analysis_exclusions(story_paths: Iterable[pathlib.Path]) -> list[AnalysisExclusion]:
    """Return copied stories that should not be analyzed as observations."""
    exclusions: list[AnalysisExclusion] = []
    for story_path in story_paths:
        story_path = pathlib.Path(story_path)
        try:
            story_data = corpus_cli.read_story_data(story_path)
        except Exception:  # noqa: BLE001 - runner records malformed stories as failures.
            continue
        body = corpus_cli.coerce_story_text(story_data.get("body", ""))
        if not body.strip():
            exclusions.append(
                AnalysisExclusion(
                    story_id=sidecar.story_identity(story_path),
                    story_path=story_path,
                    reason="empty_body",
                )
            )
    return exclusions


def prune_results(output_dir: pathlib.Path) -> None:
    """Remove stale generated artifacts before rebuilding a snapshot."""
    for path in (
        output_dir / COPIED_BUCKETS_DIRNAME,
        output_dir / STORY_LIST_FILENAME,
        output_dir / SNAPSHOT_MANIFEST_FILENAME,
        output_dir / RUN_SUMMARY_FILENAME,
        output_dir / REPORT_FILENAME,
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


def build_report(
    *,
    snapshot_manifest: dict[str, Any],
    corpus_root: pathlib.Path,
    output_dir: pathlib.Path,
    story_list_path: pathlib.Path,
    run_summary_path: pathlib.Path,
    run_summary: runner.RunSummary,
    backend_name: str,
    model_name: str,
    smoke_count: int | None,
    resume: bool,
    overwrite: bool,
    dry_run: bool,
    elapsed_seconds: float,
) -> dict[str, Any]:
    """Build the script-level experiment report."""
    copied_sidecars = sorted(output_dir.glob("copied_buckets/**/linguistics.json"))
    corpus_sidecars = _corpus_linguistics_sidecars(corpus_root)
    failures = [
        result.to_dict()
        for result in run_summary.results
        if result.status == runner.STATUS_FAILED
    ]
    return {
        "schema_version": "linguistics-corpora-report-v1",
        "experiment": EXPERIMENT_NAME,
        "source_commit": snapshot_manifest["source_commit"],
        "snapshot_manifest_path": _repo_relative(output_dir / SNAPSHOT_MANIFEST_FILENAME),
        "source_story_count": snapshot_manifest["source_story_count"],
        "selected_story_count": snapshot_manifest["selected_story_count"],
        "analysis_story_count": snapshot_manifest["analysis_story_count"],
        "analysis_exclusion_count": len(snapshot_manifest["analysis_exclusions"]),
        "analysis_exclusions": snapshot_manifest["analysis_exclusions"],
        "smoke_count": smoke_count,
        "backend_name": backend_name,
        "model_name": model_name,
        "resume": resume,
        "overwrite": overwrite,
        "dry_run": dry_run,
        "elapsed_seconds": round(elapsed_seconds, 3),
        "copied_bucket_root": _repo_relative(output_dir / COPIED_BUCKETS_DIRNAME),
        "copied_story_count": len(snapshot_manifest["stories"]),
        "copied_sidecar_count": len(copied_sidecars),
        "copied_bucket_bytes": _directory_size(output_dir / COPIED_BUCKETS_DIRNAME),
        "story_list_path": _repo_relative(story_list_path),
        "run_summary_path": _repo_relative(run_summary_path),
        "run_clean": run_summary.clean,
        "run_counts": run_summary.to_dict()["counts"],
        "failures": failures,
        "corpus_linguistics_sidecars_found": [
            _repo_relative(path) for path in corpus_sidecars
        ],
        "corpora_modified": bool(corpus_sidecars),
    }


def build_parser() -> argparse.ArgumentParser:
    """Build the experiment CLI parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-root", type=pathlib.Path, default=CORPUS_ROOT)
    parser.add_argument("--output-dir", type=pathlib.Path, default=RESULTS_DIR)
    parser.add_argument(
        "--backend", choices=["spacy", "stanza", "fake"], default="spacy"
    )
    parser.add_argument("--model", default="")
    parser.add_argument("--smoke-count", type=int)
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
    parser.add_argument("--include-token-detail", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the experiment CLI."""
    args = build_parser().parse_args(argv)
    try:
        report = run_corpora(
            corpus_root=args.corpus_root,
            output_dir=args.output_dir,
            backend_name=args.backend,
            model_name=args.model,
            smoke_count=args.smoke_count,
            overwrite=args.overwrite,
            resume=args.resume,
            existing=args.existing,
            include_token_detail=args.include_token_detail,
            dry_run=args.dry_run,
        )
    except Exception as error:  # noqa: BLE001
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["run_clean"] else 1


def _required_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"missing string field {key!r}")
    return value


def _resolve_beneath(root: pathlib.Path, relative_path: pathlib.Path) -> pathlib.Path:
    resolved = (root / relative_path).resolve(strict=False)
    if resolved != root and root not in resolved.parents:
        raise ValueError(f"path escapes configured root: {relative_path}")
    return resolved


def _corpus_linguistics_sidecars(corpus_root: pathlib.Path) -> list[pathlib.Path]:
    corpus_root = corpus_root.resolve(strict=True)
    paths = [
        path
        for path in corpus_root.rglob("linguistics*.json")
        if path.name in (sidecar.SIDECAR_FILENAME, sidecar.TOKEN_DETAIL_FILENAME)
    ]
    return sorted(paths, key=lambda path: path.relative_to(corpus_root).as_posix())


def _directory_size(path: pathlib.Path) -> int:
    if not path.exists():
        return 0
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def _sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


if __name__ == "__main__":
    raise SystemExit(main())
