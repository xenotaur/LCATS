# lcats/analysis/text_indexing.py

import re
from typing import Any, Dict, List, Tuple

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
