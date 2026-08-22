---
resolution: null
blocked_reason: null
blocked: false
id: WI-EVENT-0079
title: Run the cross-segment density readiness gate
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
  - lcats/project/design/proposals/proposed/lcats-pilot-improvements/00_proposal.md
depends_on:
  - WI-EVENT-0078
blocked_by: []
expected_actions:
  - edit_file
  - create_report
  - run_tests
  - create_pr
forbidden_actions:
  - run_real_llm_calls_without_explicit_approval
  - execute_wi_event_0030
  - implement_batch_api_adoption
  - tune_prompts_after_negative_gate_result
  - force_push
  - delete_branch
acceptance:
  - A readiness report states whether run_pilot.py's current checkpoint, resume, usage logging, segmentation reliability, output artifact, and failure-reporting behavior are safe enough for the small feasibility run
  - The report uses no real LLM calls unless a separate explicit approval and cost estimate are recorded in-session
  - Any blockers are named as stop conditions or follow-on WIs rather than worked around silently
  - The next-step recommendation is one of proceed_to_small_feasibility, fix_named_blocker, or stop
  - lrh validate reports 0 errors
required_evidence:
  - manual_review
  - lrh_validate
artifacts_expected:
  - experiments/03_cross_segment_relation_pilot/results/density_readiness_gate/
  - lcats/project/work_items/proposed/WI-EVENT-0030.md
---

## Summary

Assess whether the current cross-segment pilot runner is ready for a
bounded paid feasibility run before scaling toward `WI-EVENT-0030`.

## Problem / Context

Checkpointing has reduced the risk that a crash discards paid work, but the
project still needs to know whether segmentation reliability, usage logging,
artifact writing, output validation, and failure handling are good enough
for the next paid density step. This readiness gate is the bridge between
planning/preregistration and a small real feasibility run.

### Duplication search

- In-repo: Related readiness/stability evidence exists in `WI-PILOT-0067`
  and segmentation follow-ups, but no current readiness gate exists for the
  staged density experiment after preregistering `WI-EVENT-0030`.
- Sibling repos: None identified.
- External libraries: None identified.
- Recommendation: Proceed.

### Demand search

- Work items: `WI-EVENT-0078` is expected to preregister the gate criteria.
- Proposals: `PROP-LCATS-CROSS-SEGMENT-DENSITY-EXPERIMENT` requests this
  readiness step.
- Backlog: The pilot minimum-cost validation backlog entry is relevant.
- Recommendation: Link this item to `WS-PILOT-CROSS-SEGMENT-DENSITY`.

## Scope

- Review current `run_pilot.py` behavior against the preregistered readiness
  criteria.
- Use no-cost tests, existing artifacts, and dry-run/fixture behavior where
  possible.
- Produce a clear proceed/fix/stop recommendation before any paid feasibility
  run.

## Required Changes

1. Create a readiness report under
   `experiments/03_cross_segment_relation_pilot/results/density_readiness_gate/`.
2. Check current checkpoint/resume behavior, usage/cost logging coverage,
   segmentation alignment risk, output artifact completeness, and
   excluded-story/failure reporting against `WI-EVENT-0078`'s preregistered
   criteria.
3. If a real LLM check is necessary, stop first to present the model, story
   count, call/cost estimate, and explicit approval request.
4. Update control-plane notes or `WI-EVENT-0030` if the gate finds a blocker
   that changes the staged plan.

## Non-Goals

- Does not execute `WI-EVENT-0030`.
- Does not run paid calls without a separate explicit approval.
- Does not implement Batch API, prompt caching, model tiering, or new
  segmentation fixes.
- Does not loosen preregistered thresholds to make the gate pass.

## Acceptance Criteria

- A readiness report states whether `run_pilot.py`'s current checkpoint,
  resume, usage logging, segmentation reliability, output artifact, and
  failure-reporting behavior are safe enough for the small feasibility run.
- The report uses no real LLM calls unless a separate explicit approval and
  cost estimate are recorded in-session.
- Any blockers are named as stop conditions or follow-on WIs rather than
  worked around silently.
- The next-step recommendation is one of `proceed_to_small_feasibility`,
  `fix_named_blocker`, or `stop`.
- `lrh validate` reports 0 errors.

## Validation

- `lrh validate`

## Risk Notes

- A readiness gate that only checks that the script starts is insufficient;
  it must cover artifact preservation, failure semantics, and cost
  visibility.
- If the gate produces a negative result, the correct outcome is to stop or
  file a named blocker, not to retry paid feasibility runs until one passes.

## Related Workstream and Designs

- Workstream: `lcats/project/workstreams/proposed/WS-PILOT-CROSS-SEGMENT-DENSITY.md`
- Design: `lcats/project/design/proposals/proposed/lcats-cross-segment-density-experiment/00_proposal.md`
