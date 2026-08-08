"""WI-LLM-0059: does appending the reminder to SCENE_SEQUEL_SYSTEM_PROMPT
regress frontier-model (Claude/GPT) segmentation output quality or
latency? SCENE_SEQUEL_SYSTEM_PROMPT is shared across every LLMBackend, so
a permanent edit would ship to these paths too - a single before/after
pair cannot distinguish a real prompt effect from ordinary model/API
run-to-run variance (Codex review finding on this WI's own planning PR,
#260), so this runs multiple paired baseline/modified calls per frontier
backend.

Usage:
    python lcats/experimental/model_comparison/wi_llm_0059/run_frontier_paired.py
"""

from __future__ import annotations

import json
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
_MODEL_COMPARISON = _HERE.parent
sys.path.insert(0, str(_MODEL_COMPARISON))

from common import harness  # noqa: E402
from lcats.llm import anthropic_backend  # noqa: E402
from lcats.llm import openai_backend  # noqa: E402
from lcats.utils import secrets  # noqa: E402

TEMPERATURE = 0.2  # unchanged from scene_analysis.py's own default - frontier paths are not being re-tuned here


def run_pair(*, candidate, backend_kind, backend, model, story_name, story_text):
    """One baseline call (unmodified prompt) + one modified call (reminder appended)."""
    baseline = harness._run_segmentation_once(  # noqa: SLF001
        candidate=candidate,
        backend_kind=backend_kind,
        backend=backend,
        model=model,
        story_name=story_name,
        story_text=story_text,
        max_tokens=harness.DEFAULT_SEGMENTATION_MAX_TOKENS,
        temperature=TEMPERATURE,
    )
    modified = harness._run_segmentation_once(  # noqa: SLF001
        candidate=candidate,
        backend_kind=backend_kind,
        backend=backend,
        model=model,
        story_name=story_name,
        story_text=story_text,
        max_tokens=harness.DEFAULT_SEGMENTATION_MAX_TOKENS,
        temperature=TEMPERATURE,
        system_prompt_suffix=harness._SEGMENTATION_RETRY_REMINDER,  # noqa: SLF001
    )
    return baseline.to_dict(), modified.to_dict()


def main() -> None:
    secrets.load_secrets()
    story_name, story_text = harness.load_sample_story()

    all_pairs = []

    # Anthropic: 3 paired runs (this WI's Required Changes item 2 - at
    # least 3, not a single pair).
    anthropic = anthropic_backend.AnthropicBackend()
    for i in range(1, 4):
        print(f"--- anthropic_opus pair {i}/3 ---", flush=True)
        baseline, modified = run_pair(
            candidate="anthropic_opus",
            backend_kind="anthropic",
            backend=anthropic,
            model="claude-opus-4-8",
            story_name=story_name,
            story_text=story_text,
        )
        pair = {
            "backend": "anthropic_opus",
            "pair_index": i,
            "baseline": baseline,
            "modified": modified,
        }
        print(json.dumps(pair, indent=2))
        all_pairs.append(pair)

    # OpenAI: 1 paired run (this WI's Required Changes item 3 - the
    # supported path this proposal's Non-Goals left untested; a real key
    # is available in this environment, so it is tested for real rather
    # than deferred).
    openai_be = openai_backend.OpenAIBackend()
    print("--- openai_gpt4o pair 1/1 ---", flush=True)
    baseline, modified = run_pair(
        candidate="openai_gpt4o",
        backend_kind="openai",
        backend=openai_be,
        model="gpt-4o",
        story_name=story_name,
        story_text=story_text,
    )
    pair = {
        "backend": "openai_gpt4o",
        "pair_index": 1,
        "baseline": baseline,
        "modified": modified,
    }
    print(json.dumps(pair, indent=2))
    all_pairs.append(pair)

    out_path = _HERE / "results_frontier_paired.json"
    out_path.write_text(json.dumps(all_pairs, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
