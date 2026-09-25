---
execution_id: 2026_09_02_19_30_08_WI_LINGUISTICS_0007_REVIEW
prompt_id: PROMPT(AD_HOC:WI_LINGUISTICS_0007_REVIEW)[2026-09-02T19:26:43+00:00]
work_item: AD_HOC
status: landed
rerun_of: 2026_09_02_19_11_59_WI_LINGUISTICS_0007
pr: https://github.com/xenotaur/LCATS/pull/423
commit: ede5d004338917e383369f3b98d49ee7beb7baa7
created_at: 2026-09-02T19:30:08+00:00
agent: codex_app
instruction_source: https://github.com/xenotaur/LCATS/pull/423
session_transcript: pending
---

# Summary

Addressed four Copilot review comments on PR 423 for the
`WI-LINGUISTICS-0007` rich-linguistics pilot.

# Result

- Fixed Parquet restore handling for absent compact sidecars by treating
  non-string `compact_json` cells, including pandas null values, as missing
  rather than JSON-decodable payloads.
- Kept validation summary `findings` consistently shaped as a list of
  dictionaries, including missing-output rows.
- Corrected full-corpus cost projection to use the `corpus_root` passed to
  `run_pilot()` instead of the module-level default corpus root.
- Updated result pruning so `--overwrite` removes stale `results/parquet/`
  metadata before rebuilding the pilot output tree.
- Added regression coverage for all four reviewer findings.
- Pushed fix commit `0ba1ab3f` to PR 423.

# Validation

- `python -m unittest experiments/09_rich_linguistics_genre_sample/run_rich_linguistics_sample_test.py experiments/09_rich_linguistics_genre_sample/parquet_bridge_test.py`
  — 10 tests OK.
- `scripts/version tools` — LCATS
  `0.1.1.dev933+g8d14332bd.d20260902`, Python 3.11.8, Ruff 0.15.0, Black
  25.11.0.
- `scripts/format --check --diff` — 230 files would be left unchanged
  (required sandbox escalation for Black's multiprocessing manager socket).
- `scripts/lint` — Ruff and Black checks passed.
- `scripts/test` — 2,249 tests OK.
- `lrh validate` — 0 errors, 268 standing warnings.

# Follow-up

- Review threads still need `/lrh-confirm-fixes` verification and resolution
  before merge.
- `session_transcript` remains `pending` until a durable Codex app task pointer
  is supplied.
