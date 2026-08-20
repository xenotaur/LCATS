"""Classify check_segmentation_reliability.py's alignment_error outcomes
into named categories, using each failing story's persisted parsed_output
(the raw, pre-alignment segments dict -- see that script's Required
Change 1, WI-SEGMENT-0069) plus a paragraph index recomputed deterministically
from the story's own body text.

For each alignment_error outcome, re-runs the same anchor-resolution logic
align_segment uses (text_segmenter._locate_anchor_span) against the failing
segment's raw start_par_id/end_par_id/start_exact/end_exact, this time also
checking whether the anchor text exists ANYWHERE in the document (not just
within the claimed paragraph range). This distinguishes two structurally
different failure modes that align_segment's single "anchor text not found
in story text" error message conflates:

  - anchor_absent_from_document: the anchor text (even whitespace-tolerant)
    does not appear anywhere in the story at all.
  - found_outside_claimed_range ("paragraph mis-numbering"): the anchor
    text is real and present, just outside the paragraph range implied by
    the model's own start_par_id/end_par_id.

CAVEAT: align_segment (via segments_result_aligner) fails fast on a
story's first unalignable segment and never checks the rest -- this script
inherits that same one-category-per-story limitation from
check_segmentation_reliability.py's own per-story error message, which
only ever reports the first failing segment_id.

USAGE
-----
    python experiments/03_cross_segment_relation_pilot/classify_alignment_failures.py \\
        --smoke-dir /tmp/segmentation_reliability --data-dir corpora

`--smoke-dir` is a check_segmentation_reliability.py `--output` directory.
No LLM calls are made; this only reads already-persisted JSON.
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lcats" / "src"))

from lcats.analysis import story_analysis
from lcats.analysis import text_segmenter

# Margin (in characters) below which a paragraph-mis-numbering match is
# reported as "narrow" rather than "large" -- an arbitrary but documented
# threshold, not a claim about where a fix would need to draw the line.
_NARROW_MARGIN_CHARS = 200


def parse_failing_segment_id(outcome: str) -> int | None:
    """Extract the segment_id align_segment reported as unalignable."""
    match = re.search(r"segment_id=(\d+)", outcome)
    return int(match.group(1)) if match else None


def classify_anchor(text: str, anchor: str, lo: int, hi: int) -> dict:
    """Classify one anchor's failure mode against its claimed [lo, hi)."""
    if not anchor or not anchor.strip():
        return {"present": True, "reason": "empty_anchor_no_check_needed"}
    if text_segmenter._locate_anchor_span(text, anchor, lo, hi) is not None:
        return {"present": True, "reason": "resolves_in_claimed_range"}
    doc_span = text_segmenter._locate_anchor_span(text, anchor, 0, len(text))
    if doc_span is None:
        return {"present": False, "reason": "absent_from_document"}
    margin_chars = lo - doc_span[0] if doc_span[0] < lo else doc_span[0] - hi
    return {
        "present": True,
        "reason": "found_outside_claimed_range",
        "margin_chars": margin_chars,
        "real_pos": doc_span[0],
        "claimed_range": [lo, hi],
    }


