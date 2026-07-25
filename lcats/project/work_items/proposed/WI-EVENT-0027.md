---
resolution: null
blocked_reason: null
blocked: false
id: WI-EVENT-0027
title: Implement Event-Role-World extractor stage 8 (optional hypothesis pass)
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
  - WI-EVENT-0026
blocked_by: []
expected_actions:
  - create_file
  - edit_file
  - run_tests
  - create_pr
forbidden_actions:
  - implement_graph_database
  - force_push
  - delete_branch
acceptance:
  - A Hypothesis schema is defined and validated, extending SegmentWorldAnnotation, with an explicit hypothesis marker distinguishing it from extractive claims
  - The hypothesis pass extracts belief/uncertainty/perspective/emotion-appraisal annotations with subject, proposition/target, evidence, and confidence, excluded from primary quantitative claims unless validated
  - export.py's artifact-validation and analysis-table export cover the new hypothesis layer
  - baseline.py's summary/comparison functions are extended to report hypothesis rates alongside the other layers
  - lrh validate reports 0 errors and scripts/test passes
  - WS-EVENT-ROLE-WORLD's exit criterion for stage 8 becomes satisfiable
required_evidence:
  - lrh_validate
  - test_output
  - manual_review
artifacts_expected:
  - lcats/lcats/analysis/event_role_world/hypothesis_extractor.py
  - lcats/lcats/analysis/event_role_world/schema.py (extended, not new)
  - lcats/lcats/analysis/event_role_world/processor.py (extended, not new)
  - lcats/lcats/analysis/event_role_world/export.py (extended, not new)
  - lcats/lcats/analysis/event_role_world/baseline.py (extended, not new)
  - lcats/tests/analysis_tests/event_role_world_test.py (extended, not new)
---

## Summary

Implement the last deferred stage of the Event-Role-World extractor's
Recommended staged pipeline: stage 8, the optional hypothesis pass. Adds a
`Hypothesis` dataclass recording belief, uncertainty, perspective, or
emotion/appraisal annotations, with subject, proposition/target, evidence,
confidence, and an explicit hypothesis marker — extracted per segment and
integrated into the existing story-level (`StoryWorldAnnotation`) pipeline
built by `WI-EVENT-0024` and `WI-EVENT-0026`.

## Problem / Context

`WS-EVENT-ROLE-WORLD` coordinates implementation of the Science-Fiction
Event-Role-World extractor proposed in
`project/design/proposals/proposed/lcats-event-role-world-extractor/00_proposal.md`,
in support of the Worldcon "Shape of Science Fiction" paper
(`FOCUS-WORLDCON-2026`). `WI-EVENT-0024` (stages 1-5) and `WI-EVENT-0026`
(stages 6-7 and 9) both explicitly deferred stage 8 as optional, per the
proposal's own framing. `WS-EVENT-ROLE-WORLD`'s exit criteria require stage
8 to be "implemented, or explicitly deferred with a follow-up work item
recorded" — prose deferral notes in the other two work items do not satisfy
this literally, since no work item existed to track it. This item is that
recorded follow-up, and implements the pass itself.

### Duplication search
- In-repo: No existing implementation found. No `hypothesis_extractor.py`
  or `Hypothesis` dataclass anywhere in `lcats/`. The proposal's own schema
  sketch (`00_proposal.md:175-177`) names `Hypothesis` as a design sketch,
  not code. `implement_stage_8_hypothesis_pass`/`implement_hypothesis_pass`
  are used in `WI-EVENT-0024`/`WI-EVENT-0026` as `forbidden_actions` scope-
  control markers deferring stage 8 (they also appear referentially in
  `schema.py`'s docstrings, alongside those markers, not as an
  implementation).
- Sibling repos: None identified.
- External libraries: None identified.
- Recommendation: Proceed.

### Demand search
- Work items: None found beyond `WI-EVENT-0024`'s and `WI-EVENT-0026`'s own
  deferral notes and `WS-EVENT-ROLE-WORLD`'s exit criterion requiring this
  item to exist.
- Proposals: None found beyond the governing proposal itself.
- Backlog: No matching entries.
- Recommendation: No action.

## Scope

- Hypothesis pass (stage 8): extract belief, uncertainty, perspective, and
  emotion/appraisal annotations from segment text, each with a subject,
  proposition or target, evidence, confidence, and an explicit hypothesis
  marker — per the proposal's fact/hypothesis distinction, these are never
  extractive facts even when confidently stated.
