# ollama_gemma4_12b

Gemma-offline candidate for `model_comparison/` (`WI-LLM-0056`, tranche 1)
- `gemma4:12b` (Google's open-weight lineage - Gemini itself has no open
weights) via `lcats.llm.openai_backend.OpenAIBackend` pointed at Ollama's
OpenAI-compatible endpoint, the same pattern `ollama_qwen3_8b` uses.

## Setup

```bash
python setup.py
```

Checks Ollama is reachable and `gemma4:12b` is pulled
(`ollama pull gemma4:12b`, ~7.6GB). Does not pull it itself.

## Run

```bash
python benchmark.py
```

Runs the ERW pipeline's actual stage-3 entity-extraction tool-schema call
against the same real ~600-word scene/sequel segment `anthropic_opus`
uses (`../common/sample_segment.json`), with `max_tokens=8192`.

## Status (`WI-LLM-0056`)

**Pending.** The `ollama pull gemma4:12b` download was interrupted by
unreliable network conditions at implementation time (94% complete before
failing with a connection error) and has not yet been re-run to
completion. `setup.py`/`benchmark.py` are ready; no `results.json` exists
yet because the model was never fully pulled. Run `ollama pull
gemma4:12b` followed by `python benchmark.py` once on a reliable
connection to produce a real result.
