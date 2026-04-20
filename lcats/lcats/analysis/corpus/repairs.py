"""Conservative repair proposal helpers for special-character findings."""

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence

from lcats.analysis.corpus import specials


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


DEFAULT_REPAIR_RULES = (
    RepairRule(
        rule_id="mojibake-right-single-quote",
        source_text="â€™",
        replacement_text="’",
        description="Broken UTF-8 right single quote sequence.",
    ),
    RepairRule(
        rule_id="mojibake-left-double-quote",
        source_text="â€œ",
        replacement_text="“",
        description="Broken UTF-8 left double quote sequence.",
    ),
    RepairRule(
        rule_id="mojibake-right-double-quote",
        source_text="â€\u009d",
        replacement_text="”",
        description="Broken UTF-8 right double quote sequence.",
    ),
    RepairRule(
        rule_id="mojibake-en-dash",
        source_text="â€“",
        replacement_text="–",
        description="Broken UTF-8 en dash sequence.",
    ),
    RepairRule(
        rule_id="mojibake-em-dash",
        source_text="â€”",
        replacement_text="—",
        description="Broken UTF-8 em dash sequence.",
    ),
    RepairRule(
        rule_id="mojibake-ellipsis",
        source_text="â€¦",
        replacement_text="…",
        description="Broken UTF-8 ellipsis sequence.",
    ),
)


def _rule_map(rules: Sequence[RepairRule]) -> dict[str, RepairRule]:
    return {rule.source_text: rule for rule in rules}


def _extract_evidence_fragment(evidence: str) -> str:
    """Return fragment value from semicolon-delimited evidence string."""
    for part in evidence.split(";"):
        segment = part.strip()
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

    for finding in findings:
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
    """Apply suggestions in reverse order when original spans still match."""
    updated = text
    for suggestion in sorted(
        suggestions, key=lambda current: (current.start, current.end), reverse=True
    ):
        current_original = updated[suggestion.start : suggestion.end]
        if current_original != suggestion.original_text:
            continue
        updated = (
            updated[: suggestion.start]
            + suggestion.replacement_text
            + updated[suggestion.end :]
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
    return suggest_repairs(text, findings, rules=rules)


def build_dry_run_report(
    suggestions: Sequence[RepairSuggestion],
    *,
    file_label: str = "",
) -> str:
    """Return a deterministic dry-run report for review/audit."""
    lines = []
    for suggestion in suggestions:
        prefix = f"{file_label}:" if file_label else ""
        lines.append(
            (
                f"{prefix}{suggestion.start}-{suggestion.end}\t"
                f"{suggestion.rule_id}\t"
                f"confidence={suggestion.confidence}\t"
                f"before={suggestion.original_text}\t"
                f"after={suggestion.replacement_text}\t"
                f"reason={suggestion.rationale}"
            )
        )
    return "\n".join(lines)
