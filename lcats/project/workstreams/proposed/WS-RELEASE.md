---
id: WS-RELEASE
kind: planning_node
title: LCATS PyPI Release Readiness
status: proposed
stage: planned
origin: design_review
summary: Coordinate the work items that resolve LCATS's gutenbergpy PyPI-upload blocker, deliver minimal release-version tooling, and gate any real publish behind a pre-launch verification check, per PROP-LCATS-PYPI-RELEASE-READINESS.
related_focus: []
related_roadmap: []
related_design:
  - project/design/proposals/proposed/lcats-pypi-release-readiness/00_proposal.md
work_items:
  - WI-RELEASE-0037
  - WI-RELEASE-0038
  - WI-RELEASE-0039
exit_criteria:
  - WI-RELEASE-0037 is resolved -- lcats/pyproject.toml's gutenbergpy dependency no longer contains a direct URL/VCS reference
  - WI-RELEASE-0037 is resolved -- lcats/environment.yml's gutenbergpy dependency no longer contains a direct URL/VCS reference
  - WI-RELEASE-0038 is resolved (already true) -- lcats.version, --version, and scripts/version exist and pass validation
  - WI-RELEASE-0039 is resolved by actually being run, confirming the gutenbergpy resolution is still current, immediately before any real LCATS PyPI publish is attempted -- not resolved merely as a formality shortly after WI-RELEASE-0037
  - PROP-LCATS-PYPI-RELEASE-READINESS's implementation_status is updated to implemented once all three work items are resolved
---

# Workstream: LCATS PyPI Release Readiness

## Purpose

This workstream coordinates the work items that implement
`PROP-LCATS-PYPI-RELEASE-READINESS`: resolving the `gutenbergpy`
direct-VCS-dependency PyPI-upload blocker, delivering the minimal
release-version tooling LCATS actually needs now, and gating any real
publish behind a dedicated pre-launch verification step rather than a
one-time decision. It exists to track the sequencing between "decide and
implement the dependency fix" and "confirm that fix is still valid right
before publish" — a distinction a single unscoped work item couldn't
express.

## Scope

- Resolve `WI-RELEASE-0037` (the `gutenbergpy` dependency blocker).
- `WI-RELEASE-0038` (version tooling) — already resolved, tracked here for
  completeness.
- Run `WI-RELEASE-0039` (pre-launch verification) immediately before any
  real PyPI publish attempt.
- Update `PROP-LCATS-PYPI-RELEASE-READINESS`'s `implementation_status`
  once all three work items are resolved.

## Prior Art Check

### Duplication search
- In-repo: No existing workstream addresses PyPI release readiness
  (checked `project/workstreams/proposed/`, `project/workstreams/resolved/`).
- Sibling repos: `logical_robotics_harness`'s release apparatus is the
  comparison point used throughout the governing proposal, not duplicated
  work.
- External libraries: None applicable.
- Recommendation: Proceed.

### Demand search
- Work items: Found — `WI-RELEASE-0037`, `WI-RELEASE-0038` (already
  linked above).
- Proposals: `PROP-LCATS-PYPI-RELEASE-READINESS` is this workstream's own
  originating proposal, not a duplicate.
- Backlog: No `project/design/backlog.md` in this repo.
- Recommendation: No action.

## Work Items

- **WI-RELEASE-0037** — Resolve the `gutenbergpy` VCS-pin PyPI-publish
  blocker (vendor vs. re-fork-and-publish vs. wait-on-upstream). Proposed,
  open.
- **WI-RELEASE-0038** — `lcats.version` module, `--version` CLI flag,
  `scripts/version` helper. Resolved, merged (PR #183).
- **WI-RELEASE-0039** — Pre-launch verification gate: re-checks the
  `gutenbergpy` dependency-blocker's resolution status (upstream release
  state, or the continued validity of whatever fix `WI-RELEASE-0037`
  lands on) immediately before any real LCATS PyPI publish is attempted.
  `depends_on: WI-RELEASE-0037`. Proposed.

## Exit Criteria

- `WI-RELEASE-0037` is resolved: `lcats/pyproject.toml`'s `gutenbergpy`
  dependency no longer contains a direct URL/VCS reference.
- `WI-RELEASE-0037` is resolved: `lcats/environment.yml`'s `gutenbergpy`
  dependency no longer contains a direct URL/VCS reference.
- `WI-RELEASE-0038` is resolved (already true): `lcats.version`,
  `--version`, and `scripts/version` exist and pass validation.
- The pre-launch verification work item is resolved — actually run,
  confirming the `gutenbergpy` resolution is still current, immediately
  before any real LCATS PyPI publish is attempted.
- `PROP-LCATS-PYPI-RELEASE-READINESS`'s `implementation_status` is
  updated to `implemented` once all three work items are resolved.

## Non-Goals

- Does not include actually publishing LCATS to PyPI — no
  `publish_package` action happens under this workstream, per the
  governing proposal's Non-Goals.
- Does not scope `scripts/release-smoke`, a release runbook, or PyPI
  Trusted Publishing setup — deferred to future work items once a real
  publish is imminent.
- Does not decide vendor vs. fork-and-publish vs. wait for
  `WI-RELEASE-0037` — that decision is that work item's own scope.

## Relationship to Design

- Design proposal:
  `project/design/proposals/proposed/lcats-pypi-release-readiness/00_proposal.md`
  (PR #184, not yet merged; proposal `status` remains `proposed` on disk
  until this workstream closes and adopts it, per LRH convention).
- Prior workstream: `project/workstreams/resolved/WS-PACKAGING.md` (the
  model this workstream follows).
