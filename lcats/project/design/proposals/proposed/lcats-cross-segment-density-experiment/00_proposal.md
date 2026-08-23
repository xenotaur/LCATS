---
id: PROP-LCATS-CROSS-SEGMENT-DENSITY-EXPERIMENT
type: design_proposal
title: Cross-Segment Density Experiment Delivery
status: proposed
created_on: 2026-08-22
updated_on: 2026-08-22
implementation_status: not_started
implemented_by: []
supersedes: []
superseded_by: null
related_design:
  - lcats/project/design/proposals/adopted/lcats-event-role-world-extractor/00_proposal.md
  - lcats/project/design/event-role-world-cross-segment-relations-evaluation.md
  - lcats/project/work_items/proposed/WI-EVENT-0030.md
  - lcats/project/design/proposals/proposed/lcats-pilot-improvements/00_proposal.md
  - lcats/project/workstreams/proposed/WS-PILOT-IMPROVEMENTS.md
  - lcats/project/workstreams/resolved/WS-PIPELINE-CHECKPOINTING.md
  - lcats/project/workstreams/resolved/WS-PILOT-COST-SUSTAINABILITY.md
---

# Cross-Segment Density Experiment Delivery

## Summary

This proposal defines a staged delivery plan for the cross-segment relation
density experiment needed for the Worldcon paper. It makes `WI-EVENT-0030`
the near-final empirical run, preceded by preregistration, readiness, and
small real feasibility gates, and followed by final analysis and figure
packaging.

## Background / Motivation

`WI-EVENT-0028` established, through a small four-story reading exercise,
that science fiction and horror material may contain more long-range
cross-segment causal chains than comparison material. `WI-EVENT-0029`
implemented the story-level relation pass needed to capture those links.
`WI-EVENT-0030` then scoped the larger stratified pilot needed before the
paper can publish a cross-segment density figure.

The project history shows that directly running `WI-EVENT-0030` was not
safe enough as the first next step. `WS-PIPELINE-CHECKPOINTING` was created
after real `run_pilot.py` attempts spent about `$50` with zero surviving
artifacts. `WS-PILOT-COST-SUSTAINABILITY` was created after two more real
`run_pilot.py` runs spent `$67.54` mostly discovering bugs rather than
producing usable density evidence. That work delivered checkpointing,
targeted fixtures, and measured cost-sustainability evaluations, but it did
not itself execute the full scientific experiment.

The experiment goal is broader than one chart: produce a defensible,
auditable, reliably executing, as-inexpensive-as-feasible way to measure
cross-segment-only relation density over a Worldcon-scale sample comparable
to the current genre and linguistics pilot scale. The existing
`WI-GENRE-0004` 146-story genre-balanced sample is the obvious initial
full-scale frame, subject to preregistered sampling and cost decisions.

## Prior Art Check

### Duplication search

- In-repo: Related and partially overlapping work exists. `WI-EVENT-0030`
  already scopes the stratified density measurement, but it is a single
  proposed evaluation rather than a staged experiment-delivery workstream.
  `WS-PILOT-IMPROVEMENTS` owns reusable pilot stability/cost/run-mode
  improvements, not the final scientific density evidence package.
  `WS-LINGUISTICS` and `WS-KNIGHT-NOVUM-ANALYSIS` provide project-local
  precedents for Worldcon-scale sample runs and phased feasibility-to-scale
  pilot gating.
- Sibling repos: None identified.
- External libraries: None identified. This is a project-specific corpus
  experiment built on LCATS's existing ERW extraction and control-plane
  artifacts.
- Recommendation: Proceed by linking and revising existing LCATS planning
  artifacts, especially `WI-EVENT-0030`, rather than creating a parallel
  density-pilot item.

### Demand search

- Work items: `WI-EVENT-0030` directly requests the larger density pilot.
  The new work is to make that run safe, preregistered, cost-gated, and
  analyzable at Worldcon scale.
- Proposals: `PROP-LCATS-PILOT-IMPROVEMENTS` requests stabilized,
  researcher-facing pilot improvements behind quality and spend gates.
- Backlog: `lcats/project/design/backlog.md` records that `run_pilot.py`
  lacks a cheap bounded real-API validation mode between fake dry-run and
  full expensive real execution.
- Recommendation: Link the demand into a new workstream and preserve
  `WI-EVENT-0030` as the near-final empirical run.

## Design Decisions

### Decision 1: Treat `WI-EVENT-0030` as the near-final empirical run

**Question:** Should the new planning path replace `WI-EVENT-0030`, or make
it safely executable?

**Options considered:**

- Replace `WI-EVENT-0030` with a new work item.
- Run `WI-EVENT-0030` immediately.
- Create a staged workstream that leads into `WI-EVENT-0030`.

**Chosen: create a staged workstream that leads into `WI-EVENT-0030`.**
The existing item already captures the core scientific measurement, metric
contract, genre-label uncertainty handling, and result location. The missing
piece is not a second density item; it is a controlled runway that prevents
another expensive run from mainly discovering infrastructure defects.

### Decision 2: Preregister before observing new density results

