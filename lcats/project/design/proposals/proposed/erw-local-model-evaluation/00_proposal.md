---
id: PROP-ERW-LOCAL-MODEL-EVALUATION
type: design_proposal
title: Local/Hybrid Model Evaluation Infrastructure for the Event-Role-World Pipeline
status: proposed
created_on: 2026-08-05
updated_on: 2026-08-12
implementation_status: partial
implemented_by: []
supersedes: []
superseded_by: null
related_design:
  - lcats/project/audits/2026-07-27-erw-pipeline-structured-output-reliability-audit.md
  - lcats/project/design/backlog.md
  - lcats/experiments/03_cross_segment_relation_pilot/run_pilot.py
  - lcats/experimental/model_comparison/README.md
  - lcats/project/design/proposals/adopted/lcats-pipeline-checkpointing/00_proposal.md
---

## Summary

This proposal promotes the audit's deferred Category E ("local model
options") to a real design decision. It adopts (a) reusing the existing
`LLMBackend` Protocol plus a `base_url` addition to `OpenAIBackend` -
rather than a new backend class - as how any OpenAI-compatible local
runtime (Ollama, vLLM, LM Studio) plugs into the pipeline, and (b) a
checked-in benchmarking harness (`lcats/experimental/model_comparison/`)
as the durable, reusable way to evaluate model/runtime candidates against
the pipeline's real tool-schema calls going forward. **Update
2026-08-05:** the harness's first methodology (whole story as input,
`temperature=0.2`) produced an apparent "unreliable" verdict for
`qwen3:8b` that turned out to be substantially an artifact of that
methodology, not the model - see "Decision 3 update" below. With the
corrected methodology (a real single segment, `temperature=0.6` matching
Qwen3's own recommendation), `qwen3:8b` succeeded consistently across 3
runs at ~1.5-2.2x `claude-opus-4-8`'s latency. This still does not
justify a default-model change on its own (see the updated Decision 3),
but the evidence base is now meaningfully different from this proposal's
original recommendation.

## Background / Motivation

`experiments/03_cross_segment_relation_pilot/run_pilot.py` defaults to
`claude-opus-4-8` via `lcats.llm.anthropic_backend.AnthropicBackend` for
every stage: genre detection, scene/sequel segmentation, and the four ERW
extractor calls (entity/event/relation/discourse) plus a story-level
cross-segment-relation pass. Real runs have cost $10-40+ each, which is
not sustainable for a script meant to be run repeatedly during iteration,
let alone for the full 5-10-per-genre research runs it exists to
eventually support.

`project/audits/2026-07-27-erw-pipeline-structured-output-reliability-audit.md`'s
Category E raised this cost concern and specifically flagged local models
as an unvalidated cost-reduction lever: a colleague's report (Kenny, using
Ollama for conversational Llama 3/Gemma use, not coding/structured
extraction) that local models "historically had much weaker/inconsistent
tool-calling and structured-output support than Anthropic's or OpenAI's
mature APIs." The audit's own recommendation was "a cheap, targeted spike
- run one story through the actual tool-schema path against a local
Ollama model - before investing further, rather than assuming it's a
viable cost-reduction lever untested." `project/design/backlog.md`'s "ERW
pipeline audit's Category E ... never promoted to a proposal" entry left
this unscoped pending that spike. `WI-PIPELINE-0041`
(`lcats-pipeline-checkpointing`, adopted and resolved) already addressed
the audit's separate checkpointing/resumability gap; this proposal
addresses the remaining local-model piece only.

This session ran that spike for real (not simulated) - see Design
Decisions below - and it produced a concrete, actionable result: the one
local candidate tested failed the exact call the pipeline depends on.

## Prior Art Check

### Duplication search
- In-repo: No existing local-model backend or benchmarking harness found.
  `src/lcats/llm/openai_backend.py` already existed (OpenAI chat
  completions adapter) and is directly reusable for any OpenAI-compatible
  local runtime once given a `base_url` override - see Design Decision 1.
- Sibling repos: None identified.
- External libraries: None identified as a wholesale replacement -
  Ollama/vLLM/LM Studio are runtimes to point the existing abstraction at,
  not libraries that replace `LLMBackend` itself.
- Recommendation: Proceed.

### Demand search
- Work items: None found requesting this directly; `WI-EVENT-0032`/
  `WI-EVENT-0033` cover tool-schema hardening (Categories A-D of the same
  audit), not local-model evaluation.
- Proposals: None found.
- Backlog: Found - `project/design/backlog.md`'s "ERW pipeline audit's
  Category E (cost/checkpointing/local-model options) never promoted to a
  proposal" entry (P3) directly requests this. This proposal satisfies its
  local-model portion (the checkpointing portion is already resolved via
  `PROP-LCATS-PIPELINE-CHECKPOINTING`).
- Recommendation: Offer to close/update that backlog entry once this
  proposal is adopted.

## Design Decisions

### Decision 1: How a local/OpenAI-compatible runtime plugs into the pipeline

Options considered:
- A new `OllamaBackend` class - explicit, but duplicates nearly all of
  `OpenAIBackend`'s translation logic (Ollama's `/v1/chat/completions`
  endpoint is OpenAI-compatible), and would need a sibling for every other
  OpenAI-compatible local server (vLLM, LM Studio) that shows up.
- Extend `OpenAIBackend` with an optional `base_url` constructor
  parameter, defaulting to `None` (unchanged, real OpenAI API behavior).

**Chosen: extend `OpenAIBackend` with `base_url`.** One local runtime
already satisfies the "point an existing OpenAI-shaped client at a
different host" case for every OpenAI-API-compatible server (confirmed for
Ollama in this session; vLLM and LM Studio advertise the same
compatibility). No new class, no new Protocol implementation, no new
tests beyond confirming the parameter forwards correctly. Implemented in
this session: `src/lcats/llm/openai_backend.py`'s `OpenAIBackend.__init__`
now accepts `base_url`, with a covering test
(`tests/llm_tests/openai_backend_test.py::test_constructor_forwards_base_url`).
`strict: true` tool-schema forwarding (`tool.get("strict", False)` into
the OpenAI function schema) was already present and required no change.

### Decision 2: Where evaluation infrastructure lives and how it's shaped

Options considered:
- Inline, ad-hoc scripts written per-evaluation and discarded - fast but
  not reusable, and this exact "should we trust a cheaper model" question
  will recur every time a new model family ships.
- `lcats/notebooks/` - this repo's existing convention for exploratory
  `.ipynb` work, but not meant to be re-run as a checked, comparable suite.
