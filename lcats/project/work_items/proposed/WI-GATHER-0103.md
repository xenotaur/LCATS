---
resolution: null
blocked_reason: null
blocked: false
id: WI-GATHER-0103
title: Reconcile sherlock/gatherer.py onto gatherlib.gather()
type: deliverable
status: proposed
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
  - sherlock/gatherer.py's gather() calls gatherlib.gather() directly with author="Arthur Conan Doyle", year=1891, headings=ADVENTURES_HEADINGS, gutenberg_url=ADVENTURES_GUTENBERG, and paragraph_finder=find_paragraphs_adventures passed through unchanged (per the audit's ready-to-implement design sketch — zero behavior change, no gatherlib.find_paragraphs substitution)
  - The now-dead create_download_callback in sherlock/gatherer.py is removed
  - sherlock_gatherer_test.py's existing assertions pass unchanged, confirming output parity with the pre-reconciliation implementation
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
reconciliation onto `gatherlib.gather()` with zero behavior change: it
already accepts a `paragraph_finder` override, so `sherlock`'s existing
`find_paragraphs_adventures` can be passed through unchanged rather than
substituted for `gatherlib.find_paragraphs`. This closes both the
run-log coverage gap `WI-RUNLOG-0082` left open for `sherlock` and a
real code-duplication gap, with no behavioral risk.

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
   `paragraph_finder=find_paragraphs_adventures`.
2. Remove `create_download_callback` from `sherlock/gatherer.py`.
3. Run `sherlock_gatherer_test.py` and extend it only if a real gap is
   found (e.g. asserting the run-log side-effect exists) — the audit's
   own claim is zero behavior change, so existing assertions should pass
   as written.

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
