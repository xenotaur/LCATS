---
execution_id: 2026_08_21_07_30_41_WI_LINGUISTICS_0001_SELFREVIEW
prompt_id: PROMPT(AD_HOC:WI_LINGUISTICS_0001_SELFREVIEW)[2026-08-21T07:30:36+00:00]
work_item: AD_HOC
status: landed
rerun_of: 2026_08_20_23_28_50_WI_LINGUISTICS_0001
pr: https://github.com/xenotaur/LCATS/pull/325
commit: 96e227d7d3aaf74d34caf5022622f9a1b584a8d6
created_at: 2026-08-21T07:30:41+00:00
agent: codex_app
instruction_source: https://github.com/xenotaur/LCATS/pull/325
session_transcript: pending
---

# Summary

Run PR-mode substitute self-review for PR 325 after the `_CONFIRM` commit did
not receive an automatic reviewer response for the exact head.

# Result

Dispatched cold-context subagent `01a02323-d427-7611-94ff-d620e19766fe`
(`Avicenna`) against PR 325 at
`8343d642c06db6be3a40310823ac8af36ba3202a`.

Findings: 1.

- P2: `lcats linguistics --backend fake` succeeded with status 0 and an empty
  run summary when no inputs or `--story-list` were supplied.

The invoking session independently re-verified the finding before accepting
it:

- Read `src/lcats/analysis/corpus/linguistics_cli.py`; there was no no-input
  guard before `runner.run()`.
- Ran `cli.dispatch('linguistics', ['--backend', 'fake'])`; it returned status
  0 with empty `counts` and `results`.

Remediation applied in commit `2c8bb07e`: `linguistics_cli.run()` now fails
before backend construction when resolution yields no story paths and no
missing explicit paths, and `tests/cli_test.py` covers the top-level CLI
dispatch case.

# Validation

- `PYTHONPATH=src python -m unittest tests.cli_test
  tests.analysis_tests.linguistics_test` -- ran 50 tests, OK.
- `PYTHONPATH=src python - <<'PY' ... cli.dispatch('linguistics', ['--backend',
  'fake']) ... PY` -- returned status 1 and printed `error: no stories
  resolved; provide story paths, story buckets, directories, or --story-list`.
- `PATH=/Users/centaur/anaconda3/bin:/usr/bin:/bin:/usr/sbin:/sbin
  scripts/format --check --diff` -- 194 files unchanged.
- `PATH=/Users/centaur/anaconda3/bin:/usr/bin:/bin:/usr/sbin:/sbin
  scripts/lint` -- Ruff passed; Black formatting check passed.
- `PATH=/Users/centaur/anaconda3/bin:/usr/bin:/bin:/usr/sbin:/sbin
  scripts/test` -- ran 1788 tests, OK.
- `lrh validate` -- 0 errors, 159 warnings. Warnings are existing
  owner/instruction-source warnings and the proposed `WI-LINGUISTICS-0001`
  owner warning already present on this branch.

# Follow-up

Rerun confirm-fixes after pushing this remediation and this `_SELFREVIEW`
record, because the PR head will have changed.
