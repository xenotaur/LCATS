---
resolution: null
blocked_reason: null
blocked: false
id: WI-EVENT-0080
title: Run a small real cross-segment density feasibility pilot
type: evaluation
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
depends_on:
  - WI-EVENT-0079
blocked_by: []
expected_actions:
  - create_report
  - edit_file
  - run_tests
  - create_pr
forbidden_actions:
  - run_real_llm_calls_without_explicit_approval
  - execute_full_wi_event_0030
  - tune_prompts_after_negative_gate_result
  - redefine_thresholds_after_seeing_real_results
  - force_push
  - delete_branch
acceptance:
  - The real feasibility run is bounded to the preregistered small story set and starts only after explicit in-session approval of model, story count, expected calls, and cost estimate
  - Results report completion rate, parseability, semantic plausibility, segmentation/alignment failures, excluded stories, usage/cost, and whether the run met preregistered thresholds
  - The recommendation is one of proceed_to_wi_event_0030, fix_named_blocker, revise_preregistration_before_results, or stop
  - Negative or low-quality results are reported as valid outcomes rather than retried or tuned away
  - lrh validate reports 0 errors
required_evidence:
  - manual_review
  - validation_output
  - lrh_validate
artifacts_expected:
  - experiments/03_cross_segment_relation_pilot/results/density_feasibility/
  - experiments/03_cross_segment_relation_pilot/results/density_feasibility/feasibility_report.md
---

## Summary

Run a small, explicitly approved real cross-segment density feasibility
pilot to decide whether the system is ready for the near-final
`WI-EVENT-0030` run.

## Problem / Context

The project needs one paid proof-of-life after preregistration and readiness
checks, but before spending on the larger density experiment. This item
measures whether real outputs complete, parse, make semantic sense, preserve
artifacts, and produce usable cost/failure evidence on a small story set.

### Duplication search

- In-repo: Related: `WI-PILOT-0067` ran an earlier stability gate, but it
  failed and did not follow this new density-experiment preregistration.
  No current small feasibility pilot exists for the staged path to
  `WI-EVENT-0030`.
- Sibling repos: None identified.
- External libraries: None identified.
- Recommendation: Proceed after `WI-EVENT-0079` passes.

### Demand search

- Work items: `WI-EVENT-0030` remains the target near-final run; this item
  supplies the small real gate before it.
- Proposals: `PROP-LCATS-CROSS-SEGMENT-DENSITY-EXPERIMENT` requests this
  feasibility step.
- Backlog: The minimum-cost validation backlog entry is relevant.
- Recommendation: Link this item to `WS-PILOT-CROSS-SEGMENT-DENSITY`.

## Scope

- Run only the preregistered small real story set.
- Require explicit cost approval before making any real Anthropic call.
- Report quality, cost, completion, artifact, and failure evidence in a
  durable experiment directory.

## Required Changes

1. Present the model, story set, expected call count, and cost estimate for
   explicit in-session approval before any real LLM call.
2. Run the preregistered small feasibility pilot using the approved command
   and output root.
3. Preserve raw output, usage/cost rows, excluded-story details, and any
   validation report under
   `experiments/03_cross_segment_relation_pilot/results/density_feasibility/`.
4. Write `feasibility_report.md` stating whether the run passed thresholds
   and whether `WI-EVENT-0030` should proceed, wait for a named blocker, be
   revised before results, or stop.

## Non-Goals

- Does not execute the full `WI-EVENT-0030` run.
- Does not change preregistered thresholds after seeing real results.
- Does not tune prompts or retry to manufacture a positive result.
- Does not implement unrelated pilot infrastructure.

## Acceptance Criteria

- The real feasibility run is bounded to the preregistered small story set
  and starts only after explicit in-session approval of model, story count,
  expected calls, and cost estimate.
- Results report completion rate, parseability, semantic plausibility,
  segmentation/alignment failures, excluded stories, usage/cost, and whether
  the run met preregistered thresholds.
- The recommendation is one of `proceed_to_wi_event_0030`,
  `fix_named_blocker`, `revise_preregistration_before_results`, or `stop`.
- Negative or low-quality results are reported as valid outcomes rather
  than retried or tuned away.
- `lrh validate` reports 0 errors.

## Validation

- `lrh validate`

## Risk Notes

- This is the first paid gate in the staged plan, so approval and bounded
  scope are part of the artifact, not incidental process notes.
- A failed feasibility run should not be treated as a failed work item if it
  produces the preregistered evidence and recommendation.

## Related Workstream and Designs

- Workstream: `lcats/project/workstreams/proposed/WS-PILOT-CROSS-SEGMENT-DENSITY.md`
- Design: `lcats/project/design/proposals/proposed/lcats-cross-segment-density-experiment/00_proposal.md`
- Target run: `lcats/project/work_items/proposed/WI-EVENT-0030.md`
