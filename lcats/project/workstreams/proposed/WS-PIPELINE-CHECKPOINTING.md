---
id: WS-PIPELINE-CHECKPOINTING
kind: planning_node
title: Staged, checkpointed pipeline execution for LCATS batch scripts
status: proposed
stage: designed
origin: design_review
summary: Deliver PROP-LCATS-PIPELINE-CHECKPOINTING's shared checkpoint helper and migrate run_pilot.py to staged, checkpointed execution, so a crash or interruption no longer discards already-paid-for LLM calls.
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap: []
related_design:
  - lcats/project/design/proposals/proposed/lcats-pipeline-checkpointing/00_proposal.md
  - lcats/project/audits/2026-07-27-erw-pipeline-structured-output-reliability-audit.md
  - lcats/project/workstreams/proposed/WS-EVENT-STRUCTURED-OUTPUT-RELIABILITY.md
work_items: []
exit_criteria:
  - A shared checkpoint helper exists (location settled during work-item scoping) implementing Decision 1's atomic temp-file + rename publication and Decision 2's success/failure predicate plus configuration-identity fingerprint, with unit tests
  - run_pilot.py is migrated to staged, checkpointed execution per Decision 3's per-stage granularity, with separate checkpointed artifacts for genre-detection, segmentation, ERW-extraction, and cross-segment-relation (not the whole per-story pipeline collapsed into one unit)
  - The migrated run_pilot.py is re-vetted against the same 8 operational criteria used to freeze it this session, with both hard blockers (bounded small-scale trial, crash/interrupt recovery) confirmed resolved
  - Both work items resolved and lrh validate reports 0 errors
---

# Workstream: Staged, checkpointed pipeline execution for LCATS batch scripts

## Purpose

This workstream will deliver `PROP-LCATS-PIPELINE-CHECKPOINTING`
(`lcats/project/design/proposals/proposed/lcats-pipeline-checkpointing/00_proposal.md`),
drafted and confirmed this session in response to `run_pilot.py`'s
measured failure against 8 operational criteria (3 real runs, ~$50, zero
surviving artifacts; no bounded small-scale trial). The proposal's own
`status` is still `proposed`, not yet formally `adopted` — this
workstream exists as the recommended follow-on the proposal's own
Implementation Plan calls for, and its scoping is contingent on that
proposal's adoption completing before implementation work items are
picked up. It coordinates building a shared, reusable checkpoint
pattern — not a `run_pilot.py`-only patch — and migrating `run_pilot.py`
onto it, then re-vetting the migrated script before any further real,
paid run is attempted.

## Scope

- Design and implement a shared checkpoint helper following the
  proposal's Decision 1 (atomic publication), Decision 2 (success/failure
  predicate plus configuration-identity fingerprint), and Decision 4
  (shared pattern, not a one-script fix).
- Migrate `run_pilot.py` to staged, checkpointed execution using the
  helper, per Decision 3's per-stage granularity: separate checkpointed
  artifacts for genre-detection, segmentation, ERW-extraction, and
  cross-segment-relation, not the whole per-story pipeline treated as one
  checkpointed unit (an interruption mid-pipeline must not discard
  already-succeeded earlier-stage calls for that story).
- Re-vet the migrated `run_pilot.py` against this session's own 8
  operational criteria before it is considered safe for another real run.
- Land both work items through the standard LRH execution lifecycle
  (`/lrh-implement` → `/lrh-review-response` → `/lrh-confirm-fixes` →
  `/lrh-closeout`).
- Category E1 (model-invocation logging/budget enforcement) is a stretch
  item only if picked up as part of the same effort — see Non-Goals.

## Prior Art Check

### Duplication search
- In-repo: No existing checkpointing implementation. `PROP-LCATS-PIPELINE-CHECKPOINTING`
  itself already ran this search in full (see the proposal's own Prior
  Art Check) — `lcats/src/lcats/pipeline.py` is a documented, tested
  module (root `README.md`; `lcats/tests/pipeline_test.py`) but not a
  duplicate to extend as-is for this purpose: its `Stage`/`Pipeline`/
  `RunResult`/`RunContext` dataclasses have no disk persistence or
  checkpointing of any kind, the exact gap this workstream exists to fill.
- Sibling repos: None identified.
- External libraries: Considered and deferred in the proposal (Prefect,
  Dagster, Ray, Airflow) — none adopted now; zero-dependency
  bucket-directory pattern chosen instead.
- Recommendation: Proceed.

### Demand search
- Work items: `WI-EVENT-0032` and `WI-EVENT-0033` both explicitly defer
  Category E (checkpointing/logging) as "independent and schedulable
  separately" — this workstream is exactly that follow-on.
- Proposals: `PROP-LCATS-PIPELINE-CHECKPOINTING` (drafted and confirmed
  this session; still `status: proposed`) requests this workstream
  directly in its own Implementation Plan.
- Backlog: No matching entries (no `project/design/backlog.md` exists).
- Recommendation: Proceed.

## Work Items

Not yet created. Per the proposal's Implementation Plan, this workstream
expects two work items once scoped via `/lrh-work-item`:

- **Shared checkpoint helper** — implement and unit-test the helper
  described above (Decisions 1, 2, 4).
- **`run_pilot.py` migration + re-vetting** — migrate the script to use
  the helper (Decision 3) and re-run this session's 8-criteria vetting
  against the migrated version.

## Exit Criteria

(see frontmatter `exit_criteria:` above)

## Non-Goals

- Does not adopt Ray, Dagster, Prefect, or any other orchestration
  framework — the proposal's own Non-Goals defer this until real
  parallel/distributed execution is demonstrated as needed.
- Does not implement Category E1 (model-invocation logging and
  dollar-cost budget enforcement) as a required deliverable — stretch
  only, per the proposal's Non-Goals.
- Does not migrate the corpus to the deferred per-story-directory layout
  (`flat_story_layout_migration_impact_report.md`) — a separate,
  larger body of work the proposal's design would extend to cleanly.
- Does not retrofit every existing LCATS batch script (`lcats/KMo/`,
  other `experiments/` scripts) — initial implementation targets
  `run_pilot.py` only.
- Does not change `check_segmentation_reliability.py`'s existing,
  narrower persistence approach.
- Does not decide retry/backoff policy for rate-limited or
  truncated-output API errors — deferred, per the proposal's Non-Goals.

## Open Questions

- Exact shared-helper API shape and the configuration-fingerprint
  contents — deferred to work-item scoping, per the proposal's own Open
  Questions.
- Whether Category E1 should fold into this workstream or be proposed
  separately — deferred, per the proposal's Non-Goals.
