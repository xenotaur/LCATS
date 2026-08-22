# Why LCATS evaluates local models against the ERW pipeline

The Event-Role-World (ERW) pipeline's real, tool-schema-driven calls
(`experiments/03_cross_segment_relation_pilot/run_pilot.py`) default to
`claude-opus-4-8` via `AnthropicBackend`, for every stage: genre
detection, scene/sequel segmentation, and the four extractor calls
(entity/event/relation/discourse) plus a story-level cross-segment pass.
Real runs have cost $10-40+ each - not sustainable for a script meant to
be run repeatedly during iteration, let alone for the eventual 5-10-
per-genre research runs it exists to support. This page explains why
LCATS started evaluating cheaper local models as a substitute for some of
that work, what the architecture decision behind it was, what the
evidence actually shows so far, and what's still unresolved.

## Where the question came from

`project/audits/2026-07-27-erw-pipeline-structured-output-reliability-audit.md`'s
Category E flagged local models as an unvalidated cost-reduction lever,
alongside a second-hand report that local models "historically had much
weaker/inconsistent tool-calling and structured-output support" than
Anthropic's or OpenAI's mature APIs. The audit's own recommendation was
not "adopt local models" or "dismiss them" - it was to run a cheap,
targeted spike against the pipeline's real tool-schema path before
assuming either. `project/design/backlog.md` left this unscoped pending
that spike. The governing design proposal,
[`PROP-ERW-LOCAL-MODEL-EVALUATION`](../../project/design/proposals/proposed/erw-local-model-evaluation/00_proposal.md),
picked this up and ran the spike for real, not simulated - and has kept
accumulating real evidence ever since, tracked as a running series of
"Decision 3 update" sections rather than a single verdict.

## The architectural choice: `base_url`, not a new backend class

The proposal's Decision 1 considered building a dedicated `OllamaBackend`
class versus extending the existing `OpenAIBackend` with an optional
`base_url` constructor parameter. A new class would have been explicit,
but it would have duplicated nearly all of `OpenAIBackend`'s translation
logic, since Ollama's `/v1/chat/completions` endpoint already speaks the
OpenAI-compatible wire format - and it would need a sibling class for
every other OpenAI-compatible local server (vLLM, LM Studio) that shows
up later. The proposal chose `base_url` instead: one runtime satisfies
the "point an existing OpenAI-shaped client at a different host" case for
any OpenAI-API-compatible server, confirmed for Ollama and advertised by
vLLM and LM Studio too. Omitting `base_url` leaves real OpenAI API
behavior completely unchanged - this is an opt-in override, not a mode
switch. See
[`docs/how-to/local-openai-endpoint.md`](../how-to/local-openai-endpoint.md)
for how to actually use it, and
[`docs/reference/llm-backend.md`](../reference/llm-backend.md) for the
full constructor reference.

