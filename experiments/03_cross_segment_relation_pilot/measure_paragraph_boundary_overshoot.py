"""Measure WI-SEGMENT-0098's paragraph-boundary-overshoot pattern for a
committed segmentation-reliability results directory (WI-SEGMENT-0101).

Replays WI-SEGMENT-0098's own methodology exactly: for every segment
produced by a run (whether the story's overall `outcome` was `included`
or `alignment_error` - `parsed_output` preserves the pre-alignment
segment fields either way), locates `start_exact` then `end_exact` using
the exact same bounded search `text_segmenter.align_segment` itself
performs (`start_exact` in `[lo, hi)`; `end_exact` in `[s_idx, hi)`, where
`s_idx` is wherever `start_exact` actually resolved - not `lo` again),
and only falls back to an unbounded full-document search when the
bounded search genuinely fails, to size how far outside the claimed
`[start_par_id, end_par_id]` paragraph range (inclusive - `align_segment`'s
own convention: `hi = para_spans[end_par_id-1][1]`) the true anchor lies.

Run against both the WI-EVENT-0096 baseline directory (the unchanged
production prompt) and the WI-SEGMENT-0101 reworded-prompt directory,
then compare, to see whether the reworded prompt's paragraph-boundary
overshoot rate shrinks, per WI-SEGMENT-0101's Required Change 3.

USAGE
-----
    python experiments/03_cross_segment_relation_pilot/measure_paragraph_boundary_overshoot.py \\
        --results-dir experiments/03_cross_segment_relation_pilot/results/segmentation_reliability \\
        --label baseline

    python experiments/03_cross_segment_relation_pilot/measure_paragraph_boundary_overshoot.py \\
        --results-dir experiments/03_cross_segment_relation_pilot/results/segmentation_reliability_reworded_prompt \\
        --label reworded
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any, Dict, List

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lcats" / "src"))

from lcats.analysis import story_analysis  # noqa: E402
from lcats.analysis import text_segmenter  # noqa: E402

CORPORA_ROOT = pathlib.Path(__file__).resolve().parents[2] / "corpora"


def _story_text(story_id: str) -> str:
    path = CORPORA_ROOT / story_id / "story.json"
    data = json.loads(path.read_text("utf-8"))
    return text_segmenter.canonicalize_text(
        story_analysis.coerce_text(data.get("body", ""))
    )


def _segments(parsed_output: Any) -> List[Dict[str, Any]]:
    if isinstance(parsed_output, dict):
        return list(parsed_output.get("segments") or [])
    if isinstance(parsed_output, list):
        return list(parsed_output)
    return []


def _check_segment(
    text: str, para_spans: List[tuple], seg: Dict[str, Any]
) -> Dict[str, Any] | None:
    """Return a per-anchor overshoot report for one segment, or None if
    the segment lacks the fields needed to check it (e.g. missing
    start_par_id/end_par_id from a malformed model response - a separate
    failure mode this measurement does not classify).

    Normalizes start_par_id/end_par_id the same way
    text_segmenter.align_segment does, including two review-caught cases
    (PR #420):

    - bools are rejected even though isinstance(True, int) is true in
      Python (align_segment explicitly excludes them, WI-SEGMENT-0059
      review finding, PR #269);
    - end_par_id is clamped up to start_par_id when the model reports it
      lower (align_segment's `ep = max(ep, sp)`);
    - out-of-range par_ids are clamped into [1, len(para_spans)] via
      align_segment's own `max(1, min(x, n))`, not skipped - an earlier
      draft of this function returned None (treating the segment as
      unchecked) for an out-of-range par_id instead of clamping like
      production does, which would silently drop such segments from the
      measurement rather than mirror what align_segment would actually
      compute.

    None of these three cases occurred in either committed results
    directory (verified directly), so none of these fixes changed this
    run's reported numbers - the check now matches align_segment's real
    normalization exactly rather than only approximately.
    """
    start_par_id = seg.get("start_par_id")
    end_par_id = seg.get("end_par_id")
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
    lo, hi = para_spans[sp][0], para_spans[ep][1]

    report: Dict[str, Any] = {
        "segment_id": seg.get("segment_id"),
        "start_par_id": start_par_id,
        "end_par_id": end_par_id,
        "claimed_window": [lo, hi],
    }

    # Resolve start_exact first, exactly matching align_segment's own
    # sequencing: start_exact is searched in [lo, hi), and end_exact is
    # then searched starting from wherever start_exact actually resolved
    # (s_idx), not from lo again.
    start_report, s_idx = _locate_one_anchor(
        text, seg.get("start_exact"), lo, hi, lo, hi
    )
    report["start"] = start_report
    end_search_lo = s_idx if s_idx is not None else lo
    end_report, _ = _locate_one_anchor(
        text, seg.get("end_exact"), end_search_lo, hi, lo, hi
    )
    report["end"] = end_report

    return report


def _locate_one_anchor(
    text: str,
    anchor: str | None,
    search_lo: int,
    search_hi: int,
    window_lo: int,
    window_hi: int,
) -> tuple:
    """Locate one anchor, preferring the search range production would
    actually use, but always judging "inside the claimed window" against
    the TRUE window (window_lo/window_hi) - not against whatever range
    was searched.

    These two are deliberately kept separate (review finding, PR #420):
    an earlier draft treated "found via the bounded search" as
    synonymous with "inside the claimed window," but end_exact's own
    search range can be widened below the true window's start when
    start_exact itself only resolved via the unbounded fallback (i.e.
    search_lo can be < window_lo). A match found in that widened gap is
    NOT actually inside the claimed window even though the bounded
    search "succeeded" - two real cases in this dataset hit exactly this
    (lovecraft/the_haunter_of_the_dark segment 10 in the baseline;
    mass_quantities/the_guardians__cox segment 6 in the reworded run),
    though in both, re-checking against the true window happened to
    still classify the end anchor as inside - this fix makes that a
    guarantee of the method, not a coincidence of this particular data.

    Still tries the search range first (not an unconditional unbounded
    search) to prefer the occurrence production would actually find over
    an unrelated duplicate elsewhere in the story (see
    mass_quantities/the_invaders__ferris segment 8, an `included` story
    whose end_exact anchor also happens, coincidentally, to occur
    thousands of characters earlier in the same story - an
    unbounded-only search would wrongly flag that as an overshoot).

    Returns (report_dict, resolved_start_or_None) - the resolved absolute
    start offset is returned separately so the caller can use it as the
    next anchor's search floor, mirroring align_segment's s_idx handoff.
    """
    if not anchor:
        return {"anchor_present": False}, None

    match = text_segmenter._locate_anchor_span(text, anchor, search_lo, search_hi)
    if match is None:
        match = text_segmenter._locate_anchor_span(text, anchor, 0, len(text))
    if match is None:
        return {"anchor_present": True, "located": False}, None

    match_start, match_end = match
    inside = window_lo <= match_start and match_end <= window_hi
    return (
        {
            "anchor_present": True,
            "located": True,
            "match_span": [match_start, match_end],
            "inside_claimed_window": inside,
            "overshoot_chars": (
                0
                if inside
                else max(0, window_lo - match_start) + max(0, match_end - window_hi)
            ),
        },
        match_start,
    )


def measure(results_dir: pathlib.Path) -> Dict[str, Any]:
    per_story: Dict[str, Any] = {}
    total_segments = 0
    total_checked = 0
    total_outside = 0
    total_anchors = 0
    total_anchors_outside = 0

    for story_dir in sorted(results_dir.iterdir()):
        if not story_dir.is_dir():
            continue
        for result_file in sorted(story_dir.glob("*.json")):
            data = json.loads(result_file.read_text("utf-8"))
            story_id = data.get("story_id")
            if not story_id or not data.get("llm_call_made"):
                continue
            segments = _segments(data.get("parsed_output"))
            if not segments:
                continue
            text = _story_text(story_id)
            _, index_meta = text_segmenter.paragraph_text_indexer(text)
            para_spans = index_meta["para_spans"]

            story_reports = []
            for seg in segments:
                total_segments += 1
                report = _check_segment(text, para_spans, seg)
                if report is None:
                    continue
                total_checked += 1
                # Two distinct metrics, deliberately both reported (review
                # finding, PR #420): "segment-level" counts a segment once
                # if EITHER anchor is outside; "anchor-level" counts each
                # outside anchor individually (a segment with both anchors
                # outside, e.g. easy_money__sinclair segment 4 in the
                # reworded run, contributes 1 to the segment-level count
                # but 2 to the anchor-level count) - an earlier draft's
                # prose called the segment-level number "anchor-level,"
                # which understated the true per-anchor rate.
                side_outside = {
                    side: bool(
                        report.get(side, {}).get("located")
                        and not report[side].get("inside_claimed_window", True)
                    )
                    for side in ("start", "end")
                }
                outside = any(side_outside.values())
                report["outside_claimed_window"] = outside
                if outside:
                    total_outside += 1
                for side, present in (
                    ("start", report.get("start", {}).get("anchor_present")),
                    ("end", report.get("end", {}).get("anchor_present")),
                ):
                    if present:
                        total_anchors += 1
                        if side_outside[side]:
                            total_anchors_outside += 1
                story_reports.append(report)

            per_story[story_id] = {
                "outcome": data.get("outcome"),
                "segments": story_reports,
            }

    return {
        "results_dir": str(results_dir),
        "total_segments": total_segments,
        "total_checked": total_checked,
        "total_outside_claimed_window": total_outside,
        "total_anchors_checked": total_anchors,
        "total_anchors_outside_claimed_window": total_anchors_outside,
        "per_story": per_story,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    result = measure(pathlib.Path(args.results_dir))
    if args.label:
        result["label"] = args.label

    output = json.dumps(result, indent=2)
    if args.output:
        pathlib.Path(args.output).write_text(output + "\n", encoding="utf-8")
    print(
        f"{args.label or args.results_dir}: "
        f"{result['total_outside_claimed_window']}/{result['total_checked']} segments "
        f"have >=1 anchor outside the claimed paragraph window "
        f"({result['total_anchors_outside_claimed_window']}/"
        f"{result['total_anchors_checked']} individual anchors outside; "
        f"{result['total_segments']} total segments seen)"
    )
    if not args.output:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
