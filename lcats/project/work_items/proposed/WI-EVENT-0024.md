---
resolution: null
blocked_reason: null
blocked: false
id: WI-EVENT-0024
title: Implement Event-Role-World extractor stages 1-5 (input contract through anchor pass)
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
depends_on: []
blocked_by: []
expected_actions:
  - create_file
  - edit_file
  - run_tests
  - create_pr
forbidden_actions:
  - implement_relation_pass
  - implement_discourse_sf_tag_pass
  - implement_hypothesis_pass
  - implement_graph_database
  - force_push
  - delete_branch
acceptance:
  - New Event-Role-World object schemas (EvidenceSpan, EntityMention, Entity, SemanticRole, Event, TemporalAnchor, SpatialAnchor) are defined and validated
  - Extraction calls for these schemas use the backend's existing tool= structured-output path, not json_object mode
  - Given existing LCATS story JSON plus segments, the extractor produces real syntactic/morphological surface features via a swappable NLPBackend (Stanza and spaCy both supported), plus entity/participant, event/semantic-role, and temporal/spatial anchor annotations per segment
  - Per-pass LLM-backed calls record token counts, model, and elapsed time (not just call counts)
  - A fixed-chunk-vs-segment comparison is produced by running the same extractor over both scene/sequel segments and fixed-token chunks, per the proposal's Cost and baseline requirements section
  - lrh validate reports 0 errors and scripts/test passes after all files are written
required_evidence:
  - lrh_validate
  - test_output
  - manual_review
artifacts_expected:
  - lcats/lcats/analysis/event_role_world/__init__.py
  - lcats/lcats/analysis/event_role_world/schema.py
  - lcats/lcats/analysis/event_role_world/nlp_backend.py
  - lcats/lcats/analysis/event_role_world/processor.py
  - lcats/lcats/analysis/event_role_world/surface_feature_extractor.py
  - lcats/lcats/analysis/event_role_world/entity_extractor.py
  - lcats/lcats/analysis/event_role_world/event_extractor.py
  - lcats/lcats/analysis/event_role_world/baseline.py
  - lcats/tests/analysis_tests/event_role_world_test.py
  - lcats/lcats/analysis/llm_extractor.py (extended, not new)
  - lcats/pyproject.toml (adds stanza, spacy dependencies)
---

## Summary

Implement the first five stages of the Event-Role-World extractor's
Recommended staged pipeline — input contract, surface feature pass, entity
participant pass, event-role pass, and anchor pass — producing
entity/participant, event/semantic-role, and temporal/spatial anchor
annotations for each existing LCATS segment.

## Problem / Context

`WS-EVENT-ROLE-WORLD` coordinates implementation of the Science-Fiction
Event-Role-World extractor proposed in
`project/design/proposals/proposed/lcats-event-role-world-extractor/00_proposal.md`,
in support of the Worldcon "Shape of Science Fiction" paper
(`FOCUS-WORLDCON-2026`). The proposal's own "Recommended staged pipeline"
(`00_proposal.md`, stages 1-9) does not define an early/late split; this
work item implements stages 1-5 as the workstream's chosen first phase,
deferring stages 6-7 (relation, discourse/SF tag) and 9 (validation/export)
to a closely-following work item, and stage 8 (optional hypothesis pass) to
whenever the workstream chooses to pick it up.

### Duplication search
- In-repo: No existing implementation found. No `EntityParticipantAnnotator`,
  `EventRoleAnnotator`, `AnchorAnnotator`, or `SurfaceFeatureAnnotator`
  anywhere in `lcats/`. The proposal's own architecture sketch
  (`00_proposal.md:91`) names these as a design sketch, not code.
- Sibling repos: None identified.
- External libraries: None identified.
- Recommendation: Proceed.

### Demand search
- Work items: None found.
- Proposals: None found beyond the governing proposal itself.
- Backlog: No matching entries.
- Recommendation: No action.

## Scope

- Extraction passes for stages 1-5: input contract (reuse existing segment
  JSON), surface feature pass, entity participant pass, event-role pass,
  and anchor pass.
- Schema definitions for `EvidenceSpan`, `EntityMention`, `Entity`,
  `SemanticRole`, `Event`, `TemporalAnchor`, and `SpatialAnchor` per the
  proposal's "Core schema sketch".
- Backend `tool=` schema wiring: new extraction calls use
  `OpenAIBackend`/`AnthropicBackend`'s existing tool/function-calling path
  (`lcats/lcats/llm/openai_backend.py`, `lcats/lcats/llm/anthropic_backend.py`),
  not `json_object` mode.
- Cost/baseline reporting: record token counts, model, and elapsed time per
  LLM-backed pass, and produce a fixed-chunk-vs-segment comparison by
  running the same extractor over both scene/sequel segments and
  fixed-token chunks, per the proposal's "Cost and baseline requirements"
  section.
- **Stage 2 surface features (revised from the original scope):**
  `WI-EVENT-0025`'s NLP-library evaluation
  (`project/design/event-role-world-surface-feature-nlp-evaluation.md`)
  recommended deferring library adoption, which created a real tension with
  this WI's own literal acceptance criterion requiring "syntactic,
  morphological" output — a dependency-free heuristic cannot produce that.
  Per an explicit follow-up decision, this work item resolves that tension
  by **adopting real NLP libraries now** (Stanza first, for near-term
  multilingual direction; spaCy also supported) rather than narrowing the
  acceptance criterion. Both libraries are hidden behind a swappable
  `NLPBackend` Protocol (`nlp_backend.py`), mirroring
  `lcats.llm.backend.LLMBackend`'s existing pattern
  (`lcats/lcats/llm/backend.py:31-68`), so the library choice remains
  swappable rather than locked in.

