---
execution_id: 2026_08_21_06_45_26_WI_LINGUISTICS_0001_REVIEW
prompt_id: PROMPT(AD_HOC:WI_LINGUISTICS_0001_REVIEW)[2026-08-21T06:41:12+00:00]
work_item: AD_HOC
status: landed
rerun_of: 2026_08_20_23_28_50_WI_LINGUISTICS_0001
pr: https://github.com/xenotaur/LCATS/pull/325
commit: 96e227d7d3aaf74d34caf5022622f9a1b584a8d6
created_at: 2026-08-21T06:45:26+00:00
agent: codex_app
instruction_source: https://github.com/xenotaur/LCATS/pull/325
session_transcript: pending
---

# Summary

Address open review comments on PR 325 for the standalone linguistic sidecar
infrastructure.

# Result

Applied and pushed review fixes in commit `3fffcba6`:

- Fixed token-detail resume checks to compare `linguistics.tokens.json` against
  its own `linguistics-token-detail-v1` fingerprint instead of the compact
  sidecar fingerprint.
- Fixed bucket-relative `story.json` identity derivation so running from inside
  a story bucket uses the current bucket directory name rather than producing an
  empty `lcats_id`.
- Replaced stale recovery diagnostics that said `--overwrite` with the accepted
  CLI spelling, `--existing overwrite`.

Skipped comments: none. The six returned comments reduced to the three issues
above, and each was present, valid, feasible, and addressed.

# Validation

- `PYTHONPATH=src python -m unittest tests.analysis_tests.linguistics_test` --
  ran 25 tests, OK.
- `scripts/develop` -- refreshed editable install for this worktree after a
  prior full test run imported a stale editable install from another worktree.
- `scripts/version tools` -- LCATS `0.1.1.dev608+gc2eb1ad1b.d20260821`,
  Python `3.11.8`, Ruff command reported `0.16.2`, Black command reported
  `26.5.1`, pip `23.2.1`.
- `PATH=/Users/centaur/anaconda3/bin:$PATH scripts/format --check --diff` --
  194 files unchanged.
- `PATH=/Users/centaur/anaconda3/bin:$PATH scripts/lint` -- Ruff passed; Black
  formatting check passed.
- `PATH=/Users/centaur/anaconda3/bin:$PATH scripts/test` -- ran 1787 tests, OK.
- `lrh validate` -- 0 errors, 159 warnings. Warnings are existing
  owner/instruction-source warnings and the proposed `WI-LINGUISTICS-0001`
  owner warning already present on this branch.

# Follow-up

Run `/lrh-confirm-fixes https://github.com/xenotaur/LCATS/pull/325` before
merge to verify the current diff and resolve review threads.
