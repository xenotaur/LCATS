---
id: WS-EVENT-CROSS-SEGMENT-RELATIONS
kind: planning_node
title: Cross-Segment Causal Relation Extraction for Event-Role-World
status: proposed
stage: designed
origin: design_review
summary: Investigate whether the Worldcon paper's analysis needs causal relations spanning segment boundaries, and if so, design how the Event-Role-World extractor's stage-6 relation pass gets broader (multi-segment or full-story) context.
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap: []
related_design:
  - project/design/proposals/adopted/lcats-event-role-world-extractor/00_proposal.md
work_items:
  - WI-EVENT-0028
exit_criteria:
  - A design recommendation exists on whether cross-segment causal relation extraction is needed for the Worldcon paper's analysis, grounded in the paper's actual claims
  - If needed, a recommended architecture for giving stage 6 broader context is documented with tradeoffs, ready to hand off to an implementation work item
  - All work items under this workstream resolved and lrh validate reports 0 errors
---

# Workstream: Cross-Segment Causal Relation Extraction for Event-Role-World

## Purpose

This workstream investigates and, if warranted, designs an extension to the
Event-Role-World extractor's relation layer (stage 6) so it can represent
genuinely cross-segment causal relations — a cause established in one
segment and its effect appearing in a different segment. The current
per-segment stage-6 pass (`relation_extractor.py`, implemented in
WI-EVENT-0026) cannot represent this today: it only ever receives its own
segment's event IDs, so a relation's source/target event can never actually
reference a different segment's event.

## Origin

Raised as a P1 review comment during WI-EVENT-0026's review
(`chatgpt-codex-connector`, PR #150). The review-response fix documented the
limitation (a "Known limitation" note on `schema.StoryWorldAnnotation` and a
"Known Follow-ups" entry on WS-EVENT-ROLE-WORLD) rather than attempting a fix
in that PR, since designing broader context for stage 6 is a meaningfully
different, larger extraction strategy than the current per-segment `tool=`
call — not a small addition to that work item's scope. WS-EVENT-ROLE-WORLD
has since closed (all its own exit criteria were met without this); this
workstream picks up that recorded follow-up as new scope.

## Scope

- Investigate whether the Worldcon "Shape of Science Fiction" paper's
  comparative analysis actually requires cross-segment causal relations, or
  whether per-segment relations (already implemented) are sufficient for the
  paper's claims.
- If cross-segment relations are needed: evaluate candidate architectures for
  giving stage 6 broader context (e.g., a story-level relation pass run
  after per-segment extraction completes and story-level reconciliation has
  produced global entity/event IDs; feeding stage 6 a compact story-level
  event index instead of only the current segment's; widening the
  per-segment extraction window to include neighboring segments), with
  tradeoffs on cost/latency, implementation complexity, and accuracy risk.
- Produce a design recommendation, not an implementation — mirroring how
  WI-EVENT-0025's investigation preceded WI-EVENT-0024's implementation
  decision.

## Prior Art Check

### Duplication search
- In-repo: No existing cross-segment relation extraction or story-level
  relation-context design exists in `lcats/`. `schema.reconcile_story_annotations`
  (WI-EVENT-0026) performs story-level entity alias reconciliation and
  relation ID qualification, but explicitly does not attempt cross-segment
  relation discovery — see its "Known limitation" docstring note.
- Sibling repos: None identified.
- External libraries: None identified.
- Recommendation: Proceed.

### Demand search
- Work items: None found beyond the review comment and Known-Follow-up note
  that prompted this workstream.
- Proposals: None found beyond the governing Event-Role-World extractor
  proposal, which this workstream extends.
- Backlog: No matching entries.
- Recommendation: No action.

## Work Items

- **WI-EVENT-0028** — investigation (not implementation): determines whether
  cross-segment causal relations are needed for the paper's analysis, and if
  so, evaluates and recommends an architecture for giving stage 6 broader
  context. Produces a design recommendation only.

## Exit Criteria

(see frontmatter `exit_criteria:` above)

## Non-Goals

- Does not implement any chosen architecture — that is deferred to a
  follow-up deliverable work item once a recommendation exists.
- Does not reopen or modify WS-EVENT-ROLE-WORLD or any of its resolved work
  items (WI-EVENT-0024 through WI-EVENT-0027).
- Does not choose the Worldcon paper's final statistical method.

## Relationship to Design

- Design proposal: `project/design/proposals/adopted/lcats-event-role-world-extractor/00_proposal.md`
