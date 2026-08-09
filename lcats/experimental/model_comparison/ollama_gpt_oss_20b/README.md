# ollama_gpt_oss_20b

OpenAI-offline candidate for `model_comparison/` (`WI-LLM-0056`, tranche 1)
- `gpt-oss:20b` (OpenAI's Apache 2.0 open-weight release, native Ollama
MXFP4 support - [Ollama Blog](https://ollama.com/blog/gpt-oss)) via
`lcats.llm.openai_backend.OpenAIBackend` pointed at Ollama's
OpenAI-compatible endpoint, the same pattern `ollama_qwen3_8b` uses.

## Setup

```bash
python setup.py
```

Checks Ollama is reachable and `gpt-oss:20b` is pulled
(`ollama pull gpt-oss:20b`, ~13.8GB). Does not pull it itself.

## Run

```bash
python benchmark.py
```

Runs the ERW pipeline's actual stage-3 entity-extraction tool-schema call
(`lcats.analysis.event_role_world.entity_extractor`) against the same real
~600-word scene/sequel segment `anthropic_opus` uses
(`../common/sample_segment.json`), with `max_tokens=8192`. Free to run
repeatedly once the model is pulled - no per-call API cost.

Writes `results.json` in this directory. See `../benchmark_summary.py` to
compare against other candidates.

## Actual results (`WI-LLM-0056`)

**Succeeded consistently (2/2)**, and fast:

| Run | Result | Latency | Output tokens | Entities |
|---|---|---|---|---|
| 1 | success | 37.8s | 1065 | 12 |
| 2 | success | 35.1s | 1516 | 21 |

Both runs comfortably beat `ollama_qwen3_8b`'s latency (74-106s) on the
identical call, and run 2 matched `anthropic_opus`'s exact entity count
(21) - a real, favorable early signal for this candidate, though 2 runs
is not enough to call it reliable at `qwen3:8b`'s scale of evidence (3
runs across every stage) or to draw a precision/recall conclusion (out of
this tranche's Non-Goals). Notably no `gpt-oss`-family `<think>`/reasoning
artifacts or the tool-call reliability issues Qwen3 showed on
segmentation appeared in these two runs, but that stage hasn't been
tested against this candidate yet.
