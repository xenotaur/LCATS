# LCATS docs index

This page is the entry point for LCATS human-facing documentation.

## Project execution root

Run LCATS commands from the nested execution root:

```bash
cd LCATS/lcats
```

## Diátaxis map

### Tutorials

- [Quickstart](tutorials/quickstart.md) — from a fresh clone to your first working `lcats` command

### How-to guides

- [Set up API keys](secrets-setup.md)
- [Secrets hygiene: responding to and preventing leaked API keys](how-to/secrets-hygiene.md)
- [Run `lcats assess`](how-to/run-assess.md) — modes, manual prompt validation, and dry-run guidance
- [Prepare a corpora release](reference/prepare-corpora-release.md) — manual, agent-free runbook: clear, regenerate, verify, and promote `data/` into `corpora/`
- [Run the cross-segment relation density pilot](../../experiments/03_cross_segment_relation_pilot/running_the_pilot.md) — manual runbook: environment setup, zero-cost smoke testing (including spaCy/Stanza), the real run (safely resumable after a crash or interrupt via per-stage checkpointing), and closing out the work item

### Reference

- [CLI status matrix](reference/cli-status.md)
- [CLI command reference](reference/cli-commands.md) — flags and arguments for every `lcats` subcommand
- [LLMBackend reference](reference/llm-backend.md) — the `LLMBackend` Protocol and its providers
- [Corpus promotion (`lcats promote`)](reference/corpus-promotion.md) — command reference and collection-name mapping

### Explanation

- [Why stories live in per-story bucket directories](explanation/story-bucket-layout.md) — the storage-layout migration, what changed, and why
- Control-plane concepts live in [`project/README.md`](../project/README.md).
- Corpus-analysis architecture details live in [`lcats/analysis/corpus/README.md`](../src/lcats/analysis/corpus/README.md).
