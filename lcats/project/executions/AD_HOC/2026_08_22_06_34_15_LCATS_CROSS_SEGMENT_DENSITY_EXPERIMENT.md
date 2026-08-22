---
execution_id: 2026_08_22_06_34_15_LCATS_CROSS_SEGMENT_DENSITY_EXPERIMENT
prompt_id: PROMPT(AD_HOC:LCATS_CROSS_SEGMENT_DENSITY_EXPERIMENT)[2026-08-22T06:33:58+00:00]
work_item: AD_HOC
status: in_progress
rerun_of:
pr: https://github.com/xenotaur/LCATS/pull/355
commit:
created_at: 2026-08-22T06:34:15+00:00
agent: codex_app
instruction_source: user request to capture the staged cross-segment density experiment design, workstream, and work items in one PR
session_transcript: pending
---

# Summary

Capture the staged cross-segment relation density experiment plan as LCATS
control-plane artifacts in one planning PR. The requested bundle includes a
durable design proposal, a `WS-PILOT-CROSS-SEGMENT-DENSITY` workstream, a
first preregistration/reconciliation work item, and later readiness,
feasibility, near-final execution, and final-analysis work items.

# Result

Created `PROP-LCATS-CROSS-SEGMENT-DENSITY-EXPERIMENT`, proposed
`WS-PILOT-CROSS-SEGMENT-DENSITY`, and added four new proposed work items:
`WI-EVENT-0078`, `WI-EVENT-0079`, `WI-EVENT-0080`, and `WI-EVENT-0081`.
Updated existing `WI-EVENT-0030` so it is explicitly linked into the new
workstream as the near-final empirical run, dependent on preregistration,
readiness, and a small real feasibility gate before execution.

# Validation

- `lrh validate --project-dir lcats/project` reported 0 errors.

# Follow-up

- Land this planning PR through review.
- Execute `WI-EVENT-0078` first to reconcile/preregister `WI-EVENT-0030`
  before any new density results are observed.
