"""Validation and publication helpers for science-fiction sidecars."""

from __future__ import annotations

import json
import os
import pathlib
import tempfile
from typing import Any

from lcats.analysis.science_fiction import evidence
from lcats.analysis.science_fiction import models

SCHEMA_VERSION = models.SCIENCE_FICTION_SIDECAR_VERSION
SIDECAR_FILENAME = "science-fiction.json"
PARTIAL_SUCCESS_STAGE_NAMES = frozenset(
    {
        "preparation",
        "evidence",
        "knight",
        "suvin_novum",
        "sidecar",
        "publication",
    }
)


def validate_envelope(
    envelope: models.ScienceFictionSidecarEnvelope,
) -> models.ValidationResult:
    """Validate an in-memory sidecar envelope."""

    return envelope.validate()


def validate_sidecar(data: Any) -> models.ValidationResult:
    """Validate one loaded ``science-fiction-sidecar-v1`` object.

    This is intentionally pure Python and operates on already-loaded JSON-like
    values, so experiment runners and later promotion gates can validate
    sidecars without importing a JSON Schema dependency.
    """

    findings: list[models.ValidationFinding] = []
    if not isinstance(data, dict):
        findings.append(
            _finding(
                "$",
                "wrong_type",
                f"expected a JSON object, got {type(data).__name__}",
            )
        )
        return _result(findings)

    schema_version = data.get("schema_version")
    _require_string(data, "schema_version", "$.schema_version", findings)
    if _is_non_empty_string(schema_version) and schema_version != SCHEMA_VERSION:
        findings.append(
            _finding(
                "$.schema_version",
                "invalid_schema_version",
                f"expected {SCHEMA_VERSION!r}",
            )
        )

    for key in ("lcats_id", "story_path", "story_hash"):
        _require_string(data, key, f"$.{key}", findings)

    story_hash = data.get("story_hash")
    evidence_sets = _require_list(data, "evidence_sets", "$.evidence_sets", findings)
    analyses = _require_mapping(data, "analyses", "$.analyses", findings)
    current = _require_mapping(data, "current", "$.current", findings)
    _require_mapping(data, "validation", "$.validation", findings)

    evidence_ids_by_set = _validate_evidence_sets(
        evidence_sets, story_hash=story_hash, findings=findings
    )
    current_evidence_set_id: str | None = None
    current_knight_analysis_id: str | None = None
    current_suvin_analysis_id: str | None = None
    if isinstance(current, dict):
        current_evidence_set_id = _optional_string_or_none(
            current,
            "evidence_set_id",
            "$.current.evidence_set_id",
            findings,
        )
        current_knight_analysis_id = _optional_string_or_none(
            current,
            "knight_analysis_id",
            "$.current.knight_analysis_id",
            findings,
        )
        current_suvin_analysis_id = _optional_string_or_none(
            current,
            "suvin_novum_analysis_id",
            "$.current.suvin_novum_analysis_id",
            findings,
        )
        if (
            current_evidence_set_id is not None
            and current_evidence_set_id not in evidence_ids_by_set
        ):
            findings.append(
                _finding(
                    "$.current.evidence_set_id",
                    "missing_reference",
                    "current evidence set does not exist",
                )
            )

    knight_index: dict[str, dict[str, Any]] = {}
    suvin_index: dict[str, dict[str, Any]] = {}
    if isinstance(analyses, dict):
        knight_items = _require_list(analyses, "knight", "$.analyses.knight", findings)
        suvin_items = _require_list(
            analyses, "suvin_novum", "$.analyses.suvin_novum", findings
        )
        knight_index = _validate_analyses(
            knight_items,
            path="$.analyses.knight",
            label="Knight",
            story_hash=story_hash,
            evidence_ids_by_set=evidence_ids_by_set,
            findings=findings,
        )
        suvin_index = _validate_analyses(
            suvin_items,
            path="$.analyses.suvin_novum",
            label="Suvin novum",
            story_hash=story_hash,
            evidence_ids_by_set=evidence_ids_by_set,
            findings=findings,
        )

    _validate_current_analysis(
        current_knight_analysis_id,
        index=knight_index,
        path="$.current.knight_analysis_id",
        label="Knight",
        current_evidence_set_id=current_evidence_set_id,
        findings=findings,
    )
    _validate_current_analysis(
        current_suvin_analysis_id,
        index=suvin_index,
        path="$.current.suvin_novum_analysis_id",
        label="Suvin novum",
        current_evidence_set_id=current_evidence_set_id,
        findings=findings,
    )

    if data.get("partial_success") is not None:
        _validate_partial_success(data.get("partial_success"), findings)
    _validate_stored_validation(data.get("validation"), findings)
    return _result(findings)


def dumps_json(data: Any) -> str:
    """Serialize sidecar JSON deterministically."""

    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def envelope_to_data(
    envelope: models.ScienceFictionSidecarEnvelope,
) -> dict[str, Any]:
    """Convert an envelope to a validated JSON-like mapping."""

    data = envelope.to_dict()
    validation = validate_sidecar(data)
    if not validation.valid:
        raise ValueError("science-fiction sidecar envelope is invalid")
    return data


def render_sidecar_json(
    data: dict[str, Any] | models.ScienceFictionSidecarEnvelope,
) -> str:
    """Return deterministic JSON text for a valid sidecar."""

    payload = (
        envelope_to_data(data)
        if isinstance(data, models.ScienceFictionSidecarEnvelope)
        else data
    )
    validation = validate_sidecar(payload)
    if not validation.valid:
        raise ValueError("science-fiction sidecar data is invalid")
    return dumps_json(payload)


def write_json_atomic(path: pathlib.Path, data: dict[str, Any]) -> None:
    """Atomically publish deterministic sidecar JSON at ``path``."""

    _atomic_write_text(path, render_sidecar_json(data))


def load_json(path: pathlib.Path) -> Any:
    """Load JSON from ``path`` using UTF-8."""

    return json.loads(path.read_text(encoding="utf-8"))


