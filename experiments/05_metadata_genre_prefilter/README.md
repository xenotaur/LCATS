# Metadata Genre Prefilter

`WI-GENRE-0002` extends the dry-run scaffold from `WI-GENRE-0001` into an
experiment-local metadata-rule evidence pilot. The runner discovers LCATS story
buckets, uses LCATS path identity as the primary story ID, reads Gutenberg
subjects from an explicitly supplied existing SQLite cache in read-only mode,
records all matching metadata genre-rule evidence, and writes a deterministic
40-story pilot manifest (the default mode, below).

`WI-GENRE-0004` adds two further modes on top of that same scan: `--full-scan`
(a full-corpus metadata scan plus a genre-balanced 100-200 story selection,
still free) and `--validate` (a real, gated Claude Opus validation pass
against that selection, see [Validation Pass](#validation-pass-real-gated-claude-opus)).

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

## Full-Corpus Scan and Genre-Balanced Selection

`--full-scan` runs the same discovery/enrichment as the default pilot mode,
but across the entire corpus, and selects a genre-balanced (not
corpus-proportional) sample of `--target-total` stories (default 160,
acceptance range 100-200) distributed evenly across the 8 target genres —
grouped by each story's primary metadata-rule target genre, not by source
collection like the 40-story pilot. No API calls; free.

```bash
python experiments/05_metadata_genre_prefilter/run_prefilter.py \
  --full-scan \
  --corpus-root corpora \
  --cache-db /path/to/existing/gutenbergindex.db \
  --target-total 160 \
  --output experiments/05_metadata_genre_prefilter/results/full_scan
```

Writes `candidates.jsonl` (every discovered story), `genre_balanced_manifest.jsonl`
(the selected sample), and `summary.json` — including `genre_coverage`
(per-genre candidate counts plus a `no_usable_signal_count` for stories with
no metadata match at all), `genre_balanced_selection` (the selection
diagnostics: per-genre selected counts and any shortfalls), and
`estimated_validation_cost_usd` (a rough pre-call estimate for the separate
`--validate` step below). Review the manifest and this estimate before
running `--validate` — selection and validation are deliberately two
separate invocations, not one atomic step.

## Validation Pass (Real, Gated Claude Opus)

`--validate` reads back an existing `genre_balanced_manifest.jsonl` from
`--output` (written by `--full-scan` above) and runs a real Claude Opus
detect-mode classification against just that selected sample — never the
full corpus. Estimate-only by default; **no API calls are made** unless
`--run-real-validation` is also passed, mirroring
`experiments/04_genre_census/run_census.py`'s established cost-gate
convention (never spend real money without an explicit, separate opt-in).

```bash
# 1. Cost estimate only — no API calls, no ANTHROPIC_API_KEY needed.
python experiments/05_metadata_genre_prefilter/run_prefilter.py \
  --validate \
  --output experiments/05_metadata_genre_prefilter/results/full_scan

# 2. Real run — requires ANTHROPIC_API_KEY and explicit go-ahead.
python experiments/05_metadata_genre_prefilter/run_prefilter.py \
  --validate --run-real-validation \
  --output experiments/05_metadata_genre_prefilter/results/full_scan
```

The real run writes `validation_results.jsonl` (one `genre-sidecar-v1`
append-only sidecar record per story — the metadata-rule assessment plus a
new `model_detect` assessment, each validated against
`lcats.analysis.corpus.genre_sidecar.validate_sidecar()` before being
written) and `validation_summary.json` (per-story and aggregate
agreement/disagreement between the metadata rules and the model, an
`agreement_by_genre` breakdown per selected genre — since an aggregate
rate alone can hide one genre's poor coverage behind seven good ones —
plus real measured cost). These sidecar records live under this
experiment's own output directory only — never promoted into `corpora/`,
which remains a separately-gated, unimplemented later step (see Current
Boundary below).

The cost estimate's default per-story token averages (13,449 input / 416
output) are the real measured values from
`experiments/04_genre_census/results/census_sample_summary.json`
(`WI-ASSESS-0051`'s 20-story `claude-opus-4-8` sample), not invented
placeholders — the estimate is the human review gate before real billed
calls, so it must not understate expected spend.

## Outputs

The runner writes only under the requested output directory:

- `candidates.jsonl`: one row per discovered story, keyed by LCATS story ID.
- `pilot_40_manifest.jsonl`: deterministic pilot rows, roughly 10 each from
  `lovecraft`, `sherlock`, O. Henry (`ohenry-four_million` and
  `ohenry-whirligigs`), and `mass_quantities`.
- `summary.json`: story counts, collection counts, cache readiness,
  target-candidate counts, secondary-signal counts, `genre_coverage`
  (per-genre primary-candidate counts plus a no-usable-signal count),
  Gutenberg-ID parse failures, repeated Gutenberg-ID diagnostics, and
  pilot-selection diagnostics. `--full-scan` additionally writes
  `genre_balanced_manifest.jsonl` and adds `genre_balanced_selection`
  and `estimated_validation_cost_usd` to `summary.json` — see
  [Full-Corpus Scan](#full-corpus-scan-and-genre-balanced-selection) above.

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
`corpora/`, promote sidecars, modify `lcats annotate`, or modify
`lcats promote`. Those remain later workstream steps.

`WI-GENRE-0004` implemented the full-corpus scan, the genre-balanced
100-200 story selection, and the real gated Claude Opus validation pass
described above — none of these three were built as of `WI-GENRE-0002`.
`--full-scan` still makes no network/model calls of its own beyond the
same read-only cache access the pilot mode already used; `--validate`'s
real mode is the only path in this experiment that makes billed API
calls, and only against the already-selected sample, never the full
corpus.

The reusable `genre-sidecar-v1` validator lives in
`lcats.analysis.corpus.genre_sidecar` (`WI-GENRE-0003`). It validates the
production sidecar shape and detects legacy flat `AssessmentResult.to_dict()`
genre sidecars; `--validate --run-real-validation` above is this
experiment's first real producer of sidecar-shaped records validated
against it, but this experiment still remains experiment-local and does
not materialize or promote production `genre.json` files under `corpora/`.
