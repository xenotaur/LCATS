---
resolution: null
blocked_reason: null
blocked: false
id: WI-PROCESSING-0057
title: Guard unhandled pathlib.Path.resolve() failures in batch processing and survey row-building
type: deliverable
status: proposed
priority: medium
owner: unassigned
contributors: []
assigned_agents: []
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap: []
related_workstreams: []
related_design:
  - lcats/project/design/backlog.md
depends_on: []
blocked_by: []
expected_actions:
  - edit_file
  - create_file
  - create_pr
  - run_tests
forbidden_actions:
  - force_push
  - delete_branch
  - modify_promote_validate_distinct_roots
  - modify_checkpoint_protected_root_guards
  - modify_paths_find_pyproject_root
acceptance:
  - "output.story_dir_value catches an OSError from resolve() and returns \"\" instead of propagating it"
  - "processing.process_file catches an OSError from any of its three initial resolve() calls and returns a status=\"error\" result instead of crashing"
  - "processing.process_files no longer eagerly resolves every input path before its per-file loop starts -- one file's unresolvable path no longer aborts the whole batch before any processing begins"
  - "New regression tests prove all three fixes: a resolve() failure produces a graceful result, not an unhandled exception, and a batch with one bad file still processes the rest"
  - "lrh validate reports 0 errors"
required_evidence:
  - manual_review
  - test_output
  - lrh_validate
artifacts_expected:
  - lcats/src/lcats/analysis/corpus/output.py
  - lcats/src/lcats/analysis/corpus/processing.py
  - lcats/tests/analysis_tests/output_test.py
  - lcats/tests/analysis_tests/processing_test.py
---

# Work Item: Guard unhandled pathlib.Path.resolve() failures in batch processing and survey row-building

## Summary

Guard two real, unhandled `pathlib.Path.resolve()` failure paths found
during an audit of all 14 unguarded `.resolve()` call sites in
`lcats/src/lcats/`: `output.story_dir_value` (the exact pattern
`assess_story`'s fix in `WI-ASSESS-0050` was modeled on, but never
itself fixed) and `processing.py`'s batch file-processing functions,
where an eager resolve step defeats the module's own carefully-designed
per-file fault isolation.

## Problem / Context

Surfaced 2026-08-07 during `WI-ASSESS-0050`'s review: `assess_story`'s
error-path title fallback added an unguarded `file_path.resolve()`
call, which a follow-on self-review finding showed could crash the
whole call on a filesystem error (broken symlink loop, permission
error) since it ran before the function's own `try/except`. Fixed
locally in that WI, with a backlog item to audit the same pattern
elsewhere. That audit is complete; this work item resolves the two
sites it found to be real bugs (see the backlog entry this WI resolves
for the full audit results, including the 10 sites confirmed correct
as-is).

**Site 1 — `lcats/src/lcats/analysis/corpus/output.py:113`,
`story_dir_value`:** the exact same unguarded pattern
`assess_story`'s fix was modeled on (its own docstring says so), but
never itself received the guard. Confirmed reachable from an unguarded
per-file loop: `cli.py`'s `run_survey` (`cli.py:327-330`) calls
`survey_file` per file with **no per-file exception handling at all**
-- `story_dir_value` is called (via `parse_special_character_rows`,
`finding_to_row`, `clean_row`) for every survey row. One resolve()
failure anywhere in a `lcats survey` run over potentially thousands of
files would crash the entire run.

**Site 2 — `lcats/src/lcats/analysis/corpus/processing.py`'s
`process_files`/`process_file`:** `process_file` (lines 40-42) resolves
three paths (`input_path`, `corpora_root_path`, `job_dir_path`) before
its own `try/except Exception` (starting line 62) -- a resolve()
failure here crashes the function instead of returning the
`status: "error"` result its own design contract promises. Worse,
`process_files`'s own per-file loop (`process_files:121-123`) eagerly
resolves *every* input path in a list comprehension **before the
per-file loop even starts** (`process_files:132`) -- this runs ahead of
`process_file`'s per-file error handling entirely, so one unresolvable
path anywhere in a batch aborts processing of every file, including
ones that would have succeeded. This directly undermines the fault
isolation `process_file`'s own `except Exception` block
(lines 89-98) exists to provide.

### Duplication search
- In-repo: No existing implementation found. `output_test.py` has
  `TestStoryDirValue` coverage but no resolve-failure test.
  `processing.py` has no dedicated test file at all today.
- Sibling repos: None identified.
- External libraries: None identified -- internal robustness fix.
- Recommendation: Proceed.

### Demand search
- Work items: None found specifically covering this gap.
- Proposals: None found.
- Backlog: Found: "Unguarded `pathlib.Path.resolve()` calls could crash
  callers on filesystem errors" in `lcats/project/design/backlog.md`.
  This work item resolves the two real-bug sites that entry's audit
  identified.
