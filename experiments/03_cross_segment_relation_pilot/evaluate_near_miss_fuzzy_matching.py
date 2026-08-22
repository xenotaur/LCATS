"""Evaluate safe fuzzy matching for near-miss segmentation anchors.

This is an offline WI-SEGMENT-0072 experiment. It reads committed
parsed_output/source-text fixtures, evaluates a candidate fuzzy policy, and
reports recovery and false-positive counts. It does not change production
alignment behavior and makes no LLM calls.
"""

from __future__ import annotations

import argparse
import dataclasses
import difflib
import json
import pathlib
import re
import sys
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lcats" / "src"))

from lcats.analysis import story_analysis
from lcats.analysis import text_segmenter

DEFAULT_FIXTURE = (
    pathlib.Path(__file__).parent
    / "fixtures"
    / ("wi_segment_0072_near_miss_fuzzy_cases.json")
)


@dataclasses.dataclass(frozen=True)
class Policy:
    """A deliberately strict local fuzzy policy candidate."""

    name: str
    max_edit_distance: int
    min_similarity_ratio: float
    min_contiguous_run_ratio: float
    uniqueness_margin: float


@dataclasses.dataclass(frozen=True)
class CandidateMatch:
    start: int
    end: int
    text: str
    edit_distance: int
    similarity_ratio: float
    contiguous_run_ratio: float


def _read_json(path: pathlib.Path) -> Any:
    return json.loads(path.read_text("utf-8"))


def _story_text(path: pathlib.Path) -> str:
    data = _read_json(path)
    return text_segmenter.canonicalize_text(
        story_analysis.coerce_text(data.get("body", ""))
    )


def _paragraph_range(text: str, start_par_id: int, end_par_id: int) -> tuple[int, int]:
    _, index_meta = text_segmenter.paragraph_text_indexer(text)
    spans = index_meta["para_spans"]
    sp = max(1, min(start_par_id, len(spans))) - 1
    ep = max(1, min(end_par_id, len(spans))) - 1
    ep = max(ep, sp)
    return spans[sp][0], spans[ep][1]


