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
script deliberately avoids all of that: it writes each story's outcome to
its own file immediately, and skips any story whose output file already
exists on a subsequent run (see RESUMING below).

ABOUT THE COHORT (review finding, PR #189)
-------------------------------------------
The 65% baseline came from `run_pilot.py`'s genre-detected, stratified
`build_stratified_sample()` - not from a shuffle over all of `corpora/`.
That baseline's exact story list was never persisted anywhere in this repo
(confirmed: no `pilot_stories.jsonl` survives from any real run), so this
script CANNOT reproduce the literal baseline cohort. Reproducing the
original stratified *procedure* would cost ~200 genre-detection calls
(measured separately), defeating this script's entire purpose.

This is a real, honest limitation, not swept under the rug: a shuffle-based
sample can differ from the baseline in genre mix and story length, and
either could independently affect the exclusion rate. Two mitigations:

  1. `--story-list FILE` accepts an explicit list of story paths (one per
     line, `#`-prefixed lines ignored) if you have a specific cohort in
     mind - e.g. from a future run_pilot.py run whose sample IS persisted.
  2. Absent `--story-list`, the report always includes the sampled
     cohort's word-count distribution, so a large rate change can be
     sanity-checked against whether the cohort skewed unusually
     short/long relative to the corpus median (per
     `estimate_stage2.py`-style stats: corpora/ overall median is ~4,881
     words - not hardcoded here since the actual sampled cohort is what
     matters for this run).

Treat a shuffle-sampled result as suggestive, not as a strictly controlled
before/after comparison - and prefer `--story-list` when a real comparison
matters.

READING THE RESULT
------------------
Do NOT compare `parsing_error` counts. On the `tool_schema` path
`llm_extractor.extract()` sets `parsing_error = None` unconditionally
("there is no JSON-text parse step"), so a post-fix `parsing_error` rate is
0% by construction - a tautology, not evidence. This script instead reports
the *segmentation exclusion rate for any cause*, broken down by cause,
which is the honest comparison against the 65% baseline. The exclusion
rate's denominator is stories that actually reached an extraction attempt
(`llm_calls_made`), not the raw sample size - a story skipped for an
unreadable file or empty body never made a call and would otherwise
silently understate the rate (or, worse, divide by zero if every sampled
file were unreadable).

If a batch-fatal error is hit (bad/expired API key, exhausted account
balance - `api_error.get("should_abort_batch")` on the classified error),
the run stops immediately rather than reporting every remaining story as
"excluded", which would otherwise look like a real reliability finding
instead of an account problem.

RESUMING
--------
Re-running the same command with the same `--output` skips any story whose
output file already exists, regardless of that story's prior outcome (a
completed failure, like a completed success, does not need re-computation
here - this script does not retry). Delete specific files under `--output`
to force re-running just those stories, or pass a fresh `--output` to start
clean.

USAGE
-----
Needs a real API key (see `lcats/docs/secrets-setup.md`); costs ~1 LLM call
per story that hasn't already been persisted. Run from the repo root with
the conda environment active:

    python experiments/03_cross_segment_relation_pilot/check_segmentation_reliability.py \
        --data-dir corpora --sample-size 20 --model claude-haiku-4-5-20251001 \
        --output /tmp/segmentation_reliability

`--model` defaults to the baseline's `claude-haiku-4-5-20251001` so the
comparison is like-for-like; the cheaper model is what exposed the failure.
`--seed` reuses `run_pilot._iter_candidate_files`'s shuffle convention, so a
given seed selects a reproducible story set (subject to the COHORT caveat
above). Pass `--story-list FILE` instead of `--data-dir`/`--sample-size`/
`--seed` to use an explicit cohort.
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import random
import statistics
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


