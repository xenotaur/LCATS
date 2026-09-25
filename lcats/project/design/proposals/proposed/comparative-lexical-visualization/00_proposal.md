---
id: PROP-LCATS-COMPARATIVE-LEXICAL-VISUALIZATION
type: design_proposal
title: Comparative Lexical Visualization and Rich Linguistic Annotations
status: proposed
created_on: 2026-08-23
updated_on: 2026-08-24
implementation_status: not_started
implemented_by:
  - WI-VISUALIZE-0091
  - WI-VISUALIZE-0092
  - WI-LINGUISTICS-0005
  - WI-LINGUISTICS-0006
  - WI-LINGUISTICS-0007
  - WI-VISUALIZE-0093
  - WI-LINGUISTICS-0008
  - WI-VISUALIZE-0095
  - WI-VISUALIZE-0094
supersedes: []
superseded_by: null
related_design:
  - project/design/proposals/adopted/corpus-text-visualization/00_proposal.md
  - project/workstreams/resolved/WS-CORPUS-TEXT-VISUALIZATION.md
  - project/workstreams/resolved/WS-LINGUISTICS.md
  - docs/reference/linguistics-sidecar.md
  - docs/how-to/run-visualize.md
---

## Summary

LCATS should add a reproducible comparative-lexical analysis pipeline that can
place two aligned term series in mirrored charts or overlay a target series on
a reference series to make excesses and deficits visible. The same pipeline
should consume a versioned rich-token annotation and derived lexical index so
surface forms, lemmas, stopword policies, and Universal POS classes such as
`NOUN` and `PROPN` are selectable without rerunning NLP for every figure.

## Background / Motivation

The adopted corpus-text-visualization proposal and resolved
`WS-CORPUS-TEXT-VISUALIZATION` delivered reusable visualization modules,
figure manifests, word frequencies, within-group TF-IDF salience, and a true
group-versus-complement TF-IDF contrast. The current renderer, however, accepts
one ranked mapping at a time, and the CLI selects either the full corpus or one
genre. It cannot yet express a declared comparison universe, two independently
selected groups, an optional group complement, aligned vocabulary, or the
mirrored/reference-overlay chart needed for the paper.

LCATS also already has more linguistic capability than the checked-in
experiment data exposes. `TokenRecord` in
`src/lcats/analysis/event_role_world/nlp_backend.py` normalizes lemma, UPOS,
XPOS, morphology, dependency head, and dependency relation across spaCy and
Stanza. `linguistics-token-detail-v1`, documented in
`docs/reference/linguistics-sidecar.md`, can serialize those fields when token
detail is requested. However, experiments 06 and 07 were run with
`include_token_detail: false`; experiment 07 currently rejects token-detail
runs; and v1 flattens sentence-relative dependency records without stable
sentence/token identities or source offsets. The practical gap is therefore
not the absence of a POS tagger, but the absence of durable rich annotations
and a compact, validated lexical view for the datasets used by the figures.

The paper can benefit immediately from count, normalized-frequency, document
frequency, and existing TF-IDF comparisons. POS-aware noun figures should
follow a bounded 146-story pilot so annotation quality, cost, runtime, and
storage are measured before any full-corpus regeneration.

## Prior Art Check

### Duplication search

- In-repo: extend `src/lcats/visualize/`, the existing linguistic runner and
  sidecar infrastructure, and experiments 05-08. The repository has a TF-IDF
  group-minus-complement metric and single-series charts, but no general
  comparison specification, aligned two-series renderer, reference-overlay
  chart, token-detail-v2 schema, or derived lexical index.
- Sibling repos: no sibling repository was identified for this LCATS-specific
  corpus/sidecar/figure workflow.
- External libraries: Matplotlib, scikit-learn, spaCy, and Stanza already
  provide the plotting, vectorization, and NLP primitives. None replaces the
  LCATS-specific selection semantics, provenance manifests, schemas, derived
  artifacts, or experiment workflow.
- Recommendation: proceed by extending the existing LCATS modules and reusing
  their current dependencies; do not build a parallel visualization or NLP
  stack.

### Demand search

