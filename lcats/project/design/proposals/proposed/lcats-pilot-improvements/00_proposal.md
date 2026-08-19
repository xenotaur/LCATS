---
id: PROP-LCATS-PILOT-IMPROVEMENTS
type: design_proposal
title: Stabilized, User-Facing ERW Pilot Improvements After Cost-Sustainability Evaluation
status: proposed
created_on: 2026-08-12
updated_on: 2026-08-12
implementation_status: not_started
implemented_by: []
supersedes: []
superseded_by: null
related_design:
  - lcats/project/design/proposals/adopted/lcats-pilot-cost-sustainability/00_proposal.md
  - lcats/project/workstreams/proposed/WS-PILOT-COST-SUSTAINABILITY.md
  - lcats/project/design/proposals/adopted/lcats-pipeline-checkpointing/00_proposal.md
  - lcats/project/audits/2026-07-27-erw-pipeline-structured-output-reliability-audit.md
  - lcats/project/design/backlog.md
---

## Summary

This proposal defines the follow-on implementation direction after
`PROP-LCATS-PILOT-COST-SUSTAINABILITY`: create a new
`WS-PILOT-IMPROVEMENTS` workstream that adopts measured pilot improvements
only after a first, explicit real-API/output stability gate proves the ERW
pilot can run end to end, produce well-formed and semantically meaningful
artifacts, meet a quality bar, and serve its intended research purpose at
bounded cost.

## Background / Motivation

`PROP-LCATS-PILOT-COST-SUSTAINABILITY` was created because two real
`experiments/03_cross_segment_relation_pilot/run_pilot.py` runs spent
$67.54 combined while mostly discovering bugs rather than producing usable
data. That proposal deliberately sequenced a cheap targeted harness first,
then evaluation gates for prompt caching, Batch API, and per-stage model
tiering rather than adopting those changes immediately.