def _validate_evidence_sets(
    evidence_sets: Any,
    *,
    story_hash: Any,
    findings: list[models.ValidationFinding],
) -> dict[str, set[str]]:
    evidence_ids_by_set: dict[str, set[str]] = {}
    if not isinstance(evidence_sets, list):
        return evidence_ids_by_set
    for index, item in enumerate(evidence_sets):
        base = f"$.evidence_sets[{index}]"
        if not isinstance(item, dict):
            findings.append(
                _finding(
                    base,
                    "wrong_type",
                    f"expected object, got {type(item).__name__}",
                )
            )
            continue
        evidence_set_id = item.get("evidence_set_id")
        _require_string(item, "version", f"{base}.version", findings)
        if (
            _is_non_empty_string(item.get("version"))
            and item.get("version") != evidence.EVIDENCE_SET_VERSION
        ):
            findings.append(
                _finding(
                    f"{base}.version",
                    "invalid_evidence_set_version",
                    "evidence set version does not match science-fiction-evidence-set-v1",
                )
            )
        _require_string(item, "evidence_set_id", f"{base}.evidence_set_id", findings)
        _require_string(item, "story_hash", f"{base}.story_hash", findings)
        if (
            _is_non_empty_string(item.get("story_hash"))
            and item.get("story_hash") != story_hash
        ):
            findings.append(
                _finding(
                    f"{base}.story_hash",
                    "story_hash_mismatch",
                    "evidence set story hash does not match sidecar",
                )
            )
        if _is_non_empty_string(evidence_set_id):
            if evidence_set_id in evidence_ids_by_set:
                findings.append(
                    _finding(
                        f"{base}.evidence_set_id",
                        "duplicate_reference",
                        "evidence set id is not unique",
                    )
                )
            evidence_ids_by_set.setdefault(evidence_set_id, set())
        records = _require_list(item, "records", f"{base}.records", findings)
        quarantined = _require_list(
            item, "quarantined", f"{base}.quarantined", findings
        )
        conflicts = _require_list(item, "conflicts", f"{base}.conflicts", findings)
        if isinstance(records, list) and _is_non_empty_string(evidence_set_id):
            _validate_evidence_records(
                records, base, evidence_ids_by_set[evidence_set_id], findings
            )
        if isinstance(quarantined, list):
            _validate_quarantined_evidence(quarantined, f"{base}.quarantined", findings)
        if isinstance(conflicts, list) and _is_non_empty_string(evidence_set_id):
            _validate_evidence_conflicts(
                conflicts,
                base,
                evidence_ids_by_set[evidence_set_id],
                findings,
            )
    return evidence_ids_by_set


def _validate_evidence_records(
    records: list[Any],
    evidence_set_path: str,
    evidence_ids: set[str],
    findings: list[models.ValidationFinding],
) -> None:
    for index, record in enumerate(records):
        base = f"{evidence_set_path}.records[{index}]"
        if not isinstance(record, dict):
            findings.append(
                _finding(
                    base,
                    "wrong_type",
                    f"expected object, got {type(record).__name__}",
                )
            )
            continue
        evidence_id = record.get("evidence_id")
        _require_string(record, "evidence_id", f"{base}.evidence_id", findings)
        _require_string(record, "evidence_type", f"{base}.evidence_type", findings)
        if (
            _is_non_empty_string(record.get("evidence_type"))
            and record.get("evidence_type") not in evidence.EVIDENCE_TYPES
        ):
            findings.append(
                _finding(
                    f"{base}.evidence_type",
                    "invalid_evidence_type",
                    "evidence_type is not a science-fiction neutral evidence type",
                )
            )
        _require_string(record, "quote", f"{base}.quote", findings)
        anchor = _require_mapping(record, "anchor", f"{base}.anchor", findings)
        if isinstance(anchor, dict):
            _validate_evidence_anchor(anchor, f"{base}.anchor", findings)
        _require_string(record, "paraphrase", f"{base}.paraphrase", findings)
        _require_number(record, "confidence", f"{base}.confidence", findings)
        if (
            isinstance(record.get("confidence"), (int, float))
            and not isinstance(record.get("confidence"), bool)
            and not 0.0 <= record["confidence"] <= 1.0
        ):
            findings.append(
                _finding(
                    f"{base}.confidence",
                    "invalid_confidence",
                    "confidence must be between 0 and 1",
                )
            )
        _validate_string_items(record, "entity_ids", f"{base}.entity_ids", findings)
        _validate_string_items(record, "event_ids", f"{base}.event_ids", findings)
        provenance = _require_list(record, "provenance", f"{base}.provenance", findings)
        if isinstance(provenance, list):
            _validate_evidence_provenance_items(
                provenance, f"{base}.provenance", findings
            )
        if _is_non_empty_string(evidence_id):
            if evidence_id in evidence_ids:
                findings.append(
                    _finding(
                        f"{base}.evidence_id",
                        "duplicate_reference",
                        "evidence id is not unique within evidence set",
                    )
                )
            evidence_ids.add(evidence_id)


def _validate_quarantined_evidence(
    quarantined: list[Any],
    path: str,
    findings: list[models.ValidationFinding],
) -> None:
    for index, item in enumerate(quarantined):
        item_path = f"{path}[{index}]"
        if not isinstance(item, dict):
            findings.append(
                _finding(
                    item_path,
                    "wrong_type",
                    f"expected object, got {type(item).__name__}",
                )
            )
            continue
        _require_string(item, "reason", f"{item_path}.reason", findings)
        candidate = _require_mapping(
            item, "candidate", f"{item_path}.candidate", findings
        )
        if isinstance(candidate, dict):
            _validate_evidence_candidate(candidate, f"{item_path}.candidate", findings)


def _validate_evidence_candidate(
    candidate: dict[str, Any],
    path: str,
    findings: list[models.ValidationFinding],
) -> None:
    _optional_string_or_none(candidate, "raw_id", f"{path}.raw_id", findings)
    _require_string_value(candidate, "evidence_type", f"{path}.evidence_type", findings)
    _require_string_value(candidate, "quote", f"{path}.quote", findings)
    _validate_string_items(
        candidate, "paragraph_ids", f"{path}.paragraph_ids", findings
    )
    _require_optional_int(candidate, "start_char", f"{path}.start_char", findings)
    _require_optional_int(candidate, "end_char", f"{path}.end_char", findings)
    _require_string_value(candidate, "paraphrase", f"{path}.paraphrase", findings)
    _validate_string_items(candidate, "entity_ids", f"{path}.entity_ids", findings)
    _validate_string_items(candidate, "event_ids", f"{path}.event_ids", findings)
    _require_number(candidate, "confidence", f"{path}.confidence", findings)
    if (
        isinstance(candidate.get("confidence"), (int, float))
        and not isinstance(candidate.get("confidence"), bool)
        and not 0.0 <= candidate["confidence"] <= 1.0
    ):
        findings.append(
            _finding(
                f"{path}.confidence",
                "invalid_confidence",
                "confidence must be between 0 and 1",
            )
        )
    _optional_string_or_none(
        candidate, "source_chunk_id", f"{path}.source_chunk_id", findings
    )
    _require_string_value(candidate, "source", f"{path}.source", findings)
    _validate_string_items(
        candidate, "schema_errors", f"{path}.schema_errors", findings
    )


