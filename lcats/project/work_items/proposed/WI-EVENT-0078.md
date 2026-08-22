---
resolution: null
blocked_reason: null
blocked: false
id: WI-EVENT-0078
title: Reconcile and preregister WI-EVENT-0030 for staged density execution
type: operation
status: proposed
priority: high
owner: unassigned
contributors: []
assigned_agents: []
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap:
  - ROADMAP-CORE
related_workstreams:
  - WS-PILOT-CROSS-SEGMENT-DENSITY
related_design:
  - lcats/project/design/proposals/proposed/lcats-cross-segment-density-experiment/00_proposal.md
  - lcats/project/work_items/proposed/WI-EVENT-0030.md
  - lcats/project/work_items/resolved/WI-GENRE-0004.md
depends_on: []
blocked_by: []
expected_actions:
  - edit_file
  - create_pr
  - write_docs
forbidden_actions:
  - run_real_llm_calls
  - execute_wi_event_0030
  - tune_prompts_after_seeing_density_results
  - redefine_thresholds_after_seeing_density_results
  - force_push
  - delete_branch
acceptance:
  - WI-EVENT-0030's role as the near-final empirical run is explicit, including whether it remains 5-10 stories per genre or is revised toward the full WI-GENRE-0004 146-story sample
  - The preregistration records sample frame, genre strata, inclusion/exclusion rules, quality thresholds, semantic audit expectations, cost-estimation method, stop conditions, and required artifacts before new density results are observed
  - The preregistration names which WS-PILOT-IMPROVEMENTS outputs are required, optional, or explicitly deferred before the near-final run
  - No real LLM calls are made
  - lrh validate reports 0 errors
required_evidence:
  - manual_review
  - lrh_validate
artifacts_expected:
  - lcats/project/work_items/proposed/WI-EVENT-0030.md
  - lcats/project/design/proposals/proposed/lcats-cross-segment-density-experiment/00_proposal.md
  - lcats/project/workstreams/proposed/WS-PILOT-CROSS-SEGMENT-DENSITY.md
---

## Summary

Reconcile and preregister `WI-EVENT-0030` into the staged
cross-segment-density experiment plan before any new density results are
observed.

## Problem / Context

`WI-EVENT-0030` remains the near-final empirical run for the cross-segment
density hypothesis, but direct attempts to run `run_pilot.py` already led
to expensive bug discovery and follow-on checkpointing/cost-sustainability
work. The project now needs a no-paid-call preregistration pass that fixes
the sample, thresholds, stop conditions, and dependency gates before any
new density results can bias the plan.

### Duplication search

- In-repo: Related: `WI-EVENT-0030` already scopes the density run itself,
  but it does not preregister the staged path that now needs to precede
  execution.
- Sibling repos: None identified.
- External libraries: None identified.
- Recommendation: Proceed by updating/linking `WI-EVENT-0030`, not by
  replacing it.

### Demand search

- Work items: `WI-EVENT-0030` supplies the target run; this item supplies
  the missing preregistration/reconciliation step.
- Proposals: `PROP-LCATS-CROSS-SEGMENT-DENSITY-EXPERIMENT` requests this
  first gate.
- Backlog: The pilot minimum-cost validation backlog entry is relevant but
  not satisfied by this no-paid-call planning step alone.
- Recommendation: Link this item to `WS-PILOT-CROSS-SEGMENT-DENSITY`.

## Scope

- Reconcile `WI-EVENT-0030` with the current 146-story `WI-GENRE-0004`
  sample and the staged density-experiment proposal.
- Freeze preregistered thresholds, artifacts, stop conditions, and cost
  gates before new density results are observed.
- Decide whether the near-final `WI-EVENT-0030` run should remain a
  stratified 5-10 stories-per-genre run or be revised toward the full
  Worldcon-scale sample.

## Required Changes

1. Edit `lcats/project/work_items/proposed/WI-EVENT-0030.md` to record its
   role as the near-final empirical run in `WS-PILOT-CROSS-SEGMENT-DENSITY`.
2. Add or update preregistration text covering sample frame, genre strata,
   inclusion/exclusion rules, semantic audit expectations, cost estimates,
   stop conditions, and artifact contract.
3. Record which `WS-PILOT-IMPROVEMENTS` outputs are required before the
   near-final run, optional if available, or explicitly deferred.
4. Keep all changes in planning/control-plane artifacts; do not run the
   pilot or make real LLM calls.

## Non-Goals

- Does not execute `WI-EVENT-0030`.
- Does not implement pilot reliability or cost improvements.
- Does not change Event-Role-World extractor behavior.
- Does not loosen thresholds after seeing new density results.

## Acceptance Criteria

- `WI-EVENT-0030`'s role as the near-final empirical run is explicit,
  including whether it remains 5-10 stories per genre or is revised toward
  the full `WI-GENRE-0004` 146-story sample.
- The preregistration records sample frame, genre strata,
  inclusion/exclusion rules, quality thresholds, semantic audit
  expectations, cost-estimation method, stop conditions, and required
  artifacts before new density results are observed.
- The preregistration names which `WS-PILOT-IMPROVEMENTS` outputs are
  required, optional, or explicitly deferred before the near-final run.
- No real LLM calls are made.
- `lrh validate` reports 0 errors.

## Validation

- `lrh validate`

## Risk Notes

- This item is intentionally no-paid-call; treating it as permission to run
  `WI-EVENT-0030` would repeat the failure pattern the workstream exists to
  avoid.
- If the sample-size decision remains unresolved, the item should record the
  unresolved choice explicitly rather than silently defaulting to the older
  5-10 stories-per-genre plan.

## Related Workstream and Designs

- Workstream: `lcats/project/workstreams/proposed/WS-PILOT-CROSS-SEGMENT-DENSITY.md`
- Design: `lcats/project/design/proposals/proposed/lcats-cross-segment-density-experiment/00_proposal.md`
- Target run: `lcats/project/work_items/proposed/WI-EVENT-0030.md`
