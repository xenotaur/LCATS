# ollama_qwen3_8b

Local-model candidate for `model_comparison/` - `qwen3:8b` served locally by
[Ollama](https://ollama.com), driven through the existing
`lcats.llm.openai_backend.OpenAIBackend` (via its `base_url` parameter,
pointed at Ollama's OpenAI-compatible `/v1` endpoint) rather than a new
backend class.

Sized for ~8GB of RAM/VRAM headroom - the "cheap tier" candidate a hybrid
pipeline (local model for genre detection/segmentation, frontier model for
extraction) would use. See `../ollama_qwen3_30b_a3b/` for the
"quality tier" MoE candidate - now tested (`WI-LLM-0049`): it did **not**
turn out to be a reliable upgrade over this candidate, both slower and
less consistent on the identical call.

## Setup

```bash
brew install ollama
ollama serve            # or open the Ollama app
ollama pull qwen3:8b    # ~5GB download
python setup.py         # verifies the above
```

## Run

```bash
python benchmark.py               # stage 3: entity extraction
python benchmark_genre.py         # genre detection (detect mode)
python benchmark_segmentation.py  # scene/sequel segmentation
```

`benchmark.py` runs the ERW pipeline's real stage-3 entity-extraction
tool-schema call against a real ~600-word scene/sequel segment
(`../common/sample_segment.json` - see `../common/generate_sample_segment.py`
for how it was produced), `temperature=0.6` (Qwen3's own recommended value
- see "Methodology fix" below), `max_tokens=8192`. No API cost once the
model is pulled. Writes `results.json` in this directory (the most recent
run; see `results_segment_run1.json`/`run2.json`/`run3.json` for three real
runs against the corrected methodology, and
`results_fullstory_run1_failed.json`/`results_fullstory_run2_succeeded.json`
for the two runs against the prior, oversized whole-story input - kept for
transparency, not representative of current results).

`benchmark_genre.py` and `benchmark_segmentation.py` (`WI-LLM-0050`) cover
the two "comparatively simple" stages the hybrid-pipeline hypothesis names
- see "Actual results: genre detection and segmentation" below. Both run
against the whole sample story (`../common/harness.py`'s
`DEFAULT_SAMPLE_STORY`), not a segment - genre detection and segmentation
both operate over a full story in the real pipeline. Write
`results_genre.json`/`results_segmentation.json` respectively; see
`results_genre_run1.json`/`run2.json` and
`results_segmentation_run1.json`/`run2.json` for the real runs behind the
table below.

## What this tests

Whether Ollama's grammar-constrained JSON-schema decoding (XGrammar-backed
since Ollama 0.3+) actually produces a valid, schema-conformant
`extract_entities` tool call for a real story segment - the same question
Categories A-C of
`project/audits/2026-07-27-erw-pipeline-structured-output-reliability-audit.md`
raised for hosted backends, now asked of a local one. A local model
excelling at conversational chat but failing this call (empty/malformed
`tool_result`, wrong entity count, hallucinated schema fields) would rule
it out for the pipeline's extraction stages specifically, even if it's fine
for lighter stages like genre detection.

## Methodology fix (this candidate's first two runs were measuring the wrong thing)

The first two runs against this candidate (`results_fullstory_run1_failed.json`,
`results_fullstory_run2_succeeded.json`) sent the model the **entire**
~7,300-word source story instead of a single segment, at
`temperature=0.2` - a setting inherited from `entity_extractor.py`'s
Anthropic/OpenAI-tuned default, well below Qwen3's own official
recommendation (0.6 thinking-mode / 0.7 non-thinking - see
[Qwen3-8B's model card](https://huggingface.co/Qwen/Qwen3-8B), which
explicitly warns **"Do NOT use greedy decoding, as it can lead to
performance degradation and endless repetitions"**) and below Ollama's
own bundled default for this model (`ollama show qwen3:8b --parameters`
reports `temperature 0.6, top_k 20, top_p 0.95` - i.e. our own explicit
`temperature=0.2` was overriding an already-correct default). Both
issues are fixed as of this candidate's current `benchmark.py`/`../common/harness.py`.

## Actual results: genre detection and segmentation (`WI-LLM-0050`)

Real runs against `../common/harness.py`'s `run_genre_detection()`/
`run_segmentation()`, both at `temperature=0.6` against the whole sample
story (`corpora/sherlock/five_orange_pips/story.json`):

| Stage | Run | Result | Latency | Output tokens | Detail |
|---|---|---|---|---|---|
| genre_detection | 1 | success | 84.9s | 423 | detected_genre=mystery |
| genre_detection | 2 | success | 25.4s | 498 | detected_genre=mystery |
| segmentation | 1 | **failed** | 383.0s | 5089 | tool never invoked (`no_tool_call`) |
| segmentation | 2 | **failed** | 157.8s | 2560 | tool never invoked (`no_tool_call`) |

Segmentation's output token counts are real, billed usage - not zero
despite the failed call - via `lcats.llm.backend.NoToolCallError`
(review finding, PR #249: `OpenAIBackend`/`AnthropicBackend`'s
forced-`tool_choice`-ignored path previously discarded the provider's
own usage report, which made these two runs read as "0 output tokens"
even though the model generated thousands of tokens of free text).

**Genre detection succeeded consistently (2/2)**, correctly identifying
"mystery" both times, at latencies well below the entity-extraction
stage. This is real evidence for the hybrid-pipeline hypothesis's
easier-stage half.

**Segmentation failed consistently (2/2)** - not an outright refusal or
gibberish: both responses came back as `finish_reason='stop'` with the
model's free-text `content` beginning a well-formed, schema-shaped JSON
object matching `SEGMENT_TOOL_SCHEMA`'s field names/structure for its
first two segments (see `results_segmentation_run1.json`/`run2.json`'s
`error_message` for the captured text), but the OpenAI-compatible
`tool_choice` never actually invoked `record_segments`. **Caveat on this
evidence:** `OpenAIBackend.complete()` truncates the captured content to
2000 characters before raising (visible in both files - the captured text
cuts off mid-object, inside segment 2's fields), so neither the full
response nor its completeness/full conformance can actually be confirmed
from what's committed - only that the visible portion is schema-shaped,
not that the whole response was (review finding, PR #249). This is still
the exact `tool_choice` forced-function-name gap flagged as a residual
risk in `PROP-ERW-LOCAL-MODEL-EVALUATION`'s Decision 3 update and named as
`WI-LLM-0051`'s own investigation target - now reproduced directly on a
second, harder-schema stage, not just theorized. Segmentation's tool
schema is substantially larger/more nested (GACD/ERAC classification,
per-segment anchors) than entity extraction's, which may explain why
`tool_choice` fails here but not there - not conclusively diagnosed,
left to `WI-LLM-0051`.

### Follow-up: `tool_choice` reliability investigation (`WI-LLM-0051`)

A 3rd run at the identical `(qwen3:8b, five_orange_pips)` config, plus
two more varying model/story (baseline, `retry_with_reminder=False`, all
committed as real runnable evidence, not prose-only):

| Config | Result | Latency | Output tokens | Detail |
|---|---|---|---|---|
| `qwen3:8b` / `five_orange_pips` (run 3) | **failed** | 193.7s | 1972 | `no_tool_call` |
| `qwen3:8b` / `engineers_thumb` (`benchmark_segmentation_engineers_thumb.py`) | **failed** | 340.7s | 4518 | `no_tool_call` |
| `qwen3:30b-a3b` / `five_orange_pips` (`../ollama_qwen3_30b_a3b/benchmark_segmentation.py`) | **failed** | 268.2s | 5459 | `no_tool_call` |

**Baseline: 0/5 total segmentation attempts succeeded** across 2 models
and 2 stories, including 3 independent samples at the identical config -
a systemic gap, not intermittent noise.

**Retry mitigation - actually tested, not inferred from resampling
alone:** an earlier draft of this investigation reasoned from the 3
identical-config baseline repeats that a retry had "no observed chance"
of helping - **that reasoning was corrected after review.** Repeating
the identical request only tests whether `temperature=0.6` resampling
changes the outcome; it doesn't test the WI's own named mitigation - an
explicit reminder appended to the system prompt. Tested directly: 5 live
calls at the identical `(qwen3:8b, five_orange_pips)` config with
`"CRITICAL INSTRUCTION: You MUST call the record_segments function/tool
..."` appended to the system prompt. **2/5 succeeded (40%)** - real,
substantial, though not reliable.

`../common/harness.py`'s `run_segmentation()` now implements this as an
automatic retry-once path (`retry_with_reminder=True` by default),
triggered only when the first attempt fails with `error_type=
"no_tool_call"`. Verified end-to-end with a real live call:
`results_segmentation.json` (this candidate's canonical "latest run"
file) now reflects that call - `success: true, retry_attempted: true,
retry_succeeded: true, segment_count: 4` - the first attempt failed
exactly as before, the automatic retry succeeded. The pre-retry-code
baseline failures remain preserved separately in
`results_segmentation_run1.json` through `run3.json` and the two varied-
condition files above, so the 0/5 baseline evidence isn't lost just
because the "latest" file now shows a retry-assisted success.

See `PROP-ERW-LOCAL-MODEL-EVALUATION`'s "Decision 3 update (2026-08-08,
`tool_choice` reliability investigation, `WI-LLM-0051`)" section for the
full verdict, including what remains open (why the reminder only helps
40% of the time rather than reliably, and whether it would help the real
production `SCENE_SEQUEL_SYSTEM_PROMPT` - flagged as a candidate
follow-up, not investigated here).

## Actual results: entity extraction

**Fixed methodology (real segment, `temperature=0.6`), 3 runs:**

| Run | Result | Latency | Output tokens | Entities |
|---|---|---|---|---|
| 1 | success | 74.4s | 1477 | 11 |
| 2 | success | 100.3s | 2318 | 13 |
| 3 | success | 105.7s | 2301 | 14 |

`../anthropic_opus/` on the identical segment: success, 49.3s, 5439
output tokens, 21 entities. So on the corrected methodology, `qwen3:8b`
succeeds consistently (3/3) at roughly **1.5-2.2x** Opus's latency, with
lower recall (11-14 vs. 21 entities - not evaluated for precision here,
see Non-Goals) - a real cost/latency tradeoff, not the outright
unreliability the prior methodology suggested.

**Prior methodology (whole story, `temperature=0.2`), for comparison -
not representative of current results:**

- Run 1: **failed** - `finish_reason='stop'` with no tool call at all,
  despite `tool_choice` forcing `extract_entities`.
- Run 2: **succeeded**, but took 1727s (~29 minutes) generating 7996
  output tokens before finally producing a valid call.

This reversal is itself the finding: the original "qwen3:8b is
unreliable" conclusion in
`project/design/proposals/proposed/erw-local-model-evaluation/00_proposal.md`
was substantially an artifact of benchmarking against the wrong input
size and an unsuited sampling temperature, not a stable property of the
model. See that proposal's "Update" section for the corrected
conclusion. One remaining, unfixed candidate cause of the *original*
run 1's total non-call: community reports on Ollama's own GitHub
(e.g. [issue #4386](https://github.com/ollama/ollama/issues/4386))
describe gaps in how Ollama's OpenAI-compatible `tool_choice` forces a
specific function name - not reproduced across 3 fixed-methodology runs
here, but not ruled out as a residual risk either.
