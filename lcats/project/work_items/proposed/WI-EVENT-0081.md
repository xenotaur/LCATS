---
resolution: null
blocked_reason: null
blocked: false
id: WI-EVENT-0081
title: Produce the final cross-segment density analysis package
type: deliverable
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
  - WI-EVENT-0030
blocked_by: []
expected_actions:
  - create_file
  - edit_file
  - create_report
  - create_pr
forbidden_actions:
  - run_new_llm_extraction_without_explicit_approval
  - change_density_metric_after_results
  - hide_excluded_stories
  - force_push
  - delete_branch
acceptance:
  - If WI-EVENT-0030 ran at the approved near-final scale, final analysis artifacts include the raw-source references, per-story density rows, per-genre summaries, excluded-story/failure taxonomy, usage/cost report, figure/table source, and generated paper-facing figure or table
  - If a preregistered gate stopped WI-EVENT-0030 before near-final execution, the final package instead includes the gate evidence, named stop condition, costs incurred, unavailable-result explanation, and recommendation to stop, revise, or file follow-on work
  - The written interpretation states whether WI-EVENT-0030 confirms, weakens, contradicts, or did not reach the evidentiary conditions needed to assess WI-EVENT-0028's long-range cross-segment relation hypothesis
  - Genre-label reliability and any low-confidence strata are reported alongside the density findings when density findings exist, or carried forward as planned-but-unobserved caveats when the run is gate-stopped
  - The package states whether to stop, expand to more stories, revise methodology, or file follow-on work
  - lrh validate reports 0 errors
required_evidence:
  - manual_review
  - lrh_validate
artifacts_expected:
  - experiments/03_cross_segment_relation_pilot/results/
  - experiments/03_cross_segment_relation_pilot/results/final_density_analysis/
---

## Summary

Turn the completed `WI-EVENT-0030` run output into the final paper-facing
cross-segment density analysis package.

## Problem / Context

The density experiment is not complete when raw pilot output exists. The
paper needs a defensible analysis package that records the exact data used,
exclusions/failures, costs, genre-label uncertainty, figure/table source,
and interpretation of whether the long-range relation hypothesis held. If
the staged gates stop the near-final run before density results exist, the
analysis package should report that stopped outcome rather than requiring a
figure that the workstream deliberately chose not to produce.

### Duplication search

- In-repo: Related: `WI-EVENT-0030` requires findings and methodology under
  the experiment directory, but no separate final analysis/figure package
  item exists.
- Sibling repos: None identified.
- External libraries: No external substitute; ordinary plotting or table
  tooling may be used during implementation.
- Recommendation: Proceed after `WI-EVENT-0030` completes or records a
  gate-stopped outcome with enough evidence to analyze.

### Demand search

- Work items: `WI-EVENT-0030` produces the run evidence this item consumes.
- Proposals: `PROP-LCATS-CROSS-SEGMENT-DENSITY-EXPERIMENT` requests final
  paper-facing analysis.
- Backlog: No separate matching entry found.
- Recommendation: Link this item to `WS-PILOT-CROSS-SEGMENT-DENSITY`.

## Scope

- Analyze the completed near-final density run, or the gate-stopped outcome
  if preregistered thresholds prevented the run.
- Produce paper-facing figures/tables and a written interpretation when
  density results exist; otherwise produce a gate-stopped evidence package.
- Preserve enough provenance for a reader to audit how the result was
  computed.

## Required Changes

1. Read the committed `WI-EVENT-0030` output artifacts, or the gate-stop
   evidence if the near-final run did not execute, and verify that the
   analysis inputs match the preregistered artifact contract.
2. Create `experiments/03_cross_segment_relation_pilot/results/final_density_analysis/`
   with figure/table source, generated figure or table, and a written
   analysis report when density results exist; for a gate-stopped outcome,
   include the gate evidence, stop condition, costs incurred, and
   unavailable-result explanation instead.
3. When density results exist, report cross-segment-only density separately
   from folded total density, preserving the weakly inferred partition.
4. Include excluded-story/failure taxonomy, usage/cost summary, genre-label
   reliability caveats, and a stop/expand/revise/follow-up recommendation.

## Non-Goals

- Does not run new extraction calls unless the user separately approves a
  bounded paid rerun or expansion.
- Does not change the metric definition after results are known.
- Does not hide excluded stories or count failed partial outputs as zero.
- Does not choose all final paper prose outside the analysis package.

## Acceptance Criteria

- If `WI-EVENT-0030` ran at the approved near-final scale, final analysis
  artifacts include the raw-source references, per-story density rows,
  per-genre summaries, excluded-story/failure taxonomy, usage/cost report,
  figure/table source, and generated paper-facing figure or table.
- If a preregistered gate stopped `WI-EVENT-0030` before near-final
  execution, the final package instead includes the gate evidence, named
  stop condition, costs incurred, unavailable-result explanation, and
  recommendation to stop, revise, or file follow-on work.
- The written interpretation states whether `WI-EVENT-0030` confirms,
  weakens, contradicts, or did not reach the evidentiary conditions needed
  to assess `WI-EVENT-0028`'s long-range cross-segment relation hypothesis.
- Genre-label reliability and any low-confidence strata are reported
  alongside the density findings when density findings exist, or carried
  forward as planned-but-unobserved caveats when the run is gate-stopped.
- The package states whether to stop, expand to more stories, revise
  methodology, or file follow-on work.
- `lrh validate` reports 0 errors.

## Validation

- `lrh validate`

## Risk Notes

- If `WI-EVENT-0030` is gate-stopped before a full result, this item should
  analyze that stopped outcome rather than forcing a density figure or
  per-genre conclusion that does not exist.
- The final analysis should not overstate low-confidence strata, especially
  if genre-label agreement or exclusion rates are uneven.

## Related Workstream and Designs

- Workstream: `lcats/project/workstreams/proposed/WS-PILOT-CROSS-SEGMENT-DENSITY.md`
- Design: `lcats/project/design/proposals/proposed/lcats-cross-segment-density-experiment/00_proposal.md`
- Input run: `lcats/project/work_items/proposed/WI-EVENT-0030.md`
