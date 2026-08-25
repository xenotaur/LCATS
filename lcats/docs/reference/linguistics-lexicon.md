# Linguistic lexicon schema

`lcats linguistics --include-lexicon` writes `linguistics.lexicon.json`, a
deterministic materialized view derived from `linguistics-token-detail-v2`.
The artifact is regenerable and is not an independently editable source of
truth. Use the v2 token-detail artifact for audit evidence, source offsets,
dependency records, and provenance.

Lexicon output is opt-in and requires:

```bash
lcats linguistics STORY_OR_BUCKET \
  --include-token-detail \
  --token-detail-version v2 \
  --include-lexicon
```

With `--output-root`, the lexicon is redirected beside the compact sidecar and
token detail under `<output-root>/<collection>/<story>/`. LCATS publishes the
file with the same deterministic JSON settings as other linguistic artifacts:
UTF-8, sorted keys, two-space indentation, trailing newline, and atomic replace
within the target directory.

## Top-Level Fields

| Field | Type | Description |
|---|---|---|
| `schema_version` | string | Always `linguistics-lexicon-v1`. |
| `lcats_id` | string | Same story identity as the source token-detail artifact. |
| `story_path` | string | Same serialized story path as the source token-detail artifact. |
| `source_token_detail` | object | Fingerprint and provenance copied from the v2 token-detail artifact. |
| `derivation` | object | LCATS derivation identity and generation policy. |
| `denominators` | object | Token, sentence, and lexical-row denominators. |
| `counts` | array | Sorted lexical count rows keyed by surface, lemma, and UPOS. |

## Source Linkage

`source_token_detail` links the materialized view to its source:

| Field | Type | Description |
|---|---|---|
| `schema_version` | string | Always `linguistics-token-detail-v2`. |
| `sha256` | string | SHA-256 hash of the canonical source token-detail JSON. |
| `lcats_id` | string | Source story identity. |
| `story_path` | string | Source story path. |
| `extractor` | object | Extractor provenance from token detail. |
| `backend` | object | Backend provenance from token detail. |
| `input` | object | Source-text provenance from token detail. |
| `options` | object | Effective token-detail options. |

Validation with the source token-detail artifact checks this fingerprint and
requires exact regeneration, so changing the v2 source invalidates the lexicon.

## Derivation

`derivation` records:

| Field | Type | Description |
|---|---|---|
| `name` | string | `lcats.analysis.linguistics.lexicon`. |
| `version` | string | Derivation contract version, currently `v1`. |
| `generation_policy` | string | Always `no_stopword_or_pos_filtering`. |

Stopword inclusion, noun-family selection, top-N cutoffs, genre selectors, and
chart policies are query-time choices. They are not baked into the generated
artifact.

## Denominators

| Field | Type | Description |
|---|---|---|
| `token_count` | integer | Count of all source v2 token rows. |
| `sentence_count` | integer | Count of source v2 sentence rows. |
| `lexical_row_count` | integer | Number of unique `(surface, lemma, upos)` count rows. |

`token_count` must equal the sum of all row counts, and
`lexical_row_count` must equal the number of count rows.

## Count Rows

Each row has:

| Field | Type | Description |
|---|---|---|
| `surface` | string | Token surface form from v2 `text`. |
| `lemma` | string | Token lemma from v2, preserving empty strings when unavailable. |
| `upos` | string | Universal POS tag from v2. |
| `count` | integer | Non-negative count for the exact tuple. |

Rows are sorted by `(surface, lemma, upos)` and must be unique. Summing rows by
`surface`, `lemma`, or `upos` reproduces raw surface, lemma, `NOUN`, and
`PROPN` totals without rescanning every token row.

## Query Helper And Benchmark

`lcats.analysis.linguistics.lexicon.LexiconIndex` builds reusable lookup maps
from one lexicon artifact:

- `surface_count(surface)`;
- `lemma_count(lemma)`;
- `upos_count(upos)`;
- `tuple_count(surface, lemma, upos)`.

`benchmark_queries(data, queries)` reports representative indexed lookup
metadata, including token rows, lexicon rows, estimated row visits for repeated
token scans, indexed row visits, elapsed nanoseconds, and query results. The
benchmark is local evidence that repeated comparison queries can use the
materialized view instead of scanning full token-detail rows repeatedly.

## Resume Behavior

When `--include-lexicon` is set and a matching compact sidecar already exists,
the runner also requires:

- an existing matching `linguistics.tokens.json` in v2 format; and
- an existing `linguistics.lexicon.json` that validates against that token
  detail and exactly regenerates from it.

Missing, stale, unreadable, invalid, or non-regenerating lexicon outputs fail
without replacement unless the run uses `--existing overwrite`.
