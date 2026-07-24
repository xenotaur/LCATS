---
resolution: null
blocked_reason: null
blocked: false
id: WI-EVENT-0026
title: Implement Event-Role-World extractor stages 6-7 and 9 (relation, discourse/SF-tag, and validation/export)
type: deliverable
status: proposed
priority: medium
owner: unassigned
contributors: []
assigned_agents: []
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap:
  - ROADMAP-CORE
related_workstreams:
  - WS-EVENT-ROLE-WORLD
related_design:
  - project/design/proposals/proposed/lcats-event-role-world-extractor/00_proposal.md
depends_on:
  - WI-EVENT-0024
blocked_by: []
expected_actions:
  - create_file
  - edit_file
  - run_tests
  - create_pr
forbidden_actions:
  - implement_stage_8_hypothesis_pass
  - implement_graph_database
  - force_push
  - delete_branch
acceptance:
  - New Event-Role-World object schemas (EventRelation, SpeechAct, ExplanationDiscourse, SFWorldModelTag) are defined and validated, extending the existing SegmentWorldAnnotation
  - The relation pass extracts causal/enabling/preventing/temporal/motivational/explanatory links between existing Event IDs, with evidence and certainty (explicit/strongly_implied/weakly_inferred); explicit and strongly-implied links are in the main relations list, weakly-inferred links are partitioned into a separate list on the same EventRelation type (not the stage-8 Hypothesis dataclass)
  - The discourse/SF-tag pass extracts speech acts, explanation discourse, and SF world-model tags, each with evidence and, where possible, linked entity/event IDs
  - Validation/export emits canonical per-story JSON plus derived JSONL/CSV analysis tables, and the proposal's Artifact validation checks pass
  - baseline.py's summary/comparison functions are extended to cover relations, discourse, and SF-tag counts (not just token/model/timing), and the fixed-chunk-vs-segment comparison is run with the full stage 1-9-minus-8 extractor so the new layers' metrics are covered by the same chunking control as the existing ones
  - Story-level reconciliation (alias resolution and cross-segment relation linking into StoryWorldAnnotation) is actually implemented and covered by a dedicated test, not just the container dataclass
  - lrh validate reports 0 errors and scripts/test passes; stage 8 (hypothesis pass) is explicitly out of scope
required_evidence:
  - lrh_validate
  - test_output
  - manual_review
artifacts_expected:
  - lcats/lcats/analysis/event_role_world/relation_extractor.py
  - lcats/lcats/analysis/event_role_world/discourse_extractor.py
  - lcats/lcats/analysis/event_role_world/export.py
  - lcats/lcats/analysis/event_role_world/schema.py (extended, not new)
  - lcats/lcats/analysis/event_role_world/processor.py (extended, not new)
  - lcats/lcats/analysis/event_role_world/baseline.py (extended, not new)
  - lcats/tests/analysis_tests/event_role_world_test.py (extended, not new)
---

## Summary

Implement the next three stages of the Event-Role-World extractor's
Recommended staged pipeline — relation pass, discourse/SF-tag pass, and
validation/export — extending WI-EVENT-0024's entity/participant,
event/semantic-role, and temporal/spatial anchor output with causal/relation
links between events, speech-act and explanation-discourse tagging, SF
world-model tags, and a canonical export path with artifact validation.

## Problem / Context

`WS-EVENT-ROLE-WORLD` coordinates implementation of the Science-Fiction
Event-Role-World extractor proposed in
`project/design/proposals/proposed/lcats-event-role-world-extractor/00_proposal.md`,
in support of the Worldcon "Shape of Science Fiction" paper
(`FOCUS-WORLDCON-2026`). `WI-EVENT-0024` implemented stages 1-5 (input
contract through anchor pass) and was merged in PR #148; its own scope
explicitly deferred stages 6-7 (relation, discourse/SF tag) and 9
(validation/export) "to a closely-following work item" and stage 8
(optional hypothesis pass) to whenever the workstream chooses to pick it up.
This work item is that closely-following item for stages 6-7 and 9. Stage 8
remains out of scope per the proposal's own framing of it as optional.

