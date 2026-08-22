---
execution_id: 2026_08_22_17_59_34_WI_LINGUISTICS_0003_REVIEW
prompt_id: PROMPT(AD_HOC:WI_LINGUISTICS_0003_REVIEW)[2026-08-22T17:56:34+00:00]
work_item: AD_HOC
status: in_progress
rerun_of: 2026_08_22_17_04_34_WI_LINGUISTICS_0003
pr: https://github.com/xenotaur/LCATS/pull/356
commit: 7a8454b0
created_at: 2026-08-22T17:59:34+00:00
agent: codex_app
instruction_source: https://github.com/xenotaur/LCATS/pull/356
session_transcript: pending
---

# Summary

Address open review comments on PR #356 for WI-LINGUISTICS-0003.

# Result

- Fixed the redirected collision check to compare canonical filesystem
  destinations before accepting another output target. This resolves symlinked
  output-root aliases and case-folds paths on common case-insensitive platforms.
- Preserved the `linguistics-run-summary-v1` default summary shape by omitting
  `output_root` unless redirection is used.
- Short-circuited batch preflight output-path resolution for default beside-story
  runs, so default mode keeps existing per-story behavior and avoids redundant
  work.
- Added regression coverage for default summary compatibility and symlinked
  redirected-output collisions.

# Validation

- `PATH=/Users/centaur/anaconda3/bin:/usr/bin:/bin:/usr/sbin:/sbin scripts/develop` — refreshed editable LCATS install for this worktree after Python imported a sibling checkout.
- `PATH=/Users/centaur/anaconda3/bin:/usr/bin:/bin:/usr/sbin:/sbin python -m unittest tests.analysis_tests.linguistics_test` — 37 tests OK.
- `PATH=/Users/centaur/anaconda3/bin:/usr/bin:/bin:/usr/sbin:/sbin scripts/version tools` — LCATS 0.1.1.dev701+g23eaf1384.d20260822, Python 3.11.8, Ruff 0.15.0, Black 25.11.0.
- `PATH=/Users/centaur/anaconda3/bin:/usr/bin:/bin:/usr/sbin:/sbin scripts/format --check --diff` — first sandboxed run hit Black multiprocessing socket permission error; escalated rerun passed with 198 files unchanged.
- `PATH=/Users/centaur/anaconda3/bin:/usr/bin:/bin:/usr/sbin:/sbin scripts/lint` — all checks passed.
- `PATH=/Users/centaur/anaconda3/bin:/usr/bin:/bin:/usr/sbin:/sbin scripts/test` — 1856 tests OK.
- `PATH=/Users/centaur/anaconda3/bin:/usr/bin:/bin:/usr/sbin:/sbin lrh validate` — 0 errors, 178 pre-existing warnings.
- `git diff --check` — clean.

# Follow-up

Run `/lrh-confirm-fixes https://github.com/xenotaur/LCATS/pull/356` before
merge to verify the current diff satisfies the review findings.
