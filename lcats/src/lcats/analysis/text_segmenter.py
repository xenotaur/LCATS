"""Functionality to index story text for robust segment alignment and auditing."""

import re
from typing import Any, Dict, List, Tuple


from lcats import utils


def canonicalize_text(s: str) -> str:
    """Canonicalize newlines to \n and trim trailing whitespace."""
    return s.replace("\r\n", "\n").replace("\r", "\n")


def _effective_paragraph_splitter(story_text: str, splitter: str) -> str:
    """Return splitter, or a single-newline fallback if story_text has no
    blank-line paragraph breaks at all.

    Some Gutenberg-sourced story text uses single-newline paragraph
    formatting with no blank lines. Splitting that on a literal blank
    line collapses the whole document into one giant "paragraph," which
    forces any downstream anchor-based alignment search across the
    entire document instead of a tight local range -- confirmed to
    produce silently wrong, overlapping segment offsets on real
    corpora/london stories (WI-SEGMENT-0059, WI-ANNOTATE-0054). Only
    applies when splitter itself contains a newline and genuinely does
    not occur in story_text; a caller-supplied non-newline splitter is
    respected unchanged.
    """
    if "\n" in splitter and splitter not in story_text and "\n" in story_text:
        return "\n"
    return splitter


def build_paragraph_index(
    story_text: str, splitter: str = "\n\n"
) -> Tuple[List[str], List[Tuple[int, int]]]:
    """Split story_text into paragraphs by splitter, returning (parts, spans).

    Each span is a (start, end) tuple of absolute character indices in story_text.
    See _effective_paragraph_splitter for the single-newline fallback this
    applies when story_text has no blank-line breaks at all.

    Args:
        story_text: The full text to split.
        splitter: The string that delimits paragraphs (default: double newline).
    Returns:
        A tuple (parts, spans):
          - parts: List of paragraph strings.
          - spans: List of (start, end) tuples giving absolute character indices.
    """
    effective_splitter = _effective_paragraph_splitter(story_text, splitter)
    parts: List[str] = []
    spans: List[Tuple[int, int]] = []
    i = 0
    for chunk in story_text.split(effective_splitter):
        j = story_text.find(chunk, i)
        if j == -1:
            j = i
        k = j + len(chunk)
        parts.append(chunk)
        spans.append((j, k))
        i = k + len(effective_splitter)
    return parts, spans


def add_paragraph_markers(paragraphs: List[str], delimiter: str = "\n\n") -> str:
    """Return text with [P0001], [P0002], ... markers prefixed to each paragraph.

    Args:
        paragraphs: List of paragraph strings.
        delimiter: String to place between paragraphs (default: double newline).
    Returns:
        The combined text with paragraph markers.
    """
    return "".join(
        f"[P{idx+1:04d}] " + p + (delimiter if idx < len(paragraphs) - 1 else "")
        for idx, p in enumerate(paragraphs)
    )


# Matches the marker format add_paragraph_markers emits
# (f"[P{idx+1:04d}] ") -- :04d is a MINIMUM width, not an exact one, so a
# document with 10,000+ paragraphs produces a 5+-digit marker like
# "[P10000]" (review finding, PR #324); \d{4,} (four or more digits)
# matches that while still excluding a looser \d+, which would also
# strip real story content that merely resembles a marker (e.g. a
# citation like "[P045]", 3 digits) (WI-SEGMENT-0070, review finding on
# the WI's own Risk Notes text, PR #321). A model quoting from the
# indexed (marker-prefixed) text instead of the raw story text sometimes
# echoes this marker as a literal prefix -- or, at a paragraph boundary
# within the segment, mid-anchor -- into start_exact/end_exact; the real
# story text never contains it, so the anchor can never resolve without
# stripping it first (WI-SEGMENT-0069).
_PARAGRAPH_MARKER_RE = re.compile(r"\[P\d{4,}\]\s*")

