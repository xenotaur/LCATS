---
id: PROP-LCATS-CORPUS-TEXT-VISUALIZATION
type: design_proposal
title: Corpus and Document Text Visualization for LCATS
status: adopted
created_on: 2026-08-15
updated_on: 2026-08-21
implementation_status: not_started
implemented_by: []
supersedes: []
superseded_by: null
related_design:
  - lcats/project/README.md
  - lcats/project/design/README.md
  - lcats/project/work_items/README.md
  - lcats/project/design/proposals/proposed/genre-evidence-sidecars/00_proposal.md
---

## Summary

LCATS should provide a reusable Python analysis/visualization layer, exposed
through an `lcats visualize ...` CLI family, for generating visual summaries of
corpus metadata and document text.

The near-term motivation is research and paper support: quickly turn current
LCATS corpus outputs such as genre counts and story text into reproducible,
publication-useful graphics. The longer-term opportunity is broader: provide a
small document-analysis substrate suitable for exploratory digital humanities,
corpus inspection, and future ingestion of formats outside the native LCATS
story JSON representation.

This proposal is intentionally a rough design skeleton. It identifies the
problem, proposed command surface, architectural boundaries, paper-critical
scope, future scope, and open decisions that should be resolved in review before
implementation work is decomposed into workstreams or work items.

## Motivation

LCATS now contains a large story corpus and increasingly rich derived metadata.
Recent corpus work includes genre classification, which naturally produces
aggregate distributions that benefit from visualization. The project also needs
ways to inspect the textual content of stories and derived subsets without
requiring one-off notebook code for every figure.

A useful first example is the current genre distribution. A frequency mapping
such as:

```python
{
    "SF": 1308,
    "Fantasy": 120,
    "Mystery": 34,
    "Horror": 43,
    "Western": 44,
    ...
}
```

can be rendered as a word cloud, but the same underlying data should also be
usable for more conventional charts. Likewise, story text can support word
frequency clouds, TF-IDF comparisons, and topic-oriented visualizations.

The implementation should avoid baking these analyses into notebooks or into
one specific figure. Instead, LCATS should expose reusable Python functions and
thin CLI commands whose outputs can be reproduced, scripted, tested, and later
used from notebooks.

## Goals

1. Provide a stable `lcats visualize` command family for corpus/document
   visualization.
2. Keep visualization logic available as reusable Python APIs rather than only
   CLI code.
3. Support deterministic/reproducible output where the underlying algorithm
   permits it.
4. Make near-term paper figures easy to generate from current LCATS corpus data.
5. Separate source loading, text/statistical analysis, and rendering so future
   input formats and visualization types can be added without rewriting the
   pipeline.
6. Preserve enough metadata about parameters and inputs that generated figures
   can be regenerated and audited.
7. Prefer established open-source Python libraries over custom implementations
   when they satisfy the requirement.

## Non-Goals for the Initial Implementation

- Building a general-purpose digital-humanities platform.
- Replacing notebooks as an exploratory research environment.
- Committing generated figures as authoritative corpus data by default.
- Training new language models for visualization.
- Solving semantic topic modeling comprehensively in the first tranche.
- Supporting every document format immediately.
- Treating word clouds as scientifically sufficient when a conventional chart
  is more appropriate.

## Proposed User Surface

The working CLI shape is:

```text
lcats visualize genres ...
lcats visualize words ...
lcats visualize tfidf ...
lcats visualize topics ...
```

The names and exact arguments remain reviewable. The intended semantics are:

### `lcats visualize genres`

Visualize categorical corpus metadata such as genre counts.

Paper-oriented first uses:

- word cloud sized by story count;
- bar chart or similar conventional distribution plot;
- output to PNG and, if practical, SVG/PDF-capable vector output.

**Genre source is not yet a native `Story`/`Corpora` field and must be named
explicitly.** `Corpora`/`Story` (see Common Document Representation) load
only canonical `story.json` files; genre labels live in separate `genre.json`
sidecars per `PROP-GENRE-EVIDENCE-SIDECARS`, are not currently loaded by
`Corpora.get_corpora`, and the checked-in corpus does not yet have
`genre.json` files for every story. This command must consume genre data
through whatever artifact `PROP-GENRE-EVIDENCE-SIDECARS` (or the existing
`experiments/04_genre_census` census tooling, see
`tests/experiment_tests/run_census_test.py`) actually produces — an
assessment/census artifact or sidecar read, not an assumption that genre is
already present in `Story.metadata`. The exact artifact, label
normalization, and story-identity join key must be pinned down as part of
implementation planning for this command, aligned with
`PROP-GENRE-EVIDENCE-SIDECARS` rather than defining a second, competing
genre input contract.

