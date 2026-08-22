---
resolution: null
blocked_reason: null
blocked: false
id: WI-RUNLOG-0078
title: Implement shared lcats.utils.run_log module
type: deliverable
status: proposed
owner: unassigned
contributors: []
assigned_agents: []
related_focus: []
related_roadmap: []
related_workstreams:
  - WS-RUN-LOG
related_design:
  - lcats/project/design/proposals/proposed/lcats-run-log/00_proposal.md
depends_on: []
blocked_by: []
expected_actions:
  - create_file
  - edit_file
  - run_tests
forbidden_actions:
  - force_push
  - delete_branch
  - implement_run_prefilter_migration
acceptance:
  - lcats.utils.run_log exists with a free function matching _log_run_event()'s shape and a RunLog context manager per the proposal's Decision 1
  - RunLog re-validates its own working_root (or accepts only an already-validated CheckpointRoots) per Decision 3's review-finding requirement — a directly-constructed CheckpointRoots pointed at data/ or corpora/ is rejected, not silently accepted
  - RunLog's __exit__ emits run_end on clean exit and run_aborted_fatal / run_aborted_unexpected on exception, per Decision 1's event-name family
  - Unit tests cover the crash-safety property (no buffered-but-unflushed line lost), the protected-root rejection, and both exit-path event types
  - lrh validate and scripts/test pass with 0 errors
required_evidence:
  - lrh_validate
  - test_output
artifacts_expected:
  - lcats/src/lcats/utils/run_log.py
  - lcats/tests/utils_tests/run_log_test.py
---

## Summary

Implements `lcats.utils.run_log`, a shared crash-safe run-event-logging
module: a free function matching `_log_run_event()`'s append-open-write-close
shape, plus a `RunLog` context manager that auto-emits
`run_start`/`run_end`/`run_aborted_*` and re-validates its own protected
root.

## Problem / Context

`PROP-LCATS-RUN-LOG` (adopted design; see `related_design`) found the
crash-safe run-log pattern from PR #334's `_log_run_event()` scoped to one
script, with the identical gap recurring at 6 more sites. This item
delivers the shared module the other 6 items depend on. Decisions 1-3 of
the proposal are binding: the context manager, the `run_aborted_*` event
family, and the protected-root re-validation requirement (a real review
finding on PR #338 — a caller-constructed `CheckpointRoots` bypassing
`checkpoint.resolve_roots()`'s guard must not be trusted blindly).

### Duplication search
- In-repo: No existing implementation. `_log_run_event()` in
  `run_prefilter.py:883-905` is the pattern being generalized, not a
  duplicate to avoid.
- Sibling repos: None identified.
- External libraries: Considered and rejected in the proposal itself
  (stdlib `logging`, `structlog`/`loguru`) — not revisited here.
- Recommendation: Proceed.

### Demand search
- Work items: None found.
- Proposals: Found: `PROP-LCATS-RUN-LOG` — requests this directly.
- Backlog: No matching entries.
- Recommendation: No action — `WS-RUN-LOG` is exactly the request this
  item fulfills.

## Scope

- Implement `lcats.utils.run_log` (function + `RunLog` context manager)
- Unit-test the crash-safety, protected-root, and event-vocabulary
  properties
- Do not migrate any call site — that's items WI-RUNLOG-0079 through
  WI-RUNLOG-0084

## Required Changes

1. Create `lcats/src/lcats/utils/run_log.py` with the free function and
   `RunLog` class.
2. `RunLog.__init__` accepts a `checkpoint.CheckpointRoots` (or
   `working_root`) and re-validates it (Decision 3).
3. `RunLog.__enter__`/`__exit__` emit
   `run_start`/`run_end`/`run_aborted_fatal`/`run_aborted_unexpected` per
   Decision 1.
4. Create `lcats/tests/utils_tests/run_log_test.py`.

## Non-Goals

- Does not migrate `run_prefilter.py` or any other call site.
- Does not add `fsync()`-based power-loss durability — proposal Decision 1
  leaves this an open question; implement process-crash-safety only
  unless a follow-up decision changes this.
- Does not implement dollar-cost budget enforcement.

## Acceptance Criteria

(see frontmatter `acceptance:`)

## Validation

- `scripts/version tools`
- `lrh validate`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`

## Risk Notes

- The protected-root re-validation mechanism's exact shape is an open
  question in the proposal — implementor has design latitude here,
  should be conservative (reuse `checkpoint.resolve_roots`'s own guard
  rather than reimplementing it).

## Related Workstream and Designs

- Workstream: `project/workstreams/proposed/WS-RUN-LOG.md`
- Design: `project/design/proposals/proposed/lcats-run-log/00_proposal.md`