- Work items: resolved `WI-VISUALIZE-0085` explicitly deferred
  lemmatization/POS filtering; resolved `WI-VISUALIZE-0090` supplied the first
  complement-aware TF-IDF primitive but intentionally did not extend it to
  word-frequency charts or a general comparison API.
- Proposals: the adopted corpus-text-visualization proposal asks whether
  lemmatization/POS filtering should be added and establishes the reusable
  analysis/rendering/CLI foundation this proposal extends.
- Backlog: no separate open backlog entry defines the complete comparison,
  rich-token, lexical-index, pilot, and paper-figure sequence.
- Recommendation: link the deferred demand and proceed under a new workstream;
  do not reopen the two resolved workstreams.

## Design Decisions

### Decision 1: One comparison specification governs analysis and rendering

Options considered:

- add chart-specific flags directly to the existing `words` and `tfidf`
  handlers;
- build one-off experiment scripts for the paper figures;
- define a reusable immutable comparison specification consumed by selection,
  analysis, rendering, and manifest code.

**Chosen: a reusable `ComparisonSpec`.** It declares the universe, left and
right selectors, membership semantics, metrics, denominators, term form,
filters, vocabulary policy, order controller, rendering style, and output
formats. Thin CLI orchestration will construct the specification and call pure
or mostly pure analysis functions. This preserves the architecture established
by `src/lcats/visualize/analysis.py`, `rendering.py`, and `cli.py` while keeping
paper-specific choices out of library internals.

### Decision 2: Complements are relative to an explicit universe

Options considered:

- silently interpret “complement” as every story LCATS can discover;
- infer the complement from whichever dataset a command happens to load;
- require a declared universe and define complement as `U - S`.

**Chosen: `complement(S) = U - S` for an explicit universe `U`.** Supported
universes initially include the checked-in corpus, a manifest such as the
146-story genre sample, and an explicit story list. Selectors include all,
genre, complement, manifest genre, story-list, and include/exclude story IDs.
Genre membership semantics (`candidate`, `primary`, or `selection`) are
explicit, and manifests record universe size, group sizes, intersection, and
overlap warnings. This prevents “science fiction versus the other 126 stories
in the balanced sample” from being confused with “science fiction versus the
rest of the approximately 1,800-story corpus.”

### Decision 3: Compare commensurate values in overlays

Options considered:

- allow any left/right measures to overlap visually;
- restrict the entire feature to identical measures;
- allow different measures in mirrored panels but require the same metric and
  denominator for a reference overlay.

**Chosen: the hybrid rule.** Mirrored panels may show different metrics and
use separately labelled axes. Reference overlays, overlap shading, and
excess/deficit encodings require commensurate values: the same metric,
normalization, denominator, term form, and token-filter policy. Incompatible
overlay specifications fail clearly rather than imply a false geometric
comparison.

Initial metric vocabulary:

- raw term count;
- occurrences per million included tokens;
- document count and document percentage;
- mean per-document relative frequency;
- mean TF-IDF, fit once over the declared universe;
- existing group-minus-complement mean TF-IDF contrast.

Independent TF-IDF fits for the two sides are disallowed in a direct overlay.
The fitted universe, tokenizer, vocabulary, IDF parameters, and package version
must be shared and disclosed.

### Decision 4: Align one vocabulary before ranking or rendering

Options considered:

- independently choose each side’s top terms and merge them in the renderer;
- display only the intersection of independently ranked lists;
- construct one candidate vocabulary and align both series before sorting.

**Chosen: one aligned vocabulary.** Vocabulary policies include all eligible
terms, top N by left, top N by right, top N by signed or absolute difference,
union/intersection, explicit include/exclude lists, and minimum document
frequency. Ordering may be controlled by left value, right value, signed
difference, absolute difference, alphabetical order, or an explicit term list.
Ties use a documented deterministic secondary order.

### Decision 5: Provide related two-series and multi-panel chart types

Options considered:

- only a conventional grouped bar chart;
- only a population-pyramid/mirrored chart;
- a mirrored pair plus a reference-overlay variant;
- aligned small multiples for comparing several subsets or their complements.

