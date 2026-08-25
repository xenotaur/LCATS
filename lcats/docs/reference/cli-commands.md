# LCATS CLI command reference

Flags and arguments for every `lcats` subcommand, verified against
`lcats <command> --help`. For which commands are implemented vs. placeholder,
see [`cli-status.md`](cli-status.md).

## `help`

```
lcats help [topic]
```

Display LCATS help, including command-specific help.

| Argument | Description |
|---|---|
| `topic` | Optional command name, e.g. `lcats help survey`. |

## `info`

```
lcats info
```

Describe LCATS, the literary captain's advisory tool system.

## `gather`

```
lcats gather [--dry-run] [gatherers ...]
```

Gather one or more configured corpora.

| Argument / Flag | Description |
|---|---|
| `gatherers` | Optional gatherer names. Defaults to all gatherers. |
| `--dry-run` | Show which gatherers would run without executing downloads. |

## `inspect`

```
lcats inspect [files ...]
```

Inspect one or more story JSON files and print summaries.

## `display`

```
lcats display [files ...]
```

Display one or more story JSON files in human-readable form.

## `survey`

```
lcats survey [--mode {qa,specials}] [--check-for CHECK_FOR]
              [--print-clean-filenames] [--allowlist-config ALLOWLIST_CONFIG]
              [--allow-smart] [--no-allow-smart] [--context CONTEXT]
              [--nocontext] [--name-width NAME_WIDTH]
              [--identifier {path,filename,title}]
              [--unicode-name-width UNICODE_NAME_WIDTH] [--header]
              [--no-header] [--format {human,tsv}] [--output OUTPUT]
              [--progress] [--no-progress]
              [--exclude-codepoint EXCLUDE_CODEPOINT]
              [--exclude-char EXCLUDE_CHAR]
              [directories ...]
```

Survey LCATS corpus JSON files for quality issues such as special characters
and boundary contamination.

| Argument / Flag | Description |
|---|---|
| `directories` | Directories or files to survey. |
| `--mode {qa,specials}` | Survey mode. `qa` (default) for normal checks, or `specials` to default to special-character extraction. |
| `--check-for CHECK_FOR` | Check(s) to run. Repeatable or comma-separated: `special-characters`, `boundary-contamination`, `the_end-contamination`. |
| `--print-clean-filenames` | Print filenames of clean (finding-free) files. |
| `--allowlist-config ALLOWLIST_CONFIG` | Path to an allowlist config JSON. Defaults to the packaged corpus allowlist; pass an empty string to disable. |
| `--allow-smart` / `--no-allow-smart` | Toggle smart-punctuation allowlisting. |
| `--context CONTEXT` / `--nocontext` | Toggle surrounding-text context in findings. |
| `--name-width NAME_WIDTH` | Column width for filenames in human-format output. |
| `--identifier {path,filename,title}` | Identifier shown in TSV reports. Defaults to `path`. |
| `--unicode-name-width UNICODE_NAME_WIDTH` | Maximum Unicode name width for TSV shown on a TTY. `0` disables truncation. |
| `--header` / `--no-header` | Toggle TSV header row. |
| `--format {human,tsv}` | Output format. |
| `--output OUTPUT` | Write output to a file instead of stdout. |
| `--progress` / `--no-progress` | Toggle progress display. |
| `--exclude-codepoint EXCLUDE_CODEPOINT` | Exclude a specific Unicode codepoint from findings. |
| `--exclude-char EXCLUDE_CHAR` | Exclude a specific character from findings. |

**Note:** `--extract-script` also appears in `--help` output but is a legacy
compatibility flag — extraction now runs in-process via
`lcats.analysis.corpus.specials_cli`.

```
lcats survey --mode specials corpora/sherlock
lcats survey corpora/sherlock --check-for special-characters
lcats survey data/ --format tsv --output findings.tsv
lcats survey corpora/sherlock --no-progress --print-clean-filenames
```

## `assess`

```
lcats assess [--genre GENRE] [--model MODEL]
              [--max-body-chars MAX_BODY_CHARS]
              [--format {jsonl,json,tsv,human}] [--output OUTPUT]
              [--dry-run] [--progress] [--no-progress]
              [directories ...]
```

Assess LCATS corpus JSON files for quality and genre fit. Calls the Claude
API to produce structured include/exclude/review verdicts, genre confidence
scores, issue lists, and story summaries.

