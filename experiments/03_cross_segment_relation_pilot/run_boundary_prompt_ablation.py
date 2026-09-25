"""Run the WI-SEGMENT-0101 reworded-prompt ablation against a real cohort.

Structurally mirrors check_segmentation_reliability.py (WI-EVENT-0033/
WI-EVENT-0096): one LLM call per story, immediate per-story persistence,
resumable by skipping already-existing output files. The only difference
is which extractor is used - reworded_boundary_prompt.make_reworded_
segment_extractor instead of scene_analysis.make_segment_extractor - so
this script measures the REWORDED prompt only. The "before" side of the
comparison reuses WI-EVENT-0096's already-committed real output under
results/segmentation_reliability/ rather than re-spending on the
unchanged production prompt (see measure_paragraph_boundary_overshoot.py).

USAGE
-----
Needs a real API key (see lcats/docs/secrets-setup.md). Run from the repo
root with the conda environment active:

    python experiments/03_cross_segment_relation_pilot/run_boundary_prompt_ablation.py \\
        --model claude-haiku-4-5-20251001 \\
        --output experiments/03_cross_segment_relation_pilot/results/segmentation_reliability_reworded_prompt

`--story-list` defaults to the committed WI-EVENT-0096 baseline cohort
(results/segmentation_reliability/baseline_story_list.txt) so both prompt
variants run against the exact same 17 stories.
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lcats" / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import reworded_boundary_prompt  # noqa: E402
from lcats.analysis import story_analysis  # noqa: E402
from lcats.analysis.corpus import discovery  # noqa: E402
from lcats.utils.secrets import load_secrets  # noqa: E402

DEFAULT_STORY_LIST = (
    pathlib.Path(__file__).parent
    / "results"
    / "segmentation_reliability"
    / "baseline_story_list.txt"
)


def classify(result: dict, segments: list) -> str:
    """Identical classification logic to check_segmentation_reliability.py's
    classify() - duplicated rather than imported since that module is a
    script (`if __name__ == "__main__"`), not an importable library, and
    the two measurements are read independently, not composed."""
    api_error = result.get("api_error")
    if api_error:
        category = api_error.get("category") or "unknown"
        label = api_error.get("code") if category == "unknown" else category
        return f"api_error:{label or 'unknown'}"
    if result.get("extraction_error"):
        return f"extraction_error:{result['extraction_error']}"
    if result.get("alignment_error"):
        return f"alignment_error:{result['alignment_error']}"
    if not segments:
        return "no_segments"
    return "included"


def select_files(story_list_path: pathlib.Path) -> list[pathlib.Path]:
    lines = story_list_path.read_text("utf-8").splitlines()
    listed = [
        line.strip()
        for line in lines
        if line.strip() and not line.strip().startswith("#")
    ]
    return sorted(discovery.find_json_files(listed))


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--story-list", default=str(DEFAULT_STORY_LIST))
    parser.add_argument("--model", default="claude-haiku-4-5-20251001")
    parser.add_argument(
        "--output",
        default="experiments/03_cross_segment_relation_pilot/results/segmentation_reliability_reworded_prompt",
    )
    args = parser.parse_args()

    load_secrets()
    from lcats.llm import anthropic_backend

    output_dir = pathlib.Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    files = select_files(pathlib.Path(args.story_list))
    if not files:
        print("error: no stories selected", file=sys.stderr)
        return 1

    extractor = reworded_boundary_prompt.make_reworded_segment_extractor(
        anthropic_backend.AnthropicBackend()
    )
    counts: collections.Counter = collections.Counter()
    llm_calls_made = 0

    for i, path in enumerate(files, 1):
        story_id = f"{path.parent.parent.name}/{path.parent.name}"
        result_path = output_dir / path.parent.parent.name / f"{path.parent.name}.json"
        if result_path.exists():
            cached = json.loads(result_path.read_text("utf-8"))
            counts[cached["outcome"]] += 1
            if cached.get("llm_call_made"):
                llm_calls_made += 1
            print(f"[{i}/{len(files)}] {story_id}: {cached['outcome']} (cached)")
            continue

        result_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            data = json.loads(path.read_text("utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            outcome = "story_json_error"
            record = {
                "story_id": story_id,
                "outcome": outcome,
                "llm_call_made": False,
                "error": f"{type(exc).__name__}: {exc}",
            }
            counts[outcome] += 1
            result_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
            print(f"[{i}/{len(files)}] {story_id}: {outcome}")
            continue

        body = story_analysis.coerce_text(data.get("body", ""))
        if not body.strip():
            outcome = "empty_story_body"
            record = {"story_id": story_id, "outcome": outcome, "llm_call_made": False}
            counts[outcome] += 1
            result_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
            print(f"[{i}/{len(files)}] {story_id}: {outcome}")
            continue

        result = extractor.extract(body, model_name=args.model)
        llm_calls_made += 1
        api_error = result.get("api_error")
        segments = result.get("extracted_output") or []
        if result.get("alignment_error"):
            segments = []
        outcome = classify(result, segments)
        counts[outcome] += 1
        record = {
            "story_id": story_id,
            "outcome": outcome,
            "llm_call_made": True,
            "segment_count": len(segments),
            "raw_output": result.get("raw_output"),
            "parsed_output": result.get("parsed_output"),
            "extracted_output": result.get("extracted_output"),
            "api_error": api_error,
            "extraction_error": result.get("extraction_error"),
            "usage": result.get("usage"),
        }
        result_path.write_text(
            json.dumps(record, indent=2, default=str), encoding="utf-8"
        )
        print(f"[{i}/{len(files)}] {story_id}: {outcome} ({len(segments)} segments)")

        if api_error and api_error.get("should_abort_batch"):
            print(
                f"\nfatal: {story_id}: {api_error.get('message', api_error)}",
                file=sys.stderr,
            )
            print(
                "Aborting - looks like a bad/expired API key or exhausted "
                f"quota, not a per-story problem. Results so far are still "
                f"persisted under {output_dir}/.",
                file=sys.stderr,
            )
            break

    print(f"\nStories: {len(files)}")
    print(f"LLM calls made: {llm_calls_made}")
    print(f"Outcomes: {dict(counts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
