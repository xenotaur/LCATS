"""Canonical span operation model for deterministic repair workflows."""

import json

from dataclasses import dataclass
from typing import Iterable, Sequence

REPLACE_SPAN = "replace_span"
REMOVE_SPAN = "remove_span"
INSERT_SPAN = "insert_span"

_OPERATION_ORDER = {
    REMOVE_SPAN: 0,
    REPLACE_SPAN: 1,
    INSERT_SPAN: 2,
}


@dataclass(frozen=True)
class SpanOperationProvenance:
    """Traceability metadata linking span operations to repair planning."""

    rule_id: str
    source: str
    finding_offset: int
    evidence: str
    rationale: str = ""
    confidence: str = "high"

    def to_dict(self) -> dict[str, str | int]:
        """Return a stable, JSON-serializable provenance payload."""
        return {
            "rule_id": self.rule_id,
            "source": self.source,
            "finding_offset": self.finding_offset,
            "evidence": self.evidence,
            "rationale": self.rationale,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "SpanOperationProvenance":
        """Build provenance from a serialized mapping."""
        return cls(
            rule_id=str(payload.get("rule_id", "")),
            source=str(payload.get("source", "")),
            finding_offset=int(payload.get("finding_offset", 0)),
            evidence=str(payload.get("evidence", "")),
            rationale=str(payload.get("rationale", "")),
            confidence=str(payload.get("confidence", "high")),
        )


@dataclass(frozen=True)
class SpanOperation:
    """One canonical span operation over character offsets."""

    operation_id: str
    operation_type: str
    start: int
    end: int
    replacement_text: str
    original_text: str
    provenance: SpanOperationProvenance

    def to_dict(self) -> dict[str, object]:
        """Return stable, JSON-serializable operation payload."""
        return {
            "operation_id": self.operation_id,
            "operation_type": self.operation_type,
            "start": self.start,
            "end": self.end,
            "replacement_text": self.replacement_text,
            "original_text": self.original_text,
            "provenance": self.provenance.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "SpanOperation":
        """Build one operation from a serialized mapping."""
        return cls(
            operation_id=str(payload.get("operation_id", "")),
            operation_type=str(payload.get("operation_type", REPLACE_SPAN)),
            start=int(payload.get("start", 0)),
            end=int(payload.get("end", 0)),
            replacement_text=str(payload.get("replacement_text", "")),
            original_text=str(payload.get("original_text", "")),
            provenance=SpanOperationProvenance.from_dict(payload.get("provenance", {})),
        )


def operation_sort_key(operation: SpanOperation) -> tuple[object, ...]:
    """Return deterministic ordering key for span operations."""
    return (
        operation.start,
        operation.end,
        _OPERATION_ORDER.get(operation.operation_type, 99),
        operation.replacement_text,
        operation.provenance.rule_id,
        operation.provenance.finding_offset,
        operation.operation_id,
    )


def sort_operations(operations: Iterable[SpanOperation]) -> list[SpanOperation]:
    """Return deterministically sorted operations."""
    return sorted(operations, key=operation_sort_key)


def validate_operation(operation: SpanOperation) -> None:
    """Fail fast when one operation is internally inconsistent."""
    if operation.start < 0:
        raise ValueError("start must be non-negative")
    if operation.end < operation.start:
        raise ValueError("end must be greater than or equal to start")
    if operation.operation_type not in _OPERATION_ORDER:
        raise ValueError("unsupported operation_type")

    if operation.operation_type == INSERT_SPAN and operation.start != operation.end:
        raise ValueError("insert_span requires start == end")
    if operation.operation_type in (REMOVE_SPAN, REPLACE_SPAN):
        if operation.start == operation.end:
            raise ValueError("remove_span and replace_span require non-empty spans")

    if operation.operation_type == REMOVE_SPAN and operation.replacement_text != "":
        raise ValueError("remove_span replacement_text must be empty")
    if operation.operation_type == INSERT_SPAN and operation.original_text != "":
        raise ValueError("insert_span original_text must be empty")


def validate_operation_set(operations: Sequence[SpanOperation]) -> None:
    """Fail fast when an operation set is invalid or ambiguous."""
    ordered = sort_operations(operations)
    seen_ids: set[str] = set()
    previous: SpanOperation | None = None

    for operation in ordered:
        validate_operation(operation)
        if operation.operation_id in seen_ids:
            raise ValueError("duplicate operation_id")
        seen_ids.add(operation.operation_id)

        if previous is None:
            previous = operation
            continue

        if previous.end > operation.start:
            raise ValueError("overlapping spans are not allowed")
        if (
            previous.operation_type == INSERT_SPAN
            and operation.operation_type == INSERT_SPAN
            and previous.start == operation.start
        ):
            raise ValueError("multiple insert_span operations at the same index")

        previous = operation


def serialize_operations(operations: Sequence[SpanOperation]) -> str:
    """Serialize a validated canonical operation set to stable JSON."""
    validate_operation_set(operations)
    payload = [operation.to_dict() for operation in sort_operations(operations)]
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)


def deserialize_operations(payload: str) -> list[SpanOperation]:
    """Deserialize and validate canonical operations from JSON."""
    loaded = json.loads(payload)
    operations = [SpanOperation.from_dict(item) for item in loaded]
    validate_operation_set(operations)
    return sort_operations(operations)


def from_repair_suggestions(
    suggestions: Sequence[object],
    *,
    source: str = "repair_proposal",
) -> list[SpanOperation]:
    """Convert repair suggestions into canonical span operations.

    Args:
        suggestions: Sequence of repair suggestion objects with required fields.
        source: Provenance source label.

    Returns:
        Deterministically ordered canonical span operations.
    """
    sortable = sorted(
        suggestions,
        key=lambda suggestion: (
            suggestion.start,
            suggestion.end,
            suggestion.rule_id,
            suggestion.replacement_text,
            suggestion.original_text,
            suggestion.finding_offset,
            suggestion.evidence,
        ),
    )

    operations: list[SpanOperation] = []
    for index, suggestion in enumerate(sortable):
        operation_id = f"spanop-{index:06d}-{suggestion.rule_id}"
        operations.append(
            SpanOperation(
                operation_id=operation_id,
                operation_type=REPLACE_SPAN,
                start=suggestion.start,
                end=suggestion.end,
                replacement_text=suggestion.replacement_text,
                original_text=suggestion.original_text,
                provenance=SpanOperationProvenance(
                    rule_id=suggestion.rule_id,
                    source=source,
                    finding_offset=suggestion.finding_offset,
                    evidence=suggestion.evidence,
                    rationale=suggestion.rationale,
                    confidence=suggestion.confidence,
                ),
            )
        )

    validate_operation_set(operations)
    return sort_operations(operations)
