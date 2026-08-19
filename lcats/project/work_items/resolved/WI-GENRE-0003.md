---
resolution: Implemented and merged in PR #314 (commit c33e6a5791b3581515216f072ea4d937df055498).
blocked_reason: null
blocked: false
id: WI-GENRE-0003
title: Define and validate genre-sidecar-v1
type: deliverable
status: resolved
owner: unassigned
contributors: []
assigned_agents: []
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap:
  - ROADMAP-CORE
related_workstreams:
  - WS-GENRE-EVIDENCE-SIDECARS
related_design:
  - lcats/project/design/proposals/proposed/genre-evidence-sidecars/00_proposal.md
  - lcats/project/workstreams/proposed/WS-GENRE-EVIDENCE-SIDECARS.md
  - lcats/project/work_items/resolved/WI-GENRE-0001.md
  - lcats/project/work_items/resolved/WI-GENRE-0002.md
  - experiments/05_metadata_genre_prefilter/README.md
  - lcats/src/lcats/analysis/corpus/annotate.py
  - lcats/src/lcats/analysis/corpus/promote.py
depends_on:
  - WI-GENRE-0002
blocked_by: []
expected_actions:
  - create_file
  - edit_file
  - run_tests
  - create_pr
  - write_docs
forbidden_actions:
  - force_push
  - delete_branch
  - run_model_calls
  - run_network_or_cache_build_without_explicit_approval
  - write_corpus_sidecars
  - promote_sidecars
  - modify_lcats_annotate_append_mode
  - modify_lcats_promote_tranche_semantics
  - implement_legacy_flat_sidecar_conversion
  - implement_human_adjudication_ui
  - implement_100_200_story_sample
acceptance:
  - A reusable genre-sidecar-v1 schema/validation module exists for append-only genre.json sidecars keyed by LCATS story ID
  - Validation covers metadata, model, and human assessment records with timestamps, scope, method/provenance, evidence, result, and repeated-run identity fields
  - Validation covers optional current_adjudication without requiring adjudication for a valid sidecar
  - Tests cover valid v1 sidecars, malformed v1 sidecars, legacy flat genre.json detection/diagnostics, and fixture examples for metadata/model/human assessment layers
  - Documentation records the v1 shape, required fields, validation behavior, legacy-conversion boundary, and non-goals before annotate/promote integration
  - scripts/test passes with no new failures
  - lrh validate reports 0 errors when run from lcats/
required_evidence:
  - test_output
  - lrh_validate
  - manual_review
artifacts_expected:
  - lcats/src/lcats/analysis/corpus/genre_sidecar.py
  - lcats/tests/analysis_tests/genre_sidecar_test.py
  - lcats/project/design/proposals/proposed/genre-evidence-sidecars/00_proposal.md
  - experiments/05_metadata_genre_prefilter/README.md
---

# Work Item: WI-GENRE-0003

## Summary

Define and validate `genre-sidecar-v1`, the append-only `genre.json` sidecar schema for LCATS story genre evidence.

## Problem / Context

`WI-GENRE-0002` produced experiment-local metadata assessment records, but the project still needs a reusable production-sidecar schema before `lcats promote`, `lcats annotate`, or corpus sidecar promotion can safely preserve and extend genre evidence. The governing proposal chooses an append-only `assessments[]` ledger so Gutenberg metadata rules, repeated model assessments, and human assessments can coexist with timestamps and provenance.

### Duplication search

- In-repo: Related code exists: `lcats annotate` writes flat `genre.json` sidecars, `lcats promote` validates basic sidecar JSON shape, and `experiments/05_metadata_genre_prefilter` emits assessment-shaped metadata evidence. No reusable `genre-sidecar-v1` schema/validator exists.
- Sibling repos: No sibling repository was identified for this project-specific LCATS sidecar validator.
- External libraries: No external library replaces the project-local schema and corpus-sidecar validation needs.
- Recommendation: Proceed by adding a focused LCATS validator module and tests, reusing existing sidecar/discovery conventions.

### Demand search

- Work items: `WI-GENRE-0002` explicitly deferred the final `genre-sidecar-v1` validator.
- Proposals: `PROP-GENRE-EVIDENCE-SIDECARS` requests sidecar schema validation as implementation step 3.
- Backlog: No separate backlog entry supersedes this work item.
- Recommendation: Proceed and link this item to `WS-GENRE-EVIDENCE-SIDECARS`.

