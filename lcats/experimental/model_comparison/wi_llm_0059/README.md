# wi_llm_0059

Investigation-specific scripts for `WI-LLM-0059`: does appending
`WI-LLM-0051`'s tested reminder to the real, production
`SCENE_SEQUEL_SYSTEM_PROMPT` (`lcats/src/lcats/analysis/scene_analysis.py`)
- not just `common/harness.py`'s own harness-scoped retry copy - help
local-model segmentation reliability, and does it regress the frontier
paths (`AnthropicBackend`, `OpenAIBackend`) that prompt is shared with?

`run_local_reminder.py` calls `common/harness._run_segmentation_once()`
directly (the same underlying single-call function `run_segmentation()`'s
retry path already uses) rather than the retry-wrapped public entry
point, so the reminder can be tested as an *eager/permanent*
system-prompt suffix instead of only on a second attempt after a first
failure. `run_frontier_paired.py` calls `scene_analysis.make_segment_
extractor()` directly instead, so it can persist each call's actual
segments (type/summary), not just `BenchmarkResult`'s bare
`segment_count` - a P1 review finding on this WI's own implementation PR
(#266) correctly identified that a count alone cannot support a claim
about output *quality*.

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
- `run_frontier_paired.py --legs anthropic|openai|all` - real, billed
  calls: 3 paired baseline/modified `claude-opus-4-8` calls (Anthropic,
  `results_frontier_paired_anthropic.json`), 1 paired baseline/modified
  `gpt-4o` call (OpenAI, `results_frontier_paired_openai.json`), merged
  into `results_frontier_paired.json`. Anthropic: 3/3 success both
  conditions, comparable latency (25.4-34.7s) - but reading the actual
  segments (not just counts) shows 2 of 3 modified-condition runs split
  the story's ending into an extra segment (baseline stayed at 4 all 3
  times; modified produced 4, 5, 5) - the same split pattern both times,
  not one-off noise, in mild tension with the production prompt's own
  "prefer FEWER, LARGER segments" rule. Not a functional failure - every
  segment across all 6 calls used a valid label and read coherently - but
  not a clean "neutral" result either. OpenAI originally could not be
  verified at all (real API key present, but the organization had zero
  remaining credits - both baseline and modified calls failed identically
  with `429 insufficient_quota`).
- **2026-08-09 follow-up, after credits were added:** `python
  run_frontier_paired.py --legs openai` re-run twice (once at the
  default `max_tokens`, once after attempting to raise it to 24576 to
  rule out a fixable truncation). Both real attempts reproduced the same
  result: **baseline failed with `truncated_output`** (hit `gpt-4o`'s own
  hard maximum of 16384 completion tokens before the tool call finished)
  and **modified failed with `extraction_or_alignment_error`** (a
  different failure mode). The OpenAI API rejected `max_tokens=24576`
  outright ("max_tokens is too large: 24576. This model supports at most
  16384 completion tokens, whereas you provided 24576.") - 16384 is
  `gpt-4o`'s hard ceiling, not a value this harness chose and could
  raise. This story/prompt combination cannot complete on `gpt-4o`
  within its own maximum possible output at all, independent of the
  reminder.

## Verdict

Per `WI-LLM-0059`'s own Required Changes item 5, an unverified OpenAI
path forces the documented no-change outcome regardless of the Anthropic
result - now confirmed by a real, credits-enabled attempt rather than an
absence of one. `SCENE_SEQUEL_SYSTEM_PROMPT` was **not** edited - see
`PROP-ERW-LOCAL-MODEL-EVALUATION`'s "Decision 3 update (2026-08-08,
production system-prompt reminder, `WI-LLM-0059`)" section (updated
2026-08-09) for the full write-up. Even a working OpenAI result would not
have made this an obviously-safe edit, given the Anthropic granularity
side effect above - a future revisit should weigh that finding on its
own merits. A real OpenAI/GPT comparison for this question would now need
a smaller/shorter test story that fits within `gpt-4o`'s 16384-completion-
token ceiling - a methodology fix, not just a bigger API budget.
