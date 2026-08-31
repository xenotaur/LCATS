---
resolution: null
blocked_reason: null
blocked: false
id: WI-GATHER-0105
title: Add a dedicated run-log wrapper to mass_quantities/gatherer.py
type: deliverable
status: proposed
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
  - mass_quantities/gatherer.py's gather_stories() loop is wrapped in a RunLog scope emitting run_start before the loop, a per-story event after each story's outcome resolves, run_end after the loop completes normally, and run_aborted_unexpected on an uncaught exception -- mirroring WI-RUNLOG-0080's pattern rather than reconciling onto gatherlib.gather()
  - Log path lives outside data/ and corpora/, derived via RunLog's protected-root re-validation
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
  `RunLog` scope: `run_start`, a per-story event, `run_end`,
  `run_aborted_unexpected`.
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

1. Hook a per-story event inside `gather_stories()`'s loop
   (`mass_quantities/gatherer.py:26-58`), after each story's outcome
   (success, `load_etext()` failure, or other rejection) resolves.
2. Wrap the call to `gather_stories()` in a `RunLog` scope in its caller,
   emitting `run_start` before the call and `run_end` after, with
   `run_aborted_unexpected` on an uncaught exception -- following
   `WI-RUNLOG-0080`'s precedent for where the wrapping boundary belongs.
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
