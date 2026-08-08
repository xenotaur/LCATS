"""Local-model candidate: qwen3:8b against segmentation, on a different
story than the default sample (`corpora/sherlock/engineers_thumb`).

WI-LLM-0051 investigation variant - checks whether the `tool_choice`
gap `benchmark_segmentation.py` reproduces is story-specific or general,
by holding the model fixed and varying only the story. Run setup.py
first - it confirms Ollama is running and the model is pulled. See
../common/harness.py's run_segmentation() for the real call path this
reuses.

Usage:
    python lcats/experimental/model_comparison/ollama_qwen3_8b/benchmark_segmentation_engineers_thumb.py
"""

from __future__ import annotations

import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
_MODEL_COMPARISON = _HERE.parent
sys.path.insert(0, str(_MODEL_COMPARISON))

from common import harness  # noqa: E402
from lcats.llm import openai_backend  # noqa: E402

MODEL = "qwen3:8b"
OLLAMA_BASE_URL = "http://localhost:11434/v1"

# Same override as benchmark.py's entity-extraction run - see that file's
# TEMPERATURE comment for the full rationale.
TEMPERATURE = 0.6

STORY_PATH = (
    _MODEL_COMPARISON.parents[2]
    / "corpora"
    / "sherlock"
    / "engineers_thumb"
    / "story.json"
)


def main() -> None:
    backend = openai_backend.OpenAIBackend(api_key="ollama", base_url=OLLAMA_BASE_URL)
    result = harness.run_segmentation(
        candidate="ollama_qwen3_8b",
        backend_kind="openai_compatible_local",
        backend=backend,
        model=MODEL,
        story_path=STORY_PATH,
        temperature=TEMPERATURE,
        # This variant's purpose is characterizing the baseline gap
        # across stories, not re-validating the retry mitigation
        # (already validated on the default story) - disable it so a
        # retry success on this story doesn't get conflated with the
        # baseline-frequency evidence.
        retry_with_reminder=False,
    )
    out_path = harness.save_result(
        result, _HERE, filename="results_segmentation_engineers_thumb.json"
    )
    print(f"Wrote {out_path}")
    print(result.to_dict())


if __name__ == "__main__":
    main()
