---
resolution: null
blocked_reason: null
blocked: false
id: WI-PACKAGING-0036
title: Replace hardcoded parent-depth path counting with a pyproject.toml anchor
type: operation
status: proposed
owner: xenotaur
contributors:
  - xenotaur
assigned_agents: []
related_focus: []
related_roadmap: []
related_workstreams: []
related_design:
  - project/design/proposals/adopted/lcats-packaging-modernization/00_proposal.md
depends_on: []
blocked_by: []
expected_actions:
  - create_file
  - edit_file
  - run_tests
  - create_pr
forbidden_actions:
  - force_push
  - delete_branch
  - modify_ci_pipeline
acceptance:
  - lcats/src/lcats/utils/paths.py has a new helper that walks up from a starting file to find the directory containing pyproject.toml, raising a clear error if none is found
  - secrets.py's _DEFAULT_SECRETS_DIR uses the new helper instead of parents[4]
  - test_utils.py's TestCaseWithData.test_data_dir uses the new helper instead of ../../../tests/data
  - paths.py's own header comment is corrected (still says lcats/lcats/utils/paths.py, stale since the src-layout move)
  - the full test suite passes, confirming the anchor-based lookup resolves identically to the current hardcoded values
  - lrh validate reports 0 errors
required_evidence:
  - lrh_validate
  - test_output
artifacts_expected:
  - lcats/src/lcats/utils/paths.py
  - lcats/src/lcats/utils/secrets.py
  - lcats/src/lcats/utils/test_utils.py
---

## Summary

Replace the two hardcoded `parents[N]`/relative-path depth-counting
lookups in `secrets.py` and `test_utils.py` with a shared helper that
anchors on the presence of `pyproject.toml`, so a future package-layout
change can't silently break either one again the way the src-layout move
already did twice.

## Problem / Context

`WI-PACKAGING-0032`'s Non-Goals explicitly deferred this: "Does not
replace `secrets.py`'s parent-depth-counting pattern with a more robust
anchor-on-`pyproject.toml` approach... a proper fix is a candidate
follow-up per the proposal's Non-Goals." No work item was ever created
for it. During the same effort, `test_utils.py`'s `TestCaseWithData` was
found to have the identical fragility class (`../../../tests/data`,
discovered via the project's own grep-parent-depth-pattern lesson from
that effort), and was fixed with the same kind of one-line index bump
rather than the anchor approach — so this WI covers both, not just
`secrets.py`, since they're the same root cause.

### Duplication search
- In-repo: No existing repo-root/package-root-finder utility found
  (confirmed via grep across `lcats/src/lcats`).
- Sibling repos: None checked — this is LCATS-specific path-resolution
  logic.
- External libraries: None identified — a simple upward directory walk
  doesn't need a dependency.
- Recommendation: Proceed.

### Demand search
- Work items: None found.
- Proposals: None found (the deferral is a Non-Goals note in
  `WI-PACKAGING-0032`, not a separate request).
- Backlog: `project/design/backlog.md` doesn't exist in this repo.
- Recommendation: No action.

## Scope

- Add one shared helper to `lcats/src/lcats/utils/paths.py`.
- Update `secrets.py` and `test_utils.py` to use it instead of their
  current hardcoded depth/relative-path logic.
- Fix `paths.py`'s own stale header comment while touching the file.

## Required Changes

1. Add a function to `paths.py` (e.g. `find_pyproject_root(start=None)`)
   that walks up from a starting path looking for a `pyproject.toml`
   file, returning the containing directory, and raises a clear
   `FileNotFoundError`-style error if it walks off the filesystem root
   without finding one.
2. `secrets.py`: replace
   `pathlib.Path(__file__).resolve().parents[4] / ".secrets"` with
   `find_pyproject_root(__file__).parent / ".secrets"`, guarding the
   module-level assignment so a non-editable install (no `pyproject.toml`
   ancestor on disk) doesn't raise at import time — see Risk Notes.
3. `test_utils.py`: replace the `../../../tests/data` relative-path join
   with `find_pyproject_root(__file__) / "tests" / "data"`.
4. `paths.py`: correct the header comment path from
   `lcats/lcats/utils/paths.py` to `lcats/src/lcats/utils/paths.py`.
5. Run the full test suite to confirm both resolve to the same paths as
   before.

## Non-Goals

- Does not touch any other file's path-resolution logic beyond these
  two.
- Does not add a general-purpose "project root" concept beyond what
  these two call sites need.
- Does not modify CI workflow YAML.

## Acceptance Criteria

- `lcats/src/lcats/utils/paths.py` has a new helper that walks up from a
  starting file to find the directory containing `pyproject.toml`,
  raising a clear error if none is found.
- `secrets.py`'s `_DEFAULT_SECRETS_DIR` uses the new helper instead of
  `parents[4]`.
- `test_utils.py`'s `TestCaseWithData.test_data_dir` uses the new helper
  instead of `../../../tests/data`.
- `paths.py`'s own header comment is corrected (still says
  `lcats/lcats/utils/paths.py`, stale since the src-layout move).
- The full test suite passes, confirming the anchor-based lookup
  resolves identically to the current hardcoded values.
- `lrh validate` reports 0 errors.

## Validation

- `lrh validate`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `python -c "from lcats.utils.secrets import _DEFAULT_SECRETS_DIR; print(_DEFAULT_SECRETS_DIR)"`
- A non-editable install check: `pip install .` (not `-e`) into a
  throwaway venv outside the checkout, then confirm
  `import lcats.utils.secrets` succeeds and `load_secrets()` still
  no-ops rather than raising.

## Risk Notes

- The new helper must correctly handle both editable-install and
  non-editable-install cases — verify with an actual non-editable install
  (e.g. `pip install .` into a separate venv, or a built wheel), not just
  `pip install -e .`.
- `secrets.py`'s `_DEFAULT_SECRETS_DIR` is computed at module import time.
  A wheel or `pip install .` install outside the checkout has no
  `pyproject.toml` ancestor on disk, so calling `find_pyproject_root`
  unguarded at module scope would raise `FileNotFoundError` on every
  `import lcats.utils.secrets` — breaking `load_secrets()` entirely,
  including calls that pass an explicit `secrets_dir=...` and don't need
  the default at all. Today's behavior is a silent no-op when
  `.secrets/` doesn't exist (see `load_secrets`'s docstring); the fallback
  must preserve that: catch the "not found" case at import time and set
  `_DEFAULT_SECRETS_DIR` to `None` (or similar), so `load_secrets()`
  continues to no-op gracefully in non-editable installs instead of
  failing to import.
- Keep the walk-up bounded (stop at filesystem root) so a misconfigured
  environment fails loudly with a clear error only when the lookup is
  actually invoked with no explicit override — not as an import-time
  side effect.

## Related Workstream and Designs

- Design:
  `project/design/proposals/adopted/lcats-packaging-modernization/00_proposal.md`
  (the closed effort that deferred this)
- Not linked to any workstream — `WS-PACKAGING` is closed and this is
  out-of-band cleanup, following the same pattern as `WI-PACKAGING-0034`.