# Curly quotes/dashes -> their plain-ASCII equivalents, each a single
# character so the substitution never changes string length. Applied to
# both the anchor and the searched text before the whitespace-tolerant
# match, so a real position found in the *normalized* text maps 1:1 onto
# the same index in the original `text` (WI-SEGMENT-0070): the source
# corpus uses Unicode typographic quotes/dashes; an LLM-provided anchor
# routinely uses plain ASCII ones for the same real content.
_TYPOGRAPHY_NORMALIZE_MAP = str.maketrans(
    {
        "“": '"',  # “
        "”": '"',  # ”
        "‘": "'",  # ‘
        "’": "'",  # ’
        "—": "-",  # — em dash
        "–": "-",  # – en dash
    }
)


def _normalize_typography(s: str) -> str:
    """Map curly quotes/dashes to ASCII equivalents, preserving length."""
    return s.translate(_TYPOGRAPHY_NORMALIZE_MAP)


def _locate_anchor_span(
    text: str, anchor: str, lo: int, hi: int
) -> tuple[int, int] | None:
    """Exact search first; if not found, try a whitespace-tolerant,
    typography-normalized, case-insensitive match within [lo, hi).
    Returns the (start, end) absolute character span of the actual
    matched text in `text`, or None if not found.

    The exact-match attempt is case-sensitive; only the fallback ignores
    case (WI-SEGMENT-0097), alongside its existing typography and
    whitespace-run tolerance.

    The matched span's length can differ from len(anchor): the
    whitespace-tolerant fallback can match a source whitespace run whose
    length differs from the anchor's own whitespace run (e.g. anchor
    "quick brown" against source "quick  brown"). A caller that needs
    the real end offset of the match -- not just its start -- must use
    this span directly rather than assuming `start + len(anchor)`
    (WI-SEGMENT-0068, review finding, PR #317: align_segment's
    end_exact branch originally made exactly this assumption, silently
    producing a wrong end offset whenever the matched whitespace run's
    length differed from the anchor's).

    Args:
        text: The full text to search within.
        anchor: The substring to find.
        lo: The inclusive lower bound index to start searching.
        hi: The exclusive upper bound index to stop searching.
    Returns:
        The (start, end) absolute span of the anchor in text, or None if
        not found.
    """
    # Treat empty/whitespace-only anchor as unspecified
    if not anchor or not anchor.strip():
        return None

    segment = text[lo:hi]
    # Exact
    pos = segment.find(anchor)
    if pos != -1:
        return lo + pos, lo + pos + len(anchor)

    # Whitespace-tolerant fallback: build a regex from anchor that matches
    # any whitespace run wherever anchor itself has one, searched directly
    # against segment. An LLM-provided anchor's internal newline placement
    # doesn't reliably match the source's hard-wrap boundaries even when
    # every word is correct -- e.g. an anchor's "...the\nneighbors." vs.
    # source text's "...the neighbors." on the same line (WI-SEGMENT-0068).
    # Matched case-insensitively -- real anchors have been observed to
    # differ from the source only in a single letter's case (e.g. a
    # sentence-initial capital the model transcribed lowercase), with no
    # other difference; a deterministic case-fold carries no similarity-
    # threshold risk, unlike bounded edit-distance fuzzy matching
    # (WI-SEGMENT-0072, deliberately not reopened by this fix -
    # WI-SEGMENT-0097).
    #
    # Strip a leaked paragraph-index marker (see _PARAGRAPH_MARKER_RE)
    # and normalize typography before building the fallback regex --
    # neither transform can help the exact-match attempt above (the
    # marker and the curly/ASCII distinction are both intentional
    # differences from the real text, not whitespace noise), so both are
    # applied only here, on the fallback path (WI-SEGMENT-0070).
    anchor_for_fallback = _PARAGRAPH_MARKER_RE.sub("", anchor)
    if not anchor_for_fallback.strip():
        return None
    anchor_for_fallback = _normalize_typography(anchor_for_fallback)
    normalized_segment = _normalize_typography(segment)

    # Escape only the non-whitespace runs, not the whole anchor: escaping
    # anchor first via re.escape() and then substituting whitespace runs
    # with \s+ does not work, because re.escape() itself turns a literal
    # space into "\ " (backslash-space) on supported Python versions,
    # leaving nothing left for a later whitespace-run substitution to
    # match -- this exact ordering mistake was caught in review on the
    # WI-SEGMENT-0068 PR itself, which is why the split happens before
    # escaping, not after.
    parts = re.split(r"(\s+)", anchor_for_fallback)
    pattern = "".join(r"\s+" if part.isspace() else re.escape(part) for part in parts)
    match = re.search(pattern, normalized_segment, re.IGNORECASE)
    if match is None:
        return None
    return lo + match.start(), lo + match.end()


