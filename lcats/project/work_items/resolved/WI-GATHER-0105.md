---
resolution: "Implemented and merged in PR #426 (commit c74fd3f7)."
blocked_reason: null
blocked: false
id: WI-GATHER-0105
title: Add a dedicated run-log wrapper to mass_quantities/gatherer.py
type: deliverable
status: resolved
owner: unassigned
contributors: []
assigned_agents: []
related_focus: []
related_roadmap: []
related_workstreams: []
related_design:
  - lcats/project/design/proposals/proposed/lcats-run-log/00_proposal.md
  - lcats/project/design/gatherer-reconciliation-audit.md
  - lcats/project/work_items/resolved/WI-GATHER-0101.md
  - lcats/project/work_items/resolved/WI-RUNLOG-0080.md
depends_on:
  - WI-RUNLOG-0078
blocked_by: []
expected_actions:
  - edit_file
  - run_tests
forbidden_actions:
  - force_push
  - delete_branch
acceptance:
  - mass_quantities/gatherer.py's gather_stories() function itself opens the RunLog scope (not a wrapper around its callers) emitting run_start before the loop, a per-story event after each story's outcome resolves, run_end after the loop completes normally, and run_aborted_unexpected on an uncaught exception -- mirroring WI-RUNLOG-0080's pattern rather than reconciling onto gatherlib.gather(); scoped inside gather_stories() specifically because it has two independent production callers (gather() at mass_quantities/gatherer.py:21 and main() at mass_quantities/gatherer.py:64) as well as its own direct test coverage, so wrapping only one caller would leave the other without a run log or require duplicate scopes
  - Log path is logs/gather/mass_quantities_gather_run_log.jsonl, matching gatherlib.gather()'s own DEFAULT_GATHER_LOG_DIR (logs/gather) and <corpus>_gather_run_log.jsonl naming convention (gatherlib.py:17,122) so the destination is deterministic and consistent with the other gatherers' run logs, derived via RunLog's protected-root re-validation
  - An explicit, recorded decision on whether to preserve gather_story()'s existing narrow load_etext()-only per-story recovery (parser.py:1402-1405) as-is -- default is preserve, no behavior change to that recovery path
  - A crash mid-run (e.g. simulated kill/exception) leaves a readable partial run log reflecting every story processed so far
  - mass_quantities_test.py covers the new logging, extended as needed
  - lrh validate and scripts/test pass with 0 errors
required_evidence:
  - lrh_validate
  - test_output
artifacts_expected:
  - lcats/src/lcats/gatherers/mass_quantities/gatherer.py
  - lcats/tests/gatherers_tests/mass_quantities_test.py
---

## Summary

`WI-GATHER-0101`'s audit (`project/design/gatherer-reconciliation-audit.md`)
classified `mass_quantities/gatherer.py` as structurally incompatible with
`gatherlib.gather()` -- it is a bulk Gutenberg-ID scanner with
metadata-based filtering, not a corpus-with-known-headings gatherer, so
no equivalent concept exists in `gatherlib.gather()`'s model. Rather than
reconciling, this work item wraps `gather_stories()`'s own loop in a
`RunLog` scope directly, mirroring `WI-RUNLOG-0080`'s pattern, to close
the run-log coverage gap `WI-RUNLOG-0082` left open for this site.

## Problem / Context

`mass_quantities/gatherer.py`'s `gather_stories()` loop has no run-log
coverage today. The audit verified `parser.gather_story()`'s real error
handling (`parser.py:1365-1483`) line by line: only `api.load_etext()`
is wrapped in `try`/`except`
(`parser.py:1402-1405`; `mass_quantities/gatherer.py:49-56`'s loop never
breaks on that error) -- a narrow, single-failure-mode per-story recovery,
not general isolation. Every other exception path (metadata access, body
processing, filename construction, normalization, directory creation,
the final JSON write) remains unprotected and can propagate. This work
item must preserve that existing narrow recovery path exactly, adding
only run-log instrumentation around it.

