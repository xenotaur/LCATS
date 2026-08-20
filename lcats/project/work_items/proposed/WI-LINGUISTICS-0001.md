---
resolution: null
blocked_reason: null
blocked: false
id: WI-LINGUISTICS-0001
title: Build standalone linguistic-feature sidecar extraction
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
related_workstreams: []
related_design:
  - project/design/proposals/adopted/lcats-story-bucket-layout/00_proposal.md
  - project/design/proposals/adopted/lcats-pipeline-checkpointing/00_proposal.md
depends_on: []
blocked_by: []
expected_actions:
  - create_file
  - edit_file
  - add_cli_command
  - write_docs
  - run_tests
  - create_pr
forbidden_actions:
  - implement_balanced_sampler
  - modify_segmentation_logic
  - implement_knight_novum_sidecar_contract
  - promote_experimental_sidecars
  - make_paid_api_calls
  - force_push
  - delete_branch
acceptance:
  - A reusable linguistics-sidecar-v1 data model, validator, deterministic serializer, and atomic writer exist
  - A pure story-analysis API computes compact aggregate story-level linguistic features using the existing normalized NLPBackend and surface-feature extractor
  - A standalone LCATS CLI command processes explicit stories, story buckets, directories, and story-list files with skip/resume/overwrite behavior and machine-readable run summaries
  - Tests cover deterministic aggregation, validation, provenance and input hashes, atomic writes, skip/overwrite/resume behavior, failure isolation, missing backend diagnostics, fixtures, and optional NLP smoke tests
  - Documentation explains local setup, sidecar shape, backend requirements, example commands, and deferred Worldcon sample follow-ups
  - lrh validate reports 0 errors and scripts/test passes after all files are written
required_evidence:
  - lrh_validate
  - test_output
  - validation_output
  - manual_review
artifacts_expected:
  - lcats/src/lcats/analysis/linguistics/
  - lcats/src/lcats/analysis/corpus/linguistics_cli.py
  - lcats/src/lcats/cli.py
  - lcats/tests/analysis_tests/linguistics_test.py
  - lcats/tests/analysis_tests/fixtures/
  - lcats/docs/how-to/run-linguistics.md
  - lcats/docs/reference/cli-commands.md
---

## Summary

Build a standalone LCATS linguistic-feature extractor that analyzes one or
more canonical stories and writes deterministic, schema-valid
`linguistics.json` sidecars independently of the Event-Role-World event and
relation pipeline.

## Problem / Context

The ERW subsystem already contains the reusable pieces for linguistic surface
features: a normalized `NLPBackend` protocol with spaCy/Stanza/fake
implementations and a `surface_feature_extractor` that computes lexical,
sentence, morphology, dependency, and token information. That functionality is
currently embedded inside ERW processing, so researchers cannot run a cheap,
resumable, NLP-only linguistic pass over arbitrary LCATS stories or story
buckets without invoking unrelated event/relation infrastructure.

This item provides the infrastructure needed before the later Worldcon
genre-balanced sample run: a compact, aggregate story-level
`linguistics.json` sidecar, optional detailed token/dependency output, a
generic runner over explicit story paths or buckets, schema validation,
atomic publication, deterministic serialization, and portable tests. The
implementation must not wait for or couple itself to `WI-GENRE-0004`'s
eventual manifest shape.

### Duplication search
- In-repo: Related implementation exists in
  `src/lcats/analysis/event_role_world/nlp_backend.py` and
  `src/lcats/analysis/event_role_world/surface_feature_extractor.py`, and
  sidecar/checkpoint conventions exist in `src/lcats/analysis/corpus/` and
  `src/lcats/utils/checkpoint.py`. No standalone linguistic sidecar schema,
  validator, API, or CLI exists.
- Sibling repos: No sibling repository was identified for this
  project-specific LCATS sidecar runner.
- External libraries: spaCy and Stanza already provide NLP analysis and are
  already abstracted behind the LCATS `NLPBackend`; no external library
  replaces the project-local sidecar schema, story-bucket integration, and
  LRH validation needs.
- Recommendation: Proceed by reusing the existing ERW NLP backend and
  surface-feature extractor while adding a focused LCATS sidecar API/runner.

### Demand search
- Work items: No existing proposed linguistic-features work item was found.
  `WI-GENRE-0004` needs the later sample selection/run but deliberately owns
  genre sampling and validation, not this generic linguistic infrastructure.
- Proposals: The adopted story-bucket and pipeline-checkpointing proposals
  provide relevant conventions, but no adopted proposal defines a standalone
  linguistic sidecar contract.
- Backlog: Related sidecar and pipeline reliability entries exist, but no
  entry directly requests this reusable linguistic-feature sidecar runner.
- Recommendation: No action beyond creating and implementing this focused
  work item.

## Scope

- Define and validate a compact `linguistics-sidecar-v1` JSON object written
  as `linguistics.json` beside a canonical story's `story.json`.
- Analyze story-level aggregate features by reusing the existing normalized
  `NLPBackend` and ERW surface-feature extractor rather than duplicating its
  counting logic.
- Support a generic input collection of explicit `story.json` paths, story
  bucket directories, collection/corpus directories, and ordinary story-list
  files.
