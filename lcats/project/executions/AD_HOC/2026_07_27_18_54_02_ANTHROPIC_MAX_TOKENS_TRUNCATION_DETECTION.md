---
execution_id: 2026_07_27_18_54_02_ANTHROPIC_MAX_TOKENS_TRUNCATION_DETECTION
prompt_id: PROMPT(AD_HOC:ANTHROPIC_MAX_TOKENS_TRUNCATION_DETECTION)[2026-07-27T18:34:09-04:00]
work_item: AD_HOC
status: in_progress
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/170
commit: ad57425b
agent: claude_app
instruction_source: 2026-07-27-erw-pipeline-structured-output-reliability-audit.md, followed by a confirmed implementation plan presented in-session
session_transcript: pending
created_at: 2026-07-27T18:54:02-04:00
---

# Summary

Implement the fix identified by the ERW pipeline structured-output reliability
audit (PR #169): the real WI-EVENT-0030 pilot crashed 3x on malformed tool-use
output because Anthropic silently truncates a tool_use response mid-generation
when it hits the max_tokens ceiling, and `AnthropicBackend.complete()` never
checked `stop_reason` for this. Add truncation detection to both LLM backends,
a new error classification category, and raise the ERW extractors' max_tokens
ceiling so real segments have headroom.

# Result

- `lcats/lcats/llm/backend.py`: added `TruncatedResponseError(RuntimeError)`
  carrying `stop_reason`/`max_tokens`, shared by both backend adapters.
- `lcats/lcats/llm/anthropic_backend.py`: `complete()` now raises
  `TruncatedResponseError` when a tool was requested and
  `message.stop_reason == "max_tokens"`, before attempting to read the
  (possibly incomplete/invalid) tool_use block.
- `lcats/lcats/llm/openai_backend.py`: symmetric check on
  `choice.finish_reason == "length"` when a tool was requested.
- `lcats/lcats/analysis/llm_extractor.py`: `_normalize_api_error` recognizes
  `TruncatedResponseError` directly (bypassing the generic status/code/message
  inference path); `_classify_api_error` gained a new `truncated_output`
  category (`can_retry=False`, `should_abort_batch=False`,
  `suggested_action="retry_with_higher_max_tokens"`) — distinct from existing
  categories, none of which mean "same request, bigger max_tokens."
- `experiments/03_cross_segment_relation_pilot/run_pilot.py`: `_build_erw_extractors`
  now sets `extractor.max_tokens = _ERW_MAX_TOKENS` (16384) for all five ERW
  extractors, up from `JSONPromptExtractor`'s default of 4096. Anthropic bills
  actual output tokens generated, not this ceiling, so this is free for calls
  that finish early; `claude-opus-4-8` supports up to 128k output tokens.
- No auto-retry logic was added inside either backend — they raise and
  classify clearly; the caller (a future pilot run/retry loop) decides whether
  to retry with a bumped max_tokens, matching the existing `FatalPilotError`
  pattern of explicit signaling over silent auto-retry.

# Validation

- `pytest tests/llm_tests/anthropic_backend_test.py tests/llm_tests/openai_backend_test.py tests/analysis_tests/llm_extractor_test.py` (run from `lcats/`) — 110 passed, including new truncation-detection tests for both backends (tool-requested vs. no-tool paths) and the new classification category.
- `scripts/test` (from `lcats/`) — full suite, 1446 passed.
- `scripts/lint` (from `lcats/`) — ruff clean; black flags one pre-existing, unrelated file (`lcats/gettenberg/metadata.py`) due to known formatter version skew, not touched by this change.
- `lrh validate` (from `lcats/`) — no new errors/warnings introduced by this change (pre-existing `current_focus.md`/owner-role warnings unrelated).

# Follow-up

- The real WI-EVENT-0030 pilot run still needs to be attempted again with this
  fix in place — it has never completed successfully. This PR only fixes the
  detection/signaling; running the pilot end-to-end and confirming no more
  truncation crashes occur is the next concrete step.
- No retry loop exists yet for the `truncated_output` category — a caller
  hitting it today still has the run fail for that segment/story. Whether to
  add an automatic retry-with-higher-max_tokens loop in `run_pilot.py` is an
  open follow-up, deliberately deferred per the confirmed plan (raise and
  classify now; decide on retry policy separately, informed by how often this
  actually recurs at 16384).
