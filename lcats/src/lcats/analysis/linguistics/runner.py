"""Batch runner for standalone linguistic feature sidecars."""

from __future__ import annotations

import dataclasses
import pathlib
from typing import Any, Iterable, Optional

from lcats.analysis.corpus import cli as corpus_cli
from lcats.analysis.corpus import discovery
from lcats.analysis.linguistics import sidecar

STATUS_WRITTEN = "written"
STATUS_SKIPPED = "skipped"
STATUS_FAILED = "failed"
STATUS_DRY_RUN = "dry_run"

EXISTING_SKIP = "skip"
EXISTING_OVERWRITE = "overwrite"
EXISTING_VALIDATE = "validate"


@dataclasses.dataclass(frozen=True)
class ResolvedStoryInputs:
    """Resolved story paths plus explicit inputs that could not be found."""

    story_paths: tuple[pathlib.Path, ...]
    missing_paths: tuple[pathlib.Path, ...]


@dataclasses.dataclass(frozen=True)
class StoryRunResult:
    """Outcome for one story in a linguistic sidecar run."""

    story_path: pathlib.Path
    sidecar_path: pathlib.Path
    status: str
    message: str = ""
    detail_path: Optional[pathlib.Path] = None

    def to_dict(self) -> dict[str, Any]:
        data = {
            "story_path": self.story_path.as_posix(),
            "sidecar_path": self.sidecar_path.as_posix(),
            "status": self.status,
            "message": self.message,
        }
        if self.detail_path is not None:
            data["detail_path"] = self.detail_path.as_posix()
        return data


@dataclasses.dataclass(frozen=True)
class RunSummary:
    """Machine-readable summary for a linguistic sidecar batch run."""

    results: tuple[StoryRunResult, ...]
    backend_name: str
    model_name: str
    existing: str
    include_token_detail: bool

    @property
    def clean(self) -> bool:
        return not any(result.status == STATUS_FAILED for result in self.results)

    def to_dict(self) -> dict[str, Any]:
        counts: dict[str, int] = {}
        for result in self.results:
            counts[result.status] = counts.get(result.status, 0) + 1
        return {
            "schema_version": "linguistics-run-summary-v1",
            "backend_name": self.backend_name,
            "model_name": self.model_name,
            "existing": self.existing,
            "include_token_detail": self.include_token_detail,
            "counts": counts,
            "results": [result.to_dict() for result in self.results],
        }


def make_backend(name: str, model_name: str = "") -> Any:
    """Construct an NLP backend by name with clear missing dependency errors."""
    if name == "fake":
        from lcats.analysis.event_role_world import nlp_backend

        return nlp_backend.FakeNLPBackend()
    if name == "spacy":
        from lcats.analysis.event_role_world import nlp_backend

        try:
            if model_name:
                return nlp_backend.SpacyBackend(model_name=model_name)
            return nlp_backend.SpacyBackend()
        except ImportError as error:
            raise RuntimeError(
                "spaCy is not installed; install lcats[nlp] or install spacy"
            ) from error
        except OSError as error:
            requested = model_name or "en_core_web_sm"
            raise RuntimeError(
                f"spaCy model {requested!r} is unavailable; install it with "
                f"`python -m spacy download {requested}`"
            ) from error
    if name == "stanza":
        from lcats.analysis.event_role_world import nlp_backend

        try:
            return nlp_backend.StanzaBackend(lang=model_name or "en")
        except ImportError as error:
            raise RuntimeError(
                "Stanza is not installed; install lcats[nlp] or install stanza"
            ) from error
        except Exception as error:  # noqa: BLE001 - Stanza model load errors vary.
            requested = model_name or "en"
            raise RuntimeError(
                f"Stanza model {requested!r} is unavailable; download it with "
                f"`python -c \"import stanza; stanza.download('{requested}')\"`"
            ) from error
    raise ValueError(f"Unknown NLP backend name: {name!r}")


def resolve_story_paths(
    inputs: Iterable[pathlib.Path],
    *,
    story_list_files: Iterable[pathlib.Path] = (),
) -> list[pathlib.Path]:
    """Resolve explicit stories, buckets, and story-list files deterministically."""
    resolved = resolve_story_inputs(inputs, story_list_files=story_list_files)
    return list(resolved.story_paths)


