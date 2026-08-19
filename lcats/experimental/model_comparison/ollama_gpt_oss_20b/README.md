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

## Follow-up: full 3-run vetting across all three stages (`WI-LLM-0063`)

`WI-LLM-0063` ran genre detection and segmentation for the first time
against this candidate, and added a 3rd entity-extraction run, bringing
every stage up to this lineage's 3-run evidence bar.

### Genre detection - 3/3 success

`benchmark_genre.py`, `results_genre_run{1,2,3}.json`:

| Run | Result | Latency | Output tokens | Genre |
|---|---|---|---|---|
| 1 | success | 40.5s | 395 | mystery |
| 2 | success | 8.3s | 365 | mystery |
| 3 | success | 13.5s | 584 | mystery |

3/3 success, all correctly detected `mystery`. Latency dropped sharply
after run 1 (40.5s -> 8-14s) - plausibly Ollama's model-load warmup on
the first call of a fresh session, not a per-call cost. **Verdict:
genre detection is reliable for this candidate**, matching
`ollama_qwen3_8b`'s own "hybrid-viable" finding for this stage.

### Entity extraction - 3/3 success, high variance

`benchmark.py`, `results_run{1,2,3}.json` (run 1/2 from `WI-LLM-0056`,
run 3 new):

| Run | Result | Latency | Output tokens | Entities |
|---|---|---|---|---|
| 1 | success | 37.8s | 1065 | 12 |
| 2 | success | 35.1s | 1516 | 21 |
| 3 | success | 169.8s | 5514 | 34 |

