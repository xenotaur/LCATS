"""gpt-oss:20b segmentation best-config diagnostic runs.

WI-LLM-0064: run the real scene/sequel segmentation tool-schema path with
diagnostic capture of pre-alignment anchor strings. Tests temperature=1.0
alone and temperature=1.0 plus a candidate-local verbatim-anchor reminder.

Usage:
    python lcats/experimental/model_comparison/ollama_gpt_oss_20b/benchmark_segmentation_bestconfig.py
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

VERBATIM_QUOTE_REMINDER = (
    "\n\nCRITICAL INSTRUCTION: You MUST call the record_segments function/tool "
    "to submit your answer. For every segment, start_exact and end_exact must "
    "be copied verbatim from the story text. Do not paraphrase, normalize, "
    "summarize, add punctuation, remove punctuation, or change capitalization "
    "inside start_exact or end_exact. Use short anchor strings that appear "
    "exactly once near the segment boundary."
)


def _run_variant(
    *,
    backend: openai_backend.OpenAIBackend,
    variant: str,
    system_prompt_suffix: str,
) -> list[dict]:
    runs = []
    for run_number in range(1, RUN_COUNT + 1):
        result = harness.run_segmentation_diagnostic(
            candidate="ollama_gpt_oss_20b",
            backend_kind="openai_compatible_local",
            backend=backend,
            model=MODEL,
            temperature=TEMPERATURE,
            system_prompt_suffix=system_prompt_suffix,
            variant=variant,
        )
        result["run_number"] = run_number
        runs.append(result)
        out_path = harness.save_json_result(
            result,
            _HERE,
            filename=f"results_segmentation_bestconfig_{variant}_run{run_number}.json",
        )
        print(f"Wrote {out_path}")
    return runs


def main() -> None:
    backend = openai_backend.OpenAIBackend(api_key="ollama", base_url=OLLAMA_BASE_URL)
    variants = {
        "temperature_1": _run_variant(
            backend=backend,
            variant="temperature_1",
            system_prompt_suffix="",
        ),
        "verbatim_quote_reminder": _run_variant(
            backend=backend,
            variant="verbatim_quote_reminder",
            system_prompt_suffix=VERBATIM_QUOTE_REMINDER,
        ),
    }
    aggregate = {
        "candidate": "ollama_gpt_oss_20b",
        "model": MODEL,
        "stage": "segmentation",
        "temperature": TEMPERATURE,
        "run_count_per_variant": RUN_COUNT,
        "variants": variants,
    }
    out_path = harness.save_json_result(
        aggregate, _HERE, filename="results_segmentation_bestconfig.json"
    )
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
