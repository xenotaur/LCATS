---
resolution: null
blocked_reason: null
blocked: false
id: WI-EVENT-0028
title: Investigate need and design for cross-segment causal relation extraction
type: investigation
status: proposed
priority: medium
owner: unassigned
contributors: []
assigned_agents: []
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap: []
related_workstreams:
  - WS-EVENT-CROSS-SEGMENT-RELATIONS
related_design:
  - project/design/proposals/adopted/lcats-event-role-world-extractor/00_proposal.md
depends_on:
  - WI-EVENT-0026
blocked_by: []
expected_actions:
  - create_file
  - create_pr
forbidden_actions:
  - implement_cross_segment_relation_extraction
  - implement_stage_8_hypothesis_pass
  - force_push
  - delete_branch
acceptance:
  - A clear yes/no determination on whether the paper's analysis needs cross-segment causal relations, grounded in the paper's actual claims rather than speculative need
  - If needed, at least two candidate architectures are evaluated with tradeoffs (cost/latency, implementation complexity, accuracy risk), and a recommendation is made
  - The investigation is recorded as a design doc under project/design/, following WI-EVENT-0025's precedent
  - lrh validate reports 0 errors
required_evidence:
  - lrh_validate
  - manual_review
artifacts_expected:
  - project/design/event-role-world-cross-segment-relations-evaluation.md
---

## Summary

Determine whether the Worldcon "Shape of Science Fiction" paper's
comparative analysis requires causal relations that span segment boundaries
— a cause established in one segment and its effect appearing in a
different segment — which the current per-segment stage-6 relation pass
(`relation_extractor.py`, WI-EVENT-0026) cannot represent. If cross-segment
relations are needed, evaluate architecture options for giving stage 6
broader (multi-segment or full-story) context and produce a design
recommendation. This work item does not implement any architecture.

## Problem / Context

`WS-EVENT-CROSS-SEGMENT-RELATIONS` was created after a review comment on
WI-EVENT-0026 (`chatgpt-codex-connector`, PR #150) established that the
per-segment stage-6 relation pass structurally cannot produce a relation
whose source and target events live in different segments — the extractor
only ever receives its own segment's event IDs. That review round documented
the limitation rather than fixing it, since designing broader context for
stage 6 is a meaningfully different extraction strategy, not a small
addition. WS-EVENT-ROLE-WORLD (which coordinated WI-EVENT-0024 through
WI-EVENT-0027) has since closed without addressing this — its own exit
criteria did not require it. This work item is the recorded follow-up.

### Duplication search
- In-repo: No existing cross-segment relation extraction or investigation
  exists in `lcats/`. `schema.reconcile_story_annotations` (WI-EVENT-0026)
  performs story-level entity alias reconciliation and relation ID
  qualification only — its own docstring explicitly disclaims discovering
  cross-segment relations.
- Sibling repos: None identified.
- External libraries: None identified.
- Recommendation: Proceed.

### Demand search
- Work items: None found beyond the review comment and Known-Follow-up note
  that prompted this item.
- Proposals: None found beyond the governing Event-Role-World extractor
  proposal, which this item's eventual recommendation would extend.
- Backlog: No matching entries.
- Recommendation: No action.

## Scope

- Determine whether the paper's candidate metrics and claims (per the
  governing proposal's "Resulting scientific claim" and "Candidate
  paper-facing metrics" sections) actually require cross-segment causal
  links, or whether per-segment relation density (already implemented) is
  sufficient.
- If cross-segment relations are needed, evaluate at least two candidate
  architectures, for example:
  - A story-level relation pass run after per-segment extraction and
    story-level reconciliation have produced global entity/event IDs,
    querying across all segments' events at once.
  - Feeding stage 6 a compact story-level event index (summaries, not full
    text) alongside the current segment, so it can reference prior events
    without a full-story context window.
  - Widening the per-segment extraction window to include a fixed number of
    neighboring segments.
- Evaluate each candidate on cost/latency (additional LLM calls or larger
  context per call), implementation complexity relative to the existing
  per-segment pattern, and accuracy risk (hallucinated cross-segment links
  are a known general risk per the governing proposal's risk table).
- Produce a design recommendation only.

## Required Changes

1. Research the governing proposal's claims and metrics sections to
   determine whether cross-segment causal relations are actually load-bearing
   for the paper, or a purely hypothetical concern the review raised.
2. If needed, draft and evaluate candidate architectures per Scope above.
3. Write `project/design/event-role-world-cross-segment-relations-evaluation.md`
   recording the determination, the evaluated architectures (if any), and
   the recommendation — following the structure of
   `project/design/event-role-world-surface-feature-nlp-evaluation.md`
   (WI-EVENT-0025's precedent).
4. If a recommendation to implement is made, note that a follow-up
   deliverable work item should be created — do not create it as part of
   this item.

## Non-Goals

- Does not implement any chosen architecture — implementation is a follow-up
  deliverable work item's scope, not this one's.
- Does not implement stage 8 (hypothesis pass) — already implemented by
  WI-EVENT-0027; out of scope here regardless.
- Does not reopen or modify WS-EVENT-ROLE-WORLD or any of its resolved work
  items.
- Does not choose the Worldcon paper's final statistical method.

## Acceptance Criteria

- A clear yes/no determination on whether the paper's analysis needs
  cross-segment causal relations, grounded in the paper's actual claims
  rather than speculative need.
- If needed, at least two candidate architectures are evaluated with
  tradeoffs (cost/latency, implementation complexity, accuracy risk), and a
  recommendation is made.
- The investigation is recorded as a design doc under `project/design/`,
  following WI-EVENT-0025's precedent.
- `lrh validate` reports 0 errors.

## Validation

- `lrh validate`

## Risk Notes

- LLM-hallucinated cross-segment causal links are a known general risk per
  the governing proposal's risk table; any recommended architecture must
  require aligned evidence, certainty, and confidence, and expect stratified
  human review before treating cross-segment relation-density metrics as
  reliable.
- There is a real risk this investigation concludes cross-segment relations
  are not needed at all — that is a valid, complete outcome, not a failure
  to find one; do not manufacture a need to justify an architecture change.

## Related Workstream and Designs

- Workstream: `project/workstreams/proposed/WS-EVENT-CROSS-SEGMENT-RELATIONS.md`
- Design: `project/design/proposals/adopted/lcats-event-role-world-extractor/00_proposal.md`
