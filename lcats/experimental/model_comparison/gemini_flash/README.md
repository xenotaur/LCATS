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

**Verdict (as of `WI-LLM-0056`): no working Gemini candidate lands in this
tranche.** The failure is systemic across both `strict` settings against
the real segment - most likely `ENTITY_TOOL_SCHEMA`'s nested shape
(per-entity `quotes` array of objects, multiple enum/array fields)
triggering Gemini's own function-call validation filter, not an
`openai_backend.py` wiring issue (the identical schema/call path works
against `anthropic_opus`/`ollama_qwen3_8b`). Root-causing the exact schema
property that triggers Gemini's filter (or testing a substantially
simplified schema) is out of this tranche's scope - documented here as a
real, reproducible negative finding per this work item's own acceptance
criteria, not silently dropped.

## Follow-up: the schema-complexity hypothesis was wrong - it's a token budget (`WI-LLM-0062`)

`WI-LLM-0062` tested the schema-complexity hypothesis above directly, by
running a minimal, flat, single-field tool schema (`list_character_names`
- one array of plain strings, no nesting, no enums) against the identical
real segment. `benchmark_minimal_schema.py` runs this - a diagnostic
probe against a synthetic schema, not a durable ERW-pipeline candidate,
so it doesn't go through `common.harness.run_entity_extraction()` and
writes its own small result file rather than a `BenchmarkResult`-shaped
one. **3/3 succeeded immediately**, at just `max_tokens=2048`
(`results_minimal_schema_run{1,2}.json` and `results_minimal_schema.json`
for the 3rd/latest run).

That result alone doesn't prove schema complexity is irrelevant - a
minimal schema also means a much shorter expected output, so it could
still be a token-budget effect rather than a schema-shape effect. To
isolate the variable, re-ran the **full, real `ENTITY_TOOL_SCHEMA`** -
unchanged from `benchmark.py` - at increasing `max_tokens`. The 8192/16384
rows are single direct calls to `common.harness.run_entity_extraction()`
at the stated `max_tokens` override (not wrapped in their own committed
script, since they're supplementary context for the primary 32000-token
finding, not the finding itself) -
`results_entity_8192_retest.json`/`results_entity_16384.json`. The 32000
rows are `benchmark_full_schema_32k.py`, run 3 times -
`results_entity_32k_run{1,2}.json` and `results_entity_32k.json` for the
3rd/latest run:

| `max_tokens` | Result | Output tokens | Entities |
|---|---|---|---|
| 8192 (original tranche 1 setting) | fresh re-run: **`truncated_output`**, not `MALFORMED_FUNCTION_CALL` (see below) | 3214 | - |
| 16384 | failed (`truncated_output`) | 4589 | - |
| 32000 (run 1) | **success** | 4468 | 22 |
| 32000 (run 2) | **success** | 4051 | 9 |
| 32000 (run 3) | **success** | 5392 | 19 |

**Verdict: the original `MALFORMED_FUNCTION_CALL` hypothesis (schema
complexity triggers Gemini's own validation filter) is not supported by
this evidence - reclassifying as an open, corrected finding rather than
letting the original hypothesis stand unchallenged.** The *same* full
`ENTITY_TOOL_SCHEMA`, unmodified, succeeds reliably (3/3) once given
enough `max_tokens` headroom (32000) - it is not permanently, structurally
rejected by Gemini's filter the way the original write-up concluded. A
fresh re-run at the original 8192 setting today failed with
`truncated_output` rather than reproducing the original
`MALFORMED_FUNCTION_CALL` signal at all - suggesting Gemini 3.x's
"thinking"/reasoning token consumption (which shares the same `max_tokens`
budget as the visible completion) is the real constraint, and which
specific API-level failure surfaces (a content filter rejecting an
incomplete/malformed partial call vs. a plain length cutoff) may itself be
somewhat non-deterministic depending on exactly where generation gets cut
off - not a stable, reproducible signature of "this schema is rejected."
This does not fully resolve *why* 8192-16384 tokens are insufficient for
this specific schema+segment (that would need further probing this WI's
own scope doesn't cover), but it does overturn the "systemic content-filter
rejection" framing the original tranche 1 write-up committed to.
