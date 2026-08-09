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
- **2026-08-09 follow-up, after credits were added** - 3 distinct real
  attempts at `harness.DEFAULT_SEGMENTATION_MAX_TOKENS` (16384), plus one
  rejected probe that never reached the model at all (a review finding on
  this follow-up's own PR, #272, correctly identified that the first
  write-up conflated these into "both attempts reproduced the same
  result," which overstated what the rejected probe actually showed -
  nothing, since it errored before either condition could run):
  1. First real attempt: **baseline** `truncated_output` (101.2s) -
     **modified** `extraction_or_alignment_error` (38.4s).
  2. Probe: attempted `max_tokens=24576` to rule out a fixable
     truncation. Rejected outright by the OpenAI API before contacting
     the model at all: *"max_tokens is too large: 24576. This model
     supports at most 16384 completion tokens, whereas you provided
     24576."* - 16384 is `gpt-4o`'s own hard ceiling, not a value this
     harness chose and could raise. No comparable result from this
     attempt on either condition.
  3. Confirmation re-run at the reverted default: **baseline**
     `truncated_output` (106.1s) - **modified**
     `extraction_or_alignment_error` (68.1s), reproducing attempt 1.
  4. Review-round re-run (after fixing `_call_once` to preserve real
     `extraction_error`/`alignment_error`/`validation_error` detail
     instead of collapsing to the bare classification string - a
     separate review finding on PR #272): **baseline** `truncated_output`
     (101.2s) - **modified** `truncated_output` this time (100.8s),
     rather than the `extraction_or_alignment_error` seen in attempts 1
     and 3. Only this latest attempt's raw data is committed in
     `results_frontier_paired_openai.json` (the script always writes the
     most recent run); attempts 1 and 3 are preserved here in prose since
     the script overwrites its own output file each run.

  **Baseline hit `truncated_output` in all 3 real attempts (3/3)** - a
  reproducible, not one-off, result. **Modified failed in all 3 real
  attempts too (3/3)**, but via two different observed error
  classifications (`extraction_or_alignment_error` x2,
  `truncated_output` x1) - both consistent with running out of the same
  16384-token budget at a slightly different point in the response each
  time, but this is an inference from the pattern, not confirmed for the
  two `extraction_or_alignment_error` occurrences specifically (their
  underlying detail wasn't preserved by `_call_once` until attempt 4's
  code fix, and that attempt happened to land on `truncated_output`
  instead). This story/prompt combination cannot reliably complete on
  `gpt-4o` within its own maximum possible output, on either condition,
  independent of the reminder - a structural finding, not evidence the
  reminder specifically caused either failure.

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
