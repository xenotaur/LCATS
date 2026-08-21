# Run `lcats linguistics`

`lcats linguistics` analyzes LCATS story buckets with a local NLP backend and
writes a compact, deterministic `linguistics.json` sidecar beside each
`story.json`.

The command is NLP-only. It does not call an LLM, does not use paid APIs, and
does not depend on the future `WI-GENRE-0004` balanced-sample manifest.

## Setup

Run commands from the LCATS package root:

```bash
cd LCATS/lcats
```

Install the optional NLP dependencies if your environment does not already
have them:

```bash
pip install -e ".[nlp]"
```

For spaCy, install the model you plan to use:

```bash
python -m spacy download en_core_web_sm
```

For Stanza, download the language model:

```bash
python -c "import stanza; stanza.download('en')"
```

## Examples

Analyze one story bucket:

```bash
lcats linguistics corpora/sherlock/five_orange_pips --backend spacy
```

Analyze a collection or corpus root:

```bash
lcats linguistics corpora/sherlock --backend spacy
lcats linguistics corpora --backend stanza --model en
```

Use a plain story-list file:

```bash
lcats linguistics --story-list sample.txt --summary-output linguistics-run.json
```

Preview which stories would run:

```bash
lcats linguistics corpora/sherlock --dry-run
```

Include detailed token/dependency records in a separate artifact:

```bash
lcats linguistics corpora/sherlock/five_orange_pips \
  --backend spacy \
  --include-token-detail
```

## Output

The default sidecar is `linguistics.json`. It uses
`schema_version: linguistics-sidecar-v1` and records:

- LCATS story identity and source path.
- Extractor name/version.
- NLP backend name, model, and package version when available.
- Input provenance including SHA-256 body hash and body character count.
- Effective options.
- Aggregate story-level metrics: word count, sentence count, token count,
  average sentence length, and average word length.

Full token/dependency records are intentionally not stored in
`linguistics.json`. When `--include-token-detail` is set, they are written to
`linguistics.tokens.json`.

JSON output is serialized deterministically with sorted keys and a trailing
newline. File publication is atomic: LCATS writes a temporary file in the same
directory and replaces the target only after the write completes.

## Existing Output

By default, existing matching `linguistics.json` files are skipped after schema
validation and fingerprint comparison. The fingerprint includes schema version,
extractor version, backend provenance, input body hash, and relevant options.

Use these modes for existing sidecars:

- `--existing skip` — default; skip matching output and fail on stale/invalid
  output.
- `--existing validate` — validate and report whether existing output matches;
  stale output fails without replacement.
- `--existing overwrite` — recompute and replace existing output.

Batch runs isolate failures per story and return a machine-readable JSON
summary on stdout or at `--summary-output`. See the
[linguistic sidecar schema reference](../reference/linguistics-sidecar.md)
for exact sidecar, token-detail, and run-summary fields.

## Deferred Work

This command is the generic infrastructure layer. Follow-up work remains for:

- a thin `WI-GENRE-0004` manifest adapter once that manifest lands;
- running the selected Worldcon sample;
- measuring performance over long stories;
- defining any later corpus-promotion workflow for linguistic sidecars.
