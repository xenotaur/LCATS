"""gpt-oss:20b entity-extraction best-config diagnostic runs.

WI-LLM-0064: run the real entity-extraction tool-schema path at the
model's documented/bundled temperature=1.0 setting, while recording both
raw tool-result entity counts and production-grounded build_entities()
counts.

Usage:
    python lcats/experimental/model_comparison/ollama_gpt_oss_20b/benchmark_entity_bestconfig.py
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
TEMPERATURE = 1.0
RUN_COUNT = 3


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
            variant="temperature_1_grounded",
        )
        result["run_number"] = run_number
        runs.append(result)
        out_path = harness.save_json_result(
            result,
            _HERE,
            filename=f"results_entity_bestconfig_run{run_number}.json",
        )
        print(f"Wrote {out_path}")

    aggregate = {
        "candidate": "ollama_gpt_oss_20b",
        "model": MODEL,
        "stage": "entity_extraction",
        "variant": "temperature_1_grounded",
        "temperature": TEMPERATURE,
        "run_count": RUN_COUNT,
        "success_count": sum(1 for run in runs if run.get("success")),
        "grounded_success_count": sum(
            1 for run in runs if (run.get("grounded_entity_count") or 0) > 0
        ),
        "runs": runs,
    }
    out_path = harness.save_json_result(
        aggregate, _HERE, filename="results_entity_bestconfig.json"
    )
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
