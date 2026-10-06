"""Run the bounded Worldcon Knight/Novum spike.

This experiment-local runner is deliberately narrower than the governed Phase 2
pilot. It can run a no-cost fake/local smoke first, then enforce explicit gates
before any 5-10 story sample or 146-story Worldcon-scale run.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import math
import json
import os
import pathlib
import subprocess
import sys
import time
import uuid
from typing import Any, Callable, Iterable

from lcats.analysis.science_fiction import evidence
from lcats.analysis.science_fiction import heinlein
from lcats.analysis.science_fiction import knight
from lcats.analysis.science_fiction import models
from lcats.analysis.science_fiction import novum
from lcats.analysis.science_fiction import pipeline
from lcats.analysis.science_fiction import preparation
from lcats.analysis.science_fiction.rubric import definitions as rubric_definitions
from lcats.llm import anthropic_backend
from lcats.llm import backend as llm_backend
from lcats.llm import openai_backend
from lcats.llm import tool_schema as tool_schema_module
from lcats.utils import checkpoint
from lcats.utils import paths
from lcats.utils import run_log

_O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)

MANIFEST_VERSION = "worldcon-knight-novum-spike-manifest-v1"
SUMMARY_VERSION = "worldcon-knight-novum-spike-summary-v1"
REPORT_VERSION = "worldcon-knight-novum-spike-report-v1"
PROMPT_VERSION = "worldcon-knight-novum-spike-prompt-v3"
EVIDENCE_STAGE = "sf_evidence"
KNIGHT_STAGE = "sf_knight"
SUVIN_STAGE = "sf_suvin_novum"
HEINLEIN_STAGE = "sf_heinlein"
EVIDENCE_RECORD_STAGE = "evidence"
KNIGHT_RECORD_STAGE = "knight"
SUVIN_RECORD_STAGE = "suvin_novum"
HEINLEIN_RECORD_STAGE = "heinlein"
EVIDENCE_TOOL_NAME = "record_science_fiction_evidence"
KNIGHT_TOOL_NAME = "record_knight_adjudication"
SUVIN_TOOL_NAME = "record_suvin_novum_adjudication"
HEINLEIN_TOOL_NAME = "record_heinlein_adjudication"
# The optional Heinlein stage has its own prompt version so enabling it never
# changes PROMPT_VERSION, which feeds the Knight and Suvin checkpoint payloads.
HEINLEIN_PROMPT_VERSION = "worldcon-heinlein-spike-prompt-v1"
DEFAULT_MANIFEST = (
    pathlib.Path(__file__).resolve().parent
    / "manifests"
    / "worldcon_spike_manifest.json"
)
DEFAULT_RESULTS_ROOT = (
    pathlib.Path(__file__).resolve().parent / "results" / ("worldcon_spike")
)
DEFAULT_MODEL = "fake-worldcon-spike"
DEFAULT_MAX_TOKENS = 4096
TRUNCATION_RETRY_MULTIPLIER = 2
RETRY_BACKOFF_SECONDS = 0.25
RETRY_BACKOFF_MAX_SECONDS = 2.0
DEFAULT_TEMPERATURE = 0.0
FULL_SAMPLE_LIMIT = 146
SMOKE_MODE = "smoke"
SAMPLE_MODE = "sample"
FULL_MODE = "full"
CANARY_MODE = "canary"
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
    estimated_story_cost_usd: float = 0.0
    cumulative_budget_usd: float = 0.0
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
    canary_stories: tuple[SpikeStory, ...]
    gates: dict[str, RunGate]
    source_worldcon_manifest_git_commit: str | None = None
    source_worldcon_manifest_sha256: str | None = None
    source_worldcon_manifest_expected_count: int = FULL_SAMPLE_LIMIT
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
    prior_spend_usd: float | None = None
    allow_protected_root: bool = False
    stop_on_first_failure: bool = False
    max_failures: int | None = None
    resume: bool = False
    include_heinlein: bool = False


@dataclasses.dataclass(frozen=True)
class StoryResult:
    """Per-story result summary emitted by the spike."""

    run_id: str
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
    heinlein_verdict: str | None = None
    heinlein_interval: dict[str, int] | None = None

    def to_dict(self) -> dict[str, Any]:
        data = dataclasses.asdict(self)
        # Heinlein is opt-in: omit its keys when unset so existing runs emit
        # byte-identical story rows.
        if data["heinlein_verdict"] is None:
            del data["heinlein_verdict"]
            del data["heinlein_interval"]
        return data


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
    run_id = _new_run_id()
    if options.dry_run:
        return _summary(
            status="dry_run",
            manifest=manifest,
            options=options,
            output_root=output_root,
            plan=plan,
            results=(),
            run_id=run_id,
        )

    results: list[StoryResult] = []
    summary: dict[str, Any]
    failures = 0
    stop_reason: str | None = None
    if _paid_call_requested(options, manifest.gates[options.mode]):
        _write_approval_snapshot(
            output_root,
            manifest=manifest,
            options=options,
            plan=plan,
            run_id=run_id,
        )
    with run_log.RunLog(
        output_root,
        filename="worldcon_spike_run_log.jsonl",
        work_item=manifest.work_item,
        run_id=run_id,
        mode=options.mode,
        backend_kind=options.backend_kind,
        model=options.model,
        planned_stories=len(selected_stories),
        allow_protected_root=options.allow_protected_root,
    ) as log:
        active_backend = _make_backend(options)
        for story_index, story in enumerate(selected_stories):
            gate = manifest.gates[options.mode]
            if _budget_would_be_exceeded(
                gate, story_index + 1
            ) or _cumulative_budget_would_be_exceeded(
                gate, _effective_prior_spend(options), story_index + 1
            ):
                stop_reason = "budget"
                log.event(
                    "run_stopped",
                    run_id=run_id,
                    reason="budget",
                    processed=story_index,
                    budget_usd=gate.estimated_cost_usd,
                    cumulative_budget_usd=gate.cumulative_budget_usd,
                    prior_spend_usd=_effective_prior_spend(options),
                )
                break
            log.event(
                "story_start", run_id=run_id, story_id=story.story_id, title=story.title
            )
            result = _run_story(
                story, output_root, options, active_backend, run_id, log
            )
            results.append(result)
            _append_story_result(output_root, result)
            log.event(
                "story_end",
                run_id=run_id,
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
                        run_id=run_id,
                        reason="stop_on_first_failure",
                        failures=failures,
                    )
                    break
                if (
                    options.max_failures is not None
                    and failures >= options.max_failures
                ):
                    stop_reason = "max_failures"
                    log.event(
                        "run_stopped",
                        run_id=run_id,
                        reason="max_failures",
                        failures=failures,
                        max_failures=options.max_failures,
                    )
                    break
        results_tuple = tuple(results)
        status = (
            "complete"
            if all(item.status == "complete" for item in results_tuple)
            else "failed"
        )
        if stop_reason == "budget":
            status = "budget_stopped"
        summary = _summary(
            status=status,
            manifest=manifest,
            options=options,
            output_root=output_root,
            plan=plan,
            results=results_tuple,
            run_id=run_id,
            stop_reason=stop_reason,
        )
        _write_summary(output_root, summary)
        _write_report(output_root, summary)
        log.event(
            "run_end",
            run_id=run_id,
            complete=sum(1 for item in results if item.status == "complete"),
            failed=sum(1 for item in results if item.status == "failed"),
            processed=len(results),
        )
    return summary


def load_manifest(path: pathlib.Path) -> SpikeManifest:
    """Load and validate the Worldcon spike manifest."""

    manifest_path = pathlib.Path(path)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if data.get("version") != MANIFEST_VERSION:
        raise ValueError(f"manifest version must be {MANIFEST_VERSION}")
    gates = {
        key: _load_gate(key, value) for key, value in data.get("gates", {}).items()
    }
    for required in (SMOKE_MODE, SAMPLE_MODE, CANARY_MODE, FULL_MODE):
        if required not in gates:
            raise ValueError(f"manifest missing {required!r} gate")
    return SpikeManifest(
        manifest_path=manifest_path,
        work_item=_required_string(data, "work_item"),
        source_worldcon_manifest=_required_string(data, "source_worldcon_manifest"),
        source_worldcon_manifest_git_commit=_optional_string(
            data.get("source_worldcon_manifest_git_commit")
        ),
        source_worldcon_manifest_sha256=_optional_string(
            data.get("source_worldcon_manifest_sha256")
        ),
        source_worldcon_manifest_expected_count=int(
            data.get("source_worldcon_manifest_expected_count", FULL_SAMPLE_LIMIT)
        ),
        smoke_stories=tuple(
            _load_story(item) for item in data.get("smoke_stories", ())
        ),
        sample_stories=tuple(
            _load_story(item) for item in data.get("sample_stories", ())
        ),
        canary_stories=tuple(
            _load_story(item) for item in data.get("canary_stories", ())
        ),
        gates=gates,
    )


def select_stories(manifest: SpikeManifest, mode: str) -> tuple[SpikeStory, ...]:
    """Return the deterministic story sequence for the requested mode."""

    if mode == SMOKE_MODE:
        return manifest.smoke_stories
    if mode == SAMPLE_MODE:
        return manifest.sample_stories
    if mode == CANARY_MODE:
        return manifest.canary_stories
    if mode == FULL_MODE:
        return _load_full_sample(manifest)
    raise ValueError(f"unsupported spike mode: {mode!r}")


def _run_story(
    story: SpikeStory,
    output_root: pathlib.Path,
    options: RunnerOptions,
    active_backend: llm_backend.LLMBackend,
    run_id: str,
    log: run_log.RunLog | None = None,
) -> StoryResult:
    started = time.monotonic()
    input_tokens = 0
    output_tokens = 0
    raw_response_dir: pathlib.Path | None = None
    raw_response_path: pathlib.Path | None = None
    quarantine_path: pathlib.Path | None = None
    evidence_tool_result: Any = None
    knight_tool_result: Any = None
    suvin_tool_result: Any = None
    try:
        story_file = _repo_root() / "corpora" / story.story_path
        prepared = preparation.prepare_story_file(story_file)
        raw_response_dir = output_root / "_raw" / run_id / _checkpoint_item_id(story)

        evidence_response, evidence_tool_result, evidence_raw_path, evidence_reused = (
            _run_checkpointed_model_stage(
                stage=EVIDENCE_STAGE,
                story=story,
                output_root=output_root,
                options=options,
                active_backend=active_backend,
                system_prompt=_evidence_system_prompt(),
                payload=_evidence_payload(story, prepared),
                tool_schema=_evidence_tool_schema(),
                run_id=run_id,
                log=log,
                resume=options.resume,
                validate_result=lambda _response, result: _build_evidence_set(
                    prepared, result, backend=options.backend_kind
                ),
            )
        )
        raw_response_path = evidence_raw_path
        if not evidence_reused:
            input_tokens += evidence_response.input_tokens
            output_tokens += evidence_response.output_tokens
        evidence_set = _build_evidence_set(
            prepared,
            evidence_tool_result,
            backend=options.backend_kind,
        )
        knight_analysis, knight_response, knight_raw_path, knight_reused = (
            _run_knight_stage(
                story=story,
                prepared=prepared,
                evidence_set=evidence_set,
                options=options,
                active_backend=active_backend,
                output_root=output_root,
                run_id=run_id,
                log=log,
            )
        )
        if not knight_reused:
            input_tokens += knight_response.input_tokens
            output_tokens += knight_response.output_tokens

        suvin_analysis, suvin_response, suvin_raw_path, suvin_reused = _run_suvin_stage(
            story=story,
            prepared=prepared,
            evidence_set=evidence_set,
            options=options,
            active_backend=active_backend,
            output_root=output_root,
            run_id=run_id,
            log=log,
        )
        if not suvin_reused:
            input_tokens += suvin_response.input_tokens
            output_tokens += suvin_response.output_tokens
        stage_paths = {
            EVIDENCE_STAGE: evidence_raw_path,
            KNIGHT_STAGE: knight_raw_path,
            SUVIN_STAGE: suvin_raw_path,
        }
        heinlein_analysis: models.HeinleinAnalysis | None = None
        if options.include_heinlein:
            (
                heinlein_analysis,
                heinlein_response,
                heinlein_raw_path,
                heinlein_reused,
            ) = _run_heinlein_stage(
                story=story,
                prepared=prepared,
                evidence_set=evidence_set,
                options=options,
                active_backend=active_backend,
                output_root=output_root,
                run_id=run_id,
                log=log,
            )
            if not heinlein_reused:
                input_tokens += heinlein_response.input_tokens
                output_tokens += heinlein_response.output_tokens
            stage_paths[HEINLEIN_STAGE] = heinlein_raw_path
        _write_raw_artifact_index(
            output_root=output_root,
            story=story,
            run_id=run_id,
            stage_paths=stage_paths,
        )

        partial_success = _partial_success_record(
            knight_analysis, suvin_analysis, heinlein_analysis
        )
        sidecar_inputs = pipeline.SidecarAssemblyInputs(
            lcats_id=story.story_id,
            story_path=story.story_path,
            story_hash=prepared.story_hash,
            evidence_sets=(evidence_set,),
            knight_analyses=(knight_analysis,),
            suvin_novum_analyses=(suvin_analysis,),
            heinlein_analyses=(
                (heinlein_analysis,) if heinlein_analysis is not None else ()
            ),
            partial_success=partial_success,
            configuration=_sidecar_configuration(options),
        )
        assembled = pipeline.run_checkpointed_assembly(
            working_root=output_root,
            item_id=_checkpoint_item_id(story),
            inputs=sidecar_inputs,
            allow_protected_root=options.allow_protected_root,
        )
        sidecar_path = pipeline.publish_sidecar(
            output_root=output_root,
            item_id=story.story_id,
            data=assembled.data,
            allow_protected_root=options.allow_protected_root,
        )
        knight_analysis = sidecar_inputs.knight_analyses[0]
        suvin_analysis = sidecar_inputs.suvin_novum_analyses[0]
        heinlein_complete = (
            heinlein_analysis is not None and heinlein_analysis.status == "complete"
        )
        return StoryResult(
            run_id=run_id,
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
            qualified_novum_count=(
                sum(
                    1
                    for candidate in suvin_analysis.candidates
                    if candidate.qualified_novum
                )
                if suvin_analysis.status == "complete"
                else None
            ),
            dominant_novum_id=(
                suvin_analysis.dominant_novum_id
                if suvin_analysis.status == "complete"
                else None
            ),
            raw_response_path=_display_path(raw_response_dir),
            heinlein_verdict=(heinlein_analysis.verdict if heinlein_complete else None),
            heinlein_interval=(
                heinlein_analysis.interval.to_dict() if heinlein_complete else None
            ),
        )
    except Exception as error:
        input_tokens = getattr(error, "input_tokens", input_tokens)
        output_tokens = getattr(error, "output_tokens", output_tokens)
        raw_response_path = getattr(error, "raw_response_path", raw_response_path)
        tool_result = (
            suvin_tool_result
            if suvin_tool_result is not None
            else (
                knight_tool_result
                if knight_tool_result is not None
                else evidence_tool_result
            )
        )
        if raw_response_path is None and raw_response_dir is not None:
            backend_error_path = (
                raw_response_dir / f"{EVIDENCE_STAGE}-backend-error.json"
            )
            if backend_error_path.exists():
                raw_response_path = backend_error_path
        quarantine_path = _write_quarantine(
            output_root=output_root,
            story=story,
            error=error,
            tool_result=tool_result,
            raw_response_path=raw_response_path or raw_response_dir,
            stage="story",
            run_id=run_id,
        )
        if log is not None:
            log.event(
                "story_quarantined",
                run_id=run_id,
                story_id=story.story_id,
                quarantine_path=_display_path(quarantine_path),
                failure_kind=type(error).__name__,
            )
        return StoryResult(
            run_id=run_id,
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
                _display_path(raw_response_path or raw_response_dir)
                if raw_response_path or raw_response_dir
                else None
            ),
            quarantine_path=(
                _display_path(quarantine_path) if quarantine_path else None
            ),
        )


def _append_story_result(
    output_root: pathlib.Path, result: StoryResult
) -> pathlib.Path:
    output_root.mkdir(parents=True, exist_ok=True)
    path = output_root / "worldcon_spike_story_results.jsonl"
    fd = os.open(
        path,
        os.O_WRONLY | os.O_APPEND | os.O_CREAT | _O_NOFOLLOW,
        0o644,
    )
    with os.fdopen(fd, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(result.to_dict(), sort_keys=True) + "\n")
        handle.flush()
    return path


def _run_checkpointed_model_stage(
    *,
    stage: str,
    story: SpikeStory,
    output_root: pathlib.Path,
    options: RunnerOptions,
    active_backend: llm_backend.LLMBackend,
    system_prompt: str,
    payload: dict[str, Any],
    tool_schema: dict[str, Any],
    run_id: str,
    log: run_log.RunLog | None,
    resume: bool,
    validate_result: Callable[[llm_backend.BackendResponse, Any], None],
) -> tuple[llm_backend.BackendResponse, Any, pathlib.Path, bool]:
    """Run a model stage, reusing a matching persisted response on resume."""

    fingerprint = _model_stage_fingerprint(
        stage=stage,
        options=options,
        system_prompt=system_prompt,
        payload=payload,
        tool_schema=tool_schema,
    )

    def materialize() -> dict[str, Any]:
        response, tool_result, raw_path, _ = _run_model_stage(
            stage=stage,
            story=story,
            output_root=output_root,
            options=options,
            active_backend=active_backend,
            system_prompt=system_prompt,
            payload=payload,
            tool_schema=tool_schema,
            run_id=run_id,
            log=log,
        )
        try:
            validate_result(response, tool_result)
        except Exception as error:
            error.raw_response_path = raw_path
            error.input_tokens = response.input_tokens
            error.output_tokens = response.output_tokens
            raise
        return _checkpoint_response_data(
            response, tool_result, raw_path, stage=stage, run_id=run_id
        )

    checkpointed = pipeline.run_checkpointed_stage(
        working_root=output_root,
        item_id=_checkpoint_item_id(story),
        stage=stage,
        fingerprint=fingerprint,
        materialize=materialize,
        validate_reuse=lambda data: _valid_checkpoint_response(data, output_root),
        allow_protected_root=options.allow_protected_root,
        reuse_existing=resume,
    )
    data = checkpointed.data
    response = _response_from_checkpoint_data(data)
    response.checkpoint_reused = checkpointed.reused
    response.source_run_id = data.get("source_run_id")
    response.source_code_commit = data.get("source_code_commit")
    raw_path = _stored_path(data["raw_response_path"])
    try:
        validate_result(response, data["tool_result"])
    except Exception:
        if not checkpointed.reused:
            raise
        checkpointed = pipeline.run_checkpointed_stage(
            working_root=output_root,
            item_id=_checkpoint_item_id(story),
            stage=stage,
            fingerprint=fingerprint,
            materialize=materialize,
            validate_reuse=lambda value: _valid_checkpoint_response(value, output_root),
            allow_protected_root=options.allow_protected_root,
            reuse_existing=False,
        )
        data = checkpointed.data
        response = _response_from_checkpoint_data(data)
        response.checkpoint_reused = False
        response.source_run_id = data.get("source_run_id")
        response.source_code_commit = data.get("source_code_commit")
        raw_path = _stored_path(data["raw_response_path"])
    if log is not None and checkpointed.reused:
        log.event(
            "stage_reused",
            run_id=run_id,
            story_id=story.story_id,
            stage=stage,
            checkpoint_fingerprint=fingerprint["sha256"],
            raw_response_path=_display_path(raw_path),
        )
    return response, data["tool_result"], raw_path, checkpointed.reused


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
    run_id: str,
    log: run_log.RunLog | None,
) -> tuple[llm_backend.BackendResponse, Any, pathlib.Path]:
    """Run one persisted model stage and return its raw tool result."""

    if log is not None:
        log.event("stage_start", run_id=run_id, story_id=story.story_id, stage=stage)
    attempt = 1
    max_tokens = options.max_tokens
    total_input_tokens = 0
    total_output_tokens = 0
    retried_kinds: set[str] = set()
    raw_response: llm_backend.BackendResponse | None = None
    while True:
        try:
            response = active_backend.complete(
                system=system_prompt,
                messages=[{"role": "user", "content": _stable_json(payload)}],
                model=options.model,
                temperature=options.temperature,
                max_tokens=max_tokens,
                tool=tool_schema,
            )
            raw_response = response
            raw_response.effective_max_tokens = max_tokens
            response = dataclasses.replace(
                response,
                input_tokens=response.input_tokens + total_input_tokens,
                output_tokens=response.output_tokens + total_output_tokens,
            )
            response.effective_max_tokens = max_tokens
            break
        except llm_backend.NoToolCallError as error:
            if error.raw_content:
                response = llm_backend.BackendResponse(
                    text=error.raw_content,
                    tool_result=None,
                    model=options.model,
                    input_tokens=error.input_tokens,
                    output_tokens=error.output_tokens,
                )
                response.effective_max_tokens = max_tokens
                raw_response = response
                response = dataclasses.replace(
                    response,
                    input_tokens=response.input_tokens + total_input_tokens,
                    output_tokens=response.output_tokens + total_output_tokens,
                )
                response.effective_max_tokens = max_tokens
                if log is not None:
                    log.event(
                        "no_tool_call_json_fallback",
                        run_id=run_id,
                        story_id=story.story_id,
                        stage=stage,
                        input_tokens=error.input_tokens,
                        output_tokens=error.output_tokens,
                    )
                break
            _persist_backend_failure(
                output_root, run_id, story, stage, error, attempt, log
            )
            total_input_tokens += getattr(error, "input_tokens", 0)
            total_output_tokens += getattr(error, "output_tokens", 0)
            _attach_usage(error, total_input_tokens, total_output_tokens, max_tokens)
            error.raw_response_path = (
                output_root
                / "_raw"
                / run_id
                / _checkpoint_item_id(story)
                / (
                    f"{stage}-backend-error.json"
                    if attempt == 1
                    else f"{stage}-backend-error-attempt-{attempt}.json"
                )
            )
            raise
        except Exception as error:
            kind = _classify_stage_failure(error)
            error_input = getattr(error, "input_tokens", 0)
            error_output = getattr(error, "output_tokens", 0)
            total_input_tokens += error_input
            total_output_tokens += error_output
            error.effective_max_tokens = max_tokens
            raw_path = _persist_backend_failure(
                output_root, run_id, story, stage, error, attempt, log
            )
            if kind in {"truncation", "transient"} and kind not in retried_kinds:
                retried_kinds.add(kind)
                attempt += 1
                if kind == "truncation":
                    max_tokens *= TRUNCATION_RETRY_MULTIPLIER
                if log is not None:
                    log.event(
                        "stage_retry",
                        run_id=run_id,
                        story_id=story.story_id,
                        stage=stage,
                        failure_kind=kind,
                        attempt=attempt,
                        max_tokens=max_tokens,
                    )
                time.sleep(
                    min(
                        RETRY_BACKOFF_SECONDS * (2 ** (attempt - 2)),
                        RETRY_BACKOFF_MAX_SECONDS,
                    )
                )
                continue
            error.raw_response_path = raw_path
            _attach_usage(error, total_input_tokens, total_output_tokens, max_tokens)
            raise
    tool_result = response.tool_result
    raw_path = _write_raw_response(
        output_root=output_root,
        story=story,
        response=raw_response or response,
        tool_result=tool_result,
        stage=stage,
        run_id=run_id,
        attempt=attempt,
    )
    if log is not None:
        log.event(
            "model_response_received",
            run_id=run_id,
            story_id=story.story_id,
            stage=stage,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            raw_response_path=_display_path(raw_path),
        )
    if tool_result is None:
        try:
            tool_result = json.loads(response.text)
        except json.JSONDecodeError as error:
            error.raw_response_path = raw_path
            error.input_tokens = response.input_tokens
            error.output_tokens = response.output_tokens
            error.effective_max_tokens = getattr(
                response, "effective_max_tokens", max_tokens
            )
            raise
        raw_path = _write_raw_response(
            output_root=output_root,
            story=story,
            response=raw_response or response,
            tool_result=tool_result,
            stage=stage,
            run_id=run_id,
            attempt=attempt,
        )
    if log is not None:
        log.event("stage_end", run_id=run_id, story_id=story.story_id, stage=stage)
    response.raw_input_tokens = (raw_response or response).input_tokens
    response.raw_output_tokens = (raw_response or response).output_tokens
    response.story_id = story.story_id
    response.checkpoint_reused = False
    return response, tool_result, raw_path, False


def _model_stage_fingerprint(
    *,
    stage: str,
    options: RunnerOptions,
    system_prompt: str,
    payload: dict[str, Any],
    tool_schema: dict[str, Any],
) -> dict[str, Any]:
    """Identify every effective input that can change a model-stage result."""

    data = {
        "version": "worldcon-spike-stage-fingerprint-v1",
        "stage": stage,
        "backend_kind": options.backend_kind,
        "model": options.model,
        "base_url": options.base_url,
        "temperature": options.temperature,
        "max_tokens": options.max_tokens,
        "system_prompt_sha256": _hash_text(system_prompt),
        "tool_schema_sha256": _hash_text(_stable_json(tool_schema)),
        "payload_sha256": _hash_text(_stable_json(payload)),
    }
    return {
        "version": data["version"],
        "sha256": _hash_text(_stable_json(data)),
        "inputs": data,
    }


def _checkpoint_response_data(
    response: llm_backend.BackendResponse,
    tool_result: Any,
    raw_path: pathlib.Path,
    *,
    stage: str,
    run_id: str,
) -> dict[str, Any]:
    return {
        "model": response.model,
        "story_id": getattr(response, "story_id", None),
        "stage": stage,
        "source_run_id": run_id,
        "source_code_commit": _git_commit(),
        "input_tokens": response.input_tokens,
        "output_tokens": response.output_tokens,
        "raw_input_tokens": getattr(
            response, "raw_input_tokens", response.input_tokens
        ),
        "raw_output_tokens": getattr(
            response, "raw_output_tokens", response.output_tokens
        ),
        "effective_max_tokens": getattr(response, "effective_max_tokens", None),
        "cache_creation_input_tokens": response.cache_creation_input_tokens,
        "cache_read_input_tokens": response.cache_read_input_tokens,
        "effective_max_tokens": getattr(response, "effective_max_tokens", None),
        "text": response.text,
        "tool_result": tool_result,
        "raw_response_path": str(raw_path.resolve()),
    }


def _valid_checkpoint_response(data: Any, output_root: pathlib.Path) -> bool:
    raw_path = data.get("raw_response_path") if isinstance(data, dict) else None
    raw_path_obj = pathlib.Path(raw_path) if isinstance(raw_path, str) else None
    token_fields_valid = isinstance(data, dict) and all(
        isinstance(data.get(name), int)
        and not isinstance(data.get(name), bool)
        and data.get(name) >= 0
        for name in ("input_tokens", "output_tokens")
    )
    effective_limit = (
        data.get("effective_max_tokens") if isinstance(data, dict) else None
    )
    effective_limit_valid = effective_limit is None or (
        isinstance(effective_limit, int)
        and not isinstance(effective_limit, bool)
        and effective_limit > 0
    )
    try:
        contained = raw_path_obj is not None and raw_path_obj.resolve().is_relative_to(
            output_root.resolve()
        )
    except FileNotFoundError:
        contained = False
    return (
        isinstance(data, dict)
        and isinstance(data.get("model"), str)
        and isinstance(data.get("tool_result"), dict)
        and isinstance(raw_path, str)
        and isinstance(data.get("stage"), str)
        and isinstance(data.get("source_run_id"), str)
        and isinstance(data.get("source_code_commit"), str)
        and isinstance(data.get("story_id"), str)
        and data.get("story_id")
        and all(
            isinstance(data.get(name), int)
            and not isinstance(data.get(name), bool)
            and data.get(name) >= 0
            for name in ("raw_input_tokens", "raw_output_tokens")
        )
        and token_fields_valid
        and effective_limit_valid
        # Older relative checkpoints are ambiguous across package/repository
        # roots; rematerialize them instead of guessing which artifact they mean.
        and raw_path_obj.is_absolute()
        and contained
        and raw_path_obj.is_file()
        and _valid_raw_checkpoint_artifact(raw_path_obj, data)
    )


def _valid_raw_checkpoint_artifact(
    raw_path: pathlib.Path, checkpoint_data: dict[str, Any]
) -> bool:
    try:
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False
    return (
        isinstance(raw, dict)
        and raw.get("stage") == checkpoint_data.get("stage")
        and raw.get("run_id") == checkpoint_data.get("source_run_id")
        and raw.get("story_id") == checkpoint_data.get("story_id")
        and raw.get("model") == checkpoint_data.get("model")
        and isinstance(raw.get("tool_result"), dict)
        and raw.get("tool_result") == checkpoint_data.get("tool_result")
        and raw.get("input_tokens") == checkpoint_data.get("raw_input_tokens")
        and raw.get("output_tokens") == checkpoint_data.get("raw_output_tokens")
        and raw.get("effective_max_tokens")
        == checkpoint_data.get("effective_max_tokens")
    )


def _response_from_checkpoint_data(data: dict[str, Any]) -> llm_backend.BackendResponse:
    response = llm_backend.BackendResponse(
        text=data.get("text", ""),
        tool_result=data.get("tool_result"),
        model=data["model"],
        input_tokens=int(data.get("input_tokens", 0)),
        output_tokens=int(data.get("output_tokens", 0)),
        cache_creation_input_tokens=data.get("cache_creation_input_tokens"),
        cache_read_input_tokens=data.get("cache_read_input_tokens"),
    )
    response.effective_max_tokens = data.get("effective_max_tokens")
    return response


def _stored_path(value: str) -> pathlib.Path:
    """Resolve a persisted display path independent of the caller's CWD."""

    path = pathlib.Path(value)
    if path.is_absolute():
        return path
    package_root = paths.find_pyproject_root(__file__).resolve()
    package_path = package_root / path
    if package_path.exists():
        return package_path
    return _repo_root() / path


