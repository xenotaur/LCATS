---
id: WS-PACKAGING
kind: planning_node
title: LCATS Python Packaging Modernization
status: proposed
stage: designed
origin: design_review
summary: Coordinate the three phased work items that bring lcats/pyproject.toml up to PyPA/PEP 621/PEP 639 best practice and parity with the sibling lrh project, per PROP-LCATS-PACKAGING-MODERNIZATION.
related_focus: []
related_roadmap: []
related_design:
  - project/design/proposals/proposed/lcats-packaging-modernization/00_proposal.md
work_items:
  - WI-PACKAGING-0031
  - WI-PACKAGING-0032
  - WI-PACKAGING-0035
exit_criteria:
  - lcats/pyproject.toml declares license via PEP 639 (license = "MIT" + license-files), pins setuptools>=77 (the version that added PEP 639 support), sets required-version for tool.ruff and tool.black, has no duplicate test/dev extras, and pins gutenbergpy to a commit SHA
  - lcats package code lives at lcats/src/lcats/ with scripts/lint, scripts/format, secrets.py, and all lcats/lcats path literals updated accordingly, and the full test suite passes against the new layout
  - lcats/pyproject.toml uses dynamic = ["version"] via setuptools-scm with a cut git tag, and lcats/setup.py is removed
  - all three work items are resolved and PROP-LCATS-PACKAGING-MODERNIZATION's implementation_status is updated to implemented
---

# Workstream: LCATS Python Packaging Modernization

## Purpose

This workstream coordinates the three sequential work items that implement
`PROP-LCATS-PACKAGING-MODERNIZATION`: bringing `lcats/pyproject.toml` and its
package layout up to current PyPA/PEP 621/PEP 639 best practice, matching the
sibling `lrh` project's own packaging setup. It exists to track cross-item
ordering constraints (metadata fixes must land before the layout move; the
layout move must land before `setup.py` removal) that a single unscoped work
item couldn't express.

## Scope

- Implement the three phases defined in the proposal's Implementation Plan:
  metadata/config fixes, src-layout move, dynamic versioning + `setup.py`
  removal.
- Land each phase as its own work item through the standard LRH execution
  lifecycle, in strict order.
- Update `PROP-LCATS-PACKAGING-MODERNIZATION`'s `implementation_status` and
  `implemented_by` once all three are resolved.

## Prior Art Check

### Duplication search
- In-repo: No existing implementation found.
- Sibling repos: `logical_robotics_harness` already implements the target
  pattern (src-layout, `setuptools-scm`, PEP 639 license) — reference, not
  duplicate.
- External libraries: None identified.
- Recommendation: Proceed.

### Demand search
- Work items: None found.
- Proposals: None found (`PROP-LCATS-PACKAGING-MODERNIZATION` itself is the
  originating proposal, not a duplicate request).
- Backlog: No matching entries.
- Recommendation: No action.

## Work Items

- **WI-PACKAGING-0031** — Metadata/config fixes: PEP 639 license,
  `setuptools>=77` build-system pin, tool `required-version` pins, dedupe
  extras, pin `gutenbergpy` to a commit SHA, `project.urls`/classifiers.
- **WI-PACKAGING-0032** — src-layout move: `lcats/lcats/` →
  `lcats/src/lcats/`, update `scripts/lint`/`scripts/format`, `secrets.py`,
  path-literal audit, reinstall, full test run. `depends_on:
  WI-PACKAGING-0031`.
- **WI-PACKAGING-0035** — Dynamic versioning + `setup.py` removal:
  `setuptools-scm`, first git tag, delete `setup.py`. `depends_on:
  WI-PACKAGING-0032`.

## Exit Criteria

- `lcats/pyproject.toml` declares license via PEP 639
  (`license = "MIT"` + `license-files`), pins `setuptools>=77` (the version
  that added PEP 639 `license`/`license-files` support — `>=68` is
  insufficient), sets `required-version` for `tool.ruff` and `tool.black`,
  has no duplicate `test`/`dev` extras, and pins `gutenbergpy` to a commit
  SHA.
- `lcats` package code lives at `lcats/src/lcats/` with `scripts/lint`,
  `scripts/format`, `secrets.py`, and all `lcats/lcats` path literals updated
  accordingly, and the full test suite passes against the new layout.
- `lcats/pyproject.toml` uses `dynamic = ["version"]` via `setuptools-scm`
  with a cut git tag, and `lcats/setup.py` is removed.
- All three work items are resolved and
  `PROP-LCATS-PACKAGING-MODERNIZATION`'s `implementation_status` is updated
  to `implemented`.

## Non-Goals

- Does not change LCATS's runtime dependencies or Python version floor.
- Does not migrate build backends away from setuptools.
- Does not fix `secrets.py`'s parent-depth-counting pattern beyond the
  one-line bump required by the layout move.
- Does not modify CI workflow YAML.

## Relationship to Design

- Design proposal:
  `project/design/proposals/proposed/lcats-packaging-modernization/00_proposal.md`
  (merged via PR #159, commit `398b59ceed839999cffe93ae8bc83503156ea517`;
  proposal `status` remains `proposed` on disk until this workstream closes
  and adopts it, per LRH convention)