def classify_story(record: dict, data_dir: pathlib.Path) -> tuple[str, list[str]]:
    """Return (category, [detail strings]) for one alignment_error record.

    category is one of: anchor_absent_from_document,
    paragraph_misnumbering_large_margin, paragraph_misnumbering_narrow_margin,
    or a diagnostic fallback (no_parsed_output_captured,
    failing_segment_not_found_in_parsed_output, bad_par_id_type,
    no_anchor_failure_reproduced) when the recorded outcome can't be
    reproduced from the persisted data alone.
    """
    story_id = record["story_id"]
    seg_id = parse_failing_segment_id(record.get("outcome", ""))
    parsed = record.get("parsed_output")
    if not parsed or "segments" not in parsed:
        return "no_parsed_output_captured", [story_id]

    # This script re-derives a story's body from --data-dir rather than
    # trusting the smoke-dir record alone, so a malformed story_id or a
    # story.json that's gone missing/changed since the smoke test ran
    # must degrade to a diagnostic category -- not crash the whole batch
    # report over one bad story (review finding, PR #320).
    try:
        collection, slug = story_id.split("/", 1)
        story_path = data_dir / collection / slug / "story.json"
        body = story_analysis.coerce_text(
            json.loads(story_path.read_text("utf-8")).get("body", "")
        )
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        return "story_file_unreadable", [f"{story_id}: {type(exc).__name__}: {exc}"]
    _, index_meta = text_segmenter.paragraph_text_indexer(body)
    text = index_meta.get("canonical_text") or body
    para_spans = index_meta["para_spans"]
    n_par = len(para_spans)

    seg = next((s for s in parsed["segments"] if s.get("segment_id") == seg_id), None)
    if seg is None:
        return "failing_segment_not_found_in_parsed_output", [
            f"{story_id} seg={seg_id}"
        ]

    start_par_id = seg.get("start_par_id")
    end_par_id = seg.get("end_par_id")
    if (
        not isinstance(start_par_id, int)
        or isinstance(start_par_id, bool)
        or not isinstance(end_par_id, int)
        or isinstance(end_par_id, bool)
    ):
        return "bad_par_id_type", [f"{story_id} seg={seg_id}"]

    sp = max(1, min(start_par_id, n_par)) - 1
    ep = max(1, min(end_par_id, n_par)) - 1
    ep = max(ep, sp)
    lo, hi = para_spans[sp][0], para_spans[ep][1]

    start_exact = seg.get("start_exact") or ""
    end_exact = seg.get("end_exact") or ""

    # Mirror align_segment's own sequential resolution order exactly
    # (review finding, PR #320): it resolves start_exact against
    # [lo, hi) first and, only if that succeeds, searches end_exact
    # against [s_idx, hi) -- the START of the resolved start_exact match,
    # not lo. Checking both anchors independently against the full
    # [lo, hi) range (the original version of this function) can find
    # end_exact "in range" even when it occurs before the resolved
    # start_exact position, a case align_segment itself would still
    # reject -- silently reporting no_anchor_failure_reproduced for a
    # story whose alignment genuinely failed.
    failing_name = None
    failing_result = None
    if start_exact.strip():
        start_result = classify_anchor(text, start_exact, lo, hi)
        if start_result["reason"] != "resolves_in_claimed_range":
            failing_name, failing_result = "start_exact", start_result
            s_idx = None
        else:
            s_idx = text_segmenter._locate_anchor_span(text, start_exact, lo, hi)[0]
    else:
        s_idx = lo

    if failing_name is None and end_exact.strip():
        end_result = classify_anchor(text, end_exact, s_idx, hi)
        if end_result["reason"] != "resolves_in_claimed_range":
            failing_name, failing_result = "end_exact", end_result

    if failing_name is None:
        return "no_anchor_failure_reproduced", [
            f"{story_id} seg={seg_id} n_par={n_par} claimed=[{start_par_id},{end_par_id}]"
        ]

    details = [
        f"{story_id} seg={seg_id} {failing_name}={seg.get(failing_name)!r} "
        f"n_par={n_par} claimed=[{start_par_id},{end_par_id}] detail={failing_result}"
    ]
    if failing_result["reason"] == "absent_from_document":
        return "anchor_absent_from_document", details
    margin = failing_result["margin_chars"]
    category = (
        "paragraph_misnumbering_narrow_margin"
        if margin <= _NARROW_MARGIN_CHARS
        else "paragraph_misnumbering_large_margin"
    )
    return category, details


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--smoke-dir",
        required=True,
        help="check_segmentation_reliability.py --output dir",
    )
    parser.add_argument("--data-dir", default="corpora")
    args = parser.parse_args()

    smoke_dir = pathlib.Path(args.smoke_dir)
    data_dir = pathlib.Path(args.data_dir)
    categories: collections.Counter = collections.Counter()
    examples: dict[str, list[str]] = collections.defaultdict(list)

    for result_path in sorted(smoke_dir.glob("*/*.json")):
        record = json.loads(result_path.read_text("utf-8"))
        if not record.get("outcome", "").startswith("alignment_error:"):
            continue
        category, details = classify_story(record, data_dir)
        categories[category] += 1
        examples[category].extend(details)

    print("Per-story category counts:")
    for category, n in categories.most_common():
        print(f"  {n:>3}  {category}")
    print()
    for category, exs in examples.items():
        print(f"--- {category} ({len(exs)} detail lines) ---")
        for ex in exs[:5]:
            print(f"  {ex}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
