"""Local-model candidate: gpt-oss:20b against the scene/sequel segmentation
stage.

Run setup.py first - it confirms Ollama is running and the model is pulled.
See ../common/harness.py's run_segmentation() for the real call path this
reuses (scene_analysis.make_segment_extractor()), run against the whole
sample story rather than a single segment - segmentation itself is what
produces segments, so unlike entity extraction there is no smaller unit to
feed it. run_segmentation() defaults retry_with_reminder=True, so a
no_tool_call baseline failure automatically retries once with WI-LLM-0051's
reminder appended to the system prompt.

Usage:
    python lcats/experimental/model_comparison/ollama_gpt_oss_20b/benchmark_segmentation.py
"""

from __future__ import annotations

import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
_MODEL_COMPARISON = _HERE.parent
sys.path.insert(0, str(_MODEL_COMPARISON))

from common import harness  # noqa: E402
from lcats.llm import openai_backend  # noqa: E402

MODEL = "gpt-oss:20b"
OLLAMA_BASE_URL = "http://localhost:11434/v1"


def main() -> None:
    backend = openai_backend.OpenAIBackend(api_key="ollama", base_url=OLLAMA_BASE_URL)
    result = harness.run_segmentation(
        candidate="ollama_gpt_oss_20b",
        backend_kind="openai_compatible_local",
        backend=backend,
        model=MODEL,
    )
    out_path = harness.save_result(result, _HERE, filename="results_segmentation.json")
    print(f"Wrote {out_path}")
    print(result.to_dict())


if __name__ == "__main__":
    main()
