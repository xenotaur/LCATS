---
resolution: null
blocked_reason: null
blocked: false
id: WI-PACKAGING-0034
title: Fix and document environment.yml and pre-commit tool-version drift
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
  - project/design/proposals/proposed/lcats-packaging-modernization/00_proposal.md
depends_on:
  - WI-PACKAGING-0031
blocked_by: []
expected_actions:
  - edit_file
  - run_tests
  - create_pr
forbidden_actions:
  - force_push
  - delete_branch
  - modify_ci_pipeline
acceptance:
  - lcats/environment.yml's setuptools pin matches or exceeds pyproject.toml's setuptools>=77 floor
  - lcats/environment.yml's gutenbergpy pin reflects the commit-SHA-pinned fork from pyproject.toml, not the stale PyPI 0.3.6 release
  - a comment or doc note explains scripts/update's behavior (exports whichever conda env is active) so a future contributor doesn't regenerate a stale environment.yml by running it against the wrong env
  - the pre-commit black hook's tagless-clone version-misreport issue is documented (e.g. in .pre-commit-config.yaml's header comment or CONTRIBUTING-equivalent doc), explaining why scripts/*'s validation, not the local black hook, is authoritative
  - lrh validate reports 0 errors
required_evidence:
  - lrh_validate
  - test_output
artifacts_expected:
  - lcats/environment.yml
  - .pre-commit-config.yaml
---

## Summary

Fix the confirmed drift between `lcats/environment.yml` and
`pyproject.toml` (stale `setuptools=72.1.0`/`gutenbergpy==0.3.6` pins), and
document two gotchas discovered during `WI-PACKAGING-0031`: `scripts/update`'s
active-env-dependent regeneration behavior, and the pre-commit `black`
hook's tagless-clone version bug.

## Problem / Context

`WI-PACKAGING-0031` (implemented via PR #173, execution record
`project/executions/WI-PACKAGING-0031/2026_07_27_22_00_05_WI_PACKAGING_0031.md`)
raised `lcats/pyproject.toml`'s `setuptools` floor to `>=77` and pinned
`gutenbergpy` to a commit SHA of the `xenotaur/gutenbergpy` fork. During
that work, `lcats/environment.yml` was found to still pin
`setuptools=72.1.0` and `gutenbergpy==0.3.6` (the stale PyPI release), both
now inconsistent with `pyproject.toml`. Separately, that PR's own commit
was made with `--no-verify` because the pre-commit `black` hook
self-reports a bogus `0.1.dev1+g...` version regardless of the correct
`rev:` pin — root-caused to `git describe --tags` finding no tags inside
pre-commit's own (tagless) clone of `psf/black`, a documented pre-commit +
`setuptools_scm` interaction, not fixable via `.pre-commit-config.yaml`
alone. Both gaps were deferred to this follow-up WI per explicit user
direction during that session.

### Duplication search
- In-repo: No existing implementation found.
- Sibling repos: None identified — this is LCATS-specific environment
  tooling.
- External libraries: None identified.
- Recommendation: Proceed.

### Demand search
- Work items: None found.
- Proposals: None found.
- Backlog: No matching entries.
- Recommendation: No action.

## Scope

- Update the `LCATS` conda env's installed `setuptools`/`gutenbergpy` to
  match `pyproject.toml`'s current pins, then regenerate
  `lcats/environment.yml` to reflect that.
- Add a short doc note near `scripts/update` and/or in `environment.yml`
  itself explaining that regeneration exports whichever conda env is
  currently active — so a future contributor doesn't silently re-export
  stale state by running it in the wrong env.
- Document the pre-commit `black` hook's tagless-clone version-misreport
  limitation, and reaffirm that CI/`scripts/*` remain authoritative.

## Required Changes

1. Activate the `LCATS` conda env (`~/anaconda3/envs/LCATS`) and run
   `scripts/develop` (`pip install -e ".[dev]"`) to pull in the updated
   `setuptools>=77` and commit-SHA-pinned `gutenbergpy` from
   `pyproject.toml`.
2. Run `scripts/update` (`conda env export | egrep -v "^name:" | egrep -v
   "^prefix:" > environment.yml`) from that same activated env to
   regenerate `lcats/environment.yml`.
3. Review the resulting diff — `conda env export` can pull in unrelated
   version bumps beyond `setuptools`/`gutenbergpy`; confirm nothing
   unexpected or overly broad is introduced before committing.
4. Add a short comment (in `lcats/scripts/update` and/or as a header note
   in `lcats/environment.yml`) documenting that regeneration reflects
   whichever conda env is active at run time, not necessarily the
   project's intended env.
5. Add a note to `.pre-commit-config.yaml`'s existing header comment (or an
   adjacent doc) explaining the black hook's tagless-clone version-misreport
   limitation and why `--no-verify` may be legitimate for that specific
   hook when CI/`scripts/*` already pass.

## Non-Goals

- Does not touch `lcats/pyproject.toml` again — already fixed in
  `WI-PACKAGING-0031`.
- Does not attempt to fix pre-commit's own upstream tagless-clone
  behavior, or vendor/patch `psf/black`'s pre-commit hook — documented as
  outside LCATS's control.
- Does not regenerate `environment.yml` for unrelated package updates
  beyond what's needed to align `setuptools`/`gutenbergpy` — if the conda
  env has other drifted packages, note them but don't silently bundle
  unrelated bumps into this PR.
- Does not modify `.github/workflows/*.yml` — CI already correctly pins
  `ruff==0.15.0`/`black==25.11.0` independently of `environment.yml`.

## Acceptance Criteria

- `lcats/environment.yml`'s `setuptools` pin matches or exceeds
  `pyproject.toml`'s `setuptools>=77` floor.
- `lcats/environment.yml`'s `gutenbergpy` pin reflects the
  commit-SHA-pinned fork from `pyproject.toml`, not the stale PyPI
  `0.3.6` release.
- A comment or doc note explains `scripts/update`'s behavior (exports
  whichever conda env is active) so a future contributor doesn't
  regenerate a stale `environment.yml` by running it against the wrong
  env.
- The pre-commit `black` hook's tagless-clone version-misreport issue is
  documented (e.g. in `.pre-commit-config.yaml`'s header comment or
  equivalent), explaining why `scripts/*`'s validation, not the local
  black hook, is authoritative.
- `lrh validate` reports 0 errors.

## Validation

- `lrh validate`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `git diff lcats/environment.yml` reviewed manually for unexpected scope

## Risk Notes

- `conda env export` captures the entire environment state, not just the
  two packages in scope — review the diff carefully before committing to
  avoid bundling unrelated, unreviewed version bumps.
- Regenerating `environment.yml` from the wrong conda env (e.g. `base`
  instead of `LCATS`) would silently reintroduce or worsen the drift this
  WI exists to fix — confirm `which python` / `conda info --envs` shows
  `LCATS` as active before running `scripts/update`.

## Related Workstream and Designs

- Design: `project/design/proposals/proposed/lcats-packaging-modernization/00_proposal.md`
- Related execution record: `project/executions/WI-PACKAGING-0031/2026_07_27_22_00_05_WI_PACKAGING_0031.md`