## Scope

- Define the `genre-sidecar-v1` JSON shape for production `genre.json` sidecars.
- Add reusable validation helpers for sidecar-level fields and assessment-level fields.
- Validate metadata, model, and human assessment record variants without requiring all variants to be present in every sidecar.
- Validate optional `current_adjudication` while allowing it to be absent or null.
- Add fixtures/tests that document the accepted shape and representative failures.

## Required Changes

1. Add a reusable schema/validation module, likely `lcats/src/lcats/analysis/corpus/genre_sidecar.py`.
   - Define the required sidecar fields: `schema_version`, `lcats_id`, `story_path`, `assessments`, and optional `current_adjudication`.
   - Define assessment-level requirements for `assessment_id`, `label`, `generated_at`, `scope`, `method`, `provenance`, `evidence`, and `result`.
   - Allow metadata, model, and human assessment labels while preserving open-ended provenance/evidence details for future pipelines.
   - Require repeated model assessment records to carry enough run identity to distinguish independent runs for downstream voting.
   - Return structured validation findings rather than raising for ordinary malformed sidecars.

2. Add tests, likely `lcats/tests/analysis_tests/genre_sidecar_test.py`.
   - Cover a valid metadata-rule assessment sidecar.
   - Cover a valid model assessment with model/backend/run provenance.
   - Cover a valid human assessment and optional `current_adjudication`.
   - Cover repeated model assessments with distinct run identity.
   - Cover malformed sidecars: missing schema version, wrong `assessments` type, missing LCATS ID, missing assessment fields, invalid timestamp shape, invalid scope, and duplicate `assessment_id`.
   - Cover legacy flat `AssessmentResult.to_dict()` style `genre.json` detection/diagnostics without converting it in this work item.

3. Update documentation.
   - Document the `genre-sidecar-v1` shape and validation expectations.
   - Document the legacy-flat-sidecar boundary: this item may detect/report legacy shape, but production conversion belongs to a later item.
   - Document that this item does not write or promote sidecars.

4. Preserve integration boundaries.
   - Do not change `lcats annotate` append behavior yet.
   - Do not change `lcats promote` tranche semantics yet.
   - Do not write `genre.json` files into `data/` or `corpora/`.

## Non-Goals

- Do not run model calls.
- Do not build, download, refresh, or repair the Gutenberg metadata cache.
- Do not write or promote corpus `genre.json` sidecars.
- Do not implement `lcats annotate` append mode.
- Do not implement sidecar-tranche promotion in `lcats promote`.
- Do not implement production legacy flat-sidecar conversion.
- Do not add a human adjudication UI or workflow.
- Do not implement the 100-200 story sample.

## Acceptance Criteria

- A reusable `genre-sidecar-v1` schema/validation module exists for append-only `genre.json` sidecars keyed by LCATS story ID.
- Validation accepts representative metadata, model, and human assessment records with timestamps, scope, method/provenance, evidence, and result fields.
- Validation accepts repeated model assessment records when each record has distinct run identity/provenance.
- Validation accepts `current_adjudication: null` and validates a populated adjudication shape without making adjudication mandatory.
- Validation reports structured findings for malformed v1 sidecars and legacy flat `genre.json` sidecars.
- Tests cover valid and invalid examples without writing corpus sidecars or calling models/network/cache builders.
- Documentation explains the schema, validator behavior, and deferred integration boundaries.
- `scripts/test` passes with no new failures.
- `lrh validate` reports 0 errors.

## Validation

- `scripts/version tools`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `cd lcats && lrh validate`
- From `lcats/`: `python -m unittest discover -s tests -p '*_test.py'`

Readiness check after authoring:

- `cd lcats && lrh work-items readiness WI-GENRE-0003 --format md`

## Risk Notes

- The validator should not freeze model/provider-specific provenance too tightly; local `gpt-oss:20b`, OpenAI-compatible APIs, and future human workflows need room to add fields.
- The validator should distinguish invalid v1 from legacy flat sidecars; silently accepting legacy shape as v1 would make append-mode migration unsafe.
- `current_adjudication` is still an open design edge. This item should validate a minimal reference/snapshot shape but avoid forcing human adjudication into every sidecar.
- Integration with `lcats annotate` and `lcats promote` is intentionally deferred so this item stays reviewable and does not mutate corpus behavior prematurely.
