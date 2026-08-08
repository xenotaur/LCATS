---
id: WI-PILOT-0060
title: Evaluate per-stage model tiering against the WI-PILOT-0051 fixture set
type: evaluation
status: proposed
priority: medium
owner: unassigned
contributors: []
assigned_agents: []
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap: []
related_workstreams:
  - WS-PILOT-COST-SUSTAINABILITY
related_design:
  - lcats/project/design/proposals/adopted/lcats-pilot-cost-sustainability/00_proposal.md
depends_on:
  - WI-PILOT-0051
blocked_by: []
blocked: false
blocked_reason: null
resolution: null
expected_actions:
  - edit_file
  - run_tests
  - create_pr
forbidden_actions:
  - force_push
  - delete_branch
  - run_real_llm_calls_without_explicit_approval
  - default_enable_model_tiering
  - implement_call_fusion
acceptance:
  - run_pilot.py gains optional per-stage --model overrides (genre-detect, segmentation, and each ERW extractor independently selectable), added alongside the existing global --model flag, which remains the default for every stage when no per-stage override is given (top-tier model stays the default unless a stage's --model is explicitly overridden)
  - A bounded, explicitly-approved real comparison run against WI-PILOT-0051's fixture set evaluates a cheaper model tier (e.g. Haiku 4.5) specifically on genre-detection and segmentation output quality against the current top-tier baseline - real output, not just cost, since this pipeline's own top-tier model has already produced malformed structured output under real conditions (project/design/backlog.md's speech_acts-as-string bug)
  - The comparison reports concrete quality evidence alongside the real cost delta: schema-validity rate and truncation rate for both stages, plus a semantic-accuracy check for genre-detection specifically against validated ground truth (not the fixture set's own genre labels, which experiments/03_cross_segment_relation_pilot/fixtures/README.md explicitly documents as unvalidated) or another objective adjudication - schema validity alone cannot catch a cheaper model producing structurally valid but semantically wrong genre labels
  - A written go/no-go conclusion updates Decision 5 of the adopted proposal - "quality doesn't hold, don't adopt" is a valid, complete outcome, not a failure
  - Model tiering remains off by default regardless of the evaluation's conclusion - adoption as the default is a separate follow-on decision
  - lrh validate and scripts/test both report 0 errors/failures
required_evidence:
  - manual_review
  - lrh_validate
  - test_output
artifacts_expected:
  - experiments/03_cross_segment_relation_pilot/run_pilot.py
  - experiments/03_cross_segment_relation_pilot/run_pilot_test.py
  - lcats/project/design/proposals/adopted/lcats-pilot-cost-sustainability/00_proposal.md
---

## Summary

Add per-stage model selection to `run_pilot.py` and produce a real
output-quality comparison of a cheaper model tier against the current
top-tier default, specifically for genre-detection and segmentation,
per Decision 5 of `PROP-LCATS-PILOT-COST-SUSTAINABILITY`. This is WI 4
of `WS-PILOT-COST-SUSTAINABILITY`'s Implementation Plan, gated on WI 1's
harness (`WI-PILOT-0051`, resolved, PR #244).

## Problem / Context

Decision 5 asks whether genre-detection and segmentation (comparatively
low-complexity tasks) could move to a cheaper model tier, reserving the
top-tier model for entity/event/relation/discourse/cross-segment
extraction. Anthropic's model-comparison pricing shows a real spread
(e.g. Haiku 4.5 at $1/$5 per MTok vs. legacy Opus 4.8 at $5/$25) that
could meaningfully cut genre-detect's 200-candidate scan cost
specifically. But this session directly observed the *top-tier* model
producing malformed structured output under real conditions - the
`speech_acts`-as-string bug
(`project/design/backlog.md:321-323`, not the proposal's originally
cited lines 164-180, which have drifted since the proposal was
written and were re-verified directly for this item). A cheaper
model's reliability on the same strict-schema tool-use is an open,
unvalidated question, not a safe assumption. `run_pilot.py`'s single
global `--model` flag (`run_pilot.py:1413`, re-verified directly - not
the proposal's originally cited `:1153`, also drifted) also needs to
become per-stage before this is even testable. Decision 5 explicitly
defers this to "a follow-on work item that evaluates real output
quality against the Decision 2 fixture set before any adoption" - this
is that item.

### Duplication search
- In-repo: No existing per-stage model selection or model-tiering
  evaluation anywhere in `experiments/03_cross_segment_relation_pilot/`.
  Confirmed via `grep -n "add_argument.*--model"
  experiments/03_cross_segment_relation_pilot/run_pilot.py` - exactly
  one global `--model` flag exists, no per-stage variant.
- Sibling repos: None identified.
- External libraries: None - this evaluates Anthropic's own published
  model tiers (Haiku/Sonnet/Opus), not a new dependency.
- Recommendation: Proceed.

### Demand search
- Work items: `WI-PILOT-0051` (resolved) is this item's direct
  prerequisite per `depends_on`; no other matching work item found.
- Proposals: `PROP-LCATS-PILOT-COST-SUSTAINABILITY` (adopted) requests
  this exact item as WI 4 of its Implementation Plan, explicitly gated
  on WI 1.
- Workstreams: `WS-PILOT-COST-SUSTAINABILITY` lists this as WI 4 in its
  `## Work Items` section.
- Backlog: The `speech_acts`-as-string malformed-output entry
  (`project/design/backlog.md:321-323`) is directly relevant context
  (motivates the quality-not-just-cost framing above) but is not itself
  a request for this item - already resolved via
  `WI-EVENT-0032`/similar per its own entry, unrelated to model choice.
- Recommendation: Proceed.

## Scope

- Add optional per-stage `--model` overrides to `run_pilot.py`,
  alongside the current single global `--model` flag
  (`run_pilot.py:1413`), with independently-selectable models for
  genre-detect, segmentation, and each ERW extractor
  (entity/event/relation/discourse/cross-segment) - the global flag
  remains the default for every stage when no per-stage override is
  given, so existing behavior is unchanged unless a stage's model is
  explicitly overridden.
- Run a bounded, explicitly-approved real comparison against
  `WI-PILOT-0051`'s fixture set: a cheaper model tier (e.g. Haiku 4.5)
  on genre-detection and segmentation specifically - the two stages
  Decision 5 names as candidates - versus the current top-tier baseline
  on the same fixture set.
- Measure real output quality, not just cost: schema-validity rate
  (does the cheaper model's structured output actually conform to the
  same tool schema without malformed containers, given the top-tier
  model's own confirmed failure on this exact class of problem?) and
  truncation rate for both stages, plus a semantic-accuracy check for
  genre-detection specifically - the fixture set's own genre labels
  are documented as unvalidated
  (`experiments/03_cross_segment_relation_pilot/fixtures/README.md`),
  so schema validity alone cannot catch a cheaper model producing
  structurally valid but semantically wrong genre labels; a validated
  ground truth or another objective adjudication is required for this
  stage specifically.
- Update Decision 5 of `PROP-LCATS-PILOT-COST-SUSTAINABILITY`'s
  `00_proposal.md` with the real measured numbers (cost delta and
  quality evidence) and a go/no-go recommendation.

## Required Changes

1. Extend `run_pilot.py`'s `argparse` setup to accept per-stage model
   overrides (e.g. `--model-genre-detect`, `--model-segment`, or a
   single structured flag covering all stages), each defaulting to the
   existing global `--model` value when not explicitly set - the
   current single-flag behavior must remain the unchanged default path.
2. Thread the per-stage model selection through to each stage's actual
   backend call site, replacing any place that currently assumes one
   model for the whole run.
3. Run the bounded, explicitly-approved real comparison from Scope
   against `WI-PILOT-0051`'s fixture set, capturing both cost and
   quality evidence for genre-detect and segmentation under the
   cheaper tier versus the top-tier baseline.
4. Write the go/no-go assessment as an update to Decision 5 in
   `lcats/project/design/proposals/adopted/lcats-pilot-cost-sustainability/00_proposal.md`,
   covering the real cost delta, the quality evidence, and a clear
   recommendation (adopt / reject / defer with a named blocking
   factor).
5. Add or extend `run_pilot_test.py` with fake-backend-harness tests
   proving the per-stage model flags are correctly threaded to each
   stage's backend call (no real API calls needed for this
   plumbing-correctness check - only the actual quality/cost
   measurement in Required Change 3 needs real calls).

## Non-Goals

- Does not adopt any specific cheaper model as the default for any
  stage - per-stage tiering stays off by default (every stage uses the
  top-tier model unless explicitly overridden) regardless of this
  item's own conclusion. Adoption as the default is a separate
  follow-on decision.
- Does not implement Decision 6 (fusing the 4 per-segment extractor
  calls) - rejected in the proposal, no new evidence to revisit it.
- Does not implement or evaluate local-model support - a separate,
  parallel track already covered by `PROP-ERW-LOCAL-MODEL-EVALUATION`
  (Decision 7).
- Does not evaluate cheaper models for entity/event/relation/discourse/
  cross-segment extraction - Decision 5 specifically names
  genre-detection and segmentation as the candidates; the other,
  more complex stages are out of scope for this evaluation.
- Does not run a real, paid full-corpus `run_pilot.py` execution -
  the comparison is bounded to `WI-PILOT-0051`'s small fixture set.

## Acceptance Criteria

(see frontmatter `acceptance:` above)

## Validation

- `scripts/version tools`
- `lrh validate`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- A bounded, explicitly-approved real comparison run against the
  WI-PILOT-0051 fixture set (not a fake-backend run for the quality
  measurement itself - see Risk Notes)

## Risk Notes

- Like `WI-PILOT-0057`, this item's core measurement (real output
  quality under a cheaper model) genuinely cannot be done with a fake
  backend - a fake backend cannot demonstrate whether a real cheaper
  model actually produces valid structured output. The real-call step
  must be small, bounded to the fixture set, and gated behind its own
  explicit human approval separate from this item's chain-authorization
  gate.
- The motivating concern is not hypothetical: this pipeline's own
  top-tier model has already produced malformed structured output under
  real conditions (the `speech_acts`-as-string bug). A cheaper model
  could plausibly be *more* prone to this failure mode, not less -
  the comparison must measure this directly, not assume a cheaper model
  is "probably fine" because it's cheaper.
- A "quality doesn't hold, don't adopt" result is a valid, complete
  outcome for this item, per the workstream's own exit criteria ("adopt
  or reject, with real numbers... none is a foregone commitment") - do
  not treat a negative quality result as a reason to keep tuning prompts
  or retrying until quality looks acceptable; report what was actually
  measured.
- Per-stage model plumbing correctness (Required Change 5) should be
  tested via fake-backend harness *before* spending on the real
  comparison, so a wiring bug isn't discovered only after real API
  spend.

## Dependencies / Order

Depends on `WI-PILOT-0051` (resolved, PR #244) for its fixture-set
harness. Does not depend on `WI-PILOT-0057` (prompt caching) or
`WI-PILOT-0058` (Batch API) - all three WI 2-4 evaluations only depend
on WI 1, per the workstream's own Open Questions (no strict
inter-evaluation ordering).

## Related Workstream and Designs

- Workstream: `project/workstreams/proposed/WS-PILOT-COST-SUSTAINABILITY.md`
- Design: `project/design/proposals/adopted/lcats-pilot-cost-sustainability/00_proposal.md`
