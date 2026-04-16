"""Shared models for corpus analysis."""

from dataclasses import dataclass
from typing import Any, Mapping, Protocol


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
        """Return findings detected in text."""