- Provide deterministic serialization, atomic publication, skip/resume and
  explicit overwrite semantics, per-story error isolation, and a
  machine-readable run summary.
- Keep optional token/dependency detail separate from the default compact
  `linguistics.json` unless explicitly requested.

## Required Changes

1. Add a `lcats.analysis.linguistics` package containing:
   - sidecar dataclasses or typed helpers for `linguistics-sidecar-v1`;
   - structured validation findings/results;
   - story identity, body-hash, backend/model provenance helpers;
   - deterministic serializer and atomic writer;
   - a pure `analyze_story(...)` operation over a loaded story and
     `NLPBackend`.
2. Add a batch runner that:
   - resolves input paths through the canonical story-bucket selector;
   - accepts explicit story-list files without assuming any
     `WI-GENRE-0004` manifest shape;
   - supports default skip, validation of existing output, resume, and
     explicit overwrite;
   - records per-story success, skipped, overwritten, and failed outcomes in
     a JSON-serializable summary.
3. Add a thin CLI entry point, likely `lcats linguistics`, following the
   existing `src/lcats/cli.py` subcommand pattern.
4. Add documentation with local setup, optional spaCy/Stanza model guidance,
   sidecar shape, example commands, output behavior, and deferred follow-up
   work for the balanced sample adapter/run.
5. Add deterministic unit and fixture tests covering aggregate calculations,
   empty/minimal/unicode stories, schema validity, provenance/input hashes,
   deterministic bytes, atomic writes, skip/resume/overwrite behavior,
   failure isolation, missing backend diagnostics, real story/bucket fixture
   loading, and optional spaCy/Stanza smoke tests that skip when unavailable.
6. Add an implementation report in the PR body identifying completed scope and
   explicit follow-ups for the `WI-GENRE-0004` manifest adapter, selected
   Worldcon sample run, long-story performance measurement, and any later
   corpus-promotion workflow.

## Non-Goals

- Do not implement or alter `WI-GENRE-0004`'s balanced sampler or manifest
  format.
- Do not modify segmentation logic or the `WI-SEGMENT-0070` work item.
- Do not invent a Knight/Novum or combined ERW sidecar contract.
- Do not promote experimental linguistic sidecars into `corpora/`.
- Do not make paid API calls or require an LLM.
- Do not change unrelated defaults or behavior in ERW, annotation, promotion,
  or corpus discovery.
- Do not add a generalized workflow/orchestration framework unless an
  existing LCATS helper is already sufficient and reused.

## Acceptance Criteria

- A reusable `linguistics-sidecar-v1` data model, validator, deterministic
  serializer, and atomic writer exist.
- The default `linguistics.json` sidecar is compact and aggregate
  story-level: token/dependency detail is absent unless separately enabled.
- The sidecar provenance is sufficient to reproduce the result: schema
  version, extractor version, NLP backend, backend model/package version
  where available, input body hash, story identity/path, and relevant
  options.
- The pure story-analysis API computes aggregate metrics using the existing
  normalized `NLPBackend` and `surface_feature_extractor`.
- The CLI accepts one or more explicit stories, story buckets, directories,
  and story-list files; it reports per-story outcomes and writes a
  machine-readable run summary.
- Existing-output behavior is safe: valid matching output is skipped by
  default, stale/invalid output is diagnosed, and replacement requires an
  explicit overwrite/recompute mode.
- Missing spaCy/Stanza packages or requested models produce clear diagnostics
  without turning the portable deterministic suite into a network/model
  requirement.
- Tests and documentation cover the required behavior without touching the
  balanced sample, segmentation work, corpus sidecars, paid API paths, or
  Knight/Novum sidecar design.

## Validation

- `scripts/version tools`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `python -m unittest tests.analysis_tests.linguistics_test`
- `lrh validate`

## Risk Notes

- The ERW surface extractor currently returns full token records. This item
  must reuse its aggregate logic without making full token output the default
  `linguistics.json` payload, or every story bucket will become larger than
  needed for coverage/statistical analysis.
- spaCy/Stanza package or model availability varies by environment. The
  command should fail clearly when a requested real backend is unavailable,
  while tests that require downloaded models should skip rather than fail.
- Output-sidecar writes in a story bucket are intentionally local artifacts
  for this infrastructure work. Promotion to corpus state is a separate
  policy/workflow decision and must not be smuggled into this item.
- A later `WI-GENRE-0004` manifest adapter should attach at the input
  resolution layer only; coupling this runner to an unlanded manifest shape
  would create avoidable coordination debt.

## Related Workstream and Designs

- Focus: `project/focus/current_focus.md`
- Roadmap: `project/roadmap/roadmap.md`
- Design: `project/design/proposals/adopted/lcats-story-bucket-layout/00_proposal.md`
- Design: `project/design/proposals/adopted/lcats-pipeline-checkpointing/00_proposal.md`
- Related work item: `project/work_items/proposed/WI-GENRE-0004.md`
- Related work item: `project/work_items/proposed/WI-SEGMENT-0070.md`
- Prior ERW surface-feature implementation: `project/work_items/resolved/WI-EVENT-0024.md`
