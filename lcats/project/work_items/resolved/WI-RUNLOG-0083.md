---
resolution: "Implemented and merged in PR #407 (commit 03f04c7f)."
blocked_reason: null
blocked: false
id: WI-RUNLOG-0083
title: Add run-log support to lcats promote
type: deliverable
status: resolved
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
  - change_copytree_semantics
acceptance:
  - promote_collections() emits run_start with the full collection list, promote_start/promote_end bracketing each _copy_collection call, collection_blocked for gated ones, and run_end/run_aborted_fatal/run_aborted_unexpected
  - Log path is a location outside both --source (data/) and --dest (corpora/, the default) — e.g. a new logs/promote/ directory at the project root, or an explicit --log-dir CLI option — since dest_root / "promote_run.jsonl" as originally scoped would require RunLog to accept a write into corpora/, which WI-RUNLOG-0078 requires it to reject (review finding, PR #352)
  - Both run_aborted_fatal (an account/environment-level failure, if any is defined for this command) and run_aborted_unexpected (an uncaught exception from surveying or _copy_collection) are covered — promote.py has no existing FatalPromoteError class, so an uncaught operational exception must not be silently uncategorized
  - A crash mid-copy leaves a readable partial log showing which collections completed and which was in flight
  - promote.py's existing test coverage is extended to cover the new logging
  - lrh validate and scripts/test pass with 0 errors
required_evidence:
  - lrh_validate
  - test_output
artifacts_expected:
  - lcats/src/lcats/analysis/corpus/promote.py
---

## Summary

Adds an incremental, crash-safe run-event log to `lcats promote`, the
one warranted site with a different risk shape than the rest — a
destructive local `rmtree`-then-`copytree` per collection, not a paid
API loop.

## Problem / Context

`_copy_collection` (`promote.py:267-271`) does `rmtree` then `copytree`
per collection with no record of in-flight/completed/blocked state; a
crash mid-copy currently leaves no trace of which collection was
destroyed or half-written. Proposal Decision 4 table entry.

### Duplication search
- In-repo: No existing run log. Recommendation: Proceed.
- Sibling repos: None identified.
- External libraries: None identified.
- Recommendation: Proceed.

### Demand search
- Work items: None found.
- Proposals: Found: `PROP-LCATS-RUN-LOG` — Implementation Plan step 6
  requests this directly.
- Backlog: No matching entries.
- Recommendation: No action.

## Scope

- Add logging hooks around the loop in `promote_collections`
- Do not change the `rmtree`-then-`copytree` mechanics themselves

## Required Changes

1. Hook `run_start` with the full collection list before the loop
   (`promote.py:326-333`), logging to a destination outside both
   `--source`/`--dest` (both of which resolve to protected roots by
   default — `data/`/`corpora/`) — e.g. a `logs/promote/` directory at
   the project root, or a new `--log-dir` CLI option threaded from
   `promote_cli.py`.
2. Hook `promote_start`/`promote_end` bracketing each `_copy_collection`
   call.
3. Hook `collection_blocked` for mojibake-gated collections.
4. Hook `run_end` on clean completion and `run_aborted_unexpected` for
   an uncaught exception from surveying or `_copy_collection` — `promote.py`
   has no existing `FatalPromoteError`/account-level fatal class, so
   `run_aborted_fatal` alone would leave ordinary operational failures
   (e.g. a permissions error mid-copy) unclassified (review finding,
   PR #352).

## Non-Goals

- Does not change the destructive `rmtree`-before-`copytree` sequencing
  itself — that's a separate, larger safety question not in scope here.

## Acceptance Criteria

(see frontmatter)

## Validation

- `scripts/version tools`
- `lrh validate`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`

## Dependencies / Order

Must land after WI-RUNLOG-0078.

## Related Workstream and Designs

- Workstream: `project/workstreams/proposed/WS-RUN-LOG.md`
- Design: `project/design/proposals/proposed/lcats-run-log/00_proposal.md`
