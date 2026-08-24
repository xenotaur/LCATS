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

## Worldcon Spike

`WI-SF-0012` adds a separate Worldcon-focused spike runner for the urgent
Knight/Novum feasibility question. It is still experiment-local and does not
write to corpus buckets or promotion paths.

Run the no-cost 2-3 story smoke:

```bash
PYTHONPATH=src python experimental/science_fiction_analysis_trial/run_worldcon_spike.py \
  --mode smoke \
  --backend fake \
  --output-root experimental/science_fiction_analysis_trial/results/worldcon_spike
```

The 5-10 story sample mode requires a successful smoke summary:

```bash
PYTHONPATH=src python experimental/science_fiction_analysis_trial/run_worldcon_spike.py \
  --mode sample \
  --backend fake \
  --smoke-summary experimental/science_fiction_analysis_trial/results/worldcon_spike/worldcon_spike_summary.json \
  --output-root /tmp/lcats-worldcon-sample
```

Paid backends require both a reviewed manifest/approval change and the explicit
`--approve-paid` flag. Full 146-story mode additionally requires
`--approve-full-sample` and a successful smoke summary.
