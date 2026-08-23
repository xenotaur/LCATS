"""Validation and publication helpers for science-fiction sidecars."""

from __future__ import annotations

import json
import os
import pathlib
import tempfile
from typing import Any

from lcats.analysis.science_fiction import models

SCHEMA_VERSION = models.SCIENCE_FICTION_SIDECAR_VERSION
SIDECAR_FILENAME = "science-fiction.json"


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
        _require_list(item, "quarantined", f"{base}.quarantined", findings)
        _require_list(item, "conflicts", f"{base}.conflicts", findings)
        if isinstance(records, list) and _is_non_empty_string(evidence_set_id):
            _validate_evidence_records(
                records, base, evidence_ids_by_set[evidence_set_id], findings
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
        _require_string(record, "quote", f"{base}.quote", findings)
        _require_mapping(record, "anchor", f"{base}.anchor", findings)
        _require_string(record, "paraphrase", f"{base}.paraphrase", findings)
        _require_number(record, "confidence", f"{base}.confidence", findings)
        _require_list(record, "provenance", f"{base}.provenance", findings)
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
        _require_list(analysis, "failures", f"{base}.failures", findings)
        status = analysis.get("status")
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
        if _is_non_empty_string(evidence_set_id):
            _validate_analysis_references(
                analysis,
                base,
                analysis_evidence_set_id=evidence_set_id,
                evidence_ids_by_set=evidence_ids_by_set,
                findings=findings,
            )
    return index_by_id


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
    for criteria_index, criterion in enumerate(analysis.get("criteria", ()) or ()):
        if not isinstance(criterion, dict):
            continue
        criterion_base = f"{base}.criteria[{criteria_index}]"
        for field in ("supporting_evidence", "counterevidence"):
            references.extend(
                (f"{criterion_base}.{field}[{index}]", item)
                for index, item in enumerate(criterion.get(field, ()) or ())
            )
    for candidate_index, candidate in enumerate(analysis.get("candidates", ()) or ()):
        if not isinstance(candidate, dict):
            continue
        candidate_base = f"{base}.candidates[{candidate_index}]"
        references.extend(
            (f"{candidate_base}.evidence[{index}]", item)
            for index, item in enumerate(candidate.get("evidence", ()) or ())
        )
        for dimension_name in ("novelty", "cognitive_validation", "narrative_hegemony"):
            dimension = candidate.get(dimension_name)
            if not isinstance(dimension, dict):
                continue
            dimension_base = f"{candidate_base}.{dimension_name}"
            for field in ("supporting_evidence", "counterevidence"):
                references.extend(
                    (f"{dimension_base}.{field}[{index}]", item)
                    for index, item in enumerate(dimension.get(field, ()) or ())
                )
        estrangement = candidate.get("estrangement")
        if isinstance(estrangement, dict):
            for field in (
                "reader_facing_evidence",
                "storyworld_consequence_evidence",
                "character_reaction_evidence",
            ):
                references.extend(
                    (f"{candidate_base}.estrangement.{field}[{index}]", item)
                    for index, item in enumerate(estrangement.get(field, ()) or ())
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
                seen.add(stage)
    if isinstance(failed, list):
        for index, failure in enumerate(failed):
            _validate_failure_record(
                failure, f"$.partial_success.failed_stages[{index}]", findings
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
    stored_findings = _require_list(data, "findings", "$.validation.findings", findings)
    if isinstance(stored_findings, list):
        for index, stored in enumerate(stored_findings):
            if not isinstance(stored, dict):
                findings.append(
                    _finding(
                        f"$.validation.findings[{index}]",
                        "wrong_type",
                        f"expected object, got {type(stored).__name__}",
                    )
                )
                continue
            for key in ("path", "severity", "kind", "message"):
                _require_string(
                    stored, key, f"$.validation.findings[{index}].{key}", findings
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
    elif not isinstance(data[key], int | float):
        findings.append(
            _finding(
                path, "wrong_type", f"expected number, got {type(data[key]).__name__}"
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
