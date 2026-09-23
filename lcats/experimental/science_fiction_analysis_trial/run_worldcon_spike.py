"""Run the bounded Worldcon Knight/Novum spike.

This experiment-local runner is deliberately narrower than the governed Phase 2
pilot. It can run a no-cost fake/local smoke first, then enforce explicit gates
before any 5-10 story sample or 146-story Worldcon-scale run.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
import pathlib
import sys
import time
from typing import Any, Iterable

from lcats.analysis.science_fiction import evidence
from lcats.analysis.science_fiction import knight
from lcats.analysis.science_fiction import models
from lcats.analysis.science_fiction import novum
from lcats.analysis.science_fiction import pipeline
from lcats.analysis.science_fiction import preparation
from lcats.llm import anthropic_backend
from lcats.llm import backend as llm_backend
from lcats.llm import openai_backend
from lcats.llm import tool_schema as tool_schema_module
from lcats.utils import checkpoint
from lcats.utils import paths
from lcats.utils import run_log

MANIFEST_VERSION = "worldcon-knight-novum-spike-manifest-v1"
SUMMARY_VERSION = "worldcon-knight-novum-spike-summary-v1"
REPORT_VERSION = "worldcon-knight-novum-spike-report-v1"
PROMPT_VERSION = "worldcon-knight-novum-spike-prompt-v2"
EVIDENCE_STAGE = "sf_evidence"
KNIGHT_STAGE = "sf_knight"
SUVIN_STAGE = "sf_suvin_novum"
EVIDENCE_RECORD_STAGE = "evidence"
KNIGHT_RECORD_STAGE = "knight"
SUVIN_RECORD_STAGE = "suvin_novum"
EVIDENCE_TOOL_NAME = "record_science_fiction_evidence"
KNIGHT_TOOL_NAME = "record_knight_adjudication"
SUVIN_TOOL_NAME = "record_suvin_novum_adjudication"
DEFAULT_MANIFEST = (
    pathlib.Path(__file__).resolve().parent
    / "manifests"
    / "worldcon_spike_manifest.json"
)
DEFAULT_RESULTS_ROOT = pathlib.Path(__file__).resolve().parent / "results" / (
    "worldcon_spike"
)
DEFAULT_MODEL = "fake-worldcon-spike"
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TEMPERATURE = 0.0
FULL_SAMPLE_LIMIT = 146
SMOKE_MODE = "smoke"
SAMPLE_MODE = "sample"
FULL_MODE = "full"
FAKE_BACKEND = "fake"
OPENAI_BACKEND = "openai"
ANTHROPIC_BACKEND = "anthropic"
OPENAI_COMPATIBLE_BACKEND = "openai-compatible"


@dataclasses.dataclass(frozen=True)
class SpikeStory:
    """One story selected for a spike run."""

    story_id: str
    story_path: str
    title: str
    selection_genre: str
    sample_roles: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True)
class RunGate:
    """Approval metadata for a staged spike mode."""

    mode: str
    max_stories: int
    paid_model_calls_authorized: bool = False
    estimated_cost_usd: float = 0.0
    requires_smoke_success: bool = False
    requires_full_sample_approval: bool = False
    approved_backend: str | None = None
    approved_model: str | None = None
    estimated_wall_clock_minutes: float | None = None
    stop_conditions: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True)
class SpikeManifest:
    """Loaded Worldcon spike manifest."""

    manifest_path: pathlib.Path
    work_item: str
    source_worldcon_manifest: str
    smoke_stories: tuple[SpikeStory, ...]
    sample_stories: tuple[SpikeStory, ...]
    gates: dict[str, RunGate]
    version: str = MANIFEST_VERSION


@dataclasses.dataclass(frozen=True)
class RunnerOptions:
    """Runtime options for one spike invocation."""

    manifest_path: pathlib.Path = DEFAULT_MANIFEST
    output_root: pathlib.Path = DEFAULT_RESULTS_ROOT
    mode: str = SMOKE_MODE
    backend_kind: str = FAKE_BACKEND
    model: str = DEFAULT_MODEL
    base_url: str | None = None
    dry_run: bool = False
    smoke_summary: pathlib.Path | None = None
    approve_paid: bool = False
    approve_full_sample: bool = False
    max_stories: int | None = None
    max_tokens: int = DEFAULT_MAX_TOKENS
    temperature: float = DEFAULT_TEMPERATURE
    allow_protected_root: bool = False
    stop_on_first_failure: bool = False
    max_failures: int | None = None


@dataclasses.dataclass(frozen=True)
class StoryResult:
    """Per-story result summary emitted by the spike."""

    story_id: str
    title: str
    story_path: str
    status: str
    sidecar_path: str | None
    input_tokens: int
    output_tokens: int
    latency_seconds: float
    knight_interval: dict[str, int] | None
    qualified_novum_count: int | None
    dominant_novum_id: str | None
    failure_kind: str | None = None
    failure_message: str | None = None
    raw_response_path: str | None = None
    quarantine_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


class DeterministicSpikeBackend:
    """No-cost backend that returns story-specific structured fake output."""

    def complete(
        self,
        *,
        system: str,
        messages: list,
        model: str,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        tool: dict[str, Any] | None = None,
    ) -> llm_backend.BackendResponse:
        """Return deterministic tool output derived from the prompt payload."""

        del system, temperature, max_tokens
        payload = json.loads(messages[-1]["content"])
        result = _fake_stage_result(payload, tool)
        return llm_backend.BackendResponse(
            text="",
            tool_result=result,
            model=model,
            input_tokens=_estimate_tokens(json.dumps(payload, sort_keys=True)),
            output_tokens=_estimate_tokens(json.dumps(result, sort_keys=True)),
            raw=None,
        )


def main(argv: list[str] | None = None) -> int:
    """Run the command-line spike runner."""

    options = _options_from_args(_parse_args(argv))
    summary = run_spike(options)
    sys.stdout.write(_stable_json(summary))
    return 0 if summary["status"] in {"dry_run", "complete"} else 1


def run_spike(options: RunnerOptions) -> dict[str, Any]:
    """Run one gated Worldcon spike mode and return its summary."""

    manifest = load_manifest(options.manifest_path)
    output_root = _resolve_safe_output_root(
        options.output_root,
        allow_protected_root=options.allow_protected_root,
    )
    selected_stories = select_stories(manifest, options.mode)
    if options.max_stories is not None:
        selected_stories = selected_stories[: options.max_stories]
    _enforce_run_gate(manifest, options, selected_stories)
    plan = _plan(options, manifest, selected_stories, output_root)
    if options.dry_run:
        return _summary(
            status="dry_run",
            manifest=manifest,
            options=options,
            output_root=output_root,
            plan=plan,
            results=(),
        )

    active_backend = _make_backend(options)
    results: list[StoryResult] = []
    failures = 0
    with run_log.RunLog(
        output_root,
        filename="worldcon_spike_run_log.jsonl",
        work_item=manifest.work_item,
        mode=options.mode,
        backend_kind=options.backend_kind,
        model=options.model,
        planned_stories=len(selected_stories),
    ) as log:
        for story in selected_stories:
            log.event("story_start", story_id=story.story_id, title=story.title)
            result = _run_story(story, output_root, options, active_backend, log)
            results.append(result)
            _append_story_result(output_root, result)
            log.event(
                "story_end",
                story_id=story.story_id,
                status=result.status,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                failure_kind=result.failure_kind,
            )
            if result.status == "failed":
                failures += 1
                if options.stop_on_first_failure:
                    log.event(
                        "run_stopped",
                        reason="stop_on_first_failure",
                        failures=failures,
                    )
                    break
                if options.max_failures is not None and failures >= options.max_failures:
                    log.event(
                        "run_stopped",
                        reason="max_failures",
                        failures=failures,
                        max_failures=options.max_failures,
                    )
                    break
        log.event(
            "run_end",
            complete=sum(1 for item in results if item.status == "complete"),
            failed=sum(1 for item in results if item.status == "failed"),
            processed=len(results),
        )
    results = tuple(results)
    status = "complete" if all(item.status == "complete" for item in results) else (
        "failed"
    )
    summary = _summary(
        status=status,
        manifest=manifest,
        options=options,
        output_root=output_root,
        plan=plan,
        results=results,
    )
    _write_summary(output_root, summary)
    _write_report(output_root, summary)
    return summary


def load_manifest(path: pathlib.Path) -> SpikeManifest:
    """Load and validate the Worldcon spike manifest."""

    manifest_path = pathlib.Path(path)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if data.get("version") != MANIFEST_VERSION:
        raise ValueError(f"manifest version must be {MANIFEST_VERSION}")
    gates = {
        key: _load_gate(key, value)
        for key, value in data.get("gates", {}).items()
    }
    for required in (SMOKE_MODE, SAMPLE_MODE, FULL_MODE):
        if required not in gates:
            raise ValueError(f"manifest missing {required!r} gate")
    return SpikeManifest(
        manifest_path=manifest_path,
        work_item=_required_string(data, "work_item"),
        source_worldcon_manifest=_required_string(data, "source_worldcon_manifest"),
        smoke_stories=tuple(
            _load_story(item) for item in data.get("smoke_stories", ())
        ),
        sample_stories=tuple(
            _load_story(item) for item in data.get("sample_stories", ())
        ),
        gates=gates,
    )


def select_stories(manifest: SpikeManifest, mode: str) -> tuple[SpikeStory, ...]:
    """Return the deterministic story sequence for the requested mode."""

    if mode == SMOKE_MODE:
        return manifest.smoke_stories
    if mode == SAMPLE_MODE:
        return manifest.sample_stories
    if mode == FULL_MODE:
        return _load_full_sample(manifest)
    raise ValueError(f"unsupported spike mode: {mode!r}")


def _run_story(
    story: SpikeStory,
    output_root: pathlib.Path,
    options: RunnerOptions,
    active_backend: llm_backend.LLMBackend,
    log: run_log.RunLog | None = None,
) -> StoryResult:
    started = time.monotonic()
    input_tokens = 0
    output_tokens = 0
    raw_response_dir: pathlib.Path | None = None
    quarantine_path: pathlib.Path | None = None
    evidence_tool_result: Any = None
    knight_tool_result: Any = None
    suvin_tool_result: Any = None
    try:
        story_file = _repo_root() / "corpora" / story.story_path
        prepared = preparation.prepare_story_file(story_file)
        raw_response_dir = output_root / "_raw" / _checkpoint_item_id(story)

        evidence_response, evidence_tool_result, _ = _run_model_stage(
            stage=EVIDENCE_STAGE,
            story=story,
            output_root=output_root,
            options=options,
            active_backend=active_backend,
            system_prompt=_evidence_system_prompt(),
            payload=_evidence_payload(story, prepared),
            tool_schema=_evidence_tool_schema(),
            log=log,
        )
        input_tokens += evidence_response.input_tokens
        output_tokens += evidence_response.output_tokens
        evidence_set = _build_evidence_set(
            prepared,
            evidence_tool_result,
            backend=options.backend_kind,
        )
        knight_analysis, knight_response = _run_knight_stage(
            story=story,
            prepared=prepared,
            evidence_set=evidence_set,
            options=options,
            active_backend=active_backend,
            output_root=output_root,
            log=log,
        )
        input_tokens += knight_response.input_tokens
        output_tokens += knight_response.output_tokens

        suvin_analysis, suvin_response = _run_suvin_stage(
            story=story,
            prepared=prepared,
            evidence_set=evidence_set,
            options=options,
            active_backend=active_backend,
            output_root=output_root,
            log=log,
        )
        input_tokens += suvin_response.input_tokens
        output_tokens += suvin_response.output_tokens

        partial_success = _partial_success_record(knight_analysis, suvin_analysis)
        sidecar_inputs = pipeline.SidecarAssemblyInputs(
            lcats_id=story.story_id,
            story_path=story.story_path,
            story_hash=prepared.story_hash,
            evidence_sets=(evidence_set,),
            knight_analyses=(knight_analysis,),
            suvin_novum_analyses=(suvin_analysis,),
            partial_success=partial_success,
            configuration={
                "backend_kind": options.backend_kind,
                "mode": options.mode,
                "model": options.model,
                "prompt_version": PROMPT_VERSION,
                "report_version": REPORT_VERSION,
            },
        )
        assembled = pipeline.run_checkpointed_assembly(
            working_root=output_root,
            item_id=_checkpoint_item_id(story),
            inputs=sidecar_inputs,
        )
        sidecar_path = pipeline.publish_sidecar(
            output_root=output_root,
            item_id=story.story_id,
            data=assembled.data,
        )
        knight_analysis = sidecar_inputs.knight_analyses[0]
        suvin_analysis = sidecar_inputs.suvin_novum_analyses[0]
        return StoryResult(
            story_id=story.story_id,
            title=story.title,
            story_path=story.story_path,
            status="complete",
            sidecar_path=_display_path(sidecar_path),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_seconds=round(time.monotonic() - started, 3),
            knight_interval=(
                knight_analysis.interval.to_dict()
                if knight_analysis.status == "complete"
                else None
            ),
            qualified_novum_count=sum(
                1 for candidate in suvin_analysis.candidates if candidate.qualified_novum
            ) if suvin_analysis.status == "complete" else None,
            dominant_novum_id=(
                suvin_analysis.dominant_novum_id
                if suvin_analysis.status == "complete"
                else None
            ),
            raw_response_path=(
                _display_path(raw_response_dir) if raw_response_dir else None
            ),
        )
    except Exception as error:
        tool_result = (
            suvin_tool_result
            if suvin_tool_result is not None
            else knight_tool_result
            if knight_tool_result is not None
            else evidence_tool_result
        )
        if tool_result is not None:
            quarantine_path = _write_quarantine(
                output_root=output_root,
                story=story,
                error=error,
                tool_result=tool_result,
                raw_response_path=raw_response_dir,
                stage="story",
            )
            if log is not None:
                log.event(
                    "story_quarantined",
                    story_id=story.story_id,
                    quarantine_path=_display_path(quarantine_path),
                    failure_kind=type(error).__name__,
                )
        return StoryResult(
            story_id=story.story_id,
            title=story.title,
            story_path=story.story_path,
            status="failed",
            sidecar_path=None,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_seconds=round(time.monotonic() - started, 3),
            knight_interval=None,
            qualified_novum_count=None,
            dominant_novum_id=None,
            failure_kind=type(error).__name__,
            failure_message=str(error),
            raw_response_path=(
                _display_path(raw_response_dir) if raw_response_dir else None
            ),
            quarantine_path=(
                _display_path(quarantine_path) if quarantine_path else None
            ),
        )


def _append_story_result(output_root: pathlib.Path, result: StoryResult) -> pathlib.Path:
    output_root.mkdir(parents=True, exist_ok=True)
    path = output_root / "worldcon_spike_story_results.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(result.to_dict(), sort_keys=True) + "\n")
        handle.flush()
    return path


def _run_model_stage(
    *,
    stage: str,
    story: SpikeStory,
    output_root: pathlib.Path,
    options: RunnerOptions,
    active_backend: llm_backend.LLMBackend,
    system_prompt: str,
    payload: dict[str, Any],
    tool_schema: dict[str, Any],
    log: run_log.RunLog | None,
) -> tuple[llm_backend.BackendResponse, Any, pathlib.Path]:
    """Run one persisted model stage and return its raw tool result."""

    if log is not None:
        log.event("stage_start", story_id=story.story_id, stage=stage)
    try:
        response = active_backend.complete(
            system=system_prompt,
            messages=[{"role": "user", "content": _stable_json(payload)}],
            model=options.model,
            temperature=options.temperature,
            max_tokens=options.max_tokens,
            tool=tool_schema,
        )
    except llm_backend.NoToolCallError as error:
        if not error.raw_content:
            raise
        response = llm_backend.BackendResponse(
            text=error.raw_content,
            tool_result=None,
            model=options.model,
            input_tokens=error.input_tokens,
            output_tokens=error.output_tokens,
        )
        if log is not None:
            log.event(
                "no_tool_call_json_fallback",
                story_id=story.story_id,
                stage=stage,
                input_tokens=error.input_tokens,
                output_tokens=error.output_tokens,
            )
    tool_result = response.tool_result
    raw_path = _write_raw_response(
        output_root=output_root,
        story=story,
        response=response,
        tool_result=tool_result,
        stage=stage,
    )
    if log is not None:
        log.event(
            "model_response_received",
            story_id=story.story_id,
            stage=stage,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            raw_response_path=_display_path(raw_path),
        )
    if tool_result is None:
        tool_result = json.loads(response.text)
    if log is not None:
        log.event("stage_end", story_id=story.story_id, stage=stage)
    return response, tool_result, raw_path


def _write_raw_response(
    *,
    output_root: pathlib.Path,
    story: SpikeStory,
    response: llm_backend.BackendResponse,
    tool_result: Any,
    stage: str = "combined",
) -> pathlib.Path:
    path = output_root / "_raw" / _checkpoint_item_id(story) / f"{stage}.json"
    payload = {
        "story_id": story.story_id,
        "story_path": story.story_path,
        "title": story.title,
        "stage": stage,
        "model": response.model,
        "input_tokens": response.input_tokens,
        "output_tokens": response.output_tokens,
        "cache_creation_input_tokens": response.cache_creation_input_tokens,
        "cache_read_input_tokens": response.cache_read_input_tokens,
        "text": response.text,
        "tool_result": tool_result,
    }
    _write_json_atomic(path, payload)
    return path


def _write_quarantine(
    *,
    output_root: pathlib.Path,
    story: SpikeStory,
    error: Exception,
    tool_result: Any,
    raw_response_path: pathlib.Path | None,
    stage: str = "story",
) -> pathlib.Path:
    path = output_root / "_quarantine" / _checkpoint_item_id(story) / f"{stage}.json"
    payload = {
        "story_id": story.story_id,
        "story_path": story.story_path,
        "title": story.title,
        "stage": stage,
        "failure_kind": type(error).__name__,
        "failure_message": str(error),
        "raw_response_path": (
            _display_path(raw_response_path) if raw_response_path is not None else None
        ),
        "tool_result": tool_result,
    }
    _write_json_atomic(path, payload)
    return path


def _write_json_atomic(path: pathlib.Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp")
    try:
        tmp_path.write_text(_stable_json(data), encoding="utf-8")
        os.replace(tmp_path, path)
    except BaseException:
        if tmp_path.exists():
            tmp_path.unlink()
        raise


def _build_evidence_set(
    prepared: preparation.StoryPreparation,
    tool_result: Any,
    *,
    backend: str,
) -> evidence.EvidenceSet:
    if not isinstance(tool_result, dict):
        raise ValueError(
            f"{EVIDENCE_STAGE} tool_result must be an object, "
            f"got {type(tool_result).__name__}"
        )
    return evidence.build_evidence_set(
        prepared,
        _list_field(tool_result, "evidence"),
        backend=backend,
    )


def _run_knight_stage(
    *,
    story: SpikeStory,
    prepared: preparation.StoryPreparation,
    evidence_set: evidence.EvidenceSet,
    options: RunnerOptions,
    active_backend: llm_backend.LLMBackend,
    output_root: pathlib.Path,
    log: run_log.RunLog | None,
) -> tuple[models.KnightAnalysis, llm_backend.BackendResponse]:
    response = _empty_response(options)
    tool_result: Any = None
    raw_path: pathlib.Path | None = None
    system_prompt = _knight_system_prompt()
    tool_schema = _knight_tool_schema()
    provenance = _provenance(
        story=story,
        options=options,
        response=response,
        parent_evidence_set_id=evidence_set.evidence_set_id,
        system_prompt=system_prompt,
        tool_schema=tool_schema,
        rubric_version=models.KNIGHT_RUBRIC_VERSION,
    )
    try:
        response, tool_result, raw_path = _run_model_stage(
            stage=KNIGHT_STAGE,
            story=story,
            output_root=output_root,
            options=options,
            active_backend=active_backend,
            system_prompt=system_prompt,
            payload=_knight_payload(story, prepared, evidence_set),
            tool_schema=tool_schema,
            log=log,
        )
        if not isinstance(tool_result, dict):
            raise ValueError(
                f"{KNIGHT_STAGE} tool_result must be an object, "
                f"got {type(tool_result).__name__}"
            )
        provenance = _provenance(
            story=story,
            options=options,
            response=response,
            parent_evidence_set_id=evidence_set.evidence_set_id,
            system_prompt=system_prompt,
            tool_schema=tool_schema,
            rubric_version=models.KNIGHT_RUBRIC_VERSION,
        )
        return (
            knight.build_analysis(
                analysis_id=f"{_stable_slug(story.story_id)}-knight-v1",
                story_hash=prepared.story_hash,
                evidence_set=evidence_set,
                decisions=_knight_decisions(tool_result, evidence_set),
                provenance=provenance,
            ),
            response,
        )
    except Exception as error:
        _record_stage_failure(
            output_root=output_root,
            story=story,
            stage=KNIGHT_STAGE,
            error=error,
            tool_result=tool_result,
            raw_path=raw_path,
            log=log,
        )
        failure = models.FailureRecord(
            stage=KNIGHT_RECORD_STAGE,
            kind=type(error).__name__,
            message=str(error),
            recoverable=True,
        )
        return (
            knight.failed_analysis(
                analysis_id=f"{_stable_slug(story.story_id)}-knight-v1",
                story_hash=prepared.story_hash,
                evidence_set_id=evidence_set.evidence_set_id,
                provenance=provenance,
                failure=failure,
            ),
            response,
        )


def _run_suvin_stage(
    *,
    story: SpikeStory,
    prepared: preparation.StoryPreparation,
    evidence_set: evidence.EvidenceSet,
    options: RunnerOptions,
    active_backend: llm_backend.LLMBackend,
    output_root: pathlib.Path,
    log: run_log.RunLog | None,
) -> tuple[models.SuvinNovumAnalysis, llm_backend.BackendResponse]:
    response = _empty_response(options)
    tool_result: Any = None
    raw_path: pathlib.Path | None = None
    system_prompt = _suvin_system_prompt()
    tool_schema = _suvin_tool_schema()
    provenance = _provenance(
        story=story,
        options=options,
        response=response,
        parent_evidence_set_id=evidence_set.evidence_set_id,
        system_prompt=system_prompt,
        tool_schema=tool_schema,
        rubric_version=models.SUVIN_RUBRIC_VERSION,
    )
    try:
        response, tool_result, raw_path = _run_model_stage(
            stage=SUVIN_STAGE,
            story=story,
            output_root=output_root,
            options=options,
            active_backend=active_backend,
            system_prompt=system_prompt,
            payload=_suvin_payload(story, prepared, evidence_set),
            tool_schema=tool_schema,
            log=log,
        )
        if not isinstance(tool_result, dict):
            raise ValueError(
                f"{SUVIN_STAGE} tool_result must be an object, "
                f"got {type(tool_result).__name__}"
            )
        provenance = _provenance(
            story=story,
            options=options,
            response=response,
            parent_evidence_set_id=evidence_set.evidence_set_id,
            system_prompt=system_prompt,
            tool_schema=tool_schema,
            rubric_version=models.SUVIN_RUBRIC_VERSION,
        )
        candidates = _novum_candidates(tool_result, evidence_set)
        return (
            novum.build_analysis(
                analysis_id=f"{_stable_slug(story.story_id)}-suvin-v1",
                story_hash=prepared.story_hash,
                evidence_set=evidence_set,
                candidates=candidates,
                provenance=provenance,
                dominant_novum_id=_dominant_novum_id(
                    tool_result.get("dominant_novum_id"), candidates
                ),
            ),
            response,
        )
    except Exception as error:
        _record_stage_failure(
            output_root=output_root,
            story=story,
            stage=SUVIN_STAGE,
            error=error,
            tool_result=tool_result,
            raw_path=raw_path,
            log=log,
        )
        failure = models.FailureRecord(
            stage=SUVIN_RECORD_STAGE,
            kind=type(error).__name__,
            message=str(error),
            recoverable=True,
        )
        return (
            novum.failed_analysis(
                analysis_id=f"{_stable_slug(story.story_id)}-suvin-v1",
                story_hash=prepared.story_hash,
                evidence_set_id=evidence_set.evidence_set_id,
                provenance=provenance,
                failure=failure,
            ),
            response,
        )


def _empty_response(options: RunnerOptions) -> llm_backend.BackendResponse:
    return llm_backend.BackendResponse(
        text="",
        tool_result=None,
        model=options.model,
        input_tokens=0,
        output_tokens=0,
    )


def _record_stage_failure(
    *,
    output_root: pathlib.Path,
    story: SpikeStory,
    stage: str,
    error: Exception,
    tool_result: Any,
    raw_path: pathlib.Path | None,
    log: run_log.RunLog | None,
) -> None:
    quarantine_path = _write_quarantine(
        output_root=output_root,
        story=story,
        error=error,
        tool_result=tool_result,
        raw_response_path=raw_path,
        stage=stage,
    )
    if log is not None:
        log.event(
            "stage_failed",
            story_id=story.story_id,
            stage=stage,
            failure_kind=type(error).__name__,
            quarantine_path=_display_path(quarantine_path),
        )


def _partial_success_record(
    knight_analysis: models.KnightAnalysis,
    suvin_analysis: models.SuvinNovumAnalysis,
) -> models.PartialSuccessRecord | None:
    completed = [EVIDENCE_RECORD_STAGE]
    failures: list[models.FailureRecord] = []
    if knight_analysis.status == "complete":
        completed.append(KNIGHT_RECORD_STAGE)
    failures.extend(knight_analysis.failures)
    if suvin_analysis.status == "complete":
        completed.append(SUVIN_RECORD_STAGE)
    failures.extend(suvin_analysis.failures)
    if not failures:
        return None
    return models.PartialSuccessRecord(
        completed_stages=tuple(completed),
        failed_stages=tuple(failures),
    )


def _knight_decisions(
    tool_result: dict[str, Any],
    evidence_set: evidence.EvidenceSet,
) -> tuple[knight.CriterionAdjudication, ...]:
    by_id = {
        item.get("criterion_id"): item
        for item in _list_field(tool_result, "knight_criteria")
        if isinstance(item, dict)
    }
    fallback_evidence = _first_evidence_id(evidence_set)
    decisions = []
    for criterion_id in models.KNIGHT_CRITERION_IDS:
        item = by_id.get(criterion_id, {})
        status = _decision_state(item.get("status", "not_assessable"))
        support = _string_tuple(item.get("supporting_evidence_ids", ()))
        if status == "present" and not support and fallback_evidence is not None:
            support = (fallback_evidence,)
        decisions.append(
            knight.CriterionAdjudication(
                criterion_id=criterion_id,
                status=status,
                materiality=(
                    _materiality(item.get("materiality"))
                    if status in {"present", "ambiguous"}
                    else None
                ),
                supporting_evidence_ids=_existing_evidence_ids(
                    evidence_set,
                    support,
                ),
                rationale=str(item.get("rationale", "")),
                confidence=_optional_float(item.get("confidence")),
            )
        )
    return tuple(decisions)


def _novum_candidates(
    tool_result: dict[str, Any],
    evidence_set: evidence.EvidenceSet,
) -> tuple[novum.CandidateAdjudication, ...]:
    candidates = []
    for index, raw_item in enumerate(
        _list_field(tool_result, "novum_candidates"), start=1
    ):
        if not isinstance(raw_item, dict):
            continue
        item = raw_item
        candidate_id = _optional_string(item.get("candidate_id")) or f"novum-{index}"
        candidates.append(
            novum.CandidateAdjudication(
                candidate_id=candidate_id,
                description=str(item.get("description", candidate_id)),
                novelty=_dimension(item.get("novelty", {}), evidence_set),
                cognitive_validation=_dimension(
                    item.get("cognitive_validation", {}),
                    evidence_set,
                ),
                narrative_hegemony=_dimension(
                    item.get("narrative_hegemony", {}),
                    evidence_set,
                ),
                estrangement=novum.EstrangementAdjudication(
                    reader_facing_evidence_ids=_existing_evidence_ids(
                        evidence_set,
                        _string_tuple(item.get("reader_facing_evidence_ids", ())),
                    ),
                    storyworld_consequence_evidence_ids=_existing_evidence_ids(
                        evidence_set,
                        _string_tuple(
                            item.get("storyworld_consequence_evidence_ids", ())
                        ),
                    ),
                    character_reaction_evidence_ids=_existing_evidence_ids(
                        evidence_set,
                        _string_tuple(item.get("character_reaction_evidence_ids", ())),
                    ),
                    rationale=str(item.get("estrangement_rationale", "")),
                ),
                evidence_ids=_existing_evidence_ids(
                    evidence_set,
                    _string_tuple(item.get("evidence_ids", ())),
                ),
            )
        )
    return tuple(candidates)


def _dominant_novum_id(
    raw_value: Any,
    candidates: tuple[novum.CandidateAdjudication, ...],
) -> str | None:
    candidate_id = _optional_string(raw_value)
    if candidate_id is None:
        return None
    qualified_ids = {
        candidate.candidate_id
        for candidate in candidates
        if (
            candidate.novelty.status == "present"
            and candidate.cognitive_validation.status == "present"
            and candidate.narrative_hegemony.status == "present"
        )
    }
    if candidate_id in qualified_ids:
        return candidate_id
    return None


def _dimension(
    raw: Any,
    evidence_set: evidence.EvidenceSet,
) -> novum.DimensionAdjudication:
    if not isinstance(raw, dict):
        raw = {"status": "not_assessable", "rationale": f"malformed {type(raw).__name__}"}
    return novum.DimensionAdjudication(
        status=_decision_state(raw.get("status", "not_assessable")),
        supporting_evidence_ids=_existing_evidence_ids(
            evidence_set,
            _string_tuple(raw.get("supporting_evidence_ids", ())),
        ),
        counterevidence_ids=_existing_evidence_ids(
            evidence_set,
            _string_tuple(raw.get("counterevidence_ids", ())),
        ),
        rationale=str(raw.get("rationale", "")),
        confidence=_optional_float(raw.get("confidence")),
    )


def _provenance(
    *,
    story: SpikeStory,
    options: RunnerOptions,
    response: llm_backend.BackendResponse,
    parent_evidence_set_id: str,
    system_prompt: str,
    tool_schema: dict[str, Any],
    rubric_version: str,
) -> models.ProvenanceRecord:
    return models.ProvenanceRecord(
        run_id=f"worldcon-spike:{options.mode}:{_stable_slug(story.story_id)}",
        rubric_version=rubric_version,
        code_commit=_git_commit(),
        backend=options.backend_kind,
        model=response.model,
        prompt_hash=_hash_text(system_prompt),
        schema_hash=_hash_text(_stable_json(tool_schema)),
        generation_parameters={
            "max_tokens": options.max_tokens,
            "temperature": options.temperature,
        },
        token_usage={
            "input": response.input_tokens,
            "output": response.output_tokens,
        },
        estimated_cost_usd=0.0,
        generated_at="fixed-for-byte-stability",
        parent_evidence_set_id=parent_evidence_set_id,
    )


def _evidence_payload(
    story: SpikeStory, prepared: preparation.StoryPreparation
) -> dict[str, Any]:
    return {
        "stage": EVIDENCE_STAGE,
        "prompt_version": PROMPT_VERSION,
        "story_id": story.story_id,
        "story_hash": prepared.story_hash,
        "paragraph_ids": [item.paragraph_id for item in prepared.paragraphs],
        "text": _indexed_story_text(prepared),
    }


def _knight_payload(
    story: SpikeStory,
    prepared: preparation.StoryPreparation,
    evidence_set: evidence.EvidenceSet,
) -> dict[str, Any]:
    return {
        "stage": KNIGHT_STAGE,
        "prompt_version": PROMPT_VERSION,
        "story_id": story.story_id,
        "story_hash": prepared.story_hash,
        "evidence_set_id": evidence_set.evidence_set_id,
        "text": _indexed_story_text(prepared),
        "evidence": [item.to_dict() for item in evidence_set.records],
    }


def _suvin_payload(
    story: SpikeStory,
    prepared: preparation.StoryPreparation,
    evidence_set: evidence.EvidenceSet,
) -> dict[str, Any]:
    return {
        "stage": SUVIN_STAGE,
        "prompt_version": PROMPT_VERSION,
        "story_id": story.story_id,
        "story_hash": prepared.story_hash,
        "evidence_set_id": evidence_set.evidence_set_id,
        "text": _indexed_story_text(prepared),
        "evidence": [item.to_dict() for item in evidence_set.records],
    }


def _indexed_story_text(prepared: preparation.StoryPreparation) -> str:
    return "\n\n".join(
        f"[{paragraph.paragraph_id}] {paragraph.text}"
        for paragraph in prepared.paragraphs
    )


def _evidence_system_prompt() -> str:
    return """
