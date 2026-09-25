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
  - If the pilot authorizes sample POS figures, at least one 146-story science-fiction comparison and complement variant is produced for NOUN and reviewed against authoritative CSV values
  - If the pilot defers or rejects sample POS figures, the item resolves with an evidence-backed decision, required remediation, and no figures produced from rejected data
  - POS-dependent runs reject missing, stale, mismatched, or pilot-gate-failing lexical data with actionable errors; tests and docs pass on either pilot outcome
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
UPOS and lemma/surface controls, and, when authorized by the pilot, produce the
first audited noun comparison figures over the 146-story sample.

## Problem / Context

The chart system can ship before rich linguistics, but noun figures require a
trusted link between story selection and versioned lexical counts. The term
“noun” is itself ambiguous unless common nouns (`NOUN`) and proper nouns
(`PROPN`) are distinguished. This item starts only after the pilot explicitly
resolves its quality gate. A proceed result authorizes integration and figures;
a defer/no-go result authorizes a documented resolution without noun figures.

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
- On a proceed result, sample science-fiction/reference and complement noun
  figures plus evidence.
- On a defer/no-go result, a reviewable decision and remediation path without
  using rejected pilot data.

## Required Changes

1. Load and join lexical artifacts to selected stories using stable identities
   and source fingerprints; fail on missing, mixed-version, or stale inputs.
2. Add surface/lemma selection and explicit UPOS-set filters to the comparison
   analysis and CLI without changing raw-text defaults.
3. Define named `common_nouns` (`NOUN`), `proper_nouns` (`PROPN`), and
   `noun_family` (`NOUN`,`PROPN`) presets; record expanded tags in manifests.
4. Apply stopword/include/exclude/vocabulary/order policies after fact loading
   and document interactions with lemma and POS filters.
5. If the pilot authorizes figures, generate and review sample-universe science
   fiction versus all-146 and science fiction versus complement noun charts,
   CSVs, and manifests in the visualization dogfood area or a clearly linked
   successor.
6. If the pilot defers or rejects figures, record the evidence-backed outcome,
   required remediation, and explicit absence of noun outputs; do not use the
   rejected artifacts to satisfy figure acceptance.
7. Add unit, integration, stale-input, missing-input, and gate-failure tests.

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
- On a proceed result, the committed sample figures are numerically and
  visually reviewed; on defer/no-go, the decision artifact documents why no
  noun figure was produced and what would be required to reopen the work.

## Validation

- `scripts/version tools`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`
- On a proceed result: `lcats visualize compare --universe manifest --manifest ../experiments/05_metadata_genre_prefilter/results/full_scan/genre_balanced_manifest.jsonl --right-genre "science fiction" --pos NOUN --term-form lemma --right-reference complement --output-dir /tmp/lcats_noun_compare`
- On defer/no-go: verify the decision artifact and the absence of noun outputs
  derived from pilot-gate-failing data.

## Risk Notes

- Proper names can dominate literary genre comparisons; keep `PROPN` explicit.
- Lemma/POS provenance must not be mixed across models or schema versions.
- Some terms are genuinely ambiguous across contexts; count token annotations,
  not a manually assigned word-type POS.
