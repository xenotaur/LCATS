---
execution_id: 2026_08_25_02_38_39_WI_LINGUISTICS_0006_REVIEW
prompt_id: PROMPT(AD_HOC:WI_LINGUISTICS_0006_REVIEW)[2026-08-25T02:38:19+00:00]
work_item: AD_HOC
status: in_progress
rerun_of: 2026_08_25_01_44_10_WI_LINGUISTICS_0006
pr: https://github.com/xenotaur/LCATS/pull/392
commit: 9cbe88b0
agent: codex_app
instruction_source: promptspace:lrh-review-response PR 392
session_transcript: pending
created_at: 2026-08-25T02:38:39+00:00
---

# Summary

Addressed two reviewer findings on PR #392 for
`WI-LINGUISTICS-0006`.

# Result

- Fixed `lexicon.benchmark_queries` so unvalidated or malformed artifacts no
  longer raise `TypeError` when denominator fields are missing or have the
  wrong JSON type. The benchmark now treats non-object denominators,
  non-integer token counts, negative token counts, and non-list count rows as
  zero for visit-estimate metadata while preserving indexed query behavior for
  valid rows.
- Moved the `--include-lexicon` dependency check into the CLI before backend
  construction. Invalid invocations now return status 2 with the explicit
  `--include-token-detail --token-detail-version v2` requirement instead of
  loading spaCy or another backend first.
- Added regression tests for both review findings.
- Pushed fix commit `9cbe88b0` to PR #392.

# Validation

- `PATH="/Users/centaur/anaconda3/bin:$PATH" scripts/version tools` — LCATS
  `0.1.1.dev814+ge8e961aab.d20260824`; Python `3.11.8`; Ruff `0.15.0`;
  Black `25.11.0`; pip `23.2.1`.
- `PATH="/Users/centaur/anaconda3/bin:$PATH" python -m unittest
  tests.analysis_tests.linguistics_test` — 62 tests OK.
- `PATH="/Users/centaur/anaconda3/bin:$PATH" scripts/format --check --diff`
  — 228 files unchanged. The first sandboxed run hit the known Black
  multiprocessing socket restriction; the escalated rerun passed.
- `PATH="/Users/centaur/anaconda3/bin:$PATH" scripts/lint` — Ruff passed;
  Black formatting check passed.
- `PATH="/Users/centaur/anaconda3/bin:$PATH" scripts/test` — 2161 tests OK.
- `PATH="/Users/centaur/anaconda3/bin:$PATH" lrh validate` — 0 errors, 237
  existing warnings.

# Follow-up

- Continue the LRH landing chain for PR #392: wait for fresh post-push
  review/CI, run confirm-fixes, then present the merge/closeout gate if green.