Those evaluations have now produced useful recommendations, but they also
clarify a remaining risk: making the pilot cheaper is not enough if the
pilot can still produce a null or low-quality research result. The repo's
own history includes malformed structured output, truncation failures,
unexplained Anthropic `invalid_request_error` responses, and output
alignment failures. The most recent model-tiering measurement
(`WI-PILOT-0060`, PR #286) strengthened that evidence rather than retiring
it: Haiku 4.5 needed secondary-genre sanitization on one of two
genre-detection fixture runs, the Opus 4.8 segmentation baseline produced
one schema-invalid output from an anchor-text alignment failure, and both
models disagreed with validated genre ground truth on `king_of_the_hill`'s
`wellformed` flag. A cheaper bad run is still a bad run, and even the
top-tier path still needs a small real-output gate before the project
spends toward larger research runs.

The next implementation phase should therefore separate two concerns. First,
stabilize and validate the real end-to-end API/output path under a bounded
spend gate. Second, adopt the measured cost improvements and user-facing
ergonomics behind that stability gate. This keeps the project aligned with
the cost-sustainability proposal's core lesson: validate cheaply before
optimizing or scaling.

## Prior Art Check

### Duplication search

- In-repo: No existing `WS-PILOT-IMPROVEMENTS` workstream or equivalent
  pilot-improvement adoption proposal was found. Related but not duplicate:
  `WS-PILOT-COST-SUSTAINABILITY` governs the completed evaluation work, and
  `PROP-LCATS-PILOT-COST-SUSTAINABILITY` records the measured go/no-go
  conclusions for prompt caching, Batch API, and model tiering.
- Sibling repos: None identified.
- External libraries: None identified. The core work is LCATS/LRH control
  plane scoping plus `run_pilot.py` operational behavior; the cost levers
  are native Anthropic API features or existing CLI/model configuration.
- Recommendation: Proceed.

### Demand search

- Work items: Related resolved work exists:
  `WI-PILOT-0051` created the targeted fixture harness,
  `WI-PILOT-0057` evaluated prompt caching,
  `WI-PILOT-0058` evaluated the Batch API, and
  `WI-PILOT-0060` evaluated per-stage model tiering. None implements the
  follow-on adoption workstream or the prerequisite end-to-end quality gate.
- Proposals: `PROP-LCATS-PILOT-COST-SUSTAINABILITY` requests evaluation
  gates and records follow-on go recommendations, but explicitly does not
  adopt prompt caching, Batch API, or model tiering outright.
- Backlog: Matching demand exists in `project/design/backlog.md`:
  "`pilot_usage.jsonl` doesn't track genre-detect or segmentation cost at
  all" and "Pilot's default parameters optimize for full genre coverage, not
  minimum-cost validation." These are partly addressed by the targeted
  harness, but the broader need for a bounded real validation path remains.
- Evidence limits: The completed cost studies intentionally used tiny
  bounded samples. `WI-PILOT-0057` measured 13 calls per arm, `WI-PILOT-0058`
  reused that same real baseline, and `WI-PILOT-0060` measured eight real
  calls total across two stories, two stages, and two models. These are
  valid engineering gates for direction-setting, but they are not
  statistically robust estimates for larger pilot runs; the stability gate's
  story-set choice matters because it is the first chance to broaden that
  evidence without returning to unbounded spend.
- Recommendation: Link the new workstream to the resolved pilot evaluation
  WIs and offer to close or revise matching backlog entries only after the
  follow-on workstream scopes the remaining user-facing validation path.

## Design Decisions

### Decision 1: Create a follow-on implementation workstream

**Question:** Should the measured adoption work stay inside
`WS-PILOT-COST-SUSTAINABILITY`, be implemented as isolated work items, or
move into a new workstream?

**Options considered:**
- Keep `WS-PILOT-COST-SUSTAINABILITY` open until every go recommendation is
  implemented.
- Create isolated follow-on work items without a new umbrella.
- Create a new `WS-PILOT-IMPROVEMENTS` workstream for implementation and
  user-facing pilot ergonomics.

**Chosen: create `WS-PILOT-IMPROVEMENTS`.** The existing cost-sustainability
proposal and workstream were evaluation-shaped: build a harness, measure
cost levers, and record go/no-go recommendations. The next phase is
implementation-shaped and includes additional user-facing concerns:
validation mode semantics, quality gates, CLI ergonomics, spend gates,
telemetry, and possibly asynchronous Batch API architecture. That is too
broad for one work item, and too different from the evaluation workstream
to keep mixing under the same exit criteria.

### Decision 2: Put a real end-to-end stability and quality gate first

**Question:** What must happen before adopting any cost-saving defaults or
execution-mode changes?

**Options considered:**
- Adopt low-risk cost changes immediately, relying on the fixture evaluations.
- Run another broad pilot first.
- Add a first work item that stabilizes and validates the real end-to-end
  pilot API/output path under a bounded spend gate.

**Chosen: the stability gate first.** The project must know that the pilot
can run end to end and produce usable research output before optimizing
cost or scaling. This first work item should prove:

- The real Anthropic path completes on a bounded fixture or small story set.
- Output artifacts are well formed and parseable.
- Output makes semantic sense against the source stories.
- Quality is high enough to proceed, using thresholds defined before the
  real run.
- The result achieves the pilot's intended purpose, not merely "the script
  exited successfully."
- Genre detection is exercised explicitly, either by a bounded stratified
  selection path or by a direct real genre-detection check against validated
  ground truth. A targeted `WI-PILOT-0051` fixture run alone is insufficient
  for this criterion when it receives genre labels from CLI or fixture
  metadata instead of invoking the genre-detection stage.
- Real spend is estimated in advance, explicitly approved, and bounded.

This is not another open-ended tuning loop. A negative result is valid and
should block downstream adoption work until the named failure mode is fixed.

**Measured WI-PILOT-0067 outcome (2026-08-14): fail/no-go.** The bounded
two-story stability gate ran with explicit approval against
`claude-opus-4-8` on `king_of_the_hill` and `unwelcomed_visitor`. The run
spent 34,077 input tokens and 19,025 output tokens, for an estimated
`$0.6460`. Output artifacts were parseable and there were no fatal API
errors, but the gate did not satisfy the predeclared thresholds:
`unwelcomed_visitor` failed segmentation alignment
(`segment_id=2: anchor text not found in story text`) and therefore did not
reach ERW extraction, while the separate real genre/well-formedness check
classified both stories as science fiction but marked `king_of_the_hill`
`wellformed: false` / `verdict: review` because it appears to be an excerpt
with missing prior context. The one completed pipeline output was useful for
manual inspection, but a 1/2 completion rate and 1/2 independent
well-formedness pass do not prove the pilot can reliably produce usable
research output. Downstream adoption work remains blocked; the next item
should fix the fixture/pipeline stability failure and rerun a newly
predeclared gate rather than loosening thresholds or tuning prompts inside
this result.

### Decision 3: Adopt measured cost improvements only behind the gate

**Question:** Which cost-sustainability findings should become follow-on
implementation work?

**Options considered:**
- Adopt every go recommendation at once.
- Adopt only the smallest change.
- Sequence the measured improvements by risk and blast radius.

**Chosen: sequence by risk after the stability gate.**

Prompt caching should be a small follow-on adoption item. It has measured
but limited benefit, and `AnthropicBackend` already supports opt-in
`enable_prompt_caching`; the adoption work should expose it for pilot runs
without changing the global backend default or padding short prefixes.

Per-stage model tiering should also be a follow-on adoption item, limited
to genre detection and segmentation. The fixture evidence supports Haiku
4.5 for those stages, but adoption must preserve telemetry around
sanitization and schema/quality signals.

Batch API adoption should be a larger follow-on design/implementation item.
It has the strongest economic signal, but it changes execution shape from
synchronous stage-then-checkpoint to asynchronous submit-poll-ingest. It
needs a durable batch ledger before implementation can be considered safe,
and it needs a bounded post-implementation real batch-mode validation before
researchers treat the mode as usable. That validation should verify request
`custom_id` mapping, artifact and checkpoint publication equivalence with
the synchronous path, parse/schema validity, and semantic quality after
batched results are ingested.

### Decision 4: Preserve synchronous local-debug behavior

**Question:** Should the improved pilot default to the most cost-efficient
mode, or preserve the existing synchronous path as the default?

**Options considered:**
- Make Batch API and cheaper model tiers the new defaults immediately.
- Keep the synchronous Messages API path as the default/debug path, adding
  cost-saving modes explicitly.
- Split the script into separate tools for debug, validation, and full runs.

**Chosen: preserve the synchronous path and add explicit modes.** The
existing synchronous path gives better per-story/per-stage visibility and
matches the current checkpointing model. Batch mode should be opt-in until
its ledger and result-ingestion behavior are proven. Model tiering and
prompt caching can become recommended pilot settings only after the
stability gate passes, but the system should still make the chosen model
and cache state visible in output metadata.

### Decision 5: Treat user-facing run modes as part of the design

**Question:** Is this work only about backend settings, or should it also
improve how a researcher chooses and understands pilot runs?

**Options considered:**
- Leave the current CLI as a collection of independent flags.
- Add documented, user-facing run modes such as validate, pilot-sync, and
  pilot-batch.
- Hide the complexity behind changed defaults.

**Chosen: add explicit user-facing modes or mode documentation as part of
the workstream.** The user-facing problem is not just price. It is knowing
which command proves the system works cheaply, which command produces the
high-quality synchronous pilot output, and which command trades visibility
for lower Batch API cost. The workstream should make those choices visible
through CLI help, output summaries, README updates, or a thin wrapper if
that proves cleaner during work-item scoping.

## Non-Goals

- Does not implement any cost-saving change directly. This proposal scopes
  follow-on work; work items implement it.
- Does not default prompt caching, model tiering, or Batch API on merely
  because their evaluations produced go recommendations.
- Does not replace the existing synchronous Messages API path; that path
  remains necessary for local debugging and visibility.
- Does not fuse entity/event/relation/discourse extraction calls. Decision 6
  of `PROP-LCATS-PILOT-COST-SUSTAINABILITY` continues to reject that
  direction.
- Does not fold local-model evaluation into this workstream. Local models
  remain a separate proposal track.
- Does not authorize unbounded real API runs. Any real run in the stability
  gate or adoption work must estimate calls/cost first and receive explicit
  in-session approval.

## Implementation Plan

This proposal should be implemented by a new workstream,
`WS-PILOT-IMPROVEMENTS`, with work items created in this order:

1. **Pilot API/output stability gate.** Define and run a bounded real
   end-to-end validation that checks completion, artifact well-formedness,
   semantic sense, quality thresholds, intended-purpose fit, and actual
   spend. This is a prerequisite for all later implementation work.
2. **Prompt caching adoption.** If the stability gate passes, enable
   explicit pilot-level prompt caching for Anthropic fixture/pilot runs,
   preserving `AnthropicBackend(enable_prompt_caching=False)` as the global
   default and retaining cache token telemetry.
3. **Genre/segmentation model-tiering adoption.** If the stability gate
   passes, adopt Haiku 4.5 for genre detection and segmentation in the
   pilot's recommended configuration, preserving telemetry for schema
   validity, truncation, sanitization, and semantic genre accuracy where
   applicable.
4. **Batch API opt-in design.** Design the opt-in Batch API mode, including
   durable submit/poll/result-ingestion ledger shape and its interaction with
   `checkpoint.py`. This design work can proceed after proposal/workstream
   adoption without spending real API budget, but user-facing use still
   depends on the stability gate and the validation item below.
5. **Batch API opt-in implementation and validation.** If the stability gate
   passes, implement the opt-in Batch API mode, publish normal per-stage
   checkpoint artifacts only after batch results are ingested, and run a
   bounded real batch-mode validation before treating the mode as usable.
6. **User-facing pilot run ergonomics.** Clarify CLI/help/docs/output so a
   researcher can choose a cheap validation run, a synchronous high-visibility
   pilot run, or an opt-in lower-cost batch run without reverse-engineering
   individual flags.

`WS-PILOT-COST-SUSTAINABILITY` should then be closed or explicitly
reinterpreted as the completed evaluation workstream, with this proposal and
`WS-PILOT-IMPROVEMENTS` carrying the implementation follow-through.

## Open Questions

- What exact story set should the stability gate use: the current
  `WI-PILOT-0051` fixture set, a slightly larger curated set, or a
  deliberately mixed set that includes known hard cases?
- What exact quality thresholds should block downstream adoption work?
  Candidate thresholds include zero fatal API errors, zero truncations, zero
  schema-invalid outputs, parseable output artifacts, and human-reviewed
  semantic adequacy for the pilot's intended research question.
- Should user-facing run modes be implemented as new CLI flags on
  `run_pilot.py`, documented recipes using existing flags, or a thin wrapper
  script?
- Should prompt caching and model tiering adoption be separate WIs or a
  single low-risk configuration WI after the stability gate?

## Cross-References

- `lcats/project/design/proposals/adopted/lcats-pilot-cost-sustainability/00_proposal.md`
  — source proposal and measured cost-sustainability recommendations.
- `lcats/project/workstreams/proposed/WS-PILOT-COST-SUSTAINABILITY.md`
  — evaluation workstream that produced the prerequisite harness and
  measured go/no-go decisions.
- `lcats/project/design/proposals/adopted/lcats-pipeline-checkpointing/00_proposal.md`
  — synchronous checkpointing model that Batch API adoption must preserve
  after result ingestion.
- `lcats/project/audits/2026-07-27-erw-pipeline-structured-output-reliability-audit.md`
  — originating audit for cost visibility, control, and reliability risk.
- `lcats/project/design/backlog.md`
  — contains the minimum-cost validation and pilot usage visibility backlog
  entries this proposal continues to address.
