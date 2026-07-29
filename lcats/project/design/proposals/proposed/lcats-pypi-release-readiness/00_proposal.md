---
id: PROP-LCATS-PYPI-RELEASE-READINESS
type: design_proposal
title: LCATS PyPI Release Readiness — Dependency Blocker, Minimal Tooling, and a Pre-Launch Verification Gate
status: proposed
created_on: 2026-07-29
updated_on: 2026-07-29
implementation_status: partial
implemented_by:
  - WI-RELEASE-0038
supersedes: []
superseded_by: null
related_design:
  - project/design/proposals/adopted/lcats-packaging-modernization/00_proposal.md
---

## Summary

Formalizes LCATS's path to a real, non-placeholder PyPI release: resolving
the `gutenbergpy` direct-VCS-dependency upload blocker, delivering only the
release tooling LCATS actually needs right now, and — per explicit request —
adding a dedicated work item that re-verifies the blocker's resolution
status immediately before the real publish is attempted, rather than
treating a one-time decision as permanently settled.

## Background / Motivation

`PROP-LCATS-PACKAGING-MODERNIZATION` (adopted, implemented) brought
`lcats/pyproject.toml` to PEP 621/639 standard and added `setuptools-scm`
dynamic versioning — but LCATS still cannot be uploaded to PyPI at all. A
release-readiness comparison against the sibling `logical_robotics_harness`
project's much more developed release tooling (`scripts/version`,
`scripts/release-smoke`, a full runbook at
`docs/how-to/run-a-release.md`, PyPI Trusted Publishing, TestPyPI
rehearsal) surfaced two concrete gaps and one hard blocker:

1. **Hard blocker:** `lcats/pyproject.toml:26` pins
   `gutenbergpy @ git+https://github.com/xenotaur/gutenbergpy.git@60ca548...`
   — a PEP 508 direct URL/VCS reference. Traced to the actual PyPI
   upload-validation source (`pypi/warehouse`'s
   `warehouse/forklift/metadata.py`, `_validate_metadata`): any
   `Requires-Dist` entry whose parsed `Requirement.url` is not `None` is
   rejected with `Can't have direct dependency: <req>`. This is not a
   theoretical concern — it is the literal shape of LCATS's current
   dependency declaration, and it blocks upload unconditionally regardless
   of any other release-readiness work.
2. **Tooling gap (now closed):** LCATS had no `--version` flag, no
   `lcats.version` module, and no `scripts/version` helper — `v0.1.0` was
   tagged by hand with no verification gate. Closed via `WI-RELEASE-0038`
   (merged, PR #183).
3. **Scoping question:** LRH's full release apparatus (release-smoke,
   runbook, Trusted Publishing, TestPyPI rehearsal) is more than LCATS
   needs *right now* — LCATS isn't targeting an imminent real publish
   beyond resolving the dependency blocker, and porting that full apparatus
   prematurely would be release-infrastructure investment ahead of an
   actual publish decision.

