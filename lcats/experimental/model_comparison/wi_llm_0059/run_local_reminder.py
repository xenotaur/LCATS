"""WI-LLM-0059: does the reminder help when appended to the *real*
SCENE_SEQUEL_SYSTEM_PROMPT (not the harness's own retry-only copy) for
local Ollama models?

WI-LLM-0051 already established the reminder's effect via
common/harness.py's run_segmentation() *retry* path (a second, fresh call
after a first attempt fails with error_type="no_tool_call", with the
reminder appended to the system prompt on that second call only). This
script calls the same underlying single-call function
(harness._run_segmentation_once()) directly, with the reminder appended
from the start (system_prompt_suffix set unconditionally, retry logic
bypassed) - i.e. as if SCENE_SEQUEL_SYSTEM_PROMPT already had this
reminder permanently, not just on a retry. Each call is otherwise
identical in shape (same story, same system prompt plus suffix, no prior
turn/context carried over) to WI-LLM-0051's retry calls, so results here
are directly comparable to and combinable with that prior sample.

Usage:
    python lcats/experimental/model_comparison/wi_llm_0059/run_local_reminder.py
"""

from __future__ import annotations

import json
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
_MODEL_COMPARISON = _HERE.parent
sys.path.insert(0, str(_MODEL_COMPARISON))

from common import harness  # noqa: E402
from lcats.llm import openai_backend  # noqa: E402

OLLAMA_BASE_URL = "http://localhost:11434/v1"
TEMPERATURE = 0.6

# (candidate_name, model, num_calls)
RUNS = [
    ("ollama_qwen3_8b", "qwen3:8b", 3),
    ("ollama_qwen3_30b_a3b", "qwen3:30b-a3b", 1),
]


def main() -> None:
    story_name, story_text = harness.load_sample_story()
    all_results = []
    for candidate, model, n in RUNS:
        backend = openai_backend.OpenAIBackend(
            api_key="ollama", base_url=OLLAMA_BASE_URL
        )
        for i in range(1, n + 1):
            print(f"--- {candidate} run {i}/{n} ---", flush=True)
            result = harness._run_segmentation_once(  # noqa: SLF001 - intentional reuse, see module docstring
                candidate=candidate,
                backend_kind="openai_compatible_local",
                backend=backend,
                model=model,
                story_name=story_name,
                story_text=story_text,
                max_tokens=harness.DEFAULT_SEGMENTATION_MAX_TOKENS,
                temperature=TEMPERATURE,
                system_prompt_suffix=harness._SEGMENTATION_RETRY_REMINDER,  # noqa: SLF001
            )
            d = result.to_dict()
            d["run_index"] = i
            d["reminder_mode"] = "eager_permanent"
            print(json.dumps(d, indent=2))
            all_results.append(d)

    out_path = _HERE / "results_local_reminder_eager.json"
    out_path.write_text(json.dumps(all_results, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {out_path}")

    succeeded = sum(1 for r in all_results if r["success"])
    print(f"\nSummary: {succeeded}/{len(all_results)} succeeded with eager reminder")


if __name__ == "__main__":
    main()