### Duplication search
- In-repo: No existing run log in this script. Recommendation: Proceed.
- Sibling repos: None identified.
- External libraries: None identified.
- Recommendation: Proceed.

### Demand search
- Work items: `WI-RUNLOG-0082` (resolved) -- its own Non-Goals excluded
  `mass_quantities` pending the reconciliation audit. `WI-GATHER-0101`
  (resolved) -- its audit's own Recommendation table names this as
  needing a dedicated run-log work item, not a `gatherlib.gather()`
  change. `WI-RUNLOG-0080` (resolved) -- the direct pattern precedent for
  a `RunLog`-wrapped per-story loop.
- Proposals: `PROP-LCATS-RUN-LOG` names `lcats gather` as an aggregate
  upgrade site; `mass_quantities` was explicitly excluded from that
  item's own scope pending the audit.
- Backlog: No matching entries in `project/design/backlog.md`.
- Recommendation: Proceed -- this work item is the follow-up the audit
  itself named.

## Scope

- Wrap `mass_quantities/gatherer.py`'s `gather_stories()` loop in a
  `RunLog` scope *inside `gather_stories()` itself*: `run_start`, a
  per-story event, `run_end`, `run_aborted_unexpected` (not around one of
  its two independent callers -- see Required Changes).
- Preserve the existing narrow `load_etext()`-only per-story recovery
  exactly as-is by default.
- Do not attempt reconciliation onto `gatherlib.gather()` -- out of scope
  per the audit's own classification.

## Non-Goals

- Does not touch `sherlock` or `lovecraft` -- separate work items
  (`WI-GATHER-0103`, `WI-GATHER-0104`).
- Does not change `gather_story()`'s existing error-handling scope
  (narrow `load_etext()`-only recovery) without explicit human sign-off
  at the point any such change is proposed.

## Required Changes

1. Open the `RunLog` scope inside `gather_stories()` itself
   (`mass_quantities/gatherer.py:26-58`), emitting `run_start` before the
   loop and `run_end` after it completes normally, with
   `run_aborted_unexpected` on an uncaught exception, and a per-story
   event after each story's outcome (success, `load_etext()` failure, or
   other rejection) resolves. Scope the `RunLog` here, not around a
   caller (review finding, PR #419 -- `gather_stories()` has two
   independent production callers, `gather()` at
   `mass_quantities/gatherer.py:21` and `main()` at
   `mass_quantities/gatherer.py:64`, plus its own direct test coverage;
   wrapping only one caller leaves the other without a run log or
   requires a duplicate scope, and conflicts with the acceptance
   criterion that the loop itself is covered).
2. Set the log destination to
   `logs/gather/mass_quantities_gather_run_log.jsonl` (review finding,
   PR #419 -- pinning this explicitly, matching
   `gatherlib.gather()`'s own `DEFAULT_GATHER_LOG_DIR`/naming convention
   at `gatherlib.py:17,122`, rather than leaving the destination
   underspecified).
3. Record explicitly (in this work item's execution record) the decision
   to preserve the existing narrow recovery path unchanged, per the
   audit's own finding.
4. Extend `mass_quantities_test.py` to cover the new log, including a
   case where the loop is interrupted mid-run.

## Acceptance Criteria

(see frontmatter)

## Validation

- `scripts/version tools`
- `lrh validate`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`

## Dependencies / Order

Must land after `WI-RUNLOG-0078` (the shared `lcats.utils.run_log`
module).

## Related Workstream and Designs

- Design: `project/design/proposals/proposed/lcats-run-log/00_proposal.md`
- Design: `project/design/gatherer-reconciliation-audit.md`
- Work item: `project/work_items/resolved/WI-GATHER-0101.md` (the audit
  that identified and scoped this reconciliation gap)
- Precedent: `project/work_items/resolved/WI-RUNLOG-0080.md`
