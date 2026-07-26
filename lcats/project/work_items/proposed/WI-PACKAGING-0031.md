---
resolution: null
blocked_reason: null
blocked: false
id: WI-PACKAGING-0031
title: Bring lcats/pyproject.toml metadata up to PEP 621/639 and CI-parity
type: deliverable
status: proposed
owner: xenotaur
contributors:
  - xenotaur
assigned_agents: []
related_focus: []
related_roadmap: []
related_workstreams:
  - WS-PACKAGING
related_design:
  - project/design/proposals/proposed/lcats-packaging-modernization/00_proposal.md
depends_on: []
blocked_by: []
expected_actions:
  - edit_file
  - run_tests
  - create_pr
forbidden_actions:
  - force_push
  - delete_branch
  - implement_lcats_src_layout_move
  - modify_ci_pipeline
acceptance:
  - lcats/pyproject.toml declares license = "MIT" plus license-files = ["LICENSE"] (PEP 639 form), not the deprecated {text = "MIT"} table
  - lcats/pyproject.toml build-system.requires pins setuptools>=77
  - lcats/pyproject.toml has [tool.ruff] required-version = "==0.15.0" and [tool.black] required-version = "25.11.0", matching lint.yml's CI pins
  - ruff is pinned (not left unpinned) in the test/dev optional-dependency extras, matching black's existing pin
  - the test and dev optional-dependency lists are no longer byte-identical duplicates
  - the gutenbergpy dependency is pinned to a commit SHA, not the mutable @LCATS/TitleFix branch ref
  - lcats/pyproject.toml has a [project.urls] table (Repository, Issues) and additional classifiers matching logical_robotics_harness/pyproject.toml's pattern
  - lrh validate reports 0 errors
required_evidence:
  - lrh_validate
  - test_output
artifacts_expected:
  - lcats/pyproject.toml
---

## Summary

Bring `lcats/pyproject.toml`'s metadata up to current PyPA/PEP 621/PEP 639
best practice and CI-pin parity, as Phase 1 of `WS-PACKAGING` — license
declaration, build-system floor, tool version self-enforcement,
dependency-extras cleanup, and a reproducible git dependency pin. Pure
`pyproject.toml` edits; no code, layout, or CI changes.

## Problem / Context

`PROP-LCATS-PACKAGING-MODERNIZATION` (merged via PR #159) identified nine
packaging gaps versus PyPA guidance and the sibling `lrh` project's own
setup; `WS-PACKAGING` (merged via PR #160) sequences the fix into three
phases so tool-version self-enforcement lands before the higher-risk
src-layout move. This item is that first phase. It must land before the
src-layout work item, per the workstream's documented ordering constraint.

### Duplication search
- In-repo: No existing implementation found.
- Sibling repos: `logical_robotics_harness/pyproject.toml` already
  implements the target pattern (PEP 639 license, tool `required-version`
  pins) — reference, not duplicate.
- External libraries: None identified — this is project packaging
  configuration.
- Recommendation: Proceed.

### Demand search
- Work items: None found.
- Proposals: None found (`PROP-LCATS-PACKAGING-MODERNIZATION` is the
  originating request, already linked via `related_design`).
- Backlog: No matching entries.
- Recommendation: No action.

## Scope

- Edit `lcats/pyproject.toml` metadata only: license form, build-system
  floor, tool `required-version` pins, extras cleanup, `gutenbergpy` pin,
  `project.urls`/classifiers.
- Run the standard validation sequence to confirm nothing else broke.

## Required Changes

1. `license = {text = "MIT"}` → `license = "MIT"` +
   `license-files = ["LICENSE"]`.
2. `build-system.requires`: `setuptools>=42` → `setuptools>=77` (the
   version that added PEP 639 `license`/`license-files` support).
3. Add `[tool.ruff] required-version = "==0.15.0"` and
   `[tool.black] required-version = "25.11.0"`, matching `lint.yml`'s CI
   pins.
4. Pin `ruff` (currently unpinned) alongside the existing `black==25.11.0`
   pin in both the `test` and `dev` extras.
5. Deduplicate the byte-identical `test`/`dev` optional-dependency lists
   (collapse to one `dev` extra, or confirm nothing external depends on the
   `test` extra name before removing it).
6. Replace
   `gutenbergpy @ git+https://github.com/xenotaur/gutenbergpy.git@LCATS/TitleFix`
   with a pin to that branch's current commit SHA.
7. Add `[project.urls]` (`Repository`, `Issues`) and additional
   classifiers, matching `logical_robotics_harness/pyproject.toml`'s
   pattern.

## Non-Goals

- Does not move `lcats/lcats/` to `lcats/src/lcats/` — that is the next
  work item in this workstream.
- Does not add `setuptools-scm` or change `version = "0.1"` — that is the
  third work item.
- Does not modify CI workflow YAML.
- Does not touch any file outside `lcats/pyproject.toml`.

## Acceptance Criteria

- `lcats/pyproject.toml` declares `license = "MIT"` plus
  `license-files = ["LICENSE"]` (PEP 639 form), not the deprecated
  `{text = "MIT"}` table.
- `lcats/pyproject.toml` `build-system.requires` pins `setuptools>=77`.
- `lcats/pyproject.toml` has `[tool.ruff] required-version = "==0.15.0"`
  and `[tool.black] required-version = "25.11.0"`, matching `lint.yml`'s
  CI pins.
- `ruff` is pinned (not left unpinned) in the `test`/`dev`
  optional-dependency extras, matching `black`'s existing pin.
- The `test` and `dev` optional-dependency lists are no longer
  byte-identical duplicates.
- The `gutenbergpy` dependency is pinned to a commit SHA, not the mutable
  `@LCATS/TitleFix` branch ref.
- `lcats/pyproject.toml` has a `[project.urls]` table (`Repository`,
  `Issues`) and additional classifiers matching
  `logical_robotics_harness/pyproject.toml`'s pattern.
- `lrh validate` reports 0 errors.

## Validation

- `lrh validate`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `python -m pip install -e ".[dev]"`

## Risk Notes

- Raising `setuptools>=77` could be a stricter floor than some
  contributors' local environments have installed — worth confirming CI's
  `setup-python`/pip cache picks it up correctly.
- Deduplicating `test`/`dev` extras risks breaking anything that
  references the `test` extra by name specifically; check before removing.

## Related Workstream and Designs

- Workstream: `project/workstreams/proposed/WS-PACKAGING.md`
- Design: `project/design/proposals/proposed/lcats-packaging-modernization/00_proposal.md`
