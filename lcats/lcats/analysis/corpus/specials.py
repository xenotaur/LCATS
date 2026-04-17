"""Special-character extraction helpers for corpus survey workflows."""

import argparse
import json
import pathlib
import re
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
MOJIBAKE_RE = re.compile(r"(?:Ã.|Â.|â.|ð.|�)")


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


def classify_character(text: str, offset: int, character: str) -> tuple[str, str]:
    """Classify one character with a compact evidence string."""
    if character in SMART_ALLOWED:
        return ("valid-typography", "common typographic punctuation")

    window_start = max(0, offset - 2)
    window_end = min(len(text), offset + 3)
    window = text[window_start:window_end]
    match = MOJIBAKE_RE.search(window)
    if match:
        return ("mojibake-pattern", f"matched mojibake fragment '{match.group(0)}'")

    return (
        "suspicious-unicode",
        (
            "unicode_category="
            f"{unicodedata.category(character)}; non-ascii outside allowlist"
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
):
    """Yield stable TSV rows for each extracted special character."""
    for result in iter_special_characters(
        text=text,
        allow_smart=allow_smart,
        excluded=excluded,
        allowlist=allowlist,
        context=context,
        name_width=name_width,
    ):
        yield special_character_to_tsv_row(result)


def build_special_character_report(
    text: str,
    allow_smart: bool,
    excluded: set[str],
    allowlist: AllowlistConfig,
    context: int,
    name_width: int,
    header: bool,
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
        )
    )
    return "\n".join(lines)
