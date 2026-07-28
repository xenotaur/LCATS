---
resolution: null
blocked_reason: null
blocked: false
id: WI-PACKAGING-0035
title: Add setuptools-scm dynamic versioning and remove lcats/setup.py
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
depends_on:
  - WI-PACKAGING-0032
blocked_by: []
expected_actions:
  - create_file
  - edit_file
  - delete_file
  - run_tests
  - create_pr
forbidden_actions:
  - force_push
  - delete_branch
  - modify_ci_pipeline
acceptance:
  - lcats/pyproject.toml declares dynamic = ["version"] and no longer has a static version = "0.1" field
  - build-system.requires includes setuptools-scm
  - a [tool.setuptools_scm] table exists with a fallback_version set, matching logical_robotics_harness's own pattern
  - a first git tag (e.g. v0.1.0) exists on the repo, since none currently exist
  - lcats/setup.py no longer exists
  - python -m pip install -e ".[dev]" succeeds and reports a version derived from the git tag, not a hardcoded string
  - lrh validate reports 0 errors
required_evidence:
  - lrh_validate
  - test_output
artifacts_expected:
  - lcats/pyproject.toml
  - lcats/setup.py
---

## Summary

Add dynamic versioning to `lcats/pyproject.toml` via `setuptools-scm`
(deriving the installed version from git tags instead of the hardcoded,
never-updated `version = "0.1"`), cut the repo's first git tag, and
remove the now-fully-redundant `lcats/setup.py`. Phase 3 of `WS-PACKAGING`
— the last piece before the workstream can close.

## Problem / Context

`PROP-LCATS-PACKAGING-MODERNIZATION` (merged via PR #159) identified
`version = "0.1"` as static and never updated since it was added;
`WS-PACKAGING` (merged via PR #160) sequences this as Phase 3, after the
src-layout move (`WI-PACKAGING-0032`, resolved) lands, so the package
structure is stable before adding SCM-based versioning on top of it. This
item must not begin before `WI-PACKAGING-0032` is resolved (already
true). Confirmed this session: the repo currently has **zero git tags**
— `git tag --list` returns nothing — so cutting the first tag is a real,
necessary action, not a formality. Also confirmed: `lcats/setup.py` still
calls bare `find_packages()` with no `where="src"` parameter, meaning
it's already silently broken/stale since the Phase 2 src-layout move (it
would discover zero packages if anything still invoked it) — one more
reason it's safe and correct to delete rather than fix.

### Duplication search
- In-repo: No existing implementation found.
- Sibling repos: `logical_robotics_harness/pyproject.toml` already
  implements this exact pattern (`dynamic = ["version"]`,
  `[tool.setuptools_scm]` with `fallback_version`) — reference, not
  duplicate.
- External libraries: None identified — `setuptools-scm` is the
  dependency being adopted, not duplicated.
- Recommendation: Proceed.

### Demand search
- Work items: None found.
- Proposals: None found (`PROP-LCATS-PACKAGING-MODERNIZATION` is the
  originating request, already linked via `related_design`).
- Backlog: No matching entries (`project/design/backlog.md` doesn't exist
  in this repo).
- Recommendation: No action.

## Scope

- Edit `lcats/pyproject.toml`: add `setuptools-scm` to
  `build-system.requires`, switch `version` to `dynamic = ["version"]`,
  add `[tool.setuptools_scm]` with `fallback_version`.
- Cut the repo's first git tag.
- Delete `lcats/setup.py`.
- Reinstall editable and confirm the derived version reports correctly.

## Required Changes

1. `lcats/pyproject.toml`: add `"setuptools-scm"` to
   `build-system.requires`.
2. `lcats/pyproject.toml`: remove `version = "0.1"` from `[project]`, add
   `dynamic = ["version"]`.
3. `lcats/pyproject.toml`: add `[tool.setuptools_scm]` with
   `fallback_version = "0.1.0"` (matching
   `logical_robotics_harness`'s own `fallback_version = "0.0.0"` pattern,
   adjusted to reflect LCATS's prior static version).
4. Cut a first annotated git tag (e.g. `v0.1.0`) and push it — confirm
   with the user before pushing, since tagging affects shared repo state.
5. Delete `lcats/setup.py`.
6. From `lcats/` (the package root — the `egg-info` path is relative to
   it, matching the convention already used throughout `lcats/scripts/*`):
   `rm -rf src/lcats.egg-info && pip install -e ".[dev]"` in the `LCATS`
   conda env to regenerate against dynamic versioning.
7. Verify the installed version reflects the git tag: `pip show lcats` or
   `python -c "import importlib.metadata; print(importlib.metadata.version('lcats'))"`.

## Non-Goals

- Does not change `requires-python` or any runtime dependency.
- Does not modify CI workflow YAML.
- Does not touch `lcats/src/lcats/` package code.
- Does not establish a broader release/tagging cadence or changelog
  process — only the first tag needed to unblock `setuptools-scm`.

## Acceptance Criteria

- `lcats/pyproject.toml` declares `dynamic = ["version"]` and no longer
  has a static `version = "0.1"` field.
- `build-system.requires` includes `setuptools-scm`.
- A `[tool.setuptools_scm]` table exists with a `fallback_version` set,
  matching `logical_robotics_harness`'s own pattern.
- A first git tag (e.g. `v0.1.0`) exists on the repo, since none
  currently exist.
- `lcats/setup.py` no longer exists.
- `python -m pip install -e ".[dev]"` succeeds and reports a version
  derived from the git tag, not a hardcoded string.
- `lrh validate` reports 0 errors.

## Validation

- `lrh validate`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `python -m pip install -e ".[dev]"`
- `python -c "import importlib.metadata; print(importlib.metadata.version('lcats'))"`

## Risk Notes

- Cutting and pushing a git tag is a shared-state, harder-to-reverse
  action (unlike file edits on a branch) — confirm explicitly with the
  user before pushing, even though this WI's `expected_actions` covers
  it.
- `fallback_version` must be set so a tag-less checkout (e.g. a shallow
  CI clone, or a tarball) doesn't hard-fail the build — verify by testing
  an install after a fresh shallow clone if feasible, or at minimum
  confirm the fallback value is sane.
- Deleting `setup.py` outright (rather than gutting it) is safe per the
  proposal's Decision 3 — confirmed no other file in the repo invokes it
  directly.

## Related Workstream and Designs

- Workstream: `project/workstreams/proposed/WS-PACKAGING.md`
- Design: `project/design/proposals/proposed/lcats-packaging-modernization/00_proposal.md`
