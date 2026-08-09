"""Local-model candidate: deepseek-r1:14b served by Ollama's OpenAI-compatible
API - the second open-weight family for WI-LLM-0056's tranche 1 (a genuinely
distinct lineage from Qwen3: DeepSeek's R1 reasoning-distilled family).

The WI's own research named DeepSeek V4 as the target, but V4 turned out to
be Ollama-cloud-only (no locally-runnable tag exists) at implementation
time - see ../README.md's "Research context" for the verification. R1:14b
is the real, locally-runnable DeepSeek candidate that fits this session's
Mac (9.0GB).

Run setup.py first - it confirms Ollama is running and the model is pulled.
This candidate is free to run repeatedly (no per-call API cost) once the
model is downloaded once.

Uses lcats.llm.openai_backend.OpenAIBackend pointed at Ollama's
OpenAI-compatible endpoint via base_url - no separate backend class needed
(see lcats/src/lcats/llm/openai_backend.py's base_url parameter).

Usage:
    python lcats/experimental/model_comparison/ollama_deepseek_r1_14b/benchmark.py
"""

from __future__ import annotations

import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
_MODEL_COMPARISON = _HERE.parent
sys.path.insert(0, str(_MODEL_COMPARISON))

from common import harness  # noqa: E402
from lcats.llm import openai_backend  # noqa: E402

MODEL = "deepseek-r1:14b"
OLLAMA_BASE_URL = "http://localhost:11434/v1"


def main() -> None:
    # Ollama's OpenAI-compatible endpoint ignores the API key but the SDK
    # still requires a non-empty string.
    backend = openai_backend.OpenAIBackend(api_key="ollama", base_url=OLLAMA_BASE_URL)
    result = harness.run_entity_extraction(
        candidate="ollama_deepseek_r1_14b",
        backend_kind="openai_compatible_local",
        backend=backend,
        model=MODEL,
    )
    out_path = harness.save_result(result, _HERE)
    print(f"Wrote {out_path}")
    print(result.to_dict())


if __name__ == "__main__":
    main()