3/3 success, but real, substantial variance in both latency (35-170s,
~4.5x spread) and entity count (12-34, ~3x spread) that the original
2-run sample did not reveal. This is consistent with (not contradicting)
the "succeeds reliably" verdict - `success` never flipped to failure -
but the entity-count spread is wide enough that a single run's count
should not be treated as representative; no ground-truth precision/recall
check was run to determine whether run 3's 34 entities reflects genuinely
more thorough extraction or over-generation/duplication (out of this
tranche's Non-Goals). **Verdict: entity extraction remains reliable
(3/3), but with real output/entity-count variance across runs** - not a
quality finding, since no ground-truth check was run - that a future
precision/recall-focused item should characterize before trusting any
single run's entity count as representative.

### Segmentation - 0/3, a new failure mode distinct from silent-ignore

`benchmark_segmentation.py`, `results_segmentation_run{1,2,3}.json`.
`run_segmentation()` defaults `retry_with_reminder=True`, so each of
these 3 calls already includes the automatic `WI-LLM-0051` reminder retry
when the baseline fails via `no_tool_call`:

| Run | Baseline | Retry | Final error | Latency\* |
|---|---|---|---|---|
| 1 | `no_tool_call` | tool called, content produced | `alignment failed for segment_id=1: anchor text not found in story text` | 147.3s |
| 2 | `no_tool_call` | tool called, content produced | `alignment failed for segment_id=1: anchor text not found in story text` | 257.4s |
| 3 | `no_tool_call` | tool called, content produced | `alignment failed for segment_id=2: anchor text not found in story text` | 148.2s |

\* `run_segmentation()`'s retry wrapper has the same known,
pre-existing resource-accounting gap `WI-LLM-0062` found and fixed in
`run_entity_extraction()` but explicitly left unfixed here as
out-of-scope (see that WI's Follow-up) - the latency/token figures above
are the **retry call's own numbers only**, undercounting each run's true
total (baseline + retry) resource use.

All 3 runs show the same two-stage pattern: the baseline call ignores
`tool_choice` entirely (the familiar silent-ignore mechanism), but
`WI-LLM-0051`'s reminder is effective enough to get the retry to actually
invoke the tool - unlike `gemma4:12b`/`deepseek-r1:14b`, where the
reminder sometimes fails to produce a call at all. The retry's tool call
then fails a *downstream* check: the segmenter's own alignment validation
rejects a segment whose anchor text is a paraphrase or hallucination
rather than a verbatim substring of the source story. This is a
**genuinely new failure mode** for this tranche - distinct from both the
`tool_choice`-ignored mechanism (`gemma4:12b`, `deepseek-r1:14b`) and the
active filter-rejection mechanism (`gemini_flash`) `WI-LLM-0062`
characterized; it happens *after* the tool is successfully called, in
the segmenter's own answer-validation step. **Verdict: segmentation is
not viable for this candidate (0/3)**, consistent with every other local
candidate tested on this stage (`qwen3:8b`, `qwen3:30b-a3b`: 0/5
baseline) - the reminder mitigation changes *how* it fails (silent-ignore
-> alignment rejection) but does not produce a usable result.

### Overall verdict

`gpt-oss:20b` is a strong candidate for genre detection (3/3) and looked
promising for entity extraction at the raw tool-call level (3/3, with
real output/entity-count variance not yet precision/recall
characterized), but **not viable for segmentation** (0/3, same as every
other local model tested on this stage in this tranche) - the pipeline's
segmentation stage remains an Anthropic-only stage for now, independent
of which local model is chosen for the other two.

## Best-config/grounding follow-up (`WI-LLM-0064`)

`WI-LLM-0064` tested whether the prior `gpt-oss:20b` findings were
unfairly pessimistic because the harness was still using the shared
Anthropic/OpenAI-tuned defaults. The local installation's bundled Ollama
parameters report `temperature 1`, so the follow-up added candidate-local
scripts at that setting and recorded diagnostics that the prior harness
did not preserve:

- `benchmark_entity_bestconfig.py` - 3 entity-extraction runs at
  `temperature=1.0`, recording both raw tool-result counts and the
  production `build_entities()` grounded counts.
- `benchmark_segmentation_bestconfig.py` - 3 segmentation runs at
  `temperature=1.0`, plus 3 runs at `temperature=1.0` with an explicit
  verbatim-anchor reminder, recording pre-alignment `start_exact`/
  `end_exact` strings.

### Entity extraction best-config - raw success, grounding failure

`results_entity_bestconfig.json`,
`results_entity_bestconfig_run{1,2,3}.json`:

| Run | Result | Latency | Output tokens | Raw entities | Grounded entities | Grounded mentions |
|---|---|---:|---:|---:|---:|---:|
| 1 | raw tool success | 44.6s | 1464 | 11 | 0 | 0 |
| 2 | raw tool success | 49.8s | 1904 | 11 | 0 | 0 |
| 3 | raw tool success | 110.8s | 3403 | 13 | 0 | 0 |

The API/tool-call layer worked 3/3, but every run emitted `mentions` as
plain strings (for example `"Sherlock Holmes"`) rather than the mention
objects expected by `build_entities()`. The new grounded diagnostic
therefore reports 0 grounded entities and 0 grounded mentions in all
three runs, with item-level errors checked into the per-run JSON.

**Verdict: entity extraction is not production-usable in its current
shape.** `gpt-oss:20b` remains interesting because it calls the tool
reliably and produces plausible raw names, but it needs a targeted
prompt/schema/output-handling follow-up before it should be treated as a
real ERW entity-extraction candidate. The earlier "3/3 success" verdict
should be read as raw tool-call success only, not downstream grounded
entity success.

### Segmentation best-config - still 0/3 usable

`results_segmentation_bestconfig.json`,
`results_segmentation_bestconfig_temperature_1_run{1,2,3}.json`,
`results_segmentation_bestconfig_verbatim_quote_reminder_run{1,2,3}.json`:

| Variant | Runs | Result | Latency range | Output-token range | Failure mode |
|---|---:|---|---:|---:|---|
| `temperature_1` | 3 | 0/3 | 126.5-175.1s | 4246-5610 | no tool call; schema-shaped JSON in message content |
| `verbatim_quote_reminder` | 3 | 0/3 | 99.8-127.2s | 2220-4164 | 2 alignment failures with captured bad anchors; 1 no tool call/refusal |

The verbatim-anchor reminder improved observability and partially changed
the failure mode, but did not produce a usable segmentation result. In
two runs the model called `record_segments`, yet the captured anchors show
why the production aligner rejected the output: ellipses, invented text,
case drift, and paraphrased boundary strings such as
`"...to illustrate."` or a fabricated paragraph-start sentence were not
verbatim substrings of the story.

**Verdict: segmentation remains not viable for `gpt-oss:20b`.**
`temperature=1.0` and an explicit verbatim-anchor reminder are not enough
to rescue the stage through the OpenAI-compatible Ollama path.

### Updated recommendation

- **Prefer for genre detection only**, where the prior 3/3 result remains
  clean and cheap.
- **Consider for entity extraction only as a follow-up target**, not as a
  production-ready local replacement, because raw entities are not
  grounded by the production builder.
- **Do not consider for segmentation** under the current harness/API
  shape; the fairer best-config test stayed 0/6 usable across the two
  variants.

## Production-grounded entity follow-up (`WI-LLM-0065`)

`WI-LLM-0065` tested the specific malformed entity shapes committed by
`WI-LLM-0064` against the production grounding path, rather than counting
raw tool-call success as usable entity extraction. The follow-up added:

- `entity_shape_adapter.py` - a candidate-scoped compatibility adapter
  for observed `gpt-oss:20b` shapes only. It repairs string entities,
  `name`/`entity` aliases, string mentions, and mention objects using
  `text`/`surface` instead of `quote` only when the candidate text is
  already a verbatim substring of the segment. It does not fabricate
  spans or weaken `build_entities()`.
- `benchmark_entity_production_grounded.py` - 3 live local
  `gpt-oss:20b` runs at `temperature=1.0`, passing the candidate output
  through the adapter before the unchanged production
  `build_entities()` call. The harness also has an opt-in
  no-tool-call JSON-content fallback for Ollama-style schema-shaped
  message content; the final 3-run pass did not need that fallback
  (`json_content_fallback_count=0`), but the path is unit-tested.

`results_entity_production_grounded.json`,
`results_entity_production_grounded_run{1,2,3}.json`:

| Run | Tool call | Fallback used | Latency | Output tokens | Raw entities | Grounded entities | Grounded mentions |
|---|---|---|---:|---:|---:|---:|---:|
| 1 | yes | no | 71.8s | 2038 | 14 | 12 | 13 |
| 2 | yes | no | 140.6s | 4196 | 13 | 11 | 12 |
| 3 | yes | no | 70.8s | 2637 | 16 | 16 | 18 |

**Verdict: entity extraction is production-grounded with the
candidate-scoped adapter, but not strong enough to prefer as a default.**
The adapter successfully converts known malformed shapes into real
`build_entities()` inputs without weakening quote grounding, and the
final pass produced 3/3 production-grounded successes. Quality and speed
remain uneven enough to require follow-up: grounded entity counts ranged
from 11 to 16, and latency ranged from 71s to 141s on the same segment.

### Updated recommendation after `WI-LLM-0065`

- **Prefer for genre detection**, where the prior 3/3 result remains the
  cleanest local use case.
- **Consider for entity extraction only behind the candidate-scoped
  adapter**, with follow-up precision/recall evaluation before any
  production default or routing change.
- **Do not consider for segmentation** under the current harness/API
  shape; the best-config segmentation runs remain 0/6 usable.

## Genre-census scale-test follow-up (`WI-LLM-0066`)

`WI-LLM-0066` tested whether genre detection's clean single-story result
holds at multi-story, multi-genre pilot scale (a 20-story sample, not the
full ~1,868-story corpus, which has not run for any candidate), by
wiring `experiments/04_genre_census/run_census.py` to this candidate via
a new opt-in `--base-url` flag and running the same 20-story
population-weighted sample already used for the Claude reference run.
Full detail and per-story disagreements:
`experiments/04_genre_census/README.md`'s "Local gpt-oss:20b Sample
(2026-08-13)" section.

- **18/20 exact `detected_genre` agreement** against the Claude sample
  (after normalizing one non-canonical `science_fiction` ->
  `science fiction` output). No stories excluded, no `secondary_genre`
  corruption observed.
- **$0.00 measured API cost**, 801.5s wall clock for 20 stories
  (~40.1s/story) - projecting to **~20.8 hours** for the full
  ~1,868-story corpus, versus the Claude sample's ~4.2-hour projection at
  ~$435 (a projection from this pilot's per-story rate, not a measured
  full-corpus run for either candidate).
- The 2 disagreements were both on stories the Claude sample labeled
  `humor` (`gpt-oss:20b` said `science fiction` once and `other` once) -
  a disagreement against another model's output, not a validated error,
  and the Claude sample itself only carried 3 `humor`-labeled stories
  total, too few to distinguish a systematic weak spot from sample noise.

**Verdict: go for a full local genre census**, if a roughly one-day local
run is acceptable and zero API spend is the priority - but treat this
pilot as a cost-free first-pass signal, not final ground truth; review
the humor disagreements (against real labels, not just Claude's output)
before relying on the counts. This confirms the earlier single-story
"hybrid-viable" signal holds at pilot multi-story, multi-genre scale,
closing the scale-evidence gap the original 3-run
vetting (`WI-LLM-0063`) explicitly left open.
