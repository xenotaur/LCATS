"""WI-LLM-0059: does appending the reminder to SCENE_SEQUEL_SYSTEM_PROMPT
regress frontier-model (Claude/GPT) segmentation output quality or
latency? SCENE_SEQUEL_SYSTEM_PROMPT is shared across every LLMBackend, so
a permanent edit would ship to these paths too - a single before/after
pair cannot distinguish a real prompt effect from ordinary model/API
run-to-run variance (Codex review finding on this WI's own planning PR,
#260), so this runs multiple paired baseline/modified calls per frontier
backend.

Unlike common/harness.py's BenchmarkResult (which only records
segment_count, not the segments themselves), this script calls
scene_analysis.make_segment_extractor() directly and persists each call's
actual segment types/summaries - a count alone cannot support a claim
about output *quality* (a review finding on this PR, #266: the original
version of this script relied on BenchmarkResult's count-only view and
could not actually back its "no regression" claim for content/labels).

Usage:
    python lcats/experimental/model_comparison/wi_llm_0059/run_frontier_paired.py
    python lcats/experimental/model_comparison/wi_llm_0059/run_frontier_paired.py --legs anthropic
    python lcats/experimental/model_comparison/wi_llm_0059/run_frontier_paired.py --legs openai
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
from typing import Any, Dict, List

_HERE = pathlib.Path(__file__).resolve().parent
_MODEL_COMPARISON = _HERE.parent
sys.path.insert(0, str(_MODEL_COMPARISON))

from common import harness  # noqa: E402
from lcats.analysis import scene_analysis  # noqa: E402
from lcats.llm import anthropic_backend  # noqa: E402
from lcats.llm import openai_backend  # noqa: E402
from lcats.utils import secrets  # noqa: E402

TEMPERATURE = 0.2  # unchanged from scene_analysis.py's own default - frontier paths are not being re-tuned here

_ANTHROPIC_RESULTS_PATH = _HERE / "results_frontier_paired_anthropic.json"
_OPENAI_RESULTS_PATH = _HERE / "results_frontier_paired_openai.json"
_COMBINED_RESULTS_PATH = _HERE / "results_frontier_paired.json"


def _call_once(
    *, backend, model: str, story_text: str, system_prompt_suffix: str = ""
) -> Dict[str, Any]:
    """One real segmentation call, capturing the actual segments (not just
    a count) so a reviewer can inspect labels/boundaries, not only whether
    the call succeeded. Mirrors common/harness._run_segmentation_once()'s
    success/error classification (kept in sync manually - see that
    function's docstring) but additionally persists
    extracted_output itself.
    """
    extractor = scene_analysis.make_segment_extractor(
        backend, max_tokens=harness.DEFAULT_SEGMENTATION_MAX_TOKENS
    )
    extractor.default_model = model
    extractor.temperature = TEMPERATURE
    if system_prompt_suffix:
        extractor.system_prompt = extractor.system_prompt + system_prompt_suffix

    start = time.monotonic()
    result = extractor.extract(story_text, model_name=model)
    latency = time.monotonic() - start

    api_error = result.get("api_error")
    extraction_error = result.get("extraction_error")
    alignment_error = result.get("alignment_error")
    validation_error = result.get("validation_error")
    extracted = result.get("extracted_output")

    schema_error = None
    if api_error is None:
        if extraction_error or alignment_error or validation_error:
            schema_error = "extraction_or_alignment_error"
        elif not isinstance(extracted, list):
            schema_error = "malformed_tool_result"
        elif not extracted:
            schema_error = "empty_segment_list"

    segments: List[Dict[str, Any]] = []
    if isinstance(extracted, list):
        for seg in extracted:
            if isinstance(seg, dict):
                segments.append(
                    {
                        "segment_id": seg.get("segment_id"),
                        "segment_type": seg.get("segment_type"),
                        "summary": seg.get("summary"),
                    }
                )

    return {
        "success": api_error is None and schema_error is None,
        "latency_seconds": latency,
        "segment_count": len(extracted) if isinstance(extracted, list) else None,
        "segments": segments,
        "error_type": (api_error or {}).get("code") if api_error else schema_error,
        "error_message": (
            (api_error or {}).get("message") if api_error else schema_error
        ),
    }


def run_pair(*, model: str, backend, story_text: str) -> tuple:
    """One baseline call (unmodified prompt) + one modified call (reminder appended)."""
    baseline = _call_once(backend=backend, model=model, story_text=story_text)
    modified = _call_once(
        backend=backend,
        model=model,
        story_text=story_text,
        system_prompt_suffix=harness._SEGMENTATION_RETRY_REMINDER,  # noqa: SLF001
    )
    return baseline, modified


def run_anthropic_pairs(story_text: str, n: int = 3) -> List[Dict[str, Any]]:
    anthropic = anthropic_backend.AnthropicBackend()
    pairs = []
    for i in range(1, n + 1):
        print(f"--- anthropic_opus pair {i}/{n} ---", flush=True)
        baseline, modified = run_pair(
            model="claude-opus-4-8", backend=anthropic, story_text=story_text
        )
        pair = {
            "backend": "anthropic_opus",
            "pair_index": i,
            "baseline": baseline,
            "modified": modified,
        }
        print(json.dumps(pair, indent=2))
        pairs.append(pair)
    _ANTHROPIC_RESULTS_PATH.write_text(
        json.dumps(pairs, indent=2) + "\n", encoding="utf-8"
    )
    print(f"\nWrote {_ANTHROPIC_RESULTS_PATH}")
    return pairs


def run_openai_pair(story_text: str) -> List[Dict[str, Any]]:
    openai_be = openai_backend.OpenAIBackend()
    print("--- openai_gpt4o pair 1/1 ---", flush=True)
    baseline, modified = run_pair(
        model="gpt-4o", backend=openai_be, story_text=story_text
    )
    pair = {
        "backend": "openai_gpt4o",
        "pair_index": 1,
        "baseline": baseline,
        "modified": modified,
    }
    print(json.dumps(pair, indent=2))
    pairs = [pair]
    _OPENAI_RESULTS_PATH.write_text(
        json.dumps(pairs, indent=2) + "\n", encoding="utf-8"
    )
    print(f"\nWrote {_OPENAI_RESULTS_PATH}")
    return pairs


def _load_existing(path: pathlib.Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--legs",
        choices=["anthropic", "openai", "all"],
        default="all",
        help=(
            "Which frontier backend(s) to call this run. A single leg reuses "
            "the other leg's most recent committed results for the combined "
            "output file, instead of re-running (and re-billing) it."
        ),
    )
    args = parser.parse_args()

    secrets.load_secrets()
    _, story_text = harness.load_sample_story()

    if args.legs in ("anthropic", "all"):
        anthropic_pairs = run_anthropic_pairs(story_text)
    else:
        anthropic_pairs = _load_existing(_ANTHROPIC_RESULTS_PATH)

    if args.legs in ("openai", "all"):
        openai_pairs = run_openai_pair(story_text)
    else:
        openai_pairs = _load_existing(_OPENAI_RESULTS_PATH)

    combined = anthropic_pairs + openai_pairs
    _COMBINED_RESULTS_PATH.write_text(
        json.dumps(combined, indent=2) + "\n", encoding="utf-8"
    )
    print(f"\nWrote {_COMBINED_RESULTS_PATH}")


if __name__ == "__main__":
    main()
