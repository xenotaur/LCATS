---
id: WS-CORPUS-TEXT-VISUALIZATION
kind: planning_node
title: Corpus and Document Text Visualization for LCATS
status: proposed
stage: planned
origin: design_review
summary: Deliver PROP-LCATS-CORPUS-TEXT-VISUALIZATION through a reusable `lcats visualize` CLI family (genres, words, tfidf, topics) built on the existing Story/Corpora representation and lcats.analysis.graph_plotters renderer, producing reproducible publication-ready figures for the Worldcon 2026 paper.
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap: []
related_design:
  - lcats/project/design/proposals/adopted/corpus-text-visualization/00_proposal.md
  - lcats/project/design/proposals/proposed/genre-evidence-sidecars/00_proposal.md
work_items:
  - WI-VISUALIZE-0073
  - WI-VISUALIZE-0085
  - WI-VISUALIZE-0086
  - WI-VISUALIZE-0087
  - WI-VISUALIZE-0088
  - WI-VISUALIZE-0089
exit_criteria:
  - lcats visualize genres produces genre-distribution figures (word cloud + conventional chart, PNG and vector) from a named, reproducible genre source (genre.json sidecars / whatever artifact PROP-GENRE-EVIDENCE-SIDECARS or the genre-census tooling actually produces), reusing lcats.analysis.graph_plotters for conventional charts, and any figure built from a sample rather than a full-corpus source explicitly discloses population, sample size/mode, and denominator rather than presenting the sample as the whole corpus
  - lcats visualize words produces word-frequency visualizations for the whole corpus and selected genre subsets, with explicit documented preprocessing defaults
  - lcats visualize tfidf produces TF-IDF comparison visualizations using story as the default document unit and genre (or another corpus selector) as the explicit comparison group
  - lcats visualize topics produces a topic-model baseline visualization
  - every command intended for paper use emits an input-revision/content-identity value alongside its output, not just selectors/parameters/seed
  - wordcloud and scikit-learn are added as core LCATS dependencies alongside the already-core matplotlib, with no parallel rendering API duplicating lcats.analysis.graph_plotters
  - the visualize command family is dogfooded to produce real figures used in the Worldcon 2026 paper
  - usage documentation/examples exist for lcats visualize
  - All work items resolved and lrh validate reports 0 errors
---

# Workstream: Corpus and Document Text Visualization for LCATS

## Purpose

This workstream coordinates implementation of `PROP-LCATS-CORPUS-TEXT-VISUALIZATION`: a reusable `lcats visualize` CLI family and underlying Python analysis/rendering layer for turning LCATS corpus metadata and story text into reproducible, publication-useful figures, driven by the concrete figure needs of the Worldcon 2026 paper.

## Scope

- Build the shared source-adapter / analysis / rendering / CLI-orchestration substrate described in the proposal's Architecture Sketch, reusing `lcats.stories.Story`/`Corpora` and `lcats.analysis.graph_plotters` rather than introducing parallel abstractions.
- Implement `lcats visualize genres`, sourcing genre data through whatever artifact `PROP-GENRE-EVIDENCE-SIDECARS` (or the existing `experiments/04_genre_census` census tooling) actually produces — not an assumption that genre already lives in `Story.metadata`.
- Implement `lcats visualize words` (word-frequency clouds and conventional frequency plots) and `lcats visualize tfidf` (TF-IDF comparison, story as document unit).
- Implement `lcats visualize topics` as a topic-model baseline.
- Add `wordcloud` and scikit-learn as core dependencies; wire up PNG and vector (SVG/PDF) output per command, noting `wordcloud`'s PNG-first layout may leave vector output to the `matplotlib`-rendered companion charts for word-cloud figures specifically.
- Wire up the input-revision/content-identity reproducibility requirement across all paper-use commands.
- Dogfood the full command family against the Worldcon 2026 paper's actual figures.
- Write usage documentation and examples.

## Prior Art Check

### Duplication search
- In-repo: no existing `lcats visualize` command or equivalent plotting CLI exists (`grep -rl "visualiz" lcats/src/ ...` — this repo's package lives under `lcats/src/`, not a top-level `src/` — returns no runtime hits outside this proposal and its own design doc). `lcats.analysis.graph_plotters` already exists as a Matplotlib/Seaborn plotting module and must be reused, not duplicated, for conventional-chart rendering.
- Sibling repos: none identified.
- External libraries: `matplotlib` (already core), `wordcloud`, and scikit-learn are the established libraries for this scope per the proposal; no alternative was identified as clearly preferable.
- Recommendation: Proceed.

### Demand search
- Work items: none found requesting this capability outside this workstream's own scope.
- Proposals: `PROP-LCATS-CORPUS-TEXT-VISUALIZATION` itself is the originating request; `PROP-GENRE-EVIDENCE-SIDECARS` is the upstream dependency for the `genres` command's actual data source, not a competing request.
- Backlog: no matching entries found.
- Recommendation: No action.

## Proposed Work Items

1. `WI-VISUALIZE-0073` — Paper-critical visualization substrate and `genres` command (source adapters over `Story`/`Corpora`, analysis/rendering split reusing `graph_plotters`, genre source named and wired to its real artifact, input-revision reproducibility).
2. `WI-VISUALIZE-0085` — Text selection/preprocessing and `words` command.
3. `WI-VISUALIZE-0086` — TF-IDF analysis and comparison visualization.
4. `WI-VISUALIZE-0087` — Topic baseline.
5. `WI-VISUALIZE-0088` — Dogfood against the LCATS corpus and paper figures (blocked by items 3-4).
6. `WI-VISUALIZE-0089` — Documentation and examples (blocked by items 3-4).

## Non-Goals

- This workstream does not build a general-purpose digital-humanities platform.
- It does not replace notebooks as an exploratory research environment.
- It does not commit generated figures as authoritative corpus data by default.
- It does not solve semantic topic modeling comprehensively — `topics` is a baseline only.
- It does not add external (non-LCATS) document-format adapters (`.docx`, `.txt`, Markdown, generic JSON) — that is explicitly a separate follow-on workstream per the proposal's Future Scope.
- It does not implement `PROP-GENRE-EVIDENCE-SIDECARS` itself — that proposal's own governing workstream (`WS-GENRE-EVIDENCE-SIDECARS`) owns the sidecar schema/tooling; this workstream only consumes whatever artifact it produces.

## Open Questions

- Should `visualize genres` consume live corpus metadata directly, a saved assessment/census artifact, or both? (Proposed default: live corpus API first; saved-artifact support deferred until a concrete need appears.)
- Which preprocessing defaults are scientifically defensible for literary text? (Proposed default: standard stopword removal, case folding, and tokenization; document choices in the implementing work item.)
- Should lemmatization/POS filtering be part of the initial `words` command or deferred? (Proposed default: defer.)
- Should every figure produce an adjacent data/manifest sidecar, or is the simpler logged input-revision value sufficient for the first tranche? (Proposed default: log the value now; defer the richer manifest format until after dogfooding.)
- Should arbitrary external files ever enter through `lcats visualize` directly, or always through a separate ingestion/document adapter API? (Out of scope for this workstream either way.)
