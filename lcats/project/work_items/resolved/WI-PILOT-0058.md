---
id: WI-PILOT-0058
title: Evaluate Anthropic Batch API against the WI-PILOT-0051 fixture set
type: evaluation
status: resolved
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
resolution: "Implemented and merged in PR #284 (commit 56c491a8c5efed775cad015be54c46606948a6f8): Batch API assessment completed against the WI-PILOT-0051 fixture baseline and Decision 4 updated with measured go recommendation."
expected_actions:
  - edit_file
  - run_tests
  - create_pr
forbidden_actions:
  - force_push
  - delete_branch
  - run_real_llm_calls_without_explicit_approval
  - retrofit_checkpointing_for_batch_by_default
  - implement_batch_api_adoption
acceptance:
  - A written go/no-go assessment exists comparing the Batch API's real 50% flat discount (both input and output tokens, no quality tradeoff) against the real architecture cost of retrofitting the synchronous, per-call, stage-then-checkpoint pipeline (checkpoint.py's read_checkpoint/write_checkpoint, WI-PIPELINE-0040/0041) for asynchronous submission-and-poll
  - The assessment applies that 50% discount to a real cost baseline - either WI-PILOT-0057's real measurement numbers if landed, or a small, separately-approved real baseline run of the WI-PILOT-0051 fixture set if not (WI-PILOT-0051 itself produced no real baseline to reuse)
  - The assessment explicitly addresses the batch-jobs-report-no-interim-status property of the real Batch API (client.messages.batches.create/retrieve/results has no per-item progress signal until the whole batch completes or is polled) against this pipeline's existing per-story/per-stage progress printing
  - If the assessment concludes "adopt," this item stops at the assessment - implementation (submission/polling logic, checkpoint-architecture retrofit) is a separate follow-on item, not silently started here
  - If the assessment concludes "reject" or "defer," that is a valid, complete outcome, with the specific blocking factor(s) documented
  - lrh validate reports 0 errors
required_evidence:
  - manual_review
  - lrh_validate
artifacts_expected:
  - lcats/project/design/proposals/adopted/lcats-pilot-cost-sustainability/00_proposal.md
---

## Summary

Produce a written go/no-go assessment of adopting Anthropic's Batch API
(a flat 50% discount, asynchronous) for the Event-Role-World pipeline,
per Decision 4 of `PROP-LCATS-PILOT-COST-SUSTAINABILITY`. This is WI 3
of `WS-PILOT-COST-SUSTAINABILITY`'s Implementation Plan, gated on WI 1's
fixture-set harness (`WI-PILOT-0051`, resolved, PR #244) - the harness
exists, but a real cost baseline against it still needs to be
established (see Problem/Context).

## Problem / Context

Decision 4 found the Batch API's discount real and unconditional - 50%
off both input and output tokens, with no documented quality tradeoff -
but flagged a real architectural obstacle: the pipeline's checkpointing
was migrated to synchronous, per-call, stage-then-checkpoint semantics
(`WI-PIPELINE-0040`/`0041`, adopted just two days before this proposal)
via `lcats/src/lcats/utils/checkpoint.py`'s `read_checkpoint`/
`write_checkpoint` (`checkpoint.py:251,302`). Retrofitting for batch
submission-and-poll is a real architecture change, not a flag flip -
Decision 4 explicitly defers this to "a follow-on work item that starts
with an explicit go/no-go assessment against the baseline cost
Decision 2's harness makes measurable (and Decision 3's caching
evaluation, if it lands first and shows a real benefit)." This is that
assessment.