def find_anchor_in_range(text: str, anchor: str, lo: int, hi: int) -> int | None:
    """Exact search first; if not found, try a whitespace-tolerant match
    within [lo, hi).

    Returns absolute index in text, or None if not found. Returns only
    the match's start -- a caller that also needs the match's real end
    offset (which can differ from `start + len(anchor)` for a
    whitespace-tolerant match, see _locate_anchor_span) should call
    _locate_anchor_span directly instead.

    Args:
        text: The full text to search within.
        anchor: The substring to find.
        lo: The inclusive lower bound index to start searching.
        hi: The exclusive upper bound index to stop searching.
    Returns:
        The absolute index of the anchor in text, or None if not found.
    """
    span = _locate_anchor_span(text, anchor, lo, hi)
    return span[0] if span is not None else None


def align_segment(
    story_text: str,
    para_spans: list[tuple[int, int]],
    start_par_id: int,
    end_par_id: int,
    start_exact: str,
    end_exact: str,
) -> tuple[int, int] | None:
    """Align segment to absolute character indices using paragraph IDs and exact anchors.

    Returns (start_char, end_char) or None if alignment fails.
    Args:
        story_text: The full canonicalized story text.
        para_spans: List of (start, end) tuples for each paragraph in story_text.
        start_par_id: 1-based paragraph ID where the segment starts.
        end_par_id: 1-based paragraph ID where the segment ends.
        start_exact: Exact substring expected at the start of the segment (may be empty).
        end_exact: Exact substring expected at the end of the segment (may be empty).
    Returns:
        A tuple (start_char, end_char) of absolute indices, or None if alignment fails.
    """
    # A missing/wrong-typed par_id is itself a form of malformed model
    # output (the tool schema requires these as integers) -- fail
    # cleanly via the same None-return contract as an unresolvable
    # anchor, rather than letting int-comparison operators below raise
    # an opaque TypeError (WI-SEGMENT-0059). isinstance(x, int) alone
    # would accept True/False (bool is an int subclass in Python), which
    # would misresolve to paragraph 1/0 instead of a clean failure if
    # the model ever emitted a boolean for these fields (review finding,
    # PR #269) -- explicitly excluded.
    if (
        not isinstance(start_par_id, int)
        or isinstance(start_par_id, bool)
        or not isinstance(end_par_id, int)
        or isinstance(end_par_id, bool)
    ):
        return None

    n = len(para_spans)
    sp = max(1, min(start_par_id, n)) - 1
    ep = max(1, min(end_par_id, n)) - 1
    if ep < sp:
        ep = sp

    lo = para_spans[sp][0]
    hi = para_spans[ep][1]

    # Start: empty/whitespace → paragraph start. A genuinely non-empty
    # start_exact that can't be located is an alignment failure, not a
    # silent fallback to lo -- a silent fallback here produces the same
    # class of wrong, syntactically-valid-looking span as the end_exact
    # case below (WI-SEGMENT-0059, review finding PR #255).
    if start_exact and start_exact.strip():
        s_idx = find_anchor_in_range(story_text, start_exact, lo, hi)
        if s_idx is None:
            return None
    else:
        s_idx = lo

    # End: empty/whitespace → paragraph end. A genuinely non-empty
    # end_exact that can't be located is an alignment failure, not a
    # silent fallback to hi -- the original bug: falling back to the
    # search range's own end (often end-of-document, when para_spans
    # collapsed to one paragraph) produced spurious full-document-length
    # segments that overlap every segment after them, with no error
    # signal (WI-SEGMENT-0059, WI-ANNOTATE-0054).
    if end_exact and end_exact.strip():
        # Use the actual matched span's end, not e_pos + len(end_exact):
        # a whitespace-tolerant match's real length in story_text can
        # differ from len(end_exact) whenever the matched whitespace run
        # is a different length than the anchor's own (review finding,
        # PR #317 -- see _locate_anchor_span's docstring).
        e_span = _locate_anchor_span(story_text, end_exact, s_idx, hi)
        if e_span is None:
            return None
        e_idx = e_span[1]
    else:
        e_idx = hi

    # Validate
    if (
        not (0 <= s_idx < len(story_text))
        or not (0 < e_idx <= len(story_text))
        or e_idx <= s_idx
    ):
        return None
    return s_idx, e_idx


