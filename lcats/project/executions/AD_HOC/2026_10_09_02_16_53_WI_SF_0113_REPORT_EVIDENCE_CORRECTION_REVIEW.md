---
execution_id: 2026_10_09_02_16_53_WI_SF_0113_REPORT_EVIDENCE_CORRECTION_REVIEW
prompt_id: PROMPT(AD_HOC:WI_SF_0113_REPORT_EVIDENCE_CORRECTION_REVIEW)[2026-10-09T02:16:45+00:00]
work_item: AD_HOC
status: in_progress
rerun_of: 2026_10_09_01_01_09_WI_SF_0113_REPORT_EVIDENCE_CORRECTION
pr: https://github.com/xenotaur/LCATS/pull/489
commit: 838d831f7a5d61e80ba34a4175074ec0b247f6f1
created_at: 2026-10-09T02:16:53+00:00
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/489
session_transcript: pending
---

# Summary

Review-response round for PR 489 (the canary report correction). Three open Codex and Copilot threads were triaged against the code and the owner approved the fixes.

# Result

- Fixed (Codex P2 and two Copilot threads): the correction repeated an error of the original analysis. It gave the evidence schema keys as quote and type, but the schema's keys are quote and evidence_type (run_worldcon_spike.py:2371-2400). The trial 2 raw items carry quotation where the schema key is quote, and have neither evidence_type nor type; the evidence builder would coerce a type into evidence_type (evidence.py:90-95), which is why the baseline's type keys worked, but these items had nothing to coerce. The report's finding 8, this PR's earlier execution record and the PR body now say so.
- Added, as approved: a sentence in finding 8 that in trials 1 to 3 the Vonnegut evidence stage took the runner's text fallback every time (no_tool_call_json_fallback, run_worldcon_spike.py:824-850) while the baseline used a real tool call, labeled a correlation across three trials and not a demonstrated cause, plus the note that wrong keys also appeared in real tool calls.
- Fix commit: 838d831f7a5d61e80ba34a4175074ec0b247f6f1.

# Validation

- scripts/format --check --diff passed with the CI-pinned black 25.11.0; lrh validate reported 0 errors; git diff --check on the report was clean.

# Follow-up

- Run confirm-fixes, then the merge and closeout ask.
- Update session_transcript from pending at closeout.