def _validate_evidence_conflicts(
    conflicts: list[Any],
    evidence_set_path: str,
    evidence_ids: set[str],
    findings: list[models.ValidationFinding],
) -> None:
    conflict_ids: set[str] = set()
    for index, conflict in enumerate(conflicts):
        base = f"{evidence_set_path}.conflicts[{index}]"
        if not isinstance(conflict, dict):
            findings.append(
                _finding(
                    base,
                    "wrong_type",
                    f"expected object, got {type(conflict).__name__}",
                )
            )
            continue
        conflict_id = conflict.get("conflict_id")
        _require_string(conflict, "conflict_id", f"{base}.conflict_id", findings)
        if _is_non_empty_string(conflict_id):
            if conflict_id in conflict_ids:
                findings.append(
                    _finding(
                        f"{base}.conflict_id",
                        "duplicate_reference",
                        "conflict id is not unique within evidence set",
                    )
                )
            conflict_ids.add(conflict_id)
        conflict_evidence_ids = _require_list(
            conflict, "evidence_ids", f"{base}.evidence_ids", findings
        )
        if not isinstance(conflict_evidence_ids, list):
            continue
        if len(conflict_evidence_ids) < 2:
            findings.append(
                _finding(
                    f"{base}.evidence_ids",
                    "missing_required_field",
                    "evidence conflicts require at least two evidence ids",
                )
            )
        seen_conflict_evidence_ids: set[str] = set()
        for evidence_index, evidence_id in enumerate(conflict_evidence_ids):
            evidence_path = f"{base}.evidence_ids[{evidence_index}]"
            if not _is_non_empty_string(evidence_id):
                findings.append(
                    _finding(
                        evidence_path,
                        "wrong_type",
                        f"expected non-empty string, got {type(evidence_id).__name__}",
                    )
                )
            elif evidence_id in seen_conflict_evidence_ids:
                findings.append(
                    _finding(
                        evidence_path,
                        "duplicate_reference",
                        "evidence conflicts may not repeat evidence ids",
                    )
                )
            elif evidence_id not in evidence_ids:
                findings.append(
                    _finding(
                        evidence_path,
                        "missing_reference",
                        "evidence conflicts must reference records in the same evidence set",
                    )
                )
            if _is_non_empty_string(evidence_id):
                seen_conflict_evidence_ids.add(evidence_id)


def _validate_analyses(
    analyses: Any,
    *,
    path: str,
    label: str,
    story_hash: Any,
    evidence_ids_by_set: dict[str, set[str]],
    findings: list[models.ValidationFinding],
) -> dict[str, dict[str, Any]]:
    index_by_id: dict[str, dict[str, Any]] = {}
    if not isinstance(analyses, list):
        return index_by_id
    for index, analysis in enumerate(analyses):
        base = f"{path}[{index}]"
        if not isinstance(analysis, dict):
            findings.append(
                _finding(
                    base,
                    "wrong_type",
                    f"expected object, got {type(analysis).__name__}",
                )
            )
            continue
        analysis_id = analysis.get("analysis_id")
        evidence_set_id = analysis.get("evidence_set_id")
        _require_string(analysis, "analysis_id", f"{base}.analysis_id", findings)
        _require_string(analysis, "story_hash", f"{base}.story_hash", findings)
        _require_string(
            analysis, "evidence_set_id", f"{base}.evidence_set_id", findings
        )
        _require_string(analysis, "status", f"{base}.status", findings)
        failures = _require_list(analysis, "failures", f"{base}.failures", findings)
        if isinstance(failures, list):
            _validate_failure_records(failures, f"{base}.failures", findings)
        status = analysis.get("status")
        if (
            status in {"failed", "partial"}
            and isinstance(failures, list)
            and not failures
        ):
            findings.append(
                _finding(
                    f"{base}.failures",
                    "missing_required_field",
                    "failed or partial analyses require at least one failure record",
                )
            )
        if _is_non_empty_string(status) and status not in models.ANALYSIS_STATES:
            findings.append(
                _finding(
                    f"{base}.status",
                    "invalid_status",
                    f"expected one of {sorted(models.ANALYSIS_STATES)!r}",
                )
            )
        if (
            _is_non_empty_string(analysis.get("story_hash"))
            and analysis.get("story_hash") != story_hash
        ):
            findings.append(
                _finding(
                    f"{base}.story_hash",
                    "story_hash_mismatch",
                    f"{label} analysis story hash does not match sidecar",
                )
            )
        if (
            _is_non_empty_string(evidence_set_id)
            and evidence_set_id not in evidence_ids_by_set
        ):
            findings.append(
                _finding(
                    f"{base}.evidence_set_id",
                    "missing_reference",
                    f"{label} analysis evidence set does not exist",
                )
            )
        if _is_non_empty_string(analysis_id):
            if analysis_id in index_by_id:
                findings.append(
                    _finding(
                        f"{base}.analysis_id",
                        "duplicate_reference",
                        f"{label} analysis id is not unique",
                    )
                )
            index_by_id.setdefault(analysis_id, analysis)
        if label == "Knight":
            _validate_knight_analysis(analysis, base, findings)
        elif label == "Suvin novum":
            _validate_suvin_analysis(analysis, base, findings)
        if _is_non_empty_string(evidence_set_id):
            _validate_analysis_references(
                analysis,
                base,
                analysis_evidence_set_id=evidence_set_id,
                evidence_ids_by_set=evidence_ids_by_set,
                findings=findings,
            )
    return index_by_id


