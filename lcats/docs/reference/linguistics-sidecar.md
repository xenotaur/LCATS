# Linguistic sidecar schema

`lcats linguistics` writes local NLP-derived analysis artifacts for an LCATS
story bucket's canonical `story.json`. By default, artifacts are written beside
the source story; with `--output-root`, they are redirected under an explicit
output root.

The default artifact is `linguistics.json`, a compact story-level sidecar using
`schema_version: linguistics-sidecar-v1`. When token detail is explicitly
enabled, the command also writes `linguistics.tokens.json` using
`schema_version: linguistics-token-detail-v1`.

Both artifacts are deterministic JSON: UTF-8, sorted keys, two-space
indentation, and a trailing newline. LCATS publishes them atomically by writing
a temporary file in the same directory and replacing the target after the write
completes.

When redirected, output paths use the LCATS story identity as a directory path:
`<output-root>/<collection>/<story>/linguistics.json`. Token detail, when
requested, uses the same directory. The sidecar's `story_path` and
`input.source_path` fields continue to describe the analyzed source
`story.json`, not the redirected artifact location.

## `linguistics.json`

`linguistics.json` is the default aggregate sidecar. It intentionally excludes
token and dependency rows so story buckets do not grow large unless detailed
output is requested.

Top-level fields:

| Field | Type | Description |
|---|---|---|
| `schema_version` | string | Always `linguistics-sidecar-v1`. |
| `lcats_id` | string | Stable story identity derived from the story bucket path, usually `<collection>/<story>`. |
| `story_path` | string | Serialized path to the analyzed `story.json`, preserving the invocation spelling as POSIX-style separators. |
| `extractor` | object | Extractor provenance. |
| `backend` | object | NLP backend provenance. |
| `input` | object | Source-text provenance used for reproducibility checks. |
| `options` | object | Effective options that affect extraction. |
| `metrics` | object | Aggregate story-level linguistic metrics. |

### `extractor`

| Field | Type | Description |
|---|---|---|
| `name` | string | Extractor package name, currently `lcats.analysis.linguistics`. |
| `version` | string | Extractor contract version, currently `v1`. |

### `backend`

| Field | Type | Description |
|---|---|---|
| `name` | string | NLP backend selected by `--backend`: `spacy`, `stanza`, or `fake`. |
| `model` | string | Requested model name or language code. Defaults are recorded when known. |
| `package_version` | string | Installed backend package version when available, otherwise empty. |

### `input`

| Field | Type | Description |
|---|---|---|
| `body_sha256` | string | SHA-256 hash of the analyzed story body text. |
| `body_char_count` | integer | Character count of the analyzed story body text. |
| `source_path` | string | Serialized path to the analyzed `story.json`, preserving the invocation spelling as POSIX-style separators. |

### `options`

| Field | Type | Description |
|---|---|---|
| `backend_name` | string | Effective backend name. |
| `model_name` | string | Requested model name or language code, or empty for backend default. |
| `include_token_detail` | boolean | Whether this run requested the separate token-detail artifact. |

### `metrics`

| Field | Type | Description |
|---|---|---|
| `word_count` | integer | Word count from the shared surface-feature extractor. |
| `sentence_count` | integer | Sentence count from the selected NLP backend. |
| `token_count` | integer | Count of normalized token records returned by the backend. |
| `avg_sentence_length` | number | Average words per sentence. |
| `avg_word_length` | number | Average word length. |

## `linguistics.tokens.json`

`linguistics.tokens.json` is written only when `--include-token-detail` is set.
It carries the same provenance envelope as `linguistics.json`, but its
`schema_version` is `linguistics-token-detail-v1` and it replaces `metrics`
with `tokens`.

Top-level fields:

| Field | Type | Description |
|---|---|---|
| `schema_version` | string | Always `linguistics-token-detail-v1`. |
| `lcats_id` | string | Same story identity as the compact sidecar. |
| `story_path` | string | Same serialized story path as the compact sidecar. |
| `extractor` | object | Same extractor provenance as the compact sidecar. |
| `backend` | object | Same backend provenance as the compact sidecar. |
| `input` | object | Same input provenance as the compact sidecar. |
| `options` | object | Same effective options as the compact sidecar. |
| `tokens` | array | Normalized token/dependency records from the NLP backend. |

Token records come from the normalized ERW NLP backend protocol. Each record
has these fixed fields:

| Field | Type | Description |
|---|---|---|
| `text` | string | Surface form. |
| `lemma` | string | Dictionary form, or empty string when unavailable. |
| `upos` | string | Universal part-of-speech tag, or empty string when unavailable. |
| `xpos` | string | Fine-grained or treebank-specific part-of-speech tag, or empty string when unavailable. |
| `feats` | string | Universal Dependencies-style morphological feature string, or empty string when none are available. |
| `head_index` | integer | One-based syntactic-head index within the sentence, or `0` for root. |
| `deprel` | string | Universal dependency relation to the head, or empty string when unavailable. |

## Run Summary

The CLI prints a machine-readable run summary to stdout, or writes it to the
path passed with `--summary-output`.

The run summary uses `schema_version: linguistics-run-summary-v1`.

Top-level fields:

| Field | Type | Description |
|---|---|---|
| `schema_version` | string | Always `linguistics-run-summary-v1`. |
| `backend_name` | string | Effective backend name. |
| `model_name` | string | Requested model name or language code. |
| `existing` | string | Existing-output mode: `skip`, `validate`, or `overwrite`. |
| `include_token_detail` | boolean | Whether token-detail output was requested. |
| `output_root` | string | Present only when `--output-root` was used; records the redirect root for sidecar outputs. |
| `counts` | object | Count of per-story results by status. |
| `results` | array | Per-story outcomes. |

Each result object contains:

| Field | Type | Description |
|---|---|---|
| `story_path` | string | Resolved story path. |
| `sidecar_path` | string | Target `linguistics.json` path. |
| `status` | string | One of `written`, `skipped`, `failed`, or `dry_run`. |
| `message` | string | Human-readable outcome or diagnostic. |
| `detail_path` | string | Present only on result objects that carry a token-detail target path. It appears for dry runs, writes, skips, write exceptions, and existing-token-detail validation failures when `--include-token-detail` is set; some failures detected while validating an existing compact sidecar omit it. |

## Fingerprint and Resume Behavior

LCATS compares existing outputs against a reproducibility fingerprint before
skipping or validating them. The fingerprint contains:

- `schema_version`;
- `extractor`;
- `backend`;
- `input`;
- `options`.

Matching outputs are skipped by default. Stale, invalid, unreadable, or
missing detail outputs fail without replacement unless the command is run with
`--existing overwrite`.

Path fields are serialized from the path supplied to the runner; LCATS does
not canonicalize them to an absolute or repository-relative form. Supplying the
same story through different valid spellings can therefore change `story_path`,
`input.source_path`, and the fingerprint even when the story body and backend
configuration are otherwise unchanged.

Output redirection does not change this fingerprint behavior. Existing-output
checks use the redirected target path when `--output-root` is active, but the
fingerprint still describes the source story and extraction configuration.
Within one redirected batch, duplicate output targets are reported as
per-story failures rather than silently overwriting an earlier result.

The token-detail artifact uses its own `linguistics-token-detail-v1`
fingerprint. This keeps compact sidecar resume checks independent from the
optional detailed artifact while still detecting interrupted or stale detail
writes.

## Corpus Status

Linguistic sidecars are local analysis artifacts. `lcats linguistics` can write
them beside stories in a working tree, but PR #325 did not promote generated
linguistic sidecars into `corpora/` or define a release workflow for them.
Corpus-promotion policy for these artifacts remains separate follow-up work.