def _classify_stage_failure(error: Exception) -> str:
    message = str(error).lower()
    if isinstance(error, llm_backend.TruncatedResponseError):
        return "truncation"
    if isinstance(error, (ValueError, json.JSONDecodeError)):
        return "validation"
    if any(
        token in message
        for token in ("content filter", "content_filter", "safety filter")
    ):
        return "content_filter"
    if isinstance(
        error, (llm_backend.TransientProviderError, TimeoutError, ConnectionError)
    ):
        return "transient"
    status = next(
        (
            getattr(error, name)
            for name in ("status_code", "http_status", "status")
            if getattr(error, name, None) is not None
        ),
        None,
    )
    try:
        if int(status) in {429, 500, 502, 503, 504, 529}:
            return "transient"
    except (TypeError, ValueError):
        pass
    if any(
        token in message
        for token in (
            "timeout",
            "timed out",
            "temporarily unavailable",
            "service unavailable",
            "connection",
            "disconnected",
            "rate limit",
            "429",
            "overloaded",
        )
    ):
        return "transient"
    return "unknown"


def _attach_usage(
    error: Exception, input_tokens: int, output_tokens: int, effective_max_tokens: int
) -> None:
    error.input_tokens = input_tokens
    error.output_tokens = output_tokens
    error.effective_max_tokens = effective_max_tokens


