"""Gemini minimal-schema probe (WI-LLM-0062, mechanism b).

Tests whether Gemini's function_call_filter rejection of ENTITY_TOOL_SCHEMA
(see this candidate's README) is schema-complexity-dependent, by calling
the identical real segment through a minimal, flat, single-field tool
schema instead - no nesting, no enums, no descriptions.

This is a diagnostic probe, not a durable candidate benchmark - it uses a
synthetic schema, not a real ERW pipeline extractor, so it is not run via
common/harness.py's run_entity_extraction() and does not write a
BenchmarkResult-shaped results.json. Writes its own small JSON instead.

Usage:
    python lcats/experimental/model_comparison/gemini_flash/benchmark_minimal_schema.py
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
_MODEL_COMPARISON = _HERE.parent
sys.path.insert(0, str(_MODEL_COMPARISON))

from common import harness  # noqa: E402
from lcats.llm import openai_backend  # noqa: E402
from lcats.llm import tool_schema as tool_schema_module  # noqa: E402
from lcats.utils import secrets as secrets_module  # noqa: E402

MODEL = "gemini-3.5-flash"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

# Minimal, flat schema - one array of plain strings, no nesting, no enums,
# no descriptions - about as simple as a real extraction tool can be, in
# deliberate contrast to ENTITY_TOOL_SCHEMA's nested per-entity/mentions
# shape.
MINIMAL_TOOL_SCHEMA = tool_schema_module.strict_tool_schema(
    {
        "name": "list_character_names",
        "description": "List the character names mentioned in the text.",
        "input_schema": {
            "type": "object",
            "properties": {
                "names": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["names"],
        },
    }
)


def main() -> None:
    secrets_module.load_secrets()
    backend = openai_backend.OpenAIBackend(
        api_key=os.environ["GEMINI_API_KEY"], base_url=GEMINI_BASE_URL
    )
    _, segment_text = harness.load_sample_segment()

    result: dict = {"model": MODEL, "schema": "minimal_flat"}
    try:
        response = backend.complete(
            system="Extract the character names mentioned in the following text segment.",
            messages=[{"role": "user", "content": segment_text}],
            model=MODEL,
            temperature=0.2,
            max_tokens=2048,
            tool=MINIMAL_TOOL_SCHEMA,
        )
        result.update(
            success=True,
            tool_result=response.tool_result,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
        )
    except Exception as exc:  # noqa: BLE001 - probe records, not raises
        result.update(
            success=False, error_type=type(exc).__name__, error_message=str(exc)
        )

    out_path = _HERE / "results_minimal_schema.json"
    out_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")
    print(result)


if __name__ == "__main__":
    main()
