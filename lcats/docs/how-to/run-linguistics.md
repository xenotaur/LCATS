# Run `lcats linguistics`

`lcats linguistics` analyzes LCATS story buckets with a local NLP backend and
writes a compact, deterministic `linguistics.json` sidecar beside each
`story.json` by default.

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

Redirect sidecars away from source buckets:

```bash
lcats linguistics --story-list sample.txt \
  --output-root experiments/my_linguistics_run/results/sidecars \
  --summary-output experiments/my_linguistics_run/results/summary.json
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

Write the richer sentence-nested token-detail v2 artifact instead of the
backward-compatible v1 shape:

```bash
lcats linguistics corpora/sherlock/five_orange_pips \
  --backend spacy \
  --include-token-detail \
  --token-detail-version v2
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
`linguistics.tokens.json`. The default token-detail schema is
`linguistics-token-detail-v1` for backward compatibility. Pass
`--token-detail-version v2` to write `linguistics-token-detail-v2`, which nests
tokens under sentence records and includes stable sentence/token indices,
source character offsets, backend capabilities, and model/config provenance.

By default, both artifacts are written beside the analyzed `story.json`. With
`--output-root`, LCATS writes them under the explicit root using the story
identity as the path: `<output-root>/<collection>/<story>/linguistics.json`
and, when requested, `<output-root>/<collection>/<story>/linguistics.tokens.json`.
The sidecar provenance still records the source story path and body hash for
the analyzed input.

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

## Copied Buckets vs. Output Root

Use copied-bucket experiment mirrors when the artifact should preserve the
exact story files that produced the output, as in the `WI-GENRE-0004` sample
run. Use `--output-root` when you only need generated linguistic sidecars and
run summaries separated from source buckets.

If two inputs resolve to the same LCATS story identity, redirected batch runs
fail the later duplicate result instead of overwriting the first sidecar.

## Deferred Work

This command is the generic infrastructure layer. Follow-up work remains for:

- measuring performance over long stories;
- defining any later corpus-promotion workflow for linguistic sidecars.
