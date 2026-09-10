# Worldcon Spike Captures

These experiment-local captures use the same deterministic 10-story sample
from `WI-SF-0012`. They are comparison artifacts, not corpus annotations.

## Captures

- `opus_10_20260824/`: Anthropic `claude-opus-4-8`, temporarily authorized up to
  `$5.00`; 8 complete story records and 2 story-level failures.
- `local_gpt_oss_20b_10_20260824/`: Ollama `gpt-oss:20b` through the local
  OpenAI-compatible endpoint; 9 complete story records and 1 story-level
  failure.

Each capture includes its run manifest, smoke prerequisite, summary, report,
per-story JSONL results, run log, raw stage responses, quarantines,
checkpointed assembly, and published experiment-local sidecars.