def _validate_knight_analysis(
    analysis: dict[str, Any],
    base: str,
    findings: list[models.ValidationFinding],
) -> None:
    criteria = _require_list(analysis, "criteria", f"{base}.criteria", findings)
    interval = _require_mapping(analysis, "interval", f"{base}.interval", findings)
    _validate_provenance(
        analysis,
        f"{base}.provenance",
        expected_rubric_version=models.KNIGHT_RUBRIC_VERSION,
        findings=findings,
    )
    if isinstance(interval, dict):
        _validate_knight_interval(interval, f"{base}.interval", findings)
    if not isinstance(criteria, list):
        return
    criterion_ids: list[str] = []
    for index, criterion in enumerate(criteria):
        criterion_base = f"{base}.criteria[{index}]"
        if not isinstance(criterion, dict):
            findings.append(
                _finding(
                    criterion_base,
                    "wrong_type",
                    f"expected object, got {type(criterion).__name__}",
                )
            )
            continue
        criterion_id = criterion.get("criterion_id")
        status = criterion.get("status")
        materiality = criterion.get("materiality")
        _require_string(
            criterion, "criterion_id", f"{criterion_base}.criterion_id", findings
        )
        _require_string(criterion, "status", f"{criterion_base}.status", findings)
        supporting = _require_list(
            criterion,
            "supporting_evidence",
            f"{criterion_base}.supporting_evidence",
            findings,
        )
        _require_list(
            criterion, "counterevidence", f"{criterion_base}.counterevidence", findings
        )
        _require_string_value(
            criterion, "rationale", f"{criterion_base}.rationale", findings
        )
        _validate_optional_confidence(
            criterion, f"{criterion_base}.confidence", findings
        )
        if _is_non_empty_string(criterion_id):
            criterion_ids.append(criterion_id)
            if criterion_id not in models.KNIGHT_CRITERION_IDS:
                findings.append(
                    _finding(
                        f"{criterion_base}.criterion_id",
                        "invalid_criterion_id",
                        "criterion_id must identify one Knight criterion",
                    )
                )
        if _is_non_empty_string(status) and status not in models.DECISION_STATES:
            findings.append(
                _finding(
                    f"{criterion_base}.status",
                    "invalid_status",
                    f"expected one of {sorted(models.DECISION_STATES)!r}",
                )
            )
        if materiality is not None:
            if not _is_non_empty_string(materiality):
                findings.append(
                    _finding(
                        f"{criterion_base}.materiality",
                        "wrong_type",
                        f"expected non-empty string or null, got {type(materiality).__name__}",
                    )
                )
            elif materiality not in models.MATERIALITY_STATES:
                findings.append(
                    _finding(
                        f"{criterion_base}.materiality",
                        "invalid_materiality",
                        f"expected one of {sorted(models.MATERIALITY_STATES)!r}",
                    )
                )
        if status == "present" and isinstance(supporting, list) and not supporting:
            findings.append(
                _finding(
                    f"{criterion_base}.supporting_evidence",
                    "missing_required_field",
                    "present Knight criteria require supporting evidence",
                )
            )
        if status in {"absent", "not_assessable"} and materiality is not None:
            findings.append(
                _finding(
                    f"{criterion_base}.materiality",
                    "invalid_materiality",
                    "materiality applies only to present or ambiguous criteria",
                )
            )
    if sorted(criterion_ids) != sorted(models.KNIGHT_CRITERION_IDS):
        findings.append(
            _finding(
                f"{base}.criteria",
                "invalid_criteria",
                "Knight analysis must contain seven unique criteria",
            )
        )
    elif isinstance(interval, dict):
        _validate_knight_interval_matches_criteria(
            interval, criteria, f"{base}.interval", findings
        )


def _validate_knight_interval(
    interval: dict[str, Any],
    base: str,
    findings: list[models.ValidationFinding],
) -> None:
    for key in ("definite_count", "possible_count", "total_count"):
        _require_int(interval, key, f"{base}.{key}", findings)
    definite = interval.get("definite_count")
    possible = interval.get("possible_count")
    total = interval.get("total_count")
    if not all(
        isinstance(value, int) and not isinstance(value, bool)
        for value in (definite, possible, total)
    ):
        return
    if total != len(models.KNIGHT_CRITERION_IDS):
        findings.append(
            _finding(
                f"{base}.total_count",
                "invalid_knight_interval",
                "total_count must equal the number of Knight criteria",
            )
        )
    if definite < 0 or possible < 0 or total < 0:
        findings.append(
            _finding(
                base,
                "invalid_knight_interval",
                "Knight interval counts must be non-negative",
            )
        )
    if definite > possible or possible > total:
        findings.append(
            _finding(
                base,
                "invalid_knight_interval",
                "Knight interval must satisfy definite_count <= possible_count <= total_count",
            )
        )


def _validate_knight_interval_matches_criteria(
    interval: dict[str, Any],
    criteria: list[Any],
    base: str,
    findings: list[models.ValidationFinding],
) -> None:
    definite = interval.get("definite_count")
    possible = interval.get("possible_count")
    total = interval.get("total_count")
    if not all(
        isinstance(value, int) and not isinstance(value, bool)
        for value in (definite, possible, total)
    ):
        return
    computed_definite = sum(
        1
        for criterion in criteria
        if isinstance(criterion, dict) and criterion.get("status") == "present"
    )
    computed_possible = sum(
        1
        for criterion in criteria
        if isinstance(criterion, dict)
        and criterion.get("status") in {"present", "ambiguous"}
    )
    if (
        definite != computed_definite
        or possible != computed_possible
        or total != len(criteria)
    ):
        findings.append(
            _finding(
                base,
                "knight_interval_mismatch",
                "Knight interval counts must match criterion statuses",
            )
        )