- `lcats/KMo/` - a collaborator's separate test code; wrong owner/purpose
  for pipeline-internal benchmarking.
- A new `lcats/experimental/` directory (following the `experimental/`
  convention used by large codebases for real, runnable code not yet
  ready for production dependency status), with one subdirectory per
  candidate model/backend, a shared harness module, and a summary script.

**Chosen: `lcats/experimental/model_comparison/`,** built in this session:
- `common/harness.py` - shared logic that runs the ERW pipeline's actual
  stage-3 entity-extraction tool-schema call
  (`lcats.analysis.event_role_world.entity_extractor.make_entity_extractor`,
  the same strict schema and `extract()` call path `run_pilot.py` uses,
  not a synthetic schema) against a fixed sample story
  (`corpora/sherlock/five_orange_pips/story.json`), and records
  success/failure, latency, token counts, and entity count to
  `results.json`.
- One directory per candidate (`anthropic_opus/`, `ollama_qwen3_8b/`),
  each with `README.md` (setup/cost/what a good-or-bad result means),
  `setup.py` (prerequisite check only - never downloads/installs
  anything itself), and `benchmark.py` (builds that candidate's
  `LLMBackend` and calls the shared harness).
- `benchmark_summary.py` - aggregates every candidate's `results.json`
  into one comparison table.

Adding a new candidate model or runtime means adding one new directory
following this shape, not writing a new one-off script each time.

### Decision 3: Whether to change `run_pilot.py`'s default model now

Options considered:
- Switch the default to a local model for at least the cheaper stages
  (genre detection, segmentation) now, based on general local-model
  tool-calling improvements found in the landscape survey.
- Hold the current default (`claude-opus-4-8`) and treat this proposal as
  infrastructure-only, pending more evaluation.

**Chosen: hold the current default.** Two real spike runs in this session
(candidate `ollama_qwen3_8b`, model `qwen3:8b` served by Ollama 0.32.5 on
an Apple M1 Max/32GB Mac, via `OpenAIBackend(base_url="http://localhost:11434/v1")`,
identical schema/story/`max_tokens` each time) produced two different
outcomes:

- **Run 1: failed.** Despite `tool_choice` forcing the `extract_entities`
  function, the response came back with `finish_reason='stop'` and no
  tool call at all. Ollama's server logs show it generated 3699 output
  tokens (most likely Qwen3's default chain-of-thought "thinking"
  content) over ~259 seconds before stopping without ever invoking the
  tool.
- **Run 2 (rerun, after the review-response fixes below): succeeded,**
  but generated 7996 output tokens over **1727 seconds (~29 minutes)**
  before finally producing a valid `extract_entities` call (20 entities).

The `anthropic_opus` baseline candidate, run once against the identical
call in the same session, succeeded in 202 seconds (14385 input / 7941
output tokens, 28 entities extracted) - so even `qwen3:8b`'s successful
run took ~8.5x longer than the frontier baseline, and its failure mode
(when it fails) is a silent non-call, not an error the caller can retry
against.

This is two data points on the hardest stage (entity extraction, not the
"comparatively simple" genre-detection/segmentation stages flagged as
better hybrid candidates) for one model at one size, with one untested
and likely-relevant confound (Qwen3's "thinking" mode was not disabled -
Ollama's `think` API parameter is a plausible one-line fix not yet
tried, and is the most likely explanation for both the failure and the
~29-minute latency in the successful run: the model appears to spend
most of its budget on chain-of-thought content before ever reaching the
tool call). It is real evidence that the audit's flagged concern is not
hypothetical on this pipeline's actual call shape - the local candidate
is not just slower, it is *unreliable*, succeeding and failing on
identical input - and this is not enough evidence to justify a
pipeline-wide or even single-stage default change. The hybrid-pipeline
hypothesis (cheap local model for genre detection/segmentation, frontier
model retained for entity/event/relation/discourse extraction and the
cross-segment pass) is still plausible and consistent with this result,
but unproven - it needs its own spike (a local model tested against the
genre-detection or segmentation stage specifically) before being
adopted, not inferred from mixed results on a different, harder stage.

### Decision 3 update (2026-08-05, corrected methodology)

