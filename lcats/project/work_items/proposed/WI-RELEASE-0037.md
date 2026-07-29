---
resolution: null
blocked_reason: null
blocked: false
id: WI-RELEASE-0037
title: Resolve gutenbergpy VCS-pin PyPI-publish blocker
type: deliverable
status: proposed
owner: xenotaur
contributors:
  - xenotaur
assigned_agents: []
related_focus: []
related_roadmap: []
related_workstreams: []
related_design: []
depends_on: []
blocked_by: []
expected_actions:
  - edit_file
  - create_file
  - run_tests
  - create_pr
forbidden_actions:
  - force_push
  - delete_branch
  - publish_package
  - modify_ci_pipeline
acceptance:
  - A documented decision (vendor the fix vs. publish/maintain a distinct-named LCATS-controlled PyPI fork vs. wait on upstream) exists with rationale, including why "wait on upstream" is or isn't viable given no ETA
  - lcats/pyproject.toml's gutenbergpy dependency (currently lcats/pyproject.toml:26, a git+https direct reference) no longer contains a git+https or other direct URL reference
  - lcats/environment.yml's matching gutenbergpy pin (currently environment.yml:263, the identical git+https reference) is updated to match whichever replacement was chosen, so the documented conda environment no longer installs the old fork
  - If vendoring - the alias-table/title-index logic from raduangelescu/gutenbergpy PR #26 is present in lcats/src/lcats/gettenberg/ with clear attribution/comment pointing at the upstream PR, accompanied by a new regression test that exercises the real parser/cache-writer path (not the mocked/fake-row paths in cache_test.py and metadata_test.py) and asserts on resulting title associations and alias tables
  - If re-fork-and-publish - a distinct PyPI project name is reserved and, once published via a separate prerequisite work item (this item's own forbidden_actions bars publish_package), lcats/pyproject.toml pins it by version, not URL
  - lcats/src/lcats/gettenberg/ tests, including the new regression test for the vendoring path, pass unchanged in behavior after the change
  - A built wheel's metadata contains no direct URL/VCS reference (verified via twine check and metadata inspection)
  - lrh validate reports 0 errors
required_evidence:
  - manual_review
  - lrh_validate
  - test_output
artifacts_expected:
  - lcats/pyproject.toml
  - lcats/environment.yml
  - lcats/src/lcats/gettenberg/
---

## Summary

Resolve `lcats/pyproject.toml:26`'s `gutenbergpy @ git+https://github.com/xenotaur/gutenbergpy.git@60ca548...`
dependency so LCATS's distributed package metadata contains no direct
URL/VCS reference — a hard PyPI-publish blocker independent of any other
release-readiness work.

## Problem / Context

LCATS depends on two fixes (alias tables, title-index correction) that were
merged upstream into `raduangelescu/gutenbergpy:master` via
[PR #25](https://github.com/raduangelescu/gutenbergpy/pull/25) and
[PR #26](https://github.com/raduangelescu/gutenbergpy/pull/26), both
authored by `xenotaur`. However, the published `gutenbergpy` PyPI package
is still 0.3.5 (released 2023-03-27), predating that merge — there is no
PyPI release containing the needed fixes, and no ETA for one, since
cutting a release is the upstream maintainer's call, not LCATS's. As
currently pinned, LCATS cannot be uploaded to PyPI with this dependency.
This blocks any real (non-placeholder) PyPI release regardless of how the
rest of release-readiness work proceeds.

### Duplication search
- In-repo: No existing implementation or decision record found (grepped
  `lcats/src/`, `lcats/project/design/proposals/` for `gutenbergpy`;
  `.claude/skills/` does not exist in this repo, so it was skipped
  rather than searched. Only hits in the searched paths were unrelated
  design/execution docs referencing the dependency in passing).
- Sibling repos: None identified — this is LCATS-specific.
- External libraries: None identified as an alternative; the two
  realistic paths are vendoring the small diff or publishing a
  maintained fork.
- Recommendation: Proceed.

### Demand search
- Work items: None found.
- Proposals: None found.
- Backlog: No `project/design/backlog.md` in this repo.
- Recommendation: No action.

## Scope

- Decide among: (a) wait for upstream to cut a new PyPI release, (b)
  vendor the merged diff directly into `lcats/src/lcats/gettenberg/`,
  (c) publish and maintain a distinct-named LCATS-controlled PyPI fork.
- Update `lcats/pyproject.toml`'s and `lcats/environment.yml`'s
  dependency declarations to remove the direct VCS reference, per
  whichever path is chosen.
- If vendoring, add a real (non-mocked) regression test covering the
  ported parser/cache-writer logic.
- If re-fork-and-publish, scope the fork's actual PyPI publish as a
  separate prerequisite work item rather than performing it here.
- Verify existing Gutenberg-fetching functionality is unaffected.

## Required Changes

1. Record the decision and rationale (in this work item's Problem/Context
   or its execution record).
2. Update `lcats/pyproject.toml:26`'s `gutenbergpy` dependency
   accordingly. Also update `lcats/environment.yml:263`, which pins the
   identical `gutenbergpy @ git+https://...` reference for the conda
   development environment — leaving it unchanged would mean
   contributors recreating the documented conda environment continue
   pulling the old fork commit, and tests run in that environment could
   mask a broken vendored or PyPI dependency.
3. If vendoring: port the alias-table/title-fix logic into
   `lcats/src/lcats/gettenberg/`, with a comment attributing it to the
   upstream PR, and stop depending on any gutenbergpy fork/commit for
   that behavior. Add a real parser/cache-writer regression test
   alongside the port — `tests/gettenberg_tests/cache_test.py` mocks
   `GutenbergCache.create` and `metadata_test.py` injects fake query
   rows via `_FakeCache`, so rerunning the existing suite alone cannot
   demonstrate the ported alias-table/title logic is actually correct;
   an incomplete port could satisfy "tests pass unchanged" while newly
   built caches remain wrong. Per `AGENTS.md`'s mocking/test philosophy
   ("avoid heavy mocking... validate behavior, not that mocks were
   called"), the new test should exercise the real parsing/cache-write
   path and assert on the resulting title associations and alias
   tables, not a mocked stand-in.
4. If forking-and-publishing: reserve a distinct PyPI project name.
   This work item's `forbidden_actions` includes `publish_package`
   (scoped to `lcats` itself, the actual release blocker this item
   exists to unblock) — so the fork's own publish is out of scope for
   this item regardless of which path is chosen; if re-fork-and-publish
   is selected, scope the fork's publish as an explicit, separate
   prerequisite work item rather than performing it inline here.
5. Run `lcats/src/lcats/gettenberg/`'s test suite, including the new
   regression test from step 3, to confirm no behavior regression.

## Non-Goals

- Does not implement the full LCATS PyPI publish workflow or CI
  changes — separate future work.
- Does not update `README.md:33`'s stale "not yet supported" claim —
  separate item.
- Does not build `scripts/version`/release-smoke tooling — that's
  WI-RELEASE-0038.
- Does not actually publish `lcats` to PyPI.

## Acceptance Criteria

- A documented decision (vendor the fix vs. publish/maintain a
  distinct-named LCATS-controlled PyPI fork vs. wait on upstream) exists
  with rationale, including why "wait on upstream" is or isn't viable
  given no ETA.
- `lcats/pyproject.toml`'s gutenbergpy dependency (currently
  `lcats/pyproject.toml:26`, a git+https direct reference) no longer
  contains a git+https or other direct URL reference.
- `lcats/environment.yml`'s matching gutenbergpy pin (currently
  `environment.yml:263`) is updated to the same replacement, so the
  documented conda environment doesn't silently keep installing the old
  fork.
- If vendoring: the alias-table/title-index logic from
  `raduangelescu/gutenbergpy` PR #26 is present in
  `lcats/src/lcats/gettenberg/` with clear attribution/comment pointing
  at the upstream PR, and a new regression test exercises the real
  parser/cache-writer path (not the mocked `GutenbergCache.create` or
  fake-row `_FakeCache` paths already in the suite) and asserts on the
  resulting title associations and alias tables.
- If re-fork-and-publish: a distinct PyPI project name is reserved (not
  `gutenbergpy`, to avoid squatting the upstream maintainer's
  namespace); the actual publish is scoped as a separate prerequisite
  work item, consistent with this item's own `forbidden_actions:
  publish_package`; once published, `lcats/pyproject.toml` pins it by
  version, not URL.
- `lcats/src/lcats/gettenberg/` tests, including the new regression
  test where applicable, pass unchanged in behavior after
  the change.
- A built wheel's metadata contains no direct URL/VCS reference
  (verified via `twine check` and metadata inspection).
- `lrh validate` reports 0 errors.

## Validation

- `lrh validate`
- `scripts/test`
- `scripts/build && twine check dist/*`
- `for whl in dist/*.whl; do unzip -p "$whl" '*.dist-info/METADATA'; done | grep -i gutenbergpy` (confirm no `git+`/URL reference remains; loops so multiple wheels in `dist/` are each checked, not just the first)

## Risk Notes

- Vendoring permanently diverges LCATS's copy from upstream; future
  upstream fixes must be manually re-ported.
- A separate LCATS-controlled PyPI fork adds an ongoing maintenance and
  security surface (a second package to keep current).
- "Wait on upstream" has no ETA and, left unresolved, blocks the real
  release indefinitely — list explicitly as a considered-and-likely-
  rejected option, not silently dropped.
