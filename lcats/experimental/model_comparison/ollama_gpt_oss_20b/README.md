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

`gpt-oss:20b` is a strong candidate for genre detection (3/3) and entity
extraction (3/3, with real output/entity-count variance not yet
precision/recall characterized), but **not viable for segmentation** (0/3, same as every
other local model tested on this stage in this tranche) - the pipeline's
segmentation stage remains an Anthropic-only stage for now, independent
of which local model is chosen for the other two.