Decision 2 made a parallel choice about where the evaluation code itself
lives: `lcats/experimental/model_comparison/`, following the
`experimental/` convention (real, runnable code not yet a production
dependency) rather than `notebooks/` (exploratory, not meant to be
re-run as a suite) or `KMo/` (a collaborator's separate test code). Each
candidate model gets its own directory with a `README.md`, a `setup.py`
(prerequisite check only - it never downloads or installs anything), and
a `benchmark.py` that builds an `LLMBackend` and calls a shared harness.
The harness runs the pipeline's *actual* tool schemas - stage-3 entity
extraction against a real, fixed ~600-word segment drawn from
`corpora/sherlock/five_orange_pips/story.json`, and genre detection and
scene/sequel segmentation against the same story's full text
(`DEFAULT_SAMPLE_STORY`), matching what each stage's real production call
path actually receives - not synthetic schemas or a toy prompt. See
[`experimental/model_comparison/README.md`](../../experimental/model_comparison/README.md)
for the harness's full layout and how to add a new candidate.

## What the evidence actually shows

Nine candidates have now been run for real against this harness:
`anthropic_opus` (the frontier baseline), `anthropic_haiku`,
`openai_gpt55`, `gemini_flash`, and five local Ollama models
(`gemma4:12b`, `deepseek-r1:14b`, `qwen3:8b`, `qwen3:30b-a3b`, and
`gpt-oss:20b`). The picture that emerges is not "local models work" or
"local models don't work" - it splits sharply by pipeline stage and by
model family, and even the online frontier candidates surfaced real bugs
along the way.

### A methodology mistake almost produced the wrong answer

The harness's very first runs against `qwen3:8b` sent the model the
*entire* ~7,300-word story instead of a single scene/sequel segment - a
mismatch with `entity_extractor.py`'s own system prompt, which describes
its input as "a segment of a story," and with what `run_pilot.py` ever
actually sends the extractor in production. Combined with an unrelated
sampling-temperature error (the harness inherited `entity_extractor.py`'s
Anthropic/OpenAI-tuned `temperature=0.2`, well below Qwen3's own
documented recommendation of 0.6, which explicitly warns against
greedy-decoding settings like 0.2), the first two runs produced one
outright failure and one successful-but-29-minute run - an "unreliable"
verdict. Once both were fixed, `qwen3:8b` succeeded consistently across 3
runs at roughly 1.5-2.2x `claude-opus-4-8`'s latency, with fewer
extracted entities (11-14 vs. Opus's 21 - not evaluated for precision or
recall, since the harness has no human ground-truth entity list). The original
"unreliable" conclusion was substantially an artifact of the harness, not
a stable property of the model - a reminder that the raw numbers below
are only as trustworthy as the methodology that produced them, and worth
reading each candidate's own README before trusting a headline verdict.

### Genre detection: the strongest case for a local model

Every local candidate that reached genre detection succeeded, repeatedly.
`qwen3:8b` detected "mystery" correctly 2/2, and `gpt-oss:20b` did the
same 3/3 in `WI-LLM-0063`. `gpt-oss:20b`'s genre-detection result was
then scale-tested (`WI-LLM-0066`) against a real 20-story,
population-weighted, multi-genre sample via
`experiments/04_genre_census/run_census.py`'s new `--base-url` flag: 18/20
exact agreement with the existing Claude reference sample, at $0.00
measured cost and ~40.1s/story - a go/no-go recommendation of **go** for
a full local genre census, projecting ~20.8 hours of wall-clock for the
full ~1,868-story corpus versus the Claude sample's ~4.2-hour/~$435
projection. (Neither projection is a measured full-corpus run; both are
extrapolated from a smaller sample.) The 2 disagreements were both on
`humor`-labeled stories, a category too thinly represented in the
reference sample to call a systematic weakness. Genre detection is, so
far, the one stage where the evidence points cleanly toward preferring a
local model.

### Entity extraction: works at the API layer, but grounding is the catch

Anthropic's own second tier, `claude-haiku-4-5`, matched `anthropic_opus`'s
entity count at roughly half the latency and token spend on a single run
- a favorable, if thin, signal that didn't need any local infrastructure
at all. Among local candidates, `qwen3:8b` succeeded consistently (3/3)
once the methodology was fixed, and `gpt-oss:20b` succeeded at the raw
tool-call level 3/3 across two separate tranches (`WI-LLM-0056`,
`WI-LLM-0063`) - but with real variance the initial 2-run sample missed:
latency spanning 35-170s and entity counts spanning 12-34 on identical
input.

`WI-LLM-0064` then found that `gpt-oss:20b`'s apparent success was
misleading in a specific way: at its Ollama-bundled best configuration
(`temperature=1.0`), the model reliably called the extraction tool, but
every run emitted `mentions` as plain strings rather than the mention
objects the real production `build_entities()` call expects - 0 of 3
runs produced any *grounded* entities at all, despite 3/3 raw tool-call
success. `WI-LLM-0065` closed that specific gap with a candidate-scoped
compatibility adapter (`entity_shape_adapter.py`) that repairs the
observed malformed shapes - string entities, `name`/`entity` aliases,
string mentions, mention dicts using `text`/`surface` instead of
`quote` - only when the resulting text is already a verbatim substring of
the segment, without weakening `build_entities()`'s own quote-grounding
check. With the adapter in front of the unchanged production call, 3/3
runs were production-grounded, though grounded entity counts (11-16) and
latency (71-141s) remained uneven enough that the recommendation is to
consider `gpt-oss:20b` for entity extraction *only* behind that adapter,
pending a future precision/recall evaluation - not as a drop-in default.

Not every local family got even that far. `qwen3:30b-a3b` - tested as
the hypothesized "quality tier" upgrade over `qwen3:8b` - turned out to
be both slower (148-218s vs. 74-106s) and *less* reliable: 2 of 3 runs
returned near-empty or structurally-valid-but-essentially-useless results
(one entity each), the opposite of the recall improvement the hypothesis
predicted. `gemma4:12b` and `deepseek-r1:14b` failed the call outright,
2/2 each, in a pattern the harness's authors call "silent ignore":
`finish_reason='stop'` with real free-text content - JSON-shaped for
`gemma4:12b`, plain prose for `deepseek-r1:14b` - but no tool call ever
attempted. `WI-LLM-0051`'s reminder-retry mitigation (appending an
explicit "you must call the tool" instruction on a second attempt) helped
`gemma4:12b` partially (1 of 2 applicable retries recovered) but did
nothing for `deepseek-r1:14b` (0/3), even with a tuned temperature.
Meanwhile `openai_gpt55` never got a valid result at all: it surfaced a
genuine bug in the shared, production `ENTITY_TOOL_SCHEMA` itself -
`grammatical_role` is declared as a property but missing from its
`required` array, which OpenAI's strict-mode validator rejects outright
while Anthropic's does not enforce the same completeness rule. That bug
lives in `entity_extractor.py`, affects every real caller of
`make_entity_extractor()`, and was deliberately left unfixed as
out-of-scope for the evaluation work itself.

