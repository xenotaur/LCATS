# Full-Corpus Linguistics Run

This experiment runs the standalone `lcats linguistics` pipeline over every
current canonical story in `corpora/`.

The run is intentionally experiment-local. The linguistics runner writes
`linguistics.json` beside each input `story.json`, so this experiment first
copies each story bucket into
`experiments/07_linguistics_corpora/results/copied_buckets/` and analyzes the
copies. The result is a snapshot of both the input story buckets and the
generated compact linguistic sidecars that produced the run report.

Generated sidecars must not be written into `corpora/`.

## Inputs

- Source stories: `corpora/<collection>/<story>/story.json`
- Source snapshot: discovered `story.json` paths are sorted deterministically.
  Full runs copy every discovered story bucket before analysis begins; smoke
  runs copy only the selected `--smoke-count` prefix while recording both the
  full discovered count and selected count in `snapshot_manifest.json`.

The checked-in full run records the source commit and story hashes in
`results/snapshot_manifest.json`, so later corpus changes do not silently
change the provenance of a resumed run.

## Outputs

The default output root is `experiments/07_linguistics_corpora/results/`.

- `copied_buckets/` - experiment-local mirror of corpus story buckets, with
  generated `linguistics.json` sidecars beside copied `story.json` files.
- `story-list.txt` - relative paths to copied story files.
- `snapshot_manifest.json` - pre-analysis source/copy inventory with commit
  and `story.json` hashes.
- `linguistics_run_summary.json` - machine-readable `lcats linguistics` run
  summary.
- `experiment_report.json` - script-level report with counts, elapsed time,
  backend/model, copied-bucket size, failures, and no-corpus-write checks.

## Local Setup

The full run uses local NLP only. No paid API calls are made.

```bash
python -m pip install -e "lcats[nlp]"
python -m spacy download en_core_web_sm
```

Run a small smoke pass first:

```bash
python experiments/07_linguistics_corpora/run_linguistics_corpora.py \
  --backend spacy \
  --smoke-count 5 \
  --overwrite
```

Run the full corpus:

```bash
python experiments/07_linguistics_corpora/run_linguistics_corpora.py \
  --backend spacy \
  --overwrite
```

Resume an interrupted full run without replacing the source snapshot:

```bash
python experiments/07_linguistics_corpora/run_linguistics_corpora.py \
  --backend spacy \
  --resume
```

For deterministic test fixtures, use `--backend fake` against a fixture corpus
root rather than a real spaCy model.

## Validation

```bash
python experiments/07_linguistics_corpora/run_linguistics_corpora_test.py
python experiments/07_linguistics_corpora/run_linguistics_corpora.py --backend fake --smoke-count 2 --overwrite
python experiments/07_linguistics_corpora/run_linguistics_corpora.py --backend spacy --smoke-count 5 --overwrite
python experiments/07_linguistics_corpora/run_linguistics_corpora.py --backend spacy --overwrite
find corpora -path '*linguistics.json' -o -path '*linguistics.tokens.json' | wc -l
find experiments/07_linguistics_corpora/results/copied_buckets -name linguistics.json | wc -l
scripts/format --check --diff
scripts/lint
scripts/test
lrh validate
```

Run package checks from `lcats/`.

## Promotion Boundary

The sidecars produced here are experiment artifacts. Promoting linguistic
sidecars into the main corpus, if desired later, is a separate workflow and
must not be inferred from this experiment.
