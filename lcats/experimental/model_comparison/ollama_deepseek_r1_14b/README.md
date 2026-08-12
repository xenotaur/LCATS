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

## Follow-up: reminder-retry and temperature tested, neither helped (`WI-LLM-0062`)

`WI-LLM-0062` tested both untested variables named above. Note: `ollama
show deepseek-r1:14b --parameters` reports only `stop` tokens - Ollama's
bundled Modelfile for this model does **not** override temperature the
way `qwen3:8b`'s does, so the harness's `temperature=0.2`
(Anthropic/OpenAI-tuned default, inherited from `entity_extractor.py`) was
genuinely never overridden by anything model-specific before this test.

**Reminder-retry mitigation, 3 real runs** (`benchmark_entity_reminder.py`,
`results_entity_reminder_run{1,2,3}.json`) at the same default settings.
Latency/token totals below are baseline+retry combined (a review finding,
PR #277, caught that an earlier version of this harness's retry wrapper
reported only the retry call's own numbers, discarding the failed
baseline attempt's real resource use - fixed in `common/harness.py`, and
these 3 runs were regenerated after the fix):

| Run | Baseline result | Retry result | Latency (both calls) |
|---|---|---|---|
| 1 | failed (`no_tool_call`) | failed (`no_tool_call` again) | 172.6s |
| 2 | failed (`no_tool_call`) | failed (`no_tool_call` again) | 206.6s |
| 3 | failed (`no_tool_call`) | failed (`no_tool_call` again) | 263.4s |

**Temperature test, 1 run** (`temperature=0.6`, no reminder,
`results_entity_temperature_test.json`): also failed (`no_tool_call`,
166.9s).

**Verdict: neither mitigation helped this candidate.** 3/3 baseline
failures, 3/3 reminder-retry failures (0% recovery, unlike
`ollama_gemma4_12b`'s partial 1/2 recovery under the same mechanism), and
a tuned temperature alone didn't change the outcome either. In every
failure, the model explains its reasoning in prose (sometimes with
Python-style pseudocode, sometimes a raw JSON code block) instead of
actually invoking the tool - it consistently understands the task and can
even produce schema-shaped content, but never emits a real function/tool
call regardless of the reminder or temperature tried here. This is a
more robust, harder-to-mitigate instance of the silent-ignore mechanism
than `gemma4:12b` showed - a real, negative finding, not an inconclusive
one (per this proposal lineage's evidence-quality standard: a documented
"tried, didn't work" is a valid, complete result).
