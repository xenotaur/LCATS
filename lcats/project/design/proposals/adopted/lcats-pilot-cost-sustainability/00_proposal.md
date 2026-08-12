---
id: PROP-LCATS-PILOT-COST-SUSTAINABILITY
type: design_proposal
title: Making the Event-Role-World Pilot Sustainable to Run — Test Harness, Caching, Batching, and Model Tiering
status: adopted
created_on: 2026-08-05
updated_on: 2026-08-10
implementation_status: not_started
implemented_by: []
supersedes: []
superseded_by: null
related_design:
  - lcats/project/audits/2026-07-27-erw-pipeline-structured-output-reliability-audit.md
  - lcats/project/design/proposals/adopted/lcats-pipeline-checkpointing/00_proposal.md
  - lcats/project/design/proposals/adopted/lcats-event-role-world-extractor/00_proposal.md
  - lcats/project/design/proposals/proposed/erw-local-model-evaluation/00_proposal.md
  - lcats/project/design/backlog.md
---

## Summary

Two real runs of the cross-segment relation pilot
(`experiments/03_cross_segment_relation_pilot/run_pilot.py`) spent $67.54
combined ($42.80 on the first, $24.74 on a second, incomplete follow-up),
mostly discovering and fixing bugs rather than producing usable data. This
proposal adopts a sequenced set of changes — a
targeted single/small-story test harness first, then evaluation gates (not
yet adoptions) for Anthropic prompt caching, the Batch API, and per-stage
model tiering — to make the pilot cheap enough to iterate on and validate
before committing to a full, expensive real run.

## Background / Motivation

This is not a new problem.
`lcats/project/audits/2026-07-27-erw-pipeline-structured-output-reliability-audit.md`'s
Category E (lines 288-425) raised the identical concern ten days ago: "the
real pilot run has spent roughly $15 of its ~$50 budget so far — not
sustainable for routine dogfooding" (line 291-292), and explicitly deferred
it: "revisit this file once that run completes, discuss, and only then
spin up the actual work item(s)/workstream/design proposal" (lines 18-20).
`WS-PIPELINE-CHECKPOINTING` (closed 2026-08-03) resolved Category E2
(checkpointed, resumable runs). This proposal is the deferred follow-through
on the rest of Category E, now with fresh, concrete evidence.

That evidence, from this session's two real runs against
`corpora/`/`lcats/data`:

- A real run cost $42.80 for a 5-per-genre sample with a ~78% exclusion
  rate (4 of 18 sampled stories survived).
- A follow-up run, after fixing the exclusion-causing bugs, cost another
  $24.74 before being stopped mid-story over a genuinely unexplained
  "Invalid request data" API rejection (`lcats/project/design/backlog.md`,
  "Discourse extraction truncated..." entry, lines 230-288).
- Direct inspection of `processor.py:61-230` shows the ERW-extraction
  stage issues ~4 independent LLM calls per segment (entity, event/anchor,
  relation, discourse — `processor.py:124-220`), against real per-story
  segment counts of 4-8 (computed from `pilot_usage.jsonl`'s pass-record
  counts), for ~26 LLM calls per story — versus 1 call for segmentation
  (`run_pilot.py:427-444`). This ~26x fan-out, not merely "events are
  denser than scenes," is the primary architectural cost driver.
- Direct inspection of `llm_extractor.py` and `AnthropicBackend.complete`
  confirmed zero use of Anthropic's prompt caching (`cache_control`)
  anywhere in the codebase at the time this proposal was written, despite
  each segment's 4 extractor calls independently resending the identical
  `segment_text`.
- `run_pilot.py:1153`'s `--model` flag is single and global —
  genre-detection and segmentation (comparatively simple tasks) run on the
  same top-tier, most-expensive model as the nuanced extraction stages,
  with no code path to do otherwise.
- The pipeline uses only the non-batch Messages API (streaming via
  `messages.stream`, or blocking via `messages.create` when streaming is
  disabled in `AnthropicBackend.complete`), not the Batch API. Anthropic's
  Batch API is documented to cut cost 50% flat for exactly this workload's
  shape (bulk, non-interactive, tolerant of async turnaround) —
  `platform.claude.com/docs/en/build-with-claude/batch-processing`.
- `lcats/project/design/backlog.md`'s own "pilot_usage.jsonl doesn't track
  genre-detect or segmentation cost at all" (P2) and "Pilot's default
  parameters optimize for full genre coverage, not minimum-cost validation"
  (P3) entries are direct, already-recorded instances of this same gap.