## Required Changes

1. Create `lcats/lcats/analysis/event_role_world/` package (`__init__.py`,
   `schema.py` for the object definitions, `nlp_backend.py` for the
   swappable NLP-toolkit Protocol (`StanzaBackend`, `SpacyBackend`,
   `FakeNLPBackend`), `processor.py` for pipeline orchestration,
   `surface_feature_extractor.py` for stage 2, `entity_extractor.py` for
   stage 3, `event_extractor.py` for stages 4-5, `baseline.py` for the
   fixed-chunk-vs-segment comparison) — following the proposal's "Suggested
   downstream module layout" as a starting point, not a requirement (the
   proposal itself notes this is "a future LCATS implementation sketch, not
   an LRH implementation requirement").
2. Wire extraction calls through the backend's existing `tool=` parameter
   with a JSON Schema per object type, per `00_proposal.md`'s
   "Implementation prerequisites" section. Extends
   `lcats.analysis.llm_extractor.JSONPromptExtractor` with an optional
   `tool_schema` parameter (backward-compatible; existing callers unaffected)
   rather than writing a separate extractor class, per design decision.
3. Add token/model/elapsed-time capture to each LLM-backed pass, using the
   `input_tokens`/`output_tokens`/`model` fields already returned by
   `BackendResponse` (`lcats/lcats/llm/backend.py`).
4. Reuse the existing segment/evidence substrate
   (`lcats/lcats/analysis/story_processors.py`,
   `lcats/lcats/analysis/text_segmenter.py`) as the stage-1 input contract
   — do not reimplement segmentation, paragraph indexing, or GACD/ERAC
   classification.
5. Implement the fixed-chunk-vs-segment baseline comparison required by the
   proposal's "Cost and baseline requirements" section.
6. Add `lcats/tests/analysis_tests/event_role_world_test.py` covering
   schema validation, each extraction pass, the baseline comparison, and
   both real `NLPBackend` implementations (each skipped independently, not
   failed, if its model isn't downloaded locally).
7. Add `stanza` and `spacy` to `lcats/pyproject.toml` dependencies.
8. Add `WI-EVENT-0024` to `WS-EVENT-ROLE-WORLD`'s `work_items:` list.

## Non-Goals

- Does not implement stages 6-7 (relation pass, discourse/SF tag pass) or
  stage 9 (validation/export) — deferred to a follow-up work item.
- Does not implement stage 8 (optional hypothesis pass) — optional per the
  proposal itself.
- Does not require a graph database or CBR/RAG adaptation.
- Does not reimplement scene/sequel extraction, GACD/ERAC classification,
  or paragraph indexing/alignment.
- Does not choose the Worldcon paper's final statistical method.

## Acceptance Criteria

- New Event-Role-World object schemas (`EvidenceSpan`, `EntityMention`,
  `Entity`, `SemanticRole`, `Event`, `TemporalAnchor`, `SpatialAnchor`) are
  defined and validated.
- Extraction calls for these schemas use the backend's existing `tool=`
  structured-output path, not `json_object` mode.
- Given existing LCATS story JSON plus segments, the extractor produces
  real syntactic/morphological surface features (POS tags, dependency
  relations, morphological features — not a lexical-only heuristic) via a
  swappable `NLPBackend`, with both Stanza and spaCy implementations
  available, plus entity/participant, event/semantic-role, and
  temporal/spatial anchor annotations per segment — an implementation that
  skips stage 2 (surface features) does not satisfy this item.
- Per-pass LLM-backed calls record token counts, model, and elapsed time
  (not just call counts).
- A fixed-chunk-vs-segment comparison is produced by running the same
  extractor over both scene/sequel segments and fixed-token chunks, per the
  proposal's Cost and baseline requirements section.
- `lrh validate` reports 0 errors and `scripts/test` passes after all files
  are written. Tests requiring a downloaded NLP model skip (not fail) when
  the model isn't present, so `scripts/test` stays runnable in a clean
  checkout per LCATS's offline/no-network-CI constraint.

## Validation

- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`

## Risk Notes

- Automatic entity/coreference extraction is known to struggle on older
  literary prose (epithets, pronouns, nested narration) per the proposal's
  own risk table — expect lower precision on the corpus's pre-1950 material.
- The backend `tool=` path has not previously been exercised for this many
  distinct object schemas in one pipeline; watch for schema-size or
  tool-choice-forcing limits during implementation.
- Adopting Stanza adds a real PyTorch dependency (not the hypothetical
  discussed in `WI-EVENT-0025`'s evaluation), meaningfully increasing
  install size and download time. Neither Stanza's nor spaCy's accuracy on
  this corpus's older/translated prose has been benchmarked — the
  evaluation's own recommendation to run a stratified accuracy sample
  before treating the output as reliable still applies and was not part of
  this work item's scope.

## Related Workstream and Designs

- Workstream: `project/workstreams/proposed/WS-EVENT-ROLE-WORLD.md`
- Design: `project/design/proposals/proposed/lcats-event-role-world-extractor/00_proposal.md`
