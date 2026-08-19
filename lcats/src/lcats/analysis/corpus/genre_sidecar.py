"""Validation helpers for append-only LCATS genre sidecars.

This module defines the structural contract for ``genre-sidecar-v1`` files.
It deliberately does not read, write, promote, or convert corpus sidecars; it
only validates already-loaded JSON-like values and returns structured findings.
"""

from __future__ import annotations

import dataclasses
import datetime
from typing import Any

SCHEMA_VERSION = "genre-sidecar-v1"

ASSESSMENT_LABELS = frozenset(
    {
        "gutenberg_metadata_rules",
        "metadata_rules",
        "model_detect",
        "human_assessment",
        "human_review",
    }
)

ASSESSMENT_LABEL_PREFIXES = frozenset(
    {
        "gutenberg_metadata_",
        "metadata_",
        "model_",
        "human_",
    }
)

SCOPES = frozenset(
    {
        "story",
        "gutenberg_volume",
        "collection",
        "corpus",
    }
)


@dataclasses.dataclass(frozen=True)
class ValidationFinding:
    """One structural validation finding for a genre sidecar."""

    path: str
    severity: str
    kind: str
    message: str


@dataclasses.dataclass(frozen=True)
class ValidationResult:
    """Validation outcome for one loaded genre sidecar value."""

    valid: bool
    findings: tuple[ValidationFinding, ...]


def validate_sidecar(data: Any) -> ValidationResult:
    """Validate one loaded ``genre-sidecar-v1`` object.

    ``data`` is expected to be the result of JSON parsing. Ordinary malformed
    values never raise; they produce findings and ``valid=False``.
    """
    findings: list[ValidationFinding] = []

    if not isinstance(data, dict):
        findings.append(
            _finding(
                "$",
                "error",
                "wrong_type",
                f"expected a JSON object, got {type(data).__name__}",
            )
        )
        return _result(findings)

    if is_legacy_flat_sidecar(data):
        findings.append(
            _finding(
                "$",
                "error",
                "legacy_flat_genre_sidecar",
                (
                    "legacy flat genre.json shape detected; conversion to "
                    "genre-sidecar-v1 is deferred"
                ),
            )
        )
        return _result(findings)

    schema_version = data.get("schema_version")
    _require_string(data, "schema_version", "$.schema_version", findings)
    if _is_non_empty_string(schema_version) and schema_version != SCHEMA_VERSION:
        findings.append(
            _finding(
                "$.schema_version",
                "error",
                "invalid_schema_version",
                f"expected {SCHEMA_VERSION!r}",
            )
        )

    for key in ("lcats_id", "story_path"):
        _require_string(data, key, f"$.{key}", findings)

    assessments = data.get("assessments")
    if "assessments" not in data:
        findings.append(_missing("$.assessments"))
    elif not isinstance(assessments, list):
        findings.append(
            _finding(
                "$.assessments",
                "error",
                "wrong_type",
                f"expected list, got {type(assessments).__name__}",
            )
        )
    else:
        _validate_assessments(assessments, findings)

    if "current_adjudication" in data and data["current_adjudication"] is not None:
        assessment_ids = _assessment_ids(assessments)
        _validate_current_adjudication(
            data["current_adjudication"], assessment_ids, findings
        )

    return _result(findings)


def is_legacy_flat_sidecar(data: Any) -> bool:
    """Return True for legacy ``AssessmentResult.to_dict()`` genre sidecars."""
    return (
        isinstance(data, dict)
        and "detected_genre" in data
        and "assessments" not in data
        and data.get("schema_version") != SCHEMA_VERSION
    )


def _validate_assessments(
    assessments: list[Any], findings: list[ValidationFinding]
) -> None:
    seen_ids: set[str] = set()
    seen_model_run_ids: set[str] = set()
    for index, assessment in enumerate(assessments):
        path = f"$.assessments[{index}]"
        if not isinstance(assessment, dict):
            findings.append(
                _finding(
                    path,
                    "error",
                    "wrong_type",
                    f"expected object, got {type(assessment).__name__}",
                )
            )
            continue

        assessment_id = assessment.get("assessment_id")
        if "assessment_id" not in assessment:
            findings.append(_missing(f"{path}.assessment_id"))
        elif not _is_non_empty_string(assessment_id):
            findings.append(_string_finding(f"{path}.assessment_id"))
        elif assessment_id in seen_ids:
            findings.append(
                _finding(
                    f"{path}.assessment_id",
                    "error",
                    "duplicate_assessment_id",
                    f"duplicate assessment_id {assessment_id!r}",
                )
            )
        else:
            seen_ids.add(assessment_id)

        label = assessment.get("label")
        if "label" not in assessment:
            findings.append(_missing(f"{path}.label"))
        elif not _is_non_empty_string(label):
            findings.append(_string_finding(f"{path}.label"))
        elif not _is_valid_assessment_label(label):
            findings.append(
                _finding(
                    f"{path}.label",
                    "error",
                    "invalid_label",
                    (
                        "expected a canonical assessment label or one beginning "
                        f"with {sorted(ASSESSMENT_LABEL_PREFIXES)!r}"
                    ),
                )
            )

        generated_at = assessment.get("generated_at")
        if "generated_at" not in assessment:
            findings.append(_missing(f"{path}.generated_at"))
        elif not _is_non_empty_string(generated_at):
            findings.append(_string_finding(f"{path}.generated_at"))
        elif not _is_iso_timestamp(generated_at):
            findings.append(
                _finding(
                    f"{path}.generated_at",
                    "error",
                    "invalid_timestamp",
                    "expected an ISO 8601 timestamp",
                )
            )

        scope = assessment.get("scope")
        if "scope" not in assessment:
            findings.append(_missing(f"{path}.scope"))
        elif not _is_non_empty_string(scope):
            findings.append(_string_finding(f"{path}.scope"))
        elif scope not in SCOPES:
            findings.append(
                _finding(
                    f"{path}.scope",
                    "error",
                    "invalid_scope",
                    f"expected one of {sorted(SCOPES)!r}",
                )
            )

        _require_mapping(assessment, "method", f"{path}.method", findings)
        method = assessment.get("method")
        if isinstance(method, dict):
            _require_string(method, "name", f"{path}.method.name", findings)
            _require_string(method, "version", f"{path}.method.version", findings)

        for key in ("provenance", "evidence", "result"):
            _require_mapping(assessment, key, f"{path}.{key}", findings)

        if _is_model_assessment_label(label):
            _validate_model_run_identity(assessment, path, seen_model_run_ids, findings)


