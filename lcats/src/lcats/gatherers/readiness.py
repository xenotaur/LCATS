"""Explain publication readiness without deleting candidate text.

A ready result means no unresolved cues under this versioned policy, not proof
that arbitrary prose is a story. Editorial and ambiguous structural findings
require an explicit source-bound review decision before publication.
"""

import dataclasses
import hashlib
import json
import pathlib
import re

from lcats.analysis.corpus import models
from lcats.gatherers import story_body

POLICY_VERSION = "publication-readiness-v1"
_PARAGRAPH = re.compile(r"\S(?:.*?\S)?(?=\n[ \t]*\n|\Z)", re.DOTALL)
_NOTE = re.compile(
    r"^\[?(?:transcriber['’]?s? notes?|editor['’]?s? notes?|note to (?:the )?reader)"
    r"(?: and errata)?(?:\s*[:\].—-]|\s*$)",
    re.IGNORECASE,
)
_PUBLICATION = re.compile(
    r"^(?:transcribed from\b|copyright\b|all rights reserved\b|published by\b|printed (?:by|in)\b|"
    r"(?:first|originally) published\b|(?:this (?:etext|e-text|ebook|story) was )?"
    r"(?:produced|published) (?:by|in|from)\b|"
    r"(?:this (?:etext|e-text|ebook) (?:was|is) )?produced from\b)",
    re.IGNORECASE,
)
_ADVERTISEMENT = re.compile(
    r"^(?:advertisements?|author of\b|other books by\b|books by\b|by the same author\b|"
    r"also by\b|price[, :]|for sale by\b)",
    re.IGNORECASE,
)
_NUMBERED = re.compile(
    r"(?:(?:chapter|chap\.|part)\s+)?"
    r"(?P<number>[ivxlcdm]+|[0-9]+|one|two|three|four|five|six|seven|eight|nine|ten)\.?",
    re.IGNORECASE,
)
_SHA256 = re.compile(r"[0-9a-f]{64}")


