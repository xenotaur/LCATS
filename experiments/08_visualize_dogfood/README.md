# Visualize Dogfooding — Worldcon 2026 Talk/Poster Figures

This experiment dogfoods the full `lcats visualize` command family
(`genres`, `words`, `tfidf`, `topics`) against the real, checked-in LCATS
corpus, producing real figures for the Worldcon 2026 talk and poster
(`FOCUS-WORLDCON-2026`) rather than synthetic test fixtures. It closes
`WI-VISUALIZE-0088`.

**Interim figures location.** No Worldcon 2026 paper/talk source
repository or directory exists anywhere in this codebase yet (confirmed
by search at implementation time). This directory follows the repo's
existing `experiments/NN_slug/` numbering convention as the interim
committed-figures location, until the actual talk/poster source repo (or
an in-repo `Papers/`-style location) exists to receive them.

## Inputs

- Corpus: `corpora/` (1868 stories).
- Genre membership: `experiments/05_metadata_genre_prefilter/results/full_scan/candidates.jsonl`
  and `.../summary.json` — the same artifacts `lcats visualize`'s
  `--genre` selector and `genres` command already consume by default; no
  new data source or selector was introduced.

## Genre selections

The corpus is dominated by science fiction (1308/1868 stories, ~70%) —
expected for a Worldcon-focused corpus, but it means a science-fiction
subset barely differs from the whole corpus by mean TF-IDF (the
"distinguishing terms" comparison degenerates when the subset *is*
most of the population). Fantasy gives a visibly sharper contrast
(`king`, `princess`, `tree` vs. the whole corpus), so both are
included: science fiction for corpus-scale `words`, and both science
fiction and fantasy for `tfidf` to show the contrast directly.

**Note on the two fantasy counts.** `figures/genres/genres_manifest.json` (the
`genres` command's non-overlapping *primary*-genre distribution) reports
120 fantasy stories. `figures/tfidf_fantasy/tfidf_manifest.json` (the `tfidf`
command's `--genre fantasy` selector, membership in the multi-label
`target_candidates` field) reports `story_count: 122` — 2 stories carry
fantasy as a secondary candidate genre without it being their primary
genre. These are two different, both-correct definitions of "fantasy
stories" from the same underlying `05_metadata_genre_prefilter`
artifact; the `tfidf_fantasy` figure's actual denominator is 122, not
120 — do not conflate the two when citing a count for a specific figure.

## Outputs (`figures/`)

Each subdirectory is one real `lcats visualize` invocation's output
(PNG + SVG figures, plus a JSON manifest disclosing the exact
selectors/parameters/seed and input-revision content hashes used):

| Directory | Command | Selector |
|---|---|---|
| `genres/` | `lcats visualize genres` | whole corpus |
| `words_whole_corpus/` | `lcats visualize words --top-k 30` | whole corpus |
| `words_science_fiction/` | `lcats visualize words --genre "science fiction" --top-k 30` | science fiction subset |
| `tfidf_whole_corpus/` | `lcats visualize tfidf --top-k 20` | whole corpus |
| `tfidf_science_fiction/` | `lcats visualize tfidf --genre "science fiction" --top-k 20` | science fiction subset |
| `tfidf_fantasy/` | `lcats visualize tfidf --genre fantasy --top-k 20` | fantasy subset |
| `topics_whole_corpus/` | `lcats visualize topics --n-topics 6 --top-k 10` | whole corpus, classical NMF baseline |

Every manifest's `corpus_source_revision` for this run is
`523543e4844103674db8a4e099eb218e926acc29fe6ab798c738a1110cb89331`
(content hash over every consumed story file); `figures/genres/genres_manifest.json`'s
`source_revision` (over `summary.json`) is
`7f0c12e43e7ac0baf55a764f818f50b81ed08c131d861a3a010d8cbb656bef43`; the
`--genre`-filtered runs additionally disclose
`candidates_source_revision` `ea52c53d60a39d703d168f709a929e64527494d1af3902268b26ef4883fa107d`
over `candidates.jsonl`. Any of these figures can be regenerated exactly
by running the command in the table above against a checkout whose
corpus/candidates content hashes match.

## Findings from dogfooding

- No code fix was required — every command produced a valid, real figure
  on the first real-corpus run at full 1868-story scale for both the
  whole-corpus and genre-subset cases, and the `--top-k`/`--n-topics`/
  `--max-iter`/`--init` validation paths added during
  `WI-VISUALIZE-0086`/`-0087` held up.
- `topics` (NMF baseline, whole corpus, 6 topics) mostly clusters around
  distinctive named characters (e.g. `biggs`/`hanson`, `magpie`/`yuh`)
  rather than broader thematic topics — an expected, documented
  limitation of a classical, story-level NMF baseline (see
  `WI-VISUALIZE-0087`'s own Risk Notes: "do not present a single
  baseline run's topics as a definitive or exhaustive corpus
  characterization"), not a bug. Worth a caption/note if used directly
  in the talk.
- `tfidf` against the majority genre (science fiction, ~70% of the
  corpus) is a weak "distinguishing terms" comparison by construction —
  documented above under Genre selections, not a defect in the command.

## Reproduction

```bash
lcats visualize genres --output-dir experiments/08_visualize_dogfood/figures/genres --formats png,svg
lcats visualize words --output-dir experiments/08_visualize_dogfood/figures/words_whole_corpus --top-k 30 --formats png,svg
lcats visualize words --genre "science fiction" --output-dir experiments/08_visualize_dogfood/figures/words_science_fiction --top-k 30 --formats png,svg
lcats visualize tfidf --output-dir experiments/08_visualize_dogfood/figures/tfidf_whole_corpus --top-k 20 --formats png,svg
lcats visualize tfidf --genre "science fiction" --output-dir experiments/08_visualize_dogfood/figures/tfidf_science_fiction --top-k 20 --formats png,svg
lcats visualize tfidf --genre fantasy --output-dir experiments/08_visualize_dogfood/figures/tfidf_fantasy --top-k 20 --formats png,svg
lcats visualize topics --output-dir experiments/08_visualize_dogfood/figures/topics_whole_corpus --n-topics 6 --top-k 10 --formats png,svg
```
