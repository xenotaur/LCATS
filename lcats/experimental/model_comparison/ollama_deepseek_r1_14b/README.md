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

## Actual results (`WI-LLM-0056`)

**Failed consistently (2/2).** Both runs came back `finish_reason='stop'`
with **no tool call at all** - the same `tool_choice` gap `ollama_gemma4_12b`
and `WI-LLM-0051`'s segmentation investigation both showed:

| Run | Result | Latency | Output tokens |
|---|---|---|---|
| 1 | failed (`no_tool_call`) | 86.7s | 892 |
| 2 | failed (`no_tool_call`) | 109.8s | 1228 |

Unlike `gemma4:12b`'s JSON-shaped free text, both `deepseek-r1:14b`
responses are plain prose (a numbered list of entities and quoted
mentions, not a JSON object matching `extract_entities`'s schema at all)
- the model understood the extraction task but did not attempt to match
the tool's expected output shape, a different failure signature from the
"schema-shaped but tool never called" pattern seen elsewhere in this
tranche. Notably no `<think>` reasoning-tag content appeared in either
response despite DeepSeek-R1 being a reasoning-distilled model family -
this candidate's own default sampling settings (inherited from
`entity_extractor.py`'s `temperature=0.2`) were not tuned against
`ollama show deepseek-r1:14b --parameters`, unlike `ollama_qwen3_8b`'s
candidate-specific override; whether a tuned temperature or the
`WI-LLM-0051` reminder mitigation would change this outcome is untested,
out of this tranche's own scope (Non-Goals: no quality/mitigation
comparison).