You are the shared, theory-neutral evidence extractor for an LCATS
science-fiction analysis. Read only the supplied story. Return only the
record_science_fiction_evidence tool input.

Extract concise candidate evidence for these controlled types:
storyworld_change, scientific_or_technical_explanation,
inquiry_or_scientific_method, temporal_or_spatial_displacement,
extrapolative_consequence, catastrophe, character_reaction, and
reader_facing_contrast.

Every item must contain an exact quotation copied from the story, the
paragraph IDs containing it, a short neutral paraphrase, a confidence from 0
to 1, and a unique raw_id. Do not put paragraph markers inside quotations.
Do not make Knight or Suvin judgments, identify a genre, calculate a score, or
call anything a novum. Prefer fewer strong items to unsupported guesses.
Return the exact keys required by the tool schema.
""".strip()


def _knight_system_prompt() -> str:
    return """
You are the independent Knight adjudicator in an LCATS science-fiction
analysis. The shared evidence records are supplied by an earlier stage.
Return only the record_knight_adjudication tool input.

Use rubric_id knight-seven-v1 and return exactly criterion_1 through
criterion_7. Use present, ambiguous, absent, or not_assessable. Do not return
a score, probability, pass threshold, or arithmetic; Python computes the
definite/possible interval.

criterion_1 science: scientific facts, theories, discoveries, natural
processes, or speculative sciences materially represented.
criterion_2 technology_and_invention: a device, technique, engineered system,
or invention materially affects the setting, problem, action, or outcome.
criterion_3 future_remote_past_time_travel: a speculative future or remote
past, or temporal displacement.
criterion_4 extrapolation: consequences developed from an identifiable
scientific, technological, social, or historical premise.
criterion_5 scientific_method: observation, hypothesis, testing, measurement,
evidential revision, or systematic inference materially drives understanding
or action.
criterion_6 other_places_and_visitors: other planets, dimensions,
substantially nonordinary cosmic environments, or visitors from them.
criterion_7 catastrophe: a natural, technological, cosmic, biological, or
human-caused large-scale disaster that is actual, impending, remembered, or
causally central.

