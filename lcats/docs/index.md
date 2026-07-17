# LCATS docs index

This page is the entry point for LCATS human-facing documentation.

## Project execution root

Run LCATS commands from the nested execution root:

```bash
cd LCATS/lcats
```

## Diátaxis map

### Tutorials

Tutorials are not scaffolded in this phase.

### How-to guides

- [Set up API keys](secrets-setup.md)
- [Run `lcats assess`](../lcats/analysis/corpus/README.md#9-story-assessment-lcats-assess) — usage, manual prompt validation, and dry-run guidance (interim location; pending extraction into `docs/how-to/` in a future phase)
- [Prepare a corpora release](reference/prepare-corpora-release.md) — manual, agent-free runbook: clear, regenerate, verify, and promote `data/` into `corpora/`

### Reference

- [CLI status matrix](reference/cli-status.md)
- [Corpus promotion (`lcats promote`)](reference/corpus-promotion.md) — command reference and collection-name mapping

### Explanation

- Control-plane concepts live in [`project/README.md`](../project/README.md).
- Corpus-analysis architecture details live in [`lcats/analysis/corpus/README.md`](../lcats/analysis/corpus/README.md).