def _validate_model_run_identity(
    assessment: dict[str, Any],
    path: str,
    seen_model_run_ids: set[str],
    findings: list[ValidationFinding],
) -> None:
    run_id = None
    if _is_non_empty_string(assessment.get("run_id")):
        run_id = assessment["run_id"]
    else:
        provenance = assessment.get("provenance")
        if isinstance(provenance, dict) and _is_non_empty_string(
            provenance.get("run_id")
        ):
            run_id = provenance["run_id"]

    if run_id is None:
        findings.append(
            _finding(
                path,
                "error",
                "missing_model_run_identity",
                "model assessments must include run_id or provenance.run_id",
            )
        )
        return

    if run_id in seen_model_run_ids:
        findings.append(
            _finding(
                path,
                "error",
                "duplicate_model_run_identity",
                f"duplicate model run identity {run_id!r}",
            )
        )
    else:
        seen_model_run_ids.add(run_id)


def _assessment_ids(assessments: Any) -> set[str]:
    if not isinstance(assessments, list):
        return set()
    return {
        assessment["assessment_id"]
        for assessment in assessments
        if isinstance(assessment, dict)
        and _is_non_empty_string(assessment.get("assessment_id"))
    }


def _is_valid_assessment_label(label: str) -> bool:
    return label in ASSESSMENT_LABELS or any(
        label.startswith(prefix) for prefix in ASSESSMENT_LABEL_PREFIXES
    )


def _is_model_assessment_label(label: Any) -> bool:
    return isinstance(label, str) and (
        label == "model_detect" or label.startswith("model_")
    )


def _validate_current_adjudication(
    adjudication: Any,
    assessment_ids: set[str],
    findings: list[ValidationFinding],
) -> None:
    path = "$.current_adjudication"
    if not isinstance(adjudication, dict):
        findings.append(
            _finding(
                path,
                "error",
                "wrong_type",
                f"expected object or null, got {type(adjudication).__name__}",
            )
        )
        return

    _require_string(adjudication, "label", f"{path}.label", findings)
    selected_id = adjudication.get("selected_assessment_id")
    _require_string(
        adjudication,
        "selected_assessment_id",
        f"{path}.selected_assessment_id",
        findings,
    )
    if _is_non_empty_string(selected_id) and selected_id not in assessment_ids:
        findings.append(
            _finding(
                f"{path}.selected_assessment_id",
                "error",
                "unknown_assessment_id",
                f"selected assessment_id {selected_id!r} is not present",
            )
        )
    decided_at = adjudication.get("decided_at")
    if decided_at is not None:
        if not _is_non_empty_string(decided_at):
            findings.append(_string_finding(f"{path}.decided_at"))
        elif not _is_iso_timestamp(decided_at):
            findings.append(
                _finding(
                    f"{path}.decided_at",
                    "error",
                    "invalid_timestamp",
                    "expected an ISO 8601 timestamp",
                )
            )


def _require_string(
    data: dict[str, Any],
    key: str,
    path: str,
    findings: list[ValidationFinding],
) -> None:
    if key not in data:
        findings.append(_missing(path))
    elif not _is_non_empty_string(data[key]):
        findings.append(_string_finding(path))


def _require_mapping(
    data: dict[str, Any],
    key: str,
    path: str,
    findings: list[ValidationFinding],
) -> None:
    if key not in data:
        findings.append(_missing(path))
    elif not isinstance(data[key], dict):
        findings.append(
            _finding(
                path,
                "error",
                "wrong_type",
                f"expected object, got {type(data[key]).__name__}",
            )
        )


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_iso_timestamp(value: str) -> bool:
    if "T" not in value:
        return False
    try:
        parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _missing(path: str) -> ValidationFinding:
    return _finding(path, "error", "missing_required_field", "missing required field")


def _string_finding(path: str) -> ValidationFinding:
    return _finding(path, "error", "wrong_type", "expected non-empty string")


def _finding(
    path: str,
    severity: str,
    kind: str,
    message: str,
) -> ValidationFinding:
    return ValidationFinding(path=path, severity=severity, kind=kind, message=message)


def _result(findings: list[ValidationFinding]) -> ValidationResult:
    return ValidationResult(valid=not findings, findings=tuple(findings))
