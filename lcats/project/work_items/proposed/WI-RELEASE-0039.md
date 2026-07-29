---
resolution: null
blocked_reason: null
blocked: false
id: WI-RELEASE-0039
title: Pre-launch verification of the gutenbergpy dependency resolution before real PyPI publish
type: evaluation
status: proposed
owner: xenotaur
contributors:
  - xenotaur
assigned_agents: []
related_focus: []
related_roadmap: []
related_workstreams: []
related_design:
  - project/design/proposals/proposed/lcats-pypi-release-readiness/00_proposal.md
depends_on:
  - WI-RELEASE-0037
blocked_by: []
expected_actions:
  - create_report
  - edit_file
  - create_pr
forbidden_actions:
  - force_push
  - delete_branch
  - publish_package
  - modify_ci_pipeline
acceptance:
  - A verification report exists confirming, as of a date immediately preceding the real PyPI publish attempt, whether gutenbergpy has a newer PyPI release incorporating PR #25/#26 (which would make "wait on upstream" viable even if WI-RELEASE-0037 originally chose otherwise)
  - If WI-RELEASE-0037 chose vendoring - the report confirms the vendored copy in lcats/src/lcats/gettenberg/ still matches what was verified at implementation time, and checks for any new upstream commits to the vendored files that should be considered for re-porting
  - If WI-RELEASE-0037 chose re-fork-and-publish - the report confirms the LCATS-controlled fork's PyPI package is still current, its own dependency pin in lcats/pyproject.toml resolves correctly, and the fork has not fallen behind any relevant upstream security fixes
  - If findings suggest WI-RELEASE-0037's original decision should be revisited, that discrepancy is surfaced to the user before any publish proceeds - this item does not unilaterally change the dependency pin or re-decide vendor vs. fork vs. wait
  - This item is not resolved until it has actually been run and reported on in the same work session as an imminent real PyPI publish attempt - an early dry run does not satisfy its purpose
  - lrh validate reports 0 errors
required_evidence:
  - manual_review
  - lrh_validate
artifacts_expected:
  - project/executions/WI-RELEASE-0039/
---

## Summary

Re-verify, immediately before any real LCATS PyPI publish is attempted,
that `WI-RELEASE-0037`'s `gutenbergpy` dependency-blocker resolution is
still current — catching upstream releases, drift in a vendored/forked
copy, or other changes that could make the original decision stale.

## Problem / Context

`PROP-LCATS-PYPI-RELEASE-READINESS`'s Design Decision 1 ("How to keep the
dependency-blocker resolution honest over time") identified that
resolving `WI-RELEASE-0037` once and treating it as permanently settled
has a real gap: the interval between that resolution and an actual
publish attempt could be long enough for upstream `gutenbergpy` state to
change (a new PyPI release could land, making a chosen vendor/fork
solution unnecessary or reversible), or for a vendored/forked copy to
have silently drifted from what was verified at implementation time. A
one-time decision recorded in a now-closed work item has no built-in
mechanism to force a second look before the point where drift actually
matters — the moment of real publish. This work item is that standing
mechanism, per the proposal's and governing workstream's
(`WS-RELEASE`) explicit design.

### Duplication search
- In-repo: No existing implementation or decision record found (grepped
  `project/work_items/`, `project/design/proposals/` for
  "pre-launch"/"pre-publish"/"release gate"/"publish verification").
- Sibling repos: None identified — this is LCATS-specific.
- External libraries: None applicable — this is a manual verification
  gate, not a library concern.
- Recommendation: Proceed.

### Demand search
- Work items: None found beyond the originating proposal/workstream
  themselves.
- Proposals: `PROP-LCATS-PYPI-RELEASE-READINESS` is this item's own
  originating proposal, not a duplicate demand.
- Backlog: No `project/design/backlog.md` in this repo.
- Recommendation: No action.

## Scope

- Confirm `gutenbergpy`'s current PyPI release status against the
  upstream fixes (`raduangelescu/gutenbergpy` PR #25/#26).
- If `WI-RELEASE-0037` chose vendoring or forking-and-publishing, confirm
  that solution is still intact and current.
- Surface any discrepancy to the user before a real publish proceeds —
  do not silently re-decide or auto-correct.

## Required Changes

1. Check the current `gutenbergpy` PyPI release version and changelog
   for whether it now includes the alias-table/title-index fixes from
   PR #25/#26 — if so, "wait on upstream" may now be viable even if
   `WI-RELEASE-0037` originally chose otherwise, and that should be
   surfaced as a live option, not silently ignored.
2. If `WI-RELEASE-0037` chose vendoring: diff the vendored copy in
   `lcats/src/lcats/gettenberg/` against its recorded origin to confirm
   no accidental drift, and check `raduangelescu/gutenbergpy:master` for
   any new commits to the vendored files' upstream originals since
   `WI-RELEASE-0037` was resolved.
3. If `WI-RELEASE-0037` chose re-fork-and-publish: confirm the
   LCATS-controlled fork's PyPI package is still installable and
   current, and that `lcats/pyproject.toml`'s pin to it still resolves.
4. Write findings into this work item's execution record. If findings
   suggest the original `WI-RELEASE-0037` decision should be revisited,
   stop and report to the user — do not change the dependency pin or
   re-decide vendor/fork/wait as part of this item.
5. Do not perform the actual PyPI publish as part of this work item.

## Non-Goals

- Does not implement or change the `gutenbergpy` dependency fix itself —
  that remains `WI-RELEASE-0037`'s scope, even if this item's findings
  suggest revisiting it.
- Does not perform the actual PyPI publish — `forbidden_actions` bars
  `publish_package`.
- Does not set up ongoing or automated monitoring of `gutenbergpy`'s
  release status — this is a one-time manual gate run immediately before
  a specific publish attempt, not continuous integration.

## Acceptance Criteria

- A verification report exists confirming, as of a date immediately
  preceding the real PyPI publish attempt, whether `gutenbergpy` has a
  newer PyPI release incorporating PR #25/#26.
- If vendoring was chosen: the report confirms the vendored copy still
  matches what was verified at implementation time, and checks for new
  upstream commits worth re-porting.
- If re-fork-and-publish was chosen: the report confirms the fork's
  PyPI package is still current and its dependency pin resolves
  correctly.
- If findings suggest the original decision should be revisited, that
  is surfaced to the user before any publish proceeds — this item does
  not unilaterally act on it.
- This item is not resolved until it has actually been run and reported
  on in the same work session as an imminent real PyPI publish attempt.
- `lrh validate` reports 0 errors.

## Validation

- `lrh validate`
- Manual check documented against `https://pypi.org/project/gutenbergpy/`
  (or the chosen alternative package, if `WI-RELEASE-0037` published a
  fork)

## Risk Notes

- This item's value depends entirely on being run at the right time.
  Resolving it prematurely — e.g., immediately after `WI-RELEASE-0037`
  without an actual imminent publish — defeats its purpose. Whoever
  executes it should confirm a real publish is genuinely about to happen
  before treating this item as satisfied.
- Cannot be meaningfully executed until `WI-RELEASE-0037` has resolved —
  see `depends_on`.

## Dependencies / Order

Depends on `WI-RELEASE-0037` (cannot meaningfully run before that
item's vendor/fork/wait decision is made). Should run as the final step
before any real PyPI publish attempt, not scheduled to a fixed date —
timing is tied to the publish event itself, not the calendar.
