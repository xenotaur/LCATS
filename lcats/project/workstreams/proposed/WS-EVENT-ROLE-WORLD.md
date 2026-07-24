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
work_items:
  - WI-EVENT-0024
  - WI-EVENT-0025
  - WI-EVENT-0026
exit_criteria:
  - The proposal's Recommended staged pipeline stages 1-7 and 9 (input contract, surface feature pass, entity participant pass, event-role pass, anchor pass, relation pass, discourse/SF tag pass, and validation/export) are implemented, reusing the existing segment/evidence substrate without reimplementing scene/sequel extraction
  - The optional hypothesis pass (stage 8) is implemented, or explicitly deferred with a follow-up work item recorded
  - New Event-Role-World object schemas (Event, EntityMention, EventRelation, etc.) are called through the backend's existing tool= structured-output path, not json_object mode
  - Validation and metrics export (per-story JSON, JSONL/CSV analysis tables) implemented and passes the proposal's artifact-validation checks
  - Cost/baseline reporting (token counts, model, elapsed time per pass; fixed-chunk-vs-segment comparison) implemented per the proposal's Cost and baseline requirements section
  - All work items under this workstream resolved and lrh validate reports 0 errors
---

# Workstream: SF Event-Role-World Extractor Implementation

## Purpose

This workstream coordinates implementation of the Science-Fiction
Event-Role-World extractor: entity/participant, event/semantic-role,
temporal-spatial anchor, causal-relation, discourse, and SF world-model
annotation layers built on top of LCATS's existing scene/sequel segment
output. It exists to support the forthcoming Worldcon Academic paper "The
Shape of Science Fiction," and follows a review-hardened design proposal
that has already been through two rounds of reviewer feedback.

## Scope

- Implement the proposal's Recommended staged pipeline (stages 1-9): input
  contract, surface feature pass, entity participant pass, event-role pass,
  anchor pass, relation pass, discourse/SF tag pass, optional hypothesis
  pass, and validation/export — reusing the existing segment/evidence
  substrate as the input contract rather than reimplementing it.
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
- In-repo: No existing implementation found in `lcats/lcats/`. The
  governing proposal's own architecture sketch names an
  `EventRoleWorldProcessor` and a suggested `event_role_world/` module
  layout (`00_proposal.md:91`, `00_proposal.md:132`) — these are design
  sketches, not code; no implementation exists under `lcats/lcats/`. (This
  repo has no `.claude/skills/` directory to check.)
- Sibling repos: None identified.
- External libraries: None identified.
- Recommendation: Proceed.

### Demand search
- Work items: None found.
- Proposals: None found beyond the governing proposal itself.
- Backlog: No matching entries.
- Recommendation: No action.

## Work Items

The proposal's own Recommended staged pipeline (stages 1-9) does not define
an early/late split — stages 1-7 and 9 are presented as the main pipeline,
with only stage 8 (optional hypothesis pass) marked explicitly optional.
The following phasing is a workstream-level scoping decision, not something
the proposal itself prescribes:

- **WI-EVENT-0024** — covers stages 1-5 (input contract through anchor
  pass): reusing the existing segment/evidence substrate as input,
  extracting entities/participants/actant roles and events/semantic roles,
  and anchoring them temporally and spatially — plus the backend `tool=`
  schema-wiring fix and the cost/baseline reporting requirements. Stage 2
  (surface features) is implemented as a lightweight, dependency-free
  lexical/structural pass; see WI-EVENT-0025.
- **WI-EVENT-0025** — investigation (not implementation): evaluates
  whether a real NLP library (spaCy, NLTK, Stanza, UDPipe) should be
  adopted for stage 2's syntactic/morphological features, since this repo
  has no such dependency today. Produces a design recommendation only.
- **WI-EVENT-0026** — covers stages 6-7 (relation, discourse/SF tag) and
  stage 9 (validation/export), building on WI-EVENT-0024's entity/event/
  anchor output. Stage 8 (hypothesis pass) remains optional per the
  proposal itself and is out of scope for this item.

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
