---
execution_id: 2026_09_27_20_02_47_ADD_RETRY_ACCOUNTING_AND_RESUMABLE_WORLDCON_ORCHESTRATION
prompt_id: PROMPT(WI-SF-0014:ADD_RETRY_ACCOUNTING_AND_RESUMABLE_WORLDCON_ORCHESTRATION)[2026-09-27T19:41:24+00:00]
work_item: WI-SF-0014
status: in_progress
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/453
commit: 316c97ca
created_at: 2026-09-27T20:02:47+00:00
agent: codex_app
instruction_source: project/work_items/proposed/WI-SF-0014.md
session_transcript: codex-app:01a02338-d9c7-7313-8ed5-fb9c1643bef1
---

# Summary

Implement the retry, usage-accounting, and resumable stage orchestration
required by `WI-SF-0014`, while keeping the runner experiment-local and
excluding paid calls, the Worldcon sample, corpus sidecars, and promotion.

# Result

Added one bounded truncation retry with doubled token capacity, one bounded
transient provider/network retry, explicit no-retry handling for content-filter
and deterministic validation failures, persisted attempt artifacts and usage,
fingerprinted evidence/Knight/Suvin stage checkpoints, and `--resume` support.
Updated the runbook and added regression coverage for retries, retry artifacts,
effective token provenance, validation no-retry behavior, and package-relative
checkpoint reuse.

# Validation

- `PYTHONPATH=src scripts/test`: passed, 2,355 tests.
- Targeted Worldcon suite: passed, 29 tests.
- Black check with the available formatter: passed.
- `git diff --check`: passed.
- `lrh validate`: passed with 0 errors and 337 pre-existing warnings.

# Follow-up

- Review and land PR #453 through the LRH lifecycle.
- Keep the repeated two-story canary (`WI-SF-0015`) separately gated.
- Do not run paid calls or the 146-story sample under this work item.
