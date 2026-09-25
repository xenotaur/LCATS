---
id: WS-PILOT-IMPROVEMENTS
kind: planning_node
title: Stabilized user-facing improvements for the ERW cross-segment relation pilot
status: proposed
stage: designed
origin: design_review
summary: Deliver PROP-LCATS-PILOT-IMPROVEMENTS by proving the real ERW pilot API/output path under a bounded stability gate, then adopting measured prompt-caching, model-tiering, Batch API, and run-mode ergonomics behind that gate.
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap: []
related_design:
  - lcats/project/design/proposals/proposed/lcats-pilot-improvements/00_proposal.md
  - lcats/project/design/proposals/adopted/lcats-pilot-cost-sustainability/00_proposal.md
  - lcats/project/workstreams/resolved/WS-PILOT-COST-SUSTAINABILITY.md
  - lcats/project/design/proposals/adopted/lcats-pipeline-checkpointing/00_proposal.md
  - lcats/project/audits/2026-07-27-erw-pipeline-structured-output-reliability-audit.md
  - lcats/project/design/backlog.md
work_items:
  - WI-PILOT-0067
  - WI-SEGMENT-0071
  - WI-SEGMENT-0072
  - WI-PILOT-0082
  - WI-SEGMENT-0097
  - WI-SEGMENT-0098
  - WI-SEGMENT-0099
  - WI-SEGMENT-0101
  - WI-SEGMENT-0102
  - WI-SEGMENT-0106
exit_criteria:
  - A first pilot API/output stability gate has run against a bounded, explicitly approved real Anthropic story set and reports completion, artifact well-formedness, semantic sense, quality thresholds, intended-purpose fit, actual spend, and explicit genre-detection coverage
  - Prompt-caching adoption, if still supported after the stability gate, is implemented only as an explicit pilot-level setting with cache telemetry and no global backend default change
  - Genre/segmentation model-tiering adoption, if still supported after the stability gate, is implemented only for those lower-risk stages with schema, truncation, sanitization, and semantic-quality telemetry preserved
  - Batch API work has at least a durable opt-in design for submit/poll/result-ingestion and checkpoint publication, and any implementation is validated with a bounded real batch-mode run before researcher-facing use
  - User-facing pilot run modes, CLI help, documentation, or wrappers make validation, synchronous pilot, and opt-in batch choices understandable without reverse-engineering individual flags
  - All linked work items are resolved and lrh validate reports 0 errors
---

# Workstream: Stabilized user-facing improvements for the ERW cross-segment relation pilot

## Purpose

This workstream delivers `PROP-LCATS-PILOT-IMPROVEMENTS`
(`lcats/project/design/proposals/proposed/lcats-pilot-improvements/00_proposal.md`),
the follow-on implementation direction after
`PROP-LCATS-PILOT-COST-SUSTAINABILITY`. The completed cost-sustainability
studies produced go recommendations for prompt caching, model tiering, and
Batch API use, but they also confirmed that cost reduction is not enough if
the pilot can still produce malformed, semantically weak, or research-useless
output. This workstream therefore coordinates a stability gate first, then
implements measured cost and ergonomics improvements behind that gate.

## Scope

- Define and run a bounded real API/output stability gate for the ERW pilot,
  including explicit spend estimation/approval, artifact validation, semantic
  review, quality thresholds, intended-purpose fit, and real genre-detection
  coverage.
- Adopt prompt caching for pilot runs only if the stability gate passes,
  preserving the backend default and cache-token telemetry.
- Adopt Haiku 4.5 or another cheaper tier for genre detection and segmentation
  only if the stability gate passes, preserving schema, truncation,
  sanitization, and semantic-quality telemetry.
- Design an opt-in Batch API mode with a durable submit/poll/result-ingestion
  ledger and checkpoint-publication model.
- Implement and validate Batch API mode only after the stability gate passes,
  including a bounded real batch-mode validation before researcher-facing use.
- Improve user-facing pilot run modes, CLI help, README guidance, or wrappers
  so researchers can choose validation, synchronous pilot, or opt-in batch
  runs intentionally.
- Land each work item through the standard LRH execution lifecycle.

## Prior Art Check

### Duplication search

- In-repo: No existing `WS-PILOT-IMPROVEMENTS` workstream was found. Related
  but not duplicate: `WS-PILOT-COST-SUSTAINABILITY` owns the completed
  evaluation workstream, while `PROP-LCATS-PILOT-IMPROVEMENTS` requests this
  follow-on implementation workstream directly.
- Sibling repos: None identified.
- External libraries: None identified. This workstream coordinates LCATS
  pipeline behavior, LRH control-plane scoping, and native Anthropic API
  features rather than adopting a third-party library.
- Recommendation: Proceed.

### Demand search

