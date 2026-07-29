---
resolution: "Implemented and merged in PR #183 (commit 2cc85d07)."
blocked_reason: null
blocked: false
id: WI-RELEASE-0038
title: Add lcats.version module, --version CLI flag, and scripts/version release helper
type: deliverable
status: resolved
owner: xenotaur
contributors:
  - xenotaur
assigned_agents: []
related_focus: []
related_roadmap: []
related_workstreams: []
related_design:
  - project/design/proposals/proposed/lcats-pypi-release-readiness/00_proposal.md
depends_on: []
blocked_by: []
expected_actions:
  - create_file
  - edit_file
  - run_tests
  - create_pr
  - add_cli_command
forbidden_actions:
  - force_push
  - delete_branch
  - publish_package
  - modify_ci_pipeline
acceptance:
  - lcats/src/lcats/version.py exists with get_installed_version()/format_cli_version(), mirroring lrh.version's shape
  - lcats --version prints installed package version via importlib.metadata, not a hardcoded string
  - scripts/version tools prints lcats package/CLI version plus toolchain versions (python, ruff, black, pip)
  - scripts/version verify [tag] validates tag format (if given), requires a clean working tree, and runs scripts/lint, scripts/format --check, scripts/test
  - scripts/version tag <tag> and scripts/version push <tag> create/push a git tag idempotently, mirroring lrh.dev.versioning's tag/push behavior
  - lrh validate reports 0 errors
required_evidence:
  - manual_review
  - lrh_validate
  - test_output
artifacts_expected:
  - lcats/src/lcats/version.py
  - lcats/src/lcats/dev/versioning.py
  - lcats/scripts/version
  - lcats/src/lcats/cli.py
---

## Summary

Give LCATS a `lcats.version` module, a `lcats --version` CLI flag, and a
`scripts/version` helper (`tools`/`verify`/`tag`/`push`), mirroring LRH's
`lrh.dev.versioning` pattern but scoped to what LCATS's own
`scripts/lint`/`scripts/format`/`scripts/test` actually support.

## Problem / Context

LCATS currently has no way to answer "what version is this
checkout/install?" — no `--version` flag on the CLI (confirmed via grep
on `lcats/src/lcats/cli.py`, no hits for `version`) and no `lcats.version`
module. The one existing tag, `v0.1.0`, was cut by hand with no tooling
behind it, unlike LRH's `scripts/version` which gates tagging behind a
clean-tree + lint/format/test check. This gap was identified while
comparing LCATS's packaging tooling against LRH's `scripts/version`/
`lrh.dev.versioning`
(`logical_robotics_harness/src/lrh/dev/versioning.py`) during a
release-readiness assessment session.

### Duplication search
- In-repo: No existing version-reporting module or `--version` flag
  found (grepped `src/lcats/cli.py` and `src/` broadly).
- Sibling repos: LRH's `lrh.dev.versioning` is the direct model, not a
  duplicate — LCATS has no equivalent.
- External libraries: None needed; `importlib.metadata` (stdlib) is
  sufficient, matching LRH's approach.
- Recommendation: Proceed.

### Demand search
- Work items: None found.
- Proposals: None found.
- Backlog: No `project/design/backlog.md` in this repo.
- Recommendation: No action.

## Scope

- `lcats/src/lcats/version.py` — `importlib.metadata`-based version
  helpers.
- `--version` flag on the `lcats` CLI.
- `lcats/src/lcats/dev/versioning.py` + `lcats/scripts/version` wrapper,
  supporting `tools`, `verify [tag]`, `tag <tag>`, `push <tag>`.

## Required Changes

1. Create `lcats/src/lcats/version.py` with `DISTRIBUTION_NAME =
   "lcats"`, `get_installed_version()`, `format_cli_version()`.
2. Add a `--version` flag to `lcats/src/lcats/cli.py`'s argument parser,
   printing `format_cli_version()`.
3. Create `lcats/src/lcats/dev/versioning.py` with `tools`/`verify`/
   `tag`/`push` subcommands, scoped to LCATS's actual toolchain
   (`scripts/lint`, `scripts/format --check`, `scripts/test` all exist
   and are the right checks to run for `verify`).
4. Create `lcats/scripts/version`, a thin bash wrapper matching the
   shape of `scripts/build`/`scripts/lint` (set `PYTHONPATH`, invoke
   `python -m lcats.dev.versioning "$@"`).

## Non-Goals

- Does not implement `scripts/release-smoke` — deferred, likely a
  near-term follow-up once this and WI-RELEASE-0037 land, but out of
  scope here.
- Does not modify CI workflows.
- Does not write the release runbook doc.
- Does not change `scripts/publish`'s current stub behavior.

## Acceptance Criteria

- `lcats/src/lcats/version.py` exists with
  `get_installed_version()`/`format_cli_version()`, mirroring
  `lrh.version`'s shape.
- `lcats --version` prints installed package version via
  `importlib.metadata`, not a hardcoded string.
- `scripts/version tools` prints lcats package/CLI version plus
  toolchain versions (python, ruff, black, pip).
- `scripts/version verify [tag]` validates tag format (if given),
  requires a clean working tree, and runs `scripts/lint`,
  `scripts/format --check`, `scripts/test`.
- `scripts/version tag <tag>` and `scripts/version push <tag>`
  create/push a git tag idempotently, mirroring
  `lrh.dev.versioning`'s `tag`/`push` behavior.
- `lrh validate` reports 0 errors.

## Validation

- `lrh validate`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `scripts/version tools`
- `scripts/version verify`
- `lcats --version`

## Risk Notes

- `scripts/version verify <tag>` must not be run with a real tag against
  `v0.1.0`'s existing history in a way that could confuse it with a new
  release attempt — keep `verify`'s tag argument optional-and-inert
  (validation only, no side effects) as LRH's does.
- Keep `tools`'s toolchain list matched to what LCATS actually pins
  (`ruff==0.15.0`, `black==25.11.0` per `pyproject.toml`) rather than
  copying LRH's list wholesale (e.g. LRH checks `pylint`/`pyright`,
  which LCATS's `dev` extras don't include).

## Dependencies / Order

Independent of `WI-RELEASE-0037` — this item's tooling doesn't need the
gutenbergpy dependency question resolved, and can proceed in parallel.
Both are precursors to a future `/lrh-proposal` + `/lrh-workstream` for
the real LCATS PyPI release.
