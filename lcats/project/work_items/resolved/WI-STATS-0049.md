---
resolution: "Implemented and merged via https://github.com/xenotaur/LCATS/pull/238 (squash commit 1067567eb674f365d2fb6e2f2c420c0f2f5e711a). Two real bugs found in review (Codex) were fixed in the same PR: _is_leaf_story_bucket needed ignore_dir_names too, and ignore_dir_names needed to be materialized once (not re-derived from a possibly-exhausted iterable) across recursion."
blocked_reason: null
blocked: false
id: WI-STATS-0049
title: Fix lcats stats' broad story-file selector
type: deliverable
status: resolved
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
  - "A cache/ subdirectory is still excluded from lcats stats output, matching the pre-existing find_corpus_stories(ignore_dir_names=(\"cache\",)) behavior"
  - "lrh validate reports 0 errors"
required_evidence:
  - manual_review
  - test_output
  - lrh_validate
artifacts_expected:
  - lcats/src/lcats/analysis/corpus/cli.py
  - lcats/src/lcats/analysis/corpus/discovery.py
  - lcats/tests/analysis_tests/corpus_cli_test.py
  - lcats/tests/analysis_tests/discovery_test.py
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
canonical-presence question" pattern documented in
[`PROP-LCATS-STORY-BUCKET-LAYOUT`](../../design/proposals/adopted/lcats-story-bucket-layout/00_proposal.md)'s
Decision 3, and confirmed at least four other times across the
`WS-STORY-BUCKET-LAYOUT` follow-up work (`WI-EXPERIMENTS-0046`,
`WI-EXPERIMENTS-0048`): a broad selector that is legitimately fine for
corpus-wide listing becomes wrong once its output is used to answer "is
this a real story."

**Cache-directory exclusion gap (found during this work item's own
creation-PR review, Codex P2, 2026-08-06):** the original draft assumed
`discovery.find_json_files`'s lack of an `ignore_dir_names` parameter
was a non-issue because no `cache/` directory exists inside `corpora/`
or `data/` in this repo today — but that check was scoped too narrowly.
`run_stats`'s `directories` argument accepts arbitrary paths, not just
`corpora/`/`data/`, and `cache/` directories do exist elsewhere in this
very checkout (`lcats/cache/`, and the repo root's own `cache/`) — either
would be a plausible (if unusual) target for a general-purpose CLI tool,
and a user pointing `lcats stats` at an external corpus tree has no
guarantee of a `cache/`-free layout either. The existing code's
`ignore_dir_names=("cache",)` is real, load-bearing protection that the
naive selector swap would silently drop. Folded into scope below: extend
`discovery.find_json_files` with an optional `ignore_dir_names`
parameter (matching `find_corpus_stories`'s own parameter shape) so
`run_stats` can preserve the exclusion.

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

- Extend `discovery.find_json_files` with an opt-in `ignore_dir_names`
  parameter, matching `find_corpus_stories`'s own parameter shape.
- Switch `run_stats`'s file discovery from `discovery.find_corpus_stories`
  to `discovery.find_json_files`, passing `ignore_dir_names=("cache",)`
  to preserve the existing cache-exclusion behavior.
- Add regression tests proving both sidecar files and `cache/`-directory
  contents are excluded from stats output.

## Required Changes

1. In `lcats/src/lcats/analysis/corpus/discovery.py`, add an
   `ignore_dir_names: Iterable[str] = ()` parameter to `find_json_files`,
   threaded through to `_walk_canonical_story_files` (also given the
   same parameter). Before recursing into a subdirectory, skip it if its
   name case-folds to a match in `ignore_dir_names` (matching
   `find_corpus_stories`'s own `casefold()` comparison). Default to an
   empty tuple so every existing caller (`survey`, `assess`) is
   unaffected unless it opts in.
2. In `lcats/src/lcats/analysis/corpus/cli.py`'s `run_stats`, replace the
   per-directory loop building `files` via
   `discovery.find_corpus_stories(directory, ignore_dir_names=("cache",),
   sort=True)` with a single call to
   `discovery.find_json_files(args.directories, ignore_dir_names=("cache",))`
   (it already accepts an iterable of directories/paths and handles both
   directory scanning and direct-file arguments, subsuming the existing
   loop's two branches).
3. Add a new test class to `lcats/tests/analysis_tests/discovery_test.py`
   asserting `find_json_files`'s new `ignore_dir_names` parameter prunes
   a matching subdirectory (case-insensitive) and leaves other traversal
   behavior unchanged when omitted.
4. Add a new test class to `lcats/tests/analysis_tests/corpus_cli_test.py`
   asserting: a bucket sidecar JSON file alongside a real `story.json` is
   never included in `run_stats`'s file selection; a story-shaped
   directory nested under `cache/` is excluded; real bucket-layout
   stories elsewhere are still found correctly.

## Non-Goals

- Does not change `run_stats`'s output format, CLI arguments, or
  `compute_corpus_stats`'s own logic.
- Does not change `survey`'s or `assess`'s existing `find_json_files`
  calls to also pass `ignore_dir_names` — out of scope here; the new
  parameter defaults to a no-op so their behavior is unchanged, and
  whether they should adopt it is a separate question.

## Acceptance Criteria

- `run_stats` uses `discovery.find_json_files`, not
  `discovery.find_corpus_stories`, to select story files.
- A bucket sidecar JSON file is never included in `lcats stats` output.
- A `cache/` subdirectory's contents are still excluded from `lcats
  stats` output, matching the pre-existing behavior.
- New regression tests prove the sidecar exclusion, the cache exclusion,
  and that real bucket-layout stories are still found.
- `lrh validate` reports 0 errors.

## Validation

- `scripts/version tools`
- `lrh validate`
- `scripts/test` (repository's declared source-of-truth full-suite
  command, per `AGENTS.md`)
- `python -m pytest tests/analysis_tests/discovery_test.py
  tests/analysis_tests/corpus_cli_test.py` (targeted re-run during
  development)

## Risk Notes

- `find_json_files` returns an iterator; `run_stats` currently builds a
  list via `.extend(...)` inside a loop — the replacement should collect
  the iterator into a list once, since `compute_corpus_stats` iterates
  `files` and the existing code assumes a concrete list.
- The new `ignore_dir_names` parameter changes `_walk_canonical_story_files`'s
  signature; verify no other internal caller depends on its exact
  current signature before landing.
