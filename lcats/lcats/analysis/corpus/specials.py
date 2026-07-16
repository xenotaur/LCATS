"""Special-character extraction helpers for corpus survey workflows."""

import argparse
import json
import pathlib
import unicodedata

from dataclasses import dataclass
from typing import Iterable, Optional

SMART_ALLOWED = {"–", "—", "‘", "’", "“", "”", "…"}
ASCII_PUNCT = {chr(index) for index in range(32, 127)} - set(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
)
TSV_COLUMNS = [
    "codepoint",
    "char",
    "unicode_name",
    "occurrence_index",
    "offset",
    "context",
    "classification",
    "evidence",
]
MOJIBAKE_SEQUENCES = (
    "â€™",
    "â€œ",
    "â€\u009d",
    "â€“",
    "â€”",
    "â€¦",
    # UTF-8 bytes decoded as Mac-Roman upstream; exact sequences only, so a
    # bare mathematical "√" still classifies as review_needed.
    "√©",
    "√®",
    "√±",
    "√º",
    "√∂",
    "√≤",
    "√¶",
)
MOJIBAKE_NEIGHBOR_MARKERS = {"Ã", "Â", "â", "ð", "�"}


@dataclass
class SpecialCharacter:
    """One extracted non-ASCII/suspicious character occurrence."""

    character: str
    codepoint: str
    unicode_name: str
    occurrence_index: int
    offset: int
    context: str
    classification: str
    evidence: str


class AllowlistConfig:
    """Allowlist settings loaded from CLI and optional JSON config."""

    def __init__(self):
        self.allowed_chars = set()
        self.allowed_codepoints = set()
        self.allowed_unicode_names = set()
        self.allowed_categories = set()

    def is_allowed(self, character: str) -> bool:
        if character in self.allowed_chars:
            return True
        if f"U+{ord(character):04X}" in self.allowed_codepoints:
            return True
        if get_unicode_name(character) in self.allowed_unicode_names:
            return True
        if unicodedata.category(character) in self.allowed_categories:
            return True
        return False


def parse_codepoint(text: str) -> str:
    """Parse a codepoint string and return the corresponding character."""
    cleaned = text.strip().upper()
    if cleaned.startswith("U+"):
        cleaned = cleaned[2:]
    try:
        value = int(cleaned, 16)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid codepoint '{text}'. Expected forms like U+00A3 or 00A3."
        ) from exc
    try:
        return chr(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid Unicode scalar value '{text}'."
        ) from exc


def split_csv_items(values: Optional[Iterable[str]]) -> list[str]:
    """Split repeatable comma-separated values into a flat list."""
    items = []
    for value in values or []:
        for item in value.split(","):
            item = item.strip()
            if item:
                items.append(item)
    return items


def build_excluded_set(
    exclude_chars: Optional[Iterable[str]], exclude_codepoints: Optional[Iterable[str]]
) -> set[str]:
    """Build a set of characters to exclude from reporting."""
    excluded = set()

    for item in split_csv_items(exclude_chars):
        for character in item:
            excluded.add(character)

    for item in split_csv_items(exclude_codepoints):
        excluded.add(parse_codepoint(item))

    return excluded


def load_allowlist_config(config_path: str | None) -> AllowlistConfig:
    """Load allowlist config JSON, returning an empty config when unset."""
    config = AllowlistConfig()
    if not config_path:
        return config

    with pathlib.Path(config_path).open("r", encoding="utf-8") as config_file:
        payload = json.load(config_file)

    for value in payload.get("allowed_chars", []):
        for character in value:
            config.allowed_chars.add(character)

    for codepoint in payload.get("allowed_codepoints", []):
        normalized = f"U+{ord(parse_codepoint(codepoint)):04X}"
        config.allowed_codepoints.add(normalized)

    for name in payload.get("allowed_unicode_names", []):
        config.allowed_unicode_names.add(name)

    for category in payload.get("allowed_categories", []):
        config.allowed_categories.add(category)

    return config