Decision 4's own text additionally cites "the already-flagged 'no
mid-call progress feedback' gap (backlog P2)" as a compounding factor.
That specific citation could not be verified against a matching entry
in `project/design/backlog.md` during this item's creation - the
closest P2 entry ("`pilot_usage.jsonl` doesn't track genre-detect or
segmentation cost at all") is about cost-visibility, not progress
feedback, and no backlog heading matches the "mid-call progress
feedback" description. Rather than repeat an unverified citation, this
item grounds the no-interim-status concern directly in a real,
independently-verifiable property of the Batch API itself (see Scope) -
whether the original backlog citation was a stale/broken cross-reference
is a separate, smaller documentation question, not blocking to this
assessment.

**No real cost baseline currently exists to apply the 50% discount
to.** `WI-PILOT-0051` (resolved) explicitly forbade real, paid
`run_pilot.py` execution as part of its own scope
(`run_real_llm_calls_without_explicit_approval`), and its execution
record reports only dry-run/fake-backend fixture validation - it built
the harness but never ran it for real. This item therefore cannot
assume a measured baseline is already available to halve; it must
either use `WI-PILOT-0057`'s real measurement numbers (if that item has
landed by the time this one runs - its own real-call step produces
real cost data as a byproduct of measuring caching) or commission a
small, separately-approved real baseline run of its own against the
fixture set (review finding, PR #252).

### Duplication search
- In-repo: No existing Batch API usage or assessment anywhere in
  `lcats/src/lcats/llm/`. Confirmed via `grep -rn "messages.batches"
  lcats/src/lcats/` - zero matches.
- Sibling repos: None identified.
- External libraries: None - this evaluates Anthropic's own SDK-native
  Batch API (confirmed present in the installed `anthropic==0.113.0`:
  `client.messages.batches.create`/`.retrieve`/`.results`/`.cancel`/
  `.list`), not a new dependency.
- Recommendation: Proceed.

### Demand search
- Work items: `WI-PILOT-0051` (resolved) is this item's direct
  prerequisite per `depends_on`; `WI-PILOT-0057` (proposed, prompt
  caching evaluation) is a related but non-blocking sibling per
  Decision 4's own text - no other matching work item found.
- Proposals: `PROP-LCATS-PILOT-COST-SUSTAINABILITY` (adopted) requests
  this exact item as WI 3 of its Implementation Plan, explicitly gated
  on WI 1 (and optionally informed by WI 2).
- Workstreams: `WS-PILOT-COST-SUSTAINABILITY` lists this as WI 3 in its
  `## Work Items` section.
- Backlog: No matching entries found for this specific item's request
  (see the citation-verification note above, which is about a different,
  smaller documentation question).
- Recommendation: Proceed.

## Scope

- Establish a real cost baseline to apply the Batch API's 50% discount
  to: use `WI-PILOT-0057`'s real caching-evaluation numbers if that item
  has landed by the time this one runs, or commission a small,
  explicitly-approved real baseline run of `WI-PILOT-0051`'s fixture set
  otherwise - `WI-PILOT-0051` itself never ran for real, so no existing
  measured baseline can be assumed.
- Assess the Batch API's real economics against that baseline - a
  straightforward 50% multiplier once a real baseline exists.
- Assess the architecture cost of retrofitting
  `experiments/03_cross_segment_relation_pilot/run_pilot.py`'s
  synchronous per-stage checkpointing for asynchronous batch
  submission-and-poll: what changes to `checkpoint.py`'s
  fingerprint/publication model (or a new, parallel mechanism) would be
  needed, and how much of the existing per-stage granularity (Decision 3
  of `PROP-LCATS-PIPELINE-CHECKPOINTING`) survives a batch model where
  many stories' calls submit together and results arrive together.
- Assess the real, independently-verifiable no-interim-status property:
  `client.messages.batches.retrieve()` reports overall batch
  `processing_status`, not per-request completion, until `.results()` is
  called on a finished batch - compare this against the pipeline's
  current per-story/per-stage console progress printing and decide
  whether/how that visibility gap matters for a single-researcher local
  workflow.
- Write the assessment as an update to Decision 4 in
  `PROP-LCATS-PILOT-COST-SUSTAINABILITY`'s `00_proposal.md`, with an
  explicit go/no-go recommendation.

## Required Changes

1. Read `checkpoint.py` (`lcats/src/lcats/utils/checkpoint.py`) in full
   to characterize its actual fingerprint/publication model precisely
   enough to assess batch-retrofit cost concretely, not abstractly.
2. Obtain a real cost baseline: if `WI-PILOT-0057` has landed with real
   measurement numbers, use those directly - no new API calls needed. If
   not, commission a small, explicitly-approved real run of
   `WI-PILOT-0051`'s fixture set (this requires the same separate,
   mid-implementation confirmation gate `WI-PILOT-0057` uses for its own
   real-call step - see Risk Notes). Apply the Batch API's documented
   50% discount to whichever real baseline results, to produce a real
   projected saving figure.
