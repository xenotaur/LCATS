---
resolution: null
blocked_reason: null
blocked: false
id: WI-ASSESS-0050
title: Fix assess_story's error-path title fallback
type: deliverable
status: proposed
priority: low
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
  - create_pr
  - run_tests
forbidden_actions:
  - force_push
  - delete_branch
acceptance:
  - "assess_story's fallback title (used when run_preflight raises) is derived from file_path.parent.name, not file_path.stem"
  - "lrh validate reports 0 errors"
required_evidence:
  - manual_review
  - test_output
  - lrh_validate
artifacts_expected:
  - lcats/src/lcats/analysis/corpus/assess.py
  - lcats/tests/analysis_tests/assess_test.py
---

# Work Item: Fix assess_story's error-path title fallback

## Summary

Fix `assess_story`'s pre-initialized fallback `title`, which is derived
from `file_path.stem` (always the literal string `"story"` under the
bucket layout) instead of `file_path.parent.name` (the real story slug),
so a `run_preflight` failure's error record identifies which story
actually failed.

## Problem / Context

Surfaced 2026-08-02 while scoping a different follow-up, then verified
directly against the code before concluding anything — an initial
misreading looked like a much bigger bug before reading the whole
function. `lcats/src/lcats/analysis/corpus/assess.py`'s `assess_story`
(line 294) pre-initializes `title = file_path.stem` before calling
`run_preflight(file_path)` (which correctly derives the title via the
already-fixed `infer_story_title`). In the success path, `title` is
immediately reassigned from `run_preflight`'s return value, so **the
real `lcats assess` CLI is not broadly broken** — titles are correct in
normal operation. The only surviving gap is the `except Exception`
fallback (line 364): if `run_preflight` raises (a genuine
file-read/parse error unrelated to identity), the resulting error
`AssessmentResult`'s `title` field falls back to the stale
`file_path.stem` value — literally `"story"` for every bucket file —
instead of the real story slug, making it harder to tell from the
output alone which story actually failed. This is cosmetic, not a data
or correctness bug: the error record already carries `file_path` and
`error`, so the information isn't lost, just harder to scan.

### Duplication search
- In-repo: No existing implementation found. `assess_story`'s error-path
  behavior already has dedicated test coverage
  (`TestAssessStoryErrorPaths` in `tests/analysis_tests/assess_test.py`)
  but no assertion on the fallback `title` value.
- Sibling repos: None identified.
- External libraries: None identified — internal one-line fix.
- Recommendation: Proceed.

### Demand search
- Work items: None found specifically covering this gap.
- Proposals: None found.
- Backlog: Found: "`assess_story`'s error-path title fallback uses the
  stem-collision pattern" in `lcats/project/design/backlog.md`. This
  work item is created specifically to resolve that entry.
- Recommendation: Offer to remove/mark-resolved the matching
  `backlog.md` entry once this work item's PR is confirmed (not
  auto-closed).

## Scope

- Fix the fallback `title` initialization in `assess_story` to use the
  same identity convention (`file_path.parent.name`) as the rest of the
  bucket-layout codebase.
- Add a regression test asserting the fallback title on a
  `run_preflight` exception.

## Required Changes

1. In `lcats/src/lcats/analysis/corpus/assess.py:294`, change
   `title = file_path.stem` to `title = file_path.parent.name`.
2. In `lcats/tests/analysis_tests/assess_test.py`'s
   `TestAssessStoryErrorPaths` class, extend
   `test_preflight_error_captured` (or add a new test) to assert
   `result.title` equals the expected directory-slug value derived from
   the existing `_FILE = pathlib.Path("/fake/path/story.json")` fixture
   (`"path"`), confirming the fallback no longer returns `"story"`.

## Non-Goals

- Does not touch the success-path title derivation (`run_preflight` /
  `infer_story_title`), which is already correct.
- Does not touch `compare_results.py`'s similar fallback pattern, if any
  — out of scope, a separate item if it turns out to exist.

## Acceptance Criteria

- `assess_story`'s fallback `title` (used only when `run_preflight`
  raises) is derived from `file_path.parent.name`, not `file_path.stem`.
- A new or extended regression test proves the fallback title is the
  real story slug, not the literal string `"story"`.
- `lrh validate` reports 0 errors.

## Validation

- `scripts/version tools`
- `lrh validate`
- `scripts/test` (repository's declared source-of-truth full-suite
  command, per `AGENTS.md`)
- `python -m pytest tests/analysis_tests/assess_test.py` (targeted
  re-run during development)

## Risk Notes

- None — this is a single-line, error-path-only change with no effect
  on the success path or on any persisted data.
