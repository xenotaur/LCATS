"""Functionality to index story text for robust segment alignment and auditing."""

import re
from typing import Any, Dict, List, Tuple


from lcats import utils


_WS = re.compile(r"\s+")


def _norm_ws(s: str) -> str:
    """Normalize whitespace: collapse runs, trim ends."""
    return _WS.sub(" ", s)


def canonicalize_text(s: str) -> str:
    """Canonicalize newlines to \n and trim trailing whitespace."""
    return s.replace("\r\n", "\n").replace("\r", "\n")


def build_paragraph_index(story_text: str, splitter: str = "\n\n") -> Tuple[List[str], List[Tuple[int, int]]]:
    """Split story_text into paragraphs by splitter, returning (parts, spans).

    Each span is a (start, end) tuple of absolute character indices in story_text.

    Args:
        story_text: The full text to split.
        splitter: The string that delimits paragraphs (default: double newline).
    Returns:
        A tuple (parts, spans):
          - parts: List of paragraph strings.
          - spans: List of (start, end) tuples giving absolute character indices.
    """
    parts: List[str] = []
    spans: List[Tuple[int, int]] = []
    i = 0
    for chunk in story_text.split(splitter):
        j = story_text.find(chunk, i)
        if j == -1:
            j = i
        k = j + len(chunk)
        parts.append(chunk)
        spans.append((j, k))
        i = k + len(splitter)
    return parts, spans


def add_paragraph_markers(paragraphs: List[str], delimiter: str = "\n\n") -> str:
    """Return text with [P0001], [P0002], ... markers prefixed to each paragraph.

    Args:
        paragraphs: List of paragraph strings.
        delimiter: String to place between paragraphs (default: double newline).
    Returns:
        The combined text with paragraph markers.
    """
    return "".join(f"[P{idx+1:04d}] " + p + (delimiter if idx < len(paragraphs) - 1 else "")
                   for idx, p in enumerate(paragraphs))