| Argument / Flag | Description |
|---|---|
| `directories` | Directories or JSON files to assess (default: `data/`). |
| `--genre GENRE` | Target genre for curation (lens mode): `science fiction`, `horror`, `humor`, `western`, `romance`, `mystery`, `fantasy`, `adventure`. Quote multi-word genres. Omit to detect genre automatically (detect mode). |
| `--model MODEL` | Claude model to use (default: `claude-opus-4-8`). |
| `--max-body-chars MAX_BODY_CHARS` | Max story body characters sent to the API (default: `100000`). |
| `--format {jsonl,json,tsv,human}` | Output format (default: `jsonl`). |
| `--output OUTPUT` | Write output to a file instead of stdout. |
| `--dry-run` | Run pre-flight QA checks and list files without calling the API. |
| `--progress` / `--no-progress` | Toggle progress display. |

See [`docs/how-to/run-assess.md`](../how-to/run-assess.md) for mode selection
guidance, manual prompt validation, and dry-run usage.

```
lcats assess corpora/sherlock --genre 'science fiction'
lcats assess data/ --genre horror --format tsv --output horror.tsv
lcats assess data/ --genre western --dry-run
ANTHROPIC_API_KEY=sk-... lcats assess corpora/ --genre romance --progress
```

## `stats`

```
lcats stats [--dedupe] [--no-dedupe] [--story-output STORY_OUTPUT]
            [--author-output AUTHOR_OUTPUT]
            [directories ...]
```

Compute story-level and author-level statistics for one or more corpus
directories or JSON files.

| Argument / Flag | Description |
|---|---|
| `directories` | Directories or files to compute statistics for. |
| `--dedupe` / `--no-dedupe` | Toggle deduplication by story identity. |
| `--story-output STORY_OUTPUT` | Write per-story stats to this file. |
| `--author-output AUTHOR_OUTPUT` | Write per-author stats to this file. |

```
lcats stats corpora/sherlock
lcats stats data/ --no-dedupe
lcats stats data/ --story-output story_stats.tsv --author-output author_stats.tsv
```

## `repair-specials`

```
lcats repair-specials [--header] [--format {tsv,jsonl}] files [files ...]
```

Generate conservative repair proposals for known mojibake fragments. This
command is non-destructive — it never modifies the input files.

| Argument / Flag | Description |
|---|---|
| `files` | Story JSON files to generate repair proposals for. |
| `--header` | Include a header row (TSV format only). |
| `--format {tsv,jsonl}` | Dry-run report format (human TSV or machine JSONL). |

## `promote`

```
lcats promote [--source SOURCE] [--dest DEST] [--dry-run] [collections ...]
```

Promote `data/` collections into `corpora/`. A collection with any mojibake
finding is skipped and reported rather than promoted; clean collections
wholesale-replace their `corpora/` counterpart.

| Argument / Flag | Description |
|---|---|
| `collections` | Collection names to consider. Defaults to every collection under `--source`. |
| `--source SOURCE` | Root directory of source collections (default: `data/`). |
| `--dest DEST` | Root directory to promote clean collections into (default: `../corpora`). |
| `--dry-run` | Survey and report without copying any files. |

See [`corpus-promotion.md`](corpus-promotion.md) for the full command
explanation, collection-name mapping, and exit-code semantics.

## `annotate`

```
lcats annotate [--source SOURCE] [--checkpoint-dir CHECKPOINT_DIR]
               [--model MODEL] [--dry-run]
               [collections ...]
```

Annotate `data/` story buckets with `genre.json`/`scenes.json` sidecars plus
a per-bucket `README.md`, via the `lcats assess` (genre) and
`scene_analysis` (segmentation) extractors. Requires `ANTHROPIC_API_KEY`
unless `--dry-run` is given.

| Argument / Flag | Description |
|---|---|
| `collections` | Collection names to annotate. Defaults to every collection under `--source`. |
| `--source SOURCE` | Root directory of source collections (default: `data/`). |
| `--checkpoint-dir CHECKPOINT_DIR` | Directory for checkpoint bookkeeping (default: `.annotate_checkpoints/`). Never `data/`, `corpora/`, or `cache/` — those are wiped by `lcats clean` / disposable by design. |
| `--model MODEL` | Claude model to use for both genre and segmentation (default: `claude-opus-4-8`). |
| `--dry-run` | List story buckets that would be annotated without calling the API. |

## `clean`

```
lcats clean [--data-only] [--cache-only] [gatherers ...]
```

