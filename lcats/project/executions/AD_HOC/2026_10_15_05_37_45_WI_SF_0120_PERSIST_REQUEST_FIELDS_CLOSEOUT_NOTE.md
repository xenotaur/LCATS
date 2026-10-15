---
execution_id: 2026_10_15_05_37_45_WI_SF_0120_PERSIST_REQUEST_FIELDS_CLOSEOUT_NOTE
prompt_id: PROMPT(AD_HOC:WI_SF_0120_PERSIST_REQUEST_FIELDS_CLOSEOUT_NOTE)[2026-10-15T05:37:28+00:00]
work_item: AD_HOC
status: landed
rerun_of: 2026_10_15_00_58_11_WI_SF_0120_PERSIST_REQUEST_FIELDS
pr: https://github.com/xenotaur/LCATS/pull/509
commit: 6d2678ff38cc343721aad0cb1943c88a59d40468
created_at: 2026-10-15T05:37:45+00:00
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/509
session_transcript: claude-app:dff6f127-44db-417c-9b1e-0f962af4c00a
---

# Summary

Closeout note for PR 509 (the execution of WI-SF-0120, request-record persistence), landed through /lrh-execute and /lrh-land. The primary execution record is immutable, so the CHAIN-NOTE lives in this record.

# Result

PR 509 was squash-merged as 6d2678ff38cc343721aad0cb1943c88a59d40468 at head 55f8f913a15e8c3d7bf0607b4a3390e31a382e32. OpenAIBackend gained an optional, off-by-default request_recorder (advertised through a separate optional RequestRecordingBackend Protocol, so LLMBackend and the other backends are untouched) that reports the provider request as built, before the network call, so failed attempts are recorded too. The Worldcon spike runner writes one request-<stage>[-attempt-N].json per attempt with its outcome, effective max_tokens and request source (provider for the OpenAI backend, runner otherwise), named so the raw-artifact index glob does not list them as attempts. The records hold no system prompt, messages, story text, absolute path or credential; fingerprints, prompt versions, checkpoint reuse and resume validation are unchanged, and the runbook's inspection checklist covers the new files. A cold diff review found no blocking defects; two cosmetic items were fixed with approval and a lingering recorder after a stage was left as is. Copilot recommended approval with no findings and Codex's open-time review left no comments, so there were no review threads, no review-response round and no confirm record. All four CI checks passed on the final head. The primary and self-review records were landed with this closeout and WI-SF-0120 was resolved. WS-KNIGHT-NOVUM-ANALYSIS stays open.

CHAIN-NOTE: cycles=1; stops=3; gates=[chain-authorization, self-review-triage, merge]; friction=editable-install-points-at-sibling-checkout; note="implementation run via /lrh-execute; first full scripts/test failed (7 failures, 39 errors) because the editable install imports lcats from another checkout, resolved by running with PYTHONPATH=src (2566 tests pass); black's reformatting of unrelated lines was reverted; six mutation checks caught by the new tests; no review threads; WI resolved"

# Validation

- lrh validate reported 0 errors before and after closeout.
- CI: coverage, lint and both test checks passed on the final head. Full scripts/test passed (2566 tests) with PYTHONPATH=src.

# Follow-up

- The editable install of lcats in this environment still points at a different checkout, so plain scripts/test fails here; fixing it is a separate environment decision.
- WI-SF-0121 (private Ollama server) and WI-SF-0122 (unknown evidence IDs) remain proposed; the live control run from WI-SF-0119's design can use these request records.
- run_worldcon_spike.py still fails black --check (4 hunks) and ruff F601 on main; not caused by this change.