def is_allowed(character: str, allow_smart: bool, allowlist: AllowlistConfig) -> bool:
    """Return True when a character is allowed by the configured filters."""
    if character.isascii():
        if character.isalnum() or character in " \t\r\n" or character in ASCII_PUNCT:
            return True
    if allow_smart and character in SMART_ALLOWED:
        return True
    if allowlist.is_allowed(character):
        return True
    return False


def is_flagged(
    character: str,
    allow_smart: bool,
    excluded: set[str],
    allowlist: AllowlistConfig,
) -> bool:
    """Return True when a character should be reported."""
    if character in excluded:
        return False
    return not is_allowed(character, allow_smart, allowlist)


def _is_latin_letter(character: str) -> bool:
    """Return True when character is a letter with a Latin Unicode name."""
    if not unicodedata.category(character).startswith("L"):
        return False
    return "LATIN" in get_unicode_name(character)


def _is_likely_lexical_diacritic(text: str, offset: int, character: str) -> bool:
    """Return True when a Latin diacritic appears in a word-like context."""
    if not _is_latin_letter(character):
        return False
    normalized = unicodedata.normalize("NFD", character)
    if len(normalized) <= 1:
        return False
    left = text[offset - 1] if offset > 0 else ""
    right = text[offset + 1] if offset + 1 < len(text) else ""
    return bool(left.isalpha() or right.isalpha())


def _is_utf8_continuation_char(character: str) -> bool:
    """Return True for a char in the UTF-8 continuation-byte range (U+0080-U+00BF).

    When a multi-byte UTF-8 sequence is mis-decoded as Latin-1, its trailing
    bytes surface as characters in this range (e.g. 'é' -> 'Ã' + '©', '°' ->
    'Â' + '°'). A neighbor marker adjacent to such a char is genuine mojibake;
    a marker followed by ordinary text (an ASCII letter) is a legitimate Latin
    diacritic such as French 'pâle' or the name 'Atlaanât'.
    """
    return len(character) == 1 and 0x80 <= ord(character) <= 0xBF


def _has_mojibake_pattern(text: str, offset: int, character: str) -> tuple[bool, str]:
    """Return mojibake match status and deterministic evidence snippet.

    A bare neighbor marker (Ã/Â/â/ð) is only treated as mojibake when it sits
    next to a UTF-8 continuation-range character, so legitimate diacritics in
    ordinary words are not flagged (the overbroad-exclusion fix for
    WI-RESIDUAL-0019).
    """
    window_start = max(0, offset - 4)
    window_end = min(len(text), offset + 5)
    window = text[window_start:window_end]

    # Exact known corrupted sequences: the Mac-Roman "√" family and the literal
    # smart-punctuation sequences that embed U+20AC.
    for sequence in MOJIBAKE_SEQUENCES:
        if sequence in window:
            return True, sequence

    # The Unicode replacement character is always a decode failure.
    if character == "�":
        return True, character

    following = text[offset + 1] if offset + 1 < len(text) else ""
    preceding = text[offset - 1] if offset > 0 else ""

    # A marker immediately before a continuation-range char is a corrupted
    # multi-byte sequence (Ã©, Â°, â + control); followed by ordinary text it is
    # a legitimate diacritic.
    if character in MOJIBAKE_NEIGHBOR_MARKERS and _is_utf8_continuation_char(following):
        return True, character + following

    # The trailing continuation-range char of that same corrupted sequence.
    if _is_utf8_continuation_char(character) and preceding in MOJIBAKE_NEIGHBOR_MARKERS:
        return True, preceding + character

    return False, ""


