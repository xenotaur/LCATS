"""Production-grounded gpt-oss:20b entity-extraction mitigation runs.

WI-LLM-0065 tests whether candidate-scoped JSON-content fallback plus a
conservative normalizer can make the local ``gpt-oss:20b`` entity output
usable by the real production ``build_entities()`` grounding semantics.

Usage:
    python experimental/model_comparison/ollama_gpt_oss_20b/benchmark_entity_production_grounded.py
"""

from __future__ import annotations

import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
_MODEL_COMPARISON = _HERE.parent
sys.path.insert(0, str(_MODEL_COMPARISON))
sys.path.insert(0, str(_HERE))

from common import harness  # noqa: E402
from entity_shape_adapter import normalize_gpt_oss_entity_tool_result  # noqa: E402
from lcats.llm import openai_backend  # noqa: E402

MODEL = "gpt-oss:20b"
OLLAMA_BASE_URL = "http://localhost:11434/v1"
TEMPERATURE = 1.0
RUN_COUNT = 3
VARIANT = "json_content_fallback_safe_shape_adapter"


def main() -> None:
    backend = openai_backend.OpenAIBackend(api_key="ollama", base_url=OLLAMA_BASE_URL)
    runs = []
    for run_number in range(1, RUN_COUNT + 1):
        result = harness.run_entity_extraction_with_grounding(
            candidate="ollama_gpt_oss_20b",
            backend_kind="openai_compatible_local",
            backend=backend,
            model=MODEL,
            temperature=TEMPERATURE,
            variant=VARIANT,
            tool_result_adapter=normalize_gpt_oss_entity_tool_result,
            allow_no_tool_call_json_fallback=True,
        )
        result["run_number"] = run_number
        runs.append(result)
        out_path = harness.save_json_result(
            result,
            _HERE,
            filename=f"results_entity_production_grounded_run{run_number}.json",
        )
        print(f"Wrote {out_path}")

    aggregate = {
        "candidate": "ollama_gpt_oss_20b",
        "model": MODEL,
        "stage": "entity_extraction",
        "variant": VARIANT,
        "temperature": TEMPERATURE,
        "run_count": RUN_COUNT,
        "tool_call_success_count": sum(
            1 for run in runs if run.get("tool_call_success")
        ),
        "usable_result_success_count": sum(1 for run in runs if run.get("success")),
        "json_content_fallback_count": sum(
            1 for run in runs if run.get("json_content_fallback_applied")
        ),
        "production_grounded_success_count": sum(
            1 for run in runs if run.get("production_grounded_success")
        ),
        "grounded_entity_counts": [run.get("grounded_entity_count") for run in runs],
        "grounded_mention_counts": [run.get("grounded_mention_count") for run in runs],
        "runs": runs,
    }
    out_path = harness.save_json_result(
        aggregate, _HERE, filename="results_entity_production_grounded.json"
    )
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
