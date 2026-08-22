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
  - lcats gather's shared gatherlib.gather() loop (used by the majority of individual gatherers — ohenry_four_million, ohenry_whirligigs, hemingway, chesterton, wilde_happy_prince, wodehouse, anderson, london, grimm) emits run_start, a per-story event, and run_end/run_aborted_*, writing to a log root outside the protected data/ tree — mass_quantities, sherlock, and lovecraft each implement their own separate gather() and are explicitly out of scope for this item (review finding, PR #352)
  - lcats assess's per-file loop (assess_cli.py) emits the same event triad around each assess_story call, writing to a log destination defined by a new CLI option (assess has no existing checkpoint/working directory to reuse, and --output is the result-format file, not a durable working root)
  - lcats annotate's per-story/per-collection loop (annotate.py) emits the same triad, reusing its existing checkpoint_dir as the log's home
  - Each of the 3 commands' own test suites cover the new logging
  - lrh validate and scripts/test pass with 0 errors
required_evidence:
  - lrh_validate
  - test_output
artifacts_expected:
  - lcats/src/lcats/gatherers/main.py
  - lcats/src/lcats/gatherers/gatherlib.py
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

- Add logging hooks to `gatherlib.gather()` (the shared loop most
  individual gatherers use), `assess_cli.py`, and `annotate.py`
- Define an explicit, non-protected log destination for `gather` and
  `assess`, since neither has one today (review finding, PR #352)
- Do not unify these into one shared caller — each keeps its own call
  sites
- Do not change any command's existing checkpoint semantics
- Does not instrument `mass_quantities`, `sherlock`, or `lovecraft`'s own
  separate `gather()` implementations — explicitly deferred (see
  Non-Goals)

## Required Changes

1. `lcats gather`: hook `run_start`/per-story/`run_end` in
   `gatherlib.gather()` (`lcats/src/lcats/gatherers/gatherlib.py`), the
   shared loop used by the majority of individual gatherers. Add a log
   destination outside `data/`/`corpora/` — e.g. a `logs/gather/`
   directory at the project root, or an explicit `--log-dir` CLI option
   threaded from `main.py`'s per-gatherer loop — since `RunLog` rejects
   any root under those protected trees (WI-RUNLOG-0078).
2. `lcats assess`: hook the same triad around `assess_cli.py`'s
   `for file_path in tqdm.tqdm(files, ...)` loop. Add a new CLI option
   (e.g. `--log-path`) for the log destination, since `assess` has no
   existing checkpoint/working directory and `--output` is the
   result-format file, not a durable working root; document the
   behavior when the option is omitted (no log, or a default location —
   implementor's choice, but must be specified, not left ambiguous).
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
- Does not add run-log support to `mass_quantities/gatherer.py`,
  `sherlock/gatherer.py`, or `lovecraft/gatherer.py` — each implements
  its own separate `gather()`/`gather_stories()` not routed through
  `gatherlib.gather()`; covering them is a follow-up item if warranted
  (review finding, PR #352 — `lcats gather` is not implemented only by
  `mass_quantities/gatherer.py`).

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
