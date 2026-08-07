---
id: WS-PILOT-COST-SUSTAINABILITY
kind: planning_node
title: Sustainable-cost validation harness and evaluation gates for the ERW cross-segment relation pilot
status: proposed
stage: planned
origin: design_review
summary: Deliver PROP-LCATS-PILOT-COST-SUSTAINABILITY's targeted test harness, then gate prompt caching, Batch API, and model-tiering adoption behind real, measured evaluations against that harness, so run_pilot.py stays cheap enough to iterate on before any further full, expensive real run.
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap: []
related_design:
  - lcats/project/design/proposals/adopted/lcats-pilot-cost-sustainability/00_proposal.md
  - lcats/project/audits/2026-07-27-erw-pipeline-structured-output-reliability-audit.md
  - lcats/project/design/proposals/adopted/lcats-pipeline-checkpointing/00_proposal.md
work_items:
  - WI-PILOT-0051
exit_criteria:
  - A targeted single/small-story test harness exists on run_pilot.py (--story/--story-list flag, fixture set, per-stage cost reporting), per Decision 2
  - Prompt caching, Batch API, and model-tiering each have a completed, measured evaluation against the harness's fixture set (adopt or reject, with real numbers) — none is a foregone commitment, per Decisions 3-5
  - Any evaluation that concludes "adopt" has landed as an implemented change, not left as an open recommendation
  - All work items resolved and lrh validate reports 0 errors
---

# Workstream: Sustainable-cost validation harness and evaluation gates for the ERW cross-segment relation pilot

## Purpose

This workstream delivers `PROP-LCATS-PILOT-COST-SUSTAINABILITY`
(`lcats/project/design/proposals/adopted/lcats-pilot-cost-sustainability/00_proposal.md`),
adopted 2026-08-06 in response to two real runs of
`experiments/03_cross_segment_relation_pilot/run_pilot.py` that together
spent $67.54 without producing usable data — mostly discovering and
fixing bugs rather than gathering the intended cross-segment relation
density findings. It is the deferred follow-through on
`lcats/project/audits/2026-07-27-erw-pipeline-structured-output-reliability-audit.md`'s
Category E (cost visibility and control), raised ten days earlier and
explicitly held pending this discussion. It coordinates building a
targeted, cheap-to-run test harness first, then using that harness to
gate — not pre-commit to — three cost-reduction techniques (prompt
caching, the Batch API, and per-stage model tiering).

## Scope

- Build a targeted single/small-story test harness on `run_pilot.py`
  (`--story`/`--story-list` flag, fixture set, per-stage cost reporting),
  per Decision 2 — this gates validation of everything after it.
- Evaluate Anthropic prompt caching against the harness's fixture set,
  measuring the real, narrower caching benefit given that each of the 4
  per-segment extractors uses a different tool schema (which invalidates
  Anthropic's cache hierarchy downstream of the tool definition) — or the
  mid-conversation-tool-changes beta as an alternative — per Decision 3.
  Only proceeds to `cache_control` adoption in `anthropic_backend.py` if
  the evaluation shows a real, worthwhile saving.
- Evaluate the Batch API (50% discount, asynchronous) against the
  harness's now-measurable baseline, per Decision 4. Only proceeds to
  implementation if the assessment favors it — this evaluation has real
  architecture tension with the existing synchronous, per-stage
  checkpointing (`WI-PIPELINE-0040`/`0041`) to work through.
- Evaluate per-stage model tiering (cheaper models for lower-risk stages)
  against the harness's fixtures with a real output-quality comparison,
  per Decision 5. Only proceeds to adoption if quality holds.
- Land each work item through the standard LRH execution lifecycle
  (`/lrh-implement` → `/lrh-review-response` → `/lrh-confirm-fixes` →
  `/lrh-closeout`).

## Prior Art Check

### Duplication search
- In-repo: No existing cost-visibility or evaluation harness for this
  pilot. `PROP-LCATS-PILOT-COST-SUSTAINABILITY` itself already ran this
  search in full during proposal drafting (see the proposal's own Prior
  Art Check) — no duplicate found.
- Sibling repos: None identified.
- External libraries: None — the proposal's Decisions 3-5 evaluate
  Anthropic's own API features (prompt caching, Batch API), not a
  third-party library.
- Recommendation: Proceed.

### Demand search
- Work items: None found beyond this proposal's own request.
- Proposals: `PROP-LCATS-PILOT-COST-SUSTAINABILITY` (adopted) requests
  this workstream directly in its own Implementation Plan.
- Backlog: `project/design/backlog.md` has two live entries the adopted
  proposal itself cites as demand — "`pilot_usage.jsonl` doesn't track
  genre-detect or segmentation cost at all" (P2, real cost-visibility
  gap) and "Pilot's default parameters optimize for full genre coverage,
  not minimum-cost validation" (P3, decision needed). Both are candidate
  scope for WI 1 (the test harness) to close or explicitly defer.
- Recommendation: Proceed.

## Work Items

Per the proposal's Implementation Plan, this workstream expects four, in
sequence (each of WI 2-4 depends on WI 1's harness):

- **WI-PILOT-0051 — targeted test harness** (Decision 2):
  `--story`/`--story-list` flag on `run_pilot.py`, fixture set,
  per-stage cost reporting. Created 2026-08-07.
- **WI 2 — prompt caching evaluation** (Decision 3): measure the real,
  narrower caching benefit (or the mid-conversation-tool-changes
  alternative) against WI 1's fixture set given the per-call
  different-tool-schema constraint; only proceeds to `cache_control`
  adoption if it shows a real, worthwhile saving.
- **WI 3 — Batch API evaluation** (Decision 4): go/no-go assessment using
  WI 1's (and, if it lands, WI 2's) now-measurable baseline; only
  proceeds to implementation if the assessment favors it.
- **WI 4 — model tiering evaluation** (Decision 5): per-stage `--model`
  support plus real output-quality comparison against WI 1's fixtures;
  only proceeds to adoption if quality holds.

## Exit Criteria

(see frontmatter `exit_criteria:` above)

## Non-Goals

- Does not adopt prompt caching, the Batch API, or model tiering outright
  — all three are gated evaluation decisions (Decisions 3, 4, 5), not
  commitments. An evaluation concluding "reject" is a valid, complete
  outcome for that work item.
- Does not merge or redesign the entity/event/relation/discourse
  extraction sequence (Decision 6, rejected in the proposal).
- Does not implement or evaluate local-model support — a separate,
  parallel track already covered by `PROP-ERW-LOCAL-MODEL-EVALUATION`
  (Decision 7).
- Does not change the checkpointing architecture itself
  (`WI-PIPELINE-0040`/`0041`) — any Batch API work is scoped as an
  extension, evaluated on its own terms.
- Does not re-scope `WI-EVENT-0030`'s stratified pilot for 8 genres —
  that is `WI-ASSESS-0031`'s and the genre-reconciliation backlog
  entries' concern, tracked separately.
- Does not adopt OpenTelemetry or a workflow-orchestration framework
  (Prefect/Dagster/Airflow) for cost logging — the 2026-07-27 audit's own
  Category E1 table already considered and set these aside as overkill
  for a single-researcher local pipeline; nothing here revisits that.

## Open Questions

- Exact fixture-set composition and size for the test harness — deferred
  to WI 1's own scoping.
- Whether WI 2-4's evaluations run sequentially or in parallel once WI 1
  lands — the proposal notes the Batch API and model-tiering evaluations
  "depend on the harness and on each other's findings," but does not
  mandate a strict order beyond that; deferred to work-item scoping.
