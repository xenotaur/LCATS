# anthropic_haiku

Second Anthropic tier candidate for `model_comparison/` (`WI-LLM-0056`,
tranche 1) - `claude-haiku-4-5` via
`lcats.llm.anthropic_backend.AnthropicBackend`, the cheaper/faster tier
alongside `anthropic_opus`'s frontier baseline.

## Setup

```bash
python setup.py
```

Checks the `anthropic` package is installed and `ANTHROPIC_API_KEY` is set
(env var or `.secrets/anthropic_api_keys.env`). Makes no API calls.

## Run

```bash
python benchmark.py
```

Makes **one real, billable** Anthropic API call: the ERW pipeline's actual
stage-3 entity-extraction tool-schema call
(`lcats.analysis.event_role_world.entity_extractor`) against the same real
~600-word scene/sequel segment `anthropic_opus` uses
(`../common/sample_segment.json`), with `max_tokens=8192`.

Writes `results.json` in this directory. See `../benchmark_summary.py` to
compare against other candidates.

## Actual results (`WI-LLM-0056`)

One real run at implementation time: **success**, 27.9s latency, 2729
output tokens, 20 entities extracted - versus `anthropic_opus`'s (proposal
doc) 49.3s/5439 output tokens/21 entities on the identical segment. Haiku
matched Opus's entity count almost exactly at roughly half the latency and
token spend, on this single sample - a real, favorable cost/latency
tradeoff worth tracking across more samples/stages, but not yet a
quality-verified recommendation (no precision/recall check, per this
tranche's own Non-Goals).
