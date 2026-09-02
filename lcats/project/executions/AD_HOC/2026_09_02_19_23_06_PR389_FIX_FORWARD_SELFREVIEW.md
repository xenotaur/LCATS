---
execution_id: 2026_09_02_19_23_06_PR389_FIX_FORWARD_SELFREVIEW
prompt_id: PROMPT(AD_HOC:PR389_FIX_FORWARD_SELFREVIEW)[2026-09-02T19:23:00+00:00]
work_item: AD_HOC
status: in_progress
rerun_of:
pr: https://github.com/xenotaur/LCATS/pull/395
commit: 6566a883e4ff76e9604b20e2baf122f931cc91a1
agent: codex_app
instruction_source: https://github.com/xenotaur/LCATS/pull/395
session_transcript: codex-app:01a02338-d9c7-7313-8ed5-fb9c1643bef1
created_at: 2026-09-02T19:23:06+00:00
---

# Summary

PR-mode substitute self-review for PR 395 after the post-confirm-fixes
verification. The cold-context review examined the current PR diff and prior
review history at the final pre-fix head.

# Result

The reviewer identified two findings. The filesystem-boundary finding was
independently verified: `_write_json_atomic` could traverse a pre-existing
`_raw` or `_quarantine` directory symlink. It was fixed by a root-relative
no-symlink directory walk and an exclusive no-follow temporary file, with
coverage for both directories.

The execution-record finding was reviewed against LRH conventions. This
confirm record remains intentionally `in_progress` until merge/closeout, and
its commit points to the code head immediately before the record commit, as
used by existing confirm records. The post-record verification note is a
historical record of the state when authored, not a claim that the final
landing decision was already complete.

The filesystem finding was routed through the confirm-fixes pass. This
substitute review itself did not resolve GitHub threads or push changes.
No primary implementation execution record for PR 395 exists in tracked
`project/executions/`, so `rerun_of` is intentionally empty.

A subsequent exact-head substitute review identified that backend construction
occurred before `RunLog`, which omitted lifecycle events for setup failures.
That finding was independently verified and fixed by constructing the backend
inside the `RunLog` context, with a regression test for `run_start` and
`run_aborted_unexpected`.

A final exact-head review found that automatic `RunLog` abort events did not
carry the stored invocation fields. That finding was independently verified
and fixed by including those fields in automatic terminal events, with tests
covering fatal, unexpected, and clean terminal records. The same review also
reported a missing `run_id` on `max_failures`; direct inspection showed both
stop branches already include it, so that portion was classified as a false
positive.

# Validation

- `scripts/format --check --diff`: passed; 228 files unchanged.
- `scripts/lint`: passed.
- Focused canonical `scripts/test`: 72 tests passed.
- `lrh validate --project-dir project`: passed with 0 errors; existing
  warnings remain.
- Direct re-verification confirmed the symlinked-directory case raises before
  writing outside the output root.

# Follow-up

- Re-run confirm-fixes against the new code and self-review record commit.
- Keep execution status in progress until the PR is merged and closeout lands
  the record.
