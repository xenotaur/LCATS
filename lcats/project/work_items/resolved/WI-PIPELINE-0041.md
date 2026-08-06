---
resolution: "Implemented and merged via PR #217 (commit 44e7a3e2): run_pilot.py migrated to staged, checkpointed execution (genre_detect, segment, erw_extract, cross_segment_relation, each independently checkpointed per Decision 3), discovery selector fixed to use discovery.find_json_files, and re-vetted against this session's 8 operational criteria - both hard blockers (bounded small-scale trial, crash/interrupt recovery) confirmed resolved via a real KeyboardInterrupt test. See execution record project/executions/WI-PIPELINE-0041/2026_08_03_05_47_27_WI_PIPELINE_0041.md."
blocked_reason: null
blocked: false
id: WI-PIPELINE-0041
title: Migrate run_pilot.py to staged, checkpointed execution and re-vet against operational criteria
type: deliverable
status: resolved
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
depends_on:
  - WI-PIPELINE-0040
blocked_by: []
expected_actions:
  - edit_file
  - run_tests
  - create_pr
forbidden_actions:
  - force_push
  - delete_branch
  - implement_new_architecture
  - run_real_llm_calls_without_explicit_approval
acceptance:
  - run_pilot.py uses the WI-PIPELINE-0040 checkpoint helper for staged execution, with separate checkpointed artifacts for genre-detection, segmentation, ERW-extraction, and cross-segment-relation (per Decision 3 and WS-PIPELINE-CHECKPOINTING's exit criteria), not the whole per-story pipeline collapsed into one checkpointed unit
  - A bounded small-scale trial (at most a few dozen LLM calls) can be run end to end, verified without spending real API money via a fake-backend harness
  - A crash or Ctrl-C mid-run preserves every already-completed stage's checkpointed output, verified via a fake-backend harness that actually raises KeyboardInterrupt (or terminates a subprocess) after partial completion — not merely an ordinary Exception, which run_pilot.py's existing except Exception block would catch and continue past without ever exercising the real interruption path
  - A resumed run after interruption skips already-checkpointed, successfully-completed stages and does not re-issue their LLM calls
  - The migrated script is re-vetted against the same 8 operational criteria used to freeze it this session (unit tested, bounded small-scale trial, pipelined/resumable, stronger validation, stronger error detection, call estimation, logging, call counting), with both hard blockers (bounded trial, crash/interrupt recovery) confirmed resolved
  - run_pilot.py's story-input discovery uses discovery.find_json_files([data_dir]) (not discovery.iter_collection_story_files, which only examines a single collection directory's immediate children and yields nothing when called on a multi-collection corpus root like the documented --data-dir default) instead of the current data_dir.rglob("*.json"), so a post-migration data/ or corpora/ source no longer has its sidecar files misread as spurious stories, and every collection under data_dir is still actually traversed
  - The checkpoint helper is invoked with working_root pointed at run_pilot.py's own results directory (never the canonical data/corpora roots WI-PIPELINE-0040's write-guard protects) and source_root pointed at whatever data/corpora location the run reads stories from, per WI-PIPELINE-0040's dual-root API
  - lrh validate reports 0 errors
required_evidence:
  - manual_review
  - lrh_validate
  - test_output
artifacts_expected:
  - experiments/03_cross_segment_relation_pilot/run_pilot.py
  - experiments/03_cross_segment_relation_pilot/run_pilot_test.py
---

## Summary

Migrate `run_pilot.py` from its current in-memory-only, write-at-the-end
architecture to staged, checkpointed execution using the
WI-PIPELINE-0040 helper, then re-vet the migrated script against this
session's own 8 operational criteria before it is considered safe for
another real, paid run.

## Problem / Context

This session vetted `run_pilot.py` against 8 operational criteria after
3 real runs (~$50) left zero surviving artifacts, and found it fails
both hard blockers: no bounded small-scale trial (a minimal real run
costs ~98-479 calls, not "a few dozen"), and no persistence/resume (a
crash or Ctrl-C, which is not an `Exception` subclass and escapes the
script's `except Exception` catch-all, discards every already-paid-for
result). `PROP-LCATS-PIPELINE-CHECKPOINTING` (adopted) exists to fix
this, and this item is its second Implementation Plan item — the actual
migration, gated on WI-PIPELINE-0040's helper landing first.

**Updated 2026-08-02, see `project/memory/decision_log.md`'s
2026-08-02 entry:** `PROP-LCATS-STORY-BUCKET-LAYOUT` landed after this
item was scoped and surfaced a second, independent gap in `run_pilot.py`
itself: its story-input discovery
(`experiments/03_cross_segment_relation_pilot/run_pilot.py:201-202`,
`data_dir.rglob("*.json")`) still does the same over-broad recursive
JSON matching `discovery.py`'s Decision 3 replaced in the core package —
once `data/` is regenerated under the new bucket-writing `DataGatherer`,
this glob will pick up sidecar files (`audit.json`, etc.) as if they
were separate stories. This item now also fixes that discovery path,
using WI-PIPELINE-0040's dual-root API with `source_root` pointed at
wherever the run reads stories from (`data/` or `corpora/`, read-only)
and `working_root` pointed at this script's own results directory,
never at `data/`/`corpora/` directly.