Do not count a mere mention, ordinary contemporary tool, decorative jargon,
incidental date, generic investigation, ordinary foreign country, or personal
misfortune without broader scale. For present or ambiguous criteria, use
central, substantial, or incidental materiality; otherwise use materiality
none. Cite supporting and counterevidence IDs from the supplied evidence.
Return exactly the schema keys; do not substitute criterion or assessment for
criterion_id or status.
""".strip()


def _suvin_system_prompt() -> str:
    return """
You are the independent Suvin Novum adjudicator in an LCATS science-fiction
analysis. The story and shared neutral evidence are supplied by earlier
stages. Return only the record_suvin_novum_adjudication tool input.

Identify candidate nova, not every unusual object or gadget. For each
candidate, decide independently:
- novelty: a totalizing or world-altering difference from the authorial or
  implied empirical norm that changes the story universe or a crucial aspect;
- cognitive_validation: a coherent, systematic, immanent, nonsupernatural
  account, including imaginary science or social organization. Present-day
  buildability, scientific accuracy, engineering detail, and technobabble are
  neither required nor sufficient;
- narrative_hegemony: centrality sufficient to determine the whole or
  overriding narrative logic, rather than an incidental device.

Use present, ambiguous, absent, or not_assessable for each dimension. A
candidate qualifies only when all three dimensions are present. Do not emit a
numeric score or qualified_novum; Python computes the conjunction. Record
reader-facing contrast, storyworld consequences, and optional character
reaction separately as estrangement evidence. Character surprise is not
required. Use only evidence IDs supplied in the prompt.
""".strip()


def _evidence_tool_schema() -> dict[str, Any]:
    evidence_item = {
        "type": "object",
        "properties": {
            "raw_id": {"type": "string"},
            "evidence_type": {
                "type": "string",
                "enum": [
                    "storyworld_change",
                    "scientific_or_technical_explanation",
                    "inquiry_or_scientific_method",
                    "temporal_or_spatial_displacement",
                    "extrapolative_consequence",
                    "catastrophe",
                    "character_reaction",
                    "reader_facing_contrast",
                ],
            },
            "quote": {"type": "string"},
            "paragraph_ids": {"type": "array", "items": {"type": "string"}},
            "paraphrase": {"type": "string"},
            "confidence": {"type": "number"},
        },
        "required": [
            "raw_id",
            "evidence_type",
            "quote",
            "paragraph_ids",
            "paraphrase",
            "confidence",
        ],
    }
    return tool_schema_module.strict_tool_schema(
        {
            "name": EVIDENCE_TOOL_NAME,
            "description": "Record neutral, story-grounded evidence candidates.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "evidence": {"type": "array", "items": evidence_item},
                },
                "required": ["evidence"],
            },
        }
    )


def _knight_tool_schema() -> dict[str, Any]:
    criterion = {
        "type": "object",
        "properties": {
            "criterion_id": {
                "type": "string",
                "enum": [f"criterion_{index}" for index in range(1, 8)],
            },
            "status": {
                "type": "string",
                "enum": ["present", "ambiguous", "absent", "not_assessable"],
            },
            "materiality": {
                "type": "string",
                "enum": ["central", "substantial", "incidental", "none"],
            },
            "supporting_evidence_ids": {
                "type": "array",
                "items": {"type": "string"},
            },
            "counterevidence_ids": {
                "type": "array",
                "items": {"type": "string"},
            },
            "rationale": {"type": "string"},
            "confidence": {"type": "number"},
        },
        "required": [
            "criterion_id",
            "status",
            "materiality",
            "supporting_evidence_ids",
            "counterevidence_ids",
            "rationale",
            "confidence",
        ],
    }
    return tool_schema_module.strict_tool_schema(
        {
            "name": KNIGHT_TOOL_NAME,
            "description": "Record seven independent Knight criterion decisions.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "knight_criteria": {
                        "type": "array",
                        "items": criterion,
                    }
                },
                "required": ["knight_criteria"],
            },
        }
    )


def _suvin_tool_schema() -> dict[str, Any]:
    evidence_ids = {"type": "array", "items": {"type": "string"}}
    dimension = {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["present", "ambiguous", "absent", "not_assessable"],
            },
            "supporting_evidence_ids": evidence_ids,
            "counterevidence_ids": evidence_ids,
            "rationale": {"type": "string"},
            "confidence": {"type": "number"},
        },
        "required": [
            "status",
            "supporting_evidence_ids",
            "counterevidence_ids",
            "rationale",
            "confidence",
        ],
    }
    candidate = {
        "type": "object",
        "properties": {
            "candidate_id": {"type": "string"},
            "description": {"type": "string"},
            "novelty": dimension,
            "cognitive_validation": dimension,
            "narrative_hegemony": dimension,
            "reader_facing_evidence_ids": evidence_ids,
            "storyworld_consequence_evidence_ids": evidence_ids,
            "character_reaction_evidence_ids": evidence_ids,
            "estrangement_rationale": {"type": "string"},
            "evidence_ids": evidence_ids,
        },
        "required": [
            "candidate_id",
            "description",
            "novelty",
            "cognitive_validation",
            "narrative_hegemony",
            "reader_facing_evidence_ids",
            "storyworld_consequence_evidence_ids",
            "character_reaction_evidence_ids",
            "estrangement_rationale",
            "evidence_ids",
        ],
    }
    return tool_schema_module.strict_tool_schema(
        {
            "name": SUVIN_TOOL_NAME,
            "description": "Record independent candidate-based Suvin Novum decisions.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "novum_candidates": {"type": "array", "items": candidate},
                    "dominant_novum_id": {"type": "string"},
                },
                "required": ["novum_candidates", "dominant_novum_id"],
            },
        }
    )


def _fake_tool_result(payload: dict[str, Any]) -> dict[str, Any]:
    quotes = _story_quotes(payload["text"])
    evidence_rows = [
        _evidence_row("ev-storyworld", "storyworld_change", quotes[0]),
        _evidence_row(
            "ev-explanation",
            "scientific_or_technical_explanation",
            quotes[1],
        ),
        _evidence_row("ev-method", "inquiry_or_scientific_method", quotes[2]),
        _evidence_row("ev-consequence", "extrapolative_consequence", quotes[3]),
        _evidence_row("ev-contrast", "reader_facing_contrast", quotes[4]),
        _evidence_row("ev-reaction", "character_reaction", quotes[5]),
    ]
    return {
        "evidence": evidence_rows,
        "knight_criteria": [
            {
                "criterion_id": criterion_id,
                "status": "present" if index <= 3 else "absent",
                "materiality": "central" if index <= 3 else None,
                "supporting_evidence_ids": ["ev-storyworld"] if index <= 3 else [],
                "rationale": "No-cost deterministic smoke decision.",
                "confidence": 0.5,
            }
            for index, criterion_id in enumerate(
                models.KNIGHT_CRITERION_IDS,
                start=1,
            )
        ],
        "novum_candidates": [
            {
                "candidate_id": "novum-1",
                "description": "No-cost smoke candidate derived from story text.",
                "novelty": {
                    "status": "present",
                    "supporting_evidence_ids": ["ev-storyworld"],
                    "rationale": "Smoke fixture treats the storyworld contrast as novelty.",
                    "confidence": 0.5,
                },
                "cognitive_validation": {
                    "status": "present",
                    "supporting_evidence_ids": ["ev-explanation"],
                    "rationale": "Smoke fixture treats explanatory evidence as cognitive validation.",
                    "confidence": 0.5,
                },
                "narrative_hegemony": {
                    "status": "present",
                    "supporting_evidence_ids": ["ev-consequence"],
                    "rationale": "Smoke fixture treats consequence evidence as hegemony.",
                    "confidence": 0.5,
                },
                "reader_facing_evidence_ids": ["ev-contrast"],
                "character_reaction_evidence_ids": ["ev-reaction"],
                "estrangement_rationale": "Estrangement evidence is recorded separately.",
                "evidence_ids": ["ev-storyworld", "ev-explanation", "ev-consequence"],
            }
        ],
        "dominant_novum_id": "novum-1",
    }


def _fake_stage_result(
    payload: dict[str, Any], tool: dict[str, Any] | None
) -> dict[str, Any]:
    result = _fake_tool_result(payload)
    tool_name = tool.get("name") if isinstance(tool, dict) else None
    if tool_name == EVIDENCE_TOOL_NAME:
        return {"evidence": result["evidence"]}
    if tool_name == KNIGHT_TOOL_NAME:
        return {"knight_criteria": result["knight_criteria"]}
    if tool_name == SUVIN_TOOL_NAME:
        return {
            "novum_candidates": result["novum_candidates"],
            "dominant_novum_id": result["dominant_novum_id"],
        }
    return result


def _story_quotes(text: str) -> tuple[str, str, str, str, str, str]:
    paragraphs = []
    for item in text.split("\n\n"):
        cleaned = item.strip()
        if not cleaned:
            continue
        if cleaned.startswith("[") and "] " in cleaned:
            cleaned = cleaned.split("] ", 1)[1]
        paragraphs.append(cleaned)
    if not paragraphs:
        paragraphs = [text.strip()]
    snippets = [_short_quote(item) for item in paragraphs]
    while len(snippets) < 6:
        snippets.append(snippets[-1])
    return tuple(snippets[:6])


def _short_quote(text: str) -> str:
    cleaned = text.strip()
    if len(cleaned) <= 180:
        return cleaned
    cut = cleaned[:180].rsplit(" ", 1)[0]
    return cut or cleaned[:180]


def _evidence_row(raw_id: str, evidence_type: str, quote: str) -> dict[str, Any]:
    return {
        "raw_id": raw_id,
        "evidence_type": evidence_type,
        "quote": quote,
        "paraphrase": f"Spike evidence for {evidence_type}.",
        "confidence": 0.5,
    }


def _make_backend(options: RunnerOptions) -> llm_backend.LLMBackend:
    if options.backend_kind == FAKE_BACKEND:
        return DeterministicSpikeBackend()
    if options.backend_kind in {OPENAI_BACKEND, OPENAI_COMPATIBLE_BACKEND}:
        return openai_backend.OpenAIBackend(base_url=options.base_url)
    if options.backend_kind == ANTHROPIC_BACKEND:
        return anthropic_backend.AnthropicBackend()
    raise ValueError(f"unsupported backend kind: {options.backend_kind!r}")


def _enforce_run_gate(
    manifest: SpikeManifest,
    options: RunnerOptions,
    stories: tuple[SpikeStory, ...],
) -> None:
    gate = manifest.gates[options.mode]
    if len(stories) > gate.max_stories:
        raise ValueError(
            f"{options.mode} mode may not run more than {gate.max_stories} stories"
        )
    if gate.requires_smoke_success:
        if options.smoke_summary is None:
            raise ValueError(f"{options.mode} mode requires --smoke-summary")
        smoke_summary = json.loads(
            pathlib.Path(options.smoke_summary).read_text(encoding="utf-8")
        )
        if smoke_summary.get("status") != "complete":
            raise ValueError(
                f"{options.mode} mode requires a successful smoke summary"
            )
    if gate.requires_full_sample_approval and not options.approve_full_sample:
        raise ValueError("full mode requires --approve-full-sample")
    if _paid_call_requested(options, gate):
        _enforce_paid_run_gate(gate, options)


def _paid_call_requested(options: RunnerOptions, gate: RunGate) -> bool:
    if options.backend_kind == ANTHROPIC_BACKEND:
        return True
    if options.backend_kind == OPENAI_BACKEND:
        return True
    if gate.estimated_cost_usd > 0:
        return True
    if options.backend_kind == OPENAI_COMPATIBLE_BACKEND and options.base_url is None:
        return True
    return False


def _enforce_paid_run_gate(gate: RunGate, options: RunnerOptions) -> None:
    if not options.approve_paid:
        raise ValueError("paid model calls require --approve-paid")
    if not gate.paid_model_calls_authorized:
        raise ValueError("manifest does not authorize paid model calls")
    if gate.approved_backend is None or gate.approved_model is None:
        raise ValueError(
            "paid model calls require approved_backend and approved_model"
        )
    if gate.approved_backend != options.backend_kind:
        raise ValueError(
            "paid model calls require backend to match approved_backend"
        )
    if gate.approved_model != options.model:
        raise ValueError("paid model calls require model to match approved_model")
    if gate.estimated_cost_usd <= 0:
        raise ValueError("paid model calls require positive estimated_cost_usd")
    if (
        gate.estimated_wall_clock_minutes is None
        or gate.estimated_wall_clock_minutes <= 0
    ):
        raise ValueError(
            "paid model calls require positive estimated_wall_clock_minutes"
        )
    if not gate.stop_conditions:
        raise ValueError("paid model calls require reviewed stop_conditions")


def _load_full_sample(manifest: SpikeManifest) -> tuple[SpikeStory, ...]:
    source_path = _repo_root() / manifest.source_worldcon_manifest
    stories: list[SpikeStory] = []
    with source_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            data = json.loads(line)
            stories.append(
                SpikeStory(
                    story_id=data["story_id"],
                    story_path=data["story_path"],
                    title=data.get("title", data["story_id"]),
                    selection_genre=data.get("selection_genre", ""),
                    sample_roles=("full",),
                )
            )
    if len(stories) != FULL_SAMPLE_LIMIT:
        raise ValueError(
            f"full sample source must contain {FULL_SAMPLE_LIMIT} stories"
        )
    return tuple(stories)


def _summary(
    *,
    status: str,
    manifest: SpikeManifest,
    options: RunnerOptions,
    output_root: pathlib.Path,
    plan: dict[str, Any],
    results: Iterable[StoryResult],
) -> dict[str, Any]:
    story_results = tuple(results)
    return {
        "version": SUMMARY_VERSION,
        "status": status,
        "work_item": manifest.work_item,
        "mode": options.mode,
        "backend_kind": options.backend_kind,
        "model": options.model,
        "output_root": _display_path(output_root),
        "manifest_path": _display_path(manifest.manifest_path),
        "source_worldcon_manifest": manifest.source_worldcon_manifest,
        "plan": plan,
        "totals": {
            "stories": len(story_results),
            "complete": sum(1 for item in story_results if item.status == "complete"),
            "failed": sum(1 for item in story_results if item.status == "failed"),
            "input_tokens": sum(item.input_tokens for item in story_results),
            "output_tokens": sum(item.output_tokens for item in story_results),
            "latency_seconds": round(
                sum(item.latency_seconds for item in story_results),
                3,
            ),
        },
        "stories": [item.to_dict() for item in story_results],
    }


def _plan(
    options: RunnerOptions,
    manifest: SpikeManifest,
    stories: tuple[SpikeStory, ...],
    output_root: pathlib.Path,
) -> dict[str, Any]:
    gate = manifest.gates[options.mode]
    return {
        "mode": options.mode,
        "story_count": len(stories),
        "max_stories": gate.max_stories,
        "backend_kind": options.backend_kind,
        "model": options.model,
        "base_url": options.base_url,
        "estimated_cost_usd": gate.estimated_cost_usd,
        "paid_model_calls_authorized": gate.paid_model_calls_authorized,
        "approve_paid": options.approve_paid,
        "approve_full_sample": options.approve_full_sample,
        "output_root": _display_path(output_root),
        "manifest_fingerprint": _manifest_fingerprint(manifest),
        "story_ids": [story.story_id for story in stories],
    }


def _write_summary(output_root: pathlib.Path, summary: dict[str, Any]) -> pathlib.Path:
    output_root.mkdir(parents=True, exist_ok=True)
    path = output_root / "worldcon_spike_summary.json"
    path.write_text(_stable_json(summary), encoding="utf-8")
    return path


def _write_report(output_root: pathlib.Path, summary: dict[str, Any]) -> pathlib.Path:
    output_root.mkdir(parents=True, exist_ok=True)
    path = output_root / "worldcon_spike_report.md"
    lines = [
        "# Worldcon Knight/Novum Spike Report",
        "",
        f"- Report version: `{REPORT_VERSION}`",
        f"- Work item: `{summary['work_item']}`",
        f"- Mode: `{summary['mode']}`",
        f"- Backend: `{summary['backend_kind']}`",
        f"- Model: `{summary['model']}`",
        f"- Status: `{summary['status']}`",
        f"- Stories complete: `{summary['totals']['complete']}/{summary['totals']['stories']}`",
        f"- Input tokens: `{summary['totals']['input_tokens']}`",
        f"- Output tokens: `{summary['totals']['output_tokens']}`",
        f"- Latency seconds: `{summary['totals']['latency_seconds']}`",
        "",
        "## Go/No-Go Note",
        "",
        _recommendation(summary),
        "",
        "## Stories",
        "",
    ]
    for item in summary["stories"]:
        interval = item["knight_interval"] or {}
        lines.extend(
            [
                f"### {item['story_id']}",
                "",
                f"- Title: {item['title']}",
                f"- Status: `{item['status']}`",
                "- Knight interval: "
                f"`{interval.get('definite_count')}/{interval.get('possible_count')}`",
                f"- Qualified novum count: `{item['qualified_novum_count']}`",
                f"- Dominant novum: `{item['dominant_novum_id']}`",
                f"- Sidecar: `{item['sidecar_path']}`",
                "",
            ]
        )
        if item["failure_kind"]:
            lines.extend(
                [
                    f"- Failure kind: `{item['failure_kind']}`",
                    f"- Failure message: {item['failure_message']}",
                    "",
                ]
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _recommendation(summary: dict[str, Any]) -> str:
    if summary["status"] != "complete":
        return "Stop/revise: the spike did not complete structurally."
    if summary["mode"] == SMOKE_MODE:
        return (
            "Go to the 5-10 story local or paid sample only after reviewing "
            "these smoke outputs and approving the next backend/cost gate."
        )
    if summary["mode"] == SAMPLE_MODE:
        return (
            "Use these sample outputs to decide whether to approve a full "
            "146-story local or paid run with explicit cost, time, and stop "
            "conditions."
        )
    return (
        "Use the full-sample outputs as a Worldcon spike artifact only; this "
        "does not constitute Phase 2 validation or human agreement."
    )


def _resolve_safe_output_root(
    output_root: pathlib.Path,
    *,
    allow_protected_root: bool = False,
) -> pathlib.Path:
    resolved = pathlib.Path(output_root).resolve()
    if resolved.exists() and not resolved.is_dir():
        raise ValueError("output_root must be a directory")
    checkpoint.resolve_roots(
        resolved,
        allow_protected_root=allow_protected_root,
    )
    package_root = paths.find_pyproject_root(__file__).resolve()
    repo_root = package_root.parent.resolve()
    if resolved in {repo_root, package_root}:
        raise ValueError("output_root must not be the repository or package root")
    return resolved


def _load_gate(mode: str, data: dict[str, Any]) -> RunGate:
    return RunGate(
        mode=mode,
        max_stories=int(data["max_stories"]),
        paid_model_calls_authorized=bool(
            data.get("paid_model_calls_authorized", False)
        ),
        estimated_cost_usd=float(data.get("estimated_cost_usd", 0.0)),
        requires_smoke_success=bool(data.get("requires_smoke_success", False)),
        requires_full_sample_approval=bool(
            data.get("requires_full_sample_approval", False)
        ),
        approved_backend=_optional_string(data.get("approved_backend")),
        approved_model=_optional_string(data.get("approved_model")),
        estimated_wall_clock_minutes=_optional_float(
            data.get("estimated_wall_clock_minutes")
        ),
        stop_conditions=tuple(data.get("stop_conditions", ())),
    )


def _load_story(data: dict[str, Any]) -> SpikeStory:
    return SpikeStory(
        story_id=_required_string(data, "story_id"),
        story_path=_required_string(data, "story_path"),
        title=_required_string(data, "title"),
        selection_genre=_required_string(data, "selection_genre"),
        sample_roles=tuple(data.get("sample_roles", ())),
    )


def _existing_evidence_ids(
    evidence_set: evidence.EvidenceSet,
    evidence_ids: tuple[str, ...],
) -> tuple[str, ...]:
    available = {record.evidence_id: record.evidence_id for record in evidence_set.records}
    for record in evidence_set.records:
        for provenance in record.provenance:
            if provenance.raw_id:
                available[provenance.raw_id] = record.evidence_id
    return tuple(available[item] for item in evidence_ids if item in available)


def _list_field(data: dict[str, Any], key: str) -> tuple[Any, ...]:
    value = data.get(key, ())
    if isinstance(value, list | tuple):
        return tuple(value)
    return ()


def _string_tuple(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,) if value else ()
    if isinstance(value, list | tuple):
        return tuple(item for item in value if isinstance(item, str) and item)
    return ()


def _first_evidence_id(evidence_set: evidence.EvidenceSet) -> str | None:
    if not evidence_set.records:
        return None
    return evidence_set.records[0].evidence_id


def _decision_state(value: Any) -> str:
    if value in models.DECISION_STATES:
        return str(value)
    return "not_assessable"


def _materiality(value: Any) -> str | None:
    if value == "none":
        return None
    if value in models.MATERIALITY_STATES:
        return str(value)
    return None


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str) and value:
        return value
    return None


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _manifest_fingerprint(manifest: SpikeManifest) -> str:
    payload = {
        "version": manifest.version,
        "source_worldcon_manifest": manifest.source_worldcon_manifest,
        "smoke_stories": [dataclasses.asdict(item) for item in manifest.smoke_stories],
        "sample_stories": [
            dataclasses.asdict(item) for item in manifest.sample_stories
        ],
        "gates": {
            key: dataclasses.asdict(value)
            for key, value in sorted(manifest.gates.items())
        },
    }
    return _hash_text(_stable_json(payload))


def _checkpoint_item_id(story: SpikeStory) -> str:
    return f"{_stable_slug(story.story_id)}-{_hash_text(story.story_id)[:12]}"


def _stable_slug(value: str) -> str:
    return value.replace("/", "__").replace(" ", "_")


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _git_commit() -> str | None:
    git_head = _repo_root() / ".git" / "HEAD"
    if not git_head.exists():
        return None
    head = git_head.read_text(encoding="utf-8").strip()
    if head.startswith("ref: "):
        ref = _repo_root() / ".git" / head.removeprefix("ref: ")
        if ref.exists():
            return ref.read_text(encoding="utf-8").strip()
        return None
    return head


def _repo_root() -> pathlib.Path:
    return paths.find_pyproject_root(__file__).resolve().parent


def _display_path(path: pathlib.Path) -> str:
    resolved = pathlib.Path(path).resolve()
    for root in (paths.find_pyproject_root(__file__).resolve(), _repo_root()):
        try:
            return str(resolved.relative_to(root))
        except ValueError:
            pass
    return str(resolved)


def _stable_json(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def _required_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the bounded Worldcon Knight/Novum spike."
    )
    parser.add_argument("--manifest", type=pathlib.Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-root", type=pathlib.Path, default=DEFAULT_RESULTS_ROOT)
    parser.add_argument(
        "--mode",
        choices=(SMOKE_MODE, SAMPLE_MODE, FULL_MODE),
        default=SMOKE_MODE,
    )
    parser.add_argument(
        "--backend",
        dest="backend_kind",
        choices=(FAKE_BACKEND, OPENAI_BACKEND, OPENAI_COMPATIBLE_BACKEND, ANTHROPIC_BACKEND),
        default=FAKE_BACKEND,
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--smoke-summary", type=pathlib.Path)
    parser.add_argument("--approve-paid", action="store_true")
    parser.add_argument("--approve-full-sample", action="store_true")
    parser.add_argument("--max-stories", type=int)
    parser.add_argument("--stop-on-first-failure", action="store_true")
    parser.add_argument("--max-failures", type=int)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    return parser.parse_args(argv)


def _options_from_args(args: argparse.Namespace) -> RunnerOptions:
    return RunnerOptions(
        manifest_path=args.manifest,
        output_root=args.output_root,
        mode=args.mode,
        backend_kind=args.backend_kind,
        model=args.model,
        base_url=args.base_url,
        dry_run=args.dry_run,
        smoke_summary=args.smoke_summary,
        approve_paid=args.approve_paid,
        approve_full_sample=args.approve_full_sample,
        max_stories=args.max_stories,
        stop_on_first_failure=args.stop_on_first_failure,
        max_failures=args.max_failures,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
    )


if __name__ == "__main__":
    raise SystemExit(main())