def _persist_backend_failure(
    output_root: pathlib.Path,
    run_id: str,
    story: SpikeStory,
    stage: str,
    error: Exception,
    attempt: int,
    log: run_log.RunLog | None,
) -> pathlib.Path:
    raw_path = _write_backend_failure(
        output_root=output_root,
        run_id=run_id,
        story=story,
        stage=stage,
        error=error,
        attempt=attempt,
    )
    if log is not None:
        log.event(
            "backend_failure_persisted",
            run_id=run_id,
            story_id=story.story_id,
            stage=stage,
            attempt=attempt,
            failure_kind=_classify_stage_failure(error),
            raw_response_path=_display_path(raw_path),
        )
    return raw_path


def _write_raw_response(
    *,
    output_root: pathlib.Path,
    story: SpikeStory,
    response: llm_backend.BackendResponse,
    tool_result: Any,
    run_id: str,
    stage: str = "combined",
    attempt: int = 1,
) -> pathlib.Path:
    filename = f"{stage}.json" if attempt == 1 else f"{stage}-attempt-{attempt}.json"
    path = output_root / "_raw" / run_id / _checkpoint_item_id(story) / filename
    payload = {
        "run_id": run_id,
        "story_id": story.story_id,
        "story_path": story.story_path,
        "title": story.title,
        "stage": stage,
        "attempt": attempt,
        "model": response.model,
        "effective_max_tokens": getattr(response, "effective_max_tokens", None),
        "input_tokens": response.input_tokens,
        "output_tokens": response.output_tokens,
        "cache_creation_input_tokens": response.cache_creation_input_tokens,
        "cache_read_input_tokens": response.cache_read_input_tokens,
        "text": response.text,
        "tool_result": tool_result,
    }
    _write_json_atomic(path, payload, output_root=output_root)
    return path


