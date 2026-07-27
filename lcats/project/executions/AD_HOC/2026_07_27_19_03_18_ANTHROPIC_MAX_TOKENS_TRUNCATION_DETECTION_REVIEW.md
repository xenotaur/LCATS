---
execution_id: 2026_07_27_19_03_18_ANTHROPIC_MAX_TOKENS_TRUNCATION_DETECTION_REVIEW
prompt_id: PROMPT(AD_HOC:ANTHROPIC_MAX_TOKENS_TRUNCATION_DETECTION_REVIEW)[2026-07-27T19:03:06-04:00]
work_item: AD_HOC
status: in_progress
rerun_of: 2026_07_27_18_54_02_ANTHROPIC_MAX_TOKENS_TRUNCATION_DETECTION
pr: https://github.com/xenotaur/LCATS/pull/170
commit: 1d9a14ed
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/170
session_transcript: pending
created_at: 2026-07-27T19:03:18-04:00
---

# Summary

Address review feedback on PR #170 (max_tokens truncation detection).

# Result

One open review comment from chatgpt-codex-connector (P2):
"Preserve billed usage on truncation errors" — when a tool response hits
`max_tokens`, the provider's `message`/`response` already carries token
usage, but `TruncatedResponseError` only preserved `stop_reason`/`max_tokens`,
so `JSONPromptExtractor.extract()`'s exception path always returned
`usage=None`, and `event_role_world.processor._pass_usage_from_extraction()`
recorded zero tokens in `pilot_usage.jsonl` for every truncated call — even
though the provider had already billed for the output tokens generated
before hitting the ceiling.

Triage: presence (still present, confirmed by reading the code) — valid
(a real cost-undercounting bug, not just a nitpick) — feasible (small,
localized change). Fixed by:

- `lcats/lcats/llm/backend.py`: `TruncatedResponseError` gained
  `input_tokens`/`output_tokens` fields (default 0).
- `lcats/lcats/llm/anthropic_backend.py`: passes
  `message.usage.input_tokens`/`.output_tokens` when raising.
- `lcats/lcats/llm/openai_backend.py`: passes
  `response.usage.prompt_tokens`/`.completion_tokens` when raising (guarding
  `usage` being `None`, matching the existing non-tool path's guard).
- `lcats/lcats/analysis/llm_extractor.py`: `_normalize_api_error` surfaces
  `input_tokens`/`output_tokens` in the payload for `TruncatedResponseError`;
  `extract()`'s exception handler now builds `usage` from `api_error` when
  those keys are present, instead of unconditionally returning `None`.

Added direct test coverage for all of the above (both backends' truncation
paths asserting `.input_tokens`/`.output_tokens` on the raised exception,
plus an `extract()`-level test asserting `result["usage"]` is populated from
a `TruncatedResponseError`).

# Validation

- `pytest tests/llm_tests/anthropic_backend_test.py tests/llm_tests/openai_backend_test.py tests/analysis_tests/llm_extractor_test.py` (from `lcats/`) — 113 passed.
- `scripts/test` (from `lcats/`) — full suite, 1446 passed.
- `scripts/lint` (from `lcats/`) — ruff clean; black clean on all files touched by this PR (pre-existing, unrelated skew remains on `lcats/gettenberg/metadata.py`, not touched here).
- `lrh validate` (from `lcats/`) — 0 errors (43 pre-existing warnings, unrelated).
- Review thread (`PRRT_kwDOKlhIbM6UO0EQ`) resolved via `gh api graphql resolveReviewThread` after the fix landed.

# Follow-up

None beyond what PR #170's primary execution record already lists (running
the real pilot again with this fix in place is still the next concrete
step for WI-EVENT-0030).