### Duplication search
- In-repo: No existing migration. `check_segmentation_reliability.py`
  (PR #189) already demonstrates per-story persistence for segmentation
  alone, but is deliberately scoped to a single stage, not a general
  pattern — not a duplicate of this broader migration.
- Sibling repos: None identified.
- External libraries: None — this item uses WI-PIPELINE-0040's helper,
  not a new orchestration framework.
- Recommendation: Proceed.

### Demand search
- Work items: None found beyond this proposal's own request.
- Proposals: `PROP-LCATS-PIPELINE-CHECKPOINTING`'s Implementation Plan
  names this as its second item, explicitly gated on the shared helper.
- Backlog: No matching entries.
- Recommendation: Proceed.

## Scope

- Migrate `run_pilot.py`'s genre-detection scan, segmentation,
  ERW-extraction, and cross-segment-relation stages to use the
  WI-PIPELINE-0040 checkpoint helper, per Decision 3's per-stage
  granularity.
- Define this script's own configuration-fingerprint contents (model
  name, prompt/schema/extractor-version fields, and a hash/version of
  each stage's actual upstream input), per Decision 2 — left open by
  WI-PIPELINE-0040 as a per-caller choice. A downstream stage's
  checkpoint identity must include or derive from its upstream input, so
  correcting an earlier stage's output under an unchanged model
  configuration still invalidates dependent checkpoints rather than
  silently combining stale downstream results with corrected upstream
  ones.
- Re-vet the migrated script against this session's 8 operational
  criteria, using a fake-backend harness for the bounded-trial and
  crash-recovery checks (no real API spend required to verify these).
- Fix `run_pilot.py`'s story-input discovery to use a bucket-aware
  selector instead of its current recursive `*.json` glob, and invoke
  the checkpoint helper with `source_root` (read-only input) separate
  from `working_root` (this script's own results directory), per
  WI-PIPELINE-0040's dual-root API.

## Required Changes

1. Migrate `run_pilot.py`'s per-story loop and its genre-detection scan
   to checkpoint through the WI-PIPELINE-0040 helper, replacing the
   current write-at-the-end `.open("w")` sites.
2. Define and wire up this script's configuration fingerprint (model,
   prompt/schema version, and a hash/version of each stage's upstream
   input) into every checkpoint call, so a downstream checkpoint is
   invalidated if its upstream input changes even under an unchanged
   model configuration.
3. Add or extend `run_pilot_test.py` with fake-backend-harness tests
   proving: a bounded small-scale trial completes without full-run cost;
   an interruption that actually raises `KeyboardInterrupt` (or
   terminates a subprocess) mid-run preserves already-checkpointed
   stages, not merely an ordinary `Exception` that the script's existing
   `except Exception` block would already catch and continue past; and a
   resumed run skips already-successful, fingerprint-matching stages.
4. Re-run this session's 8-criteria vetting against the migrated script
   and document the result (e.g. in the PR description or a short
   validation note), explicitly confirming both hard blockers are
   resolved.
5. Replace `_iter_candidate_files`'s `data_dir.rglob("*.json")`
   (`run_pilot.py:201-202`) with `discovery.find_json_files([data_dir])`
   — `data_dir` is a corpus root containing multiple collection
   directories, and `discovery.iter_collection_story_files` only
   examines one collection's immediate children, yielding no candidates
   at all if called directly on `data_dir` (review finding, PR #210).
   Thread `source_root`/`working_root` through the script's
   `--data-dir`/`--output` arguments so input reads and checkpoint
   writes go to separate roots.

## Non-Goals

- Does not implement the shared checkpoint helper itself — that is
  WI-PIPELINE-0040, a hard dependency.
- Does not run a real, paid `run_pilot.py` execution as part of this
  item — re-vetting must be demonstrated via a fake-backend harness, not
  a real API spend, matching this session's own dry-run discipline.
- Does not migrate any other batch script (`lcats/KMo/`, other
  `experiments/` scripts) — per the proposal's Non-Goals.
- Does not implement Category E1 (logging/budget enforcement) — per the
  proposal's Non-Goals.
- Does not change `check_segmentation_reliability.py`'s existing,
  narrower persistence approach — per the proposal's Non-Goals.

## Acceptance Criteria

(see frontmatter `acceptance:` above)

## Validation

- `scripts/version tools`
- `lrh validate`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- Fake-backend harness run demonstrating bounded trial, interrupt
  recovery via an actual `KeyboardInterrupt` or terminated subprocess
  (not an ordinary caught `Exception`), and resume-skip behavior (no
  real API calls)

## Risk Notes

- A fake-backend test can pass for the wrong reason if it doesn't
  exercise the real interruption/resume code path (a confirmed recurring
  failure mode this session, e.g. `_classify_api_error` not actually
  reached by one error branch) — tests must simulate the real
  interruption mechanism (`KeyboardInterrupt` or a terminated
  subprocess, not an ordinary caught `Exception`, per review on PR #195),
  not just assert on a mocked return value.
- A fingerprint scoped to model/schema version alone would miss upstream
  input changes (e.g. a corrected source story reprocessed under the
  same model), silently combining a stale downstream checkpoint with a
  corrected upstream result — per review on PR #195, checkpoint identity
  must account for upstream input, not configuration alone.
- Re-vetting "on paper" without an actual fake-backend run would repeat
  this session's own original vetting gap.
- Verifying the discovery-selector fix requires a corpus fixture that
  actually contains a sidecar file alongside `story.json` — a fixture
  with only bare story files would not exercise the bug the fix targets.
- Verifying the fix also requires a fixture with more than one
  collection directory under the corpus root — a single-collection
  fixture would not distinguish a correct multi-collection selector from
  the broken `iter_collection_story_files`-on-`data_dir` call the
  original scope draft mistakenly specified (review finding, PR #210).

## Dependencies / Order

Depends on WI-PIPELINE-0040 landing first — this item cannot start
implementation until the shared checkpoint helper and its API exist.

## Related Workstream and Designs

- Workstream: `project/workstreams/resolved/WS-PIPELINE-CHECKPOINTING.md`
- Design: `project/design/proposals/adopted/lcats-pipeline-checkpointing/00_proposal.md`