### `lcats visualize words`

Visualize token/term frequencies from story text or a selected corpus subset.

Expected controls include:

- corpus/story selection;
- stopword handling;
- minimum/maximum frequency;
- maximum displayed terms;
- normalization/tokenization choices;
- deterministic random seed for word-cloud layout;
- output path and dimensions.

### `lcats visualize tfidf`

Visualize terms that distinguish documents or groups using TF-IDF.

A key unresolved semantic decision is the unit of a "document" for IDF. Likely
choices include story, author, collection, genre, or user-selected groups. This
must be explicit rather than silently chosen by the implementation.

### `lcats visualize topics`

Generate topic-oriented summaries and visualizations.

This command is intentionally the least specified in the initial proposal.
Possible first implementations include classical LDA/topic-term displays;
future implementations might use embedding-based topic models. The proposal
should not commit LCATS to BERTopic, LDA, or another technique until the paper
need and evaluation criteria are clearer.

## Architecture Sketch

The implementation should separate four layers.

### 1. Source adapters

Source adapters convert LCATS-native or external inputs into a common document
representation.

Initial source:

- native LCATS corpus/story JSON and existing corpus APIs.

Possible future adapters:

- `.txt`;
- `.docx`;
- Markdown;
- generic JSON with configurable text fields;
- extracted scene/sequel or Event-Role-World artifacts.

The first implementation should not require external file adapters if the paper
work only needs the LCATS corpus, but the internal interface should avoid making
future adapters awkward.

### 2. Analysis

Pure or mostly pure functions should compute reusable intermediate results such
as:

- category -> count mappings;
- token -> frequency mappings;
- term/document TF-IDF matrices or ranked term tables;
- topic -> weighted-term mappings.

Analysis results should be independently testable without image rendering.

### 3. Rendering

Rendering functions convert analysis results to visual outputs. Candidate
libraries include:

- `wordcloud` for word clouds (new dependency — see Packaging / Dependency
  Questions);
- `matplotlib` for conventional static figures — **already a core LCATS
  dependency** (`pyproject.toml`), and LCATS already has
  `lcats.analysis.graph_plotters` with Matplotlib/Seaborn renderers and
  dedicated tests. Conventional-chart rendering in this proposal should
  reuse or extend `graph_plotters` rather than create a parallel plotting
  API; introduce a new rendering module only for outputs `graph_plotters`
  doesn't already cover (word clouds, TF-IDF/topic-specific plots);
- scikit-learn for TF-IDF and possibly baseline topic modeling (new
  dependency — see Packaging / Dependency Questions).

### 4. CLI orchestration

The CLI should remain thin: parse selectors/options, call LCATS corpus APIs,
invoke analysis, invoke rendering, and report output locations/parameters.
Business logic should not live only in command handlers.

## Common Document Representation

LCATS already has a canonical story representation: `lcats.stories.Story`
(`src/lcats/stories.py`), with a `body` field (full text) and a `metadata`
dict, plus `from_dict`/`from_json_file`/`from_yaml_file`/`to_dict`
constructors and a companion `Corpora` loader. This satisfies the `text` and
`metadata` needs a new document abstraction would otherwise exist for.

The initial implementation should consume `Story`/`Corpora` directly rather
than introducing a parallel `TextDocument` type. `Story` has no dedicated
`id` field; where analysis code needs a stable per-document identifier, use
`Story.name` or a `metadata` key rather than adding a new field to `Story`
itself.

A separate, lighter internal representation may still be worth introducing
later, if and when non-LCATS source adapters (see Future Scope) need a
common shape that isn't native to `Story`. That is out of scope for the
first tranche.

## Paper-Critical Scope

The first implementation tranche should be driven by concrete figures needed
for the current LCATS paper rather than by the full future vision.

Candidate paper-critical features, confirmed against the current Worldcon
2026 paper's needs:

1. Genre distribution visualization from current classifier/corpus outputs.
2. Word-frequency word clouds for the whole corpus and selected genre subsets.
3. Conventional ranked-frequency plots accompanying word clouds where useful.
4. TF-IDF comparison across genres or other paper-relevant groups, with
   *story* as the default document unit and genre (or another corpus
   selector) as the explicit comparison-group parameter.
