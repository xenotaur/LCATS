"""Batch runner for standalone linguistic feature sidecars."""

from __future__ import annotations

import dataclasses
import pathlib
import sys
from typing import Any, Iterable, Optional

from lcats.analysis.corpus import cli as corpus_cli
from lcats.analysis.corpus import discovery
from lcats.analysis.linguistics import lexicon
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
    lexicon_path: Optional[pathlib.Path] = None

    def to_dict(self) -> dict[str, Any]:
        data = {
            "story_path": self.story_path.as_posix(),
            "sidecar_path": self.sidecar_path.as_posix(),
            "status": self.status,
            "message": self.message,
        }
        if self.detail_path is not None:
            data["detail_path"] = self.detail_path.as_posix()
        if self.lexicon_path is not None:
            data["lexicon_path"] = self.lexicon_path.as_posix()
        return data


@dataclasses.dataclass(frozen=True)
class StoryOutputPaths:
    """Target sidecar paths for one story."""

    sidecar_path: pathlib.Path
    detail_path: Optional[pathlib.Path] = None
    lexicon_path: Optional[pathlib.Path] = None


@dataclasses.dataclass(frozen=True)
class RunSummary:
    """Machine-readable summary for a linguistic sidecar batch run."""

    results: tuple[StoryRunResult, ...]
    backend_name: str
    model_name: str
    existing: str
    include_token_detail: bool
    token_detail_version: str
    include_lexicon: bool = False
    output_root: Optional[pathlib.Path] = None

    @property
    def clean(self) -> bool:
        return not any(result.status == STATUS_FAILED for result in self.results)

    def to_dict(self) -> dict[str, Any]:
        counts: dict[str, int] = {}
        for result in self.results:
            counts[result.status] = counts.get(result.status, 0) + 1
        data = {
            "schema_version": "linguistics-run-summary-v1",
            "backend_name": self.backend_name,
            "model_name": self.model_name,
            "existing": self.existing,
            "include_token_detail": self.include_token_detail,
            "token_detail_version": self.token_detail_version,
            "include_lexicon": self.include_lexicon,
            "counts": counts,
            "results": [result.to_dict() for result in self.results],
        }
        if self.output_root is not None:
            data["output_root"] = self.output_root.as_posix()
        return data


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
    output_root: Optional[pathlib.Path] = None,
    include_lexicon: bool = False,
) -> RunSummary:
    """Analyze stories and write sidecars with per-story failure isolation."""
    results: list[StoryRunResult] = []
    seen_sidecar_targets: set[str] = set()
    for story_path in story_paths:
        story_path = pathlib.Path(story_path)
        if output_root is not None:
            try:
                output_paths = output_paths_for_story(
                    story_path,
                    include_token_detail=options.include_token_detail,
                    include_lexicon=include_lexicon,
                    output_root=output_root,
                )
                sidecar_target = _canonical_target_key(output_paths.sidecar_path)
            except Exception as error:  # noqa: BLE001 - isolate per-story failures.
                results.append(_output_path_failure(story_path, output_root, error))
                continue
            if sidecar_target in seen_sidecar_targets:
                results.append(
                    StoryRunResult(
                        story_path=story_path,
                        sidecar_path=output_paths.sidecar_path,
                        detail_path=output_paths.detail_path,
                        lexicon_path=output_paths.lexicon_path,
                        status=STATUS_FAILED,
                        message=(
                            "multiple stories resolve to the same output sidecar "
                            "path; choose distinct story identities or separate "
                            "output roots"
                        ),
                    )
                )
                continue
            seen_sidecar_targets.add(sidecar_target)
            results.append(
                run_story(
                    story_path,
                    backend=backend,
                    options=options,
                    existing=existing,
                    dry_run=dry_run,
                    output_root=output_root,
                    include_lexicon=include_lexicon,
                )
            )
            continue
        results.append(
            run_story(
                story_path,
                backend=backend,
                options=options,
                existing=existing,
                dry_run=dry_run,
                output_root=output_root,
                include_lexicon=include_lexicon,
            )
        )
    return RunSummary(
        results=tuple(results),
        backend_name=options.backend_name,
        model_name=options.model_name,
        existing=existing,
        include_token_detail=options.include_token_detail,
        token_detail_version=options.token_detail_version,
        include_lexicon=include_lexicon,
        output_root=pathlib.Path(output_root) if output_root is not None else None,
    )


