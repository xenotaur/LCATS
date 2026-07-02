# LCATS Experiments

This directory contains completed and in-progress experiments that document
research runs for the LCATS project, including results, analysis scripts, and
the data needed to reproduce each run.

## Convention

Experiments are numbered in the order they were conducted:

```
experiments/
    01_classify_corpora/       ← first experiment
    02_llm_backend_comparison/ ← second experiment
    ...
```

The number prefix serves two purposes:
1. **Chronological order at a glance** — newer experiments have higher numbers,
   making it easy to see what's recent and what's historical.
2. **Stable references** — scripts and papers can cite `02_llm_backend_comparison`
   and the path won't change as new experiments are added.

When adding a new experiment, take the next available number. Do not renumber
existing experiments.

## What lives here vs. in `lcats/`

| Asset | Location | Why |
|---|---|---|
| Experiment results (JSONL, TSV, CSV) | `experiments/NN_name/results/` | Output artifacts — versioned here for reproducibility |
| Experiment scripts (`run_*.py`, `compare_*.py`, `smoke_test.py`) | `experiments/NN_name/` | Tightly coupled to the results they produce; live with the experiment |
| Reusable library code (`assess.py`, `LLMBackend`, etc.) | `lcats/lcats/` | Part of the distributable package; used by many experiments |
| Development data (small, in-progress corpora) | `lcats/data/` | Under active iteration; not yet curated for release |
| Released corpora | `corpora/` | Curated, stable; referenced by experiments |
| Exploratory notebooks | `lcats/notebooks/` | Numbered the same way (`01_`, `02_`, …); tend to precede formal experiments |

## Experiments

| # | Name | Description |
|---|---|---|
| 01 | `01_classify_corpora` | Classify stories across corpora by genre and quality |
| 02 | `02_llm_backend_comparison` | Side-by-side Anthropic vs. OpenAI backend comparison on the assess pipeline |