`gemini_flash` looked, at first, like a third distinct failure mechanism
- "active filter rejection," where Gemini's own compat-layer returns
`finish_reason: 'function_call_filter: MALFORMED_FUNCTION_CALL'` after
apparently attempting the call. `WI-LLM-0062` traced this to a token
budget, not schema complexity as originally hypothesized: the identical,
unmodified schema succeeded reliably (3/3) once given `max_tokens=32000`,
after failing at 8192 and 16384 - most likely because Gemini's internal
"thinking" consumption shares the same token budget as the visible
completion. A review finding on the harness's own evidence caught that
what looked like one combined "tool_choice gap" across `gemma4:12b`,
`deepseek-r1:14b`, and `gemini_flash` was actually two genuinely
different mechanisms (silent ignore vs. active filter rejection) needing
different fixes - a useful correction against over-generalizing from
surface symptoms.

### Segmentation: not viable on any local candidate tested so far

Every local model tested against scene/sequel segmentation has failed it,
though not always the same way. `qwen3:8b` and `qwen3:30b-a3b` both hit
the plain silent-ignore pattern (0/5 combined baseline attempts across 2
models and 2 stories) - the model's free text visibly begins a
well-formed, schema-shaped JSON object, but `tool_choice` never actually
invokes `record_segments`. The reminder-retry mitigation helps here too,
but only partially: 2 of 5 retries succeeded (40%) for `qwen3:8b`, later
pooled with a further 0/3-eager-reminder sample from `WI-LLM-0059` to a
combined ~25% success rate - real, but far from reliable.

`gpt-oss:20b` found a *new* failure mode on this stage (`WI-LLM-0063`):
its baseline call ignores `tool_choice` the same way, but the automatic
reminder retry does succeed in getting the tool actually invoked - and
then the resulting segment fails the segmenter's own downstream alignment
check, because its anchor text isn't a verbatim substring of the source
story. This is a quality failure *after* a successful tool call, not a
tool-invocation failure at all, and it persisted even with an explicit
verbatim-quote reminder added in `WI-LLM-0064` (0/6 usable results across
both variants: ellipses, invented text, case drift, and paraphrased
boundaries were the recurring problems). Segmentation remains, across
every local candidate and every mitigation tried, an Anthropic-only
stage.

One further, narrower question got asked and answered along the way:
would the segmentation reminder help if it were baked permanently into
the real, shared production `SCENE_SEQUEL_SYSTEM_PROMPT`, not just the
harness's own retry copy? `WI-LLM-0059` tested this directly and found
the local-model effect held (~25% combined success for `qwen3:8b`, same
order as the harness-scoped retry) but also found a small, real side
effect on the Anthropic frontier path: no success-rate or latency
regression across 3 paired real calls, but 2 of 3 modified-condition runs
split the story's ending into an extra segment (baseline stayed at 4
segments all 3 times; modified produced 4, 5, 5) - a mild tension with
the production prompt's own "prefer FEWER, LARGER segments" instruction. The OpenAI/`gpt-4o` frontier leg could
never be verified either way: across 3 real, credits-enabled attempts,
`gpt-4o` reproducibly hit its own hard 16384-completion-token ceiling on
the baseline condition and failed every time on the modified condition
too. Per the work item's own acceptance criteria, an unverified frontier
path forces a no-change outcome regardless of how the other legs looked
- `SCENE_SEQUEL_SYSTEM_PROMPT` was not edited.

