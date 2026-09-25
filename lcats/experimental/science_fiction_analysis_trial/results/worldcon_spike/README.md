# Worldcon Spike Captures

These experiment-local captures use the same deterministic 10-story sample
from `WI-SF-0012`. They are comparison artifacts, not corpus annotations.

This directory is being preserved as a historical experiment record before the
next evidence-boundary hardening iteration. The captures are not a
preregistration, accuracy validation, human annotation set, or authorization
to run the 146-story sample.

## Captures

- `opus_10_20260824/`: Anthropic `claude-opus-4-8`, temporarily authorized up to
  `$5.00`; 8 complete story records and 2 story-level failures.
- `local_gpt_oss_20b_10_20260824/`: Ollama `gpt-oss:20b` through the local
  OpenAI-compatible endpoint; 9 complete story records and 1 story-level
  failure.

Each capture includes its run manifest, smoke prerequisite, summary, report,
per-story JSONL results, run log, raw stage responses, quarantines,
checkpointed assembly, and published experiment-local sidecars.

## Preservation Boundary

Included here:

- the two completed 10-story experiment captures listed above;
- their raw model responses and quarantined outputs;
- their per-story results, run logs, manifests, summaries, and reports;
- the experiment-local sidecars emitted by those runs.

Kept separate from this archival change:

- unfinished prompt and runner changes in `run_worldcon_spike.py`;
- unfinished test changes in `worldcon_spike_test.py`;
- generated repository logs under `lcats/logs/`;
- corpus data, production annotations, and promotion outputs.

The captured manifests retain the original model, backend, prompt version,
token configuration, output root, and approval metadata. Results should be
read as feasibility evidence and debugging material only; later code changes
must not silently rewrite these historical outputs.
