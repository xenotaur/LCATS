---
execution_id: 2026_10_09_18_46_49_WI_SF_0114_FAIL_LOUD_STRUCTURED_OUTPUT_CLOSEOUT_NOTE
prompt_id: PROMPT(AD_HOC:WI_SF_0114_FAIL_LOUD_STRUCTURED_OUTPUT_CLOSEOUT_NOTE)[2026-10-09T18:46:31+00:00]
work_item: AD_HOC
status: landed
rerun_of: 2026_10_09_16_00_33_WI_SF_0114_FAIL_LOUD_STRUCTURED_OUTPUT
pr: https://github.com/xenotaur/LCATS/pull/490
commit: fa33d1bbf589b5858ae1c14cf0777001ba42d61a
created_at: 2026-10-09T18:46:49+00:00
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/490
session_transcript: claude-app:dff6f127-44db-417c-9b1e-0f962af4c00a
---

# Summary

Closeout note for PR 490 (the implementation of WI-SF-0114), landed through /lrh-execute and /lrh-land. The primary execution record is immutable, so the CHAIN-NOTE lives in this record.

# Result

PR 490 was squash-merged as fa33d1bbf589b5858ae1c14cf0777001ba42d61a at head 84b46768ba643a06393b64b649e64cc8e07fa88f. The Heinlein and evidence stages of the Worldcon spike runner now fail loudly on mismatched, missing or empty model output: Heinlein criteria with the wrong keys, missing required fields or non-string ID lists quarantine the stage; an evidence response with a missing or non-list evidence key, or whose candidates are all quarantined, fails the story; an explicit empty evidence list stays valid with a run-log warning; the shared text fallback unwraps exactly one fenced JSON block through the new default-off strict_fence option of lcats.utils.extract_json and logs each unwrap; and the evidence and Heinlein prompts name the tool schema's keys. Five Codex and Copilot threads were fixed and resolved, including making supporting_evidence_ids and rationale required, which is stricter than the work item; a pre-push diff review found a quadratic regex in the strict fence, which was replaced; and two cold reviews were clean after fixes. One existing test that encoded the old silent default was rewritten as the work item requires. All four CI checks passed on the final head. The primary, review, confirm and self-review records were landed with this closeout and WI-SF-0114 was resolved. WS-KNIGHT-NOVUM-ANALYSIS stays open. The canary was not rerun.

CHAIN-NOTE: cycles=3; stops=3; gates=[review, self-review, self-review]; friction=scope-widening; self_review_rounds=2; note="implementation run via /lrh-execute; 5 bot threads fixed (required Heinlein fields, string members, mixed and baseline tests, valid prompt example), quadratic strict-fence regex found and replaced, two cold reviews clean after fixes; one existing test rewritten as the work item requires; WI resolved"

# Validation

- lrh validate reported 0 errors before and after closeout.
- CI: coverage, lint and both test checks passed on the final head; scripts/test passed with 2547 tests.

# Follow-up

- Rerun the Heinlein canary as its own step (baseline plus three local trials, manifest expectations unchanged) and count fenced_json_unwrapped, no_tool_call_json_fallback and evidence-stage failures in the new report.
- Consider a follow-up on _existing_evidence_ids, which still silently drops unknown evidence IDs.
