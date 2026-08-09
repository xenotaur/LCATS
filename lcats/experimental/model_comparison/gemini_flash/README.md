# gemini_flash

Gemini online candidate for `model_comparison/` (`WI-LLM-0056`, tranche 1)
- `gemini-3.5-flash` via `lcats.llm.openai_backend.OpenAIBackend` pointed
at Google's documented OpenAI-compatible endpoint
(`https://generativelanguage.googleapis.com/v1beta/openai/`,
[Google AI for Developers](https://ai.google.dev/gemini-api/docs/openai)).
No separate backend class needed.

## Setup

```bash
python setup.py
```

Checks the `openai` package is installed (used as the client SDK against
Google's compat endpoint) and `GEMINI_API_KEY` is set (env var or
`.secrets/gemini-api-key.env`, from
[Google AI Studio](https://aistudio.google.com/apikey)). Makes no API
calls.

## Run

```bash
python benchmark.py
```

Makes **one real** API call against Gemini's OpenAI-compat endpoint: the
ERW pipeline's actual stage-3 entity-extraction tool-schema call
(`lcats.analysis.event_role_world.entity_extractor`) against the same real
~600-word scene/sequel segment `anthropic_opus` uses
(`../common/sample_segment.json`), with `max_tokens=8192`.

Writes `results.json` in this directory. See `../benchmark_summary.py` to
compare against other candidates.

## Actual results (`WI-LLM-0056`)

**Failed consistently (2/2), and this is the real spike run this WI's Risk
Notes anticipated might be needed** - forced `tool_choice` through
Gemini's OpenAI-compat endpoint does not work for `ENTITY_TOOL_SCHEMA`'s
shape. Both committed runs (`results_run1.json`/`results.json`) returned
`finish_reason: 'function_call_filter: MALFORMED_FUNCTION_CALL'` - Gemini
itself pre-emptively rejects the model's attempted function call as
malformed, before it ever reaches this harness as a usable tool result -
at ~59-60s latency and 4000-4400 output tokens burned per attempt (the
model generates a real, substantial response; Gemini's own filter is what
discards it).

**Diagnostic (not committed as a candidate result):** tested whether
`ENTITY_TOOL_SCHEMA`'s `strict: true` flag (Anthropic-style strict
function-calling, forwarded to OpenAI's function-level `strict` field by
`openai_backend.py`) was the trigger, since OpenAI-compat layers don't
always support every OpenAI-native feature. With `strict` disabled and the
full real segment, the identical `MALFORMED_FUNCTION_CALL` failure
recurred - ruling out `strict: true` specifically as the cause. (An
earlier attempt with `strict: false` against an artificially truncated
~2000-char segment instead hit a token-budget truncation rather than the
filter - an artifact of the much shorter/simpler input, not evidence
`strict: false` fixes anything; not treated as a real data point.)

**Verdict: no working Gemini candidate lands in this tranche.** The
failure is systemic across both `strict` settings against the real
segment - most likely `ENTITY_TOOL_SCHEMA`'s nested shape (per-entity
`quotes` array of objects, multiple enum/array fields) triggering
Gemini's own function-call validation filter, not an `openai_backend.py`
wiring issue (the identical schema/call path works against
`anthropic_opus`/`ollama_qwen3_8b`). Root-causing the exact schema
property that triggers Gemini's filter (or testing a substantially
simplified schema) is out of this tranche's scope - documented here as a
real, reproducible negative finding per this work item's own acceptance
criteria, not silently dropped.
