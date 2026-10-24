---
execution_id: 2026_10_15_00_58_11_WI_SF_0120_PERSIST_REQUEST_FIELDS
prompt_id: PROMPT(WI-SF-0120:WI_SF_0120_PERSIST_REQUEST_FIELDS)[2026-10-13T19:34:11+00:00]
work_item: WI-SF-0120
status: landed
rerun_of:
pr: https://github.com/xenotaur/LCATS/pull/509
commit: 6d2678ff38cc343721aad0cb1943c88a59d40468
created_at: 2026-10-15T00:58:11+00:00
agent: claude_app
instruction_source: project/work_items/proposed/WI-SF-0120.md
session_transcript: claude-app:dff6f127-44db-417c-9b1e-0f962af4c00a
---

# Summary

Executed WI-SF-0120 through /lrh-execute: the tool-forcing request of each model call is now observable. OpenAIBackend has an optional, off-by-default request_recorder that reports the provider request as built, before the network call, and the Worldcon spike runner persists one request record per attempt.

# Result

- Changed src/lcats/llm/openai_backend.py and backend.py (a separate optional RequestRecordingBackend Protocol), experimental/science_fiction_analysis_trial/run_worldcon_spike.py (_RequestCapture, _write_request_record and record_request calls on every exit path of _run_model_stage) and heinlein_canary_runbook.md, plus tests in tests/llm_tests and tests/analysis_tests/science_fiction. PR 509.
- Record files are named request-<stage>[-attempt-N].json because the raw-artifact index globs <stage>*.json and would otherwise list them as attempts. Each holds version, attempt, effective max_tokens, outcome, request_source (provider or runner) and the request; no system prompt, messages, story text, absolute path or credential.
- Fingerprints, prompt versions, checkpoint reuse and resume validation are unchanged. No live model call was made.

# Validation

- Full scripts/test passes (2566 tests) with PYTHONPATH=src; plain scripts/test imports a different checkout in this environment and fails for unrelated reasons.
- scripts/format --check --diff and scripts/lint pass; black and ruff on run_worldcon_spike.py show only the pre-existing main failures (4 black hunks, ruff F601). lrh validate reports 0 errors; git diff --check clean.
- 14 new tests; six deliberate mutations were each caught. Black's reformatting of four unrelated spots was reverted so the diff shows only additions.

# Follow-up

- The recorder stays set on the backend after a stage until the next stage replaces it; harmless because the runner builds a backend per run, left as is.
- A later live control run (WI-SF-0119's design) can use these records once WI-SF-0121's private server is in place.
