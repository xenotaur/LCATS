"""Gemini online candidate: gemini-3.5-flash via Google's OpenAI-compatible
endpoint, using OpenAIBackend + base_url (no separate backend class needed
- see lcats/src/lcats/llm/openai_backend.py's base_url parameter).

Run setup.py first. This makes ONE real API call (the entity-extraction
tool-schema stage against a single real scene/sequel segment - see
common/sample_segment.json) - see this directory's README.md.

This is the one tranche-1 cell requiring real verification rather than
just wiring: Google's OpenAI-compat docs explicitly exclude some
Gemini-native features, and forced tool_choice reliability through this
compat layer for our exact schema is unverified before this run.

Usage:
    python lcats/experimental/model_comparison/gemini_flash/benchmark.py
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
    )
    out_path = harness.save_result(result, _HERE)
    print(f"Wrote {out_path}")
    print(result.to_dict())


if __name__ == "__main__":
    main()
