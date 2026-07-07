"""Human review models for findings, repairs, and span operations."""

import json

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence

from lcats.analysis.corpus import repairs
from lcats.analysis.corpus import span_ops
from lcats.analysis.corpus import specials

PENDING = "pending"
APPROVED = "approved"
REJECTED = "rejected"
OVERRIDDEN = "overridden"
ALLOWED = "allowed"
UNRESOLVED = "unresolved"

SPAN_OPERATION_REVIEW_STATES = frozenset((PENDING, APPROVED, REJECTED, OVERRIDDEN))


@dataclass(frozen=True)
class ReviewAuditMetadata:
    """Audit metadata for one span operation review decision."""

    created_at: str = ""
    updated_at: str = ""
    source: str = "human_review"
    notes: str = ""

    def to_dict(self) -> dict[str, str]:
        """Return a stable, JSON-serializable audit metadata payload."""
        return {
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "source": self.source,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, payload: Optional[dict]) -> "ReviewAuditMetadata":
        """Build audit metadata from a serialized mapping."""
        if payload is None:
            return cls()
        return cls(
            created_at=str(payload.get("created_at", "")),
            updated_at=str(payload.get("updated_at", "")),
            source=str(payload.get("source", "human_review")),
            notes=str(payload.get("notes", "")),
        )


@dataclass(frozen=True)
class SpanOperationOverride:
    """Reviewer-specified replacement for a proposed span operation."""

    replacement_operation: span_ops.SpanOperation
    rationale: str = ""

    def to_dict(self) -> dict[str, object]:
        """Return a stable, JSON-serializable override payload."""
        return {
            "replacement_operation": self.replacement_operation.to_dict(),
            "rationale": self.rationale,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "SpanOperationOverride":
        """Build override details from a serialized mapping."""
        return cls(
            replacement_operation=span_ops.SpanOperation.from_dict(
                payload.get("replacement_operation", {})
            ),
            rationale=str(payload.get("rationale", "")),
        )


@dataclass(frozen=True)
class SpanOperationReviewDecision:
    """One auditable human review decision for one span operation."""

    decision_id: str
    span_operation_id: str
    state: str
    reviewer: str
    rationale: str
    reviewed_operation: span_ops.SpanOperation
    audit_metadata: ReviewAuditMetadata = ReviewAuditMetadata()
    override: SpanOperationOverride | None = None

    def to_dict(self) -> dict[str, object]:
        """Return stable, JSON-serializable review decision payload."""
        payload = {
            "decision_id": self.decision_id,
            "span_operation_id": self.span_operation_id,
            "state": self.state,
            "reviewer": self.reviewer,
            "rationale": self.rationale,
            "reviewed_operation": self.reviewed_operation.to_dict(),
            "audit_metadata": self.audit_metadata.to_dict(),
            "override": None,
        }
        if self.override is not None:
            payload["override"] = self.override.to_dict()
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "SpanOperationReviewDecision":
        """Build a span operation review decision from a mapping."""
        override_payload = payload.get("override")
        decision = cls(
            decision_id=str(payload.get("decision_id", "")),
            span_operation_id=str(payload.get("span_operation_id", "")),
            state=str(payload.get("state", PENDING)),
            reviewer=str(payload.get("reviewer", "")),
            rationale=str(payload.get("rationale", "")),
            reviewed_operation=span_ops.SpanOperation.from_dict(
                payload.get("reviewed_operation", {})
            ),
            audit_metadata=ReviewAuditMetadata.from_dict(payload.get("audit_metadata")),
            override=(
                SpanOperationOverride.from_dict(override_payload)
                if override_payload is not None
                else None
            ),
        )
        validate_span_operation_review_decision(decision)
        return decision


def _has_review_text(value: str) -> bool:
    """Return True when a review text field contains non-whitespace text."""
    return value.strip() != ""


def validate_span_operation_review_decision(
    decision: SpanOperationReviewDecision,
) -> None:
    """Fail fast when a span operation review decision is inconsistent."""
    if decision.state not in SPAN_OPERATION_REVIEW_STATES:
        raise ValueError("unsupported review decision state")
    if decision.span_operation_id != decision.reviewed_operation.operation_id:
        raise ValueError("span_operation_id must match reviewed operation")
    span_ops.validate_operation(decision.reviewed_operation)

    if not _has_review_text(decision.rationale):
        raise ValueError("review rationale is required")

    if decision.state == OVERRIDDEN:
        if decision.override is None:
            raise ValueError("overridden decisions require override details")
        if not _has_review_text(decision.override.rationale):
            raise ValueError("override rationale is required")
        span_ops.validate_operation(decision.override.replacement_operation)
    elif decision.override is not None:
        raise ValueError("only overridden decisions may include override details")


def is_span_operation_review_eligible_for_application(
    decision: SpanOperationReviewDecision,
) -> bool:
    """Return True when the reviewed operation can feed application planning."""
    validate_span_operation_review_decision(decision)
    return decision.state in (APPROVED, OVERRIDDEN)


def operation_for_application(
    decision: SpanOperationReviewDecision,
) -> span_ops.SpanOperation:
    """Return the approved operation or reviewer replacement for application."""
    if not is_span_operation_review_eligible_for_application(decision):
        raise ValueError("review decision is not eligible for application")
    if decision.state == OVERRIDDEN:
        return decision.override.replacement_operation
    return decision.reviewed_operation


def _span_operation_review_decision_sort_key(
    decision: SpanOperationReviewDecision,
) -> tuple[object, ...]:
    """Return deterministic ordering key for span operation review decisions."""
    return (
        span_ops.operation_sort_key(decision.reviewed_operation),
        decision.decision_id,
        decision.span_operation_id,
        decision.state,
        decision.reviewer,
    )


def serialize_span_operation_review_decisions(
    decisions: Sequence[SpanOperationReviewDecision],
) -> str:
    """Serialize validated span operation review decisions to stable JSON."""
    for decision in decisions:
        validate_span_operation_review_decision(decision)
    ordered = sorted(decisions, key=_span_operation_review_decision_sort_key)
    payload = [decision.to_dict() for decision in ordered]
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)