A prerequisite pain point compounds all of this: there is no cheap way to
validate a fix or a design change against the real API. `--dry-run` uses a
fake backend and produces meaningless output; every real-API test today
means running the full pipeline at full sample size, which is how a schema
bug, two truncation bugs, and an unexplained API rejection all cost tens of
dollars each to discover this session.

## Prior Art Check

### Duplication search

- In-repo: No existing implementation of prompt caching, Batch API
  integration, model tiering, or a targeted single-story test harness
  (grepped `src/`, `project/design/proposals/`, `.claude/skills/` for
  `cache_control`, `batch api`, `model tiering` — no hits).
- Sibling repos: None identified.
- External libraries: None needed — prompt caching and the Batch API are
  both native features of the `anthropic` SDK this project already depends
  on (`pyproject.toml:27`), not separate dependencies.
- Recommendation: Proceed.

### Demand search

- Work items: None found proposing this directly.
- Proposals: None found.
- Backlog: Found — `lcats/project/design/backlog.md`'s "Pilot's default
  parameters optimize for full genre coverage, not minimum-cost validation"
  (P3) and "pilot_usage.jsonl doesn't track genre-detect or segmentation
  cost at all" (P2) entries are both direct instances this proposal
  addresses. Also found the originating demand:
  `lcats/project/audits/2026-07-27-erw-pipeline-structured-output-reliability-audit.md`'s
  Category E explicitly requests "the actual work item(s)/workstream/design
  proposal" (line 19) once the deferred discussion happens — this proposal
  is that discussion's output.
- Recommendation: Offer to close/link the two backlog entries and Category
  E's remaining scope once the resulting workstream/work items exist.

## Design Decisions

### Decision 1: Sequencing — validate cheaply before optimizing cost

**Question:** In what order should these changes land, given limited real-API
budget to validate each one?

