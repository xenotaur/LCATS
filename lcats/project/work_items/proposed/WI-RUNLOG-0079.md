---
resolution: null
blocked_reason: null
blocked: false
id: WI-RUNLOG-0079
title: Migrate run_prefilter.py onto lcats.utils.run_log
type: operation
status: proposed
owner: unassigned
contributors: []
assigned_agents: []
related_focus: []
related_roadmap: []
related_workstreams:
  - WS-RUN-LOG
related_design:
  - lcats/project/design/proposals/proposed/lcats-run-log/00_proposal.md
depends_on:
  - WI-RUNLOG-0078
blocked_by: []
expected_actions:
  - edit_file
  - run_tests
forbidden_actions:
  - force_push
  - delete_branch
  - change_validation_run_log_filename
acceptance:
  - run_prefilter.py's inline _log_run_event() is removed; run_validation() and write_validation_outputs() are both covered by a single RunLog scope in _run_validate_mode(), so run_end is only emitted after output writing succeeds
  - Existing behavior is unchanged from the caller's perspective — validation_run_log.jsonl's event shape and filename are unaffected
  - An exception during write_validation_outputs() produces run_aborted_unexpected, not a run_end already emitted before the failure
  - experiments/05_metadata_genre_prefilter/run_prefilter_test.py continues to pass, extended if needed to cover the migration
  - lrh validate and scripts/test pass with 0 errors
required_evidence:
  - lrh_validate
  - test_output
artifacts_expected:
  - experiments/05_metadata_genre_prefilter/run_prefilter.py
  - experiments/05_metadata_genre_prefilter/run_prefilter_test.py
---

## Summary

Migrates `run_prefilter.py`'s inline `_log_run_event()` onto the new
shared `lcats.utils.run_log` module — the dogfooding step that proves the
shared module's API against its own reference implementation.

## Problem / Context

`PROP-LCATS-RUN-LOG` Implementation Plan step 2. `_log_run_event()`
(`run_prefilter.py:1005-1027`, current `main` — line numbers shifted
since the governing proposal was written; corrected per review finding,
PR #352) is the pattern the shared module (WI-RUNLOG-0078) generalizes;
migrating the original site first is the safest place to catch API gaps
before the module is used elsewhere.

### Duplication search
- In-repo: No existing migration. Recommendation: Proceed.
- Sibling repos: None identified.
- External libraries: None identified.
- Recommendation: Proceed.

### Demand search
- Work items: None found.
- Proposals: Found: `PROP-LCATS-RUN-LOG` — Implementation Plan step 2
  requests this directly.
- Backlog: No matching entries.
- Recommendation: No action.

## Scope

- Replace `_log_run_event()` calls in `run_validation()` with the shared
  module
- Remove the now-dead inline `_log_run_event()` function
- Wrap the full `--validate --run-real-validation` output path — not just
  `run_validation()` — in a `RunLog` scope, so an exception in
  `write_validation_outputs()` or elsewhere in `_run_validate_mode()`
  still produces a terminal event (review finding, PR #352: emitting
  `run_end` before those later writes leaves them uncovered by the
  proposal's own terminal-event guarantee)
- Do not change the log's event shape/vocabulary or output filename

## Required Changes

1. Import and use `lcats.utils.run_log` in `run_prefilter.py`.
2. Delete the inline `_log_run_event()` (lines 1005-1027).
3. Use `RunLog`'s context-manager form (not the free function) around the
   call to `run_validation()` **and** the subsequent
   `write_validation_outputs()` call in `_run_validate_mode()`, so
   `run_end` is emitted only after the summary/output files are actually
   published — an exception during those writes must produce
   `run_aborted_unexpected`, not a false `run_end`.
4. Update/extend `run_prefilter_test.py` for the migration, including a
   case that exercises a failure during output writing.

## Non-Goals

- Does not change `validation_run_log.jsonl`'s event names or filename.

## Acceptance Criteria

(see frontmatter)

## Validation

- `scripts/version tools`
- `lrh validate`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`

## Dependencies / Order

Must land after WI-RUNLOG-0078 (the module must exist first).

## Related Workstream and Designs

- Workstream: `project/workstreams/proposed/WS-RUN-LOG.md`
- Design: `project/design/proposals/proposed/lcats-run-log/00_proposal.md`
