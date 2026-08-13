# Metadata Genre Prefilter

`WI-GENRE-0001` creates the dry-run scaffold for the genre evidence sidecar
workstream. The scaffold validates LCATS story identity, Gutenberg ID parsing,
cache readiness reporting, and experiment-local manifest output before any
metadata-rule assessment, model call, human adjudication, corpus sidecar, or
promotion behavior is added.

## No-Network Default

The runner is deliberately read-only. It does not import
`lcats.gettenberg.cache`, does not call `ensure_gutenberg_cache()`, and does
not build, download, refresh, or repair the Gutenberg metadata cache. Missing
cache state is reported in the summary instead of being fixed automatically.

## Usage

From the repository root:

```bash
python experiments/05_metadata_genre_prefilter/run_prefilter.py \
  --dry-run \
  --output experiments/05_metadata_genre_prefilter/results/smoke
```

Optional inputs:

```bash
python experiments/05_metadata_genre_prefilter/run_prefilter.py \
  --corpus-root corpora \
  --cache-db /path/to/existing/gutenbergindex.db \
  --output experiments/05_metadata_genre_prefilter/results/smoke
```

If `--cache-db` is omitted, the runner checks
`$LCATS_CACHE_DIR/gutenbergindex.db`, or `cache/gutenbergindex.db` when
`LCATS_CACHE_DIR` is unset. This is only a filesystem preflight; sync an
existing local Gutenberg cache into place before using it for later metadata
enrichment work.

## Outputs

The runner writes only under the requested output directory:

- `manifest.jsonl`: one row per story, keyed by LCATS story ID. Gutenberg ID
  and URL are provenance fields only.
- `summary.json`: story counts, collection counts, cache readiness,
  Gutenberg-ID parse failures, and repeated Gutenberg-ID diagnostics.

The LCATS story ID is the corpus-root-relative story bucket path, such as
`sherlock/five_orange_pips`. Repeated Gutenberg IDs are reported as collection
or volume-level diagnostics, not as story identity.

## Current Boundary

This scaffold stops before generating metadata-rule genre assessments. The
next work item can layer `lcats.utils.genre` rule evidence on top once the
cache location and dry-run artifact shape are reviewed.