def _validate_suvin_analysis(
    analysis: dict[str, Any],
    base: str,
    findings: list[models.ValidationFinding],
) -> None:
    candidates = _require_list(analysis, "candidates", f"{base}.candidates", findings)
    systems = _require_list(
        analysis, "novum_systems", f"{base}.novum_systems", findings
    )
    _validate_provenance(
        analysis,
        f"{base}.provenance",
        expected_rubric_version=models.SUVIN_RUBRIC_VERSION,
        findings=findings,
    )
    dominant_novum_id = _optional_string_or_none(
        analysis, "dominant_novum_id", f"{base}.dominant_novum_id", findings
    )
    candidate_ids: list[str] = []
    qualified_ids: set[str] = set()
    if isinstance(candidates, list):
        for index, candidate in enumerate(candidates):
            candidate_base = f"{base}.candidates[{index}]"
            if not isinstance(candidate, dict):
                findings.append(
                    _finding(
                        candidate_base,
                        "wrong_type",
                        f"expected object, got {type(candidate).__name__}",
                    )
                )
                continue
            candidate_id = candidate.get("candidate_id")
            _require_string(
                candidate, "candidate_id", f"{candidate_base}.candidate_id", findings
            )
            _require_string(
                candidate, "description", f"{candidate_base}.description", findings
            )
            _require_list(candidate, "evidence", f"{candidate_base}.evidence", findings)
            dimension_statuses = {
                name: _validate_novum_dimension(
                    candidate, candidate_base, name, findings
                )
                for name in (
                    "novelty",
                    "cognitive_validation",
                    "narrative_hegemony",
                )
            }
            _validate_estrangement(candidate, candidate_base, findings)
            computed_qualified = all(
                status == "present" for status in dimension_statuses.values()
            )
            if not isinstance(candidate.get("qualified_novum"), bool):
                findings.append(
                    _finding(
                        f"{candidate_base}.qualified_novum",
                        "wrong_type",
                        f"expected bool, got {type(candidate.get('qualified_novum')).__name__}",
                    )
                )
            elif candidate.get("qualified_novum") != computed_qualified:
                findings.append(
                    _finding(
                        f"{candidate_base}.qualified_novum",
                        "invalid_qualified_novum",
                        "qualified_novum must equal the N/C/H conjunction",
                    )
                )
            if _is_non_empty_string(candidate_id):
                if candidate_id in candidate_ids:
                    findings.append(
                        _finding(
                            f"{candidate_base}.candidate_id",
                            "duplicate_reference",
                            "candidate id is not unique",
                        )
                    )
                candidate_ids.append(candidate_id)
                if computed_qualified:
                    qualified_ids.add(candidate_id)
    if dominant_novum_id is not None and dominant_novum_id not in qualified_ids:
        findings.append(
            _finding(
                f"{base}.dominant_novum_id",
                "missing_reference",
                "dominant_novum_id must reference a qualified candidate",
            )
        )
    if isinstance(systems, list):
        for index, system in enumerate(systems):
            system_base = f"{base}.novum_systems[{index}]"
            if not isinstance(system, dict):
                findings.append(
                    _finding(
                        system_base,
                        "wrong_type",
                        f"expected object, got {type(system).__name__}",
                    )
                )
                continue
            _require_string(system, "system_id", f"{system_base}.system_id", findings)
            candidate_items = _require_list(
                system, "candidate_ids", f"{system_base}.candidate_ids", findings
            )
            _require_string_value(
                system, "rationale", f"{system_base}.rationale", findings
            )
            if isinstance(candidate_items, list):
                if len(candidate_items) < 2:
                    findings.append(
                        _finding(
                            f"{system_base}.candidate_ids",
                            "missing_required_field",
                            "novum systems require at least two candidates",
                        )
                    )
                seen_candidate_ids: set[str] = set()
                for candidate_index, candidate_id in enumerate(candidate_items):
                    candidate_path = f"{system_base}.candidate_ids[{candidate_index}]"
                    if not _is_non_empty_string(candidate_id):
                        findings.append(
                            _finding(
                                candidate_path,
                                "wrong_type",
                                f"expected non-empty string, got {type(candidate_id).__name__}",
                            )
                        )
                    elif candidate_id in seen_candidate_ids:
                        findings.append(
                            _finding(
                                candidate_path,
                                "duplicate_reference",
                                "novum systems may not repeat candidate ids",
                            )
                        )
                    elif candidate_id not in qualified_ids:
                        findings.append(
                            _finding(
                                candidate_path,
                                "missing_reference",
                                "novum systems may reference only qualified candidates",
                            )
                        )
                    if _is_non_empty_string(candidate_id):
                        seen_candidate_ids.add(candidate_id)


def _validate_novum_dimension(
    candidate: dict[str, Any],
    candidate_base: str,
    name: str,
    findings: list[models.ValidationFinding],
) -> str | None:
    path = f"{candidate_base}.{name}"
    dimension = _require_mapping(candidate, name, path, findings)
    if not isinstance(dimension, dict):
        return None
    status = dimension.get("status")
    _require_string(dimension, "status", f"{path}.status", findings)
    supporting = _require_list(
        dimension, "supporting_evidence", f"{path}.supporting_evidence", findings
    )
    _require_list(dimension, "counterevidence", f"{path}.counterevidence", findings)
    _require_string_value(dimension, "rationale", f"{path}.rationale", findings)
    _validate_optional_confidence(dimension, f"{path}.confidence", findings)
    if _is_non_empty_string(status) and status not in models.DECISION_STATES:
        findings.append(
            _finding(
                f"{path}.status",
                "invalid_status",
                f"expected one of {sorted(models.DECISION_STATES)!r}",
            )
        )
    if status == "present" and isinstance(supporting, list) and not supporting:
        findings.append(
            _finding(
                f"{path}.supporting_evidence",
                "missing_required_field",
                "present Novum dimensions require supporting evidence",
            )
        )
    return status if _is_non_empty_string(status) else None


def _validate_estrangement(
    candidate: dict[str, Any],
    candidate_base: str,
    findings: list[models.ValidationFinding],
) -> None:
    path = f"{candidate_base}.estrangement"
    estrangement = _require_mapping(candidate, "estrangement", path, findings)
    if not isinstance(estrangement, dict):
        return
    for key in (
        "reader_facing_evidence",
        "storyworld_consequence_evidence",
        "character_reaction_evidence",
    ):
        _require_list(estrangement, key, f"{path}.{key}", findings)
    _require_string_value(estrangement, "rationale", f"{path}.rationale", findings)


