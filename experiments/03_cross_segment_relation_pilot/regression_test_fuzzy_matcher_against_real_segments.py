"""WI-SEGMENT-0102: regression-test WI-SEGMENT-0072's unmodified
strict_local_fuzzy policy against every real, already-correctly-aligned
segment discovered in the repo.

This is a non-regression / no-op-invariance check, not a recovery-rate
measurement: for each real segment where the current exact/normalized
matcher already finds the correct (start_char, end_char), does the
looser strict_local_fuzzy policy ever produce a DIFFERENT match? A
"yes" is a stop condition (WI-SEGMENT-0059), not a tuning invitation.

Reuses `evaluate_near_miss_fuzzy_matching.accepted_match`/
`candidate_matches` completely unmodified - this script only discovers
real data, validates it as genuine ground truth, and calls the existing
policy. No production code or matcher parameters are touched.

DISCOVERY
---------
A repo-wide search (not just the two locations WI-SEGMENT-0102 was
originally scoped around) found real segment-schema data
(start_par_id/end_par_id/start_exact/end_exact/start_char/end_char) in:

- experiments/03_cross_segment_relation_pilot/results/segmentation_reliability/
  (WI-EVENT-0096's 17-story cohort)
- experiments/03_cross_segment_relation_pilot/results/segmentation_reliability_reworded_prompt/
  (WI-SEGMENT-0101's reworded-prompt run over the same cohort)
- experiments/03_cross_segment_relation_pilot/results/segmentation_paragraph_misnumbering_diagnostics/replay_fixture/
  (WI-SEGMENT-0071's replay fixture)
- lcats/experimental/annotation_feasibility_trial/source/trial/*/scenes.json
  (WI-ANNOTATE-0054's real trial output, story text co-located as
  story.json in the same directory)

Two other locations that matched a naive '"start_char"' grep were
checked and excluded: model_tiering_eval's `start_char` fields are
always `null` (stage-2/genre data, not segment offsets), and
science_fiction_analysis_trial's `evidence_sets[].records[].anchor` is a
different schema entirely (evidence-anchor spans, not segments) built
from `"backend": "fake"` synthetic fixture data, not real API output.

VALIDATION (why `outcome: included` alone is not enough)
---------------------------------------------------------
Per WI-SEGMENT-0102's own Problem/Context (the_secret_of_kralitz__kuttner
overlap case), every discovered segment is checked for (a) overlap with
another segment in the same story and (b) a start_exact/end_exact anchor
reused by another segment in the same story, before being trusted as
ground truth. A THIRD check was added after real data demanded it
(discovered during this item's own execution, not anticipated in the
WI's original acceptance criteria): the claimed
[start_par_id, end_par_id] paragraph window must actually CONTAIN the
segment's own recorded [start_char, end_char). Three stories in
annotation_feasibility_trial (love_of_life, story_of_keesh, brown_wolf -
the exact stories WI-SEGMENT-0059 named as pre-fix paragraph-collapse
casualties) have every segment's start_par_id/end_par_id stuck at (1, 1)
regardless of the segment's real character span, a symptom of the
single-newline paragraph-collapse bug WI-SEGMENT-0059 fixed. Some of
these segments' char spans do not even overlap each other, so overlap
detection alone would not catch them - but their paragraph metadata is
still corrupted, and using them as "ground truth" would search a
nonsensical window. This is reported as its own explicit finding, not
silently absorbed into the overlap-exclusion count.

A FOURTH check (review finding, PR #425) re-runs the current production
`text_segmenter.align_segment` over each structurally-valid segment and
excludes it if that does not reproduce the segment's own recorded
(start_char, end_char) exactly - structural validity alone does not
establish "currently correct," which is what a ground-truth control for
this item actually requires. 13 segments were excluded on this basis
alone that the first three checks would have accepted.

Sources are keyed by (source, story_id), not story_id alone: the same
story_id recurs across sources with genuinely different segment arrays
(different segmentation runs, e.g. the original vs. WI-SEGMENT-0101's
reworded-prompt cohort) - confirmed none are byte-identical duplicates -
so deduplicating by story_id alone silently dropped 52 real segments
(review finding, PR #425).
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any, Dict, List, Tuple

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lcats" / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import evaluate_near_miss_fuzzy_matching as fuzzy  # noqa: E402
from lcats.analysis import story_analysis  # noqa: E402
from lcats.analysis import text_segmenter  # noqa: E402

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
CORPORA_ROOT = REPO_ROOT / "corpora"

REQUIRED_SEGMENT_FIELDS = (
    "start_par_id",
    "end_par_id",
    "start_exact",
    "end_exact",
    "start_char",
    "end_char",
)


def _is_real_segment(seg: Any) -> bool:
    if not isinstance(seg, dict):
        return False
    for field in REQUIRED_SEGMENT_FIELDS:
        if field not in seg:
            return False
    start_char, end_char = seg.get("start_char"), seg.get("end_char")
    if not isinstance(start_char, int) or isinstance(start_char, bool):
        return False
    if not isinstance(end_char, int) or isinstance(end_char, bool):
        return False
    return start_char < end_char


def _segments_from_parsed_output(parsed_output: Any) -> List[Dict[str, Any]]:
    if isinstance(parsed_output, dict):
        candidate = parsed_output.get("segments")
    elif isinstance(parsed_output, list):
        candidate = parsed_output
    else:
        candidate = None
    if not isinstance(candidate, list):
        return []
    return [seg for seg in candidate if _is_real_segment(seg)]


def _story_text_from_corpora(story_id: str) -> str | None:
    path = CORPORA_ROOT / story_id / "story.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text("utf-8"))
    return text_segmenter.canonicalize_text(
        story_analysis.coerce_text(data.get("body", ""))
    )


def discover_sources() -> List[Tuple[str, str, str, List[Dict[str, Any]]]]:
    """Return (source_label, story_id, story_text, segments) tuples for
    every real, `outcome: included` story output discovered across all
    known real-data locations.

    Keyed by (source_label, story_id), NOT story_id alone: a story_id
    reused across sources (e.g. peace_manoeuvres__davis, present in
    segmentation_reliability, segmentation_reliability_reworded_prompt,
    and the replay_fixture) represents a genuinely distinct segmentation
    run per source - different prompt, different model call, a different
    segment array and count - not a duplicate of the same evidence
    (confirmed: no two sources ever produced byte-identical segment
    arrays for the same story_id). Deduplicating by story_id alone
    silently dropped 52 real segments from 5 stories' alternate runs
    (review finding, PR #425) - every committed real segmentation output
    must be evaluated, per this item's own acceptance criteria."""
    found: Dict[Tuple[str, str], Tuple[str, str, str, List[Dict[str, Any]]]] = {}

    reliability_dirs = [
        REPO_ROOT
        / "experiments/03_cross_segment_relation_pilot/results/segmentation_reliability",
        REPO_ROOT
        / "experiments/03_cross_segment_relation_pilot/results/segmentation_reliability_reworded_prompt",
        REPO_ROOT
        / "experiments/03_cross_segment_relation_pilot/results/segmentation_paragraph_misnumbering_diagnostics/replay_fixture",
    ]
    for base in reliability_dirs:
        if not base.exists():
            continue
        source_label = str(base.relative_to(REPO_ROOT))
        for f in sorted(base.rglob("*.json")):
            try:
                data = json.loads(f.read_text("utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(data, dict) or data.get("outcome") != "included":
                continue
            story_id = data.get("story_id")
            key = (source_label, story_id)
            if not story_id or key in found:
                continue
            segments = _segments_from_parsed_output(data.get("parsed_output"))
            if not segments:
                continue
            text = _story_text_from_corpora(story_id)
            if text is None:
                continue
            found[key] = (source_label, story_id, text, segments)

    trial_base = (
        REPO_ROOT / "lcats/experimental/annotation_feasibility_trial/source/trial"
    )
    if trial_base.exists():
        source_label = "annotation_feasibility_trial/source/trial"
        for story_dir in sorted(trial_base.iterdir()):
            if not story_dir.is_dir():
                continue
            scenes_path = story_dir / "scenes.json"
            story_path = story_dir / "story.json"
            if not scenes_path.exists() or not story_path.exists():
                continue
            story_id = f"annotation_feasibility_trial/{story_dir.name}"
            key = (source_label, story_id)
            if key in found:
                continue
            try:
                scenes_data = json.loads(scenes_path.read_text("utf-8"))
                story_data = json.loads(story_path.read_text("utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(scenes_data, dict) or not isinstance(story_data, dict):
                continue
            segments = [
                seg
                for seg in scenes_data.get("segments") or []
                if _is_real_segment(seg)
            ]
            if not segments:
                continue
            text = text_segmenter.canonicalize_text(
                story_analysis.coerce_text(story_data.get("body", ""))
            )
            found[key] = (source_label, story_id, text, segments)

    return list(found.values())


def validate_controls(
    text: str, segments: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Return (valid, excluded) - excluded entries carry a 'reason'."""
    _, index_meta = text_segmenter.paragraph_text_indexer(text)
    para_spans = index_meta["para_spans"]
    n = len(para_spans)

    if n == 0:
        return [], [
            {
                "segment_id": seg.get("segment_id"),
                "reasons": ["story has zero paragraphs - cannot validate any window"],
            }
            for seg in segments
        ]

    # Sweep by start_char, tracking the running max end_char seen in the
    # current overlapping cluster (review finding, PR #425): comparing
    # only ADJACENT pairs after sorting misses a segment that overlaps a
    # non-adjacent neighbor - e.g. A=(0,170) fully encloses both B=(5,20)
    # and C=(100,120), but B and C don't overlap each other, so a
    # sorted order of A, B, C would only ever compare (A,B) and (B,C),
    # never (A,C), silently accepting C as non-overlapping ground truth
    # even though it genuinely overlaps A. Extending the cluster's max
    # end_char (rather than resetting it to each new segment's own end)
    # keeps A's reach visible to every later segment in the same
    # cluster, not just its immediate successor.
    by_span = sorted(segments, key=lambda s: (s["start_char"], s["end_char"]))
    overlapping_ids = set()
    cluster: List[Dict[str, Any]] = []
    cluster_max_end = None
    for seg in by_span:
        if cluster and seg["start_char"] < cluster_max_end:
            cluster.append(seg)
            cluster_max_end = max(cluster_max_end, seg["end_char"])
            for member in cluster:
                overlapping_ids.add(id(member))
        else:
            cluster = [seg]
            cluster_max_end = seg["end_char"]

    anchor_counts: Dict[str, int] = {}
    for seg in segments:
        for anchor_field in ("start_exact", "end_exact"):
            anchor = seg.get(anchor_field) or ""
            if anchor:
                anchor_counts[anchor] = anchor_counts.get(anchor, 0) + 1
    reused_anchor_ids = set()
    for seg in segments:
        for anchor_field in ("start_exact", "end_exact"):
            anchor = seg.get(anchor_field) or ""
            if anchor and anchor_counts.get(anchor, 0) > 1:
                reused_anchor_ids.add(id(seg))

    valid: List[Dict[str, Any]] = []
    excluded: List[Dict[str, Any]] = []
    for seg in segments:
        reasons = []
        if id(seg) in overlapping_ids:
            reasons.append("overlaps an adjacent segment in the same story")
        if id(seg) in reused_anchor_ids:
            reasons.append("shares a start_exact/end_exact anchor with another segment")

        sp, ep = seg["start_par_id"], seg["end_par_id"]
        if (
            isinstance(sp, int)
            and isinstance(ep, int)
            and not isinstance(sp, bool)
            and not isinstance(ep, bool)
        ):
            sp_c = max(1, min(sp, n)) - 1
            ep_c = max(1, min(ep, n)) - 1
            if ep_c < sp_c:
                ep_c = sp_c
            lo, hi = para_spans[sp_c][0], para_spans[ep_c][1]
            if not (lo <= seg["start_char"] and seg["end_char"] <= hi):
                reasons.append(
                    "paragraph window derived from start_par_id/end_par_id does not "
                    "contain the segment's own recorded (start_char, end_char) - "
                    "likely pre-WI-SEGMENT-0059 collapsed-paragraph data"
                )
            else:
                # Fourth check (review finding, PR #425): structural
                # validity (non-overlap, non-reused anchor, window
                # containment) does not by itself establish that the
                # CURRENT production matcher still reproduces this
                # segment's recorded offsets - re-running
                # align_segment directly is the only way to confirm
                # "currently-correct," which is what this item's own
                # acceptance criteria require of a ground-truth control.
                reproduced = text_segmenter.align_segment(
                    text,
                    para_spans,
                    sp,
                    ep,
                    seg.get("start_exact") or "",
                    seg.get("end_exact") or "",
                )
                if reproduced != (seg["start_char"], seg["end_char"]):
                    reasons.append(
                        "current production align_segment does not reproduce this "
                        "segment's recorded (start_char, end_char) - not a "
                        "currently-correct control"
                    )
        else:
            reasons.append("start_par_id/end_par_id missing or malformed")

        if reasons:
            excluded.append({"segment_id": seg.get("segment_id"), "reasons": reasons})
        else:
            valid.append(seg)

    return valid, excluded


def load_default_policy() -> fuzzy.Policy:
    """Load WI-SEGMENT-0072's frozen strict_local_fuzzy policy from its
    own committed fixture, unmodified - never redefined here, per
    WI-SEGMENT-0102's forbidden_actions."""
    fixture = json.loads(pathlib.Path(fuzzy.DEFAULT_FIXTURE).read_text("utf-8"))
    return fuzzy._policy_from_fixture(fixture)


def check_segment(
    para_spans: List[tuple], text: str, policy: fuzzy.Policy, seg: Dict[str, Any]
) -> Dict[str, Any]:
    # Clamp identically to validate_controls's own window computation
    # (and to text_segmenter.align_segment's real clamping) - a segment
    # that passed validation was checked against this same clamped
    # window, so re-deriving it here must match exactly, not just
    # subtract 1 from the raw (possibly out-of-range) par_id values.
    n = len(para_spans)
    if n == 0:
        return {
            "segment_id": seg.get("segment_id"),
            "start": {"fuzzy_matched": False, "agrees": None},
            "end": {"fuzzy_matched": False, "agrees": None},
        }
    sp = max(1, min(seg["start_par_id"], n)) - 1
    ep = max(1, min(seg["end_par_id"], n)) - 1
    if ep < sp:
        ep = sp
    lo, hi = para_spans[sp][0], para_spans[ep][1]

    # Mirror align_segment's real two-step search exactly (review finding,
    # PR #425, 2nd self-review round): production searches end_exact
    # within [s_idx, hi) - starting from wherever start_exact was ACTUALLY
    # found - not within [lo, hi) again. Comparing the end anchor's fuzzy
    # match against a production search over the wider [lo, hi) window
    # could misclassify required_fuzzy_tolerance if end_exact's text also
    # happens to occur earlier, in [lo, s_idx). No case in the current
    # real inventory triggers this (verified directly: s_idx == lo for
    # every validated segment's start anchor), but the comparison must be
    # structurally correct, not incidentally correct for today's data.
    start_anchor = seg.get("start_exact") or ""
    if start_anchor.strip():
        start_production_span = text_segmenter._locate_anchor_span(
            text, start_anchor, lo, hi
        )
        s_idx = start_production_span[0] if start_production_span else lo
    else:
        s_idx = lo

    report: Dict[str, Any] = {"segment_id": seg.get("segment_id")}
    for anchor_field, offset_field, side in (
        ("start_exact", "start_char", "start"),
        ("end_exact", "end_char", "end"),
    ):
        anchor = seg.get(anchor_field) or ""
        expected = seg[offset_field]
        match = fuzzy.accepted_match(text, anchor, lo, hi, policy)
        if match is None:
            report[side] = {"fuzzy_matched": False, "agrees": None}
            continue
        actual = match.start if side == "start" else match.end
        # Per acceptance criterion 2: report when the fuzzy match differs
        # from, or is more permissive than, the CURRENT exact/normalized
        # result - which is production's _locate_anchor_span (case,
        # typography, and whitespace-run tolerant), not a raw byte-exact
        # substring check. A byte-exact comparison overstated how often
        # fuzzy tolerance added anything beyond what production's own
        # normalized fallback already reaches (review finding, PR #425:
        # 32 of 44 originally-flagged "required tolerance" cases were
        # already reproduced by _locate_anchor_span at the identical
        # span).
        prod_lo = lo if side == "start" else s_idx
        production_span = text_segmenter._locate_anchor_span(text, anchor, prod_lo, hi)
        required_fuzzy_tolerance = production_span != (match.start, match.end)
        report[side] = {
            "fuzzy_matched": True,
            "fuzzy_offset": actual,
            "expected_offset": expected,
            "agrees": actual == expected,
            "required_fuzzy_tolerance": required_fuzzy_tolerance,
        }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    policy = load_default_policy()
    sources = discover_sources()
    total_segments = 0
    total_excluded = 0
    exclusion_reasons: Dict[str, int] = {}
    total_valid = 0
    total_agree_both = 0
    total_required_fuzzy_tolerance = 0
    disagreements: List[Dict[str, Any]] = []
    fuzzy_tolerance_cases: List[Dict[str, Any]] = []
    # Anchor-level counts (review finding, PR #425): a segment-level
    # "disagreement" bucket hides a wrong-offset anchor whenever the
    # OTHER anchor on the same segment has no match at all - counting
    # per anchor, not per segment, is the only way every wrong-offset
    # case is actually reported (acceptance criterion 2's "any case...
    # is reported explicitly, not silently absorbed").
    total_no_match_anchors = 0
    total_wrong_offset_anchors = 0
    wrong_offset_anchors: List[Dict[str, Any]] = []
    per_source: Dict[str, Any] = {}

    for source_label, story_id, text, segments in sources:
        valid, excluded = validate_controls(text, segments)
        total_segments += len(segments)
        total_excluded += len(excluded)
        for ex in excluded:
            for reason in ex["reasons"]:
                exclusion_reasons[reason] = exclusion_reasons.get(reason, 0) + 1

        _, index_meta = text_segmenter.paragraph_text_indexer(text)
        para_spans = index_meta["para_spans"]

        story_checks = []
        for seg in valid:
            total_valid += 1
            check = check_segment(para_spans, text, policy, seg)
            both_agree = check["start"].get("agrees") and check["end"].get("agrees")
            if both_agree:
                total_agree_both += 1
            else:
                disagreements.append(
                    {"source": source_label, "story_id": story_id, **check}
                )
            for side in ("start", "end"):
                side_report = check.get(side, {})
                if side_report.get("fuzzy_matched") is False:
                    total_no_match_anchors += 1
                elif side_report.get("agrees") is False:
                    total_wrong_offset_anchors += 1
                    wrong_offset_anchors.append(
                        {
                            "source": source_label,
                            "story_id": story_id,
                            "segment_id": seg.get("segment_id"),
                            "side": side,
                            **side_report,
                        }
                    )
                if side_report.get("required_fuzzy_tolerance"):
                    total_required_fuzzy_tolerance += 1
                    fuzzy_tolerance_cases.append(
                        {
                            "source": source_label,
                            "story_id": story_id,
                            "segment_id": seg.get("segment_id"),
                            "side": side,
                            **side_report,
                        }
                    )
            story_checks.append(check)

        per_source.setdefault(source_label, []).append(
            {
                "story_id": story_id,
                "total_segments": len(segments),
                "excluded": len(excluded),
                "exclusion_detail": excluded,
                "validated": len(valid),
                "checks": story_checks,
            }
        )

    result = {
        "total_segments_discovered": total_segments,
        "total_excluded": total_excluded,
        "exclusion_reasons": exclusion_reasons,
        "total_validated": total_valid,
        "total_agree_both_anchors": total_agree_both,
        "total_disagreements": len(disagreements),
        "disagreements": disagreements,
        "total_no_match_anchors": total_no_match_anchors,
        "total_wrong_offset_anchors": total_wrong_offset_anchors,
        "wrong_offset_anchors": wrong_offset_anchors,
        "total_required_fuzzy_tolerance": total_required_fuzzy_tolerance,
        "fuzzy_tolerance_cases": fuzzy_tolerance_cases,
        "per_source": per_source,
    }

    output = json.dumps(result, indent=2)
    if args.output:
        pathlib.Path(args.output).write_text(output + "\n", encoding="utf-8")
    print(
        f"Discovered {total_segments} real segments across {len(sources)} "
        f"(source, story) outputs; "
        f"{total_excluded} excluded as invalid controls; "
        f"{total_valid} validated; "
        f"{total_agree_both} agree exactly on both anchors; "
        f"{len(disagreements)} segment-level disagreements "
        f"({total_no_match_anchors} no-match anchors, "
        f"{total_wrong_offset_anchors} wrong-offset anchors)"
    )
    if not args.output:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