**Options considered:**
- Attempt all changes at once in a single large PR.
- Attempt the highest-theoretical-impact change first (Batch API's flat
  50%, or local models' near-zero marginal cost).
- Build the ability to validate cheaply first, then layer in free/low-risk
  wins, then evaluate the higher-effort/higher-uncertainty options.

**Chosen: the third.** Every option below needs to be validated against the
real API to know if it actually helps this specific pipeline (a
well-known industry pattern — e.g. model tiering — is not a substitute for
evidence here, since this session already showed the *best* available
model struggling with reliable structured output under real conditions).
Validating anything right now costs a full expensive run. Building the
targeted test harness first is a prerequisite, not just one item among
equals.

### Decision 2: A targeted, retargetable single/small-story integration test harness

**Question:** How do we validate a pipeline change without paying for a
full sample run?

**Options considered:**
- A wholly new, separate test script.
- Extend `run_pilot.py` itself with a `--story`/`--story-list` flag that
  bypasses `build_stratified_sample` and calls `run_story()` directly.

**Chosen: extend `run_pilot.py`.** `run_story()` (`run_pilot.py:907-1105`)
already operates on exactly one story at a time; `main()`'s loop
(`run_pilot.py:1264-1330`) just calls it once per sampled story.
`_build_erw_extractors`, `_make_nlp_backend`, `_build_backend`, and the
checkpoint plumbing are already story-agnostic. A new script would
duplicate all of this. The harness needs: (a) a small, fixed, offline,
git-committed fixture set (e.g.
`experiments/03_cross_segment_relation_pilot/fixtures/`, 1-3 real short
stories) as the zero-config default; (b) a `--story
<collection/name>`/`--story-list <file>` flag targeting any real story,
not just the fixture set, since results are stochastic and a specific
failing story (e.g. `calling_the_empress__smith`) needs to be reproducible
directly; (c) explicit per-stage cost/timing reporting, closing the
`pilot_usage.jsonl` gap (backlog P2) for at least this harness's own runs;
(d) an explicit answer for how a targeted run gets the `genre` argument
`run_story(path, genre, ...)` requires (`run_pilot.py:907-918`) — bypassing
`build_stratified_sample` (`run_pilot.py:313-424`) also bypasses the only
code path that classifies a candidate and supplies that argument, so this
needs to be decided at implementation time (e.g. an explicit `--genre`
flag, one genre-detect call per targeted story, or an explicit
not-yet-classified sentinel), not left implicit.

### Decision 3: Evaluate, don't yet adopt, Anthropic prompt caching

**Question:** Can the confirmed redundant-input pattern (identical
`segment_text` resent 4 times per segment, `processor.py:124-220`) be
eliminated without changing model, calls, or output quality?

**Options considered:**
- Do nothing.
- Add `cache_control: {"type": "ephemeral"}` markers in
  `AnthropicBackend.complete`'s request construction, on the system
  prompt and/or the shared segment-text prefix.

**Originally chosen "adopt caching" — downgraded to "evaluate" after
review.** The initial framing assumed caching the shared `segment_text`
across the 4 per-segment extractor calls (entity/event/relation/discourse)
would produce cache reads on 3 of the 4. That assumption does not hold:
Anthropic's prompt-caching docs
(`platform.claude.com/docs/en/build-with-claude/prompt-caching`) define
cache prefixes in strict hierarchical order — `tools`, then `system`, then
`messages` — and state that changing tool definitions invalidates the
entire cache, tools/system/messages alike. `AnthropicBackend.complete`
(`lcats/src/lcats/llm/anthropic_backend.py`) sends a single, different
`tool` per call (`ENTITY_TOOL_SCHEMA`, `EVENT_TOOL_SCHEMA`, and so on —
`entity_extractor.py:16`, `event_extractor.py:17`, confirmed distinct per
extractor), so the 4 per-segment calls can never share a cache hit with
each other regardless of how identical their `segment_text` is — each
uses a different tool, which invalidates everything downstream before
`system`/`messages` are ever consulted.

The real, narrower opportunity is caching the (comparatively small) stable
`tools`+`system` prefix *within one extractor type*, reused across every
call of that same extractor across different segments and different
stories in a run — not the large, per-segment `segment_text`, which
varies every call regardless of extractor and is therefore never a stable
cache prefix under this pipeline's current call shape.

WI-PILOT-0057 measured that narrower opportunity on 2026-08-10 against
the WI-PILOT-0051 fixture set
(`experiments/03_cross_segment_relation_pilot/results/caching_eval/caching_comparison.json`),
using `claude-opus-4-8`, the real interleaved per-segment call order, and
the existing 5-minute prompt-cache TTL. The run covered 2 fixture stories,
3 real segments, and 13 measured ERW calls per comparison arm. Preflight
`tools`+`system` prefix counts were: entity 947 tokens, event 1,333,
relation 821, discourse 1,356, and story_relation 1,010. With Anthropic's
current 1,024-token minimum cacheable prompt length for Opus 4.8, only the
event and discourse prefixes were cacheable. The enabled arm observed
2,539 `cache_creation_input_tokens` and 5,078 `cache_read_input_tokens`;
entity, relation, and story_relation correctly stayed at zero cache tokens.
Measured costs were $0.6206 with caching disabled and $0.5702 with
caching enabled, for an observed delta of -$0.0504 (-8.1%) on this tiny
fixture run. Because output generation is nondeterministic and differed
between arms, the directly attributable input/cache component should be
computed from the enabled arm's identical requests: pricing its 27,033
effective input/cache tokens as ordinary input would cost $0.1352, versus
$0.1155 with caching, a -$0.0197 input-side delta.

Recommendation: **go** for a follow-on pilot-level adoption path that
enables prompt caching explicitly for Anthropic ERW fixture/pilot runs,
while keeping `AnthropicBackend(enable_prompt_caching=False)` as the global
default. Do not pad short entity/relation/story_relation prefixes merely
to force cacheability, and do not assume the originally imagined
per-segment `segment_text` sharing exists; the measured benefit is real
but limited to same-extractor `tools`+`system` prefix reuse.

Separately, Anthropic's "mid-conversation tool changes" beta
(`platform.claude.com/docs/en/about-claude/models/whats-new-opus-5`) —
"add or remove tools between turns of a conversation while preserving the
prompt cache" — is a genuinely relevant alternative worth investigating,
since it targets exactly this per-call-different-tool constraint, but it
would mean restructuring the 4 independent calls into one multi-turn
conversation per segment (a real architecture change, and still a beta
feature) — not something to assume works today.

### Decision 4: Evaluate, don't yet adopt, the Batch API

**Question:** Should the pipeline move to Anthropic's Batch API for its
flat, documented 50% discount?

**Options considered:**
- Adopt immediately.
- Reject because asynchronous batch submission conflicts with the current
  synchronous checkpointing model.
- Evaluate first as a distinct, gated decision.

**Chosen: go for a follow-on batch-mode design, not immediate adoption.**
WI-PILOT-0058 completed the gated assessment on 2026-08-10, reusing
WI-PILOT-0057's landed real baseline rather than making any new paid API
calls. The baseline was the disabled-caching arm of
`experiments/03_cross_segment_relation_pilot/results/caching_eval/caching_comparison.json`:
`claude-opus-4-8`, 2 WI-PILOT-0051 fixture stories, 3 real segments, 13
ERW calls, 26,959 input tokens, 19,431 output tokens, and exact recorded
cost $0.62057. Applying Anthropic's documented Batch API pricing (50% of
standard API prices for both input and output tokens) projects that same
fixture workload at about $0.3103, a savings of about $0.3103. The same
multiplier would have saved about $33.77 against the $67.54 combined
historical pilot spend cited in this proposal, before any prompt-caching or
model-tiering effects.

