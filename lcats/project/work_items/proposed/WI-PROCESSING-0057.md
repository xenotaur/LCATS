---
resolution: null
blocked_reason: null
blocked: false
id: WI-PROCESSING-0057
title: Guard unhandled pathlib.Path.resolve() failures in assessment, batch processing, and survey row-building
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
  - "assess_story's existing resolve() guard, output.story_dir_value's new guard, and processing.process_file's new guard all catch both OSError and RuntimeError (Path.resolve() raises RuntimeError for a symlink loop on Python <3.13, OSError on 3.13+; this repo declares python_requires >=3.10)"
  - "output.story_dir_value catches a resolve() failure and returns \"\" instead of propagating it"
  - "processing.process_file catches a resolve() failure from any of its three initial resolve() calls and returns a status=\"error\" result instead of crashing"
  - "processing.process_files no longer eagerly resolves every input path before its per-file loop starts -- one file's unresolvable path no longer aborts the whole batch before any processing begins"
  - "New regression tests prove all fixes across both exception types on the actual running interpreter"
  - "project/design/backlog.md's audit entry records the actual per-site reasoning for all 15 originally-identified call sites, not a pointer to non-existent evidence"
  - "lrh validate reports 0 errors"
required_evidence:
  - manual_review
  - test_output
  - lrh_validate
artifacts_expected:
  - lcats/src/lcats/analysis/corpus/assess.py
  - lcats/src/lcats/analysis/corpus/output.py
  - lcats/src/lcats/analysis/corpus/processing.py
  - lcats/tests/analysis_tests/assess_test.py
  - lcats/tests/analysis_tests/output_test.py
  - lcats/tests/analysis_tests/processing_test.py
---

# Work Item: Guard unhandled pathlib.Path.resolve() failures in assessment, batch processing, and survey row-building

## Summary

Guard three real, unhandled `pathlib.Path.resolve()` failure paths
found during an audit of all 15 unguarded `.resolve()` call sites in
`lcats/src/lcats/`: `assess.assess_story`'s already-merged guard (from
`WI-ASSESS-0050`), `output.story_dir_value` (the exact pattern that
guard was modeled on, but never itself fixed), and `processing.py`'s
batch file-processing functions, where an eager resolve step defeats
the module's own carefully-designed per-file fault isolation.

## Problem / Context

Surfaced 2026-08-07 during `WI-ASSESS-0050`'s review: `assess_story`'s
error-path title fallback added an `file_path.resolve()` call guarded
by `except OSError`, since a follow-on self-review finding showed an
unguarded resolve() call could crash the whole call on a filesystem
error (broken symlink loop, permission error) -- it ran before the
function's own `try/except`. That fix landed with a backlog item to
audit the same unguarded pattern elsewhere.

**Review finding on this work item's own creation PR (Codex,
2026-08-08), verified directly rather than trusted:** the `except
OSError` guard itself is incomplete. `pathlib.Path.resolve()` raises
`RuntimeError`, not `OSError`, for a symlink loop on Python 3.10-3.12
(confirmed directly by reproducing a symlink loop and calling
`.resolve()` on Python 3.11.8, the interpreter this repo's own test
suite runs under) -- only Python 3.13+ changed this to `OSError`. This
repo's `pyproject.toml` declares `python_requires = ">=3.10"`, so an
`except OSError`-only guard leaves the *original* motivating failure
(a symlink loop) unhandled on every currently-supported Python version
except the newest. This means `assess_story`'s own already-merged fix
has the same latent gap being guarded against here -- folded into this
work item's scope as a third site, since the guard pattern this WI
copies elsewhere would otherwise propagate the same incomplete fix.

**Second review finding, also verified directly:** this WI's own text
claimed the matching `backlog.md` entry recorded "the 10 sites
confirmed correct as-is," but that entry (as of this WI's first draft)
only says the audit had not yet been done and prescribes it as future
work -- the referenced evidence didn't exist. Fixed by writing the
actual audit results into that entry as part of this WI (see Required
Changes below), re-verifying each site directly rather than restating
the original unverified claim.

**Site 1 — `lcats/src/lcats/analysis/corpus/assess.py:350`,
`assess_story`'s existing guard:** `except OSError` alone, landed via
`WI-ASSESS-0050`. Per the review finding above, this does not catch the
`RuntimeError` `resolve()` actually raises for a symlink loop on
Python 3.10-3.12. Needs `except (OSError, RuntimeError)`.

