---
execution_id: 2026_08_22_18_21_49_WS_RUN_LOG_WORK_ITEMS_REVIEW
prompt_id: PROMPT(AD_HOC:WS_RUN_LOG_WORK_ITEMS_REVIEW)[2026-08-22T18:21:06+00:00]
work_item: AD_HOC
status: landed
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/352
commit: 644fe26562cd977b3998fa612ef89374a86b11ab
created_at: 2026-08-22T18:21:49+00:00
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/352
session_transcript: claude-app:7065c30d-504e-47af-9834-d062b53d7a74
---

# Summary

`/lrh-review-response https://github.com/xenotaur/LCATS/pull/352`
(inlined as `/lrh-land` Step 4) — addressed 16 open review comments (3
Codex, 13 Copilot) across the 6 of 7 `WI-RUNLOG-*` work items that
received findings (`WI-RUNLOG-0084` had none).

**`rerun_of` note:** left empty per the standard branch-slug search — the
branch `xenotaur/feat/ws-run-log-work-items` doesn't derive to any single
individual WI's own slug (`wi-runlog-0078` through `-0084`), so the exact-
slug target search in `land-workflow.md`'s rerun_of algorithm finds no
match. This round's fixes span all 6 affected WI creation records rather
than one primary; not guessing at a link per the algorithm's own
no-target rule.

# Result

Fetched 16 comments via `lrh request review_response`, mapped each to its
exact file/line via `gh api repos/.../pulls/352/comments` (path/line
fields absent from the GraphQL thread listing), and independently
verified the substantive ones directly against repo state before
accepting them (not taken on the reviewers' word):

- **WI-RUNLOG-0078** (3 real + 2 stale): confirmed `CheckpointRoots`
  (`checkpoint.py:82-92`) is a bare frozen dataclass with no validated/
  unvalidated marker — the "or accepts an already-validated
  CheckpointRoots" acceptance criterion was genuinely unimplementable;
  removed it, required `RunLog` to always re-run
  `checkpoint.resolve_roots()`'s guard. Added an explicit
  fatal-vs-unexpected exception-classification requirement. Verified
  `_log_run_event()` is now at `run_prefilter.py:1005-1027` (`git show
  origin/main:...`), not `883-905` as cited — fixed in both
  WI-RUNLOG-0078 and WI-RUNLOG-0079. The 2 stale comments (WS-RUN-LOG's
  `work_items: []`) were already fixed in commit `4ba85ab3`, before these
  reviews ran (confirmed via `gh api .../reviews` — both reviews'
  `commit_id` is `ff35d6ca`, the first commit).
- **WI-RUNLOG-0079** (3): required the full `_run_validate_mode()` output
  path (including `write_validation_outputs()`) wrapped in one `RunLog`
  scope — confirmed via `git show` that `run_end` (line 1377) currently
  precedes `write_validation_outputs` (1444) and `_run_validate_mode`
  continues to line 1707, leaving that gap real. Fixed the same stale
  citation.
- **WI-RUNLOG-0080** (1): confirmed via `grep -n` that `_run_stories()`
  (1403-1500) only returns `(rows, usage_rows, aborted)` and the write
  block is in `main()` at 1824-1832 — corrected the hook scoping
  accordingly.
- **WI-RUNLOG-0081** (2, Codex + Copilot on the same issue): required
  `run_end` only after the summary write succeeds, not before.
- **WI-RUNLOG-0082** (2): confirmed via `find`/`grep` that 9 gatherers
  route through the shared `gatherlib.gather()` while `mass_quantities`,
  `sherlock`, and `lovecraft` each implement their own separate `gather()`
  — narrowed scope to `gatherlib.gather()`, explicitly deferred the other
  3. Confirmed `assess_cli.py` has no checkpoint/working directory
  concept and `--output` is the result file, not a log root — added an
  explicit new-CLI-option requirement for both `gather` and `assess`.
- **WI-RUNLOG-0083** (2, Codex P1 + Copilot on the same conflict, plus 1
  more): confirmed `promote_cli.py:36` defaults `dest_root` to
  `env.corpora_root()` — a direct, genuine self-contradiction against
  WI-RUNLOG-0078's own protected-root rejection requirement. Moved the
  log destination outside both `--source`/`--dest`. Confirmed `promote.py`
  has no `FatalPromoteError` class — required both `run_aborted_fatal`
  and `run_aborted_unexpected`.

# Validation

- `lrh validate` — exit 0; no findings against any of the 6 changed
  files.
- `scripts/test` — 1844 tests, 2 pre-existing failures
  (`test_utils_test.py`'s hardcoded-path assertions — same known
  environment drift documented in memory, unrelated to this docs-only
  diff; `git diff --stat main -- '*.py'` confirms zero Python files
  touched).
- `scripts/format --check --diff`/`scripts/lint` — failed on a **tool
  version mismatch** (`black` 26.3.1 running vs. `25.11.0` pinned;
  `ruff` 0.15.12 vs. `0.15.0` pinned), not a formatting/lint violation —
  reported per the skill's own guidance as a missing/drifted environment
  dependency, not a code regression, since this diff touches no Python.

# Follow-up

- Reminder: `session_transcript` should be confirmed/updated at closeout
  time if it differs from the live `CLAUDE_CODE_HOST_SESSION_ID`
  convention.
- The `black`/`ruff` version drift noted above is a pre-existing
  environment issue, not actioned here — flagged for awareness.
- Next: re-run confirm-fixes for a fresh verdict against this new HEAD
  per `/lrh-land` Step 5.
