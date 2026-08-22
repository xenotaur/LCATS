# Linguistics Genre Sample Run

This experiment runs the standalone `lcats linguistics` pipeline over the
146-story `WI-GENRE-0004` genre-balanced sample.

The run is intentionally experiment-local. The current `lcats linguistics`
runner writes `linguistics.json` beside each input `story.json`, so this
experiment first copies sampled story buckets into
`experiments/06_linguistics_genre_sample/results/copied_buckets/` and then
analyzes those copies. Generated sidecars must not be written into `corpora/`.

## Inputs

- Sample manifest:
  `experiments/05_metadata_genre_prefilter/results/full_scan/genre_balanced_manifest.jsonl`
- Source stories:
  `corpora/<collection>/<story>/story.json`

The manifest is read as newline-delimited JSON and must contain `story_id` and
`story_path` fields for each selected row. The checked-in sample currently has
146 rows.

## Outputs

The default output root is `experiments/06_linguistics_genre_sample/results/`.

- `copied_buckets/` - experiment-local mirror of sampled story buckets, with
  generated `linguistics.json` sidecars beside copied `story.json` files.
- `story-list.txt` - relative paths to copied story files.
- `linguistics_run_summary.json` - machine-readable `lcats linguistics`
  run summary.
- `experiment_report.json` - script-level report with sample counts, copied
  bucket counts, backend/model, and no-corpus-write check.

## Local Setup

The full run uses local NLP only. No paid API calls are made.

```bash
python -m pip install -e "lcats[nlp]"
python -m spacy download en_core_web_sm
```

Run a small smoke pass first:

```bash
python experiments/06_linguistics_genre_sample/run_linguistics_sample.py \
  --backend spacy \
  --smoke-count 3 \
  --overwrite
```

Run the full sample:

```bash
python experiments/06_linguistics_genre_sample/run_linguistics_sample.py \
  --backend spacy \
  --overwrite
```

For deterministic test fixtures, use `--backend fake` against a fixture
manifest and corpus root rather than a real spaCy model.

## Validation

```bash
python experiments/06_linguistics_genre_sample/run_linguistics_sample_test.py
scripts/format --check --diff
scripts/lint
scripts/test
lrh validate
```

## Promotion Boundary

The sidecars produced here are experiment artifacts. Promoting linguistic
sidecars into the main corpus, if desired later, is a separate workflow and
must not be inferred from this experiment.