def find_anchor_in_range(text: str, anchor: str, lo: int, hi: int) -> int | None:
    """Exact search first; if not found, try whitespace-normalized match within [lo,hi).

    Returns absolute index in text, or None if not found.

    Args:
        text: The full text to search within.
        anchor: The substring to find.
        lo: The inclusive lower bound index to start searching.
        hi: The exclusive upper bound index to stop searching.
    Returns:
        The absolute index of the anchor in text, or None if not found.
    """
    # Treat empty/whitespace-only anchor as unspecified
    if not anchor or not anchor.strip():
        return None

    segment = text[lo:hi]
    # Exact
    pos = segment.find(anchor)
    if pos != -1:
        return lo + pos

    # Whitespace-insensitive fallback
    anc_n = _norm_ws(anchor)
    seg_n = _norm_ws(segment)
    pos_n = seg_n.find(anc_n)
    if pos_n == -1:
        return None

    # Heuristic remap back to original indices
    start_guess = max(0, int(pos_n * (len(segment) / max(1, len(seg_n))) - 20))
    window = segment[start_guess:start_guess + len(anchor) + 200]
    pos2 = window.find(anchor)
    if pos2 != -1:
        return lo + start_guess + pos2
    return None


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
    n = len(para_spans)
    sp = max(1, min(start_par_id, n)) - 1
    ep = max(1, min(end_par_id, n)) - 1
    if ep < sp:
        ep = sp

    lo = para_spans[sp][0]
    hi = para_spans[ep][1]

    # Start: empty/whitespace → paragraph start
    if start_exact and start_exact.strip():
        s_idx = find_anchor_in_range(story_text, start_exact, lo, hi)
        if s_idx is None:
            s_idx = lo
    else:
        s_idx = lo

    # End: empty/whitespace → paragraph end
    if end_exact and end_exact.strip():
        e_pos = find_anchor_in_range(story_text, end_exact, s_idx, hi)
        e_idx = (e_pos + len(end_exact)) if e_pos is not None else hi
    else:
        e_idx = hi

    # Validate
    if not (0 <= s_idx < len(story_text)) or not (0 < e_idx <= len(story_text)) or e_idx <= s_idx:
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
    paragraphs, para_spans = build_paragraph_index(text, splitter="\n\n")
    indexed = add_paragraph_markers(paragraphs, delimiter="\n\n")
    meta: Dict[str, Any] = {
        "canonical_text": text,
        "splitter": "\n\n",
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
        except Exception:
            span = None

        if span:
            seg["start_char"], seg["end_char"] = span
        # else: leave as-is (may remain null)

        fixed.append(seg)

    obj["segments"] = fixed
    return obj


def _normalize_preview(s: str) -> str:
    if not s:
        return ""
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = re.sub(r"\n{2,}", "\u2029", s)  # mark paragraph breaks
    s = s.replace("\n", " ")            # single newlines -> spaces
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
    whitespace_gap_max: int = 8
):
    """Returns (missing_components, overlapping_components)."""
    n = len(text)

    def is_ws_only(s: str) -> bool:
        return s.strip().strip("\u00A0") == ""

    # Build valid spans
    items = []
    for idx, seg in enumerate(segments):
        s = seg.get("start_char")
        e = seg.get("end_char")
        if _valid_span(s, e, n):
            items.append({
                "i": idx,
                "segment_id": seg.get("segment_id", f"#{idx}"),
                "start": int(s),
                "end": int(e),
            })
    items.sort(key=lambda d: (d["start"], d["end"]))

    missing, overlaps = [], []
    if not items:
        if n > 0:
            missing.append({
                "type": "start_gap",
                "start": 0, "end": n, "length": n,
                "preview": _sm(text[0:n]),
            })
        return missing, overlaps

    covered_end = 0
    prev_seg = None
    max_seg = None

    for pos, cur in enumerate(items):
        s, e = cur["start"], cur["end"]

        # GAP relative to farthest coverage so far
        if s > covered_end:
            gap_slice = text[covered_end:s]
            if not (ignore_whitespace_gaps and (s - covered_end) <= whitespace_gap_max and is_ws_only(gap_slice)):
                gap = {
                    "type": "start_gap" if covered_end == 0 else "gap",
                    "start": covered_end, "end": s, "length": s - covered_end,
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
            overlaps.append({
                "type": otype,
                "a_index": pos - 1, "b_index": pos,
                "a_segment_id": prev_seg["segment_id"],
                "b_segment_id": cur["segment_id"],
                "start": ov_start, "end": ov_end, "length": max(0, ov_end - ov_start),
            })

        # OVERLAP vs max-extent segment (containment across non-adjacent)
        if max_seg is not None and max_seg is not prev_seg and s < max_seg["end"]:
            if s >= max_seg["start"] and e <= max_seg["end"]:
                overlaps.append({
                    "type": "contained",
                    "a_index": max_seg["i"], "b_index": cur["i"],
                    "a_segment_id": max_seg["segment_id"],
                    "b_segment_id": cur["segment_id"],
                    "start": s, "end": e, "length": e - s,
                })

        # Advance coverage frontier
        if e > covered_end:
            covered_end = e
        if max_seg is None or e > max_seg["end"]:
            max_seg = cur
        prev_seg = cur

    # END GAP
    if covered_end < n:
        tail = text[covered_end:n]
        if not (ignore_whitespace_gaps and is_ws_only(tail) and (n - covered_end) <= whitespace_gap_max):
            missing.append({
                "type": "end_gap",
                "start": covered_end, "end": n, "length": n - covered_end,
                "preview": _sm(tail),
            })

    return missing, overlaps


def audit_segments_against_anchors(text: str, segments: List[Dict[str, Any]], *, sample: int = 100):
    """Warn when aligned offsets don't match the anchors verbatim."""
    warns = []
    n = len(text)
    for idx, seg in enumerate(segments):
        s = seg.get("start_char")
        e = seg.get("end_char")
        sx = (seg.get("start_exact") or "")
        ex = (seg.get("end_exact") or "")
        if _valid_span(s, e, n):
            head = text[s:s + len(sx)] if sx else ""
            tail = text[e - len(ex):e] if ex else ""
            if sx and head != sx:
                warns.append({
                    "segment_id": seg.get("segment_id", idx),
                    "issue": "start_mismatch",
                    "at": s,
                    "expected": utils.sm(sx, sample),
                    "found": utils.sm(head, sample),
                })
            if ex and tail != ex:
                warns.append({
                    "segment_id": seg.get("segment_id", idx),
                    "issue": "end_mismatch",
                    "at": e,
                    "expected": utils.sm(ex, sample),
                    "found": utils.sm(tail, sample),
                })
        else:
            warns.append({
                "segment_id": seg.get("segment_id", idx),
                "issue": "invalid_span",
                "span": (s, e),
            })
    return warns


def segments_auditor(parsed_output: Dict[str, Any], story_text: str, index_meta: Dict[str, Any]) -> Dict[str, Any]:
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
    spans = [(int(s["start_char"]), int(s["end_char"]))
             for s in segments
             if _valid_span(s.get("start_char"), s.get("end_char"), len(text))]
    covered = _union_coverage(spans)
    total = len(text)
    coverage_pct = (covered / total * 100.0) if total else 0.0

    return {
        # anchor/offset mismatches, invalid spans
        "warnings": warnings,
        "missing_components": missing,              # gaps
        "overlapping_components": overlaps,         # overlaps/containment
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