**Chosen: all three variants.** The mirrored pair places one aligned series left of
the zero line and the other right, with independent scales permitted when axes
are clearly labelled. The reference-overlay chart places the target on the
right over a gray reference bar, uses a narrower and/or hatched target mark,
and encodes signed excess or deficit beyond the overlap. Texture and labels
carry meaning independently of color. A configurable reference selector can be
the full universe or the target’s complement. The multi-panel variant composes
an ordered sequence such as `S1`, `S2`, `S3` or `U - S1`, `U - S2`, `U - S3`
against one aligned vocabulary and term order. It uses a common visible scale
by default, records pairwise selector overlap, and supports a shared or
per-panel reference/complement overlay without implying that overlapping genre
labels partition the universe.

### Decision 6: Treat preprocessing and POS selection as query policy

Options considered:

- bake stopword removal and noun selection into generated datasets;
- keep only surface-form counts and rerun NLP for every alternate query;
- retain rich token facts, derive a compact lexical index, and apply filters at
  query time.

**Chosen: query-time policy over versioned facts.** The comparison spec chooses
surface form or lemma, case policy, stopword policy, include/exclude lists, and
UPOS classes. Stopword list identity, version, and content hash are recorded.
“Nouns” is not an opaque switch: callers select `NOUN`, `PROPN`, or both, with
the paper default left open for review.

### Decision 7: Add token-detail-v2 and a separate lexical materialized view

Options considered:

- use flattened `linguistics-token-detail-v1` unchanged;
- enlarge compact `linguistics.json` with all token rows and lexical counts;
- introduce a backward-compatible v2 rich-token artifact plus a separate
  derived lexical artifact.

**Chosen: versioned rich source data plus a compact derived view.** Existing
v1 artifacts remain readable and unchanged. `linguistics-token-detail-v2`
nests tokens within sentences and records sentence index/span plus token index,
global token index, source character span, text, lemma, UPOS, XPOS, morphology,
sentence-relative head index, and dependency relation. Capability metadata
states which fields were required, optional, or unavailable for the backend.

Validation checks schema/version and source identity, monotonic unique indices,
in-bounds source-matching spans, valid sentence-local heads, recognized UPOS
values, agreement with compact counts, and deterministic lexical derivation.
The initial production backend is spaCy with exact library/model provenance;
the schema remains backend-neutral and a small Stanza comparison may be used
as audit evidence.

`linguistics.lexicon.json` (`linguistics-lexicon-v1`) stores the source-token
fingerprint, story identity, denominators, and counts keyed by surface form,
lemma, and UPOS. It is a regenerable materialized view, not a second source of
truth, and keeps compact `linguistics.json` from becoming a large token table.

### Decision 8: Pilot before a conditional full-corpus run

Options considered:

- regenerate rich data for the whole corpus immediately;
- limit rich data permanently to the 146-story sample;
- run and audit the balanced sample first, then gate a full-corpus run.

**Chosen: sample-first with an explicit full-run gate.** A new numbered
experiment uses the 146-story manifest from experiment 05, writes only into an
experiment-local mirror, produces v2 and lexical artifacts, measures runtime
and storage, and performs a stratified human POS audit across genres, authors,
dialogue, contractions, archaic prose, ambiguous noun/verb forms, and proper
names. The pilot reports `NOUN`, `PROPN`, and combined noun-family precision,
recall, confusion, and genre slices.

The proposed initial acceptance threshold is at least 0.90 precision and 0.90
recall for the combined noun family with no severe genre-specific failure. The
work item must preregister the exact sample and severe-failure rule before
scoring. A later conditional item either runs the full corpus when quality,
validation, performance, storage, and research-need gates pass, or records a
reviewable no-go/defer decision. Generated bulk-artifact retention is selected
from ordinary checked-in files, compressed release/archive storage, columnar
export, or manifests plus derived lexical artifacts based on pilot evidence.

The pilot records a separate sample-figure decision. A proceed result authorizes
POS integration and noun figures from the validated sample artifacts. A
defer/no-go result is also a valid completion path: the POS integration and
paper-package items record the decision and required remediation, omit noun
figures, and must not use rejected pilot data. This keeps the workstream
resolvable without weakening the quality gate.

## Output Contract

Each comparison run produces:

- `comparison.png` and `comparison.svg`, with PDF when requested and supported;
- `comparison.csv` containing term, left/right values, raw supporting counts,
  denominators, signed difference, absolute difference, and display order;
