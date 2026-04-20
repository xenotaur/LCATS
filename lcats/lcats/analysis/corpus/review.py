"""Human review decisions for special-character findings and repairs."""

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence

from lcats.analysis.corpus import repairs
from lcats.analysis.corpus import specials

APPROVED = "approved"
REJECTED = "rejected"
ALLOWED = "allowed"
UNRESOLVED = "unresolved"


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