# ---- public hooks ----


def paragraph_text_indexer(story_text: str) -> Tuple[str, Dict[str, Any]]:
    """
    Returns (indexed_text, index_meta) suitable for JSONPromptExtractor.
    index_meta contains everything the aligner needs.

    The indexed_text has [P0001], [P0002], ... markers prefixed to each paragraph.

    Args:
        story_text: The full text to index.
    Returns:
        A tuple (indexed_text, index_meta):
          - indexed_text: The text with paragraph markers.
          - index_meta: A dict with keys:
              - canonical_text: The canonicalized text.
              - splitter: The paragraph splitter used.
              - para_spans: List of (start, end) tuples for each paragraph.
              - n_paragraphs: The number of paragraphs.
    """
    text = canonicalize_text(story_text)
    default_splitter = "\n\n"
    effective_splitter = _effective_paragraph_splitter(text, default_splitter)
    paragraphs, para_spans = build_paragraph_index(text, splitter=default_splitter)
    # Use the same splitter build_paragraph_index actually applied
    # (which may have fallen back from the default) so the paragraph
    # markers shown to the model use consistent delimiters, and "splitter"
    # in index_meta reflects reality rather than the unconditional default.
    indexed = add_paragraph_markers(paragraphs, delimiter=effective_splitter)
    meta: Dict[str, Any] = {
        "canonical_text": text,
        "splitter": effective_splitter,
        "para_spans": para_spans,
        "n_paragraphs": len(paragraphs),
    }
    return indexed, meta


