# How to run `lcats visualize`

`lcats visualize` turns LCATS corpus metadata and story text into
reproducible, publication-useful figures: `genres` (genre distribution),
`words` (word-frequency), `tfidf` (TF-IDF comparison), `topics`
(classical topic-model baseline), `compare` (aligned two-series lexical
comparison), and `compare-many` (aligned N-way reference-deviation chart).
These commands share a common
`sources`/`analysis`/`rendering`/`cli` split under
`lcats.visualize`, reuse `lcats.analysis.graph_plotters` for conventional
charts rather than a parallel plotting API, and write a JSON manifest
alongside every figure disclosing the exact selectors/parameters/seed and
input-revision content hashes used -- so any figure can be regenerated and
audited later.

See [`../reference/cli-commands.md`](../reference/cli-commands.md#visualize)
for the full flag reference.

## Preprocessing defaults

`words`, `tfidf`, `topics`, `compare`, and `compare-many` all tokenize story text via
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
[`experiments/08_visualize_dogfood/figures/`](../../../experiments/08_visualize_dogfood/figures/)
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

### `tfidf` -- two modes: within-group salience, or a genuine contrast

`tfidf` has two ranking modes, selected by `--contrast`. Both fit IDF
across the whole corpus and require `--genre` (or another
comparison-group selector) to select a subset narrower than the whole
corpus; `--contrast` additionally *requires* `--genre` to be set, since
it needs a complement (everything outside the group) to compare against.

**Default mode (no `--contrast`): within-group salience.**

```bash
# Whole corpus
lcats visualize tfidf --output-dir figures/tfidf --top-k 20 --formats png,svg

# A genre subset
lcats visualize tfidf --genre fantasy --output-dir figures/tfidf_fantasy --top-k 20 --formats png,svg
```

**What this actually ranks.** `--genre` fits IDF across the whole
corpus, then ranks the *selected group's own* mean TF-IDF -- it does not
compute or subtract the complement group's mean, so this is not a true
distinguishing/contrast metric despite the `--help` text's wording. A
term common to the whole corpus can still rank highly for a subset if
it's frequent within that subset, even if it's no more characteristic of
that subset than of the corpus at large. Treat the result as "top terms
by within-group mean TF-IDF salience," not as a rigorous
this-vs-everything-else comparison. In practice a majority genre (e.g.
one that's 70% of the corpus) tends to rank very similarly to the
whole-corpus run, since its own mean is close to the corpus mean; a
smaller, more distinctive genre often (not guaranteed) surfaces more
genre-evocative terms, simply because its member stories share more
vocabulary with each other than with the corpus at large -- not because
the metric itself measures distinctiveness.

**`--contrast` mode: a genuine group-vs-complement comparison.**

```bash
lcats visualize tfidf --genre fantasy --contrast --output-dir figures/tfidf_contrast_fantasy --top-k 20 --formats png,svg
```

This is the mode that actually does what the default mode's `--help`
wording describes: it computes both the selected group's mean TF-IDF and
the complement's (every corpus story *not* in the group), over the same
corpus-wide-fit matrix, and ranks by `group_mean - complement_mean`. A
term common everywhere nets out near zero (or negative, if it's actually
*more* common in the complement) and drops out of the ranking entirely
-- only terms genuinely more prominent in the selected group than in the
rest of the corpus surface. This is a simple mean-difference baseline,
not a statistical significance test (no notion of sample-size confidence
or a p-value); a term from a very small group can still register a large
difference on thin evidence. `--contrast` with no `--genre` raises a
clear error rather than silently degenerating, since a whole-corpus
selection has no complement to contrast against.

The manifest's `mode` field discloses which mode produced a given
figure (`"salience"` or `"contrast"`) -- check it before citing a
`tfidf` result as a "distinguishing terms" figure. See
`experiments/08_visualize_dogfood/README.md`'s "Salience vs. contrast"
section for a real side-by-side comparison on the same fantasy subset:
the salience-mode top terms are dominated by generic narrative
vocabulary (`said`, `not`, `all`), while contrast mode correctly demotes
those and surfaces genre-distinctive terms (`king`, `princess`, `tree`,
`fox`) instead.

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

### `compare` -- aligned mirrored or reference-overlay charts

```bash
lcats visualize compare \
  --universe manifest \
  --manifest experiments/05_metadata_genre_prefilter/results/full_scan/genre_balanced_manifest.jsonl \
  --right-genre "science fiction" \
  --right-reference complement \
  --metric per_million \
  --output-dir figures/compare_sf \
  --formats png,svg
```

`compare` constructs a `ComparisonSpec`, runs the reusable aligned analysis,
and then renders either a mirrored chart (`--style mirrored`, the default) or
a commensurate reference overlay (`--style reference-overlay`). The command
writes `comparison_<style>.<format>` figures, `comparison.csv` as the
authoritative table used by the renderer, and `comparison_manifest.json`
containing universe, selector, overlap, metric, preprocessing, vocabulary,
order, and output provenance.

`--right-reference complement` makes the left/reference selector `U - S`, where
`S` is the right selector and `U` is the declared universe. `--right-reference
universe` uses the whole universe as the reference. Genre selectors use
candidate membership by default; pass `--membership-mode selection` for a
manifest's `selection_genre` labels. Reference-overlay requests require
compatible metrics and denominators and fail before writing figures when the
two sides are incommensurate. The current CLI source adapters support candidate
membership from `candidates.jsonl` and selection membership from manifest
`selection_genre` labels; primary membership is rejected until a per-story
primary source is available. Explicit term ordering is part of the reusable
analysis contract but is rejected by the CLI until a term-list option is
exposed.

### `compare-many` -- aligned N-way reference-deviation chart

```bash
lcats visualize compare-many \
  --universe manifest \
  --manifest experiments/05_metadata_genre_prefilter/results/full_scan/genre_balanced_manifest.jsonl \
  --membership-mode selection \
  --panels "fantasy,horror,science fiction" \
  --reference universe \
  --layout kabob \
  --output-dir figures/compare_many \
  --formats png,svg,pdf
```

`compare-many` composes an ordered sequence of two or more genre panels into
one figure. Every panel is resolved against the same declared universe `U`
(recorded with a SHA-256 fingerprint of its ordered story IDs) and shares one
vocabulary, term order, metric, denominator, and preprocessing policy. Panels
appear in the order given to `--panels`.

**Panels.** `--panel-mode direct` (default) shows each selector `S`;
`--panel-mode complement` shows `U - S`. The manifest's `complements` list
records every constructed complement with its base size, complement size,
universe size, and a `verified_equals_universe_minus_base` check.

**Reference policy.** `--reference universe` (default) or `--reference genre
--reference-genre G` compares every panel with one common reference and draws
that reference as its own non-negative panel. `--reference
per-panel-complement` compares each panel with `U` minus that panel.
`--reference none` draws panel values only; no deviation is computed.
Deviations are always `panel value - reference value`. The vocabulary and
order default to `auto`: `reference_value` with a common reference,
`max_absolute_deviation` for per-panel complements, and `max_panel_value`
without a reference. A `reference_value` request without a common reference
fails rather than silently choosing another ranking.

**Overlap.** Genre selectors need not be disjoint or exhaustive. The manifest
reports every pairwise intersection (including zero-size pairs) under
`panel_overlaps`, and `membership` states `partition_claim: false` together
with the observed `pairwise_disjoint` and `covers_universe` facts. Do not
caption an overlapping figure as a partition of the corpus.

**Scale.** All panels share one visible scale by default: one joint symmetric
scale for deviations, or one zero-based scale for values. `--scale
independent` is an explicit opt-in; each panel title then says
`[independent scale]`, each x-axis says `(own scale)`, the figure title warns
that bar lengths differ by panel, and the manifest's `rendering.scale.note`
records that lengths are not comparable across panels.

**Layout.** Panels fill bands of at most `--max-columns` (default 8) left to
right in declared order; each wrapped band repeats the reference panel and
term labels and keeps panel columns aligned. `--layout kabob` is a named
preset for the compact N-way reference-deviation chart: reference bars point
right, term labels sit on the outside right edge (no dedicated central word
column), and horizontal row guides run across the panels. The preset is only
a starting point; each choice is independently overridable with
`--reference-direction {left,right}`, `--term-labels
{center-column,outside-left,outside-right}`, `--[no-]hatching`,
`--[no-]legend`, `--[no-]row-guides`, and `--highlight
{off,per-genre,global}`. The Python equivalent is
`rendering.NWayRenderSpec.from_preset("kabob", ...)`.

**Accessibility.** Sign is encoded by bar direction on every figure and, with
hatching on (the default), by distinct hatches for below/above bars and
their legend swatches, so the figure remains readable in grayscale. Extrema
highlights are markedly darker than ordinary bars. For a single paper column,
pass a smaller `figsize` and a lower `max_columns` through the Python API so
labels stay legible; tick labels abbreviate thousands (`+6k`) to fit narrow
panels.

**Outputs.** The command writes `<stem>.<format>` figures, `<stem>.csv`, and
`<stem>_manifest.json` (default stem `comparison_nway`). The CSV is long-form:
one row per term and panel, with the panel's value, the reference it was
compared with, the signed deviation, raw and document counts, token and
document denominators, the plotted quantity and its axis limits, the scale
policy, the panel's band/column position, and whether the cell was
highlighted. The manifest adds the ordered selectors and resolved
memberships, references, overlaps, complements, metric and preprocessing,
vocabulary and term order, the full render spec and layout decisions, and a
SHA-256 hash of every figure and the CSV computed after writing (the manifest
does not hash itself). Figure metadata timestamps are stripped so re-running
the same inputs reproduces byte-identical files.

From Python, the same pipeline is `comparison.compare_many(corpus, spec)`
with an `NWayComparisonSpec`, followed by
`nway_outputs.write_nway_outputs(result, output_dir=..., stem=...,
render_spec=...)`. Visual deviations are descriptive; they are not
significance tests.

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

Every manifest (`<output-dir>/<command>_manifest.json`) discloses a
content hash over the exact file(s) consumed, so any figure can be
reproduced and audited:

- `words`, `tfidf`, `topics` -- `corpus_source_revision` (hash over every
  consumed story file), plus `candidates_source_revision` for
  genre-filtered `words`/`tfidf` runs.
- `compare` -- `corpus.source_revision` and, when a manifest universe is used,
  `universe.source_revision`; the adjacent CSV is the table rendered.
- `compare-many` -- the same revisions plus `universe.fingerprint`; the
  manifest's `outputs` section hashes every figure and the CSV.
- `genres` -- a different key, `source_revision` (hash over
  `summary.json` alone; `genres` doesn't read individual story files, so
  it has no `corpus_source_revision` to disclose).

Re-running the same command against a checkout whose inputs hash to the
same value(s) reproduces the figure exactly; seeded commands (`genres`,
`words`, `topics`) are additionally deterministic given the same
`--seed`.

## See also

- [CLI command reference: `visualize`](../reference/cli-commands.md#visualize)
- [`WI-VISUALIZE-0088` dogfooding output](../../../experiments/08_visualize_dogfood/) -- real, committed example figures with their manifests
- [`PROP-LCATS-CORPUS-TEXT-VISUALIZATION`](../../project/design/proposals/adopted/corpus-text-visualization/00_proposal.md) -- the design proposal this command family implements