- `comparison_manifest.json` containing the full comparison specification,
  LCATS/input revisions, story membership counts and overlaps, NLP/model
  provenance where applicable, stopword identity, displayed vocabulary/order,
  package versions, warnings, and output hashes.

The tabular result is authoritative for numerical review; rendering consumes
that table. Tests should validate analysis tables and figure structure rather
than brittle pixel-perfect images.

## Non-Goals

- Does not reopen or rewrite the resolved corpus-visualization or linguistics
  workstreams; it extends their delivered substrates in a new workstream.
- Does not overwrite experiments 06 or 07; new collection runs use new
  numbered experiment directories.
- Does not make rich token annotations a mandatory part of every normal
  `lcats linguistics` run.
- Does not promote generated sidecars into `corpora/` without a separate,
  explicit promotion decision.
- Does not add named-entity recognition, coreference, sentiment, embeddings,
  or new LLM-generated annotations to the initial rich-token contract.
- Does not claim that TF-IDF difference or visual excess/deficit is a
  statistical significance test.
- Does not require the conditional full-corpus run before sample-based noun
  figures can be produced.
- Does not change existing `lcats visualize words` or `tfidf` defaults.

## Implementation Plan

The governing workstream is
`project/workstreams/proposed/WS-COMPARATIVE-LEXICAL-VISUALIZATION.md`.
Delivery is split into nine reviewable items:

1. `WI-VISUALIZE-0091` defines `ComparisonSpec`, selector algebra, aligned
   vocabulary, metrics, tabular output, and provenance.
2. `WI-VISUALIZE-0092` adds mirrored/reference-overlay rendering and the thin
   `lcats visualize compare` CLI, unblocking immediate count/TF-IDF figures.
3. `WI-LINGUISTICS-0005` specifies and implements token-detail-v2.
4. `WI-LINGUISTICS-0006` adds the deterministic derived lexical artifact.
5. `WI-LINGUISTICS-0007` runs and audits the new 146-story rich-data pilot.
6. `WI-VISUALIZE-0093` integrates lexical/POS filtering and produces the noun
   comparison figures after a pilot go result, or records an evidence-backed
   defer/no-go resolution without producing them.
7. `WI-LINGUISTICS-0008` evaluates the gates and conditionally runs rich
   extraction over the full corpus.
8. `WI-VISUALIZE-0095` composes aligned small-multiple figures for several
   subsets or their universe-relative complements.
9. `WI-VISUALIZE-0094` dogfoods the supported variants and produces the final
   paper/presentation figure package.

Items 1 and 3 may proceed in parallel. Item 2 depends on item 1; item 4 depends
on item 3; item 5 depends on items 3 and 4; item 6 depends on items 2, 4, and 5.
The conditional full run depends on the pilot but does not block the paper
package. Sample-based noun figures are conditional on the pilot's separate
POS-figure gate. The multi-panel composer depends on the comparison engine and
two-series renderer. Final figure dogfooding depends on the renderer, resolution
of POS integration, and the multi-panel composer.

## Cross-References

- Existing visualization design:
  `project/design/proposals/adopted/corpus-text-visualization/00_proposal.md`
- Existing visualization workstream:
  `project/workstreams/resolved/WS-CORPUS-TEXT-VISUALIZATION.md`
- Existing linguistic workstream:
  `project/workstreams/resolved/WS-LINGUISTICS.md`
- Linguistic schema reference: `docs/reference/linguistics-sidecar.md`
- Visualization usage and genre-membership semantics:
  `docs/how-to/run-visualize.md`
- Existing figure dogfooding: `../experiments/08_visualize_dogfood/`

## Open Questions

- Should the paper-facing “nouns” preset include `PROPN` by default, or expose
  common nouns and proper nouns as separate named presets?
- Is the proposed combined noun-family 0.90 precision/recall gate sufficient,
  and what exact genre-slice threshold constitutes a severe failure?
- Should mean per-document relative frequency ship in the first metric tranche
  or follow after raw count, per-million frequency, document frequency, and
  existing TF-IDF metrics?
- Should the pilot include a small spaCy-versus-Stanza comparison, or use
  Stanza only if the spaCy human audit misses its gate?
- Which retention policy should govern full token-detail artifacts after the
  pilot measures actual repository and archive costs?
