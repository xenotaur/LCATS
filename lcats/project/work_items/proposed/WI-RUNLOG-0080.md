---
resolution: null
blocked_reason: null
blocked: false
id: WI-RUNLOG-0080
title: Add run-log support to run_pilot.py
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
  - lcats/project/work_items/resolved/WI-EVENT-0032.md
depends_on:
  - WI-RUNLOG-0078
blocked_by: []
expected_actions:
  - edit_file
  - run_tests
forbidden_actions:
  - force_push
  - delete_branch
  - change_checkpoint_semantics
acceptance:
  - _run_stories() emits run_start before the per-story loop and a per-story event after each run_story()/exception resolution; the caller in main() emits run_end/run_aborted_* around the call to _run_stories() plus the pilot_stories.jsonl/pilot_usage.jsonl write block that follows it, since _run_stories() itself only returns (rows, usage_rows, aborted) and does not perform those writes (review finding, PR #352)
  - Log path is <output_dir>/pilot_run_log.jsonl, derived via RunLog's protected-root re-validation
  - A crash mid-run (e.g. simulated kill/exception) leaves a readable partial run log reflecting every story processed so far
  - experiments/03_cross_segment_relation_pilot/run_pilot_test.py covers the new logging, extended as needed
  - lrh validate and scripts/test pass with 0 errors
required_evidence:
  - lrh_validate
  - test_output
artifacts_expected:
  - experiments/03_cross_segment_relation_pilot/run_pilot.py
  - experiments/03_cross_segment_relation_pilot/run_pilot_test.py
---

## Summary

Adds an incremental, crash-safe run-event log to `run_pilot.py`, closing
the gap that the `WI-EVENT-0032` precedent — cited in this script's own
inline code comments (`run_pilot.py:777,782,1467`), not its module
docstring (which names its own implementing item, `WI-EVENT-0030`,
instead) — exists to prevent, but which the write-once-at-end output
design still leaves open on a hard crash.

## Problem / Context

Highest-priority site per the proposal's Decision 4 table. `run_pilot.py`'s
`pilot_stories.jsonl`/`pilot_usage.jsonl` are written once at the very end
(`run_pilot.py:1824-1832`); a `kill -9` at any point before that discards
everything in memory, even though per-item checkpointing already exists.
`WI-EVENT-0032` (resolved) documents the real incident this class of gap
caused.

### Duplication search
- In-repo: No existing run log in this script. Recommendation: Proceed.
- Sibling repos: None identified.
- External libraries: None identified.
- Recommendation: Proceed.

### Demand search
- Work items: Found: `WI-EVENT-0032` (resolved) — names the underlying
  failure mode but is already closed against the exception-handling fix,
  not this item's scope.
- Proposals: Found: `PROP-LCATS-RUN-LOG` — Decision 4 table and
  Implementation Plan step 3 request this directly.
- Backlog: No matching entries.
- Recommendation: No action.

## Scope

- Add `_log_run_event`/`RunLog` calls to `_run_stories()` (per-story
  events) and to `main()` (run_start/run_end/run_aborted_*, since the
  final writes it wraps live there, not in `_run_stories()`)
- Do not change existing per-item checkpointing semantics
- Do not change `pilot_stories.jsonl`/`pilot_usage.jsonl`'s own format

## Required Changes

1. Hook a per-story event inside `_run_stories()`'s loop (`run_pilot.py`
   spans lines 1403-1500), after each `run_story`/exception branch
   resolves.
2. In `main()`, wrap the call to `_run_stories()` **and** the subsequent
   `pilot_stories.jsonl`/`pilot_usage.jsonl` write block (`run_pilot.py:
   1824-1832`) in a single `RunLog` scope — emitting `run_start` before
   the call and `run_end` only after both files are written, so a
   failure during those writes also produces `run_aborted_unexpected`
   (review finding, PR #352 — `_run_stories()` itself only returns
   `(rows, usage_rows, aborted)` and does not perform the writes).
3. Extend `run_pilot_test.py` to cover the new log, including a case
   where the final write block itself fails.

## Non-Goals

- Does not change checkpoint resumability behavior.
- Does not change the final `pilot_stories.jsonl`/`pilot_usage.jsonl`
  output format.

## Acceptance Criteria

(see frontmatter)

## Validation

- `scripts/version tools`
- `lrh validate`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`

## Dependencies / Order

Must land after WI-RUNLOG-0078.

## Related Workstream and Designs

- Workstream: `project/workstreams/proposed/WS-RUN-LOG.md`
- Design: `project/design/proposals/proposed/lcats-run-log/00_proposal.md`
- Precedent: `project/work_items/resolved/WI-EVENT-0032.md`