- Work items: `WI-PILOT-0067` now scopes the new stability gate. Related
  resolved items are `WI-PILOT-0051`, `WI-PILOT-0057`, `WI-PILOT-0058`, and
  `WI-PILOT-0060`, which produced the harness and evaluations this
  workstream builds on.
- Proposals: `PROP-LCATS-PILOT-IMPROVEMENTS` explicitly requests creation of
  `WS-PILOT-IMPROVEMENTS`.
- Backlog: Matching backlog demand exists for pilot usage visibility and
  minimum-cost validation in `lcats/project/design/backlog.md`; this
  workstream should close, revise, or explicitly defer those entries only
  after the scoped work items clarify what remains.
- Recommendation: Proceed; implement `WI-PILOT-0067` before downstream
  adoption work.

## Work Items

Per `PROP-LCATS-PILOT-IMPROVEMENTS`, this workstream should create and
sequence work items in this order. The `work_items:` frontmatter is the
authoritative linked-item list for LRH validation and closeout; this section
documents the intended execution order and must stay in sync with that list.

1. **`WI-PILOT-0067`: Pilot API/output stability gate** - Define and run a
   bounded real end-to-end validation that checks completion, artifact
   well-formedness, semantic sense, quality thresholds, intended-purpose fit,
   actual spend, and explicit genre-detection coverage. This is a
   prerequisite for all later implementation work.
2. **`WI-SEGMENT-0070`: Narrow segmentation anchor-matching fix** - Before
   downstream pilot adoption work proceeds, implement the already-filed
   paragraph-marker and quote/dash typography fixes that address the
   well-understood `WI-SEGMENT-0069` sub-categories. This item is tracked in
   its own segmentation planning path, not as a `work_items:` member here, but
   the two linked investigations below depend on it.
3. **`WI-SEGMENT-0071`: Paragraph-misnumbering diagnostics** - Diagnose the
   paragraph-misnumbering categories that `WI-SEGMENT-0070` explicitly leaves
   unhandled. This informs whether a future safe alignment fix should be
   filed before relying on larger pilot runs.
4. **`WI-SEGMENT-0072`: Near-miss fuzzy-matching evaluation** - Evaluate
   whether fuzzy matching can safely recover near-miss anchors without
   reintroducing the silent wrong-match behavior documented by
   `WI-SEGMENT-0059`. This is an evaluation gate, not an implementation.