**Question:** What must be frozen before the next paid density run?

**Options considered:**

- Let the execution work item decide sample and thresholds as it goes.
- Freeze only the sample manifest.
- Preregister the sample frame, thresholds, exclusions, cost gates, and
  stop conditions before new density results are observed.

**Chosen: preregister the full run plan.** The first work item should
reconcile `WI-EVENT-0030` with the current 146-story sample, previous cost
and failure evidence, current segmentation state, and the intended
Worldcon-scale target. It should decide whether `WI-EVENT-0030` remains a
5-10 stories-per-genre run, becomes the full 146-story run, or is sequenced
after an intermediate pilot, and it must record that decision before paid
execution.

### Decision 3: Use staged real-run gates before scale

**Question:** How should the project decide it is safe to spend on the
larger run?

**Options considered:**

- Trust checkpointing and run the full experiment.
- Repeat the failed two-story gate until it passes.
- Use readiness and small feasibility gates with explicit stop conditions.

**Chosen: readiness gate, then small real feasibility gate.** Checkpointing
has reduced work-loss risk, but it does not prove segmentation reliability,
semantic quality, complete usage logging, or intended-purpose fitness. A
no- or low-cost readiness gate should precede any new real feasibility run,
and the feasibility run should stop downstream scale-up if the named
completion, quality, artifact, or cost thresholds fail.

### Decision 4: Make cost improvements conditional, not mandatory

**Question:** Must prompt caching, model tiering, Batch API, and run-mode
ergonomics all land before `WI-EVENT-0030`?

**Options considered:**

- Require every pilot improvement before the density experiment.
- Ignore pilot improvements and run synchronously at top-tier cost.
- Evaluate each improvement against cost, quality, schedule, and complexity
  before the near-final run.

**Chosen: conditional adoption by diminishing returns.** The density
workstream should consume `WS-PILOT-IMPROVEMENTS` outputs when they are
available and worth their complexity, but it should not become a second
home for all pilot infrastructure. Batch mode, for example, should only be
used for the near-final run if its ledger/result-ingestion behavior is
proven and the expected savings justify the schedule risk.

### Decision 5: Close with an evidence package, not only raw output

**Question:** What is the final deliverable after `WI-EVENT-0030` runs or
is gate-stopped?

**Options considered:**

- Commit raw run output only.
- Commit summary numbers only.
- Produce a paper-facing evidence package, including a stopped-outcome
  package when preregistered gates prevent the near-final run.

**Chosen: produce a paper-facing evidence package.** The final analysis
should include raw per-story rows, excluded-story/failure taxonomy, usage
and cost report, per-genre density summaries, figure source, generated
figure/table, and prose interpretation stating whether the result confirms,
weakens, or contradicts the original hypothesis. If a preregistered gate
stops the near-final run before density results exist, the package should
instead include the gate evidence, named stop condition, costs incurred,
unavailable-result explanation, and recommendation to stop, revise, or file
follow-on work.

## Non-Goals

- Does not implement prompt caching, model tiering, Batch API, or run-mode
  ergonomics; those remain owned by `WS-PILOT-IMPROVEMENTS`.
- Does not run any real LLM call without a separate explicit spend approval.
- Does not redefine the headline metric away from cross-segment-only
  relation density.
- Does not choose the paper's final statistical interpretation beyond
  requiring a defensible experiment package.
- Does not automatically expand beyond the approved Worldcon-scale sample;
  expansion is a post-result decision.

## Implementation Plan

This proposal is delivered through
`WS-PILOT-CROSS-SEGMENT-DENSITY`:

1. `WI-EVENT-0078` - reconcile and preregister `WI-EVENT-0030` into the
   staged plan.
2. `WI-EVENT-0079` - run a no- or low-cost readiness gate over the current
   runner, segmentation, logging, checkpoint, and artifact state.
3. `WI-EVENT-0080` - run a bounded, explicitly approved small real
   feasibility pilot.
4. `WI-EVENT-0030` - execute the near-final stratified density run, possibly
   revised by `WI-EVENT-0078`, only after a fresh explicit approval gate for
   this larger paid run.
5. `WI-EVENT-0081` - produce the final analysis and paper-facing evidence
   package, or the gate-stopped evidence package if the near-final run does
   not execute.

## Cross-References

- Existing density run item:
  `lcats/project/work_items/proposed/WI-EVENT-0030.md`
- Related improvement workstream:
  `lcats/project/workstreams/proposed/WS-PILOT-IMPROVEMENTS.md`
- Prior cost-control workstream:
  `lcats/project/workstreams/resolved/WS-PILOT-COST-SUSTAINABILITY.md`
- Prior checkpointing workstream:
  `lcats/project/workstreams/resolved/WS-PIPELINE-CHECKPOINTING.md`

## Open Questions

- Should the near-final `WI-EVENT-0030` run cover the full 146-story
  `WI-GENRE-0004` sample, or should the paper-facing run remain stratified
  at 5-10 stories per genre with a separately justified expansion option?
- Which pilot improvements are worth landing before the near-final run if
  the mid-September paper schedule becomes tight?