def segments_result_aligner(
    parsed_output: Dict[str, Any], story_text: str, index_meta: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Fills/repairs start_char/end_char in-place for segments that provide:
      start_par_id, end_par_id, start_exact, end_exact

    Raises ValueError if any segment's alignment fails (align_segment
    returns None, or itself raises) -- previously such a failure was
    silently swallowed and the segment left unchanged (possibly with
    null offsets, or worse, a caller-supplied bogus offset), with no
    signal that anything went wrong. Raising here lets it propagate to
    JSONPromptExtractor.extract's own try/except around calling this
    function, which sets alignment_error -- the mechanism annotate.py's
    _annotate_genre/_annotate_scenes already checks and rejects on, but
    that previously never actually fired for this failure mode
    (WI-SEGMENT-0059). This is an all-or-nothing choice deliberately:
    a story with even one misaligned segment is not safe to partially
    trust, matching this pipeline's existing preference (elsewhere) for
    a whole-story rejection over silently-wrong partial output.

    Args:
        parsed_output: The parsed JSON output from the extractor.
        story_text: The full canonicalized story text.
        index_meta: The index_meta returned by the text_indexer.
    Returns:
        The updated parsed_output with aligned character offsets.
    """
    text = index_meta.get("canonical_text") or story_text
    para_spans = index_meta["para_spans"]

    obj = dict(parsed_output)
    segs = list(obj.get("segments") or [])
    fixed = []
    for seg in segs:
        seg = dict(seg)
        try:
            span = align_segment(
                text,
                para_spans,
                seg.get("start_par_id"),
                seg.get("end_par_id"),
                seg.get("start_exact", ""),
                seg.get("end_exact", ""),
            )
        except Exception as exc:
            raise ValueError(
                f"alignment failed for segment_id={seg.get('segment_id')!r}: {exc!r}"
            ) from exc

        if span is None:
            raise ValueError(
                f"alignment failed for segment_id={seg.get('segment_id')!r}: "
                "anchor text not found in story text"
            )

        seg["start_char"], seg["end_char"] = span
        fixed.append(seg)

    obj["segments"] = fixed
    return obj


def _normalize_preview(s: str) -> str:
    if not s:
        return ""
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = re.sub(r"\n{2,}", "\u2029", s)  # mark paragraph breaks
    s = s.replace("\n", " ")  # single newlines -> spaces
    s = re.sub(r"[ \t\u00A0]+", " ", s).strip()
    return s.replace("\u2029", "\n")


def _sm(text: str, limit: int = 160) -> str:
    return utils.sm(_normalize_preview(text or ""), limit=limit)


def _valid_span(s: Any, e: Any, n: int) -> bool:
    return isinstance(s, int) and isinstance(e, int) and 0 <= s < e <= n


def _union_coverage(spans: List[Tuple[int, int]]) -> int:
    if not spans:
        return 0
    spans = sorted(spans)
    total = 0
    cur_s, cur_e = spans[0]
    for s, e in spans[1:]:
        if s > cur_e:
            total += cur_e - cur_s
            cur_s, cur_e = s, e
        else:
            cur_e = max(cur_e, e)
    total += cur_e - cur_s
    return total


def validate_coverage_and_overlaps(
    text: str,
    segments: List[Dict[str, Any]],
    *,
    ignore_whitespace_gaps: bool = True,
    whitespace_gap_max: int = 8,
):
    """Returns (missing_components, overlapping_components)."""
    n = len(text)

    def is_ws_only(s: str) -> bool:
        return s.strip().strip("\u00a0") == ""

    # Build valid spans
    items = []
    for idx, seg in enumerate(segments):
        s = seg.get("start_char")
        e = seg.get("end_char")
        if _valid_span(s, e, n):
            items.append(
                {
                    "i": idx,
                    "segment_id": seg.get("segment_id", f"#{idx}"),
                    "start": int(s),
                    "end": int(e),
                }
            )
    items.sort(key=lambda d: (d["start"], d["end"]))

    missing, overlaps = [], []
    if not items:
        if n > 0:
            missing.append(
                {
                    "type": "start_gap",
                    "start": 0,
                    "end": n,
                    "length": n,
                    "preview": _sm(text[0:n]),
                }
            )
        return missing, overlaps

    covered_end = 0
    prev_seg = None
    max_seg = None

    for pos, cur in enumerate(items):
        s, e = cur["start"], cur["end"]

        # GAP relative to farthest coverage so far
        if s > covered_end:
            gap_slice = text[covered_end:s]
            if not (
                ignore_whitespace_gaps
                and (s - covered_end) <= whitespace_gap_max
                and is_ws_only(gap_slice)
            ):
                gap = {
                    "type": "start_gap" if covered_end == 0 else "gap",
                    "start": covered_end,
                    "end": s,
                    "length": s - covered_end,
                    "preview": _sm(gap_slice),
                }
                if prev_seg is not None and covered_end != 0:
                    gap["left_segment_id"] = prev_seg["segment_id"]
                    gap["right_segment_id"] = cur["segment_id"]
                missing.append(gap)

        # OVERLAP vs previous-by-start
        if prev_seg is not None and s < prev_seg["end"]:
            ov_start = max(prev_seg["start"], s)
            ov_end = min(prev_seg["end"], e)
            if s == prev_seg["start"] and e == prev_seg["end"]:
                otype = "duplicate"
            elif s >= prev_seg["start"] and e <= prev_seg["end"]:
                otype = "contained"
            elif prev_seg["start"] >= s and prev_seg["end"] <= e:
                otype = "contained"
            else:
                otype = "partial_overlap"
            overlaps.append(
                {
                    "type": otype,
                    "a_index": pos - 1,
                    "b_index": pos,
                    "a_segment_id": prev_seg["segment_id"],
                    "b_segment_id": cur["segment_id"],
                    "start": ov_start,
                    "end": ov_end,
                    "length": max(0, ov_end - ov_start),
                }
            )

        # OVERLAP vs max-extent segment (containment across non-adjacent)
        if max_seg is not None and max_seg is not prev_seg and s < max_seg["end"]:
            if s >= max_seg["start"] and e <= max_seg["end"]:
                overlaps.append(
                    {
                        "type": "contained",
                        "a_index": max_seg["i"],
                        "b_index": cur["i"],
                        "a_segment_id": max_seg["segment_id"],
                        "b_segment_id": cur["segment_id"],
                        "start": s,
                        "end": e,
                        "length": e - s,
                    }
                )

        # Advance coverage frontier
        if e > covered_end:
            covered_end = e
        if max_seg is None or e > max_seg["end"]:
            max_seg = cur
        prev_seg = cur

    # END GAP
    if covered_end < n:
        tail = text[covered_end:n]
        if not (
            ignore_whitespace_gaps
            and is_ws_only(tail)
            and (n - covered_end) <= whitespace_gap_max
        ):
            missing.append(
                {
                    "type": "end_gap",
                    "start": covered_end,
                    "end": n,
                    "length": n - covered_end,
                    "preview": _sm(tail),
                }
            )

    return missing, overlaps


def audit_segments_against_anchors(
    text: str, segments: List[Dict[str, Any]], *, sample: int = 100
):
    """Warn when aligned offsets don't match the anchors verbatim."""
    warns = []
    n = len(text)
    for idx, seg in enumerate(segments):
        s = seg.get("start_char")
        e = seg.get("end_char")
        sx = seg.get("start_exact") or ""
        ex = seg.get("end_exact") or ""
        if _valid_span(s, e, n):
            head = text[s : s + len(sx)] if sx else ""
            tail = text[e - len(ex) : e] if ex else ""
            if sx and head != sx:
                warns.append(
                    {
                        "segment_id": seg.get("segment_id", idx),
                        "issue": "start_mismatch",
                        "at": s,
                        "expected": utils.sm(sx, sample),
                        "found": utils.sm(head, sample),
                    }
                )
            if ex and tail != ex:
                warns.append(
                    {
                        "segment_id": seg.get("segment_id", idx),
                        "issue": "end_mismatch",
                        "at": e,
                        "expected": utils.sm(ex, sample),
                        "found": utils.sm(tail, sample),
                    }
                )
        else:
            warns.append(
                {
                    "segment_id": seg.get("segment_id", idx),
                    "issue": "invalid_span",
                    "span": (s, e),
                }
            )
    return warns


