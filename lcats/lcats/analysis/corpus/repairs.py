"""Conservative repair proposal helpers for special-character findings."""

import json

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence

from lcats.analysis.corpus import specials
from lcats.analysis.corpus import span_ops


@dataclass(frozen=True)
class RepairRule:
    """One conservative replacement rule for known mojibake fragments."""

    rule_id: str
    source_text: str
    replacement_text: str
    description: str


@dataclass(frozen=True)
class RepairSuggestion:
    """A proposed repair derived from a classified finding."""

    rule_id: str
    start: int
    end: int
    original_text: str
    replacement_text: str
    finding_offset: int
    evidence: str
    confidence: str = "high"
    rationale: str = ""


@dataclass(frozen=True)
class SpanRepairOperation:
    """Explicit span-based text operation for conservative repair workflows."""

    operation: str
    start: int
    end: int
    original_text: str
    replacement_text: str
    rule_id: str
    evidence: str
    rationale: str = ""
    confidence: str = "high"


@dataclass(frozen=True)
class RepairPlanEntry:
    """One machine-serializable dry-run plan entry."""

    start: int
    end: int
    original_text: str
    replacement_text: str
    rule_id: str
    confidence: str
    evidence: str
    rationale: str
    finding_offset: int


# Every source_text below was verified byte-for-byte against the live data/
# tree (2026-07-13 scan); do not add rules from memory — measure first.
DEFAULT_REPAIR_RULES = (
    # UTF-8 bytes decoded as Latin-1 upstream (é stored as C3 A9 -> "Ã©").
    RepairRule(
        rule_id="mojibake-latin1-e-acute",
        source_text="Ã©",
        replacement_text="é",
        description="UTF-8 'é' decoded as Latin-1 (resumÃ©, clichÃ©).",
    ),
    RepairRule(
        rule_id="mojibake-latin1-e-diaeresis",
        source_text="Ã«",
        replacement_text="ë",
        description="UTF-8 'ë' decoded as Latin-1 (aÃ«rial).",
    ),
    RepairRule(
        rule_id="mojibake-latin1-e-circumflex",
        source_text="Ãª",
        replacement_text="ê",
        description="UTF-8 'ê' decoded as Latin-1 (vÃªtements).",
    ),
    RepairRule(
        rule_id="mojibake-latin1-o-diaeresis",
        source_text="Ã¶",
        replacement_text="ö",
        description="UTF-8 'ö' decoded as Latin-1 (uncoÃ¶rdinated).",
    ),
    RepairRule(
        rule_id="mojibake-latin1-i-diaeresis",
        source_text="Ã¯",
        replacement_text="ï",
        description="UTF-8 'ï' decoded as Latin-1 (naÃ¯vely).",
    ),
    RepairRule(
        rule_id="mojibake-latin1-a-grave",
        source_text="Ã ",
        replacement_text="à",
        description="UTF-8 'à' decoded as Latin-1 (Ã la; second byte is NBSP).",
    ),
    RepairRule(
        rule_id="mojibake-latin1-degree-sign",
        source_text="Â°",
        replacement_text="°",
        description="UTF-8 '°' decoded as Latin-1 (60Â° below).",
    ),
    RepairRule(
        rule_id="mojibake-latin1-cent-sign",
        source_text="Â¢",
        replacement_text="¢",
        description="UTF-8 '¢' decoded as Latin-1 (90Â¢).",
    ),
    # UTF-8 bytes decoded as Mac-Roman upstream (é stored as C3 A9 -> "√©").
    RepairRule(
        rule_id="mojibake-macroman-e-acute",
        source_text="√©",
        replacement_text="é",
        description="UTF-8 'é' decoded as Mac-Roman (blas√©, Merop√©).",
    ),
    RepairRule(
        rule_id="mojibake-macroman-e-grave",
        source_text="√®",
        replacement_text="è",
        description="UTF-8 'è' decoded as Mac-Roman (fin de si√®cle).",
    ),
    RepairRule(
        rule_id="mojibake-macroman-n-tilde",
        source_text="√±",
        replacement_text="ñ",
        description="UTF-8 'ñ' decoded as Mac-Roman (se√±orita).",
    ),
    RepairRule(
        rule_id="mojibake-macroman-u-diaeresis",
        source_text="√º",
        replacement_text="ü",
        description="UTF-8 'ü' decoded as Mac-Roman (Tha√ºle).",
    ),
    RepairRule(
        rule_id="mojibake-macroman-o-diaeresis",
        source_text="√∂",
        replacement_text="ö",
        description="UTF-8 'ö' decoded as Mac-Roman (Ragnar√∂k).",
    ),
    RepairRule(
        rule_id="mojibake-macroman-o-grave",
        source_text="√≤",
        replacement_text="ò",
        description="UTF-8 'ò' decoded as Mac-Roman (Niccol√≤).",
    ),
    RepairRule(
        rule_id="mojibake-macroman-ae",
        source_text="√¶",
        replacement_text="æ",
        description="UTF-8 'æ' decoded as Mac-Roman (hypnop√¶dic).",
    ),
)