def deserialize_span_operation_review_decisions(
    payload: str,
) -> list[SpanOperationReviewDecision]:
    """Deserialize and validate span operation review decisions from JSON."""
    loaded = json.loads(payload)
    return [SpanOperationReviewDecision.from_dict(item) for item in loaded]


@dataclass(frozen=True)
class RepairReviewDecision:
    """One human review decision for a repair suggestion signature."""

    rule_id: str
    original_text: str
    replacement_text: str
    decision: str
    rationale: str = ""


@dataclass(frozen=True)
class AllowedSpecialCase:
    """One allow/expected rule for special-character findings."""

    character: str = ""
    codepoint: str = ""
    classification: str = ""
    evidence_contains: str = ""
    rationale: str = ""


@dataclass(frozen=True)
class ReviewedRepairs:
    """Repair suggestions grouped by review decision."""

    approved: tuple[repairs.RepairSuggestion, ...]
    rejected: tuple[repairs.RepairSuggestion, ...]
    unresolved: tuple[repairs.RepairSuggestion, ...]


@dataclass(frozen=True)
class ReviewDecisionStore:
    """Structured, serializable review decisions for specials and repairs."""

    repair_decisions: tuple[RepairReviewDecision, ...] = ()
    allowed_special_cases: tuple[AllowedSpecialCase, ...] = ()

    def to_dict(self) -> dict[str, list[dict[str, str]]]:
        """Return a JSON-serializable representation for persistence."""
        return {
            "repair_decisions": [
                {
                    "rule_id": decision.rule_id,
                    "original_text": decision.original_text,
                    "replacement_text": decision.replacement_text,
                    "decision": decision.decision,
                    "rationale": decision.rationale,
                }
                for decision in self.repair_decisions
            ],
            "allowed_special_cases": [
                {
                    "character": allowed.character,
                    "codepoint": allowed.codepoint,
                    "classification": allowed.classification,
                    "evidence_contains": allowed.evidence_contains,
                    "rationale": allowed.rationale,
                }
                for allowed in self.allowed_special_cases
            ],
        }

    @classmethod
    def from_dict(cls, payload: Optional[dict]) -> "ReviewDecisionStore":
        """Create a review decision store from a dict payload."""
        if payload is None:
            return cls()

        return cls(
            repair_decisions=tuple(
                RepairReviewDecision(
                    rule_id=item.get("rule_id", ""),
                    original_text=item.get("original_text", ""),
                    replacement_text=item.get("replacement_text", ""),
                    decision=item.get("decision", UNRESOLVED),
                    rationale=item.get("rationale", ""),
                )
                for item in payload.get("repair_decisions", [])
            ),
            allowed_special_cases=tuple(
                AllowedSpecialCase(
                    character=item.get("character", ""),
                    codepoint=item.get("codepoint", ""),
                    classification=item.get("classification", ""),
                    evidence_contains=item.get("evidence_contains", ""),
                    rationale=item.get("rationale", ""),
                )
                for item in payload.get("allowed_special_cases", [])
            ),
        )