5. Topic-oriented visualization (`lcats visualize topics`) — confirmed
   paper-critical, not deferred; belongs in the first implementation
   tranche alongside genres/words/tfidf.
6. PNG and vector (SVG/PDF) output — both are required for the paper
   workflow, not PNG-only. Note that `wordcloud`'s raster-first layout may
   make vector output impractical for word-cloud figures specifically;
   where that's the case, the conventional-chart companion plots (via
   `matplotlib`, which supports vector output natively) should carry the
   vector-output requirement for that figure.
7. Reproducible output suitable for regeneration during paper revision,
   including input revision/content identity (see Reproducibility and
   Output Metadata).

## Future Scope

Possible follow-on capabilities include:

- `.docx`, `.txt`, Markdown, and generic JSON adapters;
- scene/sequel-specific visualizations;
- Event-Role-World term/entity/role visualizations;
- comparison across authors, genres, periods, collections, or extraction runs;
- co-occurrence networks;
- keyness/log-likelihood plots;
- lexical diversity and vocabulary-growth plots;
- topic evolution through story position;
- interactive HTML views;
- richer digital-humanities visualizations;
- reusable styling/presets for paper figures;
- saved analysis manifests capturing source revision, selectors, parameters,
  library versions, and random seeds.

Future features should be added only when they support an identified research,
inspection, or communication need.

## Scientific and Visualization Principles

1. Word clouds are exploratory/communicative graphics, not substitutes for
   quantitative comparison.
2. When a visualization encodes magnitude by area/font size, the underlying
   numeric mapping must be explicit and reproducible.
3. Comparative analyses should preserve a stable denominator/unit of analysis.
4. Preprocessing choices such as stopwords, case folding, tokenization,
   lemmatization, and n-grams materially affect results and should be explicit.
5. Figures used in research should be regenerable from tracked inputs and
   parameters.
6. The system should expose intermediate numerical/tabular data where practical
   so users can inspect what a graphic represents.

## Reproducibility and Output Metadata

At minimum, commands intended for paper use should support:

- explicit output path;
- an input revision or content identity for the corpus/classifier artifacts
  consumed (e.g. corpus commit SHA, or a content hash of the specific
  metadata/story files read) — logging only selectors, parameters, and a
  random seed is not sufficient to regenerate or audit a figure if the
  underlying corpus or classifier outputs change between paper revisions;
- deterministic/random seed control where applicable;
- machine-readable or logged parameters;
- stable sorting/tie behavior for ranked outputs;
- export of the underlying frequency/score table where useful.

Input revision/content identity is required for the first tranche, not
deferred future scope, since Goal 6 and Principle 5 both require figures to
be regenerable and auditable from tracked inputs. What remains open is only
whether that identity is captured as a full sidecar manifest per figure in
the first tranche, or as a simpler logged value (e.g. printed to stdout or a
one-line companion file) with the richer manifest format deferred until
after dogfooding.

## Testing Strategy

The design should favor tests at the analysis boundary rather than brittle image
pixel comparisons.

Likely tests:

- known frequency mapping -> expected ranking/counts;
- deterministic selector behavior;
- TF-IDF matrix/ranking sanity on tiny fixtures;
- output file creation and non-empty render smoke tests;
- seeded word-cloud generation produces stable enough behavior for regression
  purposes without depending on exact raster bytes;
- CLI integration tests for representative commands.

## Packaging / Dependency Questions

`matplotlib` is already a core LCATS dependency (`pyproject.toml`,
`environment.yml`). `wordcloud` and scikit-learn are not currently
dependencies and must be added.

Since `genres`/`words`/`tfidf`/`topics` are all confirmed paper-critical
(see Paper-Critical Scope), and each depends on at least one of `wordcloud`
or scikit-learn, both should be added as **core** dependencies rather than
an optional extra — an extra would only add install friction for
functionality every paper-critical command needs, with no corresponding
opt-out use case in the first tranche.

Remaining before implementation:

- whether SVG/vector output is directly supported by the chosen rendering
  path for each command (matplotlib: yes; wordcloud: PNG-first, see Paper-
  Critical Scope item 6);
- how headless rendering behaves in CI — this hasn't been exercised for
  figure output before, so confirm `matplotlib`'s non-interactive (`Agg`)
  backend is CI-safe before relying on it in tests.

