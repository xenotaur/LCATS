# How to run `lcats visualize`

`lcats visualize` turns LCATS corpus metadata and story text into
reproducible, publication-useful figures: `genres` (genre distribution),
`words` (word-frequency), `tfidf` (TF-IDF comparison), and `topics`
(classical topic-model baseline). All four share a common
`sources`/`analysis`/`rendering`/`cli` split under
`lcats.visualize`, reuse `lcats.analysis.graph_plotters` for conventional
charts rather than a parallel plotting API, and write a JSON manifest
alongside every figure disclosing the exact selectors/parameters/seed and
input-revision content hashes used -- so any figure can be regenerated and
audited later.

See [`../reference/cli-commands.md`](../reference/cli-commands.md#visualize)
for the full flag reference.

## Preprocessing defaults

`words`, `tfidf`, and `topics` all tokenize story text via
`lcats.analysis.story_analysis.get_keywords`: terms are lowercased,
restricted to ASCII alphabetic tokens, require a minimum length of 3
characters, and are filtered through a hardcoded stopword set. This is the
same tokenizer across all three commands -- results are directly
comparable. Run `lcats visualize <subcommand> --help` for the exact
wording; it is not duplicated verbatim here to avoid drift if the
implementation's own help text changes.

## Examples

Each example below was run against the real, checked-in corpus as part of
`WI-VISUALIZE-0088`'s dogfooding pass; the actual committed output lives
under
[`experiments/08_visualize_dogfood/figures/`](../../../experiments/08_visualize_dogfood/)
if you want to see real results without running anything yourself.

### `genres` -- whole-corpus genre distribution

```bash
lcats visualize genres --output-dir figures/genres --formats png,svg
```

Produces a word cloud and a conventional bar chart of the full-corpus
genre distribution, sourced from
`experiments/05_metadata_genre_prefilter/results/full_scan/summary.json`'s
non-overlapping *primary*-genre counts (not the multi-label
`target_candidate_counts` field -- see the note on genre counts below).

### `words` -- whole corpus and a genre subset

```bash
# Whole corpus
lcats visualize words --output-dir figures/words --top-k 30 --formats png,svg

# Restricted to one genre
lcats visualize words --genre fantasy --output-dir figures/words_fantasy --top-k 30 --formats png,svg
```

`--genre` restricts to stories whose candidate genres (from
`candidates.jsonl`) include the named genre -- a *multi-label* selector,
not the same field `genres` uses (see below).

### `tfidf` -- top distinguishing terms

```bash
# Whole corpus (a valid degenerate case: ranks terms distinguishing
# nothing in particular, just corpus-wide salience)
lcats visualize tfidf --output-dir figures/tfidf --top-k 20 --formats png,svg

# A genre subset, to see what distinguishes it from the corpus at large
lcats visualize tfidf --genre fantasy --output-dir figures/tfidf_fantasy --top-k 20 --formats png,svg
```

The comparison is only as sharp as the subset is distinctive: a majority
genre (e.g. one that's 70% of the corpus) barely differs from the whole
corpus by mean TF-IDF, since the "background" it's compared against is
mostly itself. A smaller, more distinctive genre produces a visibly
sharper contrast.

### `topics` -- classical NMF baseline

```bash
lcats visualize topics --output-dir figures/topics --n-topics 6 --top-k 10 --formats png,svg
```

Fits a classical NMF topic model over the whole corpus and produces one
bar chart per topic. This is a baseline, not a final technique choice --
embedding-based topic models are explicitly deferred (see
`WI-VISUALIZE-0087`). At story-level granularity, topics often cluster
around distinctive named characters rather than broader themes; treat a
single baseline run as exploratory, not a definitive corpus
characterization.

## A note on the two genre-count definitions

`experiments/05_metadata_genre_prefilter`'s `summary.json` carries two
different, both-legitimate "story count per genre" fields, and they do
not agree with each other:

- `genre_coverage.primary_target_genre_counts` -- non-overlapping, each
  story counted once under its single primary genre. This is what
  `lcats visualize genres` renders.
- `target_candidate_counts` -- multi-label, a story counted once per
  candidate genre it matches. This is what `--genre` filtering in
  `words`/`tfidf` actually selects against (via `candidates.jsonl`'s
  `target_candidates` field).

A story can therefore appear in a `--genre fantasy` selection without
being counted as "fantasy" in the `genres` command's own distribution
figure, if fantasy is a secondary candidate genre rather than its primary
one. When citing a story count for a specific figure, cite the number
that figure's own manifest actually reports -- do not assume the two
definitions agree.

## Regenerating a figure

Every manifest (`<output-dir>/<command>_manifest.json`) discloses
`corpus_source_revision` (and, for genre-filtered runs,
`candidates_source_revision`) -- content hashes over the exact files
consumed. Re-running the same command against a checkout whose corpus
(and `candidates.jsonl`, if used) hash to the same values reproduces the
figure exactly; seeded commands (`genres`, `words`, `topics`) are
additionally deterministic given the same `--seed`.

## See also

- [CLI command reference: `visualize`](../reference/cli-commands.md#visualize)
- [`WI-VISUALIZE-0088` dogfooding output](../../../experiments/08_visualize_dogfood/) -- real, committed example figures with their manifests
- [`PROP-LCATS-CORPUS-TEXT-VISUALIZATION`](../../project/design/proposals/adopted/corpus-text-visualization/00_proposal.md) -- the design proposal this command family implements
