"""Experiment-only, metadata-corroborated terminal notice for numeric envelopes.

Apply after the isolated title-matched grammar candidate. This is a proposed source-
adapter rule, not an amendment to the production cleanup API. The caller must bind
source_id to the selected source and metadata_id/titles to that same catalog record.
No fuzzy title matching, author-name rewriting or arbitrary footer removal is used.
"""

import dataclasses
import re

from lcats.gettenberg import cleanup
import terminal_notice_candidate

_NOTICE = re.compile(terminal_notice_candidate.PATTERN, re.IGNORECASE | re.ASCII)


def extend(cleaned, *, source_id, metadata_id, titles):
    """Shorten an already accepted envelope only with exact ID/title corroboration.

    Require canonical positive IDs, an untouched numeric envelope, a whole final
    nonblank physical notice line, catalog-title equality under the cleaner's
    existing case/horizontal-space comparison, and a nonempty author/remainder.
    Author nonemptiness follows the previous rule; no catalog-author equality is
    claimed. Any missing or disagreeing evidence preserves the previous result.
    """
    if (
        type(source_id) is not int
        or source_id <= 0
        or type(metadata_id) is not int
        or metadata_id != source_id
        or not cleaned.changed
        or [d.code for d in cleaned.diagnostics] != ["envelope_removed"]
        or len(cleaned.markers) != 2
    ):
        return cleaned
    opening, closing = cleaned.markers
    if (
        opening.kind != "start"
        or closing.kind != "end"
        or opening.identifier != str(source_id)
        or closing.identifier != str(source_id)
    ):
        return cleaned
    previous = None
    # Reuse the pinned cleaner's physical-line model; never let Unicode separators
    # manufacture extra lines or rewrite the original text while finding offsets.
    for start, end, line, raw in cleanup._lines(cleaned.text):
        if raw.strip():
            previous = (start, end, line, raw.strip(" \t"))
    if previous is None:
        return cleaned
    start, end, line, value = previous
    match = _NOTICE.fullmatch(value)
    if (
        not match
        or not match[2].strip(" \t")
        or cleanup._label(match[1]) not in {cleanup._label(t) for t in titles}
        or not cleaned.text[:start].strip()
    ):
        return cleaned
    marker = cleanup.CleanupMarker(
        "end_notice",
        cleaned.content_start + start,
        cleaned.content_start + end,
        opening.line + line,
        match[1].strip(" \t"),
        closing.style,
    )
    return dataclasses.replace(
        cleaned,
        content_end=marker.start,
        markers=(opening, marker, closing),
        diagnostics=cleaned.diagnostics
        + (
            cleanup.CleanupDiagnostic(
                "numeric_notice_removed",
                "Terminal notice title matches metadata bound to numeric envelope ID",
                marker.line,
            ),
        ),
    )