The economics are therefore strong, but the architecture cost is real.
`lcats/src/lcats/utils/checkpoint.py` is a synchronous publication helper:
callers validate `(working_root, source_root)` with `resolve_roots`, compute
one caller-defined fingerprint for one `(item_id, stage)`, check
`read_checkpoint`, perform the expensive work if the checkpoint is not a
matching recorded success, and immediately publish a JSON record via
`write_checkpoint` using same-directory temp-file creation plus
`os.replace`. A recorded failure is deliberately not treated as done, a
fingerprint mismatch is treated as absent, and the helper does not know
anything about outstanding remote work. That model is a good fit for
`run_pilot.py`'s current stage-then-checkpoint flow: genre detection,
segmentation, ERW extraction, and cross-segment relation each become
durable as soon as the local call path returns.

Anthropic's Message Batches API has a different shape. It creates a batch
of Messages requests, processes them asynchronously, and exposes results
only after the batch ends. A batch-aware pilot should therefore not pretend
that `read_checkpoint`/`write_checkpoint` alone are enough. It would need a
parallel durable batch ledger recording submitted request `custom_id`s,
their mapped story/segment/stage identities, request fingerprints, batch
IDs, and retry/failure state before the process exits or polls. Only after
`client.messages.batches.results()` returns should the existing per-stage
checkpoint records be published. Without that ledger, a crash after submit
but before result ingestion could lose track of paid remote work; without
the existing final checkpoint publication, a resumed run would lose the
per-stage reproducibility and stale-fingerprint protections
`WI-PIPELINE-0040`/`0041` intentionally added.

Much of Decision 3 of `PROP-LCATS-PIPELINE-CHECKPOINTING` can survive, but
at coarser boundaries. Dependencies still force waves: event extraction
depends on entity extraction, relation and discourse depend on the event
output, and cross-segment relation depends on the story's accumulated ERW
output. A batch implementation can checkpoint after each completed wave,
and can still preserve per-story/per-stage artifacts once results are
ingested. It cannot preserve today's exact "one call returns, immediately
write that stage's result" semantics while the remote batch is still in
progress. Partial-progress recovery would move from checkpoint files to the
new batch ledger until the batch finishes.

The progress/visibility tradeoff is acceptable for this project only if it
is explicit. The current local workflow prints concrete progress such as
genre-detect hits, "Running pipeline: [genre] story", per-story exclusions,
and final output paths as the synchronous loop advances. Anthropic's Batch
API instead reports overall `processing_status` (`in_progress`,
`canceling`, `ended`) while polling; `request_counts` can show aggregate
batch-level counts, but the final succeeded/errored/canceled/expired
buckets and per-request results are only usable once the batch ends, and
results are then streamed by `custom_id` rather than submission order. For
a single-researcher, non-interactive pilot this is a reasonable exchange
for a flat 50% discount, especially because most runs are not
latency-sensitive. It is still worse interactive debugging visibility than
the current path, so the synchronous Messages API should remain the
default/local-debug mode until a batch mode has its own clear console
status and resumable ledger.

Recommendation: **go** for a separate follow-on work item that designs and
implements an explicit opt-in Batch API mode for fixture/pilot runs. That
item should keep the synchronous checkpointed path intact, add a durable
submit/poll/result-ingestion ledger rather than retrofitting
`checkpoint.py` by default, and validate that batch-mode output
publication preserves the existing per-stage checkpoint artifacts after
ingestion. Do not implement Batch API adoption inside this assessment item.

