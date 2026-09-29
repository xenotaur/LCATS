---
execution_id: 2026_09_29_06_22_59_WI_LINGUISTICS_0014_REVIEW
prompt_id: PROMPT(AD_HOC:WI_LINGUISTICS_0014_REVIEW)[2026-09-29T06:22:36+00:00]
work_item: AD_HOC
status: in_progress
rerun_of: 2026_09_29_05_07_47_WI_LINGUISTICS_0014
pr: https://github.com/xenotaur/LCATS/pull/461
commit: f160510f
created_at: 2026-09-29T06:22:59+00:00
agent: codex
instruction_source: lcats/project/work_items/proposed/WI-LINGUISTICS-0014.md
session_transcript: codex-app:01a032cd-cef2-73c0-9714-b61b36ae4513
---

# Summary

Address the five actionable review findings raised on PR 461: protect the
repository-root data check, gate downstream POS-dependent items on
`WI-LINGUISTICS-0014`, correct the repository-relative proposal path, document
validation working directories, and make the workstream’s tenth-item ordering
and delivery constraints explicit.

# Result

Updated `WI-LINGUISTICS-0008`, `WI-LINGUISTICS-0014`,
`WI-VISUALIZE-0093`, and `WS-COMPARATIVE-LEXICAL-VISUALIZATION`; committed as
`f160510f` and pushed to PR 461. All five review findings were addressed.

# Validation

- `scripts/develop` installed the declared project toolchain.
- With `/Users/centaur/anaconda3/bin` first on `PATH`, `scripts/version tools` passed.
- `scripts/format --check --diff` passed with Black 25.11.0.
- `scripts/lint` passed.
- `scripts/test` passed: 2,364 tests, 0 failures.
- `lrh validate` passed with 0 errors and 341 pre-existing warnings.
- `git diff --exit-code -- corpora experiments/07_linguistics_corpora` passed from the repository root.
- `git diff --check` passed.

# Follow-up

The PR now awaits the confirm-fixes pass and automated review of the new head.
No implementation work, full-corpus run, sample-membership change, audit
overwrite, or POS figure generation was performed.
