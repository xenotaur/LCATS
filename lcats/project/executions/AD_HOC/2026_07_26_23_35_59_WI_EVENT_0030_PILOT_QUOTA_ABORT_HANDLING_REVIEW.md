---
execution_id: 2026_07_26_23_35_59_WI_EVENT_0030_PILOT_QUOTA_ABORT_HANDLING_REVIEW
prompt_id: PROMPT(AD_HOC:WI_EVENT_0030_PILOT_QUOTA_ABORT_HANDLING_REVIEW)[2026-07-26T23:35:32-04:00]
work_item: AD_HOC
status: in_progress
rerun_of: 2026_07_26_23_24_58_WI_EVENT_0030_PILOT_QUOTA_ABORT_HANDLING
pr: https://github.com/xenotaur/LCATS/pull/166
commit: a6b768ff
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/166
session_transcript: pending
created_at: 2026-07-26T23:35:59-04:00
---

# Summary

Address PR #166 review feedback: two chatgpt-codex-connector comments (P1
auth-detection gap, P2 late abort/dropped usage) and one
copilot-pull-request-reviewer comment (missing unit test coverage).

# Result

- **P1 (chatgpt-codex-connector): auth failures not fully matched.**
  `_FATAL_ERROR_SUBSTRINGS` used narrow phrases (`"invalid api key"`,
  `"authentication_error"`) that miss real wordings like "authentication
  failed" or "Incorrect API key provided". Widened to `"api key"` /
  `"authentication"` (matching `_classify_api_error`'s own broader auth
  check) and `"quota"` (matching its quota check). Additionally, for the
  segmentation call site - which has the classified `api_error` dict
  available, not just a message string - now trusts
  `seg_error.get("should_abort_batch")` directly instead of re-deriving
  fatality from text.
- **P2 (chatgpt-codex-connector): fatal check happens too late in the ERW
  pipeline.** `_run_erw_pipeline`'s per-segment loop previously ran
  entity/event/relation/discourse extraction for every segment
  unconditionally before `run_story` ever inspected the aggregated
  `extraction_errors`. Moved the fatal check inside the per-segment loop
  (checked right after each `process_segment()` call) and into the
  story-relation block, so a multi-segment story aborts after the first
  fatal failure instead of issuing several more doomed requests per
  remaining segment.
- **P2 (chatgpt-codex-connector): usage records dropped on abort.**
  Raising `FatalPilotError` from inside `_run_erw_pipeline` previously
  prevented `run_story` from returning any of `pipeline_result["usage"]`
  for the passes that succeeded before the abort. `FatalPilotError` now
  carries a `usage_rows` attribute; `_run_erw_pipeline` populates it with
  usage accumulated so far before raising, `run_story` tags those rows with
  `story_id`/`genre` when re-raising, and `main()`'s per-story except
  handler extends its `usage_rows` list with them before writing
  `pilot_usage.jsonl`.
- **copilot-pull-request-reviewer: missing test coverage.** Added a
  table-driven case (`anthropic_credit_balance`) and a dedicated
  `test_anthropic_credit_balance_sets_abort_batch` test asserting Anthropic's
  real error shape (`status=400`, `type=invalid_request_error`, "credit
  balance" message) classifies as `category="quota_exceeded"`,
  `should_abort_batch=True`.

# Validation

- `scripts/format --check --diff` / `scripts/lint` - clean (black
  reformatted two files after edits; re-verified clean after).
- `scripts/test` - 1438 tests pass (2 new).
- Manual check: `_check_fatal()` now raises on "authentication failed" and
  "Incorrect API key provided" (the exact reviewer-cited wordings), and
  correctly carries a supplied `usage_rows` list through to the raised
  exception.

# Follow-up

- `session_transcript: pending` should be updated to `claude-app:<session-id>`
  after this session ends.
- Proceed to `/lrh-confirm-fixes https://github.com/xenotaur/LCATS/pull/166`
  to verify fixes against the current diff and resolve review threads, then
  the merge gate, then closeout.
