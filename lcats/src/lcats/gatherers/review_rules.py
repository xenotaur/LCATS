"""Propose narrowly qualified boundary edits without recording or publishing them.

Rules are opt-in review aids, not default extraction policy. Every result binds a
validated candidate and records exact removed text. A match proves only the stated
transformation; the caller must separately reconcile historical differences and
explicitly record any approval. Unknown editorial material stays unresolved.
"""

import re

from lcats.gatherers import candidate_review
from lcats.gatherers import parser
from lcats.gatherers import readiness

BOUNDARY_NOTICE_RULE = "delimited-publication-notice-v1"
_PARAGRAPH = re.compile(r"\S(?:.*?\S)?(?=\n[ \t]*\n|\Z)", re.DOTALL)
# These are complete publication names, not an arbitrary wildcard before a date.
# An unfamiliar spelling/issue format is an exception, never a reason to broaden
# the pattern at runtime. Whitespace folding is for recognition only.
_PUBLICATIONS = (
    "Planet Stories",
    "Worlds of If Science Fiction",
    "Galaxy Science Fiction",
    "Galaxy Magazine",
    "Amazing Stories",
    "Weird Tales",
    "Infinity",
    "Fantastic Universe",
    "Comet",
    "If Worlds of Science Fiction",
    "Astounding Science-Fiction",
    "Infinity Science Fiction",
    "Science Fiction Quarterly",
    "Fantastic",
    "Startling Stories",
    "Astounding Science Fiction",
    "Imagination Stories of Science and Fantasy",
    "Galaxy",
    "Fantastic Adventures",
)
_MONTH = (
    "January|February|March|April|May|June|July|August|September|October|"
    "November|December|Spring|Summer|Fall|Winter"
)
_NOTICE = re.compile(
    r"\[Transcriber(?:['’]s|s)? Note: This etext was produced from (?:"
    + "|".join(re.escape(name) for name in _PUBLICATIONS)
    + r"),? (?:"
    + _MONTH
    + r") 19[0-9]{2}\. Extensive research did not uncover any evidence that "
    r"the U\.S\. copyright on this publication was renewed\.\]",
    re.IGNORECASE,
)
# Readiness deliberately has boundary-limited detectors. A batch rule must not
# convert a remaining interior caption/sidenote into an implicitly reviewed item.
_RETAINED_LABEL = re.compile(
    r"\[(?:illustration|sidenote|transcriber|editor)\b|"
    r"^\s*(?:illustrated by|transcriber['’]?s? note|editor['’]?s? note)\b",
    re.IGNORECASE | re.MULTILINE,
)


def publication_notice(text):
    """Recognize one complete bracketed notice, never an open-ended note section."""
    return len(text) <= 1000 and _NOTICE.fullmatch(" ".join(text.split())) is not None


def _assessment(body, metadata):
    """Recompute structural/readiness evidence on the complete exact text."""
    arguments = {key: metadata[key] for key in ("titles", "authors", "aliases")}
    chapters = parser.assess_chapters(body, **arguments)
    return chapters, readiness.assess(body, chapters, **arguments)


def evaluate_boundary_notice(path):
    """Return a source-bound proposal for a saved unresolved candidate.

    Only complete matching first/last paragraphs may be removed. Interior text,
    typography and separators remain byte-for-byte identical in the contiguous
    selected substring. Reassessment must be ready and known retained labels must
    be absent before this rule can support approval. The result never writes a
    disposition, changes gathering defaults, or claims a complete literary review.

    Args:
        path: Content-addressed candidate file, checked by the normal loader.

    Returns:
        JSON-compatible evidence with applicability, exact selection/removals,
        blockers and identity bindings. Nonmatches have no selected span.

    Raises:
        ValueError: The artifact is malformed, stale or its recorded assessment
            disagrees with assessment recomputed under the current policy.
    """
    record = candidate_review.load_candidate(path)
    report = record["report"]
    body, metadata = report["body"], report["metadata"]
    chapters, assessment = _assessment(body, metadata)
    evidence = report["provenance"]["publication_readiness"]
    if (
        chapters != report["provenance"]["chapter_assessment"]
        or readiness.identity(assessment.to_dict()) != evidence["assessment_sha256"]
    ):
        raise ValueError("candidate assessment differs from current rule context")
    result = {
        "rule": BOUNDARY_NOTICE_RULE,
        "gutenberg_id": report["gutenberg_id"],
        "candidate_record_sha256": readiness.identity(record),
        **{
            key: evidence[key]
            for key in (
                "source_identity_sha256",
                "candidate_sha256",
                "assessment_sha256",
            )
        },
        "matched": False,
        "approval_eligible": False,
        "selected_span": None,
        "selected_sha256": None,
        "removed": [],
        "blockers": [],
    }
    # Scan without exterior trailing whitespace so the final prose paragraph is
    # never missed by the end-of-string alternative. Preserve that whitespace
    # in the selected substring unless a trailing notice is actually removed.
    paragraphs = list(_PARAGRAPH.finditer(body.rstrip()))
    left, right = 0, len(paragraphs)
    # At most one notice at each boundary. Duplicate runs are left for review.
    if paragraphs and publication_notice(paragraphs[0].group()):
        left += 1
    if right > left and publication_notice(paragraphs[-1].group()):
        right -= 1
    if left == 0 and right == len(paragraphs):
        result["blockers"] = ["no_matching_boundary_notice"]
        return result
    result["matched"] = True
    if left >= right:
        result["blockers"] = ["no_retained_text"]
        return result
    start = paragraphs[left].start() if left else 0
    end = paragraphs[right - 1].end() if right < len(paragraphs) else len(body)
    selected = body[start:end]
    removed = []
    for lower, upper in ((0, start), (end, len(body))):
        if lower != upper:
            # Defense in depth: a parsing error must never turn arbitrary prose
            # into discarded boundary material. Check the whole removed piece.
            if not publication_notice(body[lower:upper].strip()):
                raise ValueError("removed span contains unrecognized text")
            removed.append(
                {
                    "span": [lower, upper],
                    "text": body[lower:upper],
                    "sha256": readiness.text_sha256(body[lower:upper]),
                }
            )
    selected_chapters, selected_assessment = _assessment(selected, metadata)
    blockers = []
    if selected_assessment.status != "ready":
        blockers.append("selected_" + selected_assessment.status)
    if _RETAINED_LABEL.search(selected):
        blockers.append("retained_editorial_label")
    result.update(
        selected_span=[start, end],
        selected_sha256=readiness.text_sha256(selected),
        removed=removed,
        selected_chapter_assessment=selected_chapters,
        selected_assessment=selected_assessment.to_dict(),
        blockers=blockers,
        approval_eligible=not blockers,
    )
    return result