def text_sha256(text):
    """Identify exact UTF-8 text; offsets still count Unicode characters."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def identity(value):
    """Hash canonical JSON for source context, assessment and decision identities."""
    return text_sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    )


@dataclasses.dataclass(frozen=True, slots=True)
class Assessment:
    """A pure result; findings use offsets into the unmodified candidate body."""

    status: str
    findings: tuple[models.Finding, ...] = ()
    exclusion: str | None = None
    policy: str = POLICY_VERSION

    def to_dict(self):
        """Return a JSON-compatible report with an explicit offset basis."""
        return {
            "policy": self.policy,
            "status": self.status,
            "exclusion": self.exclusion,
            "offset_basis": "candidate_body_unicode_characters",
            "findings": [
                {**dataclasses.asdict(f), "span": list(f.span)} for f in self.findings
            ],
        }


def assess(body, chapter_assessment, *, titles=(), authors=(), aliases=()):
    """Classify candidate readiness, preserving all text and explaining uncertainty.

    Args:
        body: The exact candidate before normalization or reviewed selection.
        chapter_assessment: Evidence from parser.assess_chapters for this body.
        titles: Catalog title values.
        authors: Catalog author values.
        aliases: Catalog author aliases.

    Returns:
        Assessment with ready, needs_review or ineligible status. Standalone
        notes are reviewed even in a long body; narrative mentions of notes are
        not sufficient. Structural exclusions require corroboration beyond the
        old all-caps and numbered-prefix heuristic.
    """
    paragraphs = list(_PARAGRAPH.finditer(body))
    findings = []

    def finding(kind, match, message):
        findings.append(
            models.Finding(
                kind=kind,
                severity="warning",
                span=(match.start(), match.end()),
                message=message,
                evidence={"text": match.group()[:240]},
            )
        )

    for index, match in enumerate(paragraphs):
        value = match.group().strip()
        first_line = value.splitlines()[0].strip(" *_")
        boundary = index < 10 or index >= len(paragraphs) - 5
        # ASCII frames are presentation, not a reason to miss an explicit note.
        # Match a label at the start of a physical line; never search arbitrary
        # narrative substrings or delete the surrounding paragraph.
        note_lines = [line.strip(" |*_") for line in value.splitlines()]
        if any(_NOTE.match(line) for line in note_lines):
            finding(
                "editorial_note", match, "An editorial note remains in the candidate."
            )
        elif boundary and _PUBLICATION.match(first_line):
            finding(
                "publication_metadata",
                match,
                "Publication/production information remains near a boundary.",
            )
        elif boundary and _ADVERTISEMENT.match(first_line):
            finding(
                "advertisement",
                match,
                "Possible advertisement or list of other works remains.",
            )
        elif boundary and re.match(
            r"\[Illustration(?:\s*[:\]])", first_line, re.IGNORECASE
        ):
            finding(
                "illustration_label",
                match,
                "A retained illustration label needs boundary review.",
            )
        elif boundary and re.match(
            r"(?:end of (?:the )?)?project gutenberg\b", first_line, re.IGNORECASE
        ):
            finding(
                "retained_gutenberg_notice",
                match,
                "An unremoved Gutenberg notice needs review.",
            )
        elif index < 10 and story_body.is_metadata_heading(
            value, titles, authors, aliases
        ):
            finding(
                "retained_metadata_heading",
                match,
                "A book heading remains after the opening-prefix boundary.",
            )
        elif (
            index == 0
            and len(value.split()) <= 12
            and not value.endswith((".", "!", "?", ";"))
            and not _NUMBERED.fullmatch(value)
            and first_line.casefold().rstrip(".:")
            not in {"contents", "table of contents"}
        ):
            # A heading-like opening is uncertain, not automatically disposable.
            # Ordinary prose with punctuation and wrapped sentences stays usable.
            finding(
                "opening_label",
                match,
                "A short opening without sentence punctuation needs review.",
            )

    # Numbered advertisements can look like sections. Require multiple distinct
    # whole-paragraph headings, and do not assert structure over editorial cues.
    numbered = set()
    text_array = body.split("\n\n")
    for marker in chapter_assessment["explicit_markers"]:
        if marker["kind"] == "numbered_section":
            match = _NUMBERED.fullmatch(text_array[marker["paragraph"]].strip())
            if match:
                numbered.add(match["number"].casefold())
    contents = any(
        m["kind"] == "contents_list" for m in chapter_assessment["explicit_markers"]
    )
    if contents or (len(numbered) >= 2 and not findings):
        return Assessment("ineligible", exclusion="divided_work")
    if chapter_assessment["chaptered"]:
        # Retain the heuristic as evidence; weak capitals, a bare contents label,
        # and numbered prefixes may also be signs, advertisements or prose.
        indexes = sorted(
            set(chapter_assessment["possible_title_paragraphs"])
            | {m["paragraph"] for m in chapter_assessment["explicit_markers"]}
        )
        starts = []
        position = 0
        for paragraph in text_array:
            starts.append(position)
            position += len(paragraph) + 2
        for index in indexes:
            paragraph = text_array[index]
            findings.append(
                models.Finding(
                    kind="ambiguous_structure",
                    severity="warning",
                    span=(starts[index], starts[index] + len(paragraph)),
                    message="Chapter-like evidence requires review before collection eligibility is decided.",
                    evidence={"paragraph": index, "text": paragraph[:240]},
                )
            )
    if len(text_array) <= 10:
        return Assessment("ineligible", tuple(findings), "too_short")
    return Assessment("needs_review" if findings else "ready", tuple(findings))


@dataclasses.dataclass(frozen=True, slots=True)
class ReviewDecision:
    """Explicit approval of one contiguous span under one exact assessment.

    Reviewer/rationale are attribution, not authenticated human signatures. A
    decision is never inferred from network consent, a filename, or an ebook ID.
    """

    gutenberg_id: int
    source_identity_sha256: str
    candidate_sha256: str
    assessment_sha256: str
    selected_start: int
    selected_end: int
    selected_sha256: str
    reviewer: str
    rationale: str
    schema_version: int = 1

    def __post_init__(self):
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ValueError("unsupported review decision schema_version")
        if type(self.gutenberg_id) is not int or self.gutenberg_id <= 0:
            raise ValueError("review decision requires a positive Gutenberg ID")
        for value in (
            self.source_identity_sha256,
            self.candidate_sha256,
            self.assessment_sha256,
            self.selected_sha256,
        ):
            if not isinstance(value, str) or not _SHA256.fullmatch(value):
                raise ValueError("review decision requires lowercase SHA256 identities")
        if any(
            type(value) is not int for value in (self.selected_start, self.selected_end)
        ):
            raise ValueError(
                "review decision span must contain integer character offsets"
            )
        if not 0 <= self.selected_start < self.selected_end:
            raise ValueError("review decision requires a nonempty forward span")
        if any(
            not isinstance(v, str) or not v.strip()
            for v in (self.reviewer, self.rationale)
        ):
            raise ValueError("review decision requires reviewer and rationale")

    @classmethod
    def for_report(cls, report, *, start, end, reviewer, rationale):
        """Construct an explicit decision after the caller has reviewed a report.

        No approval is inferred: the caller supplies the selected span and
        reviewer/rationale. This convenience method copies the report's anchors;
        inspection will independently revalidate them against current sources.
        """
        if report.get("status") not in {"ready", "needs_review"}:
            raise ValueError(
                "only eligible candidate reports can receive a review decision"
            )
        candidate = report["body"]
        if (
            type(start) is not int
            or type(end) is not int
            or not 0 <= start < end <= len(candidate)
        ):
            raise ValueError(
                "review selection must be a nonempty candidate character span"
            )
        evidence = report["provenance"]["publication_readiness"]
        return cls(
            gutenberg_id=report["gutenberg_id"],
            source_identity_sha256=evidence["source_identity_sha256"],
            candidate_sha256=evidence["candidate_sha256"],
            assessment_sha256=evidence["assessment_sha256"],
            selected_start=start,
            selected_end=end,
            selected_sha256=text_sha256(candidate[start:end]),
            reviewer=reviewer,
            rationale=rationale,
        )

    def select(self, *, gutenberg_id, source_identity_sha256, candidate, assessment):
        """Validate all anchors and return the unchanged selected substring."""
        if (
            self.gutenberg_id != gutenberg_id
            or self.source_identity_sha256 != source_identity_sha256
            or self.candidate_sha256 != text_sha256(candidate)
            or self.assessment_sha256 != identity(assessment.to_dict())
        ):
            raise ValueError(
                "stale review decision: source, candidate or assessment identity changed"
            )
        if self.selected_end > len(candidate):
            raise ValueError("review decision span exceeds candidate")
        selected = candidate[self.selected_start : self.selected_end]
        if text_sha256(selected) != self.selected_sha256:
            raise ValueError("review decision selected text identity changed")
        return selected


def load_decisions(path):
    """Load a strict JSON list of decisions; reject duplicates and malformed files.

    Limit files to 8 MiB and 10,000 decisions. Unknown keys and duplicate JSON
    object keys are errors, so a typo cannot silently erase an approval anchor.
    """

    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate review field: {key}")
            result[key] = value
        return result

    with pathlib.Path(path).open("rb") as stream:
        raw = stream.read(8 * 1024**2 + 1)
    if len(raw) > 8 * 1024**2:
        raise ValueError("review decisions exceed 8 MiB")
    values = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object)
    if not isinstance(values, list) or len(values) > 10000:
        raise ValueError("review decisions must be a list of at most 10000 entries")
    result = {}
    for value in values:
        if not isinstance(value, dict):
            raise ValueError("each review decision must be an object")
        try:
            decision = ReviewDecision(**value)
        except TypeError as exc:
            raise ValueError(f"invalid review decision fields: {exc}") from exc
        if decision.gutenberg_id in result:
            raise ValueError(f"duplicate review decision for {decision.gutenberg_id}")
        result[decision.gutenberg_id] = decision
    return result