5. **`WI-PILOT-0082`: Bounded retry-with-backoff for transient API errors**
   (resolved via PR #368) - Added opt-in retry logic for
   server-overload/rate-limit failures (`_classify_api_error`'s existing
   `can_retry` categories), distinct from `WI-PILOT-0067`'s blocking
   failure mode (segmentation alignment, a deterministic issue retry
   doesn't help) and not gated on it. Verified entirely with mocked
   backends, no real spend. Wiring the new parameters into
   `run_pilot.py`'s CLI remains a separate, unfiled follow-on per this
   item's own Non-Goals.
6. **`WI-SEGMENT-0097`: Case-insensitive segmentation anchor matching**
   (resolved via PR #402) - Real evidence from `WI-EVENT-0096`'s
   2026-08-26 measurement found 2 of
   10 post-`WI-SEGMENT-0070` alignment failures are pure case-only
   near-misses. Extend `_locate_anchor_span`'s existing deterministic
   typography-normalization fallback with case-insensitivity - narrow
   and safe, not a reopening of `WI-SEGMENT-0072`'s deferred question.
7. **`WI-SEGMENT-0098`: Investigate paragraph-range boundary truncation**
   (resolved via PR #403) - Root-caused all 6 real alignment failures
   whose anchors are recoverable just outside the model's claimed
   paragraph range: all fall in the paragraph immediately after
   `end_par_id`, never before - a model-side attribution error at
   narrative-continuity boundaries, not a code-side indexing bug.
   Recommends a narrowly-scoped end-boundary-only search-window
   widening, sizing deferred to a broader real sample; not implemented
   by this item.
8. **`WI-SEGMENT-0099`: Extend near-miss fuzzy-matching evaluation**
   (resolved via PR #409) - Adds 2 new real positive cases (a content
   substitution and a spelling typo) to `WI-SEGMENT-0072`'s deferred
   evaluation corpus and reports against its frozen adoption thresholds,
   without lowering them - 75% exact recovery (up from 50%), 0 false
   positives, still short on corpus size; recommendation remains defer.
9. **`WI-SEGMENT-0101`: Investigate prompt-side fix for paragraph-boundary
   end_par_id/end_exact inconsistency** (proposed) - `WI-SEGMENT-0098`
   ruled out a prompt fix without checking the actual prompt text; direct
   inspection found `end_par_id`/`start_par_id` and `end_exact`/`start_exact`
   are independently-generated fields with no instruction requiring them
   to agree. Investigates whether deriving `end_par_id` from `end_exact`'s
   location reduces the pattern, via a real-API ablation (cost estimate +
   approval required, not covered by this item).
10. **`WI-SEGMENT-0102`: Regression-test the fuzzy near-miss matcher against
    currently-correct real segments** (proposed) - Closes a gap the
    `WI-SEGMENT-0072` evaluation's own design doc names: the
    `strict_local_fuzzy` policy has never been tested against real,
    already-correctly-aligned segments. Runs it against all such committed
    real segments (56+ known) and confirms it never disturbs an
    already-correct span - a non-regression check, independent of and not
    counting toward `WI-SEGMENT-0072`'s frozen adoption thresholds.
11. **`WI-SEGMENT-0106`: Investigate combining paragraph-boundary prompt
    fix with window-widening** (proposed) - `WI-SEGMENT-0098` recommended
    an end-boundary window-widening fix but never sized the margin;
    `WI-SEGMENT-0101` found its own prompt-side fix directionally
    positive but incomplete, with 2 unexplained regressions. This item
    resolves both open questions entirely from already-committed real
    data (no new API spend): root-causes the 2 regressions (allowing an
    explicit inconclusive verdict), sizes the window-widening margin
    separately for start-side and end-side anchor failures, and
    simulates the combined fix with an independent correctness check on
    every newly-recovered match.
12. **Prompt caching adoption** - If the stability gate and segmentation
    reliability follow-ups still support proceeding, expose
    explicit pilot-level prompt caching for Anthropic fixture/pilot runs,
    preserving `AnthropicBackend(enable_prompt_caching=False)` as the global
    default and retaining cache token telemetry.
13. **Genre/segmentation model-tiering adoption** - If the stability gate and
    segmentation reliability follow-ups still support proceeding, adopt
    cheaper-tier model settings for genre detection and segmentation in the
    pilot's recommended configuration while preserving schema, truncation,
    sanitization, and semantic-quality telemetry.
14. **Batch API opt-in design** - Design the durable batch ledger,
    submit/poll/result-ingestion flow, and interaction with `checkpoint.py`.
    This design-only work can proceed without real API spend.
15. **Batch API opt-in implementation and validation** - If the stability gate
    and segmentation reliability follow-ups still support proceeding,
    implement opt-in Batch API mode, publish per-stage checkpoints only after
    result ingestion, and run a bounded real batch validation before treating
    batch mode as usable.
16. **User-facing pilot run ergonomics** - Clarify CLI help, docs, output
    summaries, or wrappers so a researcher can choose a cheap validation run, a
    synchronous high-visibility pilot run, or an opt-in lower-cost batch run.

## Exit Criteria

- A first pilot API/output stability gate has run against a bounded,
  explicitly approved real Anthropic story set and reports completion,
  artifact well-formedness, semantic sense, quality thresholds,
  intended-purpose fit, actual spend, and explicit genre-detection coverage.
- Prompt-caching adoption, if still supported after the stability gate, is
  implemented only as an explicit pilot-level setting with cache telemetry and
  no global backend default change.
- Genre/segmentation model-tiering adoption, if still supported after the
  stability gate, is implemented only for those lower-risk stages with schema,
  truncation, sanitization, and semantic-quality telemetry preserved.
- Batch API work has at least a durable opt-in design for
  submit/poll/result-ingestion and checkpoint publication, and any
  implementation is validated with a bounded real batch-mode run before
  researcher-facing use.
- User-facing pilot run modes, CLI help, documentation, or wrappers make
  validation, synchronous pilot, and opt-in batch choices understandable
  without reverse-engineering individual flags.
- All linked work items are resolved and `lrh validate` reports 0 errors.

## Non-Goals

- Does not implement any pilot cost-saving or ergonomics change directly.
  This workstream scopes and sequences the follow-on work items.
- Does not default prompt caching, model tiering, or Batch API on merely
  because the cost-sustainability evaluations produced go recommendations.
- Does not replace the synchronous Messages API path, which remains necessary
  for local debugging and per-story/per-stage visibility.
- Does not fuse entity/event/relation/discourse extraction calls; Decision 6
  of `PROP-LCATS-PILOT-COST-SUSTAINABILITY` continues to reject that
  direction.
- Does not fold local-model evaluation into this workstream.
- Does not authorize unbounded real API runs. Every real run in this
  workstream must estimate calls/cost first and receive explicit in-session
  approval.

## Open Questions

- What exact story set should the first stability gate use: the current
  `WI-PILOT-0051` fixture set, a slightly larger curated set, or a mixed set
  including known hard cases?
- What exact quality thresholds should block downstream adoption work?
- Should prompt caching and model tiering adoption be separate work items or a
  single low-risk pilot-configuration item after the stability gate?
- Should user-facing run modes be implemented as new `run_pilot.py` flags,
  documented recipes using existing flags, or a thin wrapper script?
