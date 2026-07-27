---
resolution: null
blocked_reason: null
blocked: false
id: WI-PACKAGING-0032
title: Move lcats package from lcats/lcats/ to lcats/src/lcats/ (src-layout)
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
  - WI-PACKAGING-0031
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
  - implement_lcats_setuptools_scm_versioning
  - modify_ci_pipeline
acceptance:
  - lcats/lcats/ no longer exists; the package lives at lcats/src/lcats/ with the same module contents
  - lcats/pyproject.toml has [tool.setuptools] package-dir = {"" = "src"} and [tool.setuptools.packages.find] where = ["src"]
  - lcats/scripts/lint and lcats/scripts/format default targets reference src instead of lcats
  - lcats/src/lcats/utils/secrets.py's parents[N] depth count is updated for the new path depth and still resolves .secrets/ at the repo root
  - lcats/src/lcats/utils/test_utils.py's TestCaseWithData test_data_dir calculation is updated for the new path depth and still resolves lcats/tests/data, not lcats/src/tests/data
  - .pre-commit-config.yaml, lcats/tools/sourcetree_surveyor.py, lcats/tools/create_request.py, experiments/02_llm_backend_comparison/run_comparison.py, and experiments/03_cross_segment_relation_pilot/run_pilot.py are audited for lcats/lcats path literals or sys.path bootstraps, and updated to point at lcats/src where they assumed the old layout
  - python -m pip install -e ".[dev]" succeeds from lcats/ against the new layout
  - the full test suite (scripts/test) passes against the new layout
  - lrh validate reports 0 errors
required_evidence:
  - lrh_validate
  - test_output
artifacts_expected:
  - lcats/src/lcats/
  - lcats/pyproject.toml
  - lcats/scripts/lint
  - lcats/scripts/format
  - lcats/src/lcats/utils/secrets.py
  - lcats/src/lcats/utils/test_utils.py
  - .pre-commit-config.yaml
  - lcats/tools/sourcetree_surveyor.py
  - lcats/tools/create_request.py
  - experiments/02_llm_backend_comparison/run_comparison.py
  - experiments/03_cross_segment_relation_pilot/run_pilot.py
---

## Summary

Move the `lcats` Python package from the flat-layout `lcats/lcats/` to the
PyPA-recommended src-layout `lcats/src/lcats/`, as Phase 2 of
`WS-PACKAGING`, updating every dependent script/tool/experiment path along
the way. No metadata or versioning changes.

## Problem / Context

