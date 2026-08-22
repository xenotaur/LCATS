---
id: WS-PILOT-CROSS-SEGMENT-DENSITY
kind: planning_node
title: Cross-Segment Relation Density Experiment
status: proposed
stage: planned
origin: design_review
summary: Coordinate the staged path from preregistration and readiness gates through the near-final WI-EVENT-0030 density run and final paper-facing analysis package.
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap:
  - ROADMAP-CORE
related_design:
  - lcats/project/design/proposals/proposed/lcats-cross-segment-density-experiment/00_proposal.md
  - lcats/project/design/event-role-world-cross-segment-relations-evaluation.md
  - lcats/project/design/proposals/adopted/lcats-event-role-world-extractor/00_proposal.md
  - lcats/project/design/proposals/proposed/lcats-pilot-improvements/00_proposal.md
work_items:
  - WI-EVENT-0078
  - WI-EVENT-0079
  - WI-EVENT-0080
  - WI-EVENT-0030
  - WI-EVENT-0081
exit_criteria:
  - WI-EVENT-0030 has been reconciled/preregistered into this staged plan before any new density results are observed
  - A readiness gate has reported whether the runner, segmentation, logging, checkpoints, and artifacts are safe enough for a paid feasibility run
  - A bounded, explicitly approved small real feasibility pilot has either passed its preregistered thresholds or produced a named stop condition
  - WI-EVENT-0030, possibly revised by preregistration, has either run at the approved near-final scale or been explicitly stopped by a documented gate
  - A final analysis/evidence package reports density results, costs, exclusions/failures, figures/tables, and a confirm/weaken/contradict conclusion, or reports a preregistered gate stop with the named stop condition and unavailable-result explanation
  - All linked work items are resolved and lrh validate reports 0 errors
---

# Workstream: Cross-Segment Relation Density Experiment

## Purpose

This workstream delivers
`PROP-LCATS-CROSS-SEGMENT-DENSITY-EXPERIMENT`, the staged plan for turning
the existing cross-segment relation density pilot into defensible
Worldcon-paper evidence. It exists because directly trying to run
`WI-EVENT-0030` already exposed expensive reliability and cost-control
failures; `WI-EVENT-0030` remains the near-final empirical run, but it
should no longer be the first un-gated action.

## Scope

- Reconcile and preregister `WI-EVENT-0030` against the current
  `WI-GENRE-0004` 146-story sample, measured cost history, segmentation
  state, and Worldcon-scale evidence goal.
- Gate scale-up through readiness and small real feasibility checks with
  explicit spend approval and negative-result stop conditions.
- Treat pilot improvements (prompt caching, model tiering, Batch API, run
  ergonomics) as conditional inputs from `WS-PILOT-IMPROVEMENTS`, not as
  work this stream re-implements.
- Execute `WI-EVENT-0030`, possibly after preregistered tweaks, only after
  the gates justify it.
- Produce the final density-analysis package needed for paper use.

## Prior Art Check

### Duplication search

- In-repo: Related and partially overlapping artifacts exist. `WI-EVENT-0030`
  owns the density pilot itself; `WS-PILOT-IMPROVEMENTS` owns reusable pilot
  stability/cost/run-mode improvements; `WS-LINGUISTICS` and
  `WS-KNIGHT-NOVUM-ANALYSIS` provide precedents for Worldcon-scale sample
  runs and staged pilot gates. No workstream currently coordinates the
  full density experiment from preregistration through final analysis.
- Sibling repos: None identified.
- External libraries: None identified.
- Recommendation: Proceed by linking and sequencing the existing density
  work item rather than duplicating it.

### Demand search

- Work items: `WI-EVENT-0030` directly requests the larger cross-segment
  density run; this workstream provides the missing staged delivery frame.
- Proposals: `PROP-LCATS-PILOT-IMPROVEMENTS` requests stabilized pilot
  improvements that this workstream may consume.
- Backlog: `lcats/project/design/backlog.md` records the need for a cheap
  bounded real-API validation mode before full pilot execution.
- Recommendation: Link `WI-EVENT-0030` and the new gate/analysis items under
  this workstream.

## Work Items

- **WI-EVENT-0078 - Reconcile and preregister WI-EVENT-0030.** Freeze the
  sample plan, thresholds, cost gates, stop conditions, artifact contract,
  and relationship to the 146-story `WI-GENRE-0004` sample before observing
  new density results.
- **WI-EVENT-0079 - Run the density readiness gate.** Assess whether the
  current runner, segmentation, checkpointing, logging, and artifacts are
  safe enough for a paid feasibility run.
- **WI-EVENT-0080 - Run a small real feasibility pilot.** Execute a bounded,
  explicitly approved paid run to decide whether the path can scale.
- **WI-EVENT-0030 - Run stratified cross-segment relation density pilot
  across genres.** The near-final empirical run, possibly revised by
  `WI-EVENT-0078`.
- **WI-EVENT-0081 - Produce the final density analysis package.** Convert
  `WI-EVENT-0030` output into paper-facing tables, figures, cost/failure
  reports, and interpretation.

## Exit Criteria

(see frontmatter `exit_criteria:` above)

## Non-Goals

- Does not implement pilot prompt caching, model tiering, Batch API, or run
  ergonomics; those remain owned by `WS-PILOT-IMPROVEMENTS`.
- Does not run real LLM calls without separate explicit approval.
- Does not replace the Event-Role-World extractor architecture.
- Does not require full-corpus expansion beyond the approved Worldcon-scale
  sample unless a later result justifies it.

## Open Questions

- Should `WI-EVENT-0030` be revised to run the full 146-story sample, or
  should it remain a stratified subset with the option to expand after the
  first paper-facing result?
- Which, if any, `WS-PILOT-IMPROVEMENTS` cost improvements should be
  required before the near-final run?
