"""gemini_flash entity-extraction retest at a higher token budget (WI-LLM-0062).

Re-runs the real, unmodified ENTITY_TOOL_SCHEMA call benchmark.py makes
(`max_tokens=8192`), but at `max_tokens=32000`, to isolate whether the
original MALFORMED_FUNCTION_CALL failures (see this candidate's README)
were caused by schema complexity or by insufficient token budget for
Gemini's own "thinking"/reasoning consumption.

Usage:
    python lcats/experimental/model_comparison/gemini_flash/benchmark_full_schema_32k.py
"""

from __future__ import annotations

import os
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
_MODEL_COMPARISON = _HERE.parent
sys.path.insert(0, str(_MODEL_COMPARISON))

from common import harness  # noqa: E402
from lcats.llm import openai_backend  # noqa: E402
from lcats.utils import secrets as secrets_module  # noqa: E402

MODEL = "gemini-3.5-flash"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
MAX_TOKENS = 32000


def main() -> None:
    secrets_module.load_secrets()
    backend = openai_backend.OpenAIBackend(
        api_key=os.environ["GEMINI_API_KEY"], base_url=GEMINI_BASE_URL
    )
    result = harness.run_entity_extraction(
        candidate="gemini_flash",
        backend_kind="openai_compatible_remote",
        backend=backend,
        model=MODEL,
        max_tokens=MAX_TOKENS,
    )
    out_path = harness.save_result(result, _HERE, filename="results_entity_32k.json")
    print(f"Wrote {out_path}")
    print(result.to_dict())


if __name__ == "__main__":
    main()
