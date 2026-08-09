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

## Actual results (`WI-LLM-0056`)

**Failed consistently (2/2).** Both runs came back `finish_reason='stop'`
with **no tool call at all** - the exact `tool_choice` forced-function-name
gap `WI-LLM-0051` characterized on the segmentation stage, now reproduced
on entity extraction too:

| Run | Result | Latency | Output tokens |
|---|---|---|---|
| 1 | failed (`no_tool_call`) | 310.1s | 4208 |
| 2 | failed (`no_tool_call`) | 544.1s | 7528 |

Both runs' free-text `content` visibly *begins* a schema-shaped JSON
object matching `extract_entities`'s expected structure - but
`OpenAIBackend.complete()` truncates this content to 2000 characters
before raising, and both committed `results_run*.json` files cut off
mid-object (`raw_output_preview` is also `None` on this failure path, so
no fuller capture exists). Neither committed artifact can establish that
the *full* response would have been well-formed or complete - only that
the visible prefix is schema-shaped (review finding, PR #273; the same
caveat `WI-LLM-0050`'s segmentation README already applies to an
identical truncation situation). This
model was also markedly slower than every other candidate tested in this
tranche (5-9x `anthropic_opus`'s latency on the identical call), and run 2
took noticeably longer than run 1 while producing more output tokens for
essentially the same (never-materializing) answer - no retry-with-reminder
mitigation (`WI-LLM-0051`'s finding) was attempted here, out of this
tranche's own scope (Non-Goals: no quality/mitigation comparison, only
call-success/latency/entity-count).
