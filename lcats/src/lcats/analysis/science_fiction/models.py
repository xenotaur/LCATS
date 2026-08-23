"""Versioned data contracts for science-fiction sidecar analysis.

These records intentionally define source-neutral structure and deterministic
summary behavior. They do not freeze Knight or Suvin rubric wording; source
dependent text remains represented by rubric metadata until approved primary
sources are supplied.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping, Sequence
from types import MappingProxyType
from typing import Any

from lcats.analysis.science_fiction import evidence

SCIENCE_FICTION_SIDECAR_VERSION = "science-fiction-sidecar-v1"
KNIGHT_RUBRIC_VERSION = "knight-seven-v1"
SUVIN_RUBRIC_VERSION = "suvin-novum-v1"

KNIGHT_CRITERION_IDS = tuple(f"criterion_{index}" for index in range(1, 8))

DECISION_STATES = frozenset(
    {
        "present",
        "ambiguous",
        "absent",
        "not_assessable",
    }
)
MATERIALITY_STATES = frozenset(
    {
        "central",
        "substantial",
        "incidental",
    }
)
ANALYSIS_STATES = frozenset(
    {
        "complete",
        "partial",
        "failed",
    }
)
VALIDATION_SEVERITIES = frozenset({"error", "warning"})


@dataclasses.dataclass(frozen=True)
class EvidenceReference:
    """A stable reference to neutral evidence in one evidence set."""

    evidence_set_id: str
    evidence_id: str

    def __post_init__(self) -> None:
        _require_non_empty_string(self.evidence_set_id, "evidence_set_id")
        _require_non_empty_string(self.evidence_id, "evidence_id")

    def to_dict(self) -> dict[str, str]:
        return {
            "evidence_set_id": self.evidence_set_id,
            "evidence_id": self.evidence_id,
        }


@dataclasses.dataclass(frozen=True)
class FailureRecord:
    """A deterministic, inspectable stage failure record."""

    stage: str
    kind: str
    message: str
    recoverable: bool = False

    def __post_init__(self) -> None:
        _require_non_empty_string(self.stage, "stage")
        _require_non_empty_string(self.kind, "kind")
        _require_non_empty_string(self.message, "message")

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class ValidationFinding:
    """One validation finding for science-fiction analysis contracts."""

    path: str
    severity: str
    kind: str
    message: str

    def __post_init__(self) -> None:
        _require_non_empty_string(self.path, "path")
        _require_choice(self.severity, VALIDATION_SEVERITIES, "severity")
        _require_non_empty_string(self.kind, "kind")
        _require_non_empty_string(self.message, "message")

    def to_dict(self) -> dict[str, str]:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class ValidationResult:
    """Validation result with structured findings."""

    valid: bool
    findings: tuple[ValidationFinding, ...] = ()

    @classmethod
    def from_findings(
        cls, findings: tuple[ValidationFinding, ...]
    ) -> "ValidationResult":
        return cls(
            valid=not any(finding.severity == "error" for finding in findings),
            findings=findings,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "findings": [finding.to_dict() for finding in self.findings],
        }


@dataclasses.dataclass(frozen=True)
class ProvenanceRecord:
    """Model, prompt, rubric, code, and cost provenance for one analysis run."""

    run_id: str
    rubric_version: str
    code_commit: str | None = None
    backend: str | None = None
    model: str | None = None
    prompt_hash: str | None = None
    schema_hash: str | None = None
    chunk_config_hash: str | None = None
    generation_parameters: MappingProxyType[str, Any] | dict[str, Any] = (
        dataclasses.field(default_factory=dict)
    )
    token_usage: MappingProxyType[str, int] | dict[str, int] = dataclasses.field(
        default_factory=dict
    )
    estimated_cost_usd: float | None = None
    generated_at: str | None = None
    parent_evidence_set_id: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty_string(self.run_id, "run_id")
        _require_non_empty_string(self.rubric_version, "rubric_version")
        if self.estimated_cost_usd is not None and self.estimated_cost_usd < 0:
            raise ValueError("estimated_cost_usd must be non-negative")
        generation_parameters = _freeze_mapping(self.generation_parameters)
        token_usage = dict(self.token_usage)
        object.__setattr__(self, "generation_parameters", generation_parameters)
        object.__setattr__(self, "token_usage", MappingProxyType(token_usage))
        for key, value in token_usage.items():
            _require_non_empty_string(key, "token_usage key")
            if not isinstance(value, int) or value < 0:
                raise ValueError("token_usage values must be non-negative integers")

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "rubric_version": self.rubric_version,
            "code_commit": self.code_commit,
            "backend": self.backend,
            "model": self.model,
            "prompt_hash": self.prompt_hash,
            "schema_hash": self.schema_hash,
            "chunk_config_hash": self.chunk_config_hash,
            "generation_parameters": _thaw_value(self.generation_parameters),
            "token_usage": dict(self.token_usage),
            "estimated_cost_usd": self.estimated_cost_usd,
            "generated_at": self.generated_at,
            "parent_evidence_set_id": self.parent_evidence_set_id,
        }


@dataclasses.dataclass(frozen=True)
class KnightCriterion:
    """One independently evidenced Knight criterion decision."""

    criterion_id: str
    status: str
    materiality: str | None = None
    supporting_evidence: tuple[EvidenceReference, ...] = ()
    counterevidence: tuple[EvidenceReference, ...] = ()
    rationale: str = ""
    confidence: float | None = None

    def __post_init__(self) -> None:
        _require_choice(
            self.criterion_id, frozenset(KNIGHT_CRITERION_IDS), "criterion_id"
        )
        _require_choice(self.status, DECISION_STATES, "status")
        if self.materiality is not None:
            _require_choice(self.materiality, MATERIALITY_STATES, "materiality")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if self.status == "present" and not self.supporting_evidence:
            raise ValueError("present Knight criteria require supporting evidence")
        if self.status in {"absent", "not_assessable"} and self.materiality is not None:
            raise ValueError(
                "materiality applies only to present or ambiguous criteria"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "criterion_id": self.criterion_id,
            "status": self.status,
            "materiality": self.materiality,
            "supporting_evidence": [
                reference.to_dict() for reference in self.supporting_evidence
            ],
            "counterevidence": [
                reference.to_dict() for reference in self.counterevidence
            ],
            "rationale": self.rationale,
            "confidence": self.confidence,
        }


@dataclasses.dataclass(frozen=True)
class KnightInterval:
    """Deterministic Knight definite/possible interval."""

    definite_count: int
    possible_count: int
    total_count: int = 7

    def __post_init__(self) -> None:
        if not 0 <= self.definite_count <= self.possible_count <= self.total_count:
            raise ValueError("invalid Knight interval")

    def to_dict(self) -> dict[str, int]:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class KnightAnalysis:
    """A seven-criterion Knight profile with deterministic interval arithmetic."""

    analysis_id: str
    story_hash: str
    evidence_set_id: str
    criteria: tuple[KnightCriterion, ...]
    provenance: ProvenanceRecord
    status: str = "complete"
    failures: tuple[FailureRecord, ...] = ()

    def __post_init__(self) -> None:
        _require_non_empty_string(self.analysis_id, "analysis_id")
        _require_non_empty_string(self.story_hash, "story_hash")
        _require_non_empty_string(self.evidence_set_id, "evidence_set_id")
        _require_choice(self.status, ANALYSIS_STATES, "status")
        if self.provenance.rubric_version != KNIGHT_RUBRIC_VERSION:
            raise ValueError("Knight analysis must use knight-seven-v1 provenance")
        criterion_ids = tuple(criterion.criterion_id for criterion in self.criteria)
        if sorted(criterion_ids) != sorted(KNIGHT_CRITERION_IDS):
            raise ValueError("Knight analysis must contain seven unique criteria")

    @property
    def interval(self) -> KnightInterval:
        definite_count = sum(
            1 for criterion in self.criteria if criterion.status == "present"
        )
        possible_count = sum(
            1
            for criterion in self.criteria
            if criterion.status in {"present", "ambiguous"}
        )
        return KnightInterval(
            definite_count=definite_count,
            possible_count=possible_count,
            total_count=len(self.criteria),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "analysis_id": self.analysis_id,
            "story_hash": self.story_hash,
            "evidence_set_id": self.evidence_set_id,
            "criteria": [criterion.to_dict() for criterion in self.criteria],
            "interval": self.interval.to_dict(),
            "provenance": self.provenance.to_dict(),
            "status": self.status,
            "failures": [failure.to_dict() for failure in self.failures],
        }


@dataclasses.dataclass(frozen=True)
class NovumDimensionDecision:
    """One novelty, cognition, or hegemony decision for a novum candidate."""

    status: str
    supporting_evidence: tuple[EvidenceReference, ...] = ()
    counterevidence: tuple[EvidenceReference, ...] = ()
    rationale: str = ""
    confidence: float | None = None

    def __post_init__(self) -> None:
        _require_choice(self.status, DECISION_STATES, "status")
        if self.status == "present" and not self.supporting_evidence:
            raise ValueError("present Novum dimensions require supporting evidence")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "supporting_evidence": [
                reference.to_dict() for reference in self.supporting_evidence
            ],
            "counterevidence": [
                reference.to_dict() for reference in self.counterevidence
            ],
            "rationale": self.rationale,
            "confidence": self.confidence,
        }


@dataclasses.dataclass(frozen=True)
class EstrangementProfile:
    """Reader-facing estrangement recorded separately from qualification."""

    reader_facing_evidence: tuple[EvidenceReference, ...] = ()
    storyworld_consequence_evidence: tuple[EvidenceReference, ...] = ()
    character_reaction_evidence: tuple[EvidenceReference, ...] = ()
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "reader_facing_evidence": [
                reference.to_dict() for reference in self.reader_facing_evidence
            ],
            "storyworld_consequence_evidence": [
                reference.to_dict()
                for reference in self.storyworld_consequence_evidence
            ],
            "character_reaction_evidence": [
                reference.to_dict() for reference in self.character_reaction_evidence
            ],
            "rationale": self.rationale,
        }


@dataclasses.dataclass(frozen=True)
class NovumCandidate:
    """A candidate novum adjudicated by the Suvin N/C/H conjunction."""

    candidate_id: str
    description: str
    novelty: NovumDimensionDecision
    cognitive_validation: NovumDimensionDecision
    narrative_hegemony: NovumDimensionDecision
    estrangement: EstrangementProfile = dataclasses.field(
        default_factory=EstrangementProfile
    )
    evidence: tuple[EvidenceReference, ...] = ()

    def __post_init__(self) -> None:
        _require_non_empty_string(self.candidate_id, "candidate_id")
        _require_non_empty_string(self.description, "description")

    @property
    def qualified_novum(self) -> bool:
        return (
            self.novelty.status == "present"
            and self.cognitive_validation.status == "present"
            and self.narrative_hegemony.status == "present"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "description": self.description,
            "novelty": self.novelty.to_dict(),
            "cognitive_validation": self.cognitive_validation.to_dict(),
            "narrative_hegemony": self.narrative_hegemony.to_dict(),
            "qualified_novum": self.qualified_novum,
            "estrangement": self.estrangement.to_dict(),
            "evidence": [reference.to_dict() for reference in self.evidence],
        }


@dataclasses.dataclass(frozen=True)
class NovumSystem:
    """A qualified system made of multiple interacting novum candidates."""

    system_id: str
    candidate_ids: tuple[str, ...]
    rationale: str = ""

    def __post_init__(self) -> None:
        _require_non_empty_string(self.system_id, "system_id")
        if len(self.candidate_ids) < 2:
            raise ValueError("novum systems require at least two candidates")
        _require_unique_strings(self.candidate_ids, "candidate_ids")

    def to_dict(self) -> dict[str, Any]:
        return {
            "system_id": self.system_id,
            "candidate_ids": list(self.candidate_ids),
            "rationale": self.rationale,
        }


@dataclasses.dataclass(frozen=True)
class SuvinNovumAnalysis:
    """Independent Suvin novum analysis over one evidence set."""

    analysis_id: str
    story_hash: str
    evidence_set_id: str
    candidates: tuple[NovumCandidate, ...]
    provenance: ProvenanceRecord
    dominant_novum_id: str | None = None
    novum_systems: tuple[NovumSystem, ...] = ()
    status: str = "complete"
    failures: tuple[FailureRecord, ...] = ()

    def __post_init__(self) -> None:
        _require_non_empty_string(self.analysis_id, "analysis_id")
        _require_non_empty_string(self.story_hash, "story_hash")
        _require_non_empty_string(self.evidence_set_id, "evidence_set_id")
        _require_choice(self.status, ANALYSIS_STATES, "status")
        if self.provenance.rubric_version != SUVIN_RUBRIC_VERSION:
            raise ValueError("Suvin analysis must use suvin-novum-v1 provenance")
        candidate_ids = tuple(candidate.candidate_id for candidate in self.candidates)
        _require_unique_strings(candidate_ids, "candidate_ids")
        qualified_ids = {
            candidate.candidate_id
            for candidate in self.candidates
            if candidate.qualified_novum
        }
        if (
            self.dominant_novum_id is not None
            and self.dominant_novum_id not in qualified_ids
        ):
            raise ValueError("dominant_novum_id must reference a qualified candidate")
        for system in self.novum_systems:
            missing = set(system.candidate_ids) - qualified_ids
            if missing:
                raise ValueError(
                    "novum systems may reference only qualified candidates"
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "analysis_id": self.analysis_id,
            "story_hash": self.story_hash,
            "evidence_set_id": self.evidence_set_id,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "dominant_novum_id": self.dominant_novum_id,
            "novum_systems": [system.to_dict() for system in self.novum_systems],
            "provenance": self.provenance.to_dict(),
            "status": self.status,
            "failures": [failure.to_dict() for failure in self.failures],
        }


@dataclasses.dataclass(frozen=True)
class CurrentPointers:
    """Current sidecar pointers selected by deterministic validation."""

    evidence_set_id: str | None = None
    knight_analysis_id: str | None = None
    suvin_novum_analysis_id: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class PartialSuccessRecord:
    """Records that one side of the analysis completed while another did not."""

    completed_stages: tuple[str, ...] = ()
    failed_stages: tuple[FailureRecord, ...] = ()

    def __post_init__(self) -> None:
        _require_unique_strings(self.completed_stages, "completed_stages")

    def to_dict(self) -> dict[str, Any]:
        return {
            "completed_stages": list(self.completed_stages),
            "failed_stages": [failure.to_dict() for failure in self.failed_stages],
        }


@dataclasses.dataclass(frozen=True)
class ScienceFictionSidecarEnvelope:
    """Append-oriented science-fiction sidecar contract envelope."""

    lcats_id: str
    story_path: str
    story_hash: str
    evidence_sets: tuple[evidence.EvidenceSet, ...] = ()
    knight_analyses: tuple[KnightAnalysis, ...] = ()
    suvin_novum_analyses: tuple[SuvinNovumAnalysis, ...] = ()
    current: CurrentPointers = dataclasses.field(default_factory=CurrentPointers)
    validation: ValidationResult = dataclasses.field(
        default_factory=lambda: ValidationResult(valid=True)
    )
    partial_success: PartialSuccessRecord | None = None
    schema_version: str = SCIENCE_FICTION_SIDECAR_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCIENCE_FICTION_SIDECAR_VERSION:
            raise ValueError("unsupported science-fiction sidecar schema version")
        _require_non_empty_string(self.lcats_id, "lcats_id")
        _require_non_empty_string(self.story_path, "story_path")
        _require_non_empty_string(self.story_hash, "story_hash")
        _require_unique_strings(self.evidence_set_ids, "evidence_set_ids")

    @property
    def evidence_set_ids(self) -> tuple[str, ...]:
        return tuple(
            evidence_set.evidence_set_id for evidence_set in self.evidence_sets
        )

    def validate(self) -> ValidationResult:
        findings = list(self.validation.findings)
        findings.extend(self._validate_evidence_sets().findings)
        findings.extend(self._validate_analyses().findings)
        findings.extend(self._validate_evidence_references().findings)
        findings.extend(self.validate_current_pointers().findings)
        return ValidationResult.from_findings(tuple(findings))

    def _validate_evidence_sets(self) -> ValidationResult:
        findings: list[ValidationFinding] = []
        for index, evidence_set in enumerate(self.evidence_sets):
            if evidence_set.story_hash != self.story_hash:
                findings.append(
                    ValidationFinding(
                        f"$.evidence_sets[{index}].story_hash",
                        "error",
                        "story_hash_mismatch",
                        "evidence set story hash does not match sidecar",
                    )
                )
        return ValidationResult.from_findings(tuple(findings))

    def _validate_analyses(self) -> ValidationResult:
        findings: list[ValidationFinding] = []
        evidence_set_ids = set(self.evidence_set_ids)
        for path, label, analysis in _iter_analyses(
            self.knight_analyses, self.suvin_novum_analyses
        ):
            if analysis.story_hash != self.story_hash:
                findings.append(
                    ValidationFinding(
                        f"{path}.story_hash",
                        "error",
                        "story_hash_mismatch",
                        f"{label} analysis story hash does not match sidecar",
                    )
                )
            if analysis.evidence_set_id not in evidence_set_ids:
                findings.append(
                    ValidationFinding(
                        f"{path}.evidence_set_id",
                        "error",
                        "missing_reference",
                        f"{label} analysis evidence set does not exist",
                    )
                )
        return ValidationResult.from_findings(tuple(findings))

    def _validate_evidence_references(self) -> ValidationResult:
        findings: list[ValidationFinding] = []
        evidence_ids_by_set = {
            evidence_set.evidence_set_id: {
                record.evidence_id for record in evidence_set.records
            }
            for evidence_set in self.evidence_sets
        }
        for path, analysis_evidence_set_id, reference in _iter_evidence_references(
            self.knight_analyses, self.suvin_novum_analyses
        ):
            if reference.evidence_set_id != analysis_evidence_set_id:
                findings.append(
                    ValidationFinding(
                        path,
                        "error",
                        "evidence_set_mismatch",
                        "evidence reference must use the analysis evidence set",
                    )
                )
            evidence_ids = evidence_ids_by_set.get(reference.evidence_set_id)
            if evidence_ids is None:
                findings.append(
                    ValidationFinding(
                        path,
                        "error",
                        "missing_reference",
                        "evidence reference set does not exist",
                    )
                )
            elif reference.evidence_id not in evidence_ids:
                findings.append(
                    ValidationFinding(
                        path,
                        "error",
                        "missing_reference",
                        "evidence reference record does not exist",
                    )
                )
        return ValidationResult.from_findings(tuple(findings))

    def validate_current_pointers(self) -> ValidationResult:
        findings: list[ValidationFinding] = []
        evidence_set_ids = set(self.evidence_set_ids)
        if (
            self.current.evidence_set_id is not None
            and self.current.evidence_set_id not in evidence_set_ids
        ):
            findings.append(
                ValidationFinding(
                    "$.current.evidence_set_id",
                    "error",
                    "missing_reference",
                    "current evidence set does not exist",
                )
            )
        _validate_current_analysis(
            self.current.knight_analysis_id,
            analyses=self.knight_analyses,
            path="$.current.knight_analysis_id",
            label="Knight",
            story_hash=self.story_hash,
            evidence_set_ids=evidence_set_ids,
            current_evidence_set_id=self.current.evidence_set_id,
            findings=findings,
        )
        _validate_current_analysis(
            self.current.suvin_novum_analysis_id,
            analyses=self.suvin_novum_analyses,
            path="$.current.suvin_novum_analysis_id",
            label="Suvin novum",
            story_hash=self.story_hash,
            evidence_set_ids=evidence_set_ids,
            current_evidence_set_id=self.current.evidence_set_id,
            findings=findings,
        )
        return ValidationResult.from_findings(tuple(findings))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "lcats_id": self.lcats_id,
            "story_path": self.story_path,
            "story_hash": self.story_hash,
            "evidence_sets": [
                evidence_set.to_dict() for evidence_set in self.evidence_sets
            ],
            "analyses": {
                "knight": [analysis.to_dict() for analysis in self.knight_analyses],
                "suvin_novum": [
                    analysis.to_dict() for analysis in self.suvin_novum_analyses
                ],
            },
            "current": self.current.to_dict(),
            "validation": self.validate().to_dict(),
            "partial_success": (
                None if self.partial_success is None else self.partial_success.to_dict()
            ),
        }


def _validate_current_analysis(
    analysis_id: str | None,
    *,
    analyses: tuple[Any, ...],
    path: str,
    label: str,
    story_hash: str,
    evidence_set_ids: set[str],
    current_evidence_set_id: str | None,
    findings: list[ValidationFinding],
) -> None:
    if analysis_id is None:
        return
    matching = [
        analysis for analysis in analyses if analysis.analysis_id == analysis_id
    ]
    if not matching:
        findings.append(
            ValidationFinding(
                path,
                "error",
                "missing_reference",
                f"current {label} analysis does not exist",
            )
        )
        return
    if len(matching) > 1:
        findings.append(
            ValidationFinding(
                path,
                "error",
                "duplicate_reference",
                f"current {label} analysis id is not unique",
            )
        )
        return
    analysis = matching[0]
    if analysis.status != "complete":
        findings.append(
            ValidationFinding(
                path,
                "error",
                "incomplete_current_record",
                f"current {label} analysis must be complete",
            )
        )
    if analysis.failures:
        findings.append(
            ValidationFinding(
                path,
                "error",
                "failed_current_record",
                f"current {label} analysis must not contain failures",
            )
        )
    if analysis.story_hash != story_hash:
        findings.append(
            ValidationFinding(
                path,
                "error",
                "story_hash_mismatch",
                f"current {label} analysis story hash does not match sidecar",
            )
        )
    if analysis.evidence_set_id not in evidence_set_ids:
        findings.append(
            ValidationFinding(
                path,
                "error",
                "missing_reference",
                f"current {label} analysis evidence set does not exist",
            )
        )
    if (
        current_evidence_set_id is not None
        and analysis.evidence_set_id != current_evidence_set_id
    ):
        findings.append(
            ValidationFinding(
                path,
                "error",
                "evidence_set_mismatch",
                f"current {label} analysis must use the current evidence set",
            )
        )


def _iter_analyses(
    knight_analyses: tuple[KnightAnalysis, ...],
    suvin_novum_analyses: tuple[SuvinNovumAnalysis, ...],
) -> tuple[tuple[str, str, KnightAnalysis | SuvinNovumAnalysis], ...]:
    analyses: list[tuple[str, str, KnightAnalysis | SuvinNovumAnalysis]] = []
    analyses.extend(
        (f"$.analyses.knight[{index}]", "Knight", analysis)
        for index, analysis in enumerate(knight_analyses)
    )
    analyses.extend(
        (f"$.analyses.suvin_novum[{index}]", "Suvin novum", analysis)
        for index, analysis in enumerate(suvin_novum_analyses)
    )
    return tuple(analyses)


def _iter_evidence_references(
    knight_analyses: tuple[KnightAnalysis, ...],
    suvin_novum_analyses: tuple[SuvinNovumAnalysis, ...],
) -> tuple[tuple[str, str, EvidenceReference], ...]:
    references: list[tuple[str, str, EvidenceReference]] = []
    for analysis_index, analysis in enumerate(knight_analyses):
        for criterion_index, criterion in enumerate(analysis.criteria):
            base = f"$.analyses.knight[{analysis_index}].criteria[{criterion_index}]"
            references.extend(
                (
                    f"{base}.supporting_evidence[{index}]",
                    analysis.evidence_set_id,
                    reference,
                )
                for index, reference in enumerate(criterion.supporting_evidence)
            )
            references.extend(
                (
                    f"{base}.counterevidence[{index}]",
                    analysis.evidence_set_id,
                    reference,
                )
                for index, reference in enumerate(criterion.counterevidence)
            )
    for analysis_index, analysis in enumerate(suvin_novum_analyses):
        for candidate_index, candidate in enumerate(analysis.candidates):
            base = (
                f"$.analyses.suvin_novum[{analysis_index}]"
                f".candidates[{candidate_index}]"
            )
            references.extend(
                (f"{base}.evidence[{index}]", analysis.evidence_set_id, reference)
                for index, reference in enumerate(candidate.evidence)
            )
            for dimension_name in (
                "novelty",
                "cognitive_validation",
                "narrative_hegemony",
            ):
                dimension = getattr(candidate, dimension_name)
                dimension_base = f"{base}.{dimension_name}"
                references.extend(
                    (
                        f"{dimension_base}.supporting_evidence[{index}]",
                        analysis.evidence_set_id,
                        reference,
                    )
                    for index, reference in enumerate(dimension.supporting_evidence)
                )
                references.extend(
                    (
                        f"{dimension_base}.counterevidence[{index}]",
                        analysis.evidence_set_id,
                        reference,
                    )
                    for index, reference in enumerate(dimension.counterevidence)
                )
            estrangement = candidate.estrangement
            for field_name in (
                "reader_facing_evidence",
                "storyworld_consequence_evidence",
                "character_reaction_evidence",
            ):
                references.extend(
                    (
                        f"{base}.estrangement.{field_name}[{index}]",
                        analysis.evidence_set_id,
                        reference,
                    )
                    for index, reference in enumerate(getattr(estrangement, field_name))
                )
    return tuple(references)


def _freeze_mapping(value: Mapping[str, Any]) -> MappingProxyType[str, Any]:
    return MappingProxyType({key: _freeze_value(item) for key, item in value.items()})


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _freeze_mapping(value)
    if isinstance(value, str | bytes):
        return value
    if isinstance(value, Sequence):
        return tuple(_freeze_value(item) for item in value)
    return value


def _thaw_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_value(item) for item in value]
    return value


def _require_non_empty_string(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string")


def _require_choice(value: str, choices: frozenset[str], field_name: str) -> None:
    if value not in choices:
        raise ValueError(f"{field_name} must be one of {sorted(choices)!r}")


def _require_unique_strings(values: tuple[str, ...], field_name: str) -> None:
    for value in values:
        _require_non_empty_string(value, field_name)
    if len(set(values)) != len(values):
        raise ValueError(f"{field_name} must be unique")
