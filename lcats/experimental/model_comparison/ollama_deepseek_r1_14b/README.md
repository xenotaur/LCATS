# ollama_deepseek_r1_14b

Second open-weight family (offline) candidate for `model_comparison/`
(`WI-LLM-0056`, tranche 1) - `deepseek-r1:14b` via
`lcats.llm.openai_backend.OpenAIBackend` pointed at Ollama's
OpenAI-compatible endpoint, the same pattern `ollama_qwen3_8b` uses.

## Research context

The WI's own research named DeepSeek V4 and GLM-5.2 as the two candidates
with genuine current signal for this cell. Re-verified at implementation
time against Ollama's actual model registry
(`https://ollama.com/library/deepseek-v4-flash`,
`https://ollama.com/library/glm-5.2`): both only offer `:cloud` tags -
Ollama-hosted cloud inference, not locally-runnable weights. Neither fits
this WI's "offline" requirement. `deepseek-r1:14b` is the real,
locally-runnable DeepSeek-lineage candidate that fits this session's Mac
(9.0GB manifest size) - a genuinely distinct architecture/training
lineage from the already-tested Qwen3 family, satisfying this cell's
intent even though the specific model differs from the WI's original
placeholder name.

## Setup

```bash
python setup.py
```

Checks Ollama is reachable and `deepseek-r1:14b` is pulled
(`ollama pull deepseek-r1:14b`, ~9.0GB). Does not pull it itself.

## Run

```bash
python benchmark.py
```

Runs the ERW pipeline's actual stage-3 entity-extraction tool-schema call
against the same real ~600-word scene/sequel segment `anthropic_opus`
uses (`../common/sample_segment.json`), with `max_tokens=8192`.

## Status (`WI-LLM-0056`)

**Pending.** The `ollama pull deepseek-r1:14b` download was interrupted
by unreliable network conditions at implementation time and has not yet
been re-run to completion. `setup.py`/`benchmark.py` are ready; no
`results.json` exists yet because the model was never fully pulled. Run
`ollama pull deepseek-r1:14b` followed by `python benchmark.py` once on a
reliable connection to produce a real result. Note: DeepSeek-R1 is a
reasoning-distilled model (produces `<think>` chain-of-thought content
before its final answer, similar to Qwen3's thinking mode) - if the
default `temperature=0.2` (inherited from `entity_extractor.py`'s
Anthropic/OpenAI-tuned default) produces unreliable results, check
`ollama show deepseek-r1:14b --parameters` for the model's own
recommended sampling settings before assuming a temperature override is
needed, matching the pattern `ollama_qwen3_8b/benchmark.py` established
for Qwen3.