def _validate_analysis_references(
    analysis: dict[str, Any],
    base: str,
    *,
    analysis_evidence_set_id: str,
    evidence_ids_by_set: dict[str, set[str]],
    findings: list[models.ValidationFinding],
) -> None:
    for path, reference in _iter_reference_dicts(analysis, base):
        if not isinstance(reference, dict):
            findings.append(
                _finding(
                    path,
                    "wrong_type",
                    f"expected object, got {type(reference).__name__}",
                )
            )
            continue
        reference_set_id = reference.get("evidence_set_id")
        reference_id = reference.get("evidence_id")
        _require_string(
            reference, "evidence_set_id", f"{path}.evidence_set_id", findings
        )
        _require_string(reference, "evidence_id", f"{path}.evidence_id", findings)
        if (
            _is_non_empty_string(reference_set_id)
            and reference_set_id != analysis_evidence_set_id
        ):
            findings.append(
                _finding(
                    path,
                    "evidence_set_mismatch",
                    "evidence reference must use the analysis evidence set",
                )
            )
        evidence_ids = evidence_ids_by_set.get(reference_set_id)
        if _is_non_empty_string(reference_set_id) and evidence_ids is None:
            findings.append(
                _finding(
                    path, "missing_reference", "evidence reference set does not exist"
                )
            )
        elif (
            evidence_ids is not None
            and _is_non_empty_string(reference_id)
            and reference_id not in evidence_ids
        ):
            findings.append(
                _finding(
                    path,
                    "missing_reference",
                    "evidence reference record does not exist",
                )
            )


def _iter_reference_dicts(
    analysis: dict[str, Any], base: str
) -> tuple[tuple[str, Any], ...]:
    references: list[tuple[str, Any]] = []
    criteria = analysis.get("criteria", ())
    if not isinstance(criteria, list):
        criteria = ()
    for criteria_index, criterion in enumerate(criteria):
        if not isinstance(criterion, dict):
            continue
        criterion_base = f"{base}.criteria[{criteria_index}]"
        for field in ("supporting_evidence", "counterevidence"):
            items = criterion.get(field, ())
            if not isinstance(items, list):
                continue
            references.extend(
                (f"{criterion_base}.{field}[{index}]", item)
                for index, item in enumerate(items)
            )
    candidates = analysis.get("candidates", ())
    if not isinstance(candidates, list):
        candidates = ()
    for candidate_index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            continue
        candidate_base = f"{base}.candidates[{candidate_index}]"
        evidence_items = candidate.get("evidence", ())
        if not isinstance(evidence_items, list):
            evidence_items = ()
        references.extend(
            (f"{candidate_base}.evidence[{index}]", item)
            for index, item in enumerate(evidence_items)
        )
        for dimension_name in ("novelty", "cognitive_validation", "narrative_hegemony"):
            dimension = candidate.get(dimension_name)
            if not isinstance(dimension, dict):
                continue
            dimension_base = f"{candidate_base}.{dimension_name}"
            for field in ("supporting_evidence", "counterevidence"):
                items = dimension.get(field, ())
                if not isinstance(items, list):
                    continue
                references.extend(
                    (f"{dimension_base}.{field}[{index}]", item)
                    for index, item in enumerate(items)
                )
        estrangement = candidate.get("estrangement")
        if isinstance(estrangement, dict):
            for field in (
                "reader_facing_evidence",
                "storyworld_consequence_evidence",
                "character_reaction_evidence",
            ):
                items = estrangement.get(field, ())
                if not isinstance(items, list):
                    continue
                references.extend(
                    (f"{candidate_base}.estrangement.{field}[{index}]", item)
                    for index, item in enumerate(items)
                )
    return tuple(references)


def _validate_current_analysis(
    analysis_id: str | None,
    *,
    index: dict[str, dict[str, Any]],
    path: str,
    label: str,
    current_evidence_set_id: str | None,
    findings: list[models.ValidationFinding],
) -> None:
    if analysis_id is None:
        return
    analysis = index.get(analysis_id)
    if analysis is None:
        findings.append(
            _finding(
                path, "missing_reference", f"current {label} analysis does not exist"
            )
        )
        return
    if analysis.get("status") != "complete":
        findings.append(
            _finding(
                path,
                "incomplete_current_record",
                f"current {label} analysis must be complete",
            )
        )
    if analysis.get("failures"):
        findings.append(
            _finding(
                path,
                "failed_current_record",
                f"current {label} analysis must not contain failures",
            )
        )
    if (
        current_evidence_set_id is not None
        and analysis.get("evidence_set_id") != current_evidence_set_id
    ):
        findings.append(
            _finding(
                path,
                "evidence_set_mismatch",
                f"current {label} analysis must use the current evidence set",
            )
        )


def _validate_partial_success(
    data: Any, findings: list[models.ValidationFinding]
) -> None:
    if not isinstance(data, dict):
        findings.append(
            _finding(
                "$.partial_success",
                "wrong_type",
                f"expected object, got {type(data).__name__}",
            )
        )
        return
    completed = _require_list(
        data, "completed_stages", "$.partial_success.completed_stages", findings
    )
    failed = _require_list(
        data, "failed_stages", "$.partial_success.failed_stages", findings
    )
    if isinstance(completed, list):
        seen: set[str] = set()
        for index, stage in enumerate(completed):
            if not _is_non_empty_string(stage):
                findings.append(
                    _finding(
                        f"$.partial_success.completed_stages[{index}]",
                        "wrong_type",
                        f"expected non-empty string, got {type(stage).__name__}",
                    )
                )
            elif stage in seen:
                findings.append(
                    _finding(
                        f"$.partial_success.completed_stages[{index}]",
                        "duplicate_reference",
                        "completed stage is not unique",
                    )
                )
            else:
                _validate_stage_name(
                    stage, f"$.partial_success.completed_stages[{index}]", findings
                )
                seen.add(stage)
    if isinstance(failed, list):
        for index, failure in enumerate(failed):
            _validate_failure_record(
                failure, f"$.partial_success.failed_stages[{index}]", findings
            )
            if (
                isinstance(failure, dict)
                and _is_non_empty_string(failure.get("stage"))
                and isinstance(completed, list)
                and failure["stage"] in completed
            ):
                findings.append(
                    _finding(
                        f"$.partial_success.failed_stages[{index}].stage",
                        "conflicting_stage_outcome",
                        "failed stage must not also be listed as completed",
                    )
                )
    if (
        isinstance(completed, list)
        and isinstance(failed, list)
        and not completed
        and not failed
    ):
        findings.append(
            _finding(
                "$.partial_success",
                "missing_required_field",
                "partial_success must record at least one completed or failed stage",
            )
        )