### Decision 5: Evaluate, don't yet adopt, per-stage model tiering

**Question:** Should genre-detection and segmentation (comparatively
low-complexity tasks) move to a cheaper model tier, reserving the top-tier
model for entity/event/relation/discourse/cross-segment extraction?

**Options considered:**
- Adopt a specific cheaper model now.
- Evaluate empirically first, using the Decision 2 harness.

**Chosen: go, bounded to genre-detection and segmentation, after real
measurement.** Anthropic's current model-comparison pricing
(`platform.claude.com/docs/en/about-claude/pricing`, verified 2026-08-10)
shows the relevant spread: Claude Opus 4.8 at $5/$25 per MTok versus Claude
Haiku 4.5 at $1/$5 per MTok. `WI-PILOT-0060` added per-stage model overrides
to `run_pilot.py` so this can be evaluated without changing the global model
default.

The real bounded comparison
(`experiments/03_cross_segment_relation_pilot/results/model_tiering_eval/model_tiering_comparison.json`)
ran against the two `WI-PILOT-0051` fixture stories, using a separate
validated genre ground-truth file rather than the fixture manifest's
unvalidated plumbing labels. It made 8 real Anthropic generation calls:
2 models x 2 stories x 2 stages. Results:

- Baseline `claude-opus-4-8`: 18,748 input tokens, 2,365 output tokens,
  measured cost $0.152865; genre-detect raw/schema validity 2/2, genre
  accuracy 2/2, truncation 0/2, secondary-genre sanitization 0/2;
  segmentation schema validity 1/2, truncation 0/2. The segmentation miss
  was an alignment failure on `king_of_the_hill` (`segment_id=2` anchor text
  not found), not truncation.
- Candidate `claude-haiku-4-5-20251001`: 14,358 input tokens, 2,106 output
  tokens, measured cost $0.024888; genre-detect raw/schema validity 2/2,
  genre accuracy 2/2, truncation 0/2, secondary-genre sanitization 1/2;
  segmentation schema validity 2/2, truncation 0/2.
- Cost delta: -$0.127977 on the fixture set, an 83.72% reduction for these
  two stages in this run.

Caveat: both Opus 4.8 and Haiku 4.5 marked `king_of_the_hill` as
`wellformed: false` while the WI-PILOT-0060 ground truth marks it
wellformed. That does not change this decision's genre-detection metric,
because `run_pilot.py`'s genre-detect scan consumes `detected_genre`, not
`wellformed`, but it is a reminder not to treat the assessment call as a
complete corpus-QA substitute. Haiku also produced one schema-valid but
sanitized `secondary_genre` value containing leaked tool-call syntax; this
did not affect the consumed `detected_genre` signal, but it is real evidence
that cheaper-tier structured-output reliability is not perfect.

Recommendation: adopt Haiku 4.5 for the pilot's genre-detection and
segmentation stages in a follow-on configuration/defaulting change only if
that change keeps the existing assessment sanitization/telemetry visible,
while continuing to reserve the top-tier model for entity/event/relation/
discourse/cross-segment extraction. This decision does **not** default model
tiering on in `WI-PILOT-0060`; every stage still uses the global model unless
an explicit per-stage override is supplied.

### Decision 6: Reject fusing the 4 per-segment extractor calls

**Question:** Should entity/event/relation/discourse be combined into
fewer, larger calls to reduce the ~26-call-per-story fan-out directly?

**Options considered:**
- Merge some or all of the 4 stages into fewer calls with a combined
  schema.
- Reject this direction; leave the 4-stage decomposition as-is.

**Chosen: reject.** `PROP-LCATS-EVENT-ROLE-WORLD-EXTRACTOR` (adopted)
decomposed extraction into these 4 focused stages specifically for
reliability — larger, more complex single-call schemas need more
`max_tokens` headroom and are exactly the shape that produced this
session's malformed-container bug and repeated truncation failures.
`processor.py:149-155,180-183,207-210` also shows a real extraction
dependency (entity IDs feed event extraction, event IDs feed
relation/discourse), so merging is a genuine redesign of the extraction
sequence, not a schema
union. No new evidence has emerged to justify revisiting this.

### Decision 7: Local-model evaluation is a separate, parallel track

**Question:** Should local-model support (for Mac/Apple Silicon and
Kubuntu Focus hardware) be part of this proposal's scope?

