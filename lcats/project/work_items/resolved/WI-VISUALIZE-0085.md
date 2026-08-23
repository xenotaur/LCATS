---
resolution: "Implemented and merged in PR #363 (commit 65f83868)."
blocked_reason: null
blocked: false
id: WI-VISUALIZE-0085
title: "Word-frequency visualization: lcats visualize words"
type: deliverable
status: resolved
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
  - lcats/src/lcats/analysis/story_analysis.py
  - lcats/src/lcats/visualize/
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
  - "`lcats visualize words` is registered under `lcats visualize`, reusing the existing `lcats.visualize` package split (sources/analysis/rendering/cli) and CLI convention established by WI-VISUALIZE-0073"
  - "Tokenization, stopword removal, and frequency counting reuse `lcats.analysis.story_analysis.get_keywords`/`top_keywords` rather than reimplementing tokenization; if those functions prove insufficient for corpus-scale use, the gap is documented explicitly rather than silently forked"
  - "Story text is consumed via `lcats.stories.Story`/`Corpora` directly (unlike `genres`, word text genuinely lives on `Story.body` -- no external artifact needed for the whole-corpus case)"
  - "Supports a whole-corpus view and a genre-subset view; genre-subset filtering sources per-story genre membership from `experiments/05_metadata_genre_prefilter/results/full_scan/candidates.jsonl`'s `metadata_assessment.result.target_candidates` field (the per-story sibling of the aggregate `summary.json` WI-VISUALIZE-0073 already consumes) -- not an assumption that genre lives on `Story.metadata`"
  - "The join between `candidates.jsonl` rows and loaded story text uses `story_id`/`story_path` derived directly from `discovery.iter_collection_story_files`'s yielded paths (which preserve the exact `<collection>/<slug>` identity `candidates.jsonl` was built from), not `Corpora.get_corpora()`'s `Story` list, which discards story paths entirely -- `Story` carries only `name`/`body`/`metadata`, and both title-matching and deriving the slug from `metadata.name` are demonstrably ambiguous/lossy against the real checked-in corpus (confirmed: title matching is ambiguous for 16 rows, `metadata.name`-derived slugs fail for 17 Lovecraft rows). The join must assert complete, unambiguous one-to-one coverage rather than silently omitting or misassigning stories"
  - "Produces a word-frequency word cloud and a conventional ranked-frequency bar chart, each in PNG and vector (SVG/PDF) output, reusing `lcats.analysis.graph_plotters` and the `visualize/rendering.py` wordcloud renderer rather than duplicating a parallel plotting API"
  - "Preprocessing defaults (stopwords, case folding, minimum token length) are explicit and documented in the command's help/docs"
  - "For the genre-subset view, the command emits input-revision/content-identity values for *both* the story corpus and `candidates.jsonl` snapshots consumed, not only one -- changing candidate genre memberships while leaving story text unchanged changes the selected documents and resulting frequencies, so a corpus-only revision value cannot reproduce or audit the output. The whole-corpus view (no `candidates.jsonl` dependency) still only needs the corpus snapshot identity"
  - "Analysis functions (tokenize -> frequency mapping, etc.) are unit-tested independently of image rendering; `lcats visualize words` has a CLI integration/smoke test verifying real output-file creation"
  - "scripts/test passes with no new failures"
  - "lrh validate reports 0 errors"
required_evidence:
  - test_output
  - lrh_validate
  - manual_review
artifacts_expected:
  - "lcats/src/lcats/visualize/sources.py (extended: story-text + genre-membership loading)"
  - "lcats/src/lcats/visualize/analysis.py (extended: word-frequency functions)"
  - lcats/src/lcats/visualize/rendering.py (extended or reused)
  - lcats/src/lcats/visualize/cli.py (new words subcommand)
  - lcats/src/lcats/cli.py (registration)
  - lcats/tests/visualize_tests/ (new tests)
---

# Work Item: WI-VISUALIZE-0085

## Summary

Implement `lcats visualize words`: a word-frequency word cloud and
conventional ranked-frequency bar chart for either the whole LCATS corpus
or a genre subset. This is item 2 of `WS-CORPUS-TEXT-VISUALIZATION`'s
decomposition, building on the `lcats.visualize` substrate
`WI-VISUALIZE-0073` delivered.

## Problem / Context

The Worldcon 2026 paper needs word-frequency figures alongside the genre
distribution `WI-VISUALIZE-0073` already delivers. Unlike genre, word
text genuinely lives on the native LCATS story representation
(`Story.body`), so this command can consume `Corpora`/`Story` directly
for the whole-corpus case -- no external artifact needed there.

### Prior Art Check