3. Write the go/no-go assessment as an update to Decision 4 in
   `lcats/project/design/proposals/adopted/lcats-pilot-cost-sustainability/00_proposal.md`,
   covering: the real discount figure, the architecture-retrofit cost
   assessment, the no-interim-status tradeoff, and a clear
   recommendation (adopt / reject / defer with a named blocking
   factor).
4. If the assessment surfaces the Decision-4 backlog-citation
   discrepancy noted in Problem/Context as worth a real fix (not just
   this item's own workaround), add a small, separate backlog entry
   noting the stale/broken cross-reference - do not silently drop it,
   but do not treat fixing it as part of this item's own acceptance
   criteria either.

## Non-Goals

- Does not implement Batch API submission/polling logic - this item's
  deliverable is the assessment only, per Decision 4's own framing
  ("starts with an explicit go/no-go assessment"). Implementation, if
  the assessment recommends it, is a separate follow-on item.
- Does not retrofit `checkpoint.py` or `run_pilot.py`'s checkpointing
  architecture - assessing the retrofit's cost is in scope; performing
  it is not.
- Does not depend on `WI-PILOT-0057` landing first - only on
  `WI-PILOT-0051` - though the assessment should incorporate WI-0057's
  real numbers if they exist by the time this item runs.
- Does not evaluate per-stage model tiering (`WI 4` of this workstream)
  - a separate, sequenced item.
- Does not change the checkpointing architecture's existing behavior for
  the current synchronous pipeline in any way.

## Acceptance Criteria

(see frontmatter `acceptance:` above)

## Validation

- `lrh validate`
- Manual review of the updated Decision 4 text against
  `checkpoint.py`'s actual current implementation and the real,
  measured `WI-PILOT-0051` (and `WI-PILOT-0057`, if available) cost
  baseline

## Risk Notes

- The architecture-retrofit cost assessment and the no-interim-status
  comparison are both assessable without any real API calls - the
  Batch API's discount is documented and unconditional, and
  `checkpoint.py` can be read directly. But the *baseline cost figure*
  the 50% discount is applied to may require real API calls if
  `WI-PILOT-0057` hasn't landed with usable numbers by the time this
  item runs (review finding, PR #252 - `WI-PILOT-0051` itself produced
  no real baseline). That real-call step, if needed, requires its own
  separate, explicit human approval before any real API call is made -
  matching `WI-PILOT-0057`'s own real-call gate, not covered by this
  item's chain-authorization gate.
- A "no real numbers yet" assessment (if `WI-PILOT-0057` hasn't landed
  and its caching numbers aren't available, and no baseline run has been
  separately approved) is not grounds to block this
  item - Decision 4 only says the assessment "may" be informed by
  Decision 3's evaluation "if it lands first," not that it must wait.
- The Decision-4 backlog-citation discrepancy noted in Problem/Context
  is a real but separate, smaller finding surfaced while grounding this
  item - do not let chasing it down expand this item's own scope beyond
  the Batch API assessment itself.

## Dependencies / Order

Depends on `WI-PILOT-0051` (resolved, PR #244) for its fixture-set
harness - a real cost baseline against that harness still needs
establishing, per Scope. Does not depend on `WI-PILOT-0057` (prompt caching evaluation)
landing first, though it should incorporate that item's real numbers if
they exist. `WI 4` (model-tiering evaluation) may proceed independently.

## Related Workstream and Designs

- Workstream: `project/workstreams/proposed/WS-PILOT-COST-SUSTAINABILITY.md`
- Design: `project/design/proposals/adopted/lcats-pilot-cost-sustainability/00_proposal.md`