**Chosen: no — reference only.** Local models have the largest theoretical
cost ceiling (near-zero marginal cost) but the least validated reliability
for this pipeline's specific tool-use/strict-schema requirements, and
genuinely different research questions (runtime choice, hardware
constraints, hybrid-vs-full-swap design) than the four decisions above.
This is already scoped as a separate research effort, tracked as its own
proposal:
`lcats/project/design/proposals/proposed/erw-local-model-evaluation/00_proposal.md`
(`PROP-ERW-LOCAL-MODEL-EVALUATION`, still `proposed`) — that proposal
should report its own findings independently rather than being folded
into this proposal's implementation plan.

## Non-Goals

- Does not adopt prompt caching, the Batch API, or model tiering outright
  — all three are gated evaluation decisions (Decisions 3, 4, 5), not
  commitments.
- Does not merge or redesign the entity/event/relation/discourse extraction
  sequence (Decision 6, rejected).
- Does not implement or evaluate local-model support — a separate,
  parallel track (Decision 7).
- Does not change the checkpointing architecture itself
  (`WI-PIPELINE-0040`/`0041`) — any Batch API work is scoped as an
  extension, evaluated on its own terms.
- Does not re-scope `WI-EVENT-0030`'s stratified pilot for 8 genres — that
  is `WI-ASSESS-0031`'s and the genre-reconciliation backlog entries'
  concern, tracked separately.
- Does not adopt OpenTelemetry or a workflow-orchestration framework
  (Prefect/Dagster/Airflow) for cost logging — the 2026-07-27 audit's own
  Category E1 table already considered and set these aside as overkill for
  a single-researcher local pipeline; nothing here revisits that.

## Implementation Plan

This spans at least four distinct, sequenced pieces of work with real
dependencies between them (the harness gates validation of everything
after it; the Batch API and model-tiering evaluations depend on the
harness and on each other's findings) — large enough for a governing
workstream, not a single work item. Proposed shape:

1. **Governing workstream** (`WS-*`, to be created via `/lrh-workstream`
   — the next pending action now that this proposal is adopted)
   coordinating the work items below.
2. **WI 1 — targeted test harness** (Decision 2): `--story`/`--story-list`
   flag on `run_pilot.py`, fixture set, per-stage cost reporting.
3. **WI 2 — prompt caching evaluation** (Decision 3): measure the real,
   narrower caching benefit (or the mid-conversation-tool-changes
   alternative) against WI 1's fixture set given the per-call
   different-tool-schema constraint; only proceeds to `cache_control`
   adoption in `AnthropicBackend.complete` if it shows a real, worthwhile
   saving.
4. **WI 3 — Batch API evaluation** (Decision 4): go/no-go assessment,
   using WI 1's (and, if it lands, WI 2's) now-measurable baseline; only
   proceeds to implementation if the assessment favors it.
5. **WI 4 — model tiering evaluation** (Decision 5): per-stage `--model`
   support plus real output-quality comparison against WI 1's fixtures;
   only proceeds to adoption if quality holds.

## Open Questions

- Whether WI 3 (Batch API) and WI 4 (model tiering) should be sequential
  or can run in parallel once WI 1/2 land — deferred to workstream
  scoping.
- Whether the fixture set for WI 1 should be drawn from existing
  `corpora/` stories or purpose-built synthetic ones — deferred to WI 1's
  own scoping (this proposal only decides that a fixture set exists and is
  git-committed, not its exact contents).

## Cross-References

- `lcats/project/audits/2026-07-27-erw-pipeline-structured-output-reliability-audit.md`
  — Category E, the originating, explicitly-deferred request this
  proposal fulfills.
- `lcats/project/design/proposals/adopted/lcats-pipeline-checkpointing/00_proposal.md`
  — the just-adopted checkpointing design this proposal's Batch API
  evaluation (Decision 4) must reconcile with.
- `lcats/project/design/proposals/adopted/lcats-event-role-world-extractor/00_proposal.md`
  — the 4-stage decomposition Decision 6 declines to revisit.
- `lcats/project/design/proposals/proposed/erw-local-model-evaluation/00_proposal.md`
  (`PROP-ERW-LOCAL-MODEL-EVALUATION`) — the separate local-model track
  Decision 7 defers to.
- `lcats/project/design/backlog.md` — "pilot_usage.jsonl doesn't track
  genre-detect or segmentation cost at all" and "Pilot's default
  parameters optimize for full genre coverage, not minimum-cost
  validation" entries, both addressed here.
