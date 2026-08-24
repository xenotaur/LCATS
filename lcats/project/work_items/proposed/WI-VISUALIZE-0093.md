---
resolution: null
blocked_reason: null
blocked: false
id: WI-VISUALIZE-0093
title: Integrate POS-aware comparison and produce noun figures
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
depends_on:
  - WI-VISUALIZE-0092
  - WI-LINGUISTICS-0006
  - WI-LINGUISTICS-0007
blocked_by: []
expected_actions:
  - create_file
  - edit_file
  - run_tests
  - create_report
  - write_docs
forbidden_actions:
  - force_push
  - delete_branch
  - silently_include_propn
  - bypass_pos_quality_gate
  - run_full_corpus
  - promote_sidecars
acceptance:
  - Comparison analysis can consume linguistics-lexicon-v1 and filter by explicit UPOS sets while selecting surface or lemma terms
  - Named common-noun, proper-noun, and combined noun-family presets have documented non-overlapping semantics, and manifests record the exact selected tags
  - Stopword, include/exclude, min-document-frequency, top-N, vocabulary-source, and ordering policies work consistently with POS filters
  - At least one 146-story science-fiction comparison and complement variant is produced for NOUN and reviewed against authoritative CSV values
  - POS-dependent runs reject missing, stale, mismatched, or pilot-gate-failing lexical data with actionable errors; tests and docs pass
required_evidence:
  - test_output
  - validation_output
  - lrh_validate
  - manual_review
artifacts_expected:
  - src/lcats/visualize/comparison.py
  - src/lcats/visualize/cli.py
  - tests/visualize_tests/
  - experiments/08_visualize_dogfood/
  - docs/how-to/run-visualize.md
---

# Work Item: WI-VISUALIZE-0093

## Summary

Connect validated lexical artifacts to the comparison pipeline, expose explicit
UPOS and lemma/surface controls, and produce the first audited noun comparison
figures over the 146-story sample.

## Problem / Context

The chart system can ship before rich linguistics, but noun figures require a
trusted link between story selection and versioned lexical counts. The term
“noun” is itself ambiguous unless common nouns (`NOUN`) and proper nouns
(`PROPN`) are distinguished. This item integrates only after the pilot meets or
explicitly resolves its quality gate.

### Duplication search

- In-repo: current word visualization tokenizes raw text and has no lexical
  artifact or POS filter adapter.
- Sibling repos: none identified.
- External libraries: POS tagging is already supplied upstream; this item is
  LCATS-specific query and provenance integration.
- Recommendation: extend comparison analysis and CLI.

### Demand search

- Work items: resolved `WI-VISUALIZE-0085` explicitly deferred POS and lemma
  filtering.
- Proposals: the governing proposal makes the noun figures a target outcome.
- Backlog: no open duplicate.
- Recommendation: satisfy the deferred demand here.

## Scope

- Lexical-artifact loader and identity/quality validation.
- Surface/lemma and explicit UPOS filtering in comparison specs.
- Named noun presets with transparent semantics.
- Sample science-fiction/reference and complement noun figures plus evidence.

## Required Changes

1. Load and join lexical artifacts to selected stories using stable identities
   and source fingerprints; fail on missing, mixed-version, or stale inputs.
2. Add surface/lemma selection and explicit UPOS-set filters to the comparison
   analysis and CLI without changing raw-text defaults.
3. Define named `common_nouns` (`NOUN`), `proper_nouns` (`PROPN`), and
   `noun_family` (`NOUN`,`PROPN`) presets; record expanded tags in manifests.
4. Apply stopword/include/exclude/vocabulary/order policies after fact loading
   and document interactions with lemma and POS filters.
5. Generate and review sample-universe science-fiction versus all-146 and
   science-fiction versus complement noun charts, CSVs, and manifests in the
   visualization dogfood area or a clearly linked successor.
6. Add unit, integration, stale-input, missing-input, and gate-failure tests.

## Non-Goals

- Do not run rich NLP within a visualization command.
- Do not silently treat `PROPN` as `NOUN`.
- Do not bypass or rewrite the pilot quality decision.
- Do not require or run the full corpus.
- Do not promote linguistic artifacts into `corpora/`.

## Acceptance Criteria

- Every POS figure discloses tag set, term form, stopword policy, universe, and
  selectors.
- CSV totals reconcile with source lexical artifacts for the selected stories.
- `NOUN`, `PROPN`, and combined results are independently testable.
- Missing/stale/mixed provenance fails before analysis or output creation.
- The committed sample figures are numerically and visually reviewed.

## Validation

- `scripts/version tools`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`
- `lcats visualize compare --universe manifest --manifest ../experiments/05_metadata_genre_prefilter/results/full_scan/genre_balanced_manifest.jsonl --right-genre science_fiction --pos NOUN --term-form lemma --right-reference complement --output-dir /tmp/lcats_noun_compare`

## Risk Notes

- Proper names can dominate literary genre comparisons; keep `PROPN` explicit.
- Lemma/POS provenance must not be mixed across models or schema versions.
- Some terms are genuinely ambiguous across contexts; count token annotations,
  not a manually assigned word-type POS.
