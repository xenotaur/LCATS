---
resolution: "Implemented and merged in PR #400 (commit 8db9b10f)."
blocked_reason: null
blocked: false
id: WI-RUNLOG-0081
title: Add run-log support to run_census.py
type: deliverable
status: resolved
owner: unassigned
contributors: []
assigned_agents: []
related_focus: []
related_roadmap: []
related_workstreams:
  - WS-RUN-LOG
related_design:
  - lcats/project/design/proposals/proposed/lcats-run-log/00_proposal.md
depends_on:
  - WI-RUNLOG-0078
blocked_by: []
expected_actions:
  - edit_file
  - run_tests
forbidden_actions:
  - force_push
  - delete_branch
acceptance:
  - The classification loop emits run_start after roots resolution, a per-item event per story, and run_aborted_fatal in the FatalCensusError branch; run_end is emitted only after the final summary write succeeds, not before it — a failure while writing the summary produces run_aborted_unexpected instead (review finding, PR #352: run_end before the write is not a valid terminal-completion record)
  - Log path is <output_dir>/<prefix>_run_log.jsonl
  - A crash mid-run leaves a readable partial run log
  - lrh validate and scripts/test pass with 0 errors
required_evidence:
  - lrh_validate
  - test_output
artifacts_expected:
  - experiments/04_genre_census/run_census.py
---

## Summary

Adds an incremental, crash-safe run-event log to `run_census.py`,
matching the reference implementation's shape at the largest single
corpus scope among the audited sites (~1,868 stories in `--full` mode).

## Problem / Context

`run_census.py` has per-item checkpointing but its `records` list — and
any explanation of why a run stopped mid-way — lives only in memory
until the final summary write. Proposal Decision 4 table entry.

### Duplication search
- In-repo: No existing run log. Recommendation: Proceed.
- Sibling repos: None identified.
- External libraries: None identified.
- Recommendation: Proceed.

### Demand search
- Work items: None found.
- Proposals: Found: `PROP-LCATS-RUN-LOG` — Implementation Plan step 4
  requests this directly.
- Backlog: No matching entries.
- Recommendation: No action.

## Scope

- Add logging hooks around the classification loop and abort/end paths
- Do not change checkpoint semantics or the final summary format

## Required Changes

1. Hook `run_start` after `roots = checkpoint.resolve_roots(...)`.
2. Hook a per-item event inside the target loop (or in `_classify_story`).
3. Hook `run_aborted_fatal` in the `except FatalCensusError` branch.
4. Keep the run scope open through the final summary write; emit
   `run_end` only after it succeeds, and `run_aborted_unexpected` if it
   fails (review finding, PR #352 — do not emit `run_end` before the
   write as originally scoped).

## Non-Goals

- Does not change checkpoint resumability behavior or the final
  summary/stories JSONL format.

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
