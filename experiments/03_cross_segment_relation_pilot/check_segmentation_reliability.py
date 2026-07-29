"""Measure Stage-1 segmentation reliability only (WI-EVENT-0033 verification).

WHY THIS EXISTS, AND WHY IT ISN'T run_pilot.py
----------------------------------------------
WI-EVENT-0033's acceptance criterion asks whether schema-hardening
`scene_analysis.make_segment_extractor` reduced the segmentation exclusion
rate observed live during WI-EVENT-0030 dogfooding (11 of 17 sampled
stories, 65%, with `--model claude-haiku-4-5-20251001`).

That is a *Stage-1* metric, and `run_pilot.run_story()` early-returns on a
segmentation failure before ever entering the Event-Role-World pipeline
(`run_pilot.py`'s `return row, []` in its `if seg_error or not segments:`
branch). So the measurement needs exactly ONE LLM call per story - roughly
20 calls total - whereas a `run_pilot.py --sample-size 5` run costs several
hundred (1 genre-detect call per candidate scanned, plus 1 segmentation +
4-per-segment + 1 story-level call per sampled story).

`run_pilot.py` is also currently frozen pending the pipelining work: it
accumulates all results in memory and writes only after its whole per-story
loop finishes, so a crash (or Ctrl-C, which is not an `Exception` subclass
and so escapes its catch-all) discards every already-paid-for result. This
script deliberately avoids all of that: it writes each story's outcome,
including the raw LLM output, to its own file immediately, so an
interrupted run keeps everything it already paid for and can be re-run
over the remainder.

READING THE RESULT
------------------
Do NOT compare `parsing_error` counts. On the `tool_schema` path
`llm_extractor.extract()` sets `parsing_error = None` unconditionally
("there is no JSON-text parse step"), so a post-fix `parsing_error` rate is
0% by construction - a tautology, not evidence. This script instead reports
the *segmentation exclusion rate for any cause*, broken down by cause,
which is the honest comparison against the 65% baseline.

USAGE
-----
Needs a real API key (see `lcats/docs/secrets-setup.md`); costs ~1 LLM call
per story. Run from the repo root with the conda environment active:

    python experiments/03_cross_segment_relation_pilot/check_segmentation_reliability.py \
        --data-dir corpora --sample-size 20 --model claude-haiku-4-5-20251001 \
        --output /tmp/segmentation_reliability

`--model` defaults to the baseline's `claude-haiku-4-5-20251001` so the
comparison is like-for-like; the cheaper model is what exposed the failure.
`--seed` reuses `run_pilot._iter_candidate_files`'s shuffle convention, so a
given seed selects a reproducible story set.
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lcats" / "src"))

from lcats.analysis import scene_analysis
from lcats.analysis import story_analysis
from lcats.utils.secrets import load_secrets


def classify(result: dict, segments: list) -> str:
    """Return "included", or a short label naming why the story was excluded.

    Prefers the api_error's `category` (which distinguishes rate_limit /
    server / context_length / truncated_output - the transient-vs-fatal
    distinction that matters most when reading the result), but falls back
    to `code` when category is "unknown", since that is what an
    empty_tool_result reports and "unknown" alone would hide it.
    """
    api_error = result.get("api_error")
    if api_error:
        category = api_error.get("category") or "unknown"
        label = api_error.get("code") if category == "unknown" else category
        return f"api_error:{label or 'unknown'}"
    if result.get("extraction_error"):
        return f"extraction_error:{result['extraction_error']}"
    if not segments:
        return "no_segments"
    return "included"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--data-dir", default="corpora")
    parser.add_argument("--sample-size", type=int, default=20)
    parser.add_argument("--model", default="claude-haiku-4-5-20251001")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default="/tmp/segmentation_reliability")
    args = parser.parse_args()

    load_secrets()
    from lcats.llm import anthropic_backend

    output_dir = pathlib.Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(pathlib.Path(args.data_dir).rglob("*.json"))
    random.Random(args.seed).shuffle(files)
    files = files[: args.sample_size]
    if not files:
        print(f"error: no stories found under {args.data_dir}", file=sys.stderr)
        return 1

    extractor = scene_analysis.make_segment_extractor(
        anthropic_backend.AnthropicBackend()
    )
    counts: collections.Counter = collections.Counter()

    for i, path in enumerate(files, 1):
        body = story_analysis.coerce_text(
            json.loads(path.read_text("utf-8")).get("body", "")
        )
        result = extractor.extract(body, model_name=args.model)
        segments = result.get("extracted_output") or []
        outcome = classify(result, segments)
        counts[outcome] += 1
        # Persist immediately, including the raw LLM output, so an
        # interrupted run keeps every already-paid-for result.
        (output_dir / f"{path.stem}.json").write_text(
            json.dumps(
                {
                    "story_id": path.stem,
                    "outcome": outcome,
                    "segment_count": len(segments),
                    "llm_output": result.get("extracted_output"),
                    "api_error": result.get("api_error"),
                    "extraction_error": result.get("extraction_error"),
                    "usage": result.get("usage"),
                },
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )
        print(f"[{i}/{len(files)}] {path.stem}: {outcome} ({len(segments)} segments)")

    total = sum(counts.values())
    excluded = total - counts["included"]
    print(f"\nLLM calls made: {total} (1 per story)")
    print(f"Exclusion rate: {excluded}/{total} ({excluded / total:.0%})")
    print("  baseline was: 11/17 (65%) with claude-haiku-4-5-20251001")
    print("Breakdown by cause:")
    for cause, n in counts.most_common():
        print(f"  {n:>3}  {cause}")
    print(f"\nPer-story output (incl. raw LLM output): {output_dir}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
