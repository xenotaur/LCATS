"""ollama_gemma4_12b entity-extraction reminder-retry test (WI-LLM-0062).

Tests whether WI-LLM-0051's reminder-retry mitigation (proven on the
segmentation stage: 0/5 baseline vs. 2/5 with reminder) also helps this
candidate's entity-extraction stage, where it silently ignores
`tool_choice` (see WI-LLM-0056's tranche 1 findings).

Run setup.py first. Each run makes a real baseline attempt, then - only
if that attempt fails with error_type="no_tool_call" - a real retry
attempt with the reminder appended. Run this script 3+ times for
decision-grade evidence (a single run cannot distinguish a real prompt
effect from ordinary run-to-run variation, given the reminder's own
known 40% success rate).

Usage:
    python lcats/experimental/model_comparison/ollama_gemma4_12b/benchmark_entity_reminder.py
"""

from __future__ import annotations

import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
_MODEL_COMPARISON = _HERE.parent
sys.path.insert(0, str(_MODEL_COMPARISON))

from common import harness  # noqa: E402
from lcats.llm import openai_backend  # noqa: E402

MODEL = "gemma4:12b"
OLLAMA_BASE_URL = "http://localhost:11434/v1"

# harness.DEFAULT_MAX_TOKENS (8192) proved insufficient for this
# candidate's real entity-extraction tool-call output on this segment -
# 3/3 real runs at implementation time hit truncated_output before ever
# reaching a no_tool_call/success outcome, masking the actual
# tool_choice question this script exists to test (see
# results_entity_reminder_run{1,2,3}.json). Raised to match
# harness.DEFAULT_SEGMENTATION_MAX_TOKENS's precedent for a
# larger-output stage, per-candidate, rather than assuming the
# entity-extraction-tuned default transfers.
MAX_TOKENS = 16384


def main() -> None:
    backend = openai_backend.OpenAIBackend(api_key="ollama", base_url=OLLAMA_BASE_URL)
    result = harness.run_entity_extraction(
        candidate="ollama_gemma4_12b",
        backend_kind="openai_compatible_local",
        backend=backend,
        model=MODEL,
        max_tokens=MAX_TOKENS,
        retry_with_reminder=True,
    )
    out_path = harness.save_result(
        result, _HERE, filename="results_entity_reminder.json"
    )
    print(f"Wrote {out_path}")
    print(result.to_dict())


if __name__ == "__main__":
    main()