def _write_raw_artifact_index(
    *,
    output_root: pathlib.Path,
    story: SpikeStory,
    run_id: str,
    stage_paths: dict[str, pathlib.Path],
) -> pathlib.Path:
    """Materialize a current-run index for raw artifacts, including reused ones."""

    path = output_root / "_raw" / run_id / _checkpoint_item_id(story) / "index.json"
    _write_json_atomic(
        path,
        {
            "run_id": run_id,
            "story_id": story.story_id,
            "stages": {
                stage: {
                    "selected": str(stage_path.resolve()),
                    "attempts": sorted(
                        str(path.resolve())
                        for path in stage_path.parent.glob(f"{stage}*.json")
                    ),
                }
                for stage, stage_path in stage_paths.items()
            },
        },
        output_root=output_root,
    )
    return path


def _write_backend_failure(
    *,
    output_root: pathlib.Path,
    run_id: str,
    story: SpikeStory,
    stage: str,
    error: Exception,
    attempt: int = 1,
) -> pathlib.Path:
    filename = (
        f"{stage}-backend-error.json"
        if attempt == 1
        else f"{stage}-backend-error-attempt-{attempt}.json"
    )
    path = output_root / "_raw" / run_id / _checkpoint_item_id(story) / filename
    payload = {
        "run_id": run_id,
        "story_id": story.story_id,
        "story_path": story.story_path,
        "title": story.title,
        "stage": stage,
        "attempt": attempt,
        "backend_error": type(error).__name__,
        "error_message": str(error),
        "input_tokens": getattr(error, "input_tokens", 0),
        "output_tokens": getattr(error, "output_tokens", 0),
        "effective_max_tokens": getattr(error, "effective_max_tokens", None),
        "raw_content": getattr(error, "raw_content", None),
    }
    _write_json_atomic(path, payload, output_root=output_root)
    return path


