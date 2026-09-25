"""Resolve pilot_stories.jsonl's 17 story_ids to current corpora/ paths.

WHY THIS EXISTS
----------------
WI-EVENT-0096 needs to re-run the exact original 65% (11/17) baseline
cohort through check_segmentation_reliability.py's --story-list flag. The
committed results/pilot_stories.jsonl records each story's bare story_id
(collection-agnostic slug) and a now-stale `path` field (a retired
lcats/data/... layout that no longer exists in this repo). This script
resolves each story_id to its current, unique corpora/<collection>/<slug>
directory by globbing corpora/*/<slug> - unique per PROP-LCATS-STORY-
BUCKET-LAYOUT Decision 2 (a directory slug is only guaranteed unique per
collection, but this repo's corpora/ has no cross-collection slug
collisions among this specific 17-story cohort, verified below) - and
writes one resolved directory path per line, in the format
check_segmentation_reliability.py's --story-list already documents.

Fails loudly (raises) rather than silently on a zero-match or multi-match
story_id, since a silent skip or an arbitrary pick would corrupt the
before/after comparison this measurement exists to produce.

USAGE
-----
    python experiments/03_cross_segment_relation_pilot/resolve_baseline_story_list.py \
        --pilot-stories experiments/03_cross_segment_relation_pilot/results/pilot_stories.jsonl \
        --corpora-dir corpora \
        --output experiments/03_cross_segment_relation_pilot/results/segmentation_reliability/baseline_story_list.txt
"""

from __future__ import annotations

import argparse
import json
import pathlib


def resolve_story_ids(
    pilot_stories_path: pathlib.Path, corpora_dir: pathlib.Path
) -> list[pathlib.Path]:
    """Return each pilot_stories.jsonl row's story_id resolved to its
    current corpora/<collection>/<slug> directory, in file order.

    Streams the JSONL line-by-line rather than loading it all at once - a
    malformed or story_id-less line raises a ValueError naming the exact
    line number and content, not an unhelpful bare KeyError/JSONDecodeError,
    matching this resolver's "fail loudly" design (review finding, PR #398).
    """
    resolved = []
    with pilot_stories_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{pilot_stories_path}:{line_number}: invalid JSON ({exc})"
                ) from exc
            if "story_id" not in row:
                raise ValueError(
                    f"{pilot_stories_path}:{line_number}: row is missing 'story_id': {row!r}"
                )
            story_id = row["story_id"]
            matches = sorted(corpora_dir.glob(f"*/{story_id}"))
            if len(matches) != 1:
                raise ValueError(
                    f"{pilot_stories_path}:{line_number}: story_id {story_id!r} "
                    f"resolved to {len(matches)} directories under {corpora_dir} "
                    f"(expected exactly 1): {matches}"
                )
            resolved.append(matches[0])
    return resolved


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pilot-stories",
        type=pathlib.Path,
        default=pathlib.Path(
            "experiments/03_cross_segment_relation_pilot/results/pilot_stories.jsonl"
        ),
    )
    parser.add_argument(
        "--corpora-dir", type=pathlib.Path, default=pathlib.Path("corpora")
    )
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=pathlib.Path(
            "experiments/03_cross_segment_relation_pilot/results/segmentation_reliability/baseline_story_list.txt"
        ),
    )
    args = parser.parse_args()

    resolved = resolve_story_ids(args.pilot_stories, args.corpora_dir)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Resolved from pilot_stories.jsonl's 17 story_ids (WI-EVENT-0096) -",
        "# the exact 65% (11/17) parsing_error baseline cohort, not a fresh sample.",
    ]
    lines.extend(str(path) for path in resolved)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Resolved {len(resolved)} story paths -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
