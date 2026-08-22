---
resolution: null
blocked_reason: null
blocked: false
id: WI-RUNLOG-0082
title: Add run-log support to lcats gather, assess, and annotate
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
  - lcats gather's download loop (mass_quantities/gatherer.py) emits run_start, a per-story event, and run_end/run_aborted_*, per named gatherer
  - lcats assess's per-file loop (assess_cli.py) emits the same event triad around each assess_story call
  - lcats annotate's per-story/per-collection loop (annotate.py) emits the same triad, reusing its existing checkpoint_dir as the log's home
  - Each of the 3 commands' own test suites cover the new logging
  - lrh validate and scripts/test pass with 0 errors
required_evidence:
  - lrh_validate
  - test_output
artifacts_expected:
  - lcats/src/lcats/gatherers/main.py
  - lcats/src/lcats/gatherers/mass_quantities/gatherer.py
  - lcats/src/lcats/analysis/corpus/assess_cli.py
  - lcats/src/lcats/analysis/corpus/annotate.py
---

## Summary

Adds an incremental, crash-safe run-event log to `lcats gather`,
`lcats assess`, and `lcats annotate` — three CLI commands sharing the
same paid/network-loop shape and currently missing any ordered,
human-readable trail of what happened during a run.

## Problem / Context

All three are warranted-and-missing per the proposal's Decision 4 table:
`gather` has no `checkpoint` usage at all today; `assess` makes a paid
call per file with no resume and some output formats lossy on crash;
`annotate` has real per-item checkpointing already but no ordered trail
on top of it. Grouped into one work item since all three are small
additions of the same shape, not because they share code.

### Duplication search
- In-repo: No existing run log at any of the 3 sites. Recommendation:
  Proceed.
- Sibling repos: None identified.
- External libraries: None identified.
- Recommendation: Proceed.

### Demand search
- Work items: None found.
- Proposals: Found: `PROP-LCATS-RUN-LOG` — Implementation Plan step 5
  requests this directly (as one step covering all three).
- Backlog: No matching entries.
- Recommendation: No action.

## Scope

- Add logging hooks to each of the 3 commands' main loops
- Do not unify the 3 commands into one shared caller — each keeps its
  own call sites
- Do not change any command's existing checkpoint semantics

## Required Changes

1. `lcats gather`: hook `run_start`/per-story/`run_end` in
   `mass_quantities/gatherer.py`'s `gather_stories`, and around
   `main.py`'s per-gatherer loop.
2. `lcats assess`: hook the same triad around `assess_cli.py`'s
   `for file_path in tqdm.tqdm(files, ...)` loop.
3. `lcats annotate`: hook the same triad through
   `annotate_collections`/`annotate_collection`/`annotate_story`, log
   path under `args.checkpoint_dir`.
4. Extend each command's existing test file to cover the new logging.

## Non-Goals

- Does not fix `lcats assess`'s separately-noted lossy-output-format gap
  (`--format json`/`tsv` buffering) — related but distinct, not in scope
  here.
- Does not change any of the 3 commands' checkpoint resumability
  behavior.

## Acceptance Criteria

(see frontmatter)

## Validation

- `scripts/version tools`
- `lrh validate`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`

## Dependencies / Order

Must land after WI-RUNLOG-0078. The 3 sub-changes are independent of
each other and can be done in any order within this item.

## Risk Notes

- Bundling 3 sites into one item risks scope creep if any one proves
  harder than expected — if so, the implementor should split the
  remaining sites into a follow-up item rather than stall this one
  indefinitely.

## Related Workstream and Designs

- Workstream: `project/workstreams/proposed/WS-RUN-LOG.md`
- Design: `project/design/proposals/proposed/lcats-run-log/00_proposal.md`