`PROP-LCATS-PACKAGING-MODERNIZATION` (merged via PR #159) identified
LCATS's flat package layout as carrying the import-shadowing risk PyPA's
own guidance warns against; `WS-PACKAGING` (merged via PR #160) sequences
this as Phase 2, after Phase 1's tool-version self-enforcement
(`WI-PACKAGING-0031`) lands, so lint/format skew is caught immediately if
this move introduces any. This item must not begin implementation before
`WI-PACKAGING-0031` is resolved, per the workstream's documented ordering
constraint — encoded here via `depends_on`.

### Duplication search
- In-repo: No existing implementation found.
- Sibling repos: `logical_robotics_harness/src/lrh` already uses
  src-layout — reference, not duplicate.
- External libraries: None identified — this is project packaging
  structure.
- Recommendation: Proceed.

### Demand search
- Work items: None found (`WI-PACKAGING-0031` is the sibling Phase 1 item,
  not a duplicate of this Phase 2 scope).
- Proposals: None found (`PROP-LCATS-PACKAGING-MODERNIZATION` is the
  originating request, already linked via `related_design`).
- Backlog: No matching entries.
- Recommendation: No action.

## Scope

- Move `lcats/lcats/` → `lcats/src/lcats/` (preserve git history via
  `git mv`).
- Update `lcats/pyproject.toml`'s package-discovery config.
- Update every dependent script, tool, and experiment path identified in
  the proposal's confirmed blast-radius audit.
- Reinstall editable and run the full test suite to confirm nothing broke.

## Required Changes

1. `git mv lcats/lcats lcats/src/lcats`.
2. `lcats/pyproject.toml`: add
   `[tool.setuptools] package-dir = {"" = "src"}` and
   `[tool.setuptools.packages.find] where = ["src"]`.
3. `lcats/scripts/lint` and `lcats/scripts/format`: change default target
   list from `(lcats tests tools)` to `(src tests tools)`.
4. `lcats/src/lcats/utils/secrets.py`: update the `parents[N]` depth-count
   comment and index (shifts by one level since the package moved one
   directory deeper).
5. `lcats/src/lcats/utils/test_utils.py`: `TestCaseWithData.setUp`'s
   `os.path.join(os.path.dirname(__file__), "../../tests/data")`
   calculation resolves to `lcats/src/tests/data` after the move instead of
   the actual `lcats/tests/data` — update the relative path (or the
   depth-counting approach) so `test_data_dir` still resolves correctly.
   Numerous tests inherit `TestCaseWithData`, so this must be fixed before
   the full test run in step 8 can pass.
6. Audit and update `.pre-commit-config.yaml`,
   `lcats/tools/sourcetree_surveyor.py`, `lcats/tools/create_request.py`
   for `lcats/lcats` path literals.
7. Update `experiments/02_llm_backend_comparison/run_comparison.py` and
   `experiments/03_cross_segment_relation_pilot/run_pilot.py`'s
   `sys.path.insert(0, ... / "lcats")` bootstraps to point at
   `.../lcats/src` instead.
8. `rm -rf lcats/lcats.egg-info && python -m pip install -e ".[dev]"` from
   `lcats/` to regenerate the editable install against the new layout.
9. Run `scripts/test` and confirm the full suite passes.

## Non-Goals

- Does not add `setuptools-scm` or change `version = "0.1"` — that is
  Phase 3 (the next work item).
- Does not remove `lcats/setup.py` — also Phase 3.
- Does not modify CI workflow YAML — `working-directory: lcats` in
  `tests.yml`/`coverage.yml`/`lint.yml` already treats `lcats/` as project
  root regardless of internal layout, confirmed in the proposal.
- Does not replace `secrets.py`'s parent-depth-counting pattern with a
  more robust anchor-on-`pyproject.toml` approach — only the one-line
  index bump needed for the new depth; a proper fix is a candidate
  follow-up per the proposal's Non-Goals.
- Does not touch any file outside the audited blast-radius list without
  first confirming it's actually affected.

## Acceptance Criteria

- `lcats/lcats/` no longer exists; the package lives at `lcats/src/lcats/`
  with the same module contents.
- `lcats/pyproject.toml` has
  `[tool.setuptools] package-dir = {"" = "src"}` and
  `[tool.setuptools.packages.find] where = ["src"]`.
- `lcats/scripts/lint` and `lcats/scripts/format` default targets
  reference `src` instead of `lcats`.
- `lcats/src/lcats/utils/secrets.py`'s `parents[N]` depth count is updated
  for the new path depth and still resolves `.secrets/` at the repo root.
- `lcats/src/lcats/utils/test_utils.py`'s `TestCaseWithData` `test_data_dir`
  calculation is updated for the new path depth and still resolves
  `lcats/tests/data`, not `lcats/src/tests/data`.
- `.pre-commit-config.yaml`, `lcats/tools/sourcetree_surveyor.py`,
  `lcats/tools/create_request.py`,
  `experiments/02_llm_backend_comparison/run_comparison.py`, and
  `experiments/03_cross_segment_relation_pilot/run_pilot.py` are audited
  for `lcats/lcats` path literals or `sys.path` bootstraps, and updated to
  point at `lcats/src` where they assumed the old layout.
- `python -m pip install -e ".[dev]"` succeeds from `lcats/` against the
  new layout.
- The full test suite (`scripts/test`) passes against the new layout.
- `lrh validate` reports 0 errors.

## Validation

- `lrh validate`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `python -m pip install -e ".[dev]"`
- `python -c "import lcats; print(lcats.__file__)"`

## Risk Notes

- The `experiments/*/run_*.py` `sys.path` bootstraps are easy to miss
  since they're outside `lcats/` entirely — the proposal's review cycle
  already caught this once; double-check both files specifically before
  calling this item done.
- `secrets.py` and `test_utils.py` both hardcode `parents[N]`/relative-path
  depth counts that pass review by inspection but fail at runtime — verify
  each by actually invoking a code path that reads `.secrets/` and by
  running the full test suite (not just reading the diff), since
  `test_utils.py`'s bug specifically only surfaces when tests that inherit
  `TestCaseWithData` try to load fixture data.
- Deleting `lcats/lcats.egg-info` before reinstalling is safe (it's
  untracked/gitignored, confirmed during the design phase), but skipping
  that step risks a stale editable-install pointing at the old path.

## Related Workstream and Designs

- Workstream: `project/workstreams/proposed/WS-PACKAGING.md`
- Design: `project/design/proposals/proposed/lcats-packaging-modernization/00_proposal.md`
