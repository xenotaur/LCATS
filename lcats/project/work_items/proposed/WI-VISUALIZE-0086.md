---
resolution: null
blocked_reason: null
blocked: false
id: WI-VISUALIZE-0086
title: TF-IDF comparison visualization: lcats visualize tfidf
type: deliverable
status: proposed
owner: unassigned
contributors: []
assigned_agents: []
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap: []
related_workstreams:
  - WS-CORPUS-TEXT-VISUALIZATION
related_design:
  - project/design/proposals/adopted/corpus-text-visualization/00_proposal.md
  - lcats/src/lcats/stories.py
  - lcats/src/lcats/visualize/
depends_on:
  - WI-VISUALIZE-0073
  - WI-VISUALIZE-0085
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
  - implement_new_architecture
  - promote_sidecars
  - modify_lcats_annotate
  - modify_lcats_promote
acceptance:
  - "`lcats visualize tfidf` is registered under `lcats visualize`, reusing the existing `lcats.visualize` package split (sources/analysis/rendering/cli) and CLI convention established by `WI-VISUALIZE-0073`/`WI-VISUALIZE-0085`"
  - "The unit of a 'document' for IDF is *story* by default, matching the proposal's Paper-Critical Scope item 4 (`story as the default document unit`); the comparison group (the corpus subset(s) whose distinguishing terms are computed) defaults to genre but is an explicit, named selector -- not silently hardcoded to genre alone. Genre-subset membership sources from `experiments/05_metadata_genre_prefilter/results/full_scan/candidates.jsonl`'s `metadata_assessment.result.target_candidates`, joined on `story_id` derived from `discovery.iter_collection_story_files`'s paths -- the same join approach `WI-VISUALIZE-0085` established and validated against the real corpus (not `Corpora.get_corpora()`, which discards path identity)"
  - "TF-IDF computation reuses scikit-learn's `TfidfVectorizer` (already a core dependency per `WI-VISUALIZE-0073`) rather than a hand-rolled TF-IDF implementation"
  - "Produces a visualization of the top distinguishing terms per comparison group (e.g. per-genre top-TF-IDF-term bar charts or an equivalent conventional chart), in PNG and vector (SVG/PDF) output, reusing `lcats.analysis.graph_plotters` and/or `visualize/rendering.py`'s existing chart primitives rather than duplicating a parallel plotting API"
  - "The underlying TF-IDF term/score table is exported alongside the figure (e.g. in the command's manifest JSON) so the numeric basis of the figure is inspectable, per the proposal's Scientific and Visualization Principle 6"
  - "The command emits an input-revision/content-identity value for every corpus/candidates.jsonl snapshot it consumes, following the dual-revision-disclosure pattern `WI-VISUALIZE-0085` established for genre-subset views"
  - "Analysis functions (document/group construction -> TF-IDF matrix/ranked term table) are unit-tested independently of image rendering on tiny fixtures; `lcats visualize tfidf` has a CLI integration/smoke test verifying real output-file creation"
  - "scripts/test passes with no new failures"
  - "lrh validate reports 0 errors"
required_evidence:
  - test_output
  - lrh_validate
  - manual_review
artifacts_expected:
  - lcats/src/lcats/visualize/sources.py (reused; extended only if a new source need appears)
  - lcats/src/lcats/visualize/analysis.py (extended: TF-IDF functions)
  - lcats/src/lcats/visualize/rendering.py (extended or reused)
  - lcats/src/lcats/visualize/cli.py (new tfidf subcommand)
  - lcats/tests/visualize_tests/ (new tests)
---

# Work Item: WI-VISUALIZE-0086

## Summary

Implement `lcats visualize tfidf`: a TF-IDF comparison visualization
identifying terms that distinguish one corpus subset (by default, a genre)
from the rest of the corpus, using *story* as the default document unit.
This is item 3 of `WS-CORPUS-TEXT-VISUALIZATION`'s decomposition, building
on the `lcats.visualize` substrate `WI-VISUALIZE-0073` delivered and the
genre-membership join `WI-VISUALIZE-0085` established and validated
against the real corpus.

## Problem / Context

