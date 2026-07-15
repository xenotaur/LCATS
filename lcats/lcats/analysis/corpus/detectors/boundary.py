"""Boundary contamination detectors."""

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


class StartDetector:
    """Detect likely non-story header content near the story beginning."""

    _AUTHOR_RE = re.compile(r"^by\s+.+", re.IGNORECASE)
    _EDITOR_RE = re.compile(
        r"^\[?(editor'?s? note|note to reader)\]?[:\-\s]", re.IGNORECASE
    )

    def run(self, text: str) -> list[models.Finding]:
        lines = line_offsets(text)
        findings = []

        for line_no, (start, line) in enumerate(lines[:BOUNDARY_WINDOW_LINES], start=1):
            trimmed = line.strip()
            if not trimmed:
                continue

            if self._AUTHOR_RE.match(trimmed):
                findings.append(
                    make_line_finding(
                        kind="start-contamination",
                        severity="warning",
                        line_start=start,
                        line_text=line,
                        message="Likely byline at start of story.",
                        evidence={"line": trimmed, "type": "author-line"},
                    )
                )
                continue

            if self._EDITOR_RE.match(trimmed):
                findings.append(
                    make_line_finding(
                        kind="start-contamination",
                        severity="warning",
                        line_start=start,
                        line_text=line,
                        message="Likely editorial note at start of story.",
                        evidence={"line": trimmed, "type": "editor-note"},
                    )
                )
                continue

            if line_no <= 3 and self._looks_like_title(trimmed):
                findings.append(
                    make_line_finding(
                        kind="start-contamination",
                        severity="warning",
                        line_start=start,
                        line_text=line,
                        message="Likely title heading at story start.",
                        evidence={"line": trimmed, "type": "title-line"},
                    )
                )

        return findings

    @staticmethod
    def _looks_like_title(line: str) -> bool:
        if len(line) < 4 or len(line) > 90:
            return False
        if line.endswith((".", "!", "?", ";", ":")):
            return False
        words = [word for word in re.split(r"\s+", line) if word]
        if len(words) < 2 or len(words) > 12:
            return False
        alpha_words = [
            word for word in words if any(character.isalpha() for character in word)
        ]
        if len(alpha_words) < 2:
            return False
        titleish = sum(word[0].isupper() for word in alpha_words if word[0].isalpha())
        return titleish >= max(2, len(alpha_words) - 1)


class EndDetector:
    """Detect likely non-story footer content near the story end."""

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

            if self._GUTENBERG_RE.search(trimmed):
                findings.append(
                    make_line_finding(
                        kind="end-contamination",
                        severity="warning",
                        line_start=start,
                        line_text=line,
                        message="Likely Gutenberg footer content.",
                        evidence={"line": trimmed, "type": "gutenberg-footer"},
                    )
                )

        return findings