- Schema definition for `Hypothesis` per the proposal's "Core schema
  sketch", integrated into `SegmentWorldAnnotation` and, via story-level
  reconciliation, `StoryWorldAnnotation`.
- Backend `tool=` schema wiring for the new extraction call, consistent
  with the existing entity/event/relation/discourse extractor pattern
  (`JSONPromptExtractor`'s `tool_schema` parameter) — not `json_object`
  mode.
- Cost/baseline reporting for the new LLM-backed pass, consistent with the
  existing `PassUsage` pattern.
- Extending `export.py`'s artifact-validation checks and analysis-table
  export to cover hypotheses.
- Extending `baseline.py`'s fixed-chunk-vs-segment comparison to report
  hypothesis rates alongside the existing layers.

## Required Changes

1. Extend `lcats/lcats/analysis/event_role_world/schema.py` with a
   `Hypothesis` dataclass, add a `hypotheses` field to
   `SegmentWorldAnnotation`, and extend `validate_segment_annotation` to
   check its ID resolution and evidence alignment (mirroring the existing
   relations/discourse validation added by `WI-EVENT-0026`). Hypotheses
   must be clearly excluded from any primary quantitative claim by
   construction — e.g. not counted in the same rate fields as extractive
   entities/events unless a caller explicitly opts in — per the proposal's
   risk table entry on confusing interpretive hypotheses with extractive
   facts.
2. Create `hypothesis_extractor.py` for stage 8, following the existing
   entity/event/relation/discourse extractor pattern (LLM extraction via
   `JSONPromptExtractor` with a `tool_schema`, evidence resolution via
   `schema.EvidenceCursor`, its own independent cursor per the discourse-
   layer-cursor-sharing bug fixed in `WI-EVENT-0026`'s review).
3. Extend `processor.py` to orchestrate the hypothesis pass after stages
   6-7, following the same `PassUsage`/token-tracking and routed-through-
   `extract()` error-handling pattern as the existing passes.
4. Extend `export.py`'s `build_analysis_tables()` and `validate_artifacts()`
   to cover the hypothesis layer.
5. Extend `baseline.py`'s `summarize_annotations()` to report a
   hypotheses-per-1000-words rate alongside the existing layers.
6. Extend `lcats/tests/analysis_tests/event_role_world_test.py` covering
   the new schema, the extraction pass, its export/validation coverage,
   and the baseline extension.

## Non-Goals

- Does not require a graph database or CBR/RAG adaptation.
- Does not choose the Worldcon paper's final statistical method.
- Does not treat hypotheses as primary quantitative evidence for any
  genre-comparison claim — per the proposal, optional hypotheses are
  excluded from primary quantitative claims unless independently validated.
- Does not implement cross-segment relation extraction — a separate,
  already-tracked follow-up in `WS-EVENT-ROLE-WORLD.md`'s "Known
  Follow-ups" section, unrelated to this item's scope.

## Acceptance Criteria

- A `Hypothesis` schema is defined and validated, extending
  `SegmentWorldAnnotation`, with an explicit hypothesis marker
  distinguishing it from extractive claims.
- The hypothesis pass extracts belief/uncertainty/perspective/emotion-
  appraisal annotations with subject, proposition/target, evidence, and
  confidence, excluded from primary quantitative claims unless validated.
- `export.py`'s artifact-validation and analysis-table export cover the new
  hypothesis layer.
- `baseline.py`'s summary/comparison functions are extended to report
  hypothesis rates alongside the other layers.
- `lrh validate` reports 0 errors and `scripts/test` passes.
- `WS-EVENT-ROLE-WORLD`'s exit criterion for stage 8 becomes satisfiable
  (this work item's existence satisfies "recorded"; its completion
  satisfies "implemented").

## Validation

- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`

## Risk Notes

- Confusing interpretive hypotheses with extractive facts is a known risk
  per the proposal's own risk table; the schema and any downstream
  reporting must keep hypothesis fields, certainty, and confidence
  separate from extractive-fact fields, and exclude optional hypotheses
  from primary quantitative claims unless independently validated.
- LLM-generated hypotheses (belief, perspective, emotion/appraisal) are
  inherently more speculative than extractive passes; expect lower
  precision and plan for stratified human review before treating any
  hypothesis-derived metric as reliable, consistent with the proposal's
  general recommendation for interpretive annotations.

## Related Workstream and Designs

- Workstream: `project/workstreams/proposed/WS-EVENT-ROLE-WORLD.md`
- Design: `project/design/proposals/proposed/lcats-event-role-world-extractor/00_proposal.md`
