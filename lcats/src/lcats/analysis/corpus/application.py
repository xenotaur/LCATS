"""Apply reviewed span operations to text without mutating corpus sources."""

from dataclasses import dataclass
from typing import Sequence

from lcats.analysis.corpus import review
from lcats.analysis.corpus import span_ops

APPLIED = "applied"
ELIGIBLE = "eligible"
SKIPPED = "skipped"


@dataclass(frozen=True)
class ApplicationDecisionReport:
    """Audit record for one review decision considered for application."""

    decision_id: str
    span_operation_id: str
    state: str
    outcome: str
    reason: str
    operation_id: str = ""
    override_used: bool = False
    reviewer: str = ""
    rationale: str = ""

    def to_dict(self) -> dict[str, object]:
        """Return a stable, JSON-serializable report payload."""
        return {
            "decision_id": self.decision_id,
            "span_operation_id": self.span_operation_id,
            "state": self.state,
            "outcome": self.outcome,
            "reason": self.reason,
            "operation_id": self.operation_id,
            "override_used": self.override_used,
            "reviewer": self.reviewer,
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class ApplicationFailure:
    """Structured validation failure for an application attempt."""

    message: str
    operation_id: str = ""
    decision_id: str = ""

    def to_dict(self) -> dict[str, str]:
        """Return a stable, JSON-serializable failure payload."""
        return {
            "message": self.message,
            "operation_id": self.operation_id,
            "decision_id": self.decision_id,
        }


@dataclass(frozen=True)
class ApplicationResult:
    """Structured result for non-destructive reviewed operation application."""

    success: bool
    original_text: str
    transformed_text: str
    considered: tuple[ApplicationDecisionReport, ...]
    applied: tuple[ApplicationDecisionReport, ...]
    skipped: tuple[ApplicationDecisionReport, ...]
    failures: tuple[ApplicationFailure, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return a stable, JSON-serializable application result payload."""
        return {
            "success": self.success,
            "original_text": self.original_text,
            "transformed_text": self.transformed_text,
            "considered": [item.to_dict() for item in self.considered],
            "applied": [item.to_dict() for item in self.applied],
            "skipped": [item.to_dict() for item in self.skipped],
            "failures": [item.to_dict() for item in self.failures],
        }


def _failure_result(
    text: str,
    considered: list[ApplicationDecisionReport],
    applied: Sequence[ApplicationDecisionReport],
    skipped: list[ApplicationDecisionReport],
    failure: ApplicationFailure,
) -> ApplicationResult:
    """Return a failed result without applying a partial transformation."""
    return ApplicationResult(
        success=False,
        original_text=text,
        transformed_text=text,
        considered=tuple(considered),
        applied=tuple(applied),
        skipped=tuple(skipped),
        failures=(failure,),
    )


def _validate_operation_against_text(
    text: str,
    operation: span_ops.SpanOperation,
) -> None:
    """Fail when an operation cannot be safely applied to this text."""
    span_ops.validate_operation(operation)
    if operation.end > len(text):
        raise ValueError("operation span exceeds text length")
    if operation.operation_type != span_ops.INSERT_SPAN:
        actual = text[operation.start : operation.end]
        if actual != operation.original_text:
            raise ValueError("operation original_text does not match text span")


def _application_sort_key(
    decision: review.SpanOperationReviewDecision,
    operation: span_ops.SpanOperation,
) -> tuple[object, ...]:
    """Return deterministic ordering key for decisions entering application."""
    return (
        span_ops.operation_sort_key(operation),
        decision.decision_id,
        decision.span_operation_id,
        decision.state,
        decision.reviewer,
    )


def _apply_operations(
    text: str,
    operations: Sequence[span_ops.SpanOperation],
) -> str:
    """Apply validated non-overlapping operations from right to left."""
    transformed = text
    for operation in reversed(span_ops.sort_operations(operations)):
        if operation.operation_type == span_ops.REMOVE_SPAN:
            replacement = ""
        else:
            replacement = operation.replacement_text
        transformed = (
            transformed[: operation.start] + replacement + transformed[operation.end :]
        )
    return transformed


def apply_reviewed_operations(
    text: str,
    decisions: Sequence[review.SpanOperationReviewDecision],
) -> ApplicationResult:
    """Apply approved or overridden span operations to text.

    Pending and rejected decisions are audited as skipped. Validation happens
    before any transformation is returned as successful, so invalid spans,
    mismatched source text, duplicate operation ids, and overlaps fail without a
    partial output.
    """
    considered: list[ApplicationDecisionReport] = []
    skipped: list[ApplicationDecisionReport] = []
    eligible_reports: list[ApplicationDecisionReport] = []
    eligible_operations: list[span_ops.SpanOperation] = []
    operation_decisions: dict[str, str] = {}
    ordered_items: list[
        tuple[
            tuple[object, ...],
            review.SpanOperationReviewDecision,
            span_ops.SpanOperation,
            bool,
        ]
    ] = []

    for decision in decisions:
        try:
            review.validate_span_operation_review_decision(decision)
        except ValueError as error:
            failure = ApplicationFailure(str(error), decision_id=decision.decision_id)
            return _failure_result(text, considered, (), skipped, failure)

        if review.is_span_operation_review_eligible_for_application(decision):
            operation = review.operation_for_application(decision)
            override_used = decision.state == review.OVERRIDDEN
        else:
            operation = decision.reviewed_operation
            override_used = False
        ordered_items.append(
            (
                _application_sort_key(decision, operation),
                decision,
                operation,
                override_used,
            )
        )

    for _sort_key, decision, operation, override_used in sorted(ordered_items):
        if not review.is_span_operation_review_eligible_for_application(decision):
            report = ApplicationDecisionReport(
                decision_id=decision.decision_id,
                span_operation_id=decision.span_operation_id,
                state=decision.state,
                outcome=SKIPPED,
                reason="review state is not eligible for application",
                operation_id=operation.operation_id,
                reviewer=decision.reviewer,
                rationale=decision.rationale,
            )
            considered.append(report)
            skipped.append(report)
            continue

        report = ApplicationDecisionReport(
            decision_id=decision.decision_id,
            span_operation_id=decision.span_operation_id,
            state=decision.state,
            outcome=ELIGIBLE,
            reason="review state is eligible for application",
            operation_id=operation.operation_id,
            override_used=override_used,
            reviewer=decision.reviewer,
            rationale=decision.rationale,
        )
        considered.append(report)
        eligible_reports.append(report)
        eligible_operations.append(operation)
        operation_decisions[operation.operation_id] = decision.decision_id

    try:
        span_ops.validate_operation_set(eligible_operations)
        for operation in span_ops.sort_operations(eligible_operations):
            try:
                _validate_operation_against_text(text, operation)
            except ValueError as error:
                failure = ApplicationFailure(
                    str(error),
                    operation_id=operation.operation_id,
                    decision_id=operation_decisions.get(operation.operation_id, ""),
                )
                return _failure_result(text, considered, (), skipped, failure)
    except ValueError as error:
        failure = ApplicationFailure(str(error))
        return _failure_result(text, considered, (), skipped, failure)

    applied = tuple(
        ApplicationDecisionReport(
            decision_id=report.decision_id,
            span_operation_id=report.span_operation_id,
            state=report.state,
            outcome=APPLIED,
            reason="operation applied after validation",
            operation_id=report.operation_id,
            override_used=report.override_used,
            reviewer=report.reviewer,
            rationale=report.rationale,
        )
        for report in eligible_reports
    )

    return ApplicationResult(
        success=True,
        original_text=text,
        transformed_text=_apply_operations(text, eligible_operations),
        considered=tuple(considered),
        applied=applied,
        skipped=tuple(skipped),
    )
