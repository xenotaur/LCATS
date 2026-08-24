---
resolution: null
blocked_reason: null
blocked: false
id: WI-LINGUISTICS-0005
title: Add a validated rich token-detail v2 schema
type: deliverable
status: proposed
owner: unassigned
contributors: []
assigned_agents: []
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap:
  - ROADMAP-CORE
related_workstreams:
  - WS-COMPARATIVE-LEXICAL-VISUALIZATION
related_design:
  - project/design/proposals/proposed/comparative-lexical-visualization/00_proposal.md
  - docs/reference/linguistics-sidecar.md
depends_on: []
blocked_by: []
expected_actions:
  - create_file
  - edit_file
  - run_tests
  - write_docs
forbidden_actions:
  - force_push
  - delete_branch
  - break_token_detail_v1
  - require_token_detail_by_default
  - run_full_corpus
  - promote_sidecars
acceptance:
  - linguistics-token-detail-v2 preserves sentence identity, stable token indices, source character offsets, normalized linguistic fields, and exact backend/model provenance
  - Validation enforces source identity, unique monotonic indices, source-matching spans, sentence-local dependency heads, recognized UPOS values, and compact-sidecar count reconciliation
  - Existing compact linguistics-sidecar-v1 and optional token-detail-v1 readers and defaults remain backward compatible
  - The common CLI/runner can emit v2 through output-root or copied-bucket experiment paths without writing into corpora/ unless explicitly targeted
  - Unit, runner, CLI, schema, resume, stale-output, and representative literary-text tests pass
required_evidence:
  - test_output
  - validation_output
  - lrh_validate
  - manual_review
artifacts_expected:
  - src/lcats/analysis/linguistics/sidecar.py
  - src/lcats/analysis/linguistics/runner.py
  - src/lcats/analysis/event_role_world/nlp_backend.py
  - tests/linguistics_tests/
  - docs/reference/linguistics-sidecar.md
  - docs/how-to/run-linguistics.md
---

# Work Item: WI-LINGUISTICS-0005

## Summary

Introduce a backward-compatible `linguistics-token-detail-v2` artifact with
sentence/token identity, source spans, backend capabilities, strict validation,
and experiment-safe runner support.

## Problem / Context

LCATS already normalizes lemma, UPOS, XPOS, morphology, and dependencies, but
the checked-in experiments omitted optional token detail. The v1 token-detail
shape is also flattened: dependency heads are sentence-relative while sentence
identity, stable global identity, and source offsets are absent. A durable
lexical/POS pipeline needs stronger source alignment and invariants before data
is regenerated.

### Duplication search

- In-repo: extend the existing `TokenRecord`, linguistic sidecar, validator,
  runner, and output-root behavior. V1 is related prior art but does not satisfy
  v2 identity/span requirements.
- Sibling repos: none identified.
- External libraries: spaCy/Stanza provide annotations, not the LCATS artifact
  contract or validation/provenance rules.
- Recommendation: version the LCATS schema; do not replace the NLP backend.

### Demand search

- Work items: resolved linguistics items delivered the v1 substrate and
  experiment runners; none requests v2.
- Proposals: the governing proposal identifies v2 as the required rich source.
- Backlog: no matching open entry.
- Recommendation: proceed without reopening `WS-LINGUISTICS`.

## Scope

- Versioned v2 schema and serializer.
- Sentence/token/source identity, capability metadata, and model provenance.
- Strict per-token and cross-artifact validation.
- Runner/CLI output option, compatibility, resume/stale handling, docs/tests.

## Required Changes

1. Define v2 with story/source fingerprint, backend capability map, exact
   library/model/version/config provenance, and nested sentence records.
2. Store sentence index/start/end and token index/global index/start/end/text/
   lemma/UPOS/XPOS/features/head/dependency relation.
3. Extend backends only as needed to provide normalized spans/indices while
   retaining a backend-neutral serializer and explicit unavailable fields.
4. Validate identity, indices, spans, source text, UPOS vocabulary,
   sentence-local heads, roots, and reconciliation with compact counts.
5. Add an explicit v2 output selection to common runner/CLI code, including
   output-root, resume, existing-output, and stale-source behavior.
6. Document v1/v2 compatibility, capabilities, provenance, and storage cost.

## Non-Goals

- Do not mutate or reinterpret token-detail-v1 files.
- Do not enable rich token output by default.
- Do not add NER, coreference, sentiment, or embedding fields.
- Do not run the 146-story or full-corpus experiments in this item.
- Do not promote generated artifacts into `corpora/`.

## Acceptance Criteria

- Round-trip fixtures preserve all v2 fields and validate strictly.
- Invalid spans, heads, indices, tags, identities, and compact counts are
  rejected with actionable errors.
- Literary smoke fixtures cover Unicode, dialogue, contractions, archaic text,
  ambiguous noun/verb forms, and proper names.
- V1 and compact tests pass unmodified, proving backward compatibility.
- Documentation gives an exact schema and provenance example.

## Validation

- `scripts/version tools`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`
- `lcats linguistics --help`

## Risk Notes

- Token/source offsets can differ across backend normalization; require exact
  declared offset semantics and representative Unicode tests.
- Sentence-relative heads become corrupt if tokens are flattened; preserve
  sentence nesting in the source artifact.
- Model drift changes POS output; fingerprint the exact model and pipeline.