def run_story(
    story_path: pathlib.Path,
    *,
    backend: Any,
    options: sidecar.LinguisticsOptions,
    existing: str = EXISTING_SKIP,
    dry_run: bool = False,
    output_root: Optional[pathlib.Path] = None,
    include_lexicon: bool = False,
) -> StoryRunResult:
    """Analyze one story and write its linguistic sidecar."""
    try:
        output_paths = output_paths_for_story(
            story_path,
            include_token_detail=options.include_token_detail,
            include_lexicon=include_lexicon,
            output_root=output_root,
        )
    except Exception as error:  # noqa: BLE001 - isolate per-story failures.
        return _output_path_failure(story_path, output_root, error)
    sidecar_path = output_paths.sidecar_path
    detail_path = output_paths.detail_path
    lexicon_path = output_paths.lexicon_path
    if include_lexicon and (
        not options.include_token_detail
        or options.token_detail_version != sidecar.TOKEN_DETAIL_VERSION_V2
    ):
        return StoryRunResult(
            story_path=story_path,
            sidecar_path=sidecar_path,
            detail_path=detail_path,
            lexicon_path=lexicon_path,
            status=STATUS_FAILED,
            message=(
                "lexicon output requires --include-token-detail "
                "--token-detail-version v2"
            ),
        )
    if dry_run:
        return StoryRunResult(
            story_path=story_path,
            sidecar_path=sidecar_path,
            detail_path=detail_path,
            lexicon_path=lexicon_path,
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
                lexicon_path=lexicon_path,
                expected_fingerprint=current_fingerprint,
                expected_detail_fingerprint=expected_detail_fingerprint,
                source_body=body,
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
        if lexicon_path is not None:
            if detail is None:
                raise ValueError("lexicon output requires token-detail-v2 data")
            sidecar.write_json_atomic(lexicon_path, lexicon.build_lexicon(detail))
        return StoryRunResult(
            story_path=story_path,
            sidecar_path=sidecar_path,
            detail_path=detail_path,
            lexicon_path=lexicon_path,
            status=STATUS_WRITTEN,
            message="wrote linguistic sidecar",
        )
    except Exception as error:  # noqa: BLE001 - isolate per-story failures.
        return StoryRunResult(
            story_path=story_path,
            sidecar_path=sidecar_path,
            detail_path=detail_path,
            lexicon_path=lexicon_path,
            status=STATUS_FAILED,
            message=str(error),
        )


def _existing_result(
    *,
    story_path: pathlib.Path,
    sidecar_path: pathlib.Path,
    detail_path: Optional[pathlib.Path],
    lexicon_path: Optional[pathlib.Path],
    expected_fingerprint: dict[str, Any],
    expected_detail_fingerprint: dict[str, Any],
    source_body: str,
    existing: str,
) -> Optional[StoryRunResult]:
    try:
        current = sidecar.load_json(sidecar_path)
    except Exception as error:  # noqa: BLE001
        return StoryRunResult(
            story_path=story_path,
            sidecar_path=sidecar_path,
            detail_path=detail_path,
            lexicon_path=lexicon_path,
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
            detail_path=detail_path,
            lexicon_path=lexicon_path,
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
            source_body=source_body,
            compact_sidecar=current,
        )
        if detail_result is not None:
            return detail_result
        lexicon_result = _validate_existing_lexicon(
            story_path=story_path,
            sidecar_path=sidecar_path,
            detail_path=detail_path,
            lexicon_path=lexicon_path,
        )
        if lexicon_result is not None:
            return lexicon_result
        return StoryRunResult(
            story_path=story_path,
            sidecar_path=sidecar_path,
            detail_path=detail_path,
            lexicon_path=lexicon_path,
            status=STATUS_SKIPPED,
            message="existing sidecar matches current input and options",
        )
    if existing == EXISTING_VALIDATE:
        return StoryRunResult(
            story_path=story_path,
            sidecar_path=sidecar_path,
            detail_path=detail_path,
            lexicon_path=lexicon_path,
            status=STATUS_FAILED,
            message="existing sidecar is valid but stale for current input/options",
        )
    return StoryRunResult(
        story_path=story_path,
        sidecar_path=sidecar_path,
        detail_path=detail_path,
        lexicon_path=lexicon_path,
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
        token_detail_version=summary.token_detail_version,
        include_lexicon=summary.include_lexicon,
        output_root=summary.output_root,
    )


def _canonical_target_key(path: pathlib.Path) -> str:
    """Return a stable key for comparing filesystem destinations."""
    key = pathlib.Path(path).resolve(strict=False).as_posix()
    if sys.platform in ("darwin", "win32"):
        return key.casefold()
    return key


def output_paths_for_story(
    story_path: pathlib.Path,
    *,
    include_token_detail: bool,
    include_lexicon: bool = False,
    output_root: Optional[pathlib.Path] = None,
) -> StoryOutputPaths:
    """Return compact and optional detail output paths for one story."""
    story_path = pathlib.Path(story_path)
    if output_root is None:
        output_dir = story_path.parent
    else:
        identity = pathlib.PurePosixPath(sidecar.story_identity(story_path))
        if identity.is_absolute() or any(
            part in ("", ".", "..") for part in identity.parts
        ):
            raise ValueError(
                f"story identity cannot be used as an output path: {identity}"
            )
        output_dir = pathlib.Path(output_root).joinpath(*identity.parts)
    return StoryOutputPaths(
        sidecar_path=output_dir / sidecar.SIDECAR_FILENAME,
        detail_path=(
            output_dir / sidecar.TOKEN_DETAIL_FILENAME if include_token_detail else None
        ),
        lexicon_path=(
            output_dir / lexicon.LEXICON_FILENAME if include_lexicon else None
        ),
    )


def _output_path_failure(
    story_path: pathlib.Path,
    output_root: Optional[pathlib.Path],
    error: Exception,
) -> StoryRunResult:
    fallback = (
        pathlib.Path(output_root) / sidecar.SIDECAR_FILENAME
        if output_root is not None
        else pathlib.Path(story_path).parent / sidecar.SIDECAR_FILENAME
    )
    return StoryRunResult(
        story_path=pathlib.Path(story_path),
        sidecar_path=fallback,
        status=STATUS_FAILED,
        message=f"could not resolve output path: {error}",
    )


def _validate_existing_detail(
    *,
    story_path: pathlib.Path,
    sidecar_path: pathlib.Path,
    detail_path: Optional[pathlib.Path],
    expected_fingerprint: dict[str, Any],
    source_body: str,
    compact_sidecar: dict[str, Any],
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
    validation = sidecar.validate_token_detail(
        detail, source_body=source_body, compact_sidecar=compact_sidecar
    )
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


def _validate_existing_lexicon(
    *,
    story_path: pathlib.Path,
    sidecar_path: pathlib.Path,
    detail_path: Optional[pathlib.Path],
    lexicon_path: Optional[pathlib.Path],
) -> Optional[StoryRunResult]:
    if lexicon_path is None:
        return None
    if detail_path is None:
        return StoryRunResult(
            story_path=story_path,
            sidecar_path=sidecar_path,
            lexicon_path=lexicon_path,
            status=STATUS_FAILED,
            message="lexicon output requires token detail; use --existing overwrite",
        )
    if not lexicon_path.exists():
        return StoryRunResult(
            story_path=story_path,
            sidecar_path=sidecar_path,
            detail_path=detail_path,
            lexicon_path=lexicon_path,
            status=STATUS_FAILED,
            message="existing lexicon is missing; use --existing overwrite",
        )
    try:
        detail = sidecar.load_json(detail_path)
    except Exception as error:  # noqa: BLE001
        return StoryRunResult(
            story_path=story_path,
            sidecar_path=sidecar_path,
            detail_path=detail_path,
            lexicon_path=lexicon_path,
            status=STATUS_FAILED,
            message=(
                "existing token detail is unreadable; use --existing overwrite: "
                f"{error}"
            ),
        )
    try:
        current = sidecar.load_json(lexicon_path)
    except Exception as error:  # noqa: BLE001
        return StoryRunResult(
            story_path=story_path,
            sidecar_path=sidecar_path,
            detail_path=detail_path,
            lexicon_path=lexicon_path,
            status=STATUS_FAILED,
            message=(
                "existing lexicon is unreadable; use --existing overwrite: " f"{error}"
            ),
        )
    validation = lexicon.validate_lexicon(current, source_token_detail=detail)
    if not validation.valid:
        kinds = ", ".join(finding.kind for finding in validation.findings)
        return StoryRunResult(
            story_path=story_path,
            sidecar_path=sidecar_path,
            detail_path=detail_path,
            lexicon_path=lexicon_path,
            status=STATUS_FAILED,
            message=(
                "existing lexicon is invalid; use --existing overwrite: " f"{kinds}"
            ),
        )
    if lexicon.fingerprint_for_lexicon(current) != lexicon.expected_fingerprint(detail):
        return StoryRunResult(
            story_path=story_path,
            sidecar_path=sidecar_path,
            detail_path=detail_path,
            lexicon_path=lexicon_path,
            status=STATUS_FAILED,
            message="existing lexicon differs; use --existing overwrite to replace it",
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