def _rule_map(rules: Sequence[RepairRule]) -> dict[str, RepairRule]:
    return {rule.source_text: rule for rule in rules}


def _extract_evidence_fragment(evidence: str) -> str:
    """Return fragment value from semicolon-delimited evidence string.

    Only leading whitespace is removed: fragments may legitimately end in
    Unicode whitespace (e.g. "Ã" + NBSP for mojibake 'à'), which .strip()
    would silently delete.
    """
    for part in evidence.split(";"):
        segment = part.lstrip()
        if segment.startswith("fragment="):
            return segment.split("=", 1)[1]
    return ""


def _find_unique_span_containing_offset(
    text: str, fragment: str, offset: int
) -> Optional[tuple[int, int]]:
    """Return unique span for fragment containing offset, or None."""
    spans = []
    start = 0
    while True:
        index = text.find(fragment, start)
        if index == -1:
            break
        end = index + len(fragment)
        if index <= offset < end:
            spans.append((index, end))
        start = index + 1

    if len(spans) != 1:
        return None
    return spans[0]


def suggest_repairs(
    text: str,
    findings: Iterable[specials.SpecialCharacter],
    rules: Sequence[RepairRule] = DEFAULT_REPAIR_RULES,
    decision_store=None,
) -> list[RepairSuggestion]:
    """Convert likely-repairable findings into conservative suggestions.

    Args:
        text: Original story text.
        findings: Classified special-character findings.
        rules: Supported high-confidence replacement rules.

    Returns:
        Repair suggestions with explicit original/proposed text and source rule.
    """
    repair_rules = _rule_map(rules)
    suggestions: list[RepairSuggestion] = []
    seen_spans: set[tuple[int, int]] = set()

    filtered_findings = list(findings)
    if decision_store is not None:
        from lcats.analysis.corpus import review

        filtered_findings = review.apply_review_to_specials(
            filtered_findings,
            decision_store,
        )

    for finding in filtered_findings:
        if finding.classification != "likely_repairable":
            continue

        fragment = _extract_evidence_fragment(finding.evidence)
        if not fragment:
            continue

        rule = repair_rules.get(fragment)
        if not rule:
            continue

        span = _find_unique_span_containing_offset(text, fragment, finding.offset)
        if span is None or span in seen_spans:
            continue

        start, end = span
        seen_spans.add(span)
        suggestions.append(
            RepairSuggestion(
                rule_id=rule.rule_id,
                start=start,
                end=end,
                original_text=text[start:end],
                replacement_text=rule.replacement_text,
                finding_offset=finding.offset,
                evidence=finding.evidence,
                confidence="high",
                rationale=rule.description,
            )
        )

    suggestions.sort(key=lambda suggestion: (suggestion.start, suggestion.end))
    return suggestions


def apply_repair_suggestions(text: str, suggestions: Sequence[RepairSuggestion]) -> str:
    """Apply suggestions using explicit span operations."""
    operations = suggestions_to_span_operations(suggestions)
    return apply_span_operations(text, operations)


def suggestions_to_span_operations(
    suggestions: Sequence[RepairSuggestion],
) -> list[SpanRepairOperation]:
    """Convert suggestions to explicit span-replace operations."""
    operations = [
        SpanRepairOperation(
            operation="replace",
            start=suggestion.start,
            end=suggestion.end,
            original_text=suggestion.original_text,
            replacement_text=suggestion.replacement_text,
            rule_id=suggestion.rule_id,
            evidence=suggestion.evidence,
            rationale=suggestion.rationale,
            confidence=suggestion.confidence,
        )
        for suggestion in suggestions
    ]
    operations.sort(
        key=lambda operation: (operation.start, operation.end, operation.rule_id)
    )
    return operations


def suggestions_to_canonical_span_operations(
    suggestions: Sequence[RepairSuggestion],
) -> list[span_ops.SpanOperation]:
    """Convert repair suggestions to canonical span operations.

    This conversion is representational only and does not apply edits.
    """
    return span_ops.from_repair_suggestions(
        suggestions,
        source="repair_suggestion",
    )


def _has_overlapping_spans(operations: Sequence[SpanRepairOperation]) -> bool:
    """Return True when any sorted operation span overlaps."""
    sorted_operations = sorted(
        operations, key=lambda current: (current.start, current.end)
    )
    for left, right in zip(sorted_operations, sorted_operations[1:]):
        if left.end > right.start:
            return True
    return False