Clear `data/` and/or `cache/` contents without shell-glob reasoning. Safe for
a symlinked `data/` or `cache/` setup: only contents are removed, never the
directory (or symlink) itself.

| Argument / Flag | Description |
|---|---|
| `gatherers` | Gatherer names to clean under `data/`. **With no names given, this does not scope to "every configured gatherer" one by one — it wholesale-clears everything under `data/`, including any custom or unregistered directories that aren't a known gatherer.** Naming specific gatherers instead removes only those subdirectories. |
| `--data-only` | Clean only `data/`; leave `cache/` untouched. |
| `--cache-only` | Clean only `cache/`; leave `data/` untouched. |

See [Preparing a corpora release](prepare-corpora-release.md) step 2 for a
worked walkthrough of when and why to use `lcats clean`.

## `linguistics`

```
lcats linguistics [--story-list STORY_LIST] [--backend {spacy,stanza,fake}]
                  [--model MODEL] [--include-token-detail]
                  [--existing {skip,validate,overwrite}]
                  [--summary-output SUMMARY_OUTPUT] [--output-root OUTPUT_ROOT]
                  [--dry-run]
                  [inputs ...]
```

Analyze LCATS stories with a local NLP backend and write compact
`linguistics.json` sidecars.

| Argument / Flag | Description |
|---|---|
| `inputs` | Story JSON files, story buckets, collection directories, or corpus roots. |
| `--story-list STORY_LIST` | Text file listing story paths or bucket directories, one per line. Repeatable. |
| `--backend {spacy,stanza,fake}` | NLP backend to use. Defaults to `spacy`; `fake` is for tests/dry plumbing only. |
| `--model MODEL` | Backend model name or language code. Defaults to the backend default. |
| `--include-token-detail` | Also write `linguistics.tokens.json` with normalized token records. |
| `--existing {skip,validate,overwrite}` | Existing-output behavior. Defaults to `skip`. |
| `--summary-output SUMMARY_OUTPUT` | Write the machine-readable JSON run summary to a file instead of stdout. |
| `--output-root OUTPUT_ROOT` | Redirect sidecars under `<output-root>/<collection>/<story>/` instead of writing beside each `story.json`. |
| `--dry-run` | Resolve inputs and report what would run without writing sidecars. |

See [`../how-to/run-linguistics.md`](../how-to/run-linguistics.md) for setup
and examples, and [`linguistics-sidecar.md`](linguistics-sidecar.md) for exact
sidecar and run-summary schemas.

## `visualize`

```
lcats visualize {genres,words,tfidf,topics,compare} ...
```

Generate reproducible, publication-useful figures from LCATS corpus
metadata and story text. Each subcommand shares a common `sources` /
`analysis` / `rendering` / `cli` split, reuses
`lcats.analysis.graph_plotters` for conventional charts, and emits an
input-revision/content-identity manifest alongside its figures so any
output can be regenerated and audited.

### `visualize genres`

```
lcats visualize genres [--summary-json SUMMARY_JSON]
                       [--output-dir OUTPUT_DIR] [--formats FORMATS]
                       [--seed SEED]
```

Visualize the full-corpus genre distribution from the metadata-genre-prefilter
full scan as a word cloud and a conventional bar chart.

| Argument / Flag | Description |
|---|---|
| `--summary-json SUMMARY_JSON` | Path to the full-scan `summary.json` (default: `experiments/05_metadata_genre_prefilter/results/full_scan/summary.json`). |
| `--output-dir OUTPUT_DIR` | Directory to write output figures to (default: `genre_viz`). |
| `--formats FORMATS` | Comma-separated output formats, e.g. `png,svg,pdf` (default: `png,svg`). |
| `--seed SEED` | Deterministic random seed for word-cloud layout (default: `42`). |

### `visualize words`

```
lcats visualize words [--corpus-root CORPUS_ROOT] [--genre GENRE]
                      [--candidates-jsonl CANDIDATES_JSONL] [--top-k TOP_K]
                      [--output-dir OUTPUT_DIR] [--formats FORMATS]
                      [--seed SEED]
```

Visualize word frequency across the whole corpus, or a genre subset, as a
word cloud and a conventional ranked-frequency bar chart.