Existing LCATS CLI patterns provide a natural fit: `cli.py` already
registers commands via `subparsers.add_parser(...)` with per-command
`build_*_parser(add_help=False)` modules (see `stats`, `assess`). A
`visualize` subcommand should follow the same convention, with its own
module building nested `add_subparsers` for `genres`/`words`/`tfidf`/
`topics`.

## Candidate Work Decomposition

Do not create these work items until the proposal is refined and adopted. A
possible decomposition is:

1. Paper-critical visualization substrate and `genres` command.
2. Text selection/preprocessing and `words` command.
3. TF-IDF analysis and comparison visualization.
4. Topic baseline — confirmed paper-critical, in scope for the first tranche.
5. Dogfood against the LCATS corpus and paper figures.
6. Documentation and examples.
7. Future external document adapters as a separate follow-on workstream or work
   item set.

Given four distinct command surfaces (each with its own rendering and
testing surface) plus two new core dependencies, this should land as a
small workstream covering items 1-6, rather than a single work item. Item 7
(future external adapters) should be a separate, later workstream.

## Open Design Questions

Resolved during review:

1. **Resolved.** Genre distribution, word-frequency clouds, and TF-IDF
   comparison are paper-critical (see Paper-Critical Scope).
3. **Resolved.** Reuse `lcats.stories.Story`/`Corpora`; no new document
   abstraction for the first tranche (see Common Document Representation).
4. **Resolved.** Core dependency, not an optional extra (see Packaging /
   Dependency Questions).
7. **Resolved.** Story is the default document unit; genre (or another
   selector) is the explicit comparison-group parameter.
8. **Resolved.** Yes — the paper needs topic modeling; `topics` is in the
   first tranche.
9. **Resolved.** PNG and vector (SVG/PDF); see Paper-Critical Scope item 6
   for the wordcloud/matplotlib caveat.
11. **Resolved.** Follow the existing `subparsers.add_parser` +
    `build_*_parser(add_help=False)` convention used by `stats`/`assess`
    (see Packaging / Dependency Questions).

Still open — low-risk defaults proposed, confirm during implementation
planning rather than blocking adoption:

2. Should `visualize genres` consume live corpus metadata directly, a saved
   assessment/census artifact, or both? *Proposed default: live corpus API
   first; saved-artifact support deferred until a concrete need appears.*
5. Which preprocessing defaults are scientifically defensible for literary
   text? *Proposed default: standard stopword removal, case folding, and
   tokenization; document the exact choices in the implementing work item.*
6. Should lemmatization/POS filtering be part of the initial `words` command
   or deferred? *Proposed default: defer, per the proposal's own
   Non-Goals.*
10. Should every figure produce an adjacent data/manifest sidecar? *Proposed
    default: log/emit the input revision identity now (see Reproducibility
    and Output Metadata); defer the richer structured-manifest format until
    after dogfooding.*
12. Should arbitrary external files enter through `lcats visualize`
    directly, or through a separate ingestion/document adapter API? *Out of
    scope for the first tranche either way — see Future Scope.*

## Alternatives Considered

### Notebook-only visualization

Continue writing one-off notebook cells for each figure.

Pros: lowest initial engineering cost.

Cons: weak reuse, inconsistent preprocessing, poor CLI automation, and harder
reproducibility across paper revisions.

### One monolithic visualization script

Add a script that loads current corpus data and emits all desired figures.

Pros: fast path for a single paper.

Cons: creates another research prototype rather than reusable LCATS capability;
poor extension path for future document formats and analyses.

### Reusable Python API plus thin CLI commands

Chosen working direction for review. This costs slightly more up front, but
keeps paper-specific figures small while establishing reusable analysis and
rendering boundaries.

## Adoption Criteria

The following have been settled during review (see Open Design Questions):

- the paper-critical command/figure set (genres, words, tfidf, and topics —
  all four, with PNG and vector output);
- the initial source representation (`lcats.stories.Story`/`Corpora`) and
  TF-IDF unit-of-analysis default (story, grouped by genre or selector);
- dependency strategy (`wordcloud` and scikit-learn as core dependencies,
  alongside the already-core `matplotlib`);
- the input-revision/content-identity reproducibility requirement;
- decomposition (a small workstream covering substrate through dogfooding
  and docs, per Candidate Work Decomposition).

Remaining, non-blocking implementation-planning defaults are listed inline
in Open Design Questions 2, 5, 6, 10, and 12.

Implementation should not begin merely because this skeleton exists.
Adoption should represent agreement on the first executable tranche — this
proposal is ready to move to `status: adopted` once a maintainer confirms
the above.