def _validate_failure_record(
    failure: Any,
    path: str,
    findings: list[models.ValidationFinding],
) -> None:
    if not isinstance(failure, dict):
        findings.append(
            _finding(
                path, "wrong_type", f"expected object, got {type(failure).__name__}"
            )
        )
        return
    for key in ("stage", "kind", "message"):
        _require_string(failure, key, f"{path}.{key}", findings)
    if "recoverable" not in failure:
        findings.append(_missing(f"{path}.recoverable"))
    elif not isinstance(failure["recoverable"], bool):
        findings.append(
            _finding(
                f"{path}.recoverable",
                "wrong_type",
                f"expected bool, got {type(failure['recoverable']).__name__}",
            )
        )
    stage = failure.get("stage")
    if _is_non_empty_string(stage):
        _validate_stage_name(stage, f"{path}.stage", findings)


def _validate_failure_records(
    failures: list[Any],
    path: str,
    findings: list[models.ValidationFinding],
) -> None:
    for index, failure in enumerate(failures):
        _validate_failure_record(failure, f"{path}[{index}]", findings)


def _validate_stored_validation(
    data: Any,
    findings: list[models.ValidationFinding],
) -> None:
    if not isinstance(data, dict):
        return
    if "valid" not in data or not isinstance(data.get("valid"), bool):
        findings.append(
            _finding(
                "$.validation.valid",
                "wrong_type",
                f"expected bool, got {type(data.get('valid')).__name__}",
            )
        )
    elif data.get("valid") is False:
        findings.append(
            _finding(
                "$.validation.valid",
                "stored_validation_failed",
                "stored validation outcome must be true for publication",
            )
        )
    stored_findings = _require_list(data, "findings", "$.validation.findings", findings)
    if isinstance(stored_findings, list):
        for index, stored in enumerate(stored_findings):
            finding_base = f"$.validation.findings[{index}]"
            if not isinstance(stored, dict):
                findings.append(
                    _finding(
                        finding_base,
                        "wrong_type",
                        f"expected object, got {type(stored).__name__}",
                    )
                )
                continue
            for key in ("path", "severity", "kind", "message"):
                _require_string(stored, key, f"{finding_base}.{key}", findings)
            severity = stored.get("severity")
            if _is_non_empty_string(severity):
                if severity not in models.VALIDATION_SEVERITIES:
                    findings.append(
                        _finding(
                            f"{finding_base}.severity",
                            "invalid_severity",
                            f"expected one of {sorted(models.VALIDATION_SEVERITIES)!r}",
                        )
                    )
                elif severity == "error":
                    findings.append(
                        _finding(
                            finding_base,
                            "stored_validation_error_finding",
                            "stored validation findings must not contain errors when valid is true",
                        )
                    )


def _validate_provenance(
    data: dict[str, Any],
    path: str,
    *,
    expected_rubric_version: str,
    findings: list[models.ValidationFinding],
) -> None:
    provenance = _require_mapping(data, "provenance", path, findings)
    if not isinstance(provenance, dict):
        return
    _require_string(provenance, "run_id", f"{path}.run_id", findings)
    _require_string(provenance, "rubric_version", f"{path}.rubric_version", findings)
    rubric_version = provenance.get("rubric_version")
    if (
        _is_non_empty_string(rubric_version)
        and rubric_version != expected_rubric_version
    ):
        findings.append(
            _finding(
                f"{path}.rubric_version",
                "invalid_rubric_version",
                f"expected {expected_rubric_version!r}",
            )
        )
    for key in (
        "code_commit",
        "backend",
        "model",
        "prompt_hash",
        "schema_hash",
        "chunk_config_hash",
        "generated_at",
        "parent_evidence_set_id",
    ):
        _optional_string_or_none(provenance, key, f"{path}.{key}", findings)
    generation_parameters = provenance.get("generation_parameters")
    if generation_parameters is not None and not isinstance(
        generation_parameters, dict
    ):
        findings.append(
            _finding(
                f"{path}.generation_parameters",
                "wrong_type",
                f"expected object or null, got {type(generation_parameters).__name__}",
            )
        )
    token_usage = provenance.get("token_usage")
    if token_usage is not None:
        if not isinstance(token_usage, dict):
            findings.append(
                _finding(
                    f"{path}.token_usage",
                    "wrong_type",
                    f"expected object or null, got {type(token_usage).__name__}",
                )
            )
        else:
            for token_key, token_value in token_usage.items():
                token_path = f"{path}.token_usage.{token_key}"
                if not _is_non_empty_string(token_key):
                    findings.append(
                        _finding(
                            f"{path}.token_usage",
                            "wrong_type",
                            "token_usage keys must be non-empty strings",
                        )
                    )
                if (
                    isinstance(token_value, bool)
                    or not isinstance(token_value, int)
                    or token_value < 0
                ):
                    findings.append(
                        _finding(
                            token_path,
                            "wrong_type",
                            "token_usage values must be non-negative integers",
                        )
                    )
    estimated_cost = provenance.get("estimated_cost_usd")
    if estimated_cost is not None:
        if (
            isinstance(estimated_cost, bool)
            or not isinstance(estimated_cost, (int, float))
            or estimated_cost < 0
        ):
            findings.append(
                _finding(
                    f"{path}.estimated_cost_usd",
                    "wrong_type",
                    "estimated_cost_usd must be a non-negative number or null",
                )
            )


def _require_mapping(
    data: dict[str, Any],
    key: str,
    path: str,
    findings: list[models.ValidationFinding],
) -> Any:
    if key not in data:
        findings.append(_missing(path))
        return None
    if not isinstance(data[key], dict):
        findings.append(
            _finding(
                path, "wrong_type", f"expected object, got {type(data[key]).__name__}"
            )
        )
    return data[key]


def _require_list(
    data: dict[str, Any],
    key: str,
    path: str,
    findings: list[models.ValidationFinding],
) -> Any:
    if key not in data:
        findings.append(_missing(path))
        return None
    if not isinstance(data[key], list):
        findings.append(
            _finding(
                path, "wrong_type", f"expected list, got {type(data[key]).__name__}"
            )
        )
    return data[key]


