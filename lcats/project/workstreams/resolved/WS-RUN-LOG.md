---
id: WS-RUN-LOG
kind: planning_node
title: Shared run-event logging for LCATS batch scripts
status: resolved
stage: closed
origin: design_review
summary: Deliver PROP-LCATS-RUN-LOG's shared lcats.utils.run_log module (function + RunLog context manager) and migrate the 7 warranted batch-script/CLI sites to it, plus record the disposition of the 5 explicitly out-of-scope sites.
related_focus: []
related_roadmap: []
related_design:
  - lcats/project/design/proposals/proposed/lcats-run-log/00_proposal.md
  - lcats/project/design/proposals/adopted/lcats-pipeline-checkpointing/00_proposal.md
work_items:
  - WI-RUNLOG-0078
  - WI-RUNLOG-0079
  - WI-RUNLOG-0080
  - WI-RUNLOG-0081
  - WI-RUNLOG-0082
  - WI-RUNLOG-0083
  - WI-RUNLOG-0084
exit_criteria:
  - lcats.utils.run_log exists implementing Decision 1's function + RunLog context manager and Decision 3's CheckpointRoots-derived log path, with unit tests
  - run_prefilter.py is migrated from its inline _log_run_event() onto the shared module
  - run_pilot.py, run_census.py, lcats gather, lcats assess, lcats annotate, and lcats promote each write an incremental run-event log via the shared module
  - Each of the 5 historical/no-log-needed sites (run_stability_gate.py, run_comparison.py, lcats clean, lcats repair-specials, lcats linguistics) carries an explicit in-code note recording that disposition and why
  - All resulting work items resolved and lrh validate reports 0 errors
---

# Workstream: Shared run-event logging for LCATS batch scripts

## Purpose

This workstream delivers `PROP-LCATS-RUN-LOG`
(`lcats/project/design/proposals/proposed/lcats-run-log/00_proposal.md`),
proposed in this same PR in response to a session audit that found
`run_prefilter.py`'s `_log_run_event()` (PR #334) — a crash-safe,
incremental, human-readable run-event log distinct from per-item
checkpointing — was scoped to one script while the identical gap
recurred at five more sites, including `run_pilot.py`, the script whose
own inline code comments (not its module docstring, which names its own
implementing item `WI-EVENT-0030` instead) cite the precedent
(`WI-EVENT-0032`) this pattern exists to prevent. It coordinates
extracting a shared, reusable
`lcats.utils.run_log` module and migrating every warranted site onto it,
while explicitly recording why the remaining sites are left as-is.

## Scope

- Design and implement `lcats.utils.run_log` per the proposal's
  Decision 1 (function + `RunLog` context manager), Decision 2 (module
  location), and Decision 3 (tied to `checkpoint.CheckpointRoots`).
- Migrate the 7 "upgrade" sites from the proposal's Decision 4 table:
  `run_prefilter.py`, `run_pilot.py`, `run_census.py`, `lcats gather`,
  `lcats assess`, `lcats annotate`, `lcats promote`.
- Record the "historical/no-log-needed" disposition in-code for the 5
  remaining sites (`run_stability_gate.py`, `run_comparison.py`,
  `lcats clean`, `lcats repair-specials`, `lcats linguistics`), per the
  proposal's Implementation Plan step 7.
- Land all resulting work items through the standard LRH execution
  lifecycle.

## Prior Art Check

### Duplication search
- In-repo: No existing implementation. Excluding the governing proposal
  file itself:

  ```bash
  grep -rli "run.log\|run_event\|runlog" src/ project/design/proposals/ \
    project/workstreams/ project/work_items/
  ```

  returns nothing.
- Sibling repos: None identified.
- External libraries: Considered and rejected in the proposal's own
  Prior Art Check (stdlib `logging`, `structlog`/`loguru`) — not
  revisited here.
- Recommendation: Proceed.

### Demand search
- Work items: `grep -rli "run.log\|run.event" project/work_items/proposed/`
  — none found.
- Proposals: `PROP-LCATS-RUN-LOG` (this same PR) requests this
  workstream directly in its own Implementation Plan.
- Backlog: No matching entries in `project/design/backlog.md`.
- Recommendation: Proceed.

## Work Items

- **WI-RUNLOG-0078** — Shared `lcats.utils.run_log` module + unit tests
  (blocks everything else).
- **WI-RUNLOG-0079** — `run_prefilter.py` migration (dogfoods the module
  against the reference implementation).
- **WI-RUNLOG-0080** — `run_pilot.py` addition (highest priority).
- **WI-RUNLOG-0081** — `run_census.py` addition.
- **WI-RUNLOG-0082** — `lcats gather` / `lcats assess` / `lcats annotate`
  additions.
- **WI-RUNLOG-0083** — `lcats promote` addition.
- **WI-RUNLOG-0084** — Historical-disposition note across the 5
  out-of-scope sites.

## Exit Criteria

(see frontmatter `exit_criteria:` above)

## Non-Goals

- Does not implement dollar-cost budget enforcement — per the
  proposal's Non-Goals, this is `PROP-LCATS-PIPELINE-CHECKPOINTING`'s
  still-deferred "Category E1" other half.
- Does not change `checkpoint.py`'s resumability semantics — the run
  log is additive/observational only.
- Does not reopen scope for the 5 historical/no-log-needed sites — a
  future usage-pattern change there would need its own re-assessment,
  not an assumption this workstream already covers it.
- Does not adopt stdlib `logging` or a third-party structured-logging
  library — closed by the proposal's Decision 1.

## Open Questions

- Exact `RunLog` context-manager API and event-name vocabulary —
  deferred to work-item scoping, per the proposal's own Open Questions.
- Whether the three `lcats gather`/`assess`/`annotate` additions become
  one work item or three — deferred to work-item scoping.
