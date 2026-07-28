"""Unicode and suspicious-character detectors."""

import re
import unicodedata

from typing import Optional, Sequence

from lcats.analysis.corpus import models

SMART_ALLOWED = {"–", "—", "‘", "’", "“", "”", "…"}
ASCII_PUNCT = {chr(index) for index in range(32, 127)} - set(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
)
SAFE_EXCLUDED_CHARS = [
    "£",  # Pound Sign
    "ç",  # Latin Small Letter C with Cedilla
    "é",  # Latin Small Letter E with Acute
    "œ",  # Latin Small Ligature OE
    "æ",  # Latin Small Letter AE
    "á",  # Latin Small Letter A with Acute
    "í",  # Latin Small Letter I with Acute
    "ñ",  # Latin Small Letter N with Tilde
    "ö",  # Latin Small Letter O with Diaeresis
    "ü",  # Latin Small Letter U with Diaeresis
    "è",  # Latin Small Letter E with Grave
    "ë",  # Latin Small Letter E with Diaeresis
    "ï",  # Latin Small Letter I with Diaeresis
    "ô",  # Latin Small Letter O with Circumflex
    "ä",  # Latin Small Letter A with Diaeresis
    "ê",  # Latin Small Letter E with Circumflex
    "À",  # Latin Capital Letter A with Grave
    "Ç",  # Latin Capital Letter C with Cedilla
    "É",  # Latin Capital Letter E with Acute
    "Ê",  # Latin Capital Letter E with Circumflex
    "Î",  # Latin Capital Letter I with Circumflex
    "Ü",  # Latin Capital Letter U with Diaeresis
    "à",  # Latin Small Letter A with Grave
    "ó",  # Latin Small Letter O with Acute
    "ù",  # Latin Small Letter U with Grave
    "û",  # Latin Small Letter U with Circumflex
    "―",  # Horizontal Bar
    "½",  # Vulgar Fraction One Half
    "¼",  # Vulgar Fraction One Quarter
]
RARE_REVIEW_CHARS = [
    "°",  # Degree Sign
    "´",  # Acute Accent
    "×",  # Multiplication Sign
    "ā",  # Latin Small Letter A with Macron
    "ī",  # Latin Small Letter I with Macron
    "ū",  # Latin Small Letter U with Macron
    "Ō",  # Latin Capital Letter O with Macron
    "ō",  # Latin Small Letter O with Macron
]
MOJIBAKE_TRIGGER_CHARS = [
    "Â",  # Latin Capital Letter A with Circumflex (often appears in mojibake sequences)
    "Ã",  # Latin Capital Letter A with Tilde (often appears in mojibake sequences)
    "â",  # Latin Small Letter A with Circumflex (often appears in mojibake sequences)
]
DEFAULT_EXCLUDED_CODEPOINTS = [
    "1F4D6",  # Open Book emoji
    "1F4DC",  # Page Facing Up emoji
    "1F5C2",  # Card Index Dividers emoji
    "270D",  # Writing Hand emoji
    "FE0F",  # Variation Selector-16 (often used to force emoji presentation)
    "202F",  # Narrow No-Break Space
    "00A0",  # No-Break Space
]
DEFAULT_EXCLUDED_CHARS = (
    SAFE_EXCLUDED_CHARS + RARE_REVIEW_CHARS + MOJIBAKE_TRIGGER_CHARS
)


class SpecialCharactersDetector:
    """Classify unusual characters with safe, review, and mojibake buckets."""

    _A_CIRCUMFLEX_MOJIBAKE_RE = re.compile(r"Â(?:[\u00A0-\u00BF]|[^\w\s])")
    _A_TILDE_MOJIBAKE_RE = re.compile(r"Ã[\u00A0-\u00BF]")
    _BROKEN_PUNCT_MOJIBAKE_SEQS = {"â€™", "â€œ", "â€\u009d", "â€“", "â€”", "â€¦"}

    def __init__(
        self,
        *,
        allow_smart: bool = True,
        safe_excluded_chars: Optional[Sequence[str]] = None,
        rare_review_chars: Optional[Sequence[str]] = None,
        mojibake_trigger_chars: Optional[Sequence[str]] = None,
        excluded_chars: Optional[Sequence[str]] = None,
    ):
        self.allow_smart = allow_smart
        legacy_excluded_chars = set(excluded_chars or [])
        self.safe_excluded_chars = (
            set(safe_excluded_chars or []) | legacy_excluded_chars
        )
        self.rare_review_chars = set(rare_review_chars or [])
        self.mojibake_trigger_chars = set(mojibake_trigger_chars or [])

    def _is_allowed(self, character: str) -> bool:
        if character.isascii():
            if (
                character.isalnum()
                or character in " \t\r\n"
                or character in ASCII_PUNCT
            ):
                return True
        if self.allow_smart and character in SMART_ALLOWED:
            return True
        return False

    def _detect_mojibake_sequences(self, text: str) -> list[models.Finding]:
        findings: list[models.Finding] = []
        for pattern_type, pattern in [
            ("A-circumflex-sequence", self._A_CIRCUMFLEX_MOJIBAKE_RE),
            ("A-tilde-sequence", self._A_TILDE_MOJIBAKE_RE),
        ]:
            for match in pattern.finditer(text):
                findings.append(
                    models.Finding(
                        kind="mojibake-sequence",
                        severity="error",
                        span=(match.start(), match.end()),
                        message="Likely mojibake sequence.",
                        evidence={"type": pattern_type, "sequence": match.group(0)},
                    )
                )

        for sequence in self._BROKEN_PUNCT_MOJIBAKE_SEQS:
            start = 0
            while True:
                index = text.find(sequence, start)
                if index == -1:
                    break
                findings.append(
                    models.Finding(
                        kind="mojibake-sequence",
                        severity="error",
                        span=(index, index + len(sequence)),
                        message="Likely mojibake punctuation sequence.",
                        evidence={
                            "type": "broken-punctuation-sequence",
                            "sequence": sequence,
                        },
                    )
                )
                start = index + 1

        findings.sort(key=lambda finding: finding.span)
        return findings

    def run(self, text: str) -> list[models.Finding]:
        findings = self._detect_mojibake_sequences(text)
        mojibake_covered_indexes: set[int] = set()
        for finding in findings:
            for index in range(finding.span[0], finding.span[1]):
                mojibake_covered_indexes.add(index)

        for index, character in enumerate(text):
            if index in mojibake_covered_indexes:
                continue
            if character in self.safe_excluded_chars or self._is_allowed(character):
                continue
            if character in self.rare_review_chars:
                findings.append(
                    models.Finding(
                        kind="rare-review-character",
                        severity="info",
                        span=(index, index + 1),
                        message=f"Uncommon character for review U+{ord(character):04X}",
                        evidence={
                            "character": character,
                            "codepoint": f"U+{ord(character):04X}",
                            "unicode_name": unicodedata.name(character, "UNKNOWN"),
                        },
                    )
                )
                continue
            if character in self.mojibake_trigger_chars:
                continue

            findings.append(
                models.Finding(
                    kind="special-character",
                    severity="warning",
                    span=(index, index + 1),
                    message=f"Unexpected character U+{ord(character):04X}",
                    evidence={
                        "character": character,
                        "codepoint": f"U+{ord(character):04X}",
                        "unicode_name": unicodedata.name(character, "UNKNOWN"),
                    },
                )
            )
        return findings