def _require_string(
    data: dict[str, Any],
    key: str,
    path: str,
    findings: list[models.ValidationFinding],
) -> None:
    if key not in data:
        findings.append(_missing(path))
    elif not _is_non_empty_string(data[key]):
        findings.append(
            _finding(
                path,
                "wrong_type",
                f"expected non-empty string, got {type(data[key]).__name__}",
            )
        )


def _require_string_value(
    data: dict[str, Any],
    key: str,
    path: str,
    findings: list[models.ValidationFinding],
) -> None:
    if key not in data:
        findings.append(_missing(path))
    elif not isinstance(data[key], str):
        findings.append(
            _finding(
                path,
                "wrong_type",
                f"expected string, got {type(data[key]).__name__}",
            )
        )


def _validate_string_items(
    data: dict[str, Any],
    key: str,
    path: str,
    findings: list[models.ValidationFinding],
) -> None:
    if key not in data:
        findings.append(_missing(path))
        return
    items = _require_list(data, key, path, findings)
    if not isinstance(items, list):
        return
    for index, item in enumerate(items):
        if not _is_non_empty_string(item):
            findings.append(
                _finding(
                    f"{path}[{index}]",
                    "wrong_type",
                    f"expected non-empty string, got {type(item).__name__}",
                )
            )


def _validate_evidence_anchor(
    anchor: dict[str, Any],
    path: str,
    findings: list[models.ValidationFinding],
) -> None:
    _validate_string_items(anchor, "paragraph_ids", f"{path}.paragraph_ids", findings)
    _require_int(anchor, "start_char", f"{path}.start_char", findings)
    _require_int(anchor, "end_char", f"{path}.end_char", findings)
    start_char = anchor.get("start_char")
    end_char = anchor.get("end_char")
    if (
        isinstance(start_char, int)
        and not isinstance(start_char, bool)
        and isinstance(end_char, int)
        and not isinstance(end_char, bool)
    ):
        if start_char < 0 or end_char < 0:
            findings.append(
                _finding(
                    path,
                    "invalid_anchor",
                    "anchor character offsets must be non-negative",
                )
            )
        if end_char <= start_char:
            findings.append(
                _finding(
                    path,
                    "invalid_anchor",
                    "anchor end_char must be greater than start_char",
                )
            )


def _validate_evidence_provenance_items(
    provenance: list[Any],
    path: str,
    findings: list[models.ValidationFinding],
) -> None:
    for index, item in enumerate(provenance):
        item_path = f"{path}[{index}]"
        if not isinstance(item, dict):
            findings.append(
                _finding(
                    item_path,
                    "wrong_type",
                    f"expected object, got {type(item).__name__}",
                )
            )
            continue
        _require_string(item, "source", f"{item_path}.source", findings)
        _optional_string_or_none(
            item, "source_chunk_id", f"{item_path}.source_chunk_id", findings
        )
        _optional_string_or_none(item, "raw_id", f"{item_path}.raw_id", findings)
        _optional_string_or_none(item, "backend", f"{item_path}.backend", findings)


def _optional_string_or_none(
    data: dict[str, Any],
    key: str,
    path: str,
    findings: list[models.ValidationFinding],
) -> str | None:
    if key not in data or data[key] is None:
        return None
    if not _is_non_empty_string(data[key]):
        findings.append(
            _finding(
                path,
                "wrong_type",
                f"expected non-empty string or null, got {type(data[key]).__name__}",
            )
        )
        return None
    return data[key]


def _require_number(
    data: dict[str, Any],
    key: str,
    path: str,
    findings: list[models.ValidationFinding],
) -> None:
    if key not in data:
        findings.append(_missing(path))
    elif isinstance(data[key], bool) or not isinstance(data[key], (int, float)):
        findings.append(
            _finding(
                path, "wrong_type", f"expected number, got {type(data[key]).__name__}"
            )
        )


def _require_int(
    data: dict[str, Any],
    key: str,
    path: str,
    findings: list[models.ValidationFinding],
) -> None:
    if key not in data:
        findings.append(_missing(path))
    elif isinstance(data[key], bool) or not isinstance(data[key], int):
        findings.append(
            _finding(
                path, "wrong_type", f"expected int, got {type(data[key]).__name__}"
            )
        )


def _require_optional_int(
    data: dict[str, Any],
    key: str,
    path: str,
    findings: list[models.ValidationFinding],
) -> None:
    if key not in data or data[key] is None:
        return
    if isinstance(data[key], bool) or not isinstance(data[key], int):
        findings.append(
            _finding(
                path,
                "wrong_type",
                f"expected int or null, got {type(data[key]).__name__}",
            )
        )


def _validate_optional_confidence(
    data: dict[str, Any],
    path: str,
    findings: list[models.ValidationFinding],
) -> None:
    if "confidence" not in data:
        findings.append(_missing(path))
        return
    if data["confidence"] is None:
        return
    _require_number(data, "confidence", path, findings)
    if (
        isinstance(data["confidence"], (int, float))
        and not 0.0 <= data["confidence"] <= 1.0
    ):
        findings.append(
            _finding(path, "invalid_confidence", "confidence must be between 0 and 1")
        )


def _validate_stage_name(
    stage: str,
    path: str,
    findings: list[models.ValidationFinding],
) -> None:
    if stage not in PARTIAL_SUCCESS_STAGE_NAMES:
        findings.append(
            _finding(
                path,
                "invalid_stage",
                f"expected one of {sorted(PARTIAL_SUCCESS_STAGE_NAMES)!r}",
            )
        )


def _result(findings: list[models.ValidationFinding]) -> models.ValidationResult:
    return models.ValidationResult.from_findings(tuple(findings))


def _finding(path: str, kind: str, message: str) -> models.ValidationFinding:
    return models.ValidationFinding(
        path=path,
        severity="error",
        kind=kind,
        message=message,
    )


def _missing(path: str) -> models.ValidationFinding:
    return _finding(path, "missing_required_field", "missing required field")


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value)


def _atomic_write_text(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
            tmp_file.write(text)
        os.replace(tmp_name, path)
    except BaseException:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise
