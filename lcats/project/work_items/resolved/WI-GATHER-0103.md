---
resolution: "Implemented and merged in PR #421 (commit 5c6e9e5e)."
blocked_reason: null
blocked: false
id: WI-GATHER-0103
title: Reconcile sherlock/gatherer.py onto gatherlib.gather()
type: deliverable
status: resolved
owner: unassigned
contributors: []
assigned_agents: []
related_focus: []
related_roadmap: []
related_workstreams: []
related_design:
  - lcats/project/design/gatherer-reconciliation-audit.md
  - lcats/project/work_items/resolved/WI-GATHER-0101.md
depends_on: []
blocked_by: []
expected_actions:
  - edit_file
  - run_tests
forbidden_actions:
  - force_push
  - delete_branch
acceptance:
  - sherlock/gatherer.py's gather() calls gatherlib.gather() directly with author="Arthur Conan Doyle", year=1891, headings=ADVENTURES_HEADINGS, gutenberg_url=ADVENTURES_GUTENBERG, paragraph_finder=find_paragraphs_adventures passed through unchanged, and verbose=False (gatherlib.gather() defaults verbose=True and prints its own start/total messages at gatherlib.py:116,158; sherlock's own main() already prints equivalent messages at sherlock/gatherer.py:146,148 -- passing verbose=False avoids duplicate console output while preserving the zero-behavior-change goal)
  - The now-dead create_download_callback in sherlock/gatherer.py is removed, and sherlock_gatherer_test.py's TestCreateDownloadCallback class (lines 101-169) and the DataGatherer-construction-patching TestGather class (lines 170-208, which patch sherlock.gatherer.downloaders.DataGatherer -- no longer valid once construction happens inside gatherlib.gather() instead) are replaced with equivalent coverage retargeted at the new implementation, not left in place unchanged
  - Running gather() produces a logs/gather/*sherlock* run log, confirming sherlock inherits gatherlib.gather()'s existing RunLog coverage with no sherlock-specific code
  - lrh validate and scripts/test pass with 0 errors
required_evidence:
  - lrh_validate
  - test_output
artifacts_expected:
  - lcats/src/lcats/gatherers/sherlock/gatherer.py
  - lcats/tests/gatherers_tests/sherlock_gatherer_test.py
---

## Summary

`WI-GATHER-0101`'s audit (`project/design/gatherer-reconciliation-audit.md`)
classified `sherlock/gatherer.py`'s `gather()` as ready for full
reconciliation onto `gatherlib.gather()` with zero extraction/output-file
behavior change: it already accepts a `paragraph_finder` override, so
`sherlock`'s existing `find_paragraphs_adventures` can be passed through
unchanged rather than substituted for `gatherlib.find_paragraphs`.
(Review finding, PR #419: the migration does need one deliberate flag,
`verbose=False`, to avoid duplicating `main()`'s own console output --
see Required Changes.) This closes both the run-log coverage gap
`WI-RUNLOG-0082` left open for `sherlock` and a real code-duplication
gap.

## Problem / Context

`sherlock/gatherer.py`'s `gather()` currently reproduces
`gatherlib.gather()`'s loop 1:1, with hardcoded values in place of what
would be call-site arguments, and its own `create_download_callback`
duplicating `gatherlib.create_download_callback`. Because `sherlock`
does not route through the shared function, it did not inherit the
`RunLog` coverage `WI-RUNLOG-0082` added there.

### Duplication search
- In-repo: No existing reconciliation of `sherlock/gatherer.py`.
  Recommendation: Proceed.
- Sibling repos: None identified.
- External libraries: None identified.
- Recommendation: Proceed.

### Demand search
- Work items: `WI-GATHER-0101` (resolved) — its audit's own Recommendation
  table names this as a good follow-up candidate once confirmed
  ready-to-implement, which the review round on PR #414 did.
- Proposals: `PROP-LCATS-RUN-LOG` names `lcats gather` as an aggregate
  upgrade site; `sherlock` was explicitly excluded from that item's own
  scope pending this audit.
- Backlog: No matching entries in `project/design/backlog.md`.
- Recommendation: Proceed — this work item is the follow-up the audit
  itself named.

## Scope

- Replace `sherlock/gatherer.py`'s `gather()` body with a direct call to
  `gatherlib.gather()`, per the audit's design sketch.
- Remove the now-dead `create_download_callback`.
- Confirm output parity via the existing test suite.

## Non-Goals

- Does not touch `lovecraft` or `mass_quantities` — separate work items
  (`WI-GATHER-0104`, `WI-GATHER-0105`).
- Does not change `gatherlib.gather()`'s own signature or behavior.

## Required Changes

1. Replace `sherlock/gatherer.py`'s `gather()` implementation with the
   audit's design sketch: a direct `gatherlib.gather()` call with
   `author="Arthur Conan Doyle"`, `year=1891`,
   `headings=ADVENTURES_HEADINGS`, `gutenberg_url=ADVENTURES_GUTENBERG`,
   `paragraph_finder=find_paragraphs_adventures`, and `verbose=False`
   (review finding, PR #419 — `gatherlib.gather()` defaults `verbose=True`
   and prints its own status messages at `gatherlib.py:116,158`; `main()`
   already prints equivalent messages at `sherlock/gatherer.py:146,148`,
   so leaving the default would produce duplicate console output, a real
   observable-behavior change the "zero behavior change" claim did not
   account for).
2. Remove `create_download_callback` from `sherlock/gatherer.py`.
3. Replace `sherlock_gatherer_test.py`'s `TestCreateDownloadCallback`
   class (lines 101-169) and the `TestGather` class's
   `DataGatherer`-construction-patching assertions (lines 170-208, which
   patch `sherlock.gatherer.downloaders.DataGatherer` — review finding,
   PR #419, correcting an earlier fix's own line-range citation error —
   both directly exercise the removed callback or patch construction that
   no longer happens inside `sherlock/gatherer.py` once `gather()` calls
   `gatherlib.gather()` directly; both break as written, not pass
   unchanged) with equivalent coverage against the new implementation.

## Acceptance Criteria

(see frontmatter)

## Validation

- `scripts/version tools`
- `lrh validate`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`

## Related Workstream and Designs

- Design: `project/design/gatherer-reconciliation-audit.md`
- Work item: `project/work_items/resolved/WI-GATHER-0101.md` (the audit
  that identified and scoped this reconciliation)
