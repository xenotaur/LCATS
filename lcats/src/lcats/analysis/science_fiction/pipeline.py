"""Checkpointed assembly for experiment-local science-fiction sidecars."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import pathlib
from typing import Any, Callable

from lcats.analysis.science_fiction import evidence
from lcats.analysis.science_fiction import models
from lcats.analysis.science_fiction import sidecar
from lcats.utils import checkpoint

ASSEMBLY_STAGE = "science-fiction-sidecar"
PIPELINE_FINGERPRINT_VERSION = "science-fiction-pipeline-fingerprint-v1"


@dataclasses.dataclass(frozen=True)
class SidecarAssemblyInputs:
    """Inputs needed to assemble one science-fiction sidecar."""

    lcats_id: str
    story_path: str
    story_hash: str
    evidence_sets: tuple[evidence.EvidenceSet, ...] = ()
    knight_analyses: tuple[models.KnightAnalysis, ...] = ()
    suvin_novum_analyses: tuple[models.SuvinNovumAnalysis, ...] = ()
    current: models.CurrentPointers | None = None
    partial_success: models.PartialSuccessRecord | None = None
    configuration: dict[str, Any] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass(frozen=True)
class CheckpointedStageResult:
    """A stage result plus checkpoint provenance."""

    data: Any
    fingerprint: dict[str, Any]
    reused: bool


def effective_fingerprint(inputs: SidecarAssemblyInputs) -> dict[str, Any]:
    """Return a versioned fingerprint over every effective assembly input."""

    payload = {
        "fingerprint_version": PIPELINE_FINGERPRINT_VERSION,
        "schema_version": models.SCIENCE_FICTION_SIDECAR_VERSION,
        "lcats_id": inputs.lcats_id,
        "story_path": inputs.story_path,
        "story_hash": inputs.story_hash,
        "evidence_sets": [item.to_dict() for item in inputs.evidence_sets],
        "knight_analyses": [item.to_dict() for item in inputs.knight_analyses],
        "suvin_novum_analyses": [
            item.to_dict() for item in inputs.suvin_novum_analyses
        ],
        "current": _select_current(inputs).to_dict(),
        "partial_success": (
            None if inputs.partial_success is None else inputs.partial_success.to_dict()
        ),
        "configuration": inputs.configuration,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return {
        "version": PIPELINE_FINGERPRINT_VERSION,
        "sha256": hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
        "inputs": payload,
    }


def assemble_sidecar(
    inputs: SidecarAssemblyInputs,
) -> models.ScienceFictionSidecarEnvelope:
    """Assemble and validate a science-fiction sidecar envelope."""

    envelope = models.ScienceFictionSidecarEnvelope(
        lcats_id=inputs.lcats_id,
        story_path=inputs.story_path,
        story_hash=inputs.story_hash,
        evidence_sets=inputs.evidence_sets,
        knight_analyses=inputs.knight_analyses,
        suvin_novum_analyses=inputs.suvin_novum_analyses,
        current=_select_current(inputs),
        partial_success=inputs.partial_success,
    )
    validation = envelope.validate()
    if not validation.valid:
        raise ValueError("assembled science-fiction sidecar failed validation")
    return envelope


def assemble_sidecar_data(inputs: SidecarAssemblyInputs) -> dict[str, Any]:
    """Assemble one validated sidecar as deterministic JSON-like data."""

    return sidecar.envelope_to_data(assemble_sidecar(inputs))


def run_checkpointed_stage(
    *,
    working_root: checkpoint.PathLike,
    item_id: str,
    stage: str,
    fingerprint: dict[str, Any],
    materialize: Callable[[], Any],
    validate_reuse: Callable[[Any], bool] | None = None,
    allow_protected_root: bool = False,
) -> CheckpointedStageResult:
    """Run or reuse one checkpointed stage.

    A matching successful checkpoint is reused. Missing, stale, malformed, or
    failed checkpoints are rematerialized. Ordinary stage exceptions are
    recorded as recoverable failure checkpoints before being re-raised.
    """

    roots = checkpoint.resolve_roots(
        working_root,
        allow_protected_root=allow_protected_root,
    )
    existing = checkpoint.read_checkpoint(
        roots.working_root,
        item_id,
        stage,
        fingerprint,
    )
    if existing.done:
        reusable = validate_reuse is None
        if validate_reuse is not None:
            try:
                reusable = validate_reuse(existing.data)
            except Exception:
                reusable = False
        if reusable:
            return CheckpointedStageResult(
                data=existing.data,
                fingerprint=fingerprint,
                reused=True,
            )

    try:
        data = materialize()
    except Exception as error:
        checkpoint.write_checkpoint(
            roots.working_root,
            item_id,
            stage,
            outcome="failure",
            fingerprint=fingerprint,
            data={
                "stage": stage,
                "kind": type(error).__name__,
                "message": str(error),
                "recoverable": True,
            },
        )
        raise

    checkpoint.write_checkpoint(
        roots.working_root,
        item_id,
        stage,
        outcome="success",
        fingerprint=fingerprint,
        data=data,
    )
    return CheckpointedStageResult(data=data, fingerprint=fingerprint, reused=False)


def run_checkpointed_assembly(
    *,
    working_root: checkpoint.PathLike,
    item_id: str,
    inputs: SidecarAssemblyInputs,
    allow_protected_root: bool = False,
) -> CheckpointedStageResult:
    """Assemble or reuse the validated sidecar checkpoint for one story."""

    fingerprint = effective_fingerprint(inputs)
    return run_checkpointed_stage(
        working_root=working_root,
        item_id=item_id,
        stage=ASSEMBLY_STAGE,
        fingerprint=fingerprint,
        materialize=lambda: assemble_sidecar_data(inputs),
        validate_reuse=lambda data: sidecar.validate_sidecar(data).valid,
        allow_protected_root=allow_protected_root,
    )


def publish_sidecar(
    *,
    output_root: checkpoint.PathLike,
    item_id: str,
    data: dict[str, Any],
    allow_protected_root: bool = False,
) -> pathlib.Path:
    """Publish a validated experiment-local ``science-fiction.json`` file."""

    roots = checkpoint.resolve_roots(
        output_root,
        allow_protected_root=allow_protected_root,
    )
    output_path = _sidecar_output_path(roots.working_root, item_id)
    sidecar_id = data.get("lcats_id")
    if sidecar_id != item_id:
        raise ValueError(
            f"item_id {item_id!r} does not match sidecar lcats_id {sidecar_id!r}"
        )
    sidecar.write_json_atomic(output_path, data)
    return output_path


def _sidecar_output_path(output_root: pathlib.Path, item_id: str) -> pathlib.Path:
    item_path = pathlib.PurePosixPath(item_id)
    if item_path.is_absolute() or not item_path.parts:
        raise ValueError(
            f"item_id must be a relative story bucket path, got {item_id!r}"
        )
    if any(part in ("", ".", "..") for part in item_path.parts):
        raise ValueError(
            f"item_id must not contain empty, dot, or parent segments: {item_id!r}"
        )
    return output_root.joinpath(*item_path.parts, sidecar.SIDECAR_FILENAME)


def _select_current(inputs: SidecarAssemblyInputs) -> models.CurrentPointers:
    if inputs.current is not None:
        return inputs.current
    current_evidence_set_id = (
        inputs.evidence_sets[-1].evidence_set_id if inputs.evidence_sets else None
    )
    return models.CurrentPointers(
        evidence_set_id=current_evidence_set_id,
        knight_analysis_id=_latest_complete_analysis_id(
            inputs.knight_analyses,
            current_evidence_set_id=current_evidence_set_id,
            story_hash=inputs.story_hash,
        ),
        suvin_novum_analysis_id=_latest_complete_analysis_id(
            inputs.suvin_novum_analyses,
            current_evidence_set_id=current_evidence_set_id,
            story_hash=inputs.story_hash,
        ),
    )


def _latest_complete_analysis_id(
    analyses: tuple[models.KnightAnalysis | models.SuvinNovumAnalysis, ...],
    *,
    current_evidence_set_id: str | None,
    story_hash: str,
) -> str | None:
    for analysis in reversed(analyses):
        if (
            analysis.status == "complete"
            and not analysis.failures
            and analysis.story_hash == story_hash
            and analysis.evidence_set_id == current_evidence_set_id
        ):
            return analysis.analysis_id
    return None
