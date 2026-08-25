---
execution_id: 2026_08_24_20_59_52_SF_CONTRACT_HARDENING_PLANNING_REVIEW
prompt_id: PROMPT(AD_HOC:SF_CONTRACT_HARDENING_PLANNING_REVIEW)[2026-08-24T20:37:04+00:00]
work_item: AD_HOC
status: in_progress
rerun_of:
pr: https://github.com/xenotaur/LCATS/pull/390
commit: 20721b3a
created_at: 2026-08-24T20:59:52+00:00
agent: codex_app
instruction_source: https://github.com/xenotaur/LCATS/pull/390
session_transcript: pending
---

# Summary

Address the four review findings on PR #390 concerning Knight/Suvin (Novum) terminology and the unsound use of an all-positive deterministic fixture for semantic canary assertions.

# Result

Updated the WI-SF-0013 and WI-SF-0015 titles and terminology to name Suvin (Novum) explicitly. Updated the contract canary runbook to require local-model semantic trials and to restrict the existing all-positive fixture to structural checks unless a documented contrastive fixture is used. No runtime code, paid calls, or corpus changes were made. No `rerun_of` link was added because this planning PR has three AD_HOC creation records rather than a single branch-slug primary implementation record.

# Validation

Using the pinned tool environment (`PATH=/Users/centaur/anaconda3/bin:$PATH`) and PR source path (`PYTHONPATH=src`): `scripts/version tools` confirmed Black 25.11.0 and Ruff 0.15.0; `scripts/format --check --diff` passed with 225 files unchanged; `scripts/lint` passed; `scripts/test` passed with 2,116 tests; `git diff --check` passed; `lrh validate` reported 0 errors and 219 pre-existing warnings.

# Follow-up

Run `/lrh-confirm-fixes https://github.com/xenotaur/LCATS/pull/390` against the new head, then continue the governed landing chain. `session_transcript` remains `pending` until a durable Codex task pointer is available.