def find_repair_decision(
    suggestion: repairs.RepairSuggestion,
    decision_store: ReviewDecisionStore,
) -> str:
    """Return the decision state for one repair suggestion."""
    for decision in decision_store.repair_decisions:
        if decision.rule_id != suggestion.rule_id:
            continue
        if decision.original_text != suggestion.original_text:
            continue
        if decision.replacement_text != suggestion.replacement_text:
            continue
        return decision.decision
    return UNRESOLVED


def apply_review_to_repairs(
    suggestions: Sequence[repairs.RepairSuggestion],
    decision_store: Optional[ReviewDecisionStore],
) -> ReviewedRepairs:
    """Partition repairs into approved, rejected, and unresolved groups."""
    if decision_store is None:
        return ReviewedRepairs(
            approved=(),
            rejected=(),
            unresolved=tuple(suggestions),
        )

    approved: list[repairs.RepairSuggestion] = []
    rejected: list[repairs.RepairSuggestion] = []
    unresolved: list[repairs.RepairSuggestion] = []

    for suggestion in suggestions:
        decision = find_repair_decision(suggestion, decision_store)
        if decision == APPROVED:
            approved.append(suggestion)
        elif decision == REJECTED:
            rejected.append(suggestion)
        else:
            unresolved.append(suggestion)

    return ReviewedRepairs(
        approved=tuple(approved),
        rejected=tuple(rejected),
        unresolved=tuple(unresolved),
    )


def _is_allowed_by_case(
    finding: specials.SpecialCharacter,
    allowed_case: AllowedSpecialCase,
) -> bool:
    """Return True when an allow rule matches one special-character finding."""
    if allowed_case.character and allowed_case.character != finding.character:
        return False
    if allowed_case.codepoint and allowed_case.codepoint != finding.codepoint:
        return False
    if (
        allowed_case.classification
        and allowed_case.classification != finding.classification
    ):
        return False
    if (
        allowed_case.evidence_contains
        and allowed_case.evidence_contains not in finding.evidence
    ):
        return False
    return True


def should_suppress_special(
    finding: specials.SpecialCharacter,
    decision_store: Optional[ReviewDecisionStore],
) -> bool:
    """Return True when a finding is covered by an allowed special-case rule."""
    if decision_store is None:
        return False

    for allowed_case in decision_store.allowed_special_cases:
        if _is_allowed_by_case(finding, allowed_case):
            return True
    return False


def apply_review_to_specials(
    findings: Iterable[specials.SpecialCharacter],
    decision_store: Optional[ReviewDecisionStore],
) -> list[specials.SpecialCharacter]:
    """Filter findings using allow/expected special-character decisions."""
    if decision_store is None:
        return list(findings)
    return [
        finding
        for finding in findings
        if not should_suppress_special(finding, decision_store)
    ]
