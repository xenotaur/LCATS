"""Corpus survey architecture primitives and detector orchestration."""

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Protocol, Sequence
import unicodedata


SMART_ALLOWED = {"–", "—", "‘", "’", "“", "”", "…"}
ASCII_PUNCT = {chr(i) for i in range(32, 127)} - set(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
)


@dataclass(frozen=True)
class Finding:
    """One detector finding with stable, testable structure."""

    kind: str
    severity: str
    span: tuple[int, int]
    message: str
    evidence: Mapping[str, Any]


class Detector(Protocol):
    """Detector interface for corpus survey checks."""

    def run(self, text: str) -> list[Finding]:
        """Return findings detected in `text`."""


class SpecialCharactersDetector:
    """Placeholder detector that reuses existing special-character rules."""

    def __init__(
        self,
        *,
        allow_smart: bool = True,
        excluded_chars: Optional[Sequence[str]] = None,
    ):
        self.allow_smart = allow_smart
        self.excluded_chars = set(excluded_chars or [])

    def _is_allowed(self, ch: str) -> bool:
        if ch.isascii():
            if ch.isalnum() or ch in " \t\r\n" or ch in ASCII_PUNCT:
                return True
        if self.allow_smart and ch in SMART_ALLOWED:
            return True
        return False

    def run(self, text: str) -> list[Finding]:
        findings = []
        for idx, ch in enumerate(text):
            if ch in self.excluded_chars or self._is_allowed(ch):
                continue

            findings.append(
                Finding(
                    kind="special-character",
                    severity="warning",
                    span=(idx, idx + 1),
                    message=f"Unexpected character U+{ord(ch):04X}",
                    evidence={
                        "character": ch,
                        "codepoint": f"U+{ord(ch):04X}",
                        "unicode_name": unicodedata.name(ch, "UNKNOWN"),
                    },
                )
            )
        return findings


def run_detectors(
    text: str, config: Optional[Mapping[str, Any]] = None
) -> list[Finding]:
    """Run configured detectors and return all findings in deterministic order."""
    resolved = dict(config or {})
    detectors = resolved.get("detectors")

    if detectors is None:
        detectors = [SpecialCharactersDetector()]

    findings = []
    for detector in detectors:
        findings.extend(detector.run(text))

    return findings
