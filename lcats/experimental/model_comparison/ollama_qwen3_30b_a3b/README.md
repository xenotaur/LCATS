# ollama_qwen3_30b_a3b

Local-model candidate for `model_comparison/` - `qwen3:30b-a3b`, a
mixture-of-experts model (~30B total / ~3B active parameters) served
locally by [Ollama](https://ollama.com), driven through the existing
`lcats.llm.openai_backend.OpenAIBackend` (via its `base_url` parameter,
pointed at Ollama's OpenAI-compatible `/v1` endpoint) rather than a new
backend class - same mechanism as `../ollama_qwen3_8b/`.

The "quality tier" candidate named in
`../../../project/design/proposals/proposed/erw-local-model-evaluation/00_proposal.md`'s
landscape survey: `ollama_qwen3_8b` (the "cheap tier" candidate) succeeds
consistently on the real stage-3 entity-extraction call but extracts
fewer entities than `../anthropic_opus/` (11-14 vs. 21 on the identical
segment). This candidate tests whether the larger MoE model narrows that
gap at a still-acceptable latency.

## Setup

```bash
brew install ollama          # if not already installed
ollama serve                 # or open the Ollama app
ollama pull qwen3:30b-a3b    # ~18-20GB download - confirm current size first
python setup.py              # verifies the above
```

## Run

```bash
python benchmark.py
```

Runs the ERW pipeline's real stage-3 entity-extraction tool-schema call
against the same real ~600-word segment (`../common/sample_segment.json`)
`anthropic_opus` and `ollama_qwen3_8b` use, at `temperature=0.6`
(confirmed via `ollama show qwen3:30b-a3b --parameters` to match Qwen3's
official sampling recommendation, same as `ollama_qwen3_8b`). No API
cost once the model is pulled. Writes `results.json` in this directory
(the most recent run; see `results_run1.json`/`results_run2.json` etc.
for the individual real runs behind the numbers below, following
`ollama_qwen3_8b`'s convention of keeping every run's result snapshot
rather than only the latest).

A single local-model run is not decision-grade evidence - see
`../ollama_qwen3_8b/README.md`'s "Methodology fix" section and this
repo's own `feedback_local_model_single_run_not_decision_grade` finding
(`qwen3:8b`'s first run against this harness failed outright, while an
identical rerun succeeded at ~8.5x the frontier baseline's latency).
This candidate is run at least twice for the same reason.

## Actual results

**3 real `benchmark.py` runs (`results_run1.json` through `results_run3.json`):**

| Run | Result | Latency | Output tokens | Entities |
|---|---|---|---|---|
| 1 | success (structurally) | 192.1s | 6808 | **1** |
| 2 | **truncated failure** | 218.1s | 8192 (hit ceiling) | - |
| 3 | success (structurally) | 148.2s | 6540 | **1** |

For comparison, on the identical segment: `../anthropic_opus/` succeeds
in 49.3s with 21 entities; `../ollama_qwen3_8b/` succeeds consistently
(3/3) in 74-106s with 11-14 entities.

**This is a real, unexpected, and somewhat concerning finding, not just
a slower/lower-quality result:** the hypothesis this candidate was meant
to test - that a larger MoE model would narrow `qwen3:8b`'s entity-recall
gap - is **not supported**. `qwen3:30b-a3b` is *less* reliable than the
smaller dense model on this exact call, not more.

To be precise about what was actually observed versus inferred (per a
`/lrh-self-review` finding on an earlier draft of this section, which
conflated two distinct observations as if they were the same
phenomenon):

- **The 2 committed 1-entity runs (runs 1 and 3):** `success: true`,
  meaning `common.harness.run_entity_extraction()`'s real logic (which
  marks a missing/non-list `entities` field as `malformed_tool_result`
  and `success: false`) confirms the model *did* return a
  schema-conformant `entities` array - it just contained exactly one
  item. What that one item actually was is **not known**: `results.json`
  only records the count, not the content (this is exactly the gap
  `WI-LLM-0055` exists to close), and it was not separately captured at
  the time.
- **A distinct, uncommitted diagnostic observation:** a direct
  `extractor.extract()` call outside `benchmark.py`'s normal path (done
  afterward, to try to understand the pattern) once produced a tool call
  with a single field literally named `segment`, echoing the entire
  input text back verbatim - not populating `entities` at all. Under the
  harness's real success logic, *this* shape would have been classified
  `success: false` (`malformed_tool_result`), not `success: true` - it is
  **not** the same failure shape as the two committed 1-entity runs, and
  should not be read as explaining them. It is separate evidence that
  this model is unstable on this exact call, not a diagnosis of *why*
  the committed runs returned only one entity each.
- **A third, also-uncommitted diagnostic call** did succeed with a full,
  correct 13+-entity list in 158s, confirming the model *can* do the task
  correctly - it just does so inconsistently, more so than `qwen3:8b` at
  the same settings (`temperature=0.6`, confirmed via `ollama show
  qwen3:30b-a3b --parameters` to match Qwen3's own official
  recommendation, ruling out the same temperature-mismatch root cause
  that explained `qwen3:8b`'s earlier unreliability - see PR #223).

**Interpretation, not conclusively diagnosed here:** at least two
distinct anomalous behaviors were observed at these settings - schema-
conformant but near-empty output, and schema-non-conformant output - on
top of the committed run-2 truncation failure. This looks like a
different problem than `qwen3:8b`'s original (Ollama's `tool_choice`
forcing possibly not being honored, per `WI-LLM-0051`) - here the tool
generally *is* being called, just with wrong, minimal, or (per the
truncated run) incomplete arguments. Root-causing this (thinking-mode
budget exhaustion? a MoE-routing-specific instability at this
quantization? something else?) is out of this work item's scope - see
`WI-LLM-0051` for the adjacent, still-open `tool_choice`-reliability
investigation, and consider filing a follow-on item specifically for
this "succeeds but returns near-empty results" failure mode if it
recurs.

Note on evidence quality: `results.json`'s `raw_output_preview` field
(`common/harness.py:230`) is `null` on both committed 1-entity runs, not
because nothing was captured but because it is `None` by construction
whenever a tool call structurally succeeds - `BackendResponse.text` is
documented as "Empty string when `tool` was provided"
(`lcats/src/lcats/llm/backend.py:47`), so there is no free text to
preview on any successful tool call, malformed-but-schema-valid or not.
This is exactly why the distinction drawn above matters and why neither
diagnostic observation is recoverable from the committed JSON after the
fact. `WI-LLM-0055` (capturing full entity lists, not just counts) would
need to capture the full tool-result payload regardless of success/
failure to make this class of anomaly diagnosable from `results.json`
alone in the future.

**Bottom line:** on this evidence, `qwen3:30b-a3b` should **not** be
treated as a drop-in "quality tier" upgrade over `qwen3:8b` - it is both
slower (148-218s vs. 74-106s) and less reliable in this session's 3 real
runs. `qwen3:8b` remains the more dependable local candidate tested so
far.

## Segmentation stage (`WI-LLM-0051`)

`benchmark_segmentation.py` runs this candidate against the scene/sequel
segmentation stage (`../common/harness.py`'s `run_segmentation()`),
`temperature=0.6`, `retry_with_reminder=False` (this run's purpose is
characterizing the baseline gap across models, not re-validating the
retry mitigation already validated on `qwen3:8b` - see
`../ollama_qwen3_8b/README.md`'s "Follow-up: `tool_choice` reliability
investigation" section).

**Result: failed**, same way as every other segmentation attempt tested
so far - `finish_reason='stop'`, no tool call, despite schema-shaped
free-text content (`error_type: no_tool_call`, 268.2s, 5459 output
tokens). See `results_segmentation.json` for the full committed result.
This confirms the `tool_choice` gap is not specific to `qwen3:8b` - see
`PROP-ERW-LOCAL-MODEL-EVALUATION`'s "Decision 3 update (2026-08-08,
`tool_choice` reliability investigation, `WI-LLM-0051`)" section for the
full cross-model/cross-story verdict.
