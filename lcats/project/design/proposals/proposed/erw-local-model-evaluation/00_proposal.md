---
id: PROP-ERW-LOCAL-MODEL-EVALUATION
type: design_proposal
title: Local/Hybrid Model Evaluation Infrastructure for the Event-Role-World Pipeline
status: proposed
created_on: 2026-08-05
updated_on: 2026-08-07
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
4. Only after (1)-(3): revisit Decision 3 in a follow-on proposal or
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
  intermediate schema shapes, out of `WI-LLM-0051`'s scope). Also
  unknown: whether this same reminder would help the *production*
  `SCENE_SEQUEL_SYSTEM_PROMPT` in `scene_analysis.py` for other
  providers/models - out of scope here (this proposal's Non-Goals
  disclaim touching the shared backend/production prompts); flagged as a
  candidate follow-up.
- Is MLX (native Apple Silicon) meaningfully more reliable than
  Ollama/llama.cpp for this pipeline's tool-schema calls? Not yet tested.
- What is the actual VRAM-bound model-size sweet spot on the Kubuntu Focus
  hardware profile? Not testable in this session; needs a run on that
  machine.
- How much of `qwen3:8b`'s lower entity recall (11-14 vs. Opus's 21) is a
  real precision/recall gap versus an artifact of this harness's
  single-run, no-ground-truth measurement? Needs the quality comparison
  named in Non-Goals.