A structural review of the harness itself (prompted by the question "are
we setting `qwen3:8b` - or even Opus - up for success?") found two
concrete, grounded problems with the runs above, independent of the
model:

1. **Wrong input size.** `entity_extractor.py`'s system prompt describes
   its input as "a segment of a story," but `harness.py` was feeding it
   the *entire* ~7,300-word story - something the real pipeline
   (`run_pilot.py`'s `_run_erw_extraction`) never does; it always passes
   one scene/sequel segment. This inflated cost/latency for **both**
   candidates and gave the smaller model a harder, more diffuse task than
   it will ever face in production.
2. **Wrong sampling temperature for this model.** The harness sent
   `temperature=0.2` (inherited from `entity_extractor.py`'s
   Anthropic/OpenAI-tuned default) to every candidate, including
   `qwen3:8b`. `ollama show qwen3:8b --parameters` on the test machine
   reports Ollama's own bundled default for this model as `temperature
   0.6, top_k 20, top_p 0.95` - matching
   [Qwen3-8B's official model card](https://huggingface.co/Qwen/Qwen3-8B)
   recommendation, which explicitly warns: **"Do NOT use greedy decoding,
   as it can lead to performance degradation and endless repetitions."**
   0.2 is much closer to greedy than to Qwen3's own tuned value - our
   explicit override was replacing an already-correct default with a
   worse one.

Both are now fixed: `common/harness.py` uses a real, single ~600-word
segment (`common/sample_segment.json`, produced once by an actual
stage-1 segmentation call - see `common/generate_sample_segment.py`),
and `ollama_qwen3_8b/benchmark.py` now overrides `temperature=0.6`
instead of inheriting the pipeline's Anthropic/OpenAI-tuned 0.2. A
harness bug was also fixed alongside these: `BenchmarkResult` never
captured the model's raw text response, so a failed run's actual output
(e.g. whether `<think>` tags were present) was unrecoverable without a
live rerun - `results.json` now includes a truncated
`raw_output_preview`.

**Re-run with the corrected methodology, 3 consecutive runs:**

| Run | Result | Latency | Output tokens | Entities |
|---|---|---|---|---|
| 1 | success | 74.4s | 1477 | 11 |
| 2 | success | 100.3s | 2318 | 13 |
| 3 | success | 105.7s | 2301 | 14 |

`anthropic_opus` on the identical segment: success, 49.3s, 5439 output
tokens, 21 entities. `qwen3:8b` now succeeds **consistently (3/3)** at
roughly 1.5-2.2x Opus's latency, with lower recall (11-14 vs. 21 entities
- not evaluated for precision, see Non-Goals) - a real, quantifiable
cost/latency/quality tradeoff, not the outright unreliability the
original two runs suggested.

**Also corrected:** the original Decision 3 text named Qwen3's "thinking"
mode as the leading suspect for the failure/latency, based on a
misreading of Ollama's server logs. Direct inspection of
`ollama show qwen3:8b --modelfile` shows Ollama uses a proper,
Qwen3-aware Go template (not a broken generic one, as briefly suspected
mid-session) - so the template-mismatch and thinking-mode hypotheses are
both **not supported** by available evidence and are retracted, not
confirmed. What the evidence does support: (a) the temperature/input-size
issues above, both fixed and re-tested; (b) a still-open, independently
corroborated risk that Ollama's OpenAI-compatible `tool_choice`
forced-function-name support has real gaps (community reports on
[Ollama's own GitHub, e.g. issue #4386](https://github.com/ollama/ollama/issues/4386))
- not reproduced across the 3 fixed-methodology runs above, but not ruled
out either, since a forced-tool_choice failure would look identical to
what the original run 1 showed.

**Recommendation, updated:** still hold the current default - one
corrected-methodology candidate at one model size succeeding 3/3 is
better evidence than the original mixed 1-fail/1-slow-success result, but
it is still one model/size/stage combination, not enough to justify a
pipeline-wide change. The hybrid-pipeline hypothesis is now *more*
plausible than the original write-up suggested (a model that reliably
succeeds at ~2x latency on the hardest stage is a stronger hybrid
candidate than one that appeared to fail outright), but still needs the
genre-detection/segmentation-stage spike named in the Implementation Plan
before being adopted.

### Decision 3 update (2026-08-07, genre-detection/segmentation spike, `WI-LLM-0050`)

The spike named above is now done - `common/harness.py` gained
`run_genre_detection()` and `run_segmentation()`, and `ollama_qwen3_8b`
was run twice against each real stage (whole-story input, `temperature=0.6`,
`corpora/sherlock/five_orange_pips/story.json`). See
`ollama_qwen3_8b/README.md`'s "Actual results: genre detection and
segmentation" for the full real results this section summarizes.

**Genre detection: hybrid-viable, 2/2 successes.** `qwen3:8b` correctly
identified the story's genre ("mystery") both runs, at 25-85s latency -
comfortably within the "comparatively simple" characterization this
hypothesis assumed for this stage.

**Segmentation: hybrid-NOT-viable for this model, 2/2 failures.** Both
runs came back `finish_reason='stop'` with **no tool call at all** -
despite the model's free-text response visibly beginning a well-formed,
schema-shaped JSON object matching `record_segments`'s expected fields
for its first two segments. (The captured evidence is truncated at 2000
characters and cuts off mid-object - see
`ollama_qwen3_8b/README.md`'s "Actual results: genre detection and
segmentation" caveat - so completeness/full conformance of the whole
response is not established, only that the visible portion is
schema-shaped.) This is not the entity-extraction stage's problem
(wrong/empty content); it is the residual Ollama `tool_choice`
forced-function-name gap this proposal already flagged as an open risk
(community reports on
[Ollama's GitHub, issue #4386](https://github.com/ollama/ollama/issues/4386)),
now reproduced directly on a second stage rather than left as a
theoretical concern. `WI-LLM-0051` was already filed to investigate this
gap specifically; these results are direct motivating evidence for it,
not new information requiring a new item.

**Hybrid-pipeline verdict, no longer open:** the hypothesis as originally
framed - "a cheap local model for the lighter stages, frontier model
retained for extraction" - does **not** hold uniformly even within the
"lighter stages" bucket. Genre detection and segmentation are not
interchangeably easy for this model/runtime combination: one succeeds
reliably, the other fails reliably, and the failure mode is a
`tool_choice` gap specific to Ollama's OpenAI-compatible endpoint rather
than a difficulty gradient in the classification task itself. A hybrid
pipeline routing genre detection to `qwen3:8b` while keeping segmentation
(and extraction) on the frontier model is supported by this evidence; a
hybrid pipeline also routing segmentation to `qwen3:8b` is not, unless
`WI-LLM-0051`'s investigation finds and fixes the underlying
`tool_choice` gap. This proposal continues to hold the current default
end-to-end (see the original recommendation above) - this update narrows
*which* stages a future hybrid pipeline could safely target, it does not
change the "not yet" answer to changing `run_pilot.py`'s default.

### Decision 3 update (2026-08-08, `tool_choice` reliability investigation, `WI-LLM-0051`)

`WI-LLM-0050` left the Ollama `tool_choice` forced-function-name gap as a
reproduced-but-uncharacterized risk (2/2 segmentation failures, one
model, one story). `WI-LLM-0051` gathered more real runs varying the
axes that could explain the 2/2 as coincidence rather than a systemic
gap, then tested whether the WI's own proposed mitigation actually works
rather than inferring an answer from resampling alone.

**Baseline reproduction, no mitigation: 0/5 succeeded.**

- `qwen3:8b` / `five_orange_pips` (same config as `WI-LLM-0050`, 3rd
  attempt): **failed** - `no_tool_call`, 193.7s, 1972 output tokens.
- `qwen3:8b` / `engineers_thumb` (different story, same model): **failed**
  - `no_tool_call`, 340.7s, 4518 output tokens. Committed as
  `ollama_qwen3_8b/results_segmentation_engineers_thumb.json` (via the
  new `benchmark_segmentation_engineers_thumb.py`, `retry_with_reminder=
  False`) - a real, runnable, reproducible artifact, not prose-only
  evidence.
- `qwen3:30b-a3b` / `five_orange_pips` (different model, same story):
  **failed** - `no_tool_call`, 268.2s, 5459 output tokens. Committed as
  `ollama_qwen3_30b_a3b/results_segmentation.json` (via the new
  `benchmark_segmentation.py` in that candidate's directory, also
  `retry_with_reminder=False`).

Combined with `WI-LLM-0050`'s original 2/2, this is **0/5 across 2
models and 2 stories**, including 3 independent samples at the identical
`(model, story)` config - a systemic gap, not content-dependent noise or
a per-model quirk. `run_entity_extraction()`'s comparatively small/flat
tool schema has never shown this failure mode across any candidate
tested in this proposal's history, consistent with a schema-complexity
explanation - though this proposal does not claim to have isolated the
exact triggering schema feature (nesting depth, property count, or
something else); that would require testing intermediate schema shapes,
out of this investigation's scope.

**Retry mitigation, actually tested (not inferred): a real, substantial
improvement, not a guaranteed fix.** An initial draft of this
investigation reasoned from the 3 identical-config baseline repeats
alone that a retry would have "no observed chance" of helping - **that
reasoning was wrong and was corrected after review.** Repeating the
*identical* request only tests whether `temperature=0.6` resampling
alone changes the outcome; it does not test the WI's own named
mitigation - an explicit reminder appended to the system prompt telling
the model it must call the tool. Tested directly: 5 live calls at the
identical `(qwen3:8b, five_orange_pips)` config, each with
`"CRITICAL INSTRUCTION: You MUST call the record_segments function/tool
..."` appended to the system prompt. **2/5 succeeded (40%)** - a real,
substantial improvement over the 0/5 baseline, though still far from
reliable. (Ollama's native `/api/chat` endpoint as a fallback retry
transport - the WI's other named strategy - was not tested; left as a
follow-up if the reminder alone proves insufficient at scale.)

**Retry path: implemented, not rejected.** Given the reminder
demonstrably helps, `common/harness.py`'s `run_segmentation()` now
retries exactly once, automatically, whenever the first attempt fails
specifically with `error_type="no_tool_call"` - appending the tested
reminder to the system prompt on the retry only. Verified end-to-end
with a real live call: first attempt failed (`no_tool_call`), automatic
retry succeeded, final `BenchmarkResult` shows `success=True,
retry_attempted=True, retry_succeeded=True`, 4 segments extracted. Any
other failure mode (a genuine `api_error`, a schema/validation error, an
empty segment list) is not retried - a reminder about calling the tool
has no plausible mechanism to fix those, and retrying them would only
add latency for no benefit.

This does not fully settle the underlying question (whether a smaller or
differently-shaped tool schema would succeed without any mitigation, why
the reminder helps only 40% of the time rather than reliably, or whether
a future Ollama release fixes the gap upstream) - see Open Questions
below.

### Decision 3 update (2026-08-08, production system-prompt reminder, `WI-LLM-0059`)

`WI-LLM-0051` scoped its reminder mitigation to `common/harness.py`'s own
`run_segmentation()` retry path only, deliberately not touching the real
production `SCENE_SEQUEL_SYSTEM_PROMPT` in `scene_analysis.py` (shared by
every `LLMBackend` implementation via `make_segment_extractor()`).
`WI-LLM-0059` tested whether appending the identical reminder to that
*production* prompt text - as if it were a permanent addition, not just a
harness-only retry - actually helps local-model reliability without
regressing the frontier paths the prompt is shared with.

**Local models (Ollama): reminder still helps, still weakly.** 4 more
real calls with the reminder appended eagerly (not on retry) - `qwen3:8b`
x3, `qwen3:30b-a3b` x1 (a first test for that model) - all 4 failed
(`no_tool_call`). Since this uses the identical single-call mechanism
`WI-LLM-0051`'s retry path already tested (a fresh call, reminder
appended to the system prompt, no continuation state), this session's
3 `qwen3:8b` results are directly poolable with `WI-LLM-0051`'s prior
5-call `qwen3:8b` sample: **2/8 (25%) combined for `qwen3:8b`**, vs. 0%
with no reminder at all - a 0/3 result this round is unsurprising noise
at a true ~20-30% success rate, and does not contradict `WI-LLM-0051`'s
original 40% (2/5) finding, it just makes the combined `qwen3:8b`
estimate more conservative. The 1 `qwen3:30b-a3b` call is a separate,
first-ever data point for that model (not poolable with the `qwen3:8b`
sample above, since it's a different model) - it also failed, but n=1 is
too small to say anything beyond "does not obviously behave differently
from `qwen3:8b`."

**Anthropic (`claude-opus-4-8`): success/latency neutral, but a small,
real granularity shift observed - not clean "no regression."** 3 paired
baseline/modified real calls (not a single pair - see the P1 review
finding on `WI-LLM-0059`'s own planning PR, #260) all succeeded on both
sides: success rate 3/3 baseline, 3/3 modified; latency comparable across
all 6 calls (25.4-34.7s, no systematic shift toward the modified
condition). The initial pass through this data only recorded
`segment_count`, not the actual segments, and declared this frontier path
cleanly "neutral" from counts alone (4, 5, 4 baseline vs. 7, 4, 4
modified) - a P1 review finding on this WI's own implementation PR (#266)
correctly identified that a bare count cannot support a claim about
output *quality* (labels, boundaries), and that the review couldn't tell
whether the count divergence was meaningful without the actual segments.
Re-run with the segments themselves persisted (`results_frontier_paired_
anthropic.json`): baseline stayed at 4 segments all 3 times; modified
produced 4, 5, 5 segments. Reading the actual content: in pairs 2 and 3,
the modified condition split the story's closing "Holmes returns / traces
the killers / epilogue" material into two segments (a `dramatic_scene` or
`narrative_scene` for the return, plus a separate `narrative_scene` for
the "Lone Star lost at sea" epilogue) where the baseline kept it as one -
the same split pattern in both pairs, not two unrelated one-off
divergences. This is a real, small directional signal, not pure noise:
the reminder text appears to nudge the model toward slightly finer
end-of-story segmentation, in mild tension with
`SCENE_SEQUEL_SYSTEM_PROMPT`'s own "Coarse segmentation only... prefer
FEWER, LARGER segments" rule. It is not a functional failure - every
segment across all 6 calls used a valid `segment_type` enum value and
read as a coherent, correctly-labeled unit - and it is far short of
"risky" in the sense the OpenAI gap below is. But it means the honest
characterization is "no catastrophic effect, plus one minor, real
side effect on granularity," not "the reminder is neutral for this
frontier path" as the first draft of this section claimed. This is the
first `anthropic_opus` segmentation-stage data recorded in this
proposal's history, so there is no independent prior-session baseline
to compare either the counts or this granularity pattern against.

**OpenAI (`gpt-4o`): re-tested once real API credits were added
(2026-08-09 follow-up) - still could not be verified, now for a
structural reason rather than a billing one.** The original attempt
failed with `429 insufficient_quota` / `credit_balance_exhausted` (zero
account credits). Once credits were added, 3 distinct real attempts were
made at the harness's default `max_tokens=16384`, plus one rejected
probe that never reached the model at all (a review finding on this
follow-up's own PR, #272, correctly identified that an earlier draft of
this section conflated the probe with the real attempts, overstating
what it actually showed): (1) baseline `truncated_output` (101.2s),
modified `extraction_or_alignment_error` (38.4s); (2) a probe raising
`max_tokens` to 24576 to rule out a fixable truncation, rejected outright
by the OpenAI API before contacting the model at all - *"max_tokens is
too large: 24576. This model supports at most 16384 completion tokens,
whereas you provided 24576."* - 16384 is `gpt-4o`'s own hard maximum
completion-token limit, not a harness-chosen value a bigger budget could
raise; (3) a confirmation re-run at the reverted default, reproducing
attempt 1 exactly (baseline `truncated_output`, modified
`extraction_or_alignment_error`); (4) a further re-run after fixing a
second review finding (`_call_once` was collapsing the real
`extraction_error`/`alignment_error`/`validation_error` detail to a bare
classification string instead of preserving it, diverging from
`common/harness.py`'s own richer messaging), which this time landed on
**both conditions failing with `truncated_output`** rather than the
asymmetric split seen in attempts 1 and 3.

**Baseline hit `truncated_output` in all 3 real attempts (3/3) -
reproducible, not one-off.** **Modified failed in all 3 real attempts too
(3/3)**, but via two different observed error classifications
(`extraction_or_alignment_error` x2, `truncated_output` x1) - both
consistent with exhausting the same 16384-token budget at a slightly
different point each time, but this is an inference from the pattern,
not confirmed for the two `extraction_or_alignment_error` occurrences
specifically, since their underlying detail predates the error-message
fix. This story/prompt combination cannot reliably complete on `gpt-4o`
within its own maximum possible output, on either condition, independent
of the reminder - a structural finding, not evidence the modified prompt
specifically caused either failure (both conditions failed every time,
via mechanisms plausibly but not conclusively traced to the same root
cause, and neither condition ever produced a usable result to compare
against the other).

**Verdict, confirmed unchanged: do not edit `SCENE_SEQUEL_SYSTEM_PROMPT`.**
Per `WI-LLM-0059`'s own Required Changes item 5, an unverified OpenAI
path forces the documented no-change outcome regardless of how the other
two paths look, since the edit would ship to GPT users too and there is
still no way to confirm it is safe for them - now confirmed by a real,
credits-enabled attempt rather than an absence of one. This is not a
judgment call weighing risk against benefit - the WI's own acceptance
criteria state plainly that an unverified OpenAI path does not proceed to
a production edit. The Anthropic granularity finding above does not
independently block the edit (it is not "risky" in the WI's sense), but
it does mean that even a working OpenAI result would not have made this
an easy, obviously-safe edit - a future revisit should weigh the
granularity side effect on its own merits, not treat the Anthropic leg as
a clean pass. The reminder remains implemented only as
`common/harness.py`'s existing harness-scoped retry (`WI-LLM-0051`,
unchanged by this investigation) - not added to the real, shared
production prompt. Getting a real OpenAI/GPT comparison for this
question would now need a smaller/shorter test story that fits within
`gpt-4o`'s 16384-completion-token ceiling, not just a bigger budget - a
separate methodology fix, out of this follow-up's scope.

### Decision 3 update (2026-08-09, `WI-LLM-0056`'s two `tool_choice` mechanisms investigated, `WI-LLM-0062`)

`WI-LLM-0056`'s tranche 1 found 3 of 6 entity-extraction candidates
failing via `tool_choice`, but review caught this was two genuinely
different mechanisms, not one - `WI-LLM-0062` investigated both
independently.

**Silent ignore (`ollama_gemma4_12b`, `ollama_deepseek_r1_14b`) - the
reminder mitigation transfers, partially, and inconsistently across
models.** `WI-LLM-0051`'s reminder-retry mitigation (`common/harness.py`'s
`run_entity_extraction(..., retry_with_reminder=True)`, newly added by
this WI, mirroring `run_segmentation()`'s existing mechanism) was tested
on both candidates:

- `ollama_gemma4_12b`: a real methodological confound surfaced first and
  had to be corrected - the harness's default `max_tokens=8192` genuinely
  wasn't enough for this candidate's tool-call output (3/3 runs hit
  `truncated_output`, not `no_tool_call` at all, meaning the retry path
  never even fired). Raised to 16384. At the corrected setting, 4 real
  runs: 1 baseline success (no retry needed), 1 baseline call that timed
  out outright (a third distinct failure mode, unaddressable by the
  reminder since it only retries on `error_type="no_tool_call"`), 1
  baseline failure with a successful reminder-retry recovery, 1 baseline
  failure whose retry itself timed out. **1 of 2 applicable retries
  succeeded** - a real, partial effect, consistent with segmentation's own
  "helps but doesn't fully fix it" finding, on a small and noisy sample
  (this candidate's own latency, 250-2800+ seconds per call including two
  genuine request timeouts across 7 total runs, makes a larger sample
  expensive). A review finding (PR #277) also caught that this harness's
  retry wrapper was reporting only the retry call's own latency/tokens,
  silently discarding the failed baseline's real resource use - fixed,
  and every affected result (both candidates) was regenerated after the
  fix except one `gemma4:12b` run whose qualitative outcome (success)
  stands but whose exact resource numbers predate the fix - see
  `ollama_gemma4_12b/README.md`'s own caveat.
- `ollama_deepseek_r1_14b`: 3/3 baseline failures, **0/3 reminder-retries
  succeeded**, and a tuned `temperature=0.6` alone (the other untested
  variable `WI-LLM-0056` flagged) didn't help either. In every failure the
  model explains its reasoning in prose instead of calling the tool - a
  more robust, harder-to-mitigate instance of the same mechanism than
  `gemma4:12b` showed. A real, negative, complete finding - not
  inconclusive.

**Active filter rejection (`gemini_flash`) - the original schema-
complexity hypothesis was wrong; it's a token budget.** `WI-LLM-0056`
hypothesized `ENTITY_TOOL_SCHEMA`'s nested shape was triggering Gemini's
own `MALFORMED_FUNCTION_CALL` validation filter. Tested directly: a
minimal, flat, single-field schema succeeded 3/3 at `max_tokens=2048`
(consistent with either hypothesis on its own). To isolate the variable,
re-ran the *same, unmodified* `ENTITY_TOOL_SCHEMA` at increasing
`max_tokens`: 8192 and 16384 both failed (`truncated_output` this time,
not even reproducing the original `MALFORMED_FUNCTION_CALL` signal);
32000 succeeded **3/3**. The same schema that "systemically" failed in
`WI-LLM-0056` succeeds reliably once given enough token headroom - it is
not permanently rejected by a complexity-triggered filter. The likely
real constraint is Gemini 3.x's internal "thinking"/reasoning token
consumption sharing the same `max_tokens` budget as the visible
completion; which specific API-level failure surfaces (a content-filter
rejection vs. a plain length cutoff) may itself be non-deterministic
depending on exactly where generation gets cut off, rather than a stable
signature of schema rejection. This does not fully resolve *why* 8192-
16384 is insufficient for this schema+segment specifically (out of this
WI's own scope), but it does overturn the original "systemic filter
rejection" framing.

**Neither mechanism prompted a `common/harness.py` change beyond the new,
opt-in `run_entity_extraction(retry_with_reminder=...)` parameter itself**
(defaults to `False`, preserving every existing candidate's behavior
unchanged) - no production code (`lcats.llm`, `run_pilot.py`) was touched,
per this WI's own Non-Goals. See
`lcats/experimental/model_comparison/ollama_gemma4_12b/README.md`,
`ollama_deepseek_r1_14b/README.md`, and `gemini_flash/README.md` for the
full per-candidate write-ups and committed evidence.

### Decision 3 update (2026-08-10, `ollama_gpt_oss_20b` fully vetted across all 3 stages, `WI-LLM-0063`)

`WI-LLM-0056`'s tranche 1 tested `ollama_gpt_oss_20b` only on entity
extraction (2/2 success, fastest local candidate) - genre detection and
segmentation were untested. `WI-LLM-0063` ran 3 real calls per stage
against all three, bringing this candidate up to the same evidence bar
as `qwen3:8b`.

- **Genre detection: 3/3 success**, all correctly detected `mystery`.
  Matches `qwen3:8b`'s own "hybrid-viable" finding for this stage.
- **Entity extraction: 3/3 success**, but the added 3rd run (169.8s,
  5514 output tokens, 34 entities) revealed real, substantial variance
  the original 2-run sample (35-38s, 12-21 entities) did not show - up to
  ~4.5x latency spread and ~3x entity-count spread across 3 runs.
  `success` never flipped to failure, but a single run's entity count
  should not be treated as representative without a future
  precision/recall check (out of this tranche's Non-Goals).
- **Segmentation: 0/3 - a genuinely new failure mode.** Every run's
  baseline call ignored `tool_choice` (the familiar silent-ignore
  mechanism), and `WI-LLM-0051`'s automatic reminder retry did get the
  tool actually invoked each time (unlike `gemma4:12b`/`deepseek-r1:14b`,
  where the reminder sometimes still produces no call at all) - but the
  resulting segment then failed the segmenter's own downstream alignment
  validation (anchor text not found verbatim in the source story) in all
  3 runs. This is a failure in answer *quality* after a successful tool
  call, distinct from both mechanisms `WI-LLM-0062` characterized (silent
  ignore, active filter rejection) and from the `qwen3:8b`/`qwen3:30b-a3b`
  baseline segmentation failures (0/5, never even reaching a tool call
  that passed alignment). Segmentation remains not viable for this
  candidate, consistent with every other local model tested on this stage
  so far.

**No `common/harness.py` change was needed or made** - `run_segmentation()`'s
existing `retry_with_reminder=True` default already covered this
candidate; this WI only added `benchmark_genre.py`/
`benchmark_segmentation.py` scripts for `ollama_gpt_oss_20b` (mirroring
`ollama_qwen3_8b`'s existing shape) and a 3rd entity-extraction run. No
production code (`lcats.llm`, `run_pilot.py`) touched, per this WI's own
Non-Goals. See `lcats/experimental/model_comparison/ollama_gpt_oss_20b/README.md`'s
"Follow-up" section for the full per-stage write-up and committed
evidence.

### Decision 3 update (2026-08-10, `gpt-oss:20b` best-config/grounding follow-up, `WI-LLM-0064`)

`WI-LLM-0064` tested whether the `WI-LLM-0063` `gpt-oss:20b` verdict was
unfairly pessimistic because the harness was still using shared
Anthropic/OpenAI-tuned settings, and because prior entity results counted
raw tool-result entities rather than production-grounded entities. The
local Ollama installation's bundled parameters for `gpt-oss:20b` report
`temperature 1`, so this follow-up added candidate-local best-config
scripts at `temperature=1.0` and extra diagnostics only for this
candidate.

- **Entity extraction at `temperature=1.0`: raw tool-call success 3/3,
  grounded success 0/3.** The model still called `extract_entities`
  reliably and returned 11, 11, and 13 raw entities, but every run emitted
  `mentions` as plain strings rather than the mention objects expected by
  production `build_entities()`. The new grounded diagnostic therefore
  found 0 grounded entities and 0 grounded mentions in every run. This
  corrects the earlier "entity extraction reliable" framing: it was
  reliable at the API/tool-call layer, but not yet production-usable as an
  ERW entity-extraction replacement.
- **Segmentation at `temperature=1.0`: 0/3.** All three runs still
  ignored the forced `record_segments` tool call and emitted
  schema-shaped JSON in message content instead.
- **Segmentation with `temperature=1.0` plus an explicit verbatim-anchor
  reminder: 0/3.** The reminder changed the failure mode in 2 of 3 runs
  by getting the model to call `record_segments`, but the captured
  pre-alignment anchors still failed production alignment (ellipses,
  invented/paraphrased boundary text, case drift). The third reminder run
  returned no tool call/refusal.

**Recommendation, updated:** `gpt-oss:20b` remains a good local candidate
for genre detection only. It is a plausible follow-up target for entity
extraction prompt/schema/output-handling work, because it reliably calls
the tool and returns plausible raw names, but it should no longer be
treated as production-ready for grounded ERW entity extraction. It remains
not viable for segmentation under the current OpenAI-compatible Ollama
harness: the fairer best-config test stayed 0/6 usable across the two
segmentation variants.

### Landscape context (not itself decision-grade evidence)

A web survey (Aug 2026) of runtimes and models informs which candidates to
add next, but most "2026 benchmark" search results were SEO-farm content
with suspiciously precise, unverifiable numbers - treated as orientation
only, not cited as justification for any decision above:

- Ollama and vLLM both have first-class OpenAI-compatible tool-calling
  support; Ollama additionally does grammar-constrained JSON-schema
  decoding (XGrammar-backed since 0.3+) - the closest local analogue to
  `strict: true`, though this session's spike shows constrained decoding
  alone did not stop the model from simply never calling the tool.
- MLX (`mlx-lm`, Apple-Silicon-native) has native tool-calling support
  too, and several OpenAI-compatible-server wrappers exist for it - an
  unexplored alternative to Ollama on Apple Silicon specifically.
- Qwen3 ships Ollama-library sizes from 0.6b to 235b; `30b-a3b` (a
  mixture-of-experts model, ~30B total/~3B active parameters) was named
  here as a plausible "quality tier" candidate for extraction-grade
  stages, not yet tested. **Update (`WI-LLM-0049`):** now tested - the
  hypothesis was **not supported**. 2 of 3 real runs against the same
  entity-extraction call returned near-empty or malformed results
  (structurally valid tool calls with essentially no useful content)
  despite `temperature=0.6` matching Qwen3's own documented
  recommendation (ruling out the temperature-mismatch cause that
  explained `qwen3:8b`'s earlier unreliability); `qwen3:30b-a3b` proved
  both slower and less reliable than the smaller `qwen3:8b` on this exact
  call. See
  `lcats/experimental/model_comparison/ollama_qwen3_30b_a3b/README.md`
  for the full real results and root-cause discussion (not conclusively
  diagnosed). Similar tiers exist for Gemma 4 and Llama 4, still
  untested.
- The two target hardware profiles differ meaningfully: Apple Silicon
  unified memory (tested here, M1 Max/32GB) versus a Kubuntu Focus
  laptop's discrete NVIDIA GPU (not available in this session - untested,
  and its VRAM-bound sweet spot likely differs from the Mac's).

## Non-Goals

- Does not change `run_pilot.py`'s default model or add a `--backend
  local`/similar flag - see Decision 3.
- Does not test Ollama's `think: false` parameter, since the fixed
  methodology (real segment + Qwen3's own recommended temperature)
  already produces consistent success without it - the original
  "thinking mode" hypothesis was retracted (see Decision 3 update), not
  confirmed, and testing it further is deferred, not ruled in or out.
- Does not evaluate the Kubuntu Focus/NVIDIA hardware profile - not
  available in this session.
- Does not extend the benchmark harness to the genre-detection,
  segmentation, event/relation/discourse, or cross-segment-relation
  stages - only stage-3 entity extraction is covered so far.
- Does not perform a quality (precision/recall against ground truth)
  comparison - the harness currently only checks call success and a crude
  entity-count sanity signal, not correctness of what was extracted.

## Implementation Plan

Already done (across two PRs):
1. `OpenAIBackend.base_url` support + test
   (`src/lcats/llm/openai_backend.py`,
   `tests/llm_tests/openai_backend_test.py`).
2. `lcats/experimental/model_comparison/` harness, `anthropic_opus` and
   `ollama_qwen3_8b` candidates, `benchmark_summary.py`.
3. Initial spike run per candidate (whole-story input, `temperature=0.2`)
   - kept as `results_fullstory_*.json` for transparency.
4. Methodology fix (2026-08-05): real single-segment input
   (`common/sample_segment.json` + `common/generate_sample_segment.py`),
   per-candidate temperature override capability
   (`harness.run_entity_extraction(temperature=...)`), raw-output capture
   in `results.json` (`raw_output_preview`), and a re-tuned
   `DEFAULT_MAX_TOKENS` (8192, replacing both the too-low 4096 factory
   default and the whole-story-tuned 16384).
5. Three consecutive re-runs of `ollama_qwen3_8b` against the corrected
   methodology, all successful - see Decision 3 update.

Follow-on work (proposed as separate work items once this proposal is
adopted):
1. ~~Add an `ollama_qwen3_30b_a3b` candidate (MoE, higher quality
   ceiling) to test whether a larger local model narrows the
   entity-recall gap (11-14 vs. Opus's 21) at a still-acceptable
   latency.~~ **Done (`WI-LLM-0049`).** The hypothesis was **not
   supported** - `qwen3:30b-a3b` proved both slower and less reliable
   than `qwen3:8b` on this exact call (2 of 3 real runs returned
   essentially empty results). See
   `lcats/experimental/model_comparison/ollama_qwen3_30b_a3b/README.md`.
2. ~~Extend `common/harness.py` to cover the genre-detection and
   segmentation stages, and add a candidate run against those - this is
   the evidence still needed to actually assess the hybrid-pipeline
   hypothesis, which entity-extraction results alone do not settle.~~
   **Done (`WI-LLM-0050`).** Genre detection: hybrid-viable (2/2
   successes). Segmentation: hybrid-NOT-viable for this model/runtime
   (2/2 failures - `tool_choice` never invoked the tool at all, despite
   schema-conformant free-text content). See the "Decision 3 update
   (2026-08-07 ...)" section above and
   `lcats/experimental/model_comparison/ollama_qwen3_8b/README.md`.
3. ~~Investigate the residual Ollama `tool_choice` forced-function-name
   gap (see Decision 3 update) - not reproduced here, but not ruled out;
   consider adding a retry-once-on-empty-tool-result path to the harness
   if it recurs.~~ **Done (`WI-LLM-0051`).** Reproduced at 0% baseline
   success (0/5 across 2 models x 2 stories). A retry-once-with-reminder
   path was tested directly (not just inferred) and found to meaningfully
   help (2/5 succeeded, vs. 0/5 without) - implemented in
   `common/harness.py`'s `run_segmentation()` and verified end-to-end
   with a real call. See the "Decision 3 update (2026-08-08 ...)" section
   above.
4. ~~Test whether `gpt-oss:20b` improves under its bundled local
   best-config (`temperature=1.0`) and a targeted verbatim-anchor
   reminder.~~ **Done (`WI-LLM-0064`).** Genre detection remains the only
   clean local use case. Entity extraction stays raw-tool-call reliable
   but not production-grounded (0/3 grounded entity runs), and
   segmentation remains not viable (0/6 across plain `temperature=1.0`
   and verbatim-reminder variants). See the "Decision 3 update
   (2026-08-10 ... `WI-LLM-0064`)" section above.
5. ~~Determine whether `gpt-oss:20b` entity extraction can be made
   production-grounded or should be demoted to genre-only.~~ **Done
   (`WI-LLM-0065`).** A candidate-scoped adapter now repairs only the
   observed malformed shapes (string entities, `name`/`entity` aliases,
   string mentions, and grounded `text`/`surface` mention dicts missing
   `quote`/`mention_id`) before the unchanged production
   `build_entities()` call. Three live
   `gpt-oss:20b` runs at `temperature=1.0` produced 3/3
   production-grounded successes, but with uneven quality and latency:
   grounded entity counts were 12, 11, and 16; grounded mention counts
   were 13, 12, and 18; latency ranged 71-141 seconds. Recommendation:
   no genre-only demotion is required, but entity extraction should be
   considered only behind the candidate adapter and should not become a
   production default without a precision/recall evaluation.
6. Only after (1)-(5): revisit Decision 3 in a follow-on proposal or
   amendment.

## Cross-References

- `lcats/project/audits/2026-07-27-erw-pipeline-structured-output-reliability-audit.md`
  (Category E, this proposal's origin)
- `lcats/project/design/backlog.md` ("ERW pipeline audit's Category E ...
  never promoted to a proposal")
- `lcats/experimental/model_comparison/README.md` (the harness this
  proposal documents)
- `lcats/experiments/03_cross_segment_relation_pilot/run_pilot.py` (the
  pipeline this evaluation targets)

## Open Questions

- ~~Does Ollama's OpenAI-compatible `tool_choice` forced-function-name
  support have a real gap (per community reports), and if so, would it
  recur at scale (more stories, more candidates) even though it did not
  reproduce across 3 fixed-methodology runs here?~~ **Answered
  (`WI-LLM-0051`):** yes, reproduced at 0/5 baseline success across 2
  models and 2 stories on the segmentation stage specifically -
  `run_entity_extraction()`'s smaller/flatter schema has never shown this
  failure. An explicit system-prompt reminder meaningfully mitigates it
  (2/5 succeeded vs. 0/5 without), now implemented as an automatic retry
  in `common/harness.py`. Still open: which specific schema property
  (size, nesting depth, something else) triggers the base gap, why the
  reminder only helps 40% of the time rather than reliably, whether
  Ollama's native `/api/chat` endpoint (the WI's other named retry
  strategy, not tested) does better, and whether a future Ollama release
  fixes it upstream - not investigated (would require testing
  intermediate schema shapes, out of `WI-LLM-0051`'s scope).
- ~~Would this same reminder help the *production*
  `SCENE_SEQUEL_SYSTEM_PROMPT` in `scene_analysis.py` for other
  providers/models?~~ **Answered (`WI-LLM-0059`):** the local-model
  effect replicates for `qwen3:8b` (2/8 combined success across two
  sessions with the identical single-call mechanism, vs. 0% without).
  The Anthropic frontier path showed no success-rate or latency
  regression (3/3 paired real calls) but did show a small, real
  granularity side effect - 2 of 3 modified-condition runs split the
  story's ending into an extra segment where baseline stayed at 4 - not
  a functional failure, but not a clean "neutral" result either (initial
  count-only data had wrongly read as clean; segment content itself
  showed the pattern). The OpenAI frontier path, which the prompt is
  equally shared with, could not be verified: the original attempt hit
  zero account credits, and a 2026-08-09 follow-up re-test (after credits
  were added, 3 real attempts) found `gpt-4o` reproducibly hitting its
  own hard 16384-completion-token maximum on the baseline condition
  (3/3) and failing every time on the modified condition too (3/3, via
  two different error classifications plausibly but not conclusively
  tied to the same token ceiling) - so no working comparison was
  possible either way. Per `WI-LLM-0059`'s own acceptance criteria,
  an unverified OpenAI path forces a no-change verdict regardless of the
  other two results - `SCENE_SEQUEL_SYSTEM_PROMPT` was **not** edited.
  See the "Decision 3 update (2026-08-08, production system-prompt
  reminder, `WI-LLM-0059`)" section above for the full write-up
  including the 2026-08-09 re-test. A real OpenAI/GPT comparison for
  this question would need a smaller/shorter test story that fits within
  `gpt-4o`'s token ceiling - a methodology fix, not just a bigger
  API budget, and out of scope for this follow-up.
- ~~Do the 3 `tool_choice` failures `WI-LLM-0056` found on entity
  extraction (`gemini_flash`, `ollama_gemma4_12b`,
  `ollama_deepseek_r1_14b`) share one root cause?~~ **Answered
  (`WI-LLM-0062`):** no - two distinct mechanisms. The Ollama silent-ignore
  mechanism partially responds to `WI-LLM-0051`'s reminder mitigation
  (1/2 applicable retries succeeded for `gemma4:12b`; 0/3 for
  `deepseek-r1:14b`, where a tuned temperature didn't help either).
  Gemini's active filter rejection is **not** schema-complexity-driven as
  originally hypothesized - the identical, unmodified `ENTITY_TOOL_SCHEMA`
  succeeds reliably (3/3) once given enough `max_tokens` (32000 vs. the
  original 8192); the real constraint appears to be token budget
  (Gemini's own "thinking" consumption), not schema shape. Still open:
  why `deepseek-r1:14b`'s silent-ignore is fully unresponsive to mitigation
  where `gemma4:12b`'s is partially responsive; why Gemini needs so much
  more `max_tokens` headroom than the visible output size alone would
  suggest; and whether Ollama's native `/api/chat` endpoint (still
  untested, per `WI-LLM-0051`'s own open item) would do better on either
  Ollama candidate.
- ~~Is `ollama_gpt_oss_20b`'s segmentation-stage alignment-rejection
  failure (`WI-LLM-0063`) addressable by a different mitigation (e.g.
  instructing the model to quote source text verbatim)?~~ **Answered
  (`WI-LLM-0064`):** not by the tested best-config mitigation.
  `temperature=1.0` alone stayed 0/3 because the model emitted
  schema-shaped JSON in message content rather than a tool call; adding a
  candidate-local verbatim-anchor reminder changed 2 of 3 runs into real
  tool calls, but both still failed anchor alignment, and the third run
  returned no tool call/refusal. Segmentation remains not viable for this
  candidate under the current OpenAI-compatible Ollama path.
- ~~Is `gpt-oss:20b`'s grounded entity-extraction failure addressable by
  a prompt/schema/output-handling follow-up?~~ **Answered
  (`WI-LLM-0065`):** yes, narrowly. A candidate-scoped compatibility
  adapter can preserve production grounding for the observed malformed
  shapes without fabricated spans or weakened quote checks, and the final
  live run was 3/3 production-grounded. The answer is not a default-model
  endorsement: grounded counts and latency remained variable, so the next
  question is precision/recall quality under the adapter, not routing
  adoption.
- Is MLX (native Apple Silicon) meaningfully more reliable than
  Ollama/llama.cpp for this pipeline's tool-schema calls? Not yet tested.
- What is the actual VRAM-bound model-size sweet spot on the Kubuntu Focus
  hardware profile? Not testable in this session; needs a run on that
  machine.
- How much of `qwen3:8b`'s lower entity recall (11-14 vs. Opus's 21) is a
  real precision/recall gap versus an artifact of this harness's
  single-run, no-ground-truth measurement? Needs the quality comparison
  named in Non-Goals.