def apply_span_operations(text: str, operations: Sequence[SpanRepairOperation]) -> str:
    """Apply non-overlapping span operations in deterministic order.

    Operations are treated as spans into the original input text. If any spans
    overlap, no changes are applied and the original text is returned.
    """
    ordered = sorted(
        (operation for operation in operations if operation.operation == "replace"),
        key=lambda current: (current.start, current.end),
    )
    if _has_overlapping_spans(ordered):
        return text

    updated = text
    for operation in reversed(ordered):
        if operation.operation != "replace":
            continue
        current_original = updated[operation.start : operation.end]
        if current_original != operation.original_text:
            continue
        updated = (
            updated[: operation.start]
            + operation.replacement_text
            + updated[operation.end :]
        )
    return updated


def suggest_repairs_for_text(
    text: str,
    *,
    allow_smart: bool = False,
    excluded: Optional[set[str]] = None,
    allowlist: Optional[specials.AllowlistConfig] = None,
    context: int = 12,
    name_width: int = 0,
    rules: Sequence[RepairRule] = DEFAULT_REPAIR_RULES,
    decision_store=None,
) -> list[RepairSuggestion]:
    """Extract findings from text and propose conservative repairs.

    This is a non-destructive workflow helper. It only returns proposals and does
    not apply replacements.
    """
    effective_allowlist = (
        allowlist if allowlist is not None else specials.AllowlistConfig()
    )
    findings = specials.iter_special_characters(
        text=text,
        allow_smart=allow_smart,
        excluded=excluded or set(),
        allowlist=effective_allowlist,
        context=context,
        name_width=name_width,
    )
    return suggest_repairs(
        text,
        findings,
        rules=rules,
        decision_store=decision_store,
    )


def suggest_reviewed_repairs_for_text(
    text: str,
    *,
    allow_smart: bool = False,
    excluded: Optional[set[str]] = None,
    allowlist: Optional[specials.AllowlistConfig] = None,
    context: int = 12,
    name_width: int = 0,
    rules: Sequence[RepairRule] = DEFAULT_REPAIR_RULES,
    decision_store=None,
):
    """Return grouped repair suggestions after applying review decisions."""
    from lcats.analysis.corpus import review

    suggestions = suggest_repairs_for_text(
        text,
        allow_smart=allow_smart,
        excluded=excluded,
        allowlist=allowlist,
        context=context,
        name_width=name_width,
        rules=rules,
        decision_store=decision_store,
    )
    return review.apply_review_to_repairs(suggestions, decision_store)


def build_dry_run_report(
    suggestions: Sequence[RepairSuggestion],
    *,
    file_label: str = "",
) -> str:
    """Return a deterministic dry-run report for review/audit."""
    plan_entries = build_dry_run_plan_entries(suggestions)
    lines = []
    for entry in plan_entries:
        prefix = f"{file_label}:" if file_label else ""
        lines.append(
            (
                f"{prefix}{entry.start}-{entry.end}\t"
                f"{entry.rule_id}\t"
                f"confidence={entry.confidence}\t"
                f"before={entry.original_text}\t"
                f"after={entry.replacement_text}\t"
                f"reason={entry.rationale}"
            )
        )
    return "\n".join(lines)


def build_dry_run_plan_entries(
    suggestions: Sequence[RepairSuggestion],
) -> list[RepairPlanEntry]:
    """Convert suggestions into deterministic plan entries for dry-run use."""
    entries = [
        RepairPlanEntry(
            start=suggestion.start,
            end=suggestion.end,
            original_text=suggestion.original_text,
            replacement_text=suggestion.replacement_text,
            rule_id=suggestion.rule_id,
            confidence=suggestion.confidence,
            evidence=suggestion.evidence,
            rationale=suggestion.rationale,
            finding_offset=suggestion.finding_offset,
        )
        for suggestion in suggestions
    ]
    entries.sort(key=lambda entry: (entry.start, entry.end, entry.rule_id))
    return entries


def build_dry_run_jsonl_report(
    suggestions: Sequence[RepairSuggestion],
    *,
    path: str = "",
) -> str:
    """Return deterministic JSONL report for machine parsing."""
    lines = []
    for entry in build_dry_run_plan_entries(suggestions):
        payload = {
            "path": path,
            "start": entry.start,
            "end": entry.end,
            "original_text": entry.original_text,
            "replacement_text": entry.replacement_text,
            "rule_id": entry.rule_id,
            "confidence": entry.confidence,
            "evidence": entry.evidence,
            "rationale": entry.rationale,
            "finding_offset": entry.finding_offset,
        }
        lines.append(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return "\n".join(lines)