def _write_quarantine(
    *,
    output_root: pathlib.Path,
    story: SpikeStory,
    error: Exception,
    tool_result: Any,
    raw_response_path: pathlib.Path | None,
    run_id: str,
    stage: str = "story",
) -> pathlib.Path:
    path = (
        output_root
        / "_quarantine"
        / run_id
        / _checkpoint_item_id(story)
        / f"{stage}.json"
    )
    payload = {
        "run_id": run_id,
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
    _write_json_atomic(path, payload, output_root=output_root)
    return path


def _write_json_atomic(
    path: pathlib.Path, data: Any, *, output_root: pathlib.Path
) -> None:
    resolved_root = output_root.resolve()
    if resolved_root.is_symlink():
        raise ValueError(f"output root must not be a symlink: {output_root}")
    resolved_path = path.resolve(strict=False)
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError as error:
        raise ValueError(f"artifact escapes output root: {path}") from error
    relative_parent = resolved_path.parent.relative_to(resolved_root)
    current = resolved_root
    for part in relative_parent.parts:
        current = current / part
        if current.exists() and current.is_symlink():
            raise ValueError(f"artifact directory must not be a symlink: {current}")
    resolved_root.mkdir(parents=True, exist_ok=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        fd = os.open(
            tmp_path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | _O_NOFOLLOW,
            0o644,
        )
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(_stable_json(data))
            handle.flush()
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
    run_id: str,
    log: run_log.RunLog | None,
) -> tuple[models.KnightAnalysis, llm_backend.BackendResponse, pathlib.Path, bool]:
    response = _empty_response(options)
    tool_result: Any = None
    raw_path: pathlib.Path | None = None
    reused = False
    system_prompt = _knight_system_prompt()
    tool_schema = _knight_tool_schema()
    provenance = _provenance(
        story=story,
        options=options,
        response=response,
        parent_evidence_set_id=evidence_set.evidence_set_id,
        system_prompt=system_prompt,
        tool_schema=tool_schema,
        run_id=run_id,
        rubric_version=models.KNIGHT_RUBRIC_VERSION,
    )
    try:
        response, tool_result, raw_path, reused = _run_checkpointed_model_stage(
            stage=KNIGHT_STAGE,
            story=story,
            output_root=output_root,
            options=options,
            active_backend=active_backend,
            system_prompt=system_prompt,
            payload=_knight_payload(story, prepared, evidence_set),
            tool_schema=tool_schema,
            run_id=run_id,
            log=log,
            resume=options.resume,
            validate_result=lambda response, result: knight.build_analysis(
                analysis_id=f"{_stable_slug(story.story_id)}-knight-v1",
                story_hash=prepared.story_hash,
                evidence_set=evidence_set,
                decisions=_knight_decisions(result, evidence_set),
                provenance=_provenance(
                    story=story,
                    options=options,
                    response=response,
                    parent_evidence_set_id=evidence_set.evidence_set_id,
                    system_prompt=system_prompt,
                    tool_schema=tool_schema,
                    run_id=run_id,
                    rubric_version=models.KNIGHT_RUBRIC_VERSION,
                ),
            ),
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
            run_id=run_id,
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
            raw_path,
            reused,
        )
    except Exception as error:
        raw_path = getattr(error, "raw_response_path", raw_path)
        response = dataclasses.replace(
            response,
            input_tokens=getattr(error, "input_tokens", response.input_tokens),
            output_tokens=getattr(error, "output_tokens", response.output_tokens),
        )
        response.effective_max_tokens = getattr(
            error,
            "effective_max_tokens",
            getattr(response, "effective_max_tokens", None),
        )
        provenance = _provenance(
            story=story,
            options=options,
            response=response,
            parent_evidence_set_id=evidence_set.evidence_set_id,
            system_prompt=system_prompt,
            tool_schema=tool_schema,
            run_id=run_id,
            rubric_version=models.KNIGHT_RUBRIC_VERSION,
        )
        if raw_path is None:
            candidate = (
                output_root
                / "_raw"
                / run_id
                / _checkpoint_item_id(story)
                / f"{KNIGHT_STAGE}-backend-error.json"
            )
            if candidate.exists():
                raw_path = candidate
        _record_stage_failure(
            output_root=output_root,
            story=story,
            stage=KNIGHT_STAGE,
            error=error,
            tool_result=tool_result,
            raw_path=raw_path,
            run_id=run_id,
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
            raw_path or output_root / "_raw" / run_id / _checkpoint_item_id(story),
            reused,
        )


def _validate_suvin_result(
    *,
    story: SpikeStory,
    prepared: preparation.StoryPreparation,
    evidence_set: evidence.EvidenceSet,
    options: RunnerOptions,
    response: llm_backend.BackendResponse,
    result: Any,
    run_id: str,
    system_prompt: str,
    tool_schema: dict[str, Any],
) -> None:
    if not isinstance(result, dict):
        raise ValueError(f"{SUVIN_STAGE} tool_result must be an object")
    candidates = _novum_candidates(result, evidence_set)
    novum.build_analysis(
        analysis_id=f"{_stable_slug(story.story_id)}-suvin-v1",
        story_hash=prepared.story_hash,
        evidence_set=evidence_set,
        candidates=candidates,
        provenance=_provenance(
            story=story,
            options=options,
            response=response,
            parent_evidence_set_id=evidence_set.evidence_set_id,
            system_prompt=system_prompt,
            tool_schema=tool_schema,
            run_id=run_id,
            rubric_version=models.SUVIN_RUBRIC_VERSION,
        ),
        dominant_novum_id=_dominant_novum_id(
            result.get("dominant_novum_id"), candidates
        ),
    )


def _run_suvin_stage(
    *,
    story: SpikeStory,
    prepared: preparation.StoryPreparation,
    evidence_set: evidence.EvidenceSet,
    options: RunnerOptions,
    active_backend: llm_backend.LLMBackend,
    output_root: pathlib.Path,
    run_id: str,
    log: run_log.RunLog | None,
) -> tuple[models.SuvinNovumAnalysis, llm_backend.BackendResponse, pathlib.Path, bool]:
    response = _empty_response(options)
    tool_result: Any = None
    raw_path: pathlib.Path | None = None
    reused = False
    system_prompt = _suvin_system_prompt()
    tool_schema = _suvin_tool_schema()
    provenance = _provenance(
        story=story,
        options=options,
        response=response,
        parent_evidence_set_id=evidence_set.evidence_set_id,
        system_prompt=system_prompt,
        tool_schema=tool_schema,
        run_id=run_id,
        rubric_version=models.SUVIN_RUBRIC_VERSION,
    )
    try:
        response, tool_result, raw_path, reused = _run_checkpointed_model_stage(
            stage=SUVIN_STAGE,
            story=story,
            output_root=output_root,
            options=options,
            active_backend=active_backend,
            system_prompt=system_prompt,
            payload=_suvin_payload(story, prepared, evidence_set),
            tool_schema=tool_schema,
            run_id=run_id,
            log=log,
            resume=options.resume,
            validate_result=lambda response, result: _validate_suvin_result(
                story=story,
                prepared=prepared,
                evidence_set=evidence_set,
                options=options,
                response=response,
                result=result,
                run_id=run_id,
                system_prompt=system_prompt,
                tool_schema=tool_schema,
            ),
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
            run_id=run_id,
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
            raw_path,
            reused,
        )
    except Exception as error:
        raw_path = getattr(error, "raw_response_path", raw_path)
        response = dataclasses.replace(
            response,
            input_tokens=getattr(error, "input_tokens", response.input_tokens),
            output_tokens=getattr(error, "output_tokens", response.output_tokens),
        )
        response.effective_max_tokens = getattr(
            error,
            "effective_max_tokens",
            getattr(response, "effective_max_tokens", None),
        )
        provenance = _provenance(
            story=story,
            options=options,
            response=response,
            parent_evidence_set_id=evidence_set.evidence_set_id,
            system_prompt=system_prompt,
            tool_schema=tool_schema,
            run_id=run_id,
            rubric_version=models.SUVIN_RUBRIC_VERSION,
        )
        if raw_path is None:
            candidate = (
                output_root
                / "_raw"
                / run_id
                / _checkpoint_item_id(story)
                / f"{SUVIN_STAGE}-backend-error.json"
            )
            if candidate.exists():
                raw_path = candidate
        _record_stage_failure(
            output_root=output_root,
            story=story,
            stage=SUVIN_STAGE,
            error=error,
            tool_result=tool_result,
            raw_path=raw_path,
            run_id=run_id,
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
            raw_path or output_root / "_raw" / run_id / _checkpoint_item_id(story),
            reused,
        )


def _empty_response(options: RunnerOptions) -> llm_backend.BackendResponse:
    return llm_backend.BackendResponse(
        text="",
        tool_result=None,
        model=options.model,
        input_tokens=0,
        output_tokens=0,
    )


def _sidecar_configuration(options: RunnerOptions) -> dict[str, Any]:
    configuration: dict[str, Any] = {
        "backend_kind": options.backend_kind,
        "mode": options.mode,
        "model": options.model,
        "prompt_version": PROMPT_VERSION,
        "report_version": REPORT_VERSION,
    }
    if options.include_heinlein:
        configuration["heinlein_prompt_version"] = HEINLEIN_PROMPT_VERSION
    return configuration


def _run_heinlein_stage(
    *,
    story: SpikeStory,
    prepared: preparation.StoryPreparation,
    evidence_set: evidence.EvidenceSet,
    options: RunnerOptions,
    active_backend: llm_backend.LLMBackend,
    output_root: pathlib.Path,
    run_id: str,
    log: run_log.RunLog | None,
) -> tuple[models.HeinleinAnalysis, llm_backend.BackendResponse, pathlib.Path, bool]:
    """Run the optional Heinlein stage; a failure never affects other stages."""

    response = _empty_response(options)
    tool_result: Any = None
    raw_path: pathlib.Path | None = None
    reused = False
    system_prompt = _heinlein_system_prompt()
    tool_schema = _heinlein_tool_schema()
    analysis_id = f"{_stable_slug(story.story_id)}-heinlein-v1"

    def provenance_for(
        stage_response: llm_backend.BackendResponse,
    ) -> models.ProvenanceRecord:
        return _provenance(
            story=story,
            options=options,
            response=stage_response,
            parent_evidence_set_id=evidence_set.evidence_set_id,
            system_prompt=system_prompt,
            tool_schema=tool_schema,
            run_id=run_id,
            rubric_version=models.HEINLEIN_RUBRIC_VERSION,
        )

    try:
        response, tool_result, raw_path, reused = _run_checkpointed_model_stage(
            stage=HEINLEIN_STAGE,
            story=story,
            output_root=output_root,
            options=options,
            active_backend=active_backend,
            system_prompt=system_prompt,
            payload=_heinlein_payload(story, prepared, evidence_set),
            tool_schema=tool_schema,
            run_id=run_id,
            log=log,
            resume=options.resume,
            validate_result=lambda stage_response, result: heinlein.build_analysis(
                analysis_id=analysis_id,
                story_hash=prepared.story_hash,
                evidence_set=evidence_set,
                decisions=_heinlein_decisions(result, evidence_set),
                provenance=provenance_for(stage_response),
            ),
        )
        if not isinstance(tool_result, dict):
            raise ValueError(
                f"{HEINLEIN_STAGE} tool_result must be an object, "
                f"got {type(tool_result).__name__}"
            )
        return (
            heinlein.build_analysis(
                analysis_id=analysis_id,
                story_hash=prepared.story_hash,
                evidence_set=evidence_set,
                decisions=_heinlein_decisions(tool_result, evidence_set),
                provenance=provenance_for(response),
            ),
            response,
            raw_path,
            reused,
        )
    except Exception as error:
        raw_path = getattr(error, "raw_response_path", raw_path)
        response = dataclasses.replace(
            response,
            input_tokens=getattr(error, "input_tokens", response.input_tokens),
            output_tokens=getattr(error, "output_tokens", response.output_tokens),
        )
        response.effective_max_tokens = getattr(
            error,
            "effective_max_tokens",
            getattr(response, "effective_max_tokens", None),
        )
        if raw_path is None:
            candidate = (
                output_root
                / "_raw"
                / run_id
                / _checkpoint_item_id(story)
                / f"{HEINLEIN_STAGE}-backend-error.json"
            )
            if candidate.exists():
                raw_path = candidate
        _record_stage_failure(
            output_root=output_root,
            story=story,
            stage=HEINLEIN_STAGE,
            error=error,
            tool_result=tool_result,
            raw_path=raw_path,
            run_id=run_id,
            log=log,
        )
        failure = models.FailureRecord(
            stage=HEINLEIN_RECORD_STAGE,
            kind=type(error).__name__,
            message=str(error),
            recoverable=True,
        )
        return (
            heinlein.failed_analysis(
                analysis_id=analysis_id,
                story_hash=prepared.story_hash,
                evidence_set_id=evidence_set.evidence_set_id,
                provenance=provenance_for(response),
                failure=failure,
            ),
            response,
            raw_path or output_root / "_raw" / run_id / _checkpoint_item_id(story),
            reused,
        )


def _record_stage_failure(
    *,
    output_root: pathlib.Path,
    story: SpikeStory,
    stage: str,
    error: Exception,
    tool_result: Any,
    raw_path: pathlib.Path | None,
    run_id: str,
    log: run_log.RunLog | None,
) -> None:
    quarantine_path = _write_quarantine(
        output_root=output_root,
        story=story,
        error=error,
        tool_result=tool_result,
        raw_response_path=raw_path,
        stage=stage,
        run_id=run_id,
    )
    if log is not None:
        log.event(
            "stage_failed",
            run_id=run_id,
            story_id=story.story_id,
            stage=stage,
            failure_kind=type(error).__name__,
            quarantine_path=_display_path(quarantine_path),
        )


def _partial_success_record(
    knight_analysis: models.KnightAnalysis,
    suvin_analysis: models.SuvinNovumAnalysis,
    heinlein_analysis: models.HeinleinAnalysis | None = None,
) -> models.PartialSuccessRecord | None:
    completed = [EVIDENCE_RECORD_STAGE]
    failures: list[models.FailureRecord] = []
    if knight_analysis.status == "complete":
        completed.append(KNIGHT_RECORD_STAGE)
    failures.extend(knight_analysis.failures)
    if suvin_analysis.status == "complete":
        completed.append(SUVIN_RECORD_STAGE)
    failures.extend(suvin_analysis.failures)
    if heinlein_analysis is not None:
        if heinlein_analysis.status == "complete":
            completed.append(HEINLEIN_RECORD_STAGE)
        failures.extend(heinlein_analysis.failures)
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


def _heinlein_decisions(
    tool_result: dict[str, Any],
    evidence_set: evidence.EvidenceSet,
) -> tuple[heinlein.CriterionAdjudication, ...]:
    """Convert model output to decisions without inventing any evidence.

    Unlike the Knight path, a ``present`` decision with no valid supporting
    evidence is not given a fallback evidence ID; it fails contract validation
    and the stage is quarantined.
    """

    by_id = {
        item.get("criterion_id"): item
        for item in _list_field(tool_result, "heinlein_criteria")
        if isinstance(item, dict)
    }
    decisions = []
    for criterion_id in models.HEINLEIN_CRITERION_IDS:
        item = by_id.get(criterion_id, {})
        decisions.append(
            heinlein.CriterionAdjudication(
                criterion_id=criterion_id,
                status=_decision_state(item.get("status", "not_assessable")),
                supporting_evidence_ids=_existing_evidence_ids(
                    evidence_set,
                    _string_tuple(item.get("supporting_evidence_ids", ())),
                ),
                counterevidence_ids=_existing_evidence_ids(
                    evidence_set,
                    _string_tuple(item.get("counterevidence_ids", ())),
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
        raw = {
            "status": "not_assessable",
            "rationale": f"malformed {type(raw).__name__}",
        }
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
    run_id: str,
    parent_evidence_set_id: str,
    system_prompt: str,
    tool_schema: dict[str, Any],
    rubric_version: str,
) -> models.ProvenanceRecord:
    return models.ProvenanceRecord(
        run_id=run_id,
        rubric_version=rubric_version,
        code_commit=_git_commit(),
        backend=options.backend_kind,
        model=response.model,
        prompt_hash=_hash_text(system_prompt),
        schema_hash=_hash_text(_stable_json(tool_schema)),
        generation_parameters={
            "max_tokens": getattr(response, "effective_max_tokens", None)
            or options.max_tokens,
            "temperature": options.temperature,
            "reused_from_checkpoint": bool(
                getattr(response, "checkpoint_reused", False)
            ),
            "source_run_id": getattr(response, "source_run_id", None),
            "source_code_commit": getattr(response, "source_code_commit", None),
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


def _heinlein_payload(
    story: SpikeStory,
    prepared: preparation.StoryPreparation,
    evidence_set: evidence.EvidenceSet,
) -> dict[str, Any]:
    return {
        "stage": HEINLEIN_STAGE,
        "prompt_version": HEINLEIN_PROMPT_VERSION,
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
call anything a novum. Prefer fewer strong items to unsupported guesses. An
item is useful only when the quotation itself supports the assigned evidence
type; do not infer a criterion decision from a vague paraphrase. If a passage
could support more than one type, record the strongest neutral description and
do not duplicate it merely to increase coverage. If there is no clear passage,
return no item rather than inventing a quote or paragraph ID.

Before submitting, check every item: the quote is copied exactly, every
paragraph ID exists in the supplied story, the paraphrase is neutral, and the
evidence type is materially supported by the quote.
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

Decision states are distinct. Use present only when the story and at least one
supplied evidence record materially support the criterion. Use ambiguous when
the evidence supports a plausible reading but materiality or interpretation is
uncertain. Use absent when you considered the criterion and the story provides
no material instance. Use not_assessable only when the supplied evidence is
insufficient, conflicting, or unusable; do not use absent as a fallback for
missing evidence. A present or ambiguous decision must include valid
supporting evidence IDs and a short rationale. Never invent an evidence ID.

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

Operational examples for this experiment, not claims about Knight's exact
original wording: a contemporary telephone mentioned in passing is not
technology/invention; a time machine that drives the plot can support
technology/invention and future/remote past/time travel; a character who merely
asks questions has not thereby demonstrated scientific method. A criterion may
be absent even when a related word appears in the story.

Before submitting, check that all seven criteria appear exactly once, every
present or ambiguous criterion has supporting evidence, every cited ID exists,
and no criterion is marked present solely because another criterion is present.
Return exactly the schema keys; do not substitute criterion or assessment for
criterion_id or status.
""".strip()


def _heinlein_system_prompt() -> str:
    conditions = "\n".join(
        f"{slot.slot_id}: {slot.governing_text}"
        for slot in rubric_definitions.HEINLEIN_FIVE.text_slots
    )
    return f"""
You are the independent Heinlein adjudicator in an LCATS science-fiction
analysis. The story and shared neutral evidence are supplied by earlier
stages. Return only the record_heinlein_adjudication tool input.

Use rubric_id {models.HEINLEIN_RUBRIC_VERSION} and return exactly the five
criteria different, essential, human, causal, and plausible, each once. Use
present, ambiguous, absent, or not_assessable. Do not return a verdict, score,
probability, genre label, or arithmetic; Python derives the result.

The five conditions, from Robert A. Heinlein's description of the
"Simon-pure" science fiction story:
{conditions}

Decision states are distinct. Use present only when the story and at least one
supplied evidence record materially support the condition. Use ambiguous when
the evidence supports a plausible reading but the reading is uncertain. Use
absent when you considered the condition and the story does not meet it. Use
not_assessable only when the supplied evidence is insufficient, conflicting, or
unusable; do not use absent as a fallback for missing evidence. A present
decision must cite valid supporting evidence IDs and give a short rationale.
Never invent an evidence ID. Cite counterevidence IDs when they matter.

The conditions depend on one another. If different is absent, essential and
causal cannot be present. If human is absent, causal cannot be present.
Decisions that violate this are rejected.

Judge plausibility against established facts available to a general reader and
the story's own premises; do not penalize an explicitly rendered new theory
that explains established facts. Do not count decorative technology, a
different setting that changes nothing about the problem, or a problem that
would arise unchanged in the present day.

Before submitting, check that all five criteria appear exactly once, every
present criterion has supporting evidence, every cited ID exists, and no
criterion is marked present solely because another is present. Return exactly
the schema keys.
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

Use absent when the candidate fails a dimension after consideration, and
not_assessable only when the evidence is insufficient or conflicting. A
candidate with an unusual gadget but no story-level change may have novelty or
technology evidence while lacking narrative hegemony; it does not qualify.
Conversely, a candidate may qualify without present-day engineering detail if
the story develops a coherent cognitive or imaginary logic and the candidate
governs the narrative consequences. These are operational examples for this
experiment, not additions to Suvin's quoted theory.

Before submitting, check each candidate independently across novelty,
cognitive_validation, and narrative_hegemony; provide rationale and valid
evidence IDs for every present or ambiguous dimension; keep estrangement
evidence separate; and set dominant_novum_id only to a candidate that Python
can validate as conjunctively qualified.

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


def _heinlein_tool_schema() -> dict[str, Any]:
    criterion = {
        "type": "object",
        "properties": {
            "criterion_id": {
                "type": "string",
                "enum": list(models.HEINLEIN_CRITERION_IDS),
            },
            "status": {
                "type": "string",
                "enum": ["present", "ambiguous", "absent", "not_assessable"],
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
            "supporting_evidence_ids",
            "counterevidence_ids",
            "rationale",
            "confidence",
        ],
    }
    return tool_schema_module.strict_tool_schema(
        {
            "name": HEINLEIN_TOOL_NAME,
            "description": "Record five independent Heinlein criterion decisions.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "heinlein_criteria": {
                        "type": "array",
                        "items": criterion,
                    }
                },
                "required": ["heinlein_criteria"],
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


def _fake_heinlein_criteria() -> list[dict[str, Any]]:
    support = {
        "different": "ev-storyworld",
        "essential": "ev-consequence",
        "human": "ev-reaction",
        "causal": "ev-consequence",
        "plausible": "ev-explanation",
    }
    return [
        {
            "criterion_id": criterion_id,
            "status": "present",
            "supporting_evidence_ids": [support[criterion_id]],
            "counterevidence_ids": [],
            "rationale": "No-cost deterministic smoke decision.",
            "confidence": 0.5,
        }
        for criterion_id in models.HEINLEIN_CRITERION_IDS
    ]


def _fake_stage_result(
    payload: dict[str, Any], tool: dict[str, Any] | None
) -> dict[str, Any]:
    result = _fake_tool_result(payload)
    tool_name = tool.get("name") if isinstance(tool, dict) else None
    if tool_name == HEINLEIN_TOOL_NAME:
        return {"heinlein_criteria": _fake_heinlein_criteria()}
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
    if options.include_heinlein and _paid_call_requested(options, gate):
        raise ValueError(
            "the Heinlein stage adds a model call per story and is not covered "
            "by an approved paid-run estimate; use a no-cost backend"
        )
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
            raise ValueError(f"{options.mode} mode requires a successful smoke summary")
    if gate.requires_full_sample_approval and not options.approve_full_sample:
        raise ValueError("full mode requires --approve-full-sample")
    if _paid_call_requested(options, gate):
        _enforce_paid_run_gate(gate, options)
        _verify_paid_source_manifest(manifest)
        if options.mode != CANARY_MODE and options.prior_spend_usd is None:
            raise ValueError(
                "paid sample/full stages require --prior-spend-usd"
            )
        if options.prior_spend_usd is not None and (
            not math.isfinite(options.prior_spend_usd) or options.prior_spend_usd < 0
        ):
            raise ValueError("prior cumulative spend must be finite and non-negative")


def _paid_call_requested(options: RunnerOptions, gate: RunGate) -> bool:
    if options.backend_kind == FAKE_BACKEND:
        return False
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
        raise ValueError("paid model calls require approved_backend and approved_model")
    if gate.approved_backend != options.backend_kind:
        raise ValueError("paid model calls require backend to match approved_backend")
    if gate.approved_model != options.model:
        raise ValueError("paid model calls require model to match approved_model")
    if not math.isfinite(gate.estimated_cost_usd) or gate.estimated_cost_usd <= 0:
        raise ValueError("paid model calls require positive estimated_cost_usd")
    if not math.isfinite(gate.estimated_story_cost_usd) or gate.estimated_story_cost_usd <= 0:
        raise ValueError("paid model calls require positive estimated_story_cost_usd")
    if not math.isfinite(gate.cumulative_budget_usd) or gate.cumulative_budget_usd <= 0:
        raise ValueError("paid model calls require positive cumulative_budget_usd")
    if (
        gate.estimated_wall_clock_minutes is None
        or gate.estimated_wall_clock_minutes <= 0
    ):
        raise ValueError(
            "paid model calls require positive estimated_wall_clock_minutes"
        )
    if not gate.stop_conditions:
        raise ValueError("paid model calls require reviewed stop_conditions")


def _verify_paid_source_manifest(manifest: SpikeManifest) -> None:
    source_path = _repo_root() / manifest.source_worldcon_manifest
    if not manifest.source_worldcon_manifest_git_commit:
        raise ValueError("paid model calls require source manifest git commit")
    if not manifest.source_worldcon_manifest_sha256:
        raise ValueError("paid model calls require source manifest sha256")
    if len(manifest.source_worldcon_manifest_sha256) != 64:
        raise ValueError("source manifest sha256 must be 64 hexadecimal characters")
    if not source_path.is_file():
        raise ValueError(f"source manifest does not exist: {source_path}")
    digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
    if digest != manifest.source_worldcon_manifest_sha256:
        raise ValueError("source manifest sha256 does not match its contents")
    count = sum(1 for line in source_path.read_text(encoding="utf-8").splitlines() if line)
    if count != manifest.source_worldcon_manifest_expected_count:
        raise ValueError("source manifest story count does not match its declaration")
    git_path = f"{manifest.source_worldcon_manifest_git_commit}:{manifest.source_worldcon_manifest}"
    result = subprocess.run(
        ["git", "cat-file", "-e", git_path],
        cwd=_repo_root(),
        capture_output=True,
        check=False,
        text=True,
    )
    if result.returncode != 0:
        raise ValueError("source manifest git commit does not contain the manifest")


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
        raise ValueError(f"full sample source must contain {FULL_SAMPLE_LIMIT} stories")
    return tuple(stories)


def _summary(
    *,
    status: str,
    manifest: SpikeManifest,
    options: RunnerOptions,
    output_root: pathlib.Path,
    plan: dict[str, Any],
    results: Iterable[StoryResult],
    run_id: str,
    stop_reason: str | None = None,
) -> dict[str, Any]:
    story_results = tuple(results)
    return {
        "version": SUMMARY_VERSION,
        "run_id": run_id,
        "status": status,
        "decision": _stage_decision(status, options.mode, story_results, stop_reason),
        "work_item": manifest.work_item,
        "mode": options.mode,
        "backend_kind": options.backend_kind,
        "model": options.model,
        "code_commit": _git_commit(),
        "output_root": _display_path(output_root),
        "manifest_path": _display_path(manifest.manifest_path),
        "source_worldcon_manifest": manifest.source_worldcon_manifest,
        "plan": plan,
        "totals": {
            "stories": len(story_results),
            "complete": sum(1 for item in story_results if item.status == "complete"),
            "failed": sum(1 for item in story_results if item.status == "failed"),
            **(
                {"heinlein_verdicts": _heinlein_verdict_counts(story_results)}
                if options.include_heinlein
                else {}
            ),
            "input_tokens": sum(item.input_tokens for item in story_results),
            "output_tokens": sum(item.output_tokens for item in story_results),
            "latency_seconds": round(
                sum(item.latency_seconds for item in story_results),
                3,
            ),
            "estimated_cost_usd": round(
                len(story_results)
                * manifest.gates[options.mode].estimated_story_cost_usd,
                6,
            ),
            "prior_spend_usd": _effective_prior_spend(options),
            "cumulative_estimated_cost_usd": round(
                _effective_prior_spend(options)
                + len(story_results)
                * manifest.gates[options.mode].estimated_story_cost_usd,
                6,
            ),
        },
        "stories": [item.to_dict() for item in story_results],
    }


def _heinlein_verdict_counts(results: Iterable[StoryResult]) -> dict[str, int]:
    counts = {verdict: 0 for verdict in sorted(models.HEINLEIN_VERDICTS)}
    counts["unavailable"] = 0
    for item in results:
        counts[item.heinlein_verdict or "unavailable"] += 1
    return counts


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
        "code_commit": _git_commit(),
        "max_tokens": options.max_tokens,
        "temperature": options.temperature,
        "estimated_cost_usd": gate.estimated_cost_usd,
        "paid_model_calls_authorized": gate.paid_model_calls_authorized,
        "approve_paid": options.approve_paid,
        "approve_full_sample": options.approve_full_sample,
        "resume": options.resume,
        **({"include_heinlein": True} if options.include_heinlein else {}),
        "retry_policy": {
            "truncation": "once_with_doubled_max_tokens",
            "transient_provider_or_network": "once",
            "backoff": "bounded_exponential_0.25_to_2.0_seconds",
            "content_filter": "never",
            "deterministic_validation": "never",
        },
        "output_root": _display_path(output_root),
        "manifest_fingerprint": _manifest_fingerprint(manifest),
        "story_ids": [story.story_id for story in stories],
        "budget_usd": gate.estimated_cost_usd,
        "cumulative_budget_usd": gate.cumulative_budget_usd,
        "prior_spend_usd": _effective_prior_spend(options),
        "estimated_story_cost_usd": gate.estimated_story_cost_usd,
    }


def _write_summary(output_root: pathlib.Path, summary: dict[str, Any]) -> pathlib.Path:
    output_root.mkdir(parents=True, exist_ok=True)
    path = output_root / "worldcon_spike_summary.json"
    path.write_text(_stable_json(summary), encoding="utf-8")
    return path


def _budget_would_be_exceeded(gate: RunGate, story_count: int) -> bool:
    """Reserve the configured worst-case story estimate before each call."""

    return (
        gate.estimated_cost_usd > 0
        and gate.estimated_story_cost_usd > 0
        and story_count * gate.estimated_story_cost_usd > gate.estimated_cost_usd
    )


def _effective_prior_spend(options: RunnerOptions) -> float:
    return 0.0 if options.prior_spend_usd is None else options.prior_spend_usd


def _cumulative_budget_would_be_exceeded(
    gate: RunGate, prior_spend_usd: float, story_count: int
) -> bool:
    return (
        gate.cumulative_budget_usd > 0
        and prior_spend_usd + story_count * gate.estimated_story_cost_usd
        > gate.cumulative_budget_usd
    )


def _stage_decision(
    status: str,
    mode: str,
    results: tuple[StoryResult, ...],
    stop_reason: str | None,
) -> str:
    """Return an operational continuation decision, not a quality claim."""

    if status == "dry_run":
        return "pending"
    if not results:
        return "stop_and_revise"
    if stop_reason == "budget":
        return "stop_for_budget"
    complete = [item for item in results if item.status == "complete"]
    if mode == CANARY_MODE:
        positive = any(
            (item.knight_interval or {}).get("definite_count", 0) > 0
            or (item.qualified_novum_count or 0) > 0
            for item in complete
        )
        if len(complete) == len(results) and positive:
            return "proceed"
        if complete:
            return "proceed_with_limitations"
        return "stop_and_revise"
    if status == "complete":
        return "proceed"
    if complete:
        return "proceed_with_limitations"
    return "stop_and_revise"


def _write_approval_snapshot(
    output_root: pathlib.Path,
    *,
    manifest: SpikeManifest,
    options: RunnerOptions,
    plan: dict[str, Any],
    run_id: str,
) -> pathlib.Path:
    """Persist the resolved approval before any paid provider call."""

    snapshot = {
        "version": "worldcon-paid-run-approval-snapshot-v1",
        "run_id": run_id,
        "work_item": manifest.work_item,
        "manifest_path": _display_path(manifest.manifest_path),
        "manifest_fingerprint": plan["manifest_fingerprint"],
        "code_commit": plan["code_commit"],
        "backend_kind": options.backend_kind,
        "model": options.model,
        "temperature": options.temperature,
        "max_tokens": options.max_tokens,
        "mode": options.mode,
        "story_count": plan["story_count"],
        "story_ids": plan["story_ids"],
        "output_root": _display_path(output_root),
        "budget_usd": plan["budget_usd"],
        "cumulative_budget_usd": plan["cumulative_budget_usd"],
        "prior_spend_usd": plan["prior_spend_usd"],
        "source_manifest": {
            "path": manifest.source_worldcon_manifest,
            "git_commit": manifest.source_worldcon_manifest_git_commit,
            "sha256": manifest.source_worldcon_manifest_sha256,
            "story_count": manifest.source_worldcon_manifest_expected_count,
        },
        "configuration": {
            "prompt_version": PROMPT_VERSION,
            "prompt_sha256": {
                "evidence": _hash_text(_evidence_system_prompt()),
                "knight": _hash_text(_knight_system_prompt()),
                "suvin": _hash_text(_suvin_system_prompt()),
            },
            "rubric_versions": {
                "knight": models.KNIGHT_RUBRIC_VERSION,
                "suvin": models.SUVIN_RUBRIC_VERSION,
            },
            "schema_sha256": {
                "evidence": _hash_text(_stable_json(_evidence_tool_schema())),
                "knight": _hash_text(_stable_json(_knight_tool_schema())),
                "suvin": _hash_text(_stable_json(_suvin_tool_schema())),
            },
        },
        "configuration_fingerprint": _hash_text(
            _stable_json(
                {
                    "prompt_version": PROMPT_VERSION,
                    "prompt_sha256": {
                        "evidence": _hash_text(_evidence_system_prompt()),
                        "knight": _hash_text(_knight_system_prompt()),
                        "suvin": _hash_text(_suvin_system_prompt()),
                    },
                    "rubric_versions": {
                        "knight": models.KNIGHT_RUBRIC_VERSION,
                        "suvin": models.SUVIN_RUBRIC_VERSION,
                    },
                    "schema_sha256": {
                        "evidence": _hash_text(_stable_json(_evidence_tool_schema())),
                        "knight": _hash_text(_stable_json(_knight_tool_schema())),
                        "suvin": _hash_text(_stable_json(_suvin_tool_schema())),
                    },
                }
            )
        ),
        "retry_policy": plan["retry_policy"],
        "stop_conditions": list(manifest.gates[options.mode].stop_conditions),
        "restrictions": [
            "experiment-local outputs only",
            "no corpus sidecars",
            "no promotion commands",
            "no production integration",
            "no theoretical-accuracy or human-agreement claim",
        ],
        "user_authorization": "explicit staged paid-run authorization in task conversation",
        "decision": "pending",
    }
    output_root.mkdir(parents=True, exist_ok=True)
    path = output_root / "approval_snapshot.json"
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        immutable_existing = {
            key: value
            for key, value in existing.items()
            if key not in {"run_id", "decision"}
        }
        immutable_snapshot = {
            key: value
            for key, value in snapshot.items()
            if key not in {"run_id", "decision"}
        }
        if immutable_existing != immutable_snapshot:
            raise ValueError("existing approval_snapshot.json does not match this run")
        return path
    path.write_text(_stable_json(snapshot), encoding="utf-8")
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
        f"- Decision: `{summary['decision']}`",
        f"- Stories complete: `{summary['totals']['complete']}/{summary['totals']['stories']}`",
        f"- Input tokens: `{summary['totals']['input_tokens']}`",
        f"- Output tokens: `{summary['totals']['output_tokens']}`",
        f"- Latency seconds: `{summary['totals']['latency_seconds']}`",
        f"- Estimated cost USD: `{summary['totals']['estimated_cost_usd']}`",
        f"- Cumulative estimated cost USD: `{summary['totals']['cumulative_estimated_cost_usd']}`",
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
                *(
                    [f"- Heinlein verdict: `{item['heinlein_verdict']}`"]
                    if item.get("heinlein_verdict")
                    else []
                ),
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
    if summary["mode"] == CANARY_MODE:
        return (
            "Use the canary report to decide whether to revise the contracts "
            "or proceed to a larger sample; this is not theoretical validation."
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
        estimated_story_cost_usd=float(
            data.get("estimated_story_cost_usd", 0.0)
        ),
        requires_smoke_success=bool(data.get("requires_smoke_success", False)),
        requires_full_sample_approval=bool(
            data.get("requires_full_sample_approval", False)
        ),
        approved_backend=_optional_string(data.get("approved_backend")),
        approved_model=_optional_string(data.get("approved_model")),
        estimated_wall_clock_minutes=_optional_float(
            data.get("estimated_wall_clock_minutes")
        ),
        cumulative_budget_usd=float(data.get("cumulative_budget_usd", 0.0)),
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
    available = {
        record.evidence_id: record.evidence_id for record in evidence_set.records
    }
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
        "canary_stories": [
            dataclasses.asdict(item) for item in manifest.canary_stories
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
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=_repo_root(),
        capture_output=True,
        check=False,
        text=True,
    )
    if result.returncode != 0:
        return None
    commit = result.stdout.strip()
    return commit or None


def _new_run_id() -> str:
    return f"run-{uuid.uuid4().hex}"


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
    parser.add_argument(
        "--output-root", type=pathlib.Path, default=DEFAULT_RESULTS_ROOT
    )
    parser.add_argument(
        "--mode",
        choices=(SMOKE_MODE, SAMPLE_MODE, CANARY_MODE, FULL_MODE),
        default=SMOKE_MODE,
    )
    parser.add_argument(
        "--backend",
        dest="backend_kind",
        choices=(
            FAKE_BACKEND,
            OPENAI_BACKEND,
            OPENAI_COMPATIBLE_BACKEND,
            ANTHROPIC_BACKEND,
        ),
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
    parser.add_argument(
        "--resume",
        action="store_true",
        help="reuse matching successful model-stage checkpoints",
    )
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--prior-spend-usd", type=float)
    parser.add_argument(
        "--include-heinlein",
        action="store_true",
        help="also run the optional Heinlein five-condition stage (no-cost "
        "backends only)",
    )
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
        resume=args.resume,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        prior_spend_usd=args.prior_spend_usd,
        include_heinlein=args.include_heinlein,
    )


if __name__ == "__main__":
    raise SystemExit(main())
