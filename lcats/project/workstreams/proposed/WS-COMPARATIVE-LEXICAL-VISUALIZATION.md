---
id: WS-COMPARATIVE-LEXICAL-VISUALIZATION
kind: planning_node
title: Comparative Lexical Visualization
status: proposed
stage: planned
origin: design_review
summary: Deliver aligned mirrored, reference-overlay, and multi-subset lexical charts, rich token annotations, a queryable lexical index, a 146-story POS pilot, and gated paper figures.
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap:
  - ROADMAP-CORE
related_design:
  - project/design/proposals/proposed/comparative-lexical-visualization/00_proposal.md
  - project/design/proposals/adopted/corpus-text-visualization/00_proposal.md
  - project/workstreams/resolved/WS-CORPUS-TEXT-VISUALIZATION.md
  - project/workstreams/resolved/WS-LINGUISTICS.md
work_items:
  - WI-VISUALIZE-0091
  - WI-VISUALIZE-0092
  - WI-LINGUISTICS-0005
  - WI-LINGUISTICS-0006
  - WI-LINGUISTICS-0007
  - WI-VISUALIZE-0093
  - WI-LINGUISTICS-0008
  - WI-VISUALIZE-0095
  - WI-VISUALIZE-0094
exit_criteria:
  - A versioned comparison specification and selector engine produce deterministic aligned comparison tables with explicit universe, membership, metric, denominator, vocabulary, order, and provenance semantics
  - Mirrored-pair and commensurate reference-overlay figures are available through reusable Python APIs and a thin CLI without changing existing visualize defaults
  - Ordered multi-subset and universe-relative complement figures share a declared vocabulary, term order, metric semantics, and visible scale, with selector overlap recorded
  - Token-detail-v2 and linguistics-lexicon-v1 are implemented, documented, validated, and backward compatible with existing compact and v1 artifacts
  - A new 146-story experiment reports rich-data validation, POS audit quality, runtime, storage, and a full-corpus go/no-go recommendation without writing generated sidecars into corpora/
  - If the pilot authorizes sample POS figures, POS-aware noun comparisons are produced with adjacent CSV and manifest evidence; otherwise the POS integration item and figure package record an evidence-backed defer/no-go outcome without using rejected data
  - The conditional full-corpus item records either a validated rich-data run or an explicit evidence-backed no-go/defer decision
  - All listed work items are resolved and lrh validate reports 0 errors introduced by the workstream
---

# Workstream: Comparative Lexical Visualization

## Purpose

This workstream coordinates the next paper-oriented extension of LCATS text
visualization and linguistic data. It delivers immediately useful two-series
count and TF-IDF charts while separately building and validating the rich-token
and lexical-index substrate needed for defensible noun/POS figures.

The work belongs in a new stream because both predecessor workstreams are
resolved. Their implementations are reusable foundations, but neither governs
the new comparison contract, schema evolution, pilot quality gate, or final
figure production.

## Scope

- Define explicit universe, selector, complement, membership, metric,
  denominator, vocabulary, ordering, and preprocessing semantics.
- Add mirrored-pair and gray-reference overlay charts through reusable analysis
  and rendering APIs plus a thin `lcats visualize compare` command.
- Add aligned small-multiple figures for ordered subsets or their complements,
  with common vocabulary/order/scale and explicit overlap provenance.
- Introduce backward-compatible rich-token-v2 and derived lexical-v1 artifacts
  with strict validation and reproducible provenance.
- Run a 146-story pilot with human POS audit and measured performance/storage.
- Integrate UPOS filters and, when the pilot authorizes them, produce noun-aware
  comparison charts; otherwise close the dependent work with explicit
  evidence-backed defer/no-go records.
- Make the full-corpus rich run conditional on pilot gates and package final
  reproducible paper/presentation figures.

## Prior Art Check

### Duplication search

- In-repo: reuse and extend `src/lcats/visualize/`,
  `src/lcats/analysis/linguistics/`, experiment 05's sample, experiments 06/07's
  runners, and experiment 08's dogfooding convention. No existing active or
  resolved workstream contains this complete delivery sequence.
- Sibling repos: none identified.
- External libraries: Matplotlib, scikit-learn, spaCy, and Stanza supply core
  algorithms but not LCATS selection, schema, manifest, audit, or experiment
  semantics.
- Recommendation: proceed as an LCATS extension; do not replace the existing
  visualization or linguistic subsystems.

### Demand search

- Work items: resolved `WI-VISUALIZE-0085` deferred POS/lemmatization and
  resolved `WI-VISUALIZE-0090` deferred generalized comparison/chart work.
- Proposals: the adopted corpus-text-visualization proposal records the same
  deferred POS question and mandates reusable, reproducible figure generation.