| Argument / Flag | Description |
|---|---|
| `--corpus-root CORPUS_ROOT` | Root directory of story collections (default: `corpora`). |
| `--genre GENRE` | If provided, restrict to stories whose candidate genres (from `candidates.jsonl`) include this genre. Omit for the whole-corpus view. |
| `--candidates-jsonl CANDIDATES_JSONL` | Path to the full-scan `candidates.jsonl` (used only with `--genre`; default: `experiments/05_metadata_genre_prefilter/results/full_scan/candidates.jsonl`). |
| `--top-k TOP_K` | Number of top words to include; must be `>= 1` (default: `50`). |
| `--output-dir OUTPUT_DIR` | Directory to write output figures to (default: `words_viz`). |
| `--formats FORMATS` | Comma-separated output formats (default: `png,svg`). |
| `--seed SEED` | Deterministic random seed for word-cloud layout (default: `42`). |

### `visualize tfidf`

```
lcats visualize tfidf [--corpus-root CORPUS_ROOT] [--genre GENRE]
                      [--candidates-jsonl CANDIDATES_JSONL] [--top-k TOP_K]
                      [--contrast] [--output-dir OUTPUT_DIR] [--formats FORMATS]
```

Visualize the top TF-IDF-ranked terms for a comparison group -- by default
the whole corpus, or a genre subset via `--genre` -- as a conventional bar
chart. Story is the document unit; IDF is fit across the whole corpus
regardless of `--genre`, so a genre-subset run ranks terms distinguishing
that subset from the corpus at large.

*(This description matches the command's own `--help` text verbatim, but
is only fully accurate with `--contrast` -- read the Accuracy note below
before relying on it.)*

**Accuracy note:** the description above matches the command's own
`--help` text, but the ranking it produces *without* `--contrast` is the
selected group's mean TF-IDF only -- it does not compute or subtract the
complement group's mean, so it is not a rigorous distinguishing/contrast
metric on its own. `--contrast` (added by `WI-VISUALIZE-0090`) is the
mode that actually delivers what the description above says: it ranks by
`group_mean - complement_mean`, a genuine group-vs-rest-of-corpus
comparison, and requires `--genre` (or another comparison-group
selector) since a whole-corpus run has no complement. The output
manifest's `mode` field (`"salience"` or `"contrast"`) discloses which
ranking produced a given figure. See
[`../how-to/run-visualize.md`](../how-to/run-visualize.md) (`tfidf` section)
for what each mode actually measures, with a real side-by-side example.

| Argument / Flag | Description |
|---|---|
| `--corpus-root CORPUS_ROOT` | Root directory of story collections (default: `corpora`). |
| `--genre GENRE` | If provided, rank terms for stories whose candidate genres include this genre. Omit to rank terms across the whole corpus. |
| `--candidates-jsonl CANDIDATES_JSONL` | Path to the full-scan `candidates.jsonl` (used only with `--genre`). |
| `--top-k TOP_K` | Number of top terms to include; must be `>= 1` (default: `20`). |
| `--contrast` | Rank by group-vs-complement mean TF-IDF difference instead of within-group salience. Requires `--genre`. |
| `--output-dir OUTPUT_DIR` | Directory to write output figures to (default: `tfidf_viz`). |
| `--formats FORMATS` | Comma-separated output formats (default: `png,svg`). |

### `visualize topics`

```
lcats visualize topics [--corpus-root CORPUS_ROOT] [--n-topics N_TOPICS]
                       [--top-k TOP_K] [--seed SEED]
                       [--init {nndsvd,nndsvda,nndsvdar,random}]
                       [--max-iter MAX_ITER] [--output-dir OUTPUT_DIR]
                       [--formats FORMATS]
```

Visualize a classical topic-model baseline (scikit-learn `NMF`) over the
whole corpus as one top-weighted-term bar chart per topic. A baseline, not
a final technique choice -- embedding-based topic models (e.g. BERTopic)
are explicitly deferred.

| Argument / Flag | Description |
|---|---|
| `--corpus-root CORPUS_ROOT` | Root directory of story collections (default: `corpora`). |
| `--n-topics N_TOPICS` | Number of topics to fit; must be `>= 1` (default: `8`). |
| `--top-k TOP_K` | Number of top terms per topic to include; must be `>= 1` (default: `10`). |
| `--seed SEED` | Random seed for the NMF solver and its initialization (default: `42`). Affects the fitted topics under every `--init` choice, not only `random` -- scikit-learn's `nndsvd`-family initializers compute their starting point via a randomized SVD seeded by `--seed`. |
| `--init {nndsvd,nndsvda,nndsvdar,random}` | NMF initialization strategy (default: `nndsvda`). |
| `--max-iter MAX_ITER` | Maximum NMF solver iterations; must be `>= 1` (default: `400`). |
| `--output-dir OUTPUT_DIR` | Directory to write output figures to (default: `topics_viz`). |
| `--formats FORMATS` | Comma-separated output formats (default: `png,svg`). |

