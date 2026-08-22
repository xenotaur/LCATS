---
resolution: null
blocked_reason: null
blocked: false
id: WI-VISUALIZE-0073
title: Reusable lcats visualize CLI substrate and genres command
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
  - project/design/proposals/proposed/genre-evidence-sidecars/00_proposal.md
  - lcats/src/lcats/stories.py
  - lcats/src/lcats/analysis/graph_plotters.py
depends_on: []
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
  - "A new `lcats.visualize` package (or equivalently named module) separates source adapters, analysis functions, and rendering functions per the proposal's Architecture Sketch, consuming `lcats.stories.Story`/`Corpora` directly rather than introducing a parallel document representation"
  - "Conventional-chart rendering reuses or extends `lcats.analysis.graph_plotters` rather than duplicating a parallel Matplotlib/Seaborn plotting API"
  - "`lcats visualize genres` is registered under `lcats visualize` following the existing `subparsers.add_parser`/`build_*_parser(add_help=False)` CLI convention (see `stats`/`assess` in `cli.py`), and sources genre data through a named, real, full-corpus artifact: `experiments/05_metadata_genre_prefilter/results/full_scan/summary.json`'s `genre_coverage.primary_target_genre_counts` field plus its `no_usable_signal_count` (together sum to exactly 1868/1868 stories, unlike the multi-label `target_candidate_counts` field which sums to 1807 due to double-counting stories with more than one candidate genre) as the primary source, rather than assuming genre is already present in `Story.metadata` or building against the not-yet-checked-in `genre-sidecar-v1` schema"
  - "If the source artifact covers a sample rather than the full corpus (e.g. `experiments/04_genre_census`'s checked-in `census_sample_summary.json` currently covers 20 of 1,868 stories, `mode: \"sample\"`), the command and its rendered output explicitly surface the source population, sample size/mode, and denominator — a sample must never be presented as an unqualified corpus-wide \"genre distribution\". A figure intended to represent the whole corpus requires a full-corpus artifact instead of a sample one."
  - "`lcats visualize genres` produces a genre-distribution word cloud and a conventional bar/distribution chart, each in PNG and, where the underlying renderer supports it, SVG/PDF vector output"
  - "The command emits an input-revision/content-identity value (e.g. corpus/sidecar commit SHA or a content hash of the specific files read) alongside its output, not only selectors/parameters/seed"
  - "`wordcloud` and scikit-learn are added as core dependencies in `pyproject.toml`/`environment.yml`, matching the already-core `matplotlib`"
  - "Analysis functions (category -> count mapping, etc.) are unit-tested independently of image rendering; `lcats visualize genres` has a CLI integration/smoke test verifying output-file creation"
  - "scripts/test passes with no new failures"
  - "lrh validate reports 0 errors"
required_evidence:
  - test_output
  - lrh_validate
  - manual_review
artifacts_expected:
  - lcats/src/lcats/visualize/
  - lcats/src/lcats/cli.py (visualize subcommand registration)
  - lcats/pyproject.toml
  - lcats/environment.yml
---

# Work Item: WI-VISUALIZE-0073

## Summary

Build the shared source-adapter / analysis / rendering / CLI-orchestration
substrate for `lcats visualize` described in
`PROP-LCATS-CORPUS-TEXT-VISUALIZATION`, and deliver the first concrete
command, `lcats visualize genres`, producing genre-distribution figures
(word cloud + conventional chart, PNG and vector where practical) for the
Worldcon 2026 paper. This is item 1 of `WS-CORPUS-TEXT-VISUALIZATION`'s
Candidate Work Decomposition.

## Problem / Context

LCATS has no visualization CLI today — genre counts, word frequencies, and
other corpus-derived figures are currently produced ad hoc (notebooks or
one-off scripts) for paper work. `PROP-LCATS-CORPUS-TEXT-VISUALIZATION`
(adopted 2026-08-21) proposes a reusable `lcats visualize` command family;
this item delivers its substrate and the first, most paper-critical
command.

Two things this item must get right that a naive implementation would
miss, both surfaced during the proposal's own review:

1. **Genre data does not live where it might seem to.** `lcats.stories.Story`/`Corpora`
   load only canonical `story.json` files — genre labels live in separate
   `genre.json` sidecars per `PROP-GENRE-EVIDENCE-SIDECARS`, which are not
   currently loaded by `Corpora.get_corpora()`, and the checked-in corpus
   does not yet have `genre.json` for every story. `genres` must consume
   genre data through whichever artifact that proposal (or the existing
   `experiments/04_genre_census` census tooling) actually produces, not an
   assumption baked into `Story.metadata`.
2. **Don't build a parallel plotting API.** LCATS already has
   `lcats.analysis.graph_plotters` with Matplotlib/Seaborn renderers and
   dedicated tests (`tests/analysis_tests/graph_plotters_test.py`).
   Conventional-chart rendering here should reuse or extend that module.

### Prior Art Check

- In-repo: no existing `lcats visualize` command exists; `lcats.analysis.graph_plotters`
  is the existing conventional-chart renderer to reuse, not duplicate.
- Sibling repos / external libraries: `matplotlib` (core), `wordcloud`,
  scikit-learn (both new core deps) per the governing proposal.
- Demand: no other open work item or proposal requests this capability
  independently; `PROP-GENRE-EVIDENCE-SIDECARS`/`WS-GENRE-EVIDENCE-SIDECARS`
  is the upstream dependency for genre data, not a competing request. See
  the full search in `WS-CORPUS-TEXT-VISUALIZATION`'s Prior Art Check
  section.

