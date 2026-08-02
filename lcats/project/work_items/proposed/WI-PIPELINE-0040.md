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
  - lcats/project/design/proposals/adopted/lcats-story-bucket-layout/00_proposal.md
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
  - A shared checkpoint helper module exists (lcats/src/lcats/utils/checkpoint.py) providing a per-item/per-stage checkpoint API generalizing DataGatherer's dual-root bucket-directory + file-existence pattern
  - The API takes a required working_root (where checkpoint files are written) and an optional source_root (where upstream/input content lives), with source_root defaulting to working_root when omitted, per the 2026-08-02 decision_log.md entry
  - The checkpoint predicate (is this stage already done?) consults working_root only; source_root is never read by the predicate itself, keeping it a caller-facing convenience for input-reading, not a helper-internal concern
  - If a resolved working_root falls under the canonical data/ or corpora/ root (anchored via paths.find_pyproject_root(__file__), not env.data_root()/env.corpora_root()'s CWD-relative defaults, which do not match run_pilot.py's documented repo-root invocation and default --data-dir=lcats/data), the helper rejects the call unless an explicit override is passed; no equivalent guard applies to source_root, since pointing source_root at corpora/ or data/ as a read-only input is an intended, legitimate use
  - Checkpoint publication is atomic: writes go to a temp path in the same directory and are moved into place via os.replace/Path.replace only after the write completes, per Decision 1
  - Any checkpoint file that fails to parse (I/O error, JSON error) is treated as incomplete, never as done and never as a hard failure that aborts the caller, per Decision 1
  - The checkpoint predicate distinguishes success from recorded failure (not bare file presence), per Decision 2
  - The helper's checkpoint API requires every caller to explicitly pass a fingerprint argument (no silent default) alongside a checkpoint's outcome, per Decision 2; the exact fingerprint contents are caller-defined (e.g. model name plus a prompt/schema version/hash), and a fingerprint mismatch on resume is treated as if the checkpoint did not exist
  - A caller that explicitly opts out by passing an empty/no-op fingerprint gets defined, documented resume behavior (the mismatch check never invalidates that caller's checkpoints, since there is nothing to compare) rather than an undefined or silently-broken state
  - The helper's API supports per-stage granularity (independent checkpoints for distinct pipeline stages within a single run), per Decision 3
  - Per-story checkpoint subdirectories under working_root reuse the same directory slug discovery.py's canonical selector uses for a story's own bucket directory, and directory creation uses lcats.utils.paths.makedirs() rather than bare os.makedirs
  - New unit tests cover atomic publication under simulated interruption, the success/failure predicate, fingerprint mismatch invalidation, the dual-root default-to-working-root behavior, and the write-guard (including its override and a case proving the guard still fires when the process CWD differs from the checkpoint module's own file location)
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

**Updated 2026-08-02, see `project/memory/decision_log.md`'s
2026-08-02 entry:** `PROP-LCATS-STORY-BUCKET-LAYOUT` landed after this
item was scoped, changing `DataGatherer.ensure()`
(`lcats/src/lcats/gatherers/downloaders.py:200-233`, superseding the
earlier `:223-253` citation) to write `<collection>/<story>/story.json`
bucket directories rather than the flat cache layout this item was
originally written against. The helper must not write checkpoints into
`data/` or `corpora/` by default — both are unsuitable write targets for
arbitrary pipeline output (`data/` is a disposable, regenerable cache
per `project/design/design.md:38`; `lcats promote`'s `_copy_collection`,
`lcats/src/lcats/analysis/corpus/promote.py:172-176`, ships an entire
bucket's contents to `corpora/` unfiltered). The helper's API takes a
dual root (`working_root`/`source_root`) instead, per the decision log
entry, so a caller can still read `corpora/`/`data/` as an immutable
source while writing checkpoints to its own working directory.

### Duplication search
- In-repo: No existing implementation. `lcats/src/lcats/pipeline.py` is a
  documented, tested module but has no disk persistence of any kind (see
  the proposal's own Prior Art Check) — not something to extend as-is.
  `DataGatherer.ensure`/`download` (`lcats/src/lcats/gatherers/downloaders.py:200-233,239-`)
  is the closest existing precedent, but is bucket-specific, not a
  reusable, importable helper. `DataGatherer.__init__`
  (`downloaders.py:167-195`) is also the direct precedent for this item's
  dual-root (`working_root`/`source_root`) API: it already keeps two
  independently-defaulted roots, `root` (destination bucket) and `cache`
  (resource cache). `paths.find_pyproject_root()`
  (`lcats/src/lcats/utils/paths.py:81-114`) is the existing precedent
  for this item's write-guard anchor: it already walks upward from a
  file location (not CWD) to find a stable project root, and is already
  used this way by `lcats.utils.secrets`/`lcats.utils.test_utils`.
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
- Implement the dual-root API (`working_root` required, `source_root`
  optional and defaulting to `working_root`) and the `working_root`
  write-guard against the canonical `data/`/`corpora/` roots — anchored
  via `paths.find_pyproject_root(__file__)`, not `env.data_root()`/
  `env.corpora_root()`'s CWD-relative defaults — per the 2026-08-02
  `decision_log.md` entry.
- Unit-test the helper in isolation, with no dependency on `run_pilot.py`
  or any real LLM backend.

## Required Changes

1. Create `lcats/src/lcats/utils/checkpoint.py` implementing the
   checkpoint API described above: functions (matching the prevailing
   function-based style of `lcats/src/lcats/utils/env.py`/`paths.py`,
   not a stateful class) taking explicit `working_root`/`source_root`
   parameters, using `lcats.utils.paths.makedirs()` for directory
   creation and a `promote.py`-style resolved-path containment check
   (`lcats/src/lcats/analysis/corpus/promote.py:144-170`) for the
   `working_root` write-guard — with the protected `data/`/`corpora/`
   roots anchored via `paths.find_pyproject_root(__file__)`
   (`lcats/src/lcats/utils/paths.py:81-114`), the same CWD-independent
   pattern `lcats.utils.secrets`/`lcats.utils.test_utils` already use,
   not `env.data_root()`/`env.corpora_root()`'s CWD-relative defaults.
2. Create `lcats/tests/utils_tests/checkpoint_test.py` covering atomic
   publication (including simulated interruption of the write), the
   success/failure predicate, configuration-fingerprint mismatch
   invalidation, the dual-root default-to-`working_root` behavior, and
   the write-guard (triggering it, overriding it, and confirming it
   still fires when the test's process CWD differs from the repo root).

## Non-Goals

- Does not migrate `run_pilot.py` itself onto the helper — that is
  WI-PIPELINE-0041.
- Does not adopt Ray, Dagster, or Prefect — per the proposal's Non-Goals.
- Does not implement Category E1 (model-invocation logging/budget
  enforcement) — per the proposal's Non-Goals.
- Does not decide the exact *contents* of any specific caller's
  fingerprint (e.g. `run_pilot.py`'s own model/schema versioning fields)
  — the helper's API requires a fingerprint argument on every call (never
  silently defaulted) but leaves what goes inside it to each caller;
  per-caller fingerprint design is WI-PIPELINE-0041's concern. A caller
  may still choose an empty/no-op fingerprint, but that is an explicit,
  visible argument at the call site, not an omitted parameter.
- Does not decide whether or how pipeline checkpoint sidecars should
  ever be promoted or merged back into `data/`/`corpora/` as pipelines
  mature — the `working_root` write-guard exists specifically so this
  item does not silently make that decision by default; if/when that
  integration is wanted, it is separately-scoped future design work.

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
- The `working_root` write-guard must compare *resolved* paths
  (`Path.resolve()`), matching `promote.py`'s own `_validate_distinct_roots`
  approach — comparing unresolved paths would let a symlink or a
  relative-path variant silently bypass the guard.
- Building the guard on `env.data_root()`/`env.corpora_root()` directly
  (rather than anchoring via `paths.find_pyproject_root(__file__)`)
  would make it CWD-dependent and silently ineffective for
  `run_pilot.py`'s own documented repo-root invocation, since
  `env.data_root()`'s CWD-relative default does not resolve to the same
  directory as `run_pilot.py`'s own default `--data-dir=lcats/data` when
  launched as documented (review finding, PR #210).

## Dependencies / Order

No dependencies — this item should land first, since WI-PIPELINE-0041
depends on it.

## Related Workstream and Designs

- Workstream: `project/workstreams/proposed/WS-PIPELINE-CHECKPOINTING.md`
- Design: `project/design/proposals/adopted/lcats-pipeline-checkpointing/00_proposal.md`
