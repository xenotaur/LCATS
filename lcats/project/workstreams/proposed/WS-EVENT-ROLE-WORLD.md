---
id: WS-EVENT-ROLE-WORLD
kind: planning_node
title: SF Event-Role-World Extractor Implementation
status: proposed
stage: designed
origin: design_review
summary: Implement the Science-Fiction Event-Role-World extractor proposed for the Worldcon "Shape of Science Fiction" paper, layered on the existing LCATS scene/sequel segment substrate.
related_focus: []
related_roadmap: []
related_design:
  - project/design/proposals/proposed/lcats-event-role-world-extractor/00_proposal.md
work_items: []
exit_criteria:
  - v0.1 seed extractor implemented per the proposal's staged pipeline (paragraph indexing through per-segment semantic audit), reusing the existing segment/evidence substrate without reimplementing it
  - New Event-Role-World object schemas (Event, EntityMention, EventRelation, etc.) are called through the backend's existing tool= structured-output path, not json_object mode
  - Validation and metrics export (per-story JSON, JSONL/CSV analysis tables) implemented and passes the proposal's artifact-validation checks
  - Cost/baseline reporting (token counts, model, elapsed time per pass; fixed-chunk-vs-segment comparison) implemented per the proposal's Cost and baseline requirements section
  - All work items under this workstream resolved and lrh validate reports 0 errors
---

# WS-EVENT-ROLE-WORLD

## Purpose

This workstream coordinates implementation of the Science-Fiction
Event-Role-World extractor: entity/participant, event/semantic-role,
temporal-spatial anchor, causal-relation, discourse, and SF world-model
annotation layers built on top of LCATS's existing scene/sequel segment
output. It exists to support the forthcoming Worldcon Academic paper "The
Shape of Science Fiction," and follows a review-hardened design proposal
that has already been through two rounds of reviewer feedback.

## Scope

- Implement the v0.1 seed extractor described in the proposal's "Proposed
  v0.1 deliverable" section: segment metadata, GACD/ERAC reuse, cohesion
  fields, confidence/rationale, per-segment audit, validation report, and
  optional SF feature tags.
- Wire new Event-Role-World object schemas through the backend's existing
  `tool=` structured-output path (per the proposal's Implementation
  prerequisites section) rather than the current scene/sequel prompts'
  `json_object` mode.
- Implement the cost/baseline reporting and metrics export required by the
  proposal's Validation and metrics section.
- Land associated work items through the standard LRH execution lifecycle
  (`/lrh-implement` → `/lrh-review-response` → `/lrh-confirm-fixes` →
  `/lrh-closeout`).

## Prior Art Check

### Duplication search
- In-repo: No existing implementation found (no `EventRoleWorld`/
  `event_role_world` module or references anywhere in `lcats/` or
  `.claude/skills/`).
- Sibling repos: None identified.
- External libraries: None identified.
- Recommendation: Proceed.

### Demand search
- Work items: None found.
- Proposals: None found beyond the governing proposal itself.
- Backlog: No matching entries.
- Recommendation: No action.

## Work Items

No work items exist yet. The recommended first work item covers the
proposal's own "Proposed v0.1 deliverable" scope: stage 0 (story loading)
through stage 5 (agreement and quality metrics), reusing the existing
`make_annotated_segment_extractor` two-pass extractor, plus the backend
`tool=` schema-wiring fix and the cost/baseline reporting requirements.
Later annotator layers (relation, discourse/SF-tag, hypothesis passes) are
expected as follow-up work items once v0.1 lands. To be created via
`/lrh-work-item` after this workstream is confirmed.

## Exit Criteria

(see frontmatter `exit_criteria:` above)

## Non-Goals

- Does not reimplement scene/sequel extraction, GACD/ERAC classification,
  or paragraph indexing/alignment — these are reused as-is from the existing
  substrate.
- Does not require a graph database or CBR/RAG adaptation in this workstream
  — deferred per the proposal's own non-goals until the extracted data
  justifies them.
- Does not choose the Worldcon paper's final statistical method.
- Does not require full Story Logic extraction.

## Relationship to Design

- Design proposal: `project/design/proposals/proposed/lcats-event-role-world-extractor/00_proposal.md`