The motivating driver is wanting a real release "sooner rather than
later," informally targeting readiness around a WorldCon 2026 paper, while
being comfortable with version-number churn to get there. The
`gutenbergpy` fixes needed (alias tables, title-index correction) are
already merged upstream (`raduangelescu/gutenbergpy` PR #25, #26) but not
yet in a PyPI release (still `0.3.5`, from 2023-03-27); the maintainer's
own `setup.cfg` already shows an unreleased `version = 0.3.6` bump — a
mildly encouraging, non-committal signal. The user has contacted the
maintainer about their release schedule; response pending as of this
proposal.

## Prior Art Check

### Duplication search
- In-repo: No existing proposal or design doc addresses PyPI release
  readiness (grepped `project/design/proposals/`, `src/`).
- Sibling repos: `logical_robotics_harness`'s release tooling is the
  comparison point, not duplicated work — its full apparatus
  (release-smoke, runbook, Trusted Publishing) is explicitly *not* being
  ported wholesale; see Non-Goals.
- External libraries: None applicable — this is release-process design,
  not a library concern.
- Recommendation: Proceed.

### Demand search
- Work items: Found — `WI-RELEASE-0037` (gutenbergpy blocker, proposed,
  open) and `WI-RELEASE-0038` (version tooling, resolved, merged). Both
  predate this proposal and were created directly in conversation without
  a governing proposal; this proposal formalizes the umbrella they already
  implicitly belong to, rather than duplicating them.
- Proposals: None found.
- Backlog: No `project/design/backlog.md` in this repo.
- Recommendation: Link both work items via `related_design`/
  `implemented_by` (done above); no closure action needed —
  `WI-RELEASE-0037` remains open, governed by this proposal going forward.

## Design Decisions

### Decision 1: How to keep the dependency-blocker resolution honest over time

Options considered:
- Resolve `WI-RELEASE-0037` once (vendor, fork-and-publish, or wait) and
  treat that decision as permanently settled.
- Add no additional gate — trust whoever runs the eventual real publish to
  re-check manually.
- Add an explicit, separate work item whose sole job is to re-verify the
  dependency-blocker's resolution status immediately before the real PyPI
  publish is attempted.

**Chosen: a dedicated pre-launch verification work item**, separate from
`WI-RELEASE-0037` itself. Rationale: the interval between resolving
`WI-RELEASE-0037` and actually publishing could be long enough for
upstream state to change (a new `gutenbergpy` PyPI release could land,
making a chosen vendor/fork solution obsolete or reversible), or for a
vendored/forked copy to have silently drifted from what was verified at
implementation time. A one-time decision recorded in a now-closed work
item has no mechanism to force a second look; a standing, explicitly-scoped
item does. This directly satisfies the request to have "a specific item to
check back in on that element of the release before launch."

### Decision 2: Release-tooling scope

Options considered:
- Full LRH-parity port: `scripts/version`, `scripts/release-smoke`, a
  runbook, PyPI Trusted Publishing, TestPyPI rehearsal.
- Minimal scoped subset matching only what LCATS's current state actually
  needs.

**Chosen: minimal subset.** `scripts/version` (delivered,
`WI-RELEASE-0038`) closes the "no version visibility" gap.
`scripts/release-smoke`, the runbook, and Trusted Publishing setup are
deferred — they're meaningful once a real publish is imminent and a PyPI
project name/publishing mechanism is decided, not before. Building them
now would be infrastructure investment ahead of the actual blocking
decision (`WI-RELEASE-0037`).

### Decision 3: Governance structure

Options considered:
- Keep `WI-RELEASE-0037`/`WI-RELEASE-0038` as loose, proposal-less ad hoc
  items.
- Formalize under a governing workstream, mirroring `WS-PACKAGING`'s
  pattern.

**Chosen: a governing workstream** (companion `/lrh-workstream` invocation
follows this proposal), giving the effort visible scope, exit criteria,
and a natural home for the new pre-launch-verification work item and any
future release-smoke/runbook items.

## Non-Goals

- Does not decide vendor vs. fork-and-publish vs. wait-on-upstream for the
  `gutenbergpy` blocker — that decision remains `WI-RELEASE-0037`'s own
  scope.
- Does not scope `scripts/release-smoke` or a release runbook now —
  deferred to future work items once the dependency blocker is resolved
  and actual publish is imminent.
- Does not reserve or publish anything to PyPI — no `publish_package`
  action happens under this proposal or its immediate work items.
- Does not set up PyPI Trusted Publishing, GitHub environment protection,
  or TestPyPI rehearsal infrastructure — premature without a reserved
  PyPI project name and a concrete publish timeline.
- Does not change LCATS's `README.md:33` "not yet supported" claim — a
  separate, already-identified follow-up.

## Implementation Plan

Multi-stage; delivered against a governing workstream (recommended next
step: `/lrh-workstream`):

1. `WI-RELEASE-0037` (existing, proposed) — resolve the `gutenbergpy`
   dependency blocker.
2. `WI-RELEASE-0038` (existing, resolved) — `lcats.version`, `--version`,
   `scripts/version`. Already delivered.
3. **New work item** (to be scoped via `/lrh-work-item` after this
   proposal and its workstream land): a pre-launch verification gate —
   re-check `gutenbergpy` upstream release status and/or the chosen fix's
   continued validity, run immediately before any real PyPI publish
   attempt, blocking that publish until confirmed current.
4. Deferred, not yet scoped: `scripts/release-smoke`, release runbook,
   PyPI project reservation and Trusted Publishing setup — future work
   items once steps 1 and 3 make a real publish imminent.

## Cross-References

- `project/design/proposals/adopted/lcats-packaging-modernization/00_proposal.md`
  — prior, adopted proposal this one builds on.
- `logical_robotics_harness/docs/how-to/run-a-release.md` — comparison
  reference for release-tooling scope; not adopted wholesale, see
  Non-Goals.
- `project/work_items/proposed/WI-RELEASE-0037.md`,
  `project/work_items/resolved/WI-RELEASE-0038.md`.

## Open Questions

- No concrete WorldCon 2026 paper deadline date is known to this
  proposal — timing urgency is informal. If a hard date exists, it should
  inform the governing workstream's own scheduling, not this proposal.
- Exact trigger/procedure for the pre-launch verification work item (e.g.,
  a specific PyPI/GitHub check to run, or a manual maintainer-contact
  follow-up) is left to that work item's own scoping, not decided here.