def resolve_story_inputs(
    inputs: Iterable[pathlib.Path],
    *,
    story_list_files: Iterable[pathlib.Path] = (),
) -> ResolvedStoryInputs:
    """Resolve story inputs and preserve missing explicit paths as failures."""
    candidates = list(inputs)
    for list_file in story_list_files:
        if pathlib.Path(list_file).exists():
            candidates.extend(_read_story_list(pathlib.Path(list_file)))
        else:
            candidates.append(pathlib.Path(list_file))
    seen: set[pathlib.Path] = set()
    story_paths: list[pathlib.Path] = []
    missing_paths: list[pathlib.Path] = []
    for candidate in candidates:
        candidate_path = pathlib.Path(candidate)
        if not candidate_path.exists():
            missing_paths.append(candidate_path)
            continue
        for path in discovery.find_json_files(
            [candidate_path], ignore_dir_names=("cache",)
        ):
            normalized = pathlib.Path(path)
            if normalized not in seen:
                seen.add(normalized)
                story_paths.append(normalized)
    return ResolvedStoryInputs(
        story_paths=tuple(story_paths), missing_paths=tuple(missing_paths)
    )


def run(
    story_paths: Iterable[pathlib.Path],
    *,
    backend: Any,
    options: sidecar.LinguisticsOptions,
    existing: str = EXISTING_SKIP,
    dry_run: bool = False,
) -> RunSummary:
    """Analyze stories and write sidecars with per-story failure isolation."""
    results: list[StoryRunResult] = []
    for story_path in story_paths:
        results.append(
            run_story(
                pathlib.Path(story_path),
                backend=backend,
                options=options,
                existing=existing,
                dry_run=dry_run,
            )
        )
    return RunSummary(
        results=tuple(results),
        backend_name=options.backend_name,
        model_name=options.model_name,
        existing=existing,
        include_token_detail=options.include_token_detail,
    )


def run_story(
    story_path: pathlib.Path,
    *,
    backend: Any,
    options: sidecar.LinguisticsOptions,
    existing: str = EXISTING_SKIP,
    dry_run: bool = False,
) -> StoryRunResult:
    """Analyze one story and write its linguistic sidecar."""
    sidecar_path = story_path.parent / sidecar.SIDECAR_FILENAME
    detail_path = (
        story_path.parent / sidecar.TOKEN_DETAIL_FILENAME
        if options.include_token_detail
        else None
    )
    if dry_run:
        return StoryRunResult(
            story_path=story_path,
            sidecar_path=sidecar_path,
            detail_path=detail_path,
            status=STATUS_DRY_RUN,
            message="would analyze story",
        )

    try:
        story_data = corpus_cli.read_story_data(story_path)
        body = corpus_cli.coerce_story_text(story_data.get("body", ""))
        current_options = options
        if sidecar_path.exists() and existing != EXISTING_OVERWRITE:
            current_fingerprint = sidecar.expected_fingerprint(
                story_data={**story_data, "body": body},
                story_path=story_path,
                backend=backend,
                options=current_options,
            )
            expected_detail_fingerprint = sidecar.expected_detail_fingerprint(
                story_data={**story_data, "body": body},
                story_path=story_path,
                backend=backend,
                options=current_options,
            )
            existing_result = _existing_result(
                story_path=story_path,
                sidecar_path=sidecar_path,
                detail_path=detail_path,
                expected_fingerprint=current_fingerprint,
                expected_detail_fingerprint=expected_detail_fingerprint,
                existing=existing,
            )
            if existing_result is not None:
                return existing_result

        computed_sidecar, detail = sidecar.build_sidecar(
            story_data={**story_data, "body": body},
            story_path=story_path,
            backend=backend,
            options=current_options,
        )

        sidecar.write_json_atomic(sidecar_path, computed_sidecar)
        if detail_path is not None and detail is not None:
            sidecar.write_json_atomic(detail_path, detail)
        return StoryRunResult(
            story_path=story_path,
            sidecar_path=sidecar_path,
            detail_path=detail_path,
            status=STATUS_WRITTEN,
            message="wrote linguistic sidecar",
        )
    except Exception as error:  # noqa: BLE001 - isolate per-story failures.
        return StoryRunResult(
            story_path=story_path,
            sidecar_path=sidecar_path,
            detail_path=detail_path,
            status=STATUS_FAILED,
            message=str(error),
        )