**Site 2 — `lcats/src/lcats/analysis/corpus/output.py:113`,
`story_dir_value`:** the exact same unguarded pattern
`assess_story`'s fix was modeled on (its own docstring says so), but
never itself received any guard. Confirmed reachable from an unguarded
per-file loop: `cli.py`'s `run_survey` (`cli.py:327-330`) calls
`survey_file` per file with **no per-file exception handling at all**
-- `story_dir_value` is called (via `parse_special_character_rows`,
`finding_to_row`, `clean_row`) for every survey row. One resolve()
failure anywhere in a `lcats survey` run over potentially thousands of
files would crash the entire run. Needs `except (OSError, RuntimeError)`,
same as Site 1.

**Site 3 — `lcats/src/lcats/analysis/corpus/processing.py`'s
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
(lines 89-98) exists to provide. Both fixes need
`except (OSError, RuntimeError)`.

**Distinguished from `processing.py`'s other two `.resolve()` calls,
confirmed during this same audit pass and left alone (see Non-Goals):**
`process_files` (lines 115-116, `corpora_root_path`/`output_root_path`)
and `process_corpora` (line 184, `corpora_root_path`) each resolve once
per batch *before* the per-file loop even exists, not once per file --
a failure there means the whole call's configuration is bad, not that
one file among many is bad. This is the same category as the
pre-destructive/bootstrap checks in the Non-Goals below (fail fast on
bad configuration is the correct behavior), not the per-item fault-
isolation problem Sites 2-3 fix.

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
  This work item resolves the three real-bug sites the audit
  identified (writing the actual audit results into that entry, since
  they were not previously recorded there -- see Required Changes).
- Recommendation: Offer to remove/mark-resolved the matching
  `backlog.md` entry once this work item's PR is confirmed (not
  auto-closed).

## Scope

- Widen `assess_story`'s existing guard (from `WI-ASSESS-0050`) and add
  matching guards to `output.story_dir_value` and
  `processing.process_file` to catch both `OSError` and `RuntimeError`.
- Stop `processing.process_files` from eagerly resolving every input
  path before its per-file loop starts, so `process_file`'s own
  (now-guarded) per-file fault isolation actually applies to path
  resolution failures too.
- Record the actual audit results (all 15 sites, not just the 3 fixed
  here) in `project/design/backlog.md`'s entry, replacing the
  unverified "10 sites confirmed correct" claim this WI's own first
  draft made without evidence.
- Add regression tests for all fixes, covering both exception types.

## Required Changes

1. In `lcats/src/lcats/analysis/corpus/assess.py`'s `assess_story`,
   widen the existing `except OSError:` (line 351, from
   `WI-ASSESS-0050`) to `except (OSError, RuntimeError):`.
2. In `lcats/src/lcats/analysis/corpus/output.py`'s `story_dir_value`,
   wrap the `return file_path.resolve().parent.name` line in
   `try/except (OSError, RuntimeError): return ""`.