def select_files(args) -> list[pathlib.Path]:
    """Return the story files to run, per --story-list or the shuffle sample."""
    if args.story_list:
        lines = pathlib.Path(args.story_list).read_text("utf-8").splitlines()
        return [
            pathlib.Path(line.strip())
            for line in lines
            if line.strip() and not line.strip().startswith("#")
        ]
    files = sorted(pathlib.Path(args.data_dir).rglob("*.json"))
    random.Random(args.seed).shuffle(files)
    return files[: args.sample_size]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--data-dir", default="corpora")
    parser.add_argument("--sample-size", type=int, default=20)
    parser.add_argument("--model", default="claude-haiku-4-5-20251001")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default="/tmp/segmentation_reliability")
    parser.add_argument(
        "--story-list",
        default=None,
        help=(
            "Path to a text file of explicit story paths (one per line, "
            "'#'-prefixed lines ignored), used instead of --data-dir/"
            "--sample-size/--seed's shuffle sample. See ABOUT THE COHORT."
        ),
    )
    args = parser.parse_args()

    load_secrets()
    from lcats.llm import anthropic_backend

    output_dir = pathlib.Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    files = select_files(args)
    if not files:
        print("error: no stories selected", file=sys.stderr)
        return 1

    extractor = scene_analysis.make_segment_extractor(
        anthropic_backend.AnthropicBackend()
    )
    counts: collections.Counter = collections.Counter()
    llm_calls_made = 0
    word_counts: list[int] = []

    for i, path in enumerate(files, 1):
        result_path = output_dir / f"{path.stem}.json"
        if result_path.exists():
            cached = json.loads(result_path.read_text("utf-8"))
            counts[cached["outcome"]] += 1
            if cached.get("llm_call_made"):
                llm_calls_made += 1
            if cached.get("word_count") is not None:
                word_counts.append(cached["word_count"])
            print(f"[{i}/{len(files)}] {path.stem}: {cached['outcome']} (cached)")
            continue

        try:
            data = json.loads(path.read_text("utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            outcome = "story_json_error"
            record = {
                "story_id": path.stem,
                "outcome": outcome,
                "llm_call_made": False,
                "word_count": None,
                "error": f"{type(exc).__name__}: {exc}",
            }
            counts[outcome] += 1
            result_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
            print(f"[{i}/{len(files)}] {path.stem}: {outcome}")
            continue

        body = story_analysis.coerce_text(data.get("body", ""))
        word_count = len(body.split())
        if not body.strip():
            outcome = "empty_story_body"
            record = {
                "story_id": path.stem,
                "outcome": outcome,
                "llm_call_made": False,
                "word_count": word_count,
            }
            counts[outcome] += 1
            result_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
            print(f"[{i}/{len(files)}] {path.stem}: {outcome}")
            continue

        result = extractor.extract(body, model_name=args.model)
        llm_calls_made += 1
        word_counts.append(word_count)
        api_error = result.get("api_error")
        segments = result.get("extracted_output") or []
        outcome = classify(result, segments)
        counts[outcome] += 1
        # Persist immediately - both raw_output (empty for this extractor:
        # AnthropicBackend.complete() sets text="" on the tool-use path, so
        # this is included for completeness/symmetry with json_object-mode
        # extractors, not because it holds content here) and
        # extracted_output (the actual parsed tool result, useful for
        # debugging a non-"included" outcome) - so an interrupted run keeps
        # every already-paid-for result.
        record = {
            "story_id": path.stem,
            "outcome": outcome,
            "llm_call_made": True,
            "word_count": word_count,
            "segment_count": len(segments),
            "raw_output": result.get("raw_output"),
            "extracted_output": result.get("extracted_output"),
            "api_error": api_error,
            "extraction_error": result.get("extraction_error"),
            "usage": result.get("usage"),
        }
        result_path.write_text(
            json.dumps(record, indent=2, default=str), encoding="utf-8"
        )
        print(f"[{i}/{len(files)}] {path.stem}: {outcome} ({len(segments)} segments)")

        if api_error and api_error.get("should_abort_batch"):
            print(
                f"\nfatal: {path.name}: {api_error.get('message', api_error)}",
                file=sys.stderr,
            )
            print(
                "Aborting - this looks like a bad/expired API key or an "
                "exhausted account balance/quota, not a per-story problem. "
                "Every remaining story would fail identically, and "
                "reporting them as 'excluded' would misrepresent an "
                "account problem as a segmentation reliability finding. "
                "Results gathered so far are still persisted under "
                f"{output_dir}/.",
                file=sys.stderr,
            )
            break

    print(f"\nStories sampled: {len(files)}")
    print(f"LLM calls made: {llm_calls_made}")
    if llm_calls_made:
        # Exclusion rate's denominator is stories that actually reached an
        # extraction attempt - story_json_error/empty_story_body are
        # file-level problems, not segmentation-reliability signal, and
        # would otherwise silently understate the rate (or divide by zero
        # if every sampled file were unreadable).
        denom = llm_calls_made
        excluded_of_attempted = denom - counts["included"]
        print(
            f"Exclusion rate (of {denom} stories that reached extraction): "
            f"{excluded_of_attempted}/{denom} ({excluded_of_attempted / denom:.0%})"
        )
        print("  baseline was: 11/17 (65%) with claude-haiku-4-5-20251001")
    else:
        print("Exclusion rate: n/a (no story reached an extraction attempt)")
    if word_counts:
        print(
            f"Cohort word counts: median={statistics.median(word_counts):,.0f} "
            f"min={min(word_counts):,} max={max(word_counts):,} "
            f"(n={len(word_counts)}) - see ABOUT THE COHORT before trusting "
            "a rate change alone"
        )
    print("Breakdown by outcome (all sampled stories, including non-LLM skips):")
    for cause, n in counts.most_common():
        print(f"  {n:>3}  {cause}")
    print(f"\nPer-story output (incl. raw/extracted LLM output): {output_dir}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