**Preprocessing defaults** (`words`, `tfidf`, `topics`, via
`lcats.analysis.story_analysis.get_keywords`): terms are lowercased,
restricted to ASCII alphabetic tokens, require a minimum length of 3
characters, and are filtered through a hardcoded stopword set.

See [`../how-to/run-visualize.md`](../how-to/run-visualize.md) for setup
and worked examples.

### `visualize compare`

```
lcats visualize compare [--corpus-root CORPUS_ROOT]
                        [--candidates-jsonl CANDIDATES_JSONL]
                        [--universe {corpus,manifest}] [--manifest MANIFEST]
                        [--left-genre LEFT_GENRE] [--right-genre RIGHT_GENRE]
                        [--membership-mode {candidate,primary,selection}]
                        [--right-reference {none,complement,universe}]
                        [--metric METRIC] [--left-metric METRIC]
                        [--right-metric METRIC]
                        [--style {mirrored,reference-overlay}]
                        [--top-k TOP_K] [--vocabulary VOCABULARY]
                        [--order-by ORDER_BY] [--include-stopwords]
                        [--min-length MIN_LENGTH]
                        [--output-dir OUTPUT_DIR] [--formats FORMATS]
```

Render an aligned lexical comparison from a declared universe and selectors.
The command writes figure files, `comparison.csv`, and
`comparison_manifest.json` with the universe, selector, metric, preprocessing,
vocabulary, ordering, overlap, and output provenance.

| Argument / Flag | Description |
|---|---|
| `--corpus-root CORPUS_ROOT` | Root directory of story collections (default: `corpora`). |
| `--candidates-jsonl CANDIDATES_JSONL` | Path to full-scan `candidates.jsonl`. |
| `--universe {corpus,manifest}` | Use the full corpus or a manifest story list as `U` (default: `corpus`). |
| `--manifest MANIFEST` | Manifest JSONL path required by `--universe manifest`. |
| `--left-genre LEFT_GENRE` / `--right-genre RIGHT_GENRE` | Genre selectors for the left/reference and right/target side. |
| `--membership-mode {candidate,primary,selection}` | Genre membership semantics (default: `candidate`). The current CLI source adapters support `candidate` and manifest `selection`; `primary` is rejected until a per-story primary source is available. |
| `--right-reference {none,complement,universe}` | Derive the left/reference selector from the right selector: no derivation, `U - S`, or all of `U`. |
| `--metric METRIC` | Metric for both sides unless side-specific metric flags are supplied. |
| `--left-metric METRIC` / `--right-metric METRIC` | Side-specific metric override. |
| `--style {mirrored,reference-overlay}` | Render a mirrored chart or a commensurate reference overlay (default: `mirrored`). |
| `--top-k TOP_K` | Number of aligned terms; must be `>= 1` (default: `20`). |
| `--vocabulary VOCABULARY` | Aligned vocabulary policy. |
| `--order-by ORDER_BY` | Display order policy. `explicit` is rejected by the CLI until an explicit term-list option is exposed. |
| `--include-stopwords` | Include stopwords in tokenization. |
| `--min-length MIN_LENGTH` | Minimum alphabetic token length (default: `3`). |
| `--output-dir OUTPUT_DIR` | Directory for figures, CSV, and manifest (default: `compare_viz`). |
| `--formats FORMATS` | Comma-separated figure formats (default: `png,svg`). |

```
lcats visualize compare --universe manifest \
  --manifest experiments/05_metadata_genre_prefilter/results/full_scan/genre_balanced_manifest.jsonl \
  --right-genre "science fiction" --right-reference complement \
  --metric per_million --output-dir /tmp/lcats_compare_smoke
```

## Placeholder commands

These commands are declared but not yet implemented — running them prints a
"not yet implemented" message and exits.

| Command | Description |
|---|---|
| `lcats index` | Preprocess a corpus to answer questions. |
| `lcats advise` | Run the LCATS command-line advising tool. |
| `lcats eval` | Evaluate LCATS on a benchmark suite. |