3. In `lcats/src/lcats/analysis/corpus/processing.py`'s `process_file`,
   wrap the three initial `resolve()` calls
   (`input_path`/`corpora_root_path`/`job_dir_path`, lines 40-42) in a
   `try/except (OSError, RuntimeError)` that returns immediately with
   the function's normal error shape (`{"input": in_path, "output":
   None, "status": "error", "error": "<type>: <message>"}`), before
   `rel`/`out_path` are computed (since both depend on successful
   resolution).
4. In `lcats/src/lcats/analysis/corpus/processing.py`'s `process_files`,
   change the per-file list comprehension building `normalized_files`
   (lines 121-123) to only call `.expanduser()`, not `.resolve()` --
   real resolution now happens per-item inside `process_file` (per
   Required Change 3), so a bad path for one file no longer prevents
   the loop from starting or processing the remaining files.
5. Add a new test to `lcats/tests/analysis_tests/assess_test.py`'s
   error-path test class mocking `pathlib.Path.resolve` to raise
   `RuntimeError` (not just the existing `OSError` regression test from
   `WI-ASSESS-0050`), asserting the fallback title is still `""` rather
   than propagating.
6. Add a new test to `lcats/tests/analysis_tests/output_test.py`'s
   `TestStoryDirValue` class mocking `pathlib.Path.resolve` to raise
   both `OSError` and `RuntimeError` (two tests), asserting
   `story_dir_value` returns `""` in both cases instead of propagating.
7. Create `lcats/tests/analysis_tests/processing_test.py` (new file,
   following this repo's existing `unittest.TestCase` conventions)
   asserting: `process_file` returns a `status: "error"` result (not an
   unhandled exception) when `resolve()` raises either `OSError` or
   `RuntimeError` for one of its three path arguments; `process_files`
   given a batch of files where one file's path fails to resolve still
   processes the remaining files successfully (the batch-level fault
   isolation this fix restores).
8. Rewrite `project/design/backlog.md`'s "Unguarded
   `pathlib.Path.resolve()` calls..." entry to record the actual,
   re-verified per-site audit conclusions for all 15 originally-found
   call sites: the 3 fixed here (Sites 1-3 above), the 2 batch-level
   `processing.py` resolves left alone (Scope's "Distinguished from"
   note above), and the 10 pre-destructive/bootstrap sites in
   `promote.py`/`checkpoint.py`/`utils/paths.py` (Non-Goals below) --
   replacing the prior draft's claim that this reasoning existed there
   already, which review found to be false.

## Non-Goals

- Does not touch `promote.py`'s `_validate_distinct_roots` (2 calls),
  `checkpoint.py`'s `_protected_roots`/`_check_working_root_allowed`
  (3 calls), or `utils/paths.py`'s `find_pyproject_root` (1 call) --
  6 call sites total --
  all are pre-destructive or bootstrap safety checks where crashing on
  an unresolvable path is the correct, intentional behavior: each
  operates on a root path that must be valid for the surrounding
  operation to be safe at all (write-target validation, protected-root
  overwrite guards, project-root discovery), so failing fast rather
  than silently degrading is the right behavior, confirmed by reading
  each call site's surrounding function during this work item's audit.
- Does not touch `processing.py`'s two batch-level (once-per-call, not
  once-per-file) `resolve()` calls in `process_files` (lines 115-116)
  or `process_corpora` (line 184) -- see the Problem/Context
  "Distinguished from" note above; these fail fast on bad batch-level
  configuration, the same category as the bullet above, not the
  per-item fault-isolation problem Sites 2-3 fix.
- Does not change `process_files`' or `process_file`'s output format,
  CLI arguments, or any other error-handling behavior beyond the
  specific `resolve()` guard.
- Does not audit or change any `.resolve()` call site not explicitly
  named above. The 15 call sites found in the original audit are now
  all accounted for: 6 fixed (`assess.py` ×1, `output.py` ×1,
  `processing.py`'s `process_file` ×3 and `process_files`' per-file
  resolve ×1), 3 left alone as batch-level configuration
  (`processing.py`'s `process_files` ×2 and `process_corpora` ×1), and
  6 left alone as pre-destructive/bootstrap safety checks (`promote.py`
  ×2, `checkpoint.py` ×3, `paths.py` ×1) -- 6 + 3 + 6 = 15, matching
  `backlog.md`'s corrected entry exactly.

## Acceptance Criteria

- `assess_story`'s existing guard, `output.story_dir_value`'s new
  guard, and `processing.process_file`'s new guard all catch both
  `OSError` and `RuntimeError` from `resolve()`.
- `output.story_dir_value` catches a `resolve()` failure and returns
  `""` instead of propagating it.
- `processing.process_file` catches a `resolve()` failure from any of
  its three initial `resolve()` calls and returns a `status: "error"`
  result instead of crashing.
- `processing.process_files` no longer eagerly resolves every input
  path before its per-file loop starts.
- New regression tests prove all fixes across both exception types.
- `project/design/backlog.md`'s audit entry records real, verified
  per-site reasoning for all 15 originally-identified call sites.
- `lrh validate` reports 0 errors.

## Validation

- `scripts/version tools`
- `lrh validate`
- `scripts/test` (repository's declared source-of-truth full-suite
  command, per `AGENTS.md`)
- `python -m pytest tests/analysis_tests/assess_test.py
  tests/analysis_tests/output_test.py
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
