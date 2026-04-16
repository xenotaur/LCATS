"""Structural artifact detectors."""

import re

from lcats.analysis.corpus import models
from lcats.analysis.corpus.detectors import boundary

STRUCTURAL_WINDOW_LINES = 40


class ChapterHeadingDetector:
    """Detect chapter-style heading lines embedded in story text."""

    _CHAPTER_RE = re.compile(
        r"^(chapter|book|part)\s+([ivxlcdm]+|\d+)([\s:.-]+.*)?$", re.IGNORECASE
    )

    def run(self, text: str) -> list[models.Finding]:
        findings = []
        for line_no, (start, line) in enumerate(boundary.line_offsets(text), start=1):
            if line_no > STRUCTURAL_WINDOW_LINES:
                break
            trimmed = line.strip()
            if not trimmed or len(trimmed) > 90:
                continue
            if self._CHAPTER_RE.match(trimmed):
                findings.append(
                    boundary.make_line_finding(
                        kind="structural-artifact",
                        severity="warning",
                        line_start=start,
                        line_text=line,
                        message="Likely chapter heading.",
                        evidence={"line": trimmed, "type": "chapter-heading"},
                    )
                )
        return findings


class TocRemnantsDetector:
    """Detect table-of-contents remnants such as dotted leader lines."""

    _CONTENTS_HEADER_RE = re.compile(r"^(table of contents|contents)$", re.IGNORECASE)
    _TOC_ENTRY_RE = re.compile(
        r"^([ivxlcdm\d]+\.?\s+)?[A-Za-z][A-Za-z ,.'\-]+\.{2,}\s*\d+\s*$"
    )

    def run(self, text: str) -> list[models.Finding]:
        lines = boundary.line_offsets(text)[:STRUCTURAL_WINDOW_LINES]
        findings = []
        entry_count = 0

        for start, line in lines:
            trimmed = line.strip()
            if not trimmed:
                continue

            if self._CONTENTS_HEADER_RE.match(trimmed):
                findings.append(
                    boundary.make_line_finding(
                        kind="structural-artifact",
                        severity="warning",
                        line_start=start,
                        line_text=line,
                        message="Likely table-of-contents heading.",
                        evidence={"line": trimmed, "type": "toc-heading"},
                    )
                )
                continue

            if self._TOC_ENTRY_RE.match(trimmed):
                entry_count += 1
                findings.append(
                    boundary.make_line_finding(
                        kind="structural-artifact",
                        severity="warning",
                        line_start=start,
                        line_text=line,
                        message="Likely table-of-contents entry.",
                        evidence={"line": trimmed, "type": "toc-entry"},
                    )
                )

        if entry_count < 2:
            findings = [
                finding
                for finding in findings
                if finding.evidence.get("type") != "toc-entry"
            ]

        return findings


class SectionBreakDetector:
    """Detect standalone section-break ornament lines."""

    _SECTION_RE = re.compile(r"^(\*\s*){3,}$|^(\-\s*){3,}$|^~{3,}$|^\*\s\*\s\*$")

    def run(self, text: str) -> list[models.Finding]:
        findings = []
        for start, line in boundary.line_offsets(text):
            trimmed = line.strip()
            if not trimmed:
                continue
            if self._SECTION_RE.match(trimmed):
                findings.append(
                    boundary.make_line_finding(
                        kind="structural-artifact",
                        severity="warning",
                        line_start=start,
                        line_text=line,
                        message="Likely section break marker.",
                        evidence={"line": trimmed, "type": "section-break"},
                    )
                )
        return findings


class IllustrationCaptionDetector:
    """Detect illustration caption lines that are likely non-story artifacts."""

    _CAPTION_RE = re.compile(
        r"^(\[?illustration\]?[:.]?|figure\s+\d+[:.]|fig\.\s*\d+[:.])",
        re.IGNORECASE,
    )

    def run(self, text: str) -> list[models.Finding]:
        findings = []
        for start, line in boundary.line_offsets(text):
            trimmed = line.strip()
            if not trimmed or len(trimmed) > 120:
                continue
            if self._CAPTION_RE.match(trimmed):
                findings.append(
                    boundary.make_line_finding(
                        kind="structural-artifact",
                        severity="warning",
                        line_start=start,
                        line_text=line,
                        message="Likely illustration caption.",
                        evidence={"line": trimmed, "type": "illustration-caption"},
                    )
                )
        return findings