def classify_character(text: str, offset: int, character: str) -> tuple[str, str]:
    """Classify one character into likely-good, repairable, or review-needed."""
    unicode_category = unicodedata.category(character)
    unicode_name = get_unicode_name(character)

    has_mojibake, fragment = _has_mojibake_pattern(text, offset, character)
    if has_mojibake:
        return (
            "likely_repairable",
            f"rule=mojibake-pattern; fragment={fragment}; unicode_category={unicode_category}",
        )

    if character in SMART_ALLOWED:
        return (
            "likely_good",
            f"rule=smart-typography; unicode_category={unicode_category}",
        )

    if _is_likely_lexical_diacritic(text, offset, character):
        return (
            "likely_good",
            (
                "rule=lexical-latin-diacritic; "
                f"unicode_name={unicode_name}; normalized={unicodedata.normalize('NFD', character)}"
            ),
        )

    return (
        "review_needed",
        (
            "rule=residual-review; "
            f"unicode_name={unicode_name}; unicode_category={unicode_category}"
        ),
    )


def escape_for_tsv(text: str) -> str:
    """Escape tabs and line breaks so each row remains one-line TSV."""
    return text.replace("\t", "\\t").replace("\n", "\\n").replace("\r", "\\r")


def get_unicode_name(character: str) -> str:
    """Return a Unicode name for a character, or UNKNOWN when unnamed."""
    return unicodedata.name(character, "UNKNOWN")


def truncate_text(text: str, width: int) -> str:
    """Truncate text to a deterministic width using an ellipsis."""
    if width <= 0 or len(text) <= width:
        return text
    if width == 1:
        return "…"
    return text[: width - 1] + "…"


def get_context_snippet(text: str, offset: int, context: int) -> str:
    """Return a left/target/right context snippet around one offset."""
    if context <= 0:
        return ""
    start = max(0, offset - context)
    end = min(len(text), offset + context + 1)
    return text[start:end]


def iter_special_characters(
    text: str,
    allow_smart: bool,
    excluded: set[str],
    allowlist: AllowlistConfig,
    context: int,
    name_width: int,
):
    """Yield extracted special character occurrences for one text input."""
    occurrence_counts: dict[str, int] = {}

    for offset, character in enumerate(text):
        if not is_flagged(character, allow_smart, excluded, allowlist):
            continue

        occurrence_counts[character] = occurrence_counts.get(character, 0) + 1
        classification, evidence = classify_character(text, offset, character)
        yield SpecialCharacter(
            character=character,
            codepoint=f"U+{ord(character):04X}",
            unicode_name=truncate_text(get_unicode_name(character), name_width),
            occurrence_index=occurrence_counts[character],
            offset=offset,
            context=get_context_snippet(text, offset, context),
            classification=classification,
            evidence=evidence,
        )


def special_character_to_tsv_row(result: SpecialCharacter) -> str:
    """Serialize one extracted special character as a stable TSV row."""
    parts = [
        result.codepoint,
        escape_for_tsv(result.character),
        result.unicode_name,
        str(result.occurrence_index),
        str(result.offset),
        escape_for_tsv(result.context),
        result.classification,
        escape_for_tsv(result.evidence),
    ]
    return "\t".join(parts)


def iter_special_character_rows(
    text: str,
    allow_smart: bool,
    excluded: set[str],
    allowlist: AllowlistConfig,
    context: int,
    name_width: int,
    decision_store=None,
):
    """Yield stable TSV rows for each extracted special character."""
    findings = iter_special_characters(
        text=text,
        allow_smart=allow_smart,
        excluded=excluded,
        allowlist=allowlist,
        context=context,
        name_width=name_width,
    )
    if decision_store is not None:
        from lcats.analysis.corpus import review

        findings = review.apply_review_to_specials(findings, decision_store)

    for result in findings:
        yield special_character_to_tsv_row(result)


def build_special_character_report(
    text: str,
    allow_smart: bool,
    excluded: set[str],
    allowlist: AllowlistConfig,
    context: int,
    name_width: int,
    header: bool,
    decision_store=None,
) -> str:
    """Return full TSV report for extracted special characters."""
    lines = []
    if header:
        lines.append("\t".join(TSV_COLUMNS))
    lines.extend(
        iter_special_character_rows(
            text=text,
            allow_smart=allow_smart,
            excluded=excluded,
            allowlist=allowlist,
            context=context,
            name_width=name_width,
            decision_store=decision_store,
        )
    )
    return "\n".join(lines)
