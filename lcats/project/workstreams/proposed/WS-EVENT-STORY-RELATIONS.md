---
id: WS-EVENT-STORY-RELATIONS
kind: planning_node
title: Story-Level Cross-Segment Relation Extraction for Event-Role-World
status: proposed
stage: planned
origin: design_review
summary: Implement the recommended post-reconciliation story-level causal relation pass (option A) for the Event-Role-World extractor, so genuinely cross-segment causal/explanatory relations are captured for the Worldcon paper's analysis.
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap: []
related_design:
  - project/design/proposals/adopted/lcats-event-role-world-extractor/00_proposal.md
  - project/design/event-role-world-cross-segment-relations-evaluation.md
work_items:
  - WI-EVENT-0029
exit_criteria:
  - A story-level relation pass implementing option A is merged, producing cross-segment EventRelation entries with no double-counting against same-segment relations
  - export.build_analysis_tables and baseline.summarize_annotations both include story-level relations in their outputs
  - All work items under this workstream resolved and lrh validate reports 0 errors
---

# Workstream: Story-Level Cross-Segment Relation Extraction for Event-Role-World

## Purpose

This workstream implements the architecture that WI-EVENT-0028 determined
is needed and recommended: a post-reconciliation story-level relation pass
(option A) that discovers causal, enabling, preventing, temporal,
motivational, and explanatory relations whose two endpoints live in
different segments. The current per-segment stage-6 pass
(`relation_extractor.py`, implemented in WI-EVENT-0026) cannot represent
this today — it only ever receives its own segment's event IDs, and
`RELATION_SYSTEM_PROMPT` forbids linking outside that list.

## Origin

WI-EVENT-0028's investigation (`project/design/event-role-world-cross-segment-relations-evaluation.md`,
merged PR #154) ran a direct reading-based pilot over four corpus stories
and found a clear, genre-differentiated result: both SF/horror stories
sampled (Lovecraft's "The Colour Out of Space" and "Cool Air") exhibited
multiple long-range causal chains, while the mystery and general-fiction
comparison stories exhibited none. This confirmed — not merely
hypothesized — that per-segment-only relation counting would undercount
SF's causal density specifically, threatening the validity of the paper's
central genre comparison. The investigation recommended option A over
options B and C as the cheapest architecture that targets this phenomenon
directly, reusing already-resolved evidence spans rather than requiring
new cross-segment text-search or `event_ids` machinery.

WS-EVENT-CROSS-SEGMENT-RELATIONS (which coordinated WI-EVENT-0028) has
since closed — its own scope and Non-Goals were explicitly
investigation-only ("Does not implement any chosen architecture — that is
deferred to a follow-up deliverable work item once a recommendation
exists"). This workstream is that follow-up, created fresh rather than
reopening the closed one, mirroring how WS-EVENT-CROSS-SEGMENT-RELATIONS
itself was created fresh after WS-EVENT-ROLE-WORLD closed.

## Scope

- Implement option A: a new relation-extraction pass that runs once per
  story after `schema.reconcile_story_annotations` has produced global
  entity IDs and the full list of segment-qualified events, discovering
  relations between events in different segments.
- Reuse each event's already-resolved `EvidenceSpan` as one endpoint's
  evidence rather than requiring a fresh quote search across a
  multi-segment text blob.
- Extend `export.build_analysis_tables` and `baseline.summarize_annotations`
  to include these newly-discovered story-level relations in their
  respective outputs, without double-counting relations already present in
  a segment's own `relations` list.
- Check the corpus's actual story-length distribution to decide whether
  option A's long-story windowing caveat (a hierarchical, chapter-level
  then story-level pass) needs to be built now, or can remain deferred if
  story lengths in this corpus stay well within one call's context window.

## Prior Art Check

### Duplication search
- In-repo: No existing story-level relation extraction exists in `lcats/`.
  `schema.reconcile_story_annotations` (WI-EVENT-0026) performs story-level
  entity alias reconciliation and same-segment relation ID qualification
  only — its own docstring explicitly disclaims discovering cross-segment
  relations, and WI-EVENT-0028's investigation confirmed this gap is real
  via direct textual evidence.
- Sibling repos: None identified.
- External libraries: None identified.
- Recommendation: Proceed.

### Demand search
- Work items: None found beyond WI-EVENT-0028's recommendation.
- Proposals: None found beyond the governing Event-Role-World extractor
  proposal, which this workstream extends per its "cross-segment
  relations" schema-sketch expectation.
- Backlog: No matching entries.
- Recommendation: No action.

## Work Items

- **WI-EVENT-0029** — deliverable: implements option A's story-level
  relation pass, extends `export.py` and `baseline.py` to consume it, and
  checks corpus story-length distribution to size the windowing caveat.

## Exit Criteria

(see frontmatter `exit_criteria:` above)

## Non-Goals

- Does not implement option B (growing per-story event index) or option C
  (widened per-segment window) — option A was the recommended
  architecture; the other two are not pursued unless option A proves
  infeasible.
- Does not run the larger stratified pilot (5-10 stories per genre) that
  WI-EVENT-0028 flagged as still needed before the paper publishes a
  cross-segment relation density figure — that is a corpus/methodology
  task for the paper, not an implementation task for this workstream.
- Does not reopen or modify WS-EVENT-CROSS-SEGMENT-RELATIONS,
  WS-EVENT-ROLE-WORLD, or any of their resolved work items.
- Does not choose the Worldcon paper's final statistical method.

## Relationship to Design

- Design proposal: `project/design/proposals/adopted/lcats-event-role-world-extractor/00_proposal.md`
- Design doc: `project/design/event-role-world-cross-segment-relations-evaluation.md`