- Recommendation: Offer to remove/mark-resolved the matching
  `backlog.md` entry once this work item's PR is confirmed (not
  auto-closed).

## Scope

- Guard `output.story_dir_value`'s `resolve()` call, mirroring
  `assess_story`'s own established fix.
- Guard `processing.process_file`'s three initial `resolve()` calls so
  a failure produces the function's normal `status: "error"` result
  instead of crashing.
- Stop `processing.process_files` from eagerly resolving every input
  path before its per-file loop starts, so `process_file`'s own
  (now-guarded) per-file fault isolation actually applies to path
  resolution failures too.
- Add regression tests for all three fixes.

## Required Changes

1. In `lcats/src/lcats/analysis/corpus/output.py`'s `story_dir_value`,
   wrap the `return file_path.resolve().parent.name` line in
   `try/except OSError: return ""`, matching `assess_story`'s own
   established guard.
2. In `lcats/src/lcats/analysis/corpus/processing.py`'s `process_file`,
   wrap the three initial `resolve()` calls
   (`input_path`/`corpora_root_path`/`job_dir_path`, lines 40-42) in a
   `try/except OSError` that returns immediately with the function's
   normal error shape (`{"input": in_path, "output": None, "status":
   "error", "error": "<type>: <message>"}`), before `rel`/`out_path`
   are computed (since both depend on successful resolution).
3. In `lcats/src/lcats/analysis/corpus/processing.py`'s `process_files`,
   change the per-file list comprehension building `normalized_files`
   (lines 121-123) to only call `.expanduser()`, not `.resolve()` --
   real resolution now happens per-item inside `process_file` (per
   Required Change 2), so a bad path for one file no longer prevents
   the loop from starting or processing the remaining files.
4. Add a new test to `lcats/tests/analysis_tests/output_test.py`'s
   `TestStoryDirValue` class mocking `pathlib.Path.resolve` to raise
   `OSError`, asserting `story_dir_value` returns `""` instead of
   propagating the exception.
5. Create `lcats/tests/analysis_tests/processing_test.py` (new file,
   following this repo's existing `unittest.TestCase` conventions)
   asserting: `process_file` returns a `status: "error"` result (not an
   unhandled exception) when `resolve()` raises for one of its three
   path arguments; `process_files` given a batch of files where one
   file's path fails to resolve still processes the remaining files
   successfully (the batch-level fault isolation this fix restores).

## Non-Goals

- Does not touch `promote.py`'s `_validate_distinct_roots`,
  `checkpoint.py`'s `_protected_roots`/`_check_working_root_allowed`,
  or `utils/paths.py`'s `find_pyproject_root` -- all four are
  pre-destructive or bootstrap safety checks where crashing on an
  unresolvable path is the correct, intentional behavior, confirmed
  during this work item's own audit (see the backlog entry this WI
  resolves for the full reasoning).
- Does not change `process_files`' or `process_file`'s output format,
  CLI arguments, or any other error-handling behavior beyond the
  specific `resolve()` guard.
- Does not audit or change any `.resolve()` call site not explicitly
  named above.

## Acceptance Criteria

- `output.story_dir_value` catches an `OSError` from `resolve()` and
  returns `""` instead of propagating it.
- `processing.process_file` catches an `OSError` from any of its three
  initial `resolve()` calls and returns a `status: "error"` result
  instead of crashing.
- `processing.process_files` no longer eagerly resolves every input
  path before its per-file loop starts.
- New regression tests prove all three fixes.
- `lrh validate` reports 0 errors.

## Validation

- `scripts/version tools`
- `lrh validate`
- `scripts/test` (repository's declared source-of-truth full-suite
  command, per `AGENTS.md`)
- `python -m pytest tests/analysis_tests/output_test.py
  tests/analysis_tests/processing_test.py` (targeted re-run during
  development)

## Risk Notes

- `process_files`' `normalized_files.sort()` (when `sort=True`, the
  default) will now sort `.expanduser()`-only paths instead of fully
  resolved absolute paths. For inputs that are already absolute (the
  common case, since callers typically pass paths from
  `discovery.find_corpus_stories`/`find_json_files`), sort order is
  unaffected; for relative or `~`-prefixed inputs, sort order could
  differ slightly from before. This is a cosmetic ordering change, not
  a correctness issue -- no caller is known to depend on a specific
  resolved-path sort order.
- `process_file`'s new early-return error shape uses `"output": None`
  (since `out_path` cannot be computed without a successfully resolved
  `job_dir_path`), unlike the existing error path's `"output": out_path`.
  Callers consuming `process_files`' `errors`/`results` lists should
  tolerate `None` for `output` on this specific failure mode.