- In-repo: `lcats.analysis.story_analysis.get_keywords` (tokenize to
  lowercase alphabetic terms, length >= 3, excluding a stopword set) and
  `top_keywords` (frequency ranking, deterministic tie-break) already
  exist and should be reused rather than reimplemented. A `# TODO
  (centaur): reconcile with the word counter below` comment already in
  that module flags awareness of related duplication risk in that file;
  this work item's reuse should not add a third implementation.
  `lcats.analysis.graph_plotters.plot_category_distribution` (added by
  WI-VISUALIZE-0073) and `lcats.visualize.rendering`'s wordcloud renderer
  already exist and generalize to word-frequency data without needing a
  new plotting primitive.
- Sibling repos / external libraries: none new required beyond
  `wordcloud`/scikit-learn, already core dependencies.
- Demand: no other open work item or proposal requests this capability
  independently; `WS-CORPUS-TEXT-VISUALIZATION`'s own exit criteria are
  the originating request.

## Scope

- `lcats visualize words`, registered following the `genres` command's
  CLI convention.
- Word-frequency analysis reusing `story_analysis.get_keywords`/
  `top_keywords`.
- Whole-corpus and genre-subset views. Genre-subset membership sourced
  from `experiments/05_metadata_genre_prefilter/results/full_scan/candidates.jsonl`
  (per-story `metadata_assessment.result.target_candidates`) -- distinct
  from the aggregate `summary.json` `genres` consumes.
- Word cloud + bar chart rendering, PNG + vector output, reusing existing
  `graph_plotters`/`rendering.py` functions.
- Input-revision/content-identity disclosure.

## Out of Scope

- `tfidf`, `topics` commands -- later items in
  `WS-CORPUS-TEXT-VISUALIZATION`'s decomposition.
- Lemmatization/POS filtering -- deferred per the workstream's own Open
  Questions (proposed default: defer).
- Any new genre-sidecar tooling -- consumes whatever `WI-VISUALIZE-0073`
  established as the genre-data pattern, does not build new genre
  infrastructure.

## Required Changes

1. Extend `lcats/src/lcats/visualize/sources.py` with story-text loading
   (whole-corpus case: via `Corpora`) and genre-membership loading (via
   `candidates.jsonl`). For the genre-subset case, join on `story_id`
   derived from `discovery.iter_collection_story_files`'s paths -- not
   `Corpora.get_corpora()`'s `Story` objects, which discard path/identity
   information entirely (see acceptance criteria for why title/`metadata.name`
   matching is unreliable). Emit distinct revision identifiers for the
   corpus snapshot and the `candidates.jsonl` snapshot.
2. Extend `lcats/src/lcats/visualize/analysis.py` with word-frequency
   functions built on `story_analysis.get_keywords`/`top_keywords`.
3. Extend or reuse `lcats/src/lcats/visualize/rendering.py` for
   word-frequency word cloud + bar chart.
4. Add a `words` subcommand to `lcats/src/lcats/visualize/cli.py`,
   following the `genres` subcommand's pattern.
5. No changes expected to `lcats/src/lcats/cli.py` beyond what
   `WI-VISUALIZE-0073` already registered (the `visualize` subparser
   group already exists; `words` nests under it).

## Likely Files

- `lcats/src/lcats/visualize/sources.py`
- `lcats/src/lcats/visualize/analysis.py`
- `lcats/src/lcats/visualize/rendering.py`
- `lcats/src/lcats/visualize/cli.py`
- `lcats/tests/visualize_tests/`

## Validation

- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`
- `lcats visualize words --output-dir /tmp/words_viz`, confirming PNG
  (and vector where supported) output files are created, non-empty, and
  the source revision is disclosed
- `lcats visualize words --genre fantasy --output-dir /tmp/words_viz_fantasy`,
  confirming genre-subset filtering produces a distinct, smaller result

## Risk Notes

- **Genre-subset membership is multi-label.** `candidates.jsonl`'s
  `target_candidates` can list more than one genre per story, so a
  story may appear in more than one genre's word-frequency subset. This
  should be documented explicitly rather than silently deduplicated or
  assigned to a single "primary" genre.
- **`get_keywords`'s stopword list is minimal and hardcoded.** It may
  not be scientifically defensible as-is for corpus-scale/paper use;
  confirm during implementation whether the existing list is adequate or
  needs expansion, and document the choice either way.
- **`Story`/`Corpora` do not preserve story-path identity.** Confirmed
  against real data: `Corpora.get_corpora()` only appends bare `Story`
  objects (`name`/`body`/`metadata`, no path) to its collection lists, so
  joining `candidates.jsonl` rows to loaded stories by title or
  `metadata.name` is unreliable (ambiguous for 16 rows; fails for 17
  Lovecraft rows via `metadata.name`). The genre-subset implementation
  must derive `story_id` from `discovery.iter_collection_story_files`'s
  paths directly, not from `Corpora`'s `Story` list.