- Backlog: no matching open entry defines the new workstream as a whole.
- Recommendation: link this workstream to those resolved sources of demand; no
  open item should be auto-closed.

## Work Items

- **WI-VISUALIZE-0091 — Comparison specification and selector engine.** Define
  the reusable comparison model, selector algebra, metrics, vocabulary/order
  rules, aligned data table, and manifest contract.
- **WI-VISUALIZE-0092 — Mirrored and reference-overlay renderer.** Implement
  both chart variants and expose them through `lcats visualize compare`.
- **WI-LINGUISTICS-0005 — Rich token-detail-v2.** Add sentence/token identity,
  source offsets, capability/model provenance, strict validation, and v1
  compatibility.
- **WI-LINGUISTICS-0006 — Derived lexical artifact.** Materialize deterministic
  surface/lemma/UPOS counts and denominators from v2 token details.
- **WI-LINGUISTICS-0007 — 146-story rich linguistic pilot.** Run the balanced
  sample, audit noun-family POS quality, and measure runtime/storage.
- **WI-VISUALIZE-0093 — POS-aware comparison and noun figures.** On a pilot go
  result, integrate lexical artifacts and produce reviewed noun charts; on
  defer/no-go, record the decision and required remediation without figures.
- **WI-LINGUISTICS-0008 — Conditional full-corpus rich run.** Apply the pilot
  gates and either run/validate the full corpus or record a no-go/defer result.
- **WI-VISUALIZE-0095 — Aligned multi-subset comparison figures.** Compose
  ordered panels such as `S1`, `S2`, `S3` or their universe-relative
  complements with shared vocabulary, ordering, scale, and provenance.
- **WI-VISUALIZE-0094 — Paper figure package and dogfooding.** Produce the final
  count, frequency, TF-IDF, complement, overlay, and stopword variants plus
  pilot-authorized noun variants, all with reproducibility evidence.

## Dependencies / Delivery Order

`WI-VISUALIZE-0091` and `WI-LINGUISTICS-0005` may start in parallel.
`WI-VISUALIZE-0092` follows 0091; `WI-LINGUISTICS-0006` follows 0005; the
sample pilot follows both linguistics items. POS integration follows the
renderer, lexical artifact, and resolved pilot: it implements authorized
figures after a go result or records an evidence-backed defer/no-go resolution.
The conditional full-corpus decision follows the pilot but does not block the
paper package. The multi-subset figure follows the comparison engine and
two-series renderer. Final dogfooding follows the renderer, resolution of POS
integration, and the multi-panel composer.

## Exit Criteria

- Comparison tables and manifests reproduce selections, denominators,
  vocabulary, order, values, and displayed differences deterministically.
- The mirrored and overlay charts pass analysis/rendering/CLI tests and include
  color-independent encodings for reference, overlap, excess, and deficit.
- Multi-subset figures preserve one declared universe, aligned vocabulary and
  order, common metric semantics, and a common visible scale by default; their
  manifests report selector sizes and pairwise overlaps.
- Rich token and lexical artifacts pass schema, identity, span, dependency,
  count-reconciliation, and deterministic-regeneration validation.
- The 146-story pilot includes preregistered human audit results and a clear
  quality/performance/storage recommendation.
- On a pilot go result, noun figures state whether `NOUN`, `PROPN`, or both were
  selected and ship with adjacent CSV/manifest evidence; on defer/no-go, the
  downstream items resolve with linked decision evidence and no noun outputs
  from rejected data.
- The full-corpus item resolves with either successful validated evidence or a
  documented, reviewable no-go/defer outcome.
- All nine items are resolved without modifying existing command defaults or
  promoting generated linguistic sidecars into `corpora/` implicitly.

## Non-Goals

- Does not reopen resolved workstreams.
- Does not overwrite experiments 06, 07, or 08.
- Does not require a full-corpus rich run before producing sample noun figures.
- Does not add NER, coreference, sentiment, embeddings, or LLM annotations.
- Does not treat visual difference or TF-IDF contrast as statistical
  significance.
- Does not change existing `words` or `tfidf` default behavior.

## Relationship to Design

- Governing proposal:
  `project/design/proposals/proposed/comparative-lexical-visualization/00_proposal.md`
- Visualization foundation:
  `project/design/proposals/adopted/corpus-text-visualization/00_proposal.md`
- Closed predecessor streams: `WS-CORPUS-TEXT-VISUALIZATION` and
  `WS-LINGUISTICS`

## Open Questions

- Whether the named “nouns” preset includes `PROPN` by default.
- The exact severe genre-slice failure threshold for the POS audit.
- Whether pilot evidence justifies checking in, archiving, or externally
  storing full token-detail outputs.