def _existing_result(
    *,
    story_path: pathlib.Path,
    sidecar_path: pathlib.Path,
    detail_path: Optional[pathlib.Path],
    expected_fingerprint: dict[str, Any],
    expected_detail_fingerprint: dict[str, Any],
    existing: str,
) -> Optional[StoryRunResult]:
    try:
        current = sidecar.load_json(sidecar_path)
    except Exception as error:  # noqa: BLE001
        return StoryRunResult(
            story_path=story_path,
            sidecar_path=sidecar_path,
            status=STATUS_FAILED,
            message=(
                "existing sidecar is unreadable; use --existing overwrite: " f"{error}"
            ),
        )
    validation = sidecar.validate_sidecar(current)
    if not validation.valid:
        kinds = ", ".join(finding.kind for finding in validation.findings)
        return StoryRunResult(
            story_path=story_path,
            sidecar_path=sidecar_path,
            status=STATUS_FAILED,
            message=(
                "existing sidecar is invalid; use --existing overwrite: " f"{kinds}"
            ),
        )
    if sidecar.fingerprint_for_sidecar(current) == expected_fingerprint:
        detail_result = _validate_existing_detail(
            story_path=story_path,
            sidecar_path=sidecar_path,
            detail_path=detail_path,
            expected_fingerprint=expected_detail_fingerprint,
        )
        if detail_result is not None:
            return detail_result
        return StoryRunResult(
            story_path=story_path,
            sidecar_path=sidecar_path,
            detail_path=detail_path,
            status=STATUS_SKIPPED,
            message="existing sidecar matches current input and options",
        )
    if existing == EXISTING_VALIDATE:
        return StoryRunResult(
            story_path=story_path,
            sidecar_path=sidecar_path,
            status=STATUS_FAILED,
            message="existing sidecar is valid but stale for current input/options",
        )
    return StoryRunResult(
        story_path=story_path,
        sidecar_path=sidecar_path,
        status=STATUS_FAILED,
        message="existing sidecar differs; use --existing overwrite to replace it",
    )


def missing_input_results(paths: Iterable[pathlib.Path]) -> tuple[StoryRunResult, ...]:
    """Return failed result records for explicit inputs that do not exist."""
    return tuple(
        StoryRunResult(
            story_path=pathlib.Path(path),
            sidecar_path=pathlib.Path(path),
            status=STATUS_FAILED,
            message="input path does not exist",
        )
        for path in paths
    )


def with_prepended_results(
    summary: RunSummary, extra_results: Iterable[StoryRunResult]
) -> RunSummary:
    """Return ``summary`` with extra results prepended."""
    return RunSummary(
        results=tuple(extra_results) + summary.results,
        backend_name=summary.backend_name,
        model_name=summary.model_name,
        existing=summary.existing,
        include_token_detail=summary.include_token_detail,
    )


def _validate_existing_detail(
    *,
    story_path: pathlib.Path,
    sidecar_path: pathlib.Path,
    detail_path: Optional[pathlib.Path],
    expected_fingerprint: dict[str, Any],
) -> Optional[StoryRunResult]:
    if detail_path is None:
        return None
    if not detail_path.exists():
        return StoryRunResult(
            story_path=story_path,
            sidecar_path=sidecar_path,
            detail_path=detail_path,
            status=STATUS_FAILED,
            message="existing token detail is missing; use --existing overwrite",
        )
    try:
        detail = sidecar.load_json(detail_path)
    except Exception as error:  # noqa: BLE001
        return StoryRunResult(
            story_path=story_path,
            sidecar_path=sidecar_path,
            detail_path=detail_path,
            status=STATUS_FAILED,
            message=(
                "existing token detail is unreadable; use --existing overwrite: "
                f"{error}"
            ),
        )
    validation = sidecar.validate_token_detail(detail)
    if not validation.valid:
        kinds = ", ".join(finding.kind for finding in validation.findings)
        return StoryRunResult(
            story_path=story_path,
            sidecar_path=sidecar_path,
            detail_path=detail_path,
            status=STATUS_FAILED,
            message=(
                "existing token detail is invalid; use --existing overwrite: "
                f"{kinds}"
            ),
        )
    if sidecar.fingerprint_for_sidecar(detail) != expected_fingerprint:
        return StoryRunResult(
            story_path=story_path,
            sidecar_path=sidecar_path,
            detail_path=detail_path,
            status=STATUS_FAILED,
            message=(
                "existing token detail differs; use --existing overwrite to replace it"
            ),
        )
    return None


def _read_story_list(path: pathlib.Path) -> list[pathlib.Path]:
    base = path.parent
    results: list[pathlib.Path] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        candidate = pathlib.Path(line)
        if not candidate.is_absolute():
            candidate = base / candidate
        results.append(candidate)
    return results
