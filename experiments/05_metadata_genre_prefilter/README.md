# Metadata Genre Prefilter

`WI-GENRE-0002` extends the dry-run scaffold from `WI-GENRE-0001` into an
experiment-local metadata-rule evidence pilot. The runner discovers LCATS story
buckets, uses LCATS path identity as the primary story ID, reads Gutenberg
subjects from an explicitly supplied existing SQLite cache in read-only mode,
records all matching metadata genre-rule evidence, and writes a deterministic
40-story pilot manifest.

## No-Network Default

The runner is deliberately read-only. It does not import
`lcats.gettenberg.cache`, does not call `ensure_gutenberg_cache()`, and does
not build, download, refresh, or repair the Gutenberg metadata cache. Missing
cache state is reported in the summary instead of being fixed automatically.

Before running a cache-backed pilot, sync or expose an existing local
`gutenbergindex.db` and pass it with `--cache-db`. If `--cache-db` is omitted,
the runner reports `cache.status: "not_supplied"` and does not read any default
cache location. If an explicitly supplied cache is absent or does not match a
supported schema, candidate rows still emit assessment-shaped metadata evidence,
but with empty `raw_subjects`, empty rule matches, and a cache status explaining
the readiness state.

## Usage

From the repository root:

```bash
python experiments/05_metadata_genre_prefilter/run_prefilter.py \
  --dry-run \
  --output experiments/05_metadata_genre_prefilter/results/smoke
```

With an existing Gutenberg metadata cache:

```bash
python experiments/05_metadata_genre_prefilter/run_prefilter.py \
  --dry-run \
  --corpus-root corpora \
  --cache-db /path/to/existing/gutenbergindex.db \
  --output experiments/05_metadata_genre_prefilter/results/pilot_40
```

Optional repeated-volume cap:

```bash
python experiments/05_metadata_genre_prefilter/run_prefilter.py \
  --dry-run \
  --cache-db /path/to/existing/gutenbergindex.db \
  --max-per-gutenberg-id 2 \
  --output experiments/05_metadata_genre_prefilter/results/pilot_40_capped
```

Omit `--cache-db` for no-cache readiness and shape checks. The omitted-cache
path does not inspect `$LCATS_CACHE_DIR`, `cache/gutenbergindex.db`, or any
other implicit cache location.

## Outputs

The runner writes only under the requested output directory:

- `candidates.jsonl`: one row per discovered story, keyed by LCATS story ID.
- `pilot_40_manifest.jsonl`: deterministic pilot rows, roughly 10 each from
  `lovecraft`, `sherlock`, O. Henry (`ohenry-four_million` and
  `ohenry-whirligigs`), and `mass_quantities`.
- `summary.json`: story counts, collection counts, cache readiness,
  target-candidate counts, secondary-signal counts, Gutenberg-ID parse
  failures, repeated Gutenberg-ID diagnostics, and pilot-selection diagnostics.

The LCATS story ID is the corpus-root-relative story bucket path, such as
`sherlock/five_orange_pips`. Gutenberg ID and URL are provenance fields only.
Repeated Gutenberg IDs are reported as collection- or volume-level diagnostics,
not as story identity.

## Metadata Evidence

Each candidate row includes a `metadata_assessment` object:

- `assessment_id`: stable label plus LCATS story ID plus generation timestamp.
- `label`: `gutenberg_metadata_rules`.
- `generated_at`: UTC timestamp for this run.
- `scope`: `gutenberg_volume`, because Gutenberg subjects often describe a
  source volume that contributed multiple LCATS story buckets.
- `method`: method name/version and pipeline name/version.
- `provenance`: LCATS story identity plus Gutenberg/cache provenance.
- `evidence.raw_subjects`: Gutenberg subject strings read from the cache.
- `evidence.raw_rule_matches`: every matching rule label with matched patterns.
- `result.target_candidates`: direct mappings into the 8 LCATS target genres.
- `result.suggestive_target_candidates`: non-direct but useful target hints,
  currently `Crime` as suggestive evidence for `mystery`.
- `result.secondary_signals`: matching non-target metadata labels retained for
  audit rather than collapsed into ground truth.

Direct target-label normalization:

- `SF` -> `science fiction`
- `Fantasy` -> `fantasy`
- `Horror` -> `horror`
- `Mystery` -> `mystery`
- `Western` -> `western`
- `Adventure` -> `adventure`
- `Romance` -> `romance`
- `Humor / satire` -> `humor`

## Current Boundary

This experiment does not write `genre.json` sidecars into `data/` or
`corpora/`, promote sidecars, modify `lcats annotate`, modify `lcats promote`,
run local or remote models, run full-corpus metadata labeling for commit, or
implement the larger 100-200 story sample. Those remain later workstream steps
after the 40-story metadata pilot path is reviewed.

The reusable `genre-sidecar-v1` validator now lives in
`lcats.analysis.corpus.genre_sidecar`. It validates the production sidecar
shape and detects legacy flat `AssessmentResult.to_dict()` genre sidecars, but
this experiment still remains experiment-local and does not materialize or
promote production `genre.json` files.