## Risk Notes

- **Genre source artifact may not be fully landed yet.** If
  `PROP-GENRE-EVIDENCE-SIDECARS`'s sidecar tooling or a usable census
  export isn't available when this item executes, `genres` may need to
  target whatever partial genre data actually exists in the corpus at
  implementation time, with the gap noted explicitly rather than silently
  worked around.
- **New core dependencies.** Adding `wordcloud` and scikit-learn as
  unconditional dependencies is a real packaging change — confirm CI's
  headless (`Agg`) Matplotlib backend still works cleanly once `wordcloud`
  is added.
- **Sample-vs-full-corpus mismatch.** `experiments/04_genre_census`'s
  checked-in `census_sample_summary.json` currently covers only 20 of
  1,868 stories (`mode: "sample"`). If `genres` is implemented against
  that artifact as-is without a full-corpus source, a paper-critical
  figure could misrepresent a 20-story sample as the whole corpus — see
  the acceptance criterion requiring explicit population/sample-size/
  denominator disclosure.
- **`full_scan/summary.json` is a `dry_run: true` artifact.** Confirm
  during implementation whether a non-dry-run full-scan output exists or
  is expected before this item completes, and whether that distinction
  needs surfacing in the command's own output disclosure.

## Problem

See "Problem / Context" above for the full narrative. In short: LCATS has
no visualization CLI, and genre information lives entirely outside
`Corpora`/`Story`.

## Scope

- A new `lcats.visualize` package separating source adapters, analysis,
  and rendering, consuming `lcats.stories.Story`/`Corpora` directly.
- `lcats visualize genres`, sourcing genre counts from
  `experiments/05_metadata_genre_prefilter/results/full_scan/summary.json`'s
  `genre_coverage.primary_target_genre_counts` field plus its
  `no_usable_signal_count` (together a real, checked-in, non-overlapping
  full-corpus 1868/1868-story genre distribution — not the multi-label
  `target_candidate_counts` field, which sums to 1807 due to
  double-counting stories with more than one candidate genre) as the
  primary source.
- Word-cloud and conventional bar-chart rendering, PNG + vector output.
- Reuse of `lcats.analysis.graph_plotters` for the conventional chart.
- `wordcloud` and scikit-learn added as core dependencies.
- Input-revision/content-identity disclosure (e.g. a hash of the
  consumed `summary.json`) alongside output.

## Out of Scope

- `genre.json` sidecars / `PROP-GENRE-EVIDENCE-SIDECARS` consumption — no
  such files are checked in yet; do not build against a schema with no
  real data to validate against. Revisit once sidecars land.
- `words`, `tfidf`, `topics` commands — later items in
  `WS-CORPUS-TEXT-VISUALIZATION`'s decomposition.
- `experiments/04_genre_census`'s 20-story sample as a primary source —
  usable only as an explicitly-labeled secondary/comparison view, per the
  sample-scope-disclosure acceptance criterion, never as the corpus-wide
  figure.
- Modifying `lcats annotate`, `lcats promote`, or any sidecar-writing code
  (`forbidden_actions` already cover this).

## Required Changes

1. `lcats/src/lcats/visualize/__init__.py` (or similar) — package
   scaffold.
2. `lcats/src/lcats/visualize/sources.py` — a
   `load_full_scan_genre_counts(summary_json_path)` adapter reading
   `genre_coverage.primary_target_genre_counts` (plus
   `no_usable_signal_count` as an explicit "no signal" category) from the
   full-scan `summary.json` — not the multi-label `target_candidate_counts`
   field — returning a `{genre: count}` mapping plus the source's content
   hash/revision and story-count denominator.
3. `lcats/src/lcats/visualize/analysis.py` — pure functions operating on
   the `{genre: count}` mapping (already the shape needed; minimal
   transform).
4. `lcats/src/lcats/visualize/rendering.py` — a `plot_genre_distribution(...)`
   function following `graph_plotters.py`'s `(fig, ax)`/`save_path`
   convention (or an addition directly to `graph_plotters.py` if that
   fits its existing module boundary better — implementer's call, per the
   acceptance criterion's "reuse or extend" language), plus a
   `wordcloud`-based renderer.
5. `lcats/src/lcats/visualize/cli.py` — `build_visualize_parser(add_help=False)`
   with a nested `genres` subcommand, following `assess`/`stats`'s
   pattern.
6. `lcats/src/lcats/cli.py` — register the new `visualize` subparser and
   its nested `genres` sub-subparser; add `_handle_visualize_genres`.
7. `lcats/pyproject.toml`, `lcats/environment.yml` — add `wordcloud`,
   `scikit-learn`.

## Likely Files

- `lcats/src/lcats/visualize/` (new package)
- `lcats/src/lcats/cli.py`
- `lcats/src/lcats/analysis/graph_plotters.py` (possible extension)
- `lcats/pyproject.toml`, `lcats/environment.yml`
- `lcats/tests/visualize_tests/` (new)

## Validation

- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`
- `lcats visualize genres --output-dir /tmp/genre_viz`, confirming PNG
  (and vector where supported) output files are created, non-empty, and
  the genre counts (from `primary_target_genre_counts` plus
  `no_usable_signal_count`) sum to 1868 with the source revision disclosed

## Open Questions

- Should the full-scan `summary.json` path be hardcoded, a CLI flag with
  a default, or discovered via a corpus-relative convention? (Proposed
  default: CLI flag with a default pointing at the current checked-in
  path.)
- Exact output filename/directory convention — not yet specified
  anywhere.
