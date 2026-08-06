---
resolution: null
blocked_reason: null
blocked: false
id: WI-STATS-0049
title: Fix lcats stats' broad story-file selector
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
  - create_pr
  - run_tests
forbidden_actions:
  - force_push
  - delete_branch
acceptance:
  - "run_stats uses discovery.find_json_files, not discovery.find_corpus_stories, to select story files"
  - "A bucket sidecar JSON file (e.g. analysis.json) is never included in lcats stats output"
  - "lrh validate reports 0 errors"
required_evidence:
  - manual_review
  - test_output
  - lrh_validate
artifacts_expected:
  - lcats/src/lcats/analysis/corpus/cli.py
  - lcats/tests/analysis_tests/corpus_cli_test.py
---

# Work Item: Fix lcats stats' broad story-file selector

## Summary

Fix `lcats stats`' file selection, which currently uses the broad
recursive `discovery.find_corpus_stories` instead of the canonical,
sidecar-excluding `discovery.find_json_files` selector that `lcats
survey` and `lcats assess` both already use.

## Problem / Context

Surfaced during PR #209's review, confirmed 2026-08-02 and re-confirmed
directly against current code before drafting this work item:
`lcats/src/lcats/analysis/corpus/cli.py`'s `run_stats` (line 376) loops
over `args.directories` and, for each directory, calls
`discovery.find_corpus_stories(directory, ignore_dir_names=("cache",),
sort=True)` — the broad recursive JSON finder. This means `lcats stats`
can silently include bucket sidecar files (`analysis.json`, `scenes.json`,
etc.) as if they were independent stories, inflating or corrupting
story-level statistics. This is exactly the "wrong tool for the
canonical-presence question" pattern documented in the
`project_story_bucket_proposal_status` memory and confirmed at least
four other times across the `WS-STORY-BUCKET-LAYOUT` follow-up work
(`WI-EXPERIMENTS-0046`, `WI-EXPERIMENTS-0048`): a broad selector that is
legitimately fine for corpus-wide listing becomes wrong once its output
is used to answer "is this a real story."

**Risk checked before drafting:** `discovery.find_json_files` has no
`ignore_dir_names` parameter, unlike `find_corpus_stories`, so a `cache/`
subdirectory would no longer be explicitly skipped during traversal.
Verified directly: no `cache/` directory currently exists inside
`corpora/` or `data/` in this repo, and neither `lcats survey` nor
`lcats assess` (both already on `find_json_files`) special-cases
`cache/` either — so this is a consistency fix bringing `stats` in line
with the established selector, not a newly introduced gap.

### Duplication search
- In-repo: No existing implementation found. `run_stats` has no
  dedicated test file today (`tests/cli_test.py` only mocks it at the
  dispatch level).
- Sibling repos: None identified.
- External libraries: None identified — internal selector fix.
- Recommendation: Proceed.

### Demand search
- Work items: None found specifically covering this gap.
- Proposals: None found.
- Backlog: Found: "`lcats stats` uses the wrong (broad) story-file
  selector" in `lcats/project/design/backlog.md`. This work item is
  created specifically to resolve that entry.
- Recommendation: Offer to remove/mark-resolved the matching
  `backlog.md` entry once this work item's PR is confirmed (not
  auto-closed).

## Scope

- Switch `run_stats`'s file discovery from `discovery.find_corpus_stories`
  to `discovery.find_json_files`.
- Add a regression test proving sidecar files are excluded from stats
  output.

## Required Changes

1. In `lcats/src/lcats/analysis/corpus/cli.py`'s `run_stats`, replace the
   per-directory loop building `files` via
   `discovery.find_corpus_stories(directory, ignore_dir_names=("cache",),
   sort=True)` with a single call to
   `discovery.find_json_files(args.directories)` (it already accepts
   an iterable of directories/paths and handles both directory scanning
   and direct-file arguments, subsuming the existing loop's two branches).
2. Add a new test class to `lcats/tests/analysis_tests/corpus_cli_test.py`
   asserting: a bucket sidecar JSON file alongside a real `story.json` is
   never included in `run_stats`'s file selection; real bucket-layout
   stories are still found correctly.

## Non-Goals

- Does not change `run_stats`'s output format, CLI arguments, or
  `compute_corpus_stats`'s own logic.
- Does not add back `cache/`-directory exclusion — not needed today, and
  adding it here would make `stats` inconsistent with `survey`/`assess`
  rather than consistent with them.

## Acceptance Criteria

- `run_stats` uses `discovery.find_json_files`, not
  `discovery.find_corpus_stories`, to select story files.
- A bucket sidecar JSON file is never included in `lcats stats` output.
- A new regression test proves both the sidecar-exclusion fix and that
  real bucket-layout stories are still found.
- `lrh validate` reports 0 errors.

## Validation

- `scripts/version tools`
- `lrh validate`
- `python -m pytest tests/analysis_tests/corpus_cli_test.py`
- `python -m pytest tests/`

## Risk Notes

- See the cache-directory risk discussed above (Problem/Context) —
  checked and confirmed non-issue for the current repo state.
- `find_json_files` returns an iterator; `run_stats` currently builds a
  list via `.extend(...)` inside a loop — the replacement should collect
  the iterator into a list once, since `compute_corpus_stats` iterates
  `files` and the existing code assumes a concrete list.