The Worldcon 2026 paper needs a TF-IDF comparison figure alongside the
genre distribution and word-frequency figures already delivered.
`PROP-LCATS-CORPUS-TEXT-VISUALIZATION` flags the document unit as "a key
unresolved semantic decision" and requires it be explicit rather than
silently chosen; this work item pins it to *story*, matching the proposal's
own Paper-Critical Scope confirmation.

### Prior Art Check

- In-repo: no existing TF-IDF or scikit-learn usage exists in
  `lcats/src/lcats/analysis/` or `lcats/src/lcats/visualize/` (confirmed via
  `grep -rn "tfidf\|TfidfVectorizer\|sklearn"` across both directories --
  no hits). `lcats.analysis.graph_plotters` and `visualize/rendering.py`'s
  bar-chart primitives (added by `WI-VISUALIZE-0073`/`WI-VISUALIZE-0085`)
  already exist and should generalize to a per-group top-terms chart
  without a new plotting primitive. The genre-membership join
  (`sources.load_candidates_genre_membership`, `story_id` derived from
  `discovery.iter_collection_story_files`) already exists and should be
  reused directly rather than reimplemented.
- Sibling repos / external libraries: scikit-learn is already a core
  dependency (added by `WI-VISUALIZE-0073`); no new dependency required.
- Demand: no other open work item or proposal requests this capability
  independently; `WS-CORPUS-TEXT-VISUALIZATION`'s own exit criteria are the
  originating request.

## Scope

- `lcats visualize tfidf`, registered following the `genres`/`words`
  commands' CLI convention.
- TF-IDF computation via scikit-learn's `TfidfVectorizer`, story as the
  default document unit, genre (via the existing `candidates.jsonl` join)
  as the default comparison-group selector.
- Top-distinguishing-terms visualization per comparison group, plus export
  of the underlying term/score table.
- Input-revision/content-identity disclosure, following the dual-revision
  pattern `WI-VISUALIZE-0085` established.

## Out of Scope

- `topics` command -- separate item (`WI-VISUALIZE-0087`) in
  `WS-CORPUS-TEXT-VISUALIZATION`'s decomposition.
- Comparison groups other than genre (author, collection, period, etc.) --
  the selector should be named and explicit, but only a genre-based
  comparison group needs to actually work in this tranche; document any
  other selector as a documented gap rather than building it now.
- Any new genre-sidecar tooling -- consumes whatever `WI-VISUALIZE-0085`
  established as the genre-data join pattern, does not build new genre
  infrastructure.

## Required Changes

1. Extend `lcats/src/lcats/visualize/analysis.py` with TF-IDF functions
   (document/group construction from selected story texts, TF-IDF
   matrix/ranked term table via `TfidfVectorizer`).
2. Extend or reuse `lcats/src/lcats/visualize/rendering.py` for a
   top-distinguishing-terms chart per comparison group.
3. Add a `tfidf` subcommand to `lcats/src/lcats/visualize/cli.py`,
   following the `genres`/`words` subcommands' pattern, including the
   join-completeness assertion and dual-revision disclosure `words`
   already established for genre-subset views.
4. No changes expected to `lcats/src/lcats/cli.py` beyond what
   `WI-VISUALIZE-0073` already registered.

## Likely Files

- `lcats/src/lcats/visualize/analysis.py`
- `lcats/src/lcats/visualize/rendering.py`
- `lcats/src/lcats/visualize/cli.py`
- `lcats/tests/visualize_tests/`

## Validation

- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`
- `lcats visualize tfidf --output-dir /tmp/tfidf_viz`, confirming PNG (and
  vector where supported) output files are created, non-empty, and the
  source revision is disclosed
- `lcats visualize tfidf --genre fantasy --output-dir /tmp/tfidf_viz_fantasy`
  (or the equivalent selected-comparison-group invocation), confirming a
  distinct, genre-specific top-terms result

## Risk Notes

- **Document-unit choice affects every downstream number.** Story-as-document
  is the proposal's own confirmed default; if implementation reveals this
  produces degenerate results (e.g. too few documents per genre for a
  stable IDF), document the finding explicitly rather than silently
  switching the unit.
- **Vector output may not apply to every rendering path.** Per the
  proposal's Packaging note, `matplotlib`-rendered conventional charts
  support vector output natively; if this command's chart type ends up
  wordcloud-rendered instead, the same PNG-first caveat `words` documents
  applies.
