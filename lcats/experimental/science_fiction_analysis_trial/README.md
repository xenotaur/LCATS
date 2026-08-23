# Science-Fiction Analysis Trial

This directory contains the Phase 1F no-cost experiment runner for the
Knight/Novum science-fiction sidecar workstream.

The runner is intentionally experiment-local. It writes only to an explicit
`--output-root`, refuses protected `data/` and `corpora/` roots through the
shared checkpoint guard, and supports only the fixture backend with
`estimated_cost_usd` equal to `0.0`. Paid model execution, corpus publication,
annotation commands, promotion commands, and Phase 2/3 pilots are outside this
runner's scope.

## Usage

From `lcats/`:

```bash
PYTHONPATH=src python experimental/science_fiction_analysis_trial/run_trial.py \
  --manifest experimental/science_fiction_analysis_trial/fixtures/manifest.json \
  --output-root /tmp/lcats-sf-trial \
  --dry-run
```

Run the no-cost fixture trial:

```bash
PYTHONPATH=src python experimental/science_fiction_analysis_trial/run_trial.py \
  --manifest experimental/science_fiction_analysis_trial/fixtures/manifest.json \
  --output-root /tmp/lcats-sf-trial \
  --resume
```

The output root receives published `science-fiction.json` sidecars under the
fixture `lcats_id` paths, checkpoint files keyed by deterministic case slugs,
and a byte-stable `run_summary.json`.