ORDERED_NOTICE_RULE = "ordered-publication-notice-v1"


def evaluate_publication_notices(path):
    """Propose exact removal of complete notice paragraphs anywhere in a candidate.

    Recognition uses the unchanged finite grammar from the boundary rule. Each
    omission includes the notice and its following separator (or trailing white
    space), leaving the preceding separator intact. All other characters stay in
    source order. No opening prose is classified as a blurb by its position.

    This establishes transformation evidence only. Surviving findings, unexplained
    historical differences and prior dispositions must be considered separately;
    neither a match nor mechanical readiness authorizes recording/publication.
    At most 256 notices are proposed; larger inputs remain unresolved.
    """
    record = candidate_review.load_candidate(path)
    report = record["report"]
    body, metadata = report["body"], report["metadata"]
    chapters, assessment = _assessment(body, metadata)
    evidence = report["provenance"]["publication_readiness"]
    if (
        chapters != report["provenance"]["chapter_assessment"]
        or readiness.identity(assessment.to_dict()) != evidence["assessment_sha256"]
    ):
        raise ValueError("candidate assessment differs from current rule context")
    result = {
        "rule": ORDERED_NOTICE_RULE,
        "gutenberg_id": report["gutenberg_id"],
        "candidate_record_sha256": readiness.identity(record),
        **{
            key: evidence[key]
            for key in (
                "source_identity_sha256",
                "candidate_sha256",
                "assessment_sha256",
            )
        },
        "matched": False,
        "transformation_qualified": False,
        "selected_readiness_eligible": False,
        "publication_approved": False,
        "selected_spans": None,
        "selected_sha256": None,
        "omissions": [],
        "removed": [],
        "blockers": [],
    }
    paragraphs = list(_PARAGRAPH.finditer(body.rstrip()))
    omissions = []
    for i, paragraph in enumerate(paragraphs):
        if not publication_notice(paragraph.group()):
            continue
        start = paragraph.start() if i else 0
        end = paragraphs[i + 1].start() if i + 1 < len(paragraphs) else len(body)
        # The exact removed substring must contain nothing but a complete notice
        # and separators, even if paragraph segmentation changes in the future.
        if not publication_notice(body[start:end].strip()):
            raise ValueError("removed span contains unrecognized text")
        omissions.append(
            {
                "start": start,
                "end": end,
                "kind": "publication_notice",
                "reason": "Complete delimited publication notice, with following separator.",
                "evidence": ORDERED_NOTICE_RULE
                + "; full paragraph matches finite publication/date grammar",
            }
        )
    if not omissions:
        result["blockers"] = ["no_matching_publication_notice"]
        return result
    result["matched"] = True
    if len(omissions) > 256:
        result["blockers"] = ["too_many_notices"]
        return result
    if sum(o["end"] - o["start"] for o in omissions) == len(body):
        result["blockers"] = ["no_retained_text"]
        return result
    # Use the same strict partition validator as publication, without saving or
    # exposing an approval. The returned packet is explicitly a proposal only.
    selection = readiness.OrderedReviewDecision.for_report(
        report,
        omissions=omissions,
        reviewer="Rule proposal only",
        rationale="Transformation validation; no publication approval.",
    )
    selected = selection.reconstruct(body)
    selected_chapters, selected_assessment = _assessment(selected, metadata)
    blockers = []
    if selected_assessment.status != "ready":
        blockers.append("selected_" + selected_assessment.status)
    if _RETAINED_LABEL.search(selected):
        blockers.append("retained_editorial_label")
    result.update(
        transformation_qualified=True,
        selected_spans=[list(v) for v in selection.selected_spans],
        selected_sha256=selection.selected_sha256,
        omissions=omissions,
        removed=[
            {
                "span": [v.start, v.end],
                "text": body[v.start : v.end],
                "sha256": v.sha256,
            }
            for v in selection.omitted_spans
        ],
        selected_chapter_assessment=selected_chapters,
        selected_assessment=selected_assessment.to_dict(),
        selected_readiness_eligible=not blockers,
        blockers=blockers,
    )
    return result