### Duplication search
- In-repo: No existing implementation found. No `relation_extractor.py`,
  `discourse_extractor.py`, `export.py`, `EventRelation`, `SpeechAct`, or
  `SFWorldModelTag` anywhere in `lcats/`. The proposal's own schema sketch
  (`00_proposal.md:166-179`) names these as a design sketch, not code.
- Sibling repos: None identified.
- External libraries: None identified.
- Recommendation: Proceed.

### Demand search
- Work items: None found beyond `WI-EVENT-0024`'s own deferral note.
- Proposals: None found beyond the governing proposal itself.
- Backlog: No matching entries.
- Recommendation: No action.

## Scope

- Relation pass (stage 6): extract causal, enabling, preventing, temporal,
  motivational, and explanatory links between events already produced by
  `WI-EVENT-0024`'s event-role pass.
- Discourse/SF-tag pass (stage 7): extract speech acts, explanatory
  passages, and SF world-model tags from segment text.
- Validation and export (stage 9): emit canonical per-story JSON artifacts
  and derived JSONL/CSV analysis tables, and run the proposal's artifact
  validation checks (ID resolution, evidence alignment, evidence/certainty
  on causal links, evidence on SF tags, inferred/hypothesis marking,
  deterministic exports).
- Schema definitions for `EventRelation`, `SpeechAct`,
  `ExplanationDiscourse`, and `SFWorldModelTag` per the proposal's "Core
  schema sketch", plus `StoryWorldAnnotation` for story-level entity/alias
  reconciliation and cross-segment relations.
- Backend `tool=` schema wiring for the new extraction calls, consistent
  with `WI-EVENT-0024`'s existing pattern (`JSONPromptExtractor`'s
  `tool_schema` parameter) — not `json_object` mode.
- Cost/baseline reporting for the new LLM-backed passes (token counts,
  model, elapsed time), consistent with `WI-EVENT-0024`'s `PassUsage`
  pattern.
- Extending the fixed-chunk-vs-segment baseline comparison
  (`baseline.py`) to cover the new relation/discourse/SF-tag layers, not
  just the existing entity/event/anchor counts — the proposal's Cost and
  baseline requirements section requires every SF-vs-other-genre comparison
  metric to be checked against this control, and relation-density/SF-tag
  metrics are new comparison metrics this item introduces.
- Implementing story-level reconciliation (alias resolution across
  segments, cross-segment relation linking) into `StoryWorldAnnotation` —
  not just defining the container dataclass.

## Required Changes

1. Extend `lcats/lcats/analysis/event_role_world/schema.py` with
   `EventRelation`, `SpeechAct`, `ExplanationDiscourse`, `SFWorldModelTag`,
   and `StoryWorldAnnotation` dataclasses, plus validation helpers
   analogous to `validate_segment_annotation`. `EventRelation` instances
   with `certainty="weakly_inferred"` are partitioned into a separate list
   from `explicit`/`strongly_implied` ones — this is a storage split on
   `EventRelation` itself, not the stage-8 `Hypothesis` dataclass or any
   stage-8 orchestration logic (out of scope per `forbidden_actions`).
2. Create `relation_extractor.py` for stage 6, following the existing
   entity/event extractor pattern (LLM extraction via `JSONPromptExtractor`
   with a `tool_schema`, evidence resolution via `schema.EvidenceCursor`).
3. Create `discourse_extractor.py` for stage 7, same extraction pattern.
4. Create `export.py` for stage 9: canonical per-story JSON serialization,
   JSONL/CSV derived table export, and the artifact-validation checks from
   the proposal's "Validation and metrics" > "Artifact validation" section.
5. Extend `processor.py` to orchestrate stages 6-7-9 after the existing
   stages 2-5, following the same `PassUsage`/token-tracking pattern.
   Implement actual story-level reconciliation (alias resolution,
   cross-segment relation linking) that populates `StoryWorldAnnotation`
   from the per-segment annotations — not just the dataclass shape.
