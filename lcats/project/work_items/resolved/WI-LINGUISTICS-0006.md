---
resolution: "Implemented deterministic linguistics-lexicon-v1 artifacts in PR #392 (commit fb0916910df9b0881f31603f96f07ac51e544be0)."
blocked_reason: null
blocked: false
id: WI-LINGUISTICS-0006
title: Materialize deterministic lexical artifacts from rich tokens
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
  - WS-COMPARATIVE-LEXICAL-VISUALIZATION
related_design:
  - project/design/proposals/proposed/comparative-lexical-visualization/00_proposal.md
depends_on:
  - WI-LINGUISTICS-0005
blocked_by: []
expected_actions:
  - create_file
  - edit_file
  - run_tests
  - write_docs
forbidden_actions:
  - force_push
  - delete_branch
  - treat_derived_artifact_as_source_of_truth
  - embed_stopword_policy
  - run_full_corpus
  - promote_sidecars
acceptance:
  - linguistics-lexicon-v1 deterministically records story identity, source token-detail fingerprint, derivation version, denominators, and surface/lemma/UPOS counts
  - Regenerating from identical v2 input produces byte-stable semantic content, and validation proves all lexical counts reconcile with source tokens
  - Stopword, include/exclude, and noun-family choices remain query-time policies rather than destructive generation-time filtering
  - Runner and CLI support produce the lexical artifact atomically with correct resume and stale-source behavior
  - Tests, schema documentation, and a performance microbenchmark demonstrate that comparison queries need not scan full token rows repeatedly
required_evidence:
  - test_output
  - validation_output
  - lrh_validate
  - manual_review
artifacts_expected:
  - src/lcats/analysis/linguistics/lexicon.py
  - src/lcats/analysis/linguistics/runner.py
  - tests/linguistics_tests/
  - docs/reference/linguistics-lexicon.md
---

# Work Item: WI-LINGUISTICS-0006

## Summary

Add `linguistics-lexicon-v1`, a compact deterministic materialized view of
surface-form, lemma, and UPOS counts derived from token-detail-v2.

## Problem / Context

Rich token rows are the audit source but are unnecessarily expensive for every
frequency or POS query. Adding aggregate lexical data to compact
`linguistics.json` would bloat its stable contract and mix independently
regenerable data with core features. A separate fingerprinted lexical artifact
provides fast queries while keeping v2 authoritative.

### Duplication search

- In-repo: current word-frequency code recomputes simple token counts from raw
  text; no surface/lemma/UPOS lexical materialized view exists.
- Sibling repos: none identified.
- External libraries: counters and columnar formats are primitives, not an
  LCATS derivation/identity contract.
- Recommendation: implement a small deterministic LCATS artifact.

### Demand search

- Work items: no open match; `WI-LINGUISTICS-0005` supplies the source schema.
- Proposals: explicitly required by the governing proposal.
- Backlog: no matching entry.
- Recommendation: proceed after v2.

## Scope

- Lexical schema, builder, validator, serializer, and provenance.
- Surface/lemma/UPOS count keys and useful denominators.
- Atomic runner output, resume/stale logic, docs, tests, and benchmark.

## Required Changes

1. Define `linguistics-lexicon-v1` with story/source identities, v2 content
   fingerprint, derivation version, token denominators, and sorted count rows
   keyed by `(surface, lemma, upos)`.
2. Implement a pure v2-to-lexicon derivation function and deterministic
   serialization independent of stopword or chart policy.
3. Validate fingerprint linkage, uniqueness, non-negative counts, denominator
   reconciliation, and exact regeneration from available source v2.
4. Add opt-in runner/CLI production with atomic writes and correct handling of
   missing, stale, skip, overwrite, and redirected outputs.
5. Document consumption and measure representative build/query size and time.

## Non-Goals

- Do not make the lexical artifact an independently editable source of truth.
- Do not bake a stopword list, noun preset, top-N cutoff, or genre into it.
- Do not replace full v2 evidence with aggregates.
- Do not run sample or corpus experiments.

## Acceptance Criteria

- The artifact regenerates deterministically and validates against v2.
- Counts can reproduce raw surface, lemma, `NOUN`, and `PROPN` totals exactly.
- Changing source v2 invalidates stale lexicon output.
- Query benchmarks demonstrate a useful reduction in repeated token scanning.
- Documentation distinguishes facts stored at generation time from policies
  applied at comparison time.

## Validation

- `scripts/version tools`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`

## Risk Notes

- A poorly chosen key can inflate JSON; measure before committing bulk output.
- Lemma casing/empty values need explicit normalization without fabricating
  unavailable data.
- Fingerprint and version checks must prevent stale aggregates from appearing
  current.