def _collapse_ws(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _token_spans(anchor: str) -> list[tuple[str, int, int]]:
    return [
        (match.group(0), match.start(), match.end())
        for match in re.finditer(r"[A-Za-z][A-Za-z']+", anchor)
    ]


def _levenshtein(left: str, right: str) -> int:
    """Return Levenshtein edit distance for short evaluated snippets."""
    if left == right:
        return 0
    if len(left) < len(right):
        left, right = right, left
    previous = list(range(len(right) + 1))
    for i, lchar in enumerate(left, start=1):
        current = [i]
        for j, rchar in enumerate(right, start=1):
            current.append(
                min(
                    previous[j] + 1,
                    current[j - 1] + 1,
                    previous[j - 1] + (lchar != rchar),
                )
            )
        previous = current
    return previous[-1]


def _score(anchor: str, candidate: str, start: int) -> CandidateMatch:
    normalized_anchor = _collapse_ws(anchor)
    normalized_candidate = _collapse_ws(candidate)
    matcher = difflib.SequenceMatcher(
        None, normalized_anchor, normalized_candidate, autojunk=False
    )
    longest = matcher.find_longest_match(
        0, len(normalized_anchor), 0, len(normalized_candidate)
    ).size
    return CandidateMatch(
        start=start,
        end=start + len(candidate),
        text=candidate,
        edit_distance=_levenshtein(normalized_anchor, normalized_candidate),
        similarity_ratio=matcher.ratio(),
        contiguous_run_ratio=longest / max(1, len(normalized_anchor)),
    )


def candidate_matches(text: str, anchor: str, lo: int, hi: int) -> list[CandidateMatch]:
    """Return plausible fuzzy candidates within the claimed paragraph range."""
    window = text[lo:hi]
    anchor_len = len(anchor)
    candidates: dict[tuple[int, int], CandidateMatch] = {}
    anchors = _token_spans(anchor)
    if not anchors:
        return []
    ngrams: list[tuple[str, int]] = []
    for width in (5, 4, 3):
        for idx in range(0, max(0, len(anchors) - width + 1)):
            parts = [re.escape(token) for token, _, _ in anchors[idx : idx + width]]
            ngrams.append((r"\s+".join(parts), anchors[idx][1]))
        if ngrams:
            break

    for pattern, anchor_offset in ngrams[:24]:
        for match in re.finditer(pattern, window, flags=re.IGNORECASE):
            local_start_base = max(0, match.start() - anchor_offset)
            for start_delta in (-2, -1, 0, 1, 2):
                local_start = max(0, local_start_base + start_delta)
                for length_delta in range(-4, 5):
                    local_end = min(
                        len(window), local_start + anchor_len + length_delta
                    )
                    if local_end <= local_start:
                        continue
                    key = (lo + local_start, lo + local_end)
                    if key not in candidates:
                        candidates[key] = _score(
                            anchor, window[local_start:local_end], key[0]
                        )
    return sorted(
        candidates.values(),
        key=lambda item: (
            item.edit_distance,
            -item.similarity_ratio,
            -item.contiguous_run_ratio,
            item.text[:1].isspace(),
            abs(len(item.text) - len(anchor)),
            item.start,
        ),
    )


def _is_unique_enough(matches: list[CandidateMatch], policy: Policy) -> bool:
    if len(matches) < 2:
        return True
    best = matches[0]
    for candidate in matches[1:]:
        overlap = max(
            0, min(best.end, candidate.end) - max(best.start, candidate.start)
        )
        union = max(best.end, candidate.end) - min(best.start, candidate.start)
        if union and overlap / union >= 0.9:
            continue
        if (
            best.similarity_ratio - candidate.similarity_ratio
            < policy.uniqueness_margin
        ):
            return False
    return True


def accepted_match(
    text: str, anchor: str, lo: int, hi: int, policy: Policy
) -> CandidateMatch | None:
    """Return the accepted fuzzy match, or None if the policy rejects it."""
    matches = candidate_matches(text, anchor, lo, hi)
    if not matches:
        return None
    best = matches[0]
    if best.edit_distance > policy.max_edit_distance:
        return None
    if best.similarity_ratio < policy.min_similarity_ratio:
        return None
    if best.contiguous_run_ratio < policy.min_contiguous_run_ratio:
        return None
    if not _is_unique_enough(matches, policy):
        return None
    return best


def _positive_anchor(case: dict[str, Any]) -> tuple[str, int, int]:
    record = _read_json(pathlib.Path(case["parsed_output_path"]))
    segment = next(
        item
        for item in record["parsed_output"]["segments"]
        if item["segment_id"] == case["segment_id"]
    )
    return segment[case["anchor_field"]], segment["start_par_id"], segment["end_par_id"]


def _policy_from_fixture(fixture: dict[str, Any]) -> Policy:
    raw = fixture["candidate_policy"]
    return Policy(
        name=raw["name"],
        max_edit_distance=raw["max_edit_distance"],
        min_similarity_ratio=raw["min_similarity_ratio"],
        min_contiguous_run_ratio=raw["min_contiguous_run_ratio"],
        uniqueness_margin=raw["uniqueness_margin"],
    )


def evaluate_fixture(fixture_path: pathlib.Path = DEFAULT_FIXTURE) -> dict[str, Any]:
    fixture_path = fixture_path.resolve()
    fixture = _read_json(fixture_path)
    policy = _policy_from_fixture(fixture)
    positive_results = []
    negative_results = []

    for case in fixture["positive_cases"]:
        text = _story_text(pathlib.Path(case["story_path"]))
        anchor, start_par_id, end_par_id = _positive_anchor(case)
        lo, hi = _paragraph_range(text, start_par_id, end_par_id)
        match = accepted_match(text, anchor, lo, hi, policy)
        expected = case["expected_source_text"]
        expected_start = case["expected_span_start"]
        expected_end = expected_start + len(expected)
        recovered = (
            match is not None
            and match.start == expected_start
            and match.end == expected_end
            and match.text == expected
        )
        positive_results.append(
            {
                "case_id": case["case_id"],
                "expected": True,
                "expected_span_start": expected_start,
                "expected_span_end": expected_end,
                "matched": match is not None,
                "recovered_expected_span": recovered,
                "match": dataclasses.asdict(match) if match else None,
            }
        )

    for case in fixture["negative_cases"]:
        text = _story_text(pathlib.Path(case["story_path"]))
        lo, hi = _paragraph_range(text, case["start_par_id"], case["end_par_id"])
        match = accepted_match(text, case["anchor_text"], lo, hi, policy)
        negative_results.append(
            {
                "case_id": case["case_id"],
                "expected": False,
                "matched": match is not None,
                "false_positive": match is not None,
                "match": dataclasses.asdict(match) if match else None,
            }
        )

    positives = len(positive_results)
    negatives = len(negative_results)
    recovered = sum(1 for item in positive_results if item["recovered_expected_span"])
    false_positives = sum(1 for item in negative_results if item["false_positive"])
    try:
        fixture_label = str(fixture_path.relative_to(pathlib.Path.cwd()))
    except ValueError:
        fixture_label = str(fixture_path)
    return {
        "fixture": fixture_label,
        "policy": dataclasses.asdict(policy),
        "positive_total": positives,
        "positive_recovered": recovered,
        "positive_recovery_rate": recovered / positives if positives else None,
        "negative_total": negatives,
        "negative_false_positives": false_positives,
        "negative_false_positive_rate": (
            false_positives / negatives if negatives else None
        ),
        "positive_results": positive_results,
        "negative_results": negative_results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", default=str(DEFAULT_FIXTURE))
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    result = evaluate_fixture(pathlib.Path(args.fixture))
    output = json.dumps(result, indent=2)
    if args.output:
        pathlib.Path(args.output).write_text(output + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
