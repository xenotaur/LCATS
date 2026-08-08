# wi_llm_0059

Investigation-specific scripts for `WI-LLM-0059`: does appending
`WI-LLM-0051`'s tested reminder to the real, production
`SCENE_SEQUEL_SYSTEM_PROMPT` (`lcats/src/lcats/analysis/scene_analysis.py`)
- not just `common/harness.py`'s own harness-scoped retry copy - help
local-model segmentation reliability, and does it regress the frontier
paths (`AnthropicBackend`, `OpenAIBackend`) that prompt is shared with?

Unlike the per-candidate `benchmark*.py` scripts elsewhere in
`model_comparison/`, these two scripts call
`common/harness._run_segmentation_once()` directly (the same underlying
single-call function `run_segmentation()`'s retry path already uses)
rather than the retry-wrapped public entry point, so the reminder can be
tested as an *eager/permanent* system-prompt suffix instead of only on a
second attempt after a first failure.

## Scripts and results

- `run_local_reminder.py` - real Ollama calls: `qwen3:8b` x3 and
  `qwen3:30b-a3b` x1 (a first-ever test for that model), reminder
  appended eagerly. Free (local inference). Result:
  `results_local_reminder_eager.json` - **0/4 succeeded** this round.
  The 3 `qwen3:8b` calls combine with `WI-LLM-0051`'s prior 5-call
  `qwen3:8b` sample using the identical mechanism (2/5 succeeded):
  **2/8 (25%) combined for `qwen3:8b`**, consistent with (not
  contradicting) `WI-LLM-0051`'s original 40% estimate - a 0/3 result
  this round is unsurprising noise at a true ~20-30% success rate. The
  single `qwen3:30b-a3b` call also failed but is a separate data point
  (different model, not poolable with the `qwen3:8b` figure above).
- `run_frontier_paired.py` - real, billed calls: 3 paired baseline/
  modified `claude-opus-4-8` calls (Anthropic), 1 paired baseline/
  modified `gpt-4o` call (OpenAI). Result:
  `results_frontier_paired.json` - Anthropic showed no regression (3/3
  success both conditions, comparable latency; this is the first
  `anthropic_opus` segmentation-stage data recorded in this proposal's
  history, so the segment-count spread has no prior-session baseline to
  compare against, but shows no systematic shift between the two
  conditions on its own); OpenAI could not be verified at all in this
  session (real API key present, but the organization had zero
  remaining credits - both baseline and modified calls failed identically
  with `429 insufficient_quota`).

## Verdict

Per `WI-LLM-0059`'s own Required Changes item 5, an untested OpenAI path
forces the documented no-change outcome regardless of the other two
results. `SCENE_SEQUEL_SYSTEM_PROMPT` was **not** edited - see
`PROP-ERW-LOCAL-MODEL-EVALUATION`'s "Decision 3 update (2026-08-08,
production system-prompt reminder, `WI-LLM-0059`)" section for the full
write-up. Re-running just `run_frontier_paired.py`'s OpenAI leg once real
API credits are available is a legitimate, low-cost way to revisit this
verdict without repeating the Anthropic or local legs.
