---
execution_id: 2026_09_02_19_49_37_WI_LINGUISTICS_0007_REVIEW
prompt_id: PROMPT(AD_HOC:WI_LINGUISTICS_0007_REVIEW)[2026-09-02T19:46:26+00:00]
work_item: AD_HOC
status: landed
rerun_of: 2026_09_02_19_30_08_WI_LINGUISTICS_0007_REVIEW
pr: https://github.com/xenotaur/LCATS/pull/423
commit: ede5d004338917e383369f3b98d49ee7beb7baa7
created_at: 2026-09-02T19:49:37+00:00
agent: codex_app
instruction_source: https://github.com/xenotaur/LCATS/pull/423
session_transcript: pending
---

# Summary

Addressed the second review-response round for PR 423 after confirm-fixes
surfaced a remaining P1 about preserving human POS audit labels.

# Result

- Changed `build_pos_audit()` so the manual-label scoring path loads and
  validates `--audit-labels` before writing `results/pos_audit_sample.csv`.
- Writes a labeled audit sample only after scoring succeeds, preserving labels
  when `--audit-labels` points to the documented output sample path.
- Added a regression covering the same-file labels path.
- Pushed fix commit `ed0aa7cd` to PR 423.

# Validation

- `python -m unittest experiments/09_rich_linguistics_genre_sample/run_rich_linguistics_sample_test.py experiments/09_rich_linguistics_genre_sample/parquet_bridge_test.py`
  — 11 tests OK.
- `scripts/format --check --diff` — 230 files would be left unchanged
  (required sandbox escalation for Black's multiprocessing manager socket).
- `scripts/lint` — Ruff and Black checks passed.
- `scripts/test` — 2,249 tests OK.
- `lrh validate` — 0 errors, 268 standing warnings.

# Follow-up

- Re-run confirm-fixes for PR 423 so the resolved review threads can be
  verified, resolved, and the merge-readiness verdict can be recomputed.
- `session_transcript` remains `pending` until a durable Codex app task pointer
  is supplied.