## The emerging per-stage picture

Putting the evidence together, the shape that has held up across the
most scrutiny (the `gpt-oss:20b` arc, tracked end-to-end as
[`WS-GPT-OSS-20B-EVALUATION`](../../project/workstreams/resolved/WS-GPT-OSS-20B-EVALUATION.md))
is a per-stage split, not a per-model verdict:

- **Genre detection** is the strongest local-model case: cheap, fast, and
  now validated at pilot multi-story scale, not just a single story.
- **Entity extraction** is usable, but only cautiously and only behind
  candidate-specific handling - a local model can call the right tool
  reliably while still returning output the production code can't
  consume without a compatibility layer.
- **Segmentation** has not worked on any local candidate tried, across
  three different failure mechanisms and two different mitigation
  attempts.

None of this evidence has changed the ERW pipeline's actual default
backend or model. Every constituent work item in this lineage explicitly
excluded that as a non-goal - the harness exists to gather evidence for a
future decision, not to make one by side effect. A hybrid pipeline
(local model for the stages that hold up, frontier model for the ones
that don't) remains the most plausible direction the evidence points
toward, but adopting it would need its own follow-on proposal or
amendment, not an inference from these results alone.

## What's still open

The evaluation work is deliberately narrow in scope, and several
questions remain genuinely unanswered rather than quietly assumed:

- Whether a smaller or differently-shaped tool schema would sidestep the
  Ollama `tool_choice` gap entirely, and whether Ollama's native
  `/api/chat` endpoint (untested throughout this lineage) behaves better
  than the OpenAI-compatible one used everywhere here.
- Why the segmentation reminder only helps roughly a quarter to two-fifths
  of the time rather than reliably, for the models where it helps at all.
- Whether `gpt-oss:20b`'s entity-extraction output is good enough in a
  precision/recall sense - not just "successfully grounded" - to be worth
  routing any real traffic to, once the candidate-scoped adapter is in
  place.
- The Kubuntu Focus/NVIDIA hardware profile and MLX (Apple-Silicon-native
  tool calling) remain entirely untested; every *local-model* result on
  this page comes from Ollama on an Apple Silicon Mac (the online-provider
  results - Anthropic, OpenAI, Gemini - are unaffected by this gap).
- `WI-LLM-0074` is a **proposed, not yet executed** follow-up that would
  wire `experiments/05_metadata_genre_prefilter/run_prefilter.py`'s
  `--validate` mode to the same local-backend pattern
  `WI-LLM-0066` proved for `run_census.py`, and run it over the *exact*
  146-story genre-balanced sample `WI-GENRE-0004` already validated with
  real Opus calls - closing a sample mismatch that left the existing
  20-story local genre-census result only suggestively, not directly,
  comparable to that later validation. As of this page, that work has not
  run.

## See also

- [`docs/how-to/local-openai-endpoint.md`](../how-to/local-openai-endpoint.md)
  - the steps for pointing `OpenAIBackend` at a local server.
- [`docs/reference/llm-backend.md`](../reference/llm-backend.md) - the
  full `LLMBackend`/`OpenAIBackend` constructor reference.
- [`project/design/proposals/proposed/erw-local-model-evaluation/00_proposal.md`](../../project/design/proposals/proposed/erw-local-model-evaluation/00_proposal.md)
  (`PROP-ERW-LOCAL-MODEL-EVALUATION`) - the governing design proposal and
  its running evidence log.
- [`project/workstreams/resolved/WS-GPT-OSS-20B-EVALUATION.md`](../../project/workstreams/resolved/WS-GPT-OSS-20B-EVALUATION.md)
  - the `gpt-oss:20b` vet-diagnose-fix-scale arc.
- [`experimental/model_comparison/README.md`](../../experimental/model_comparison/README.md)
  - the benchmark harness itself: layout, methodology, and how to add a
  new candidate.