6. Extend `baseline.py`'s `summarize_annotations()` and
   `compare_chunking_strategies()` to report relation, discourse, and
   SF-tag counts/rates alongside the existing entity/event/anchor ones, and
   run the fixed-chunk-vs-segment comparison with the full stages-1-9-minus-8
   extractor so the new layers are covered by the same chunking control.
7. Extend `lcats/tests/analysis_tests/event_role_world_test.py` covering
   the new schemas, both new extraction passes, the export/validation
   path, the extended baseline comparison, and story-level reconciliation
   (including a case with a cross-segment alias or relation).

## Non-Goals

- Does not implement stage 8 (optional hypothesis pass) — the standalone
  `Hypothesis` dataclass (belief/uncertainty/perspective/emotion
  annotations) and any orchestration of a dedicated hypothesis pass are
  deferred per the proposal's own framing of stage 8 as optional; a
  follow-up work item should be recorded if and when the workstream picks
  it up. This is distinct from partitioning `weakly_inferred` `EventRelation`
  instances into a separate list, which is in scope for stage 6 itself.
- Does not require a graph database or CBR/RAG adaptation.
- Does not choose the Worldcon paper's final statistical method.
- Does not re-implement or modify stages 1-5 (`WI-EVENT-0024`'s scope).

## Acceptance Criteria

- New Event-Role-World object schemas (`EventRelation`, `SpeechAct`,
  `ExplanationDiscourse`, `SFWorldModelTag`) are defined and validated,
  extending the existing `SegmentWorldAnnotation`.
- The relation pass extracts causal/enabling/preventing/temporal/
  motivational/explanatory links between existing `Event` IDs, with
  evidence and certainty (`explicit`/`strongly_implied`/`weakly_inferred`);
  explicit and strongly-implied links are in the main relations list,
  weakly-inferred links are partitioned into a separate list on the same
  `EventRelation` type (not the stage-8 `Hypothesis` dataclass), per the
  proposal's causality tradeoff table.
- The discourse/SF-tag pass extracts speech acts, explanation discourse,
  and SF world-model tags, each with evidence and, where possible, linked
  entity/event IDs.
- Validation/export emits canonical per-story JSON plus derived JSONL/CSV
  analysis tables, and the proposal's "Artifact validation" checks pass (IDs
  resolve, evidence spans align, causal links carry evidence+certainty, SF
  tags carry evidence, inferred claims are marked, exports are
  deterministic).
- `baseline.py`'s summary/comparison functions are extended to cover
  relations, discourse, and SF-tag counts (not just token/model/timing
  reporting), and the fixed-chunk-vs-segment comparison is run with the
  full stages-1-9-minus-8 extractor so the new layers' metrics are covered
  by the same chunking control as the existing entity/event/anchor metrics.
- Story-level reconciliation (alias resolution and cross-segment relation
  linking into `StoryWorldAnnotation`) is actually implemented and covered
  by a dedicated test — not just the container dataclass.
- `lrh validate` reports 0 errors and `scripts/test` passes; stage 8
  (hypothesis pass) is explicitly out of scope and not implemented here.

## Validation

- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`

## Risk Notes

- LLM-hallucinated causal links are a known risk per the proposal's own risk
  table; require aligned evidence, certainty, and confidence, and compare
  against an explicit-link baseline before treating relation-density metrics
  as reliable.
- Over-tagging SF categories is a known risk; use the proposal's small
  controlled tag inventory and grounded examples, and expect stratified
  human review before treating SF-tag counts as publication-quality.
- Deterministic export is an explicit artifact-validation requirement; any
  non-determinism in ID assignment or ordering during export will fail
  validation and must be caught before this item is considered complete.

## Related Workstream and Designs

- Workstream: `project/workstreams/proposed/WS-EVENT-ROLE-WORLD.md`
- Design: `project/design/proposals/proposed/lcats-event-role-world-extractor/00_proposal.md`
