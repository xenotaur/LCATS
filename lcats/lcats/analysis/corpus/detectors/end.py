"""The End boundary contamination detectors."""

import re

from lcats.analysis.corpus import models

BOUNDARY_WINDOW_LINES = 12


def line_offsets(text: str) -> list[tuple[int, str]]:
    """Return (start_index, line_text_without_newline) for each line."""
    offsets = []
    position = 0
    for raw_line in text.splitlines(keepends=True):
        line = raw_line.rstrip("\r\n")
        offsets.append((position, line))
        position += len(raw_line)

    if not offsets and text:
        offsets.append((0, text))
    return offsets


def make_line_finding(
    *,
    kind: str,
    severity: str,
    line_start: int,
    line_text: str,
    message: str,
    evidence: dict[str, str],
) -> models.Finding:
    """Build a finding from one line-based match."""
    return models.Finding(
        kind=kind,
        severity=severity,
        span=(line_start, line_start + len(line_text)),
        message=message,
        evidence=evidence,
    )


class TheEndDetector:
    """Detect likely "The End" footer content near the story end."""

    _GUTENBERG_RE = re.compile(
        r"(project gutenberg|gutenberg (ebook|license)|\*\*\* end of)",
        re.IGNORECASE,
    )

    def run(self, text: str) -> list[models.Finding]:
        lines = line_offsets(text)
        if not lines:
            return []

        findings = []
        start_index = max(0, len(lines) - BOUNDARY_WINDOW_LINES)
        for line_no in range(start_index, len(lines)):
            start, line = lines[line_no]
            trimmed = line.strip()
            if not trimmed:
                continue

            if trimmed.upper() == "THE END":
                findings.append(
                    make_line_finding(
                        kind="end-contamination",
                        severity="warning",
                        line_start=start,
                        line_text=line,
                        message="Likely explicit ending marker.",
                        evidence={"line": trimmed, "type": "the-end"},
                    )
                )
                continue

        return findings
