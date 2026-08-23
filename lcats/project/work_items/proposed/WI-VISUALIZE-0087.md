---
resolution: null
blocked_reason: null
blocked: false
id: WI-VISUALIZE-0087
title: Topic-model baseline visualization: lcats visualize topics
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
  - WI-VISUALIZE-0086
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
  - "`lcats visualize topics` is registered under `lcats visualize`, reusing the existing `lcats.visualize` package split (sources/analysis/rendering/cli) and CLI convention established by `WI-VISUALIZE-0073`/`WI-VISUALIZE-0085`/`WI-VISUALIZE-0086`"
  - "Implements a classical topic-model baseline (e.g. LDA or NMF via scikit-learn, already a core dependency) over the whole corpus or a selected subset -- an embedding-based topic model is explicitly out of scope for this baseline, per the governing proposal's own framing ('should not commit LCATS to BERTopic, LDA, or another technique until the paper need and evaluation criteria are clearer' -- this work item resolves that by picking the classical baseline, documented as a baseline, not a final technique choice)"
  - "The number of topics and any other model hyperparameters are explicit, documented CLI options with stated defaults, not hardcoded"
  - "Produces a topic -> weighted-term visualization (e.g. top terms per topic, one chart per topic or a combined figure), in PNG and vector (SVG/PDF) output where the underlying renderer supports it, reusing `lcats.analysis.graph_plotters` and/or `visualize/rendering.py`'s existing chart primitives rather than duplicating a parallel plotting API"
  - "The underlying topic-term weight table is exported alongside the figure (e.g. in the command's manifest JSON) so the numeric basis of the figure is inspectable, per the proposal's Scientific and Visualization Principle 6"
  - "A deterministic random seed controls topic-model fitting where the underlying algorithm's implementation permits it (e.g. scikit-learn's `random_state`), and is disclosed in the output manifest alongside the input-revision/content-identity value for the corpus snapshot consumed"
  - "Analysis functions (document construction -> fitted topic model -> topic/term table) are unit-tested independently of image rendering on tiny fixtures; `lcats visualize topics` has a CLI integration/smoke test verifying real output-file creation"
  - "scripts/test passes with no new failures"
  - "lrh validate reports 0 errors"
required_evidence:
  - test_output
  - lrh_validate
  - manual_review
artifacts_expected:
  - lcats/src/lcats/visualize/sources.py (reused; extended only if a new source need appears)
  - lcats/src/lcats/visualize/analysis.py (extended: topic-model functions)
  - lcats/src/lcats/visualize/rendering.py (extended or reused)
  - lcats/src/lcats/visualize/cli.py (new topics subcommand)
  - lcats/tests/visualize_tests/ (new tests)
---

# Work Item: WI-VISUALIZE-0087

## Summary

Implement `lcats visualize topics`: a classical topic-model baseline
visualization (topic -> weighted-term display) over the LCATS corpus. This
is item 4 of `WS-CORPUS-TEXT-VISUALIZATION`'s decomposition, building on the
`lcats.visualize` substrate `WI-VISUALIZE-0073` delivered.

## Problem / Context

The governing proposal (`PROP-LCATS-CORPUS-TEXT-VISUALIZATION`) confirms
`lcats visualize topics` as paper-critical (Paper-Critical Scope item 5),
while explicitly deferring the choice between classical (LDA/topic-term)
and embedding-based (e.g. BERTopic) techniques until paper need and
evaluation criteria are clearer. This work item resolves that open question
by delivering a classical baseline, framed and documented as a baseline
rather than a final technique commitment -- consistent with the proposal's
own Non-Goal ("does not solve semantic topic modeling comprehensively in
the first tranche").

### Prior Art Check

- In-repo: no existing topic-modeling code exists in
  `lcats/src/lcats/analysis/` or `lcats/src/lcats/visualize/` (confirmed via
  the same grep sweep run for `WI-VISUALIZE-0086`: no `sklearn`/topic-model
  hits outside this proposal's own design doc). `lcats.analysis.graph_plotters`
  and `visualize/rendering.py`'s chart primitives already exist and should
  generalize to a topic/term display without a new plotting primitive.
- Sibling repos / external libraries: scikit-learn is already a core
  dependency (added by `WI-VISUALIZE-0073`) and provides both LDA
  (`LatentDirichletAllocation`) and NMF (`NMF`) baselines; no new dependency
  required.
- Demand: no other open work item or proposal requests this capability
  independently; `WS-CORPUS-TEXT-VISUALIZATION`'s own exit criteria are the
  originating request.

## Scope

- `lcats visualize topics`, registered following the `genres`/`words`/
  `tfidf` commands' CLI convention.
- A classical topic-model baseline (LDA or NMF, via scikit-learn) fit over
  the whole corpus or a selected subset, with explicit, documented
  hyperparameters (topic count, random seed).
- Topic -> weighted-term visualization, plus export of the underlying
  topic-term weight table.
- Input-revision/content-identity and seed disclosure.

## Out of Scope

- Embedding-based topic models (e.g. BERTopic) -- explicitly deferred by the
  governing proposal until a concrete paper need and evaluation criteria
  exist; document this deferral, do not implement it speculatively.
- Topic evolution through story position, or any other Future Scope item
  from the proposal.
- Any new genre-sidecar tooling -- if this command supports a
  genre-subset selector at all, it should reuse the exact join pattern
  `WI-VISUALIZE-0085`/`WI-VISUALIZE-0086` established, not build new
  infrastructure; a whole-corpus-only first implementation is also
  acceptable if scope is tight, provided that's documented as a
  deliberate simplification.

## Required Changes

1. Extend `lcats/src/lcats/visualize/analysis.py` with topic-model functions
   (document construction from story texts, fitted classical topic model,
   topic -> weighted-term table extraction).
2. Extend or reuse `lcats/src/lcats/visualize/rendering.py` for a
   topic/term display (e.g. top terms per topic).
3. Add a `topics` subcommand to `lcats/src/lcats/visualize/cli.py`,
   following the existing subcommands' pattern.
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
- `lcats visualize topics --output-dir /tmp/topics_viz`, confirming PNG
  (and vector where supported) output files are created, non-empty, and
  the source revision plus random seed are disclosed

## Risk Notes

- **Topic-model output is sensitive to hyperparameters and corpus
  preprocessing.** Document the chosen defaults (topic count, seed,
  preprocessing) explicitly in the command help/docs; do not present a
  single baseline run's topics as a definitive or exhaustive corpus
  characterization, per the proposal's Scientific and Visualization
  Principles.
- **Classical baseline is intentionally not the final technique.** If a
  later iteration needs embedding-based topics, that is new scope for a
  future work item, not an amendment to this one.
