"""Local-model candidate: qwen3:8b against the genre-detection stage.

Run setup.py first - it confirms Ollama is running and the model is pulled.
See ../common/harness.py's run_genre_detection() for the real call path
this reuses (corpus_assess.assess_story() in detect mode).

Usage:
    python lcats/experimental/model_comparison/ollama_qwen3_8b/benchmark_genre.py
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
# TEMPERATURE comment for the full rationale (Qwen3's own documented
# recommendation, Ollama's own bundled default for this model).
TEMPERATURE = 0.6


def main() -> None:
    backend = openai_backend.OpenAIBackend(api_key="ollama", base_url=OLLAMA_BASE_URL)
    result = harness.run_genre_detection(
        candidate="ollama_qwen3_8b",
        backend_kind="openai_compatible_local",
        backend=backend,
        model=MODEL,
        temperature=TEMPERATURE,
    )
    out_path = harness.save_result(result, _HERE, filename="results_genre.json")
    print(f"Wrote {out_path}")
    print(result.to_dict())


if __name__ == "__main__":
    main()