def segments_auditor(
    parsed_output: Dict[str, Any], story_text: str, index_meta: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Default validator/auditor for JSONPromptExtractor.
    Uses canonical text (from index_meta) if available.
    Returns a report dict with warnings, gaps/overlaps, and coverage stats.
    """
    text = index_meta.get("canonical_text") or story_text
    segments = list(parsed_output.get("segments") or [])

    # Coverage & overlap validation (ignore tiny whitespace seams)
    missing, overlaps = validate_coverage_and_overlaps(
        text, segments, ignore_whitespace_gaps=True, whitespace_gap_max=8
    )

    # Anchor-vs-offset warnings
    warnings = audit_segments_against_anchors(text, segments, sample=120)

    # Coverage stats
    spans = [
        (int(s["start_char"]), int(s["end_char"]))
        for s in segments
        if _valid_span(s.get("start_char"), s.get("end_char"), len(text))
    ]
    covered = _union_coverage(spans)
    total = len(text)
    coverage_pct = (covered / total * 100.0) if total else 0.0

    return {
        # anchor/offset mismatches, invalid spans
        "warnings": warnings,
        "missing_components": missing,  # gaps
        "overlapping_components": overlaps,  # overlaps/containment
        "coverage": {
            "covered_chars": covered,
            "total_chars": total,
            "coverage_pct": round(coverage_pct, 2),
        },
        "counts": {
            "segments_total": len(segments),
            "segments_with_valid_spans": len(spans),
            "warnings": len(warnings),
            "gaps": len(missing),
            "overlaps": len(overlaps),
        },
    }
