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
- [Point `OpenAIBackend` at a local OpenAI-compatible endpoint](how-to/local-openai-endpoint.md) — Ollama/vLLM/LM Studio via `base_url`, and which pipeline stages a local model is actually evidenced to be viable for
- [Run `lcats linguistics`](how-to/run-linguistics.md) — local NLP setup, sidecar output, and resumable batch behavior
- [Prepare a corpora release](reference/prepare-corpora-release.md) — manual, agent-free runbook: clear, regenerate, verify, and promote `data/` into `corpora/`
- [Run the cross-segment relation density pilot](../../experiments/03_cross_segment_relation_pilot/running_the_pilot.md) — manual runbook: environment setup, zero-cost smoke testing (including spaCy/Stanza), the real run (safely resumable after a crash or interrupt via per-stage checkpointing), and closing out the work item

### Reference

- [CLI status matrix](reference/cli-status.md)
- [CLI command reference](reference/cli-commands.md) — flags and arguments for every `lcats` subcommand
- [Linguistic sidecar schema](reference/linguistics-sidecar.md) — `linguistics.json`, token-detail, and run-summary fields
- [LLMBackend reference](reference/llm-backend.md) — the `LLMBackend` Protocol and its providers
- [Corpus promotion (`lcats promote`)](reference/corpus-promotion.md) — command reference and collection-name mapping
- [Full-corpus genre census](../../experiments/04_genre_census/README.md) — `lcats assess`'s detect-mode classifier run across the full corpus, with real per-genre counts
- [Metadata genre prefilter](../../experiments/05_metadata_genre_prefilter/README.md) — the metadata-rule evidence pilot backing the genre-balanced corpus selection

### Explanation

- [Why stories live in per-story bucket directories](explanation/story-bucket-layout.md) — the storage-layout migration, what changed, and why
- Control-plane concepts live in [`project/README.md`](../project/README.md).
- Corpus-analysis architecture details live in [`lcats/analysis/corpus/README.md`](../src/lcats/analysis/corpus/README.md).
