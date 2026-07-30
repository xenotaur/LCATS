---
resolution: null
blocked_reason: null
blocked: false
id: WI-PIPELINE-0040
title: Implement shared checkpoint helper for LCATS batch scripts
type: deliverable
status: proposed
priority: high
owner: unassigned
contributors: []
assigned_agents: []
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap: []
related_workstreams:
  - WS-PIPELINE-CHECKPOINTING
related_design:
  - lcats/project/design/proposals/adopted/lcats-pipeline-checkpointing/00_proposal.md
depends_on: []
blocked_by: []
expected_actions:
  - create_file
  - run_tests
  - create_pr
forbidden_actions:
  - force_push
  - delete_branch
  - implement_new_architecture
  - modify_run_pilot_script
acceptance:
  - A shared checkpoint helper module exists (lcats/src/lcats/utils/checkpoint.py) providing a per-item/per-stage checkpoint API generalizing DataGatherer.download's bucket-directory + file-existence pattern
  - Checkpoint publication is atomic: writes go to a temp path in the same directory and are moved into place via os.replace/Path.replace only after the write completes, per Decision 1
  - Any checkpoint file that fails to parse (I/O error, JSON error) is treated as incomplete, never as done and never as a hard failure that aborts the caller, per Decision 1
  - The checkpoint predicate distinguishes success from recorded failure (not bare file presence), per Decision 2
  - Each checkpoint records a configuration-identity fingerprint (at minimum model name and a version/hash of the relevant prompt template or tool schema) alongside its outcome, and a fingerprint mismatch on resume is treated as if the checkpoint did not exist, per Decision 2
  - The helper's API supports per-stage granularity (independent checkpoints for distinct pipeline stages within a single run), per Decision 3
  - New unit tests cover atomic publication under simulated interruption, the success/failure predicate, and fingerprint mismatch invalidation
  - lrh validate reports 0 errors
required_evidence:
  - manual_review
  - lrh_validate
  - test_output
artifacts_expected:
  - lcats/src/lcats/utils/checkpoint.py
  - lcats/tests/utils_tests/checkpoint_test.py
---

## Summary

Implement a shared, reusable checkpoint helper for LCATS's LLM-driven
batch scripts, generalizing `DataGatherer.download`'s existing
bucket-directory + file-existence pattern with atomic publication,
a success/failure-plus-configuration-identity predicate, and per-stage
granularity — the shared building block `PROP-LCATS-PIPELINE-CHECKPOINTING`
calls for before any script (starting with `run_pilot.py`, in
WI-PIPELINE-0041) can be migrated onto it.

## Problem / Context

`run_pilot.py`'s current in-memory-only, write-at-the-end architecture
discards every already-paid-for LLM call on any crash or interruption —
measured directly this session (3 real runs, ~$50, zero surviving
artifacts). `PROP-LCATS-PIPELINE-CHECKPOINTING` (adopted; see
`related_design`) chose a bucket-directory + file-existence checkpoint
pattern as the fix, explicitly as a shared helper rather than a
`run_pilot.py`-only patch, since LCATS has multiple other pipeline-like
processes that would otherwise keep the same fragility. This item
delivers exactly that helper, with the two hardening requirements review
added to the proposal: atomic publication (Decision 1) and a
success/failure-plus-configuration-identity checkpoint predicate
(Decision 2).

### Duplication search
- In-repo: No existing implementation. `lcats/src/lcats/pipeline.py` is a
  documented, tested module but has no disk persistence of any kind (see
  the proposal's own Prior Art Check) — not something to extend as-is.
  `DataGatherer.download` (`lcats/src/lcats/gatherers/downloaders.py:223-253`)
  is the closest existing precedent, but is bucket-specific, not a
  reusable, importable helper.
- Sibling repos: None identified.
- External libraries: Prefect/Dagster/Ray considered and deferred in the
  governing proposal — not adopted now.
- Recommendation: Proceed.

### Demand search
- Work items: None found requesting this specifically (the proposal
  itself is the request).
- Proposals: `PROP-LCATS-PIPELINE-CHECKPOINTING`'s own Implementation
  Plan names this as its first item.
- Backlog: No matching entries.
- Recommendation: Proceed.

## Scope

- Implement a shared checkpoint helper module usable by `run_pilot.py`,
  `check_segmentation_reliability.py`, and future batch scripts alike.
- Implement Decision 1 (atomic publication) and Decision 2
  (success/failure predicate plus configuration-identity fingerprint).
- Support Decision 3's per-stage granularity (the helper's API must let a
  caller checkpoint multiple distinct stages independently, not only one
  per-item checkpoint).
- Unit-test the helper in isolation, with no dependency on `run_pilot.py`
  or any real LLM backend.

## Required Changes

1. Create `lcats/src/lcats/utils/checkpoint.py` implementing the
   checkpoint API described above.
2. Create `lcats/tests/utils_tests/checkpoint_test.py` covering atomic
   publication (including simulated interruption of the write), the
   success/failure predicate, and configuration-fingerprint mismatch
   invalidation.

## Non-Goals

- Does not migrate `run_pilot.py` itself onto the helper — that is
  WI-PIPELINE-0041.
- Does not adopt Ray, Dagster, or Prefect — per the proposal's Non-Goals.
- Does not implement Category E1 (model-invocation logging/budget
  enforcement) — per the proposal's Non-Goals.
- Does not decide the exact configuration-fingerprint contents for any
  specific caller (e.g. `run_pilot.py`'s own model/schema versioning) —
  the helper's API must make omitting a fingerprint field a deliberate
  caller choice, not prescribe the contents itself; per-caller fingerprint
  design is WI-PIPELINE-0041's concern.

## Acceptance Criteria

(see frontmatter `acceptance:` above)

## Validation

- `scripts/version tools`
- `lrh validate`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`

## Risk Notes

- Getting the atomic-publication mechanism wrong (e.g. `os.replace`
  across filesystems, which is not atomic) would silently reintroduce
  the exact torn-write failure mode this item exists to eliminate —
  worth an explicit same-filesystem-temp-path test.
- An overly narrow configuration-fingerprint API (e.g. hardcoding "model
  name" as the only field) would force WI-PIPELINE-0041 to work around
  it rather than use it as designed.

## Dependencies / Order

No dependencies — this item should land first, since WI-PIPELINE-0041
depends on it.

## Related Workstream and Designs

- Workstream: `project/workstreams/proposed/WS-PIPELINE-CHECKPOINTING.md`
- Design: `project/design/proposals/adopted/lcats-pipeline-checkpointing/00_proposal.md`
