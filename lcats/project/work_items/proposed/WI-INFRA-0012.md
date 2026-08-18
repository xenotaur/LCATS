---
resolution: null
blocked_reason: null
blocked: false
id: WI-INFRA-0012
title: Verify nbstripout pre-commit hook actually strips notebook output
type: operation
status: proposed
owner: unassigned
contributors: []
assigned_agents: []
related_focus: []
related_roadmap: []
related_workstreams: []
related_design: []
depends_on: []
blocked_by: []
expected_actions:
  - run_tests
  - edit_file
forbidden_actions:
  - force_push
  - delete_branch
acceptance:
  - "pre-commit is installed and `pre-commit install` succeeds in this repo"
  - "`pre-commit run nbstripout --all-files` runs against lcats/notebooks/*.ipynb and reports its actual pass/fail/modified result, not assumed"
  - "A notebook with a deliberately-added cell output (e.g. a harmless print()) is staged and committed; the hook is confirmed to strip that output before the commit completes, or to block the commit until it's stripped"
  - "If the local hook does not work as configured, .pre-commit-config.yaml is fixed and the above is re-verified"
  - "A CI check is added (e.g. to .github/workflows/lint.yml) that fails if any lcats/notebooks/*.ipynb file carries cell output, per this repo's own stated convention that CI, not local pre-commit, is authoritative (lcats/README.md: 'Pre-commit is OPTIONAL. CI is authoritative.') - a contributor who never installs the local hook must not be able to merge a notebook with leaked output undetected"
  - "Outcome (works / didn't work and was fixed / didn't work and why) is documented in lcats/docs/secrets-setup.md, replacing its current unverified caveat"
required_evidence:
  - manual_review
  - validation_output
artifacts_expected:
  - .pre-commit-config.yaml
  - .github/workflows/lint.yml
  - lcats/docs/secrets-setup.md
---

# Work Item: WI-INFRA-0012

## Summary

Verify, end-to-end, that the `nbstripout` pre-commit hook added in PR #315
(`.pre-commit-config.yaml`) actually strips saved cell output from
`lcats/notebooks/*.ipynb` before a commit completes, and add a CI-level
check so this protection does not depend on every contributor having
installed the local hook. The hook was added as the intended backstop
against a repeat of the incident documented in
`lcats/docs/how-to/secrets-hygiene.md` — a live OpenAI key leaked via saved
notebook cell output — but was never run, because `pre-commit` wasn't
installed in the environment that authored it. The YAML was validated for
syntax only.

## Problem / Context

PR #315 added `.pre-commit-config.yaml`'s `nbstripout` hook, scoped to
`lcats/notebooks/*.ipynb`, and carved that path out of the file's global
`exclude` pattern so the hook could reach it. The commit message for that
change explicitly flags it as unverified. An unverified backstop is not a
backstop — if the hook is silently misconfigured (wrong `files:` pattern,
hook not actually installed by contributors, version pin issue), the next
raw-key-in-output leak would recur exactly as before, with everyone
believing it's covered.

A second, independent gap was caught during PR #316's own review (Codex,
P1): `lcats/README.md` explicitly states "Pre-commit is OPTIONAL. CI is
authoritative," and this item's original scope excluded CI enforcement.
Under that scope, the item could pass every acceptance criterion while a
contributor who simply never ran `pre-commit install` still commits a
notebook with leaked output straight to `main`, undetected — the exact
failure mode this item exists to close. Scope is expanded accordingly: a
CI-level check is now in scope, not deferred as a Non-Goal.

### Duplication search

In-repo: no existing work item covers this; the three `WI-PACKAGING-*`
items touching `.pre-commit-config.yaml` (`WI-PACKAGING-0031`,
`WI-PACKAGING-0032`, `WI-PACKAGING-0034`) are about `black`/`ruff` version
drift and path fixes, unrelated to `nbstripout`. Sibling repos / external
libraries: not applicable — this is a single-repo config verification.
Recommendation: proceed.

### Demand search

No open work item or proposal requests this; it originates directly from
PR #315's own self-flagged caveat, not a separately-tracked backlog entry.
Recommendation: proceed.

## Scope

- Install `pre-commit` and run it against this repo.
- Confirm `nbstripout` actually fires on `lcats/notebooks/*.ipynb` and
  actually strips output (not just "hook ran, exit 0" — check the file
  content before/after).
- Fix `.pre-commit-config.yaml` if it doesn't work as intended.
- Add a CI check that independently verifies no notebook under
  `lcats/notebooks/` carries cell output, so protection does not depend on
  local hook installation.
- Update `lcats/docs/secrets-setup.md`'s caveat with the real, verified
  outcome.

## Required Changes

1. **`.pre-commit-config.yaml`**: fix only if verification finds the local
   hook doesn't work as configured (e.g. the `files:` pattern, hook rev
   pin, or the notebooks/ exclude carve-out from PR #315).
2. **`.github/workflows/lint.yml`** (or a new workflow, whichever fits this
   repo's existing CI structure better): add a step that fails the build if
   any `lcats/notebooks/*.ipynb` file contains cell output — e.g. running
   `nbstripout` in a check/verify mode against the notebooks and diffing,
   or an equivalent script-based check. Exact mechanism is an
   implementation decision, not fixed here; the requirement is that CI,
   not just the local hook, catches this.
3. **`lcats/docs/secrets-setup.md`**: replace the existing
   unverified-caveat language in the Notebooks section with the real,
   verified outcome of this item, including the CI check added above.

## Non-Goals

- Does not touch the `black`/`ruff`/other existing hooks or CI jobs beyond
  adding the one new notebook-output check.
- Does not re-litigate whether `nbstripout` is the right *local* tool —
  only verifies the existing choice actually works, and adds the CI-level
  check needed to make it authoritative regardless of local installation.

## Acceptance Criteria

- `pre-commit` is installed and `pre-commit install` succeeds in this repo.
- `pre-commit run nbstripout --all-files` runs against
  `lcats/notebooks/*.ipynb` and its actual pass/fail/modified result is
  reported, not assumed.
- A notebook with a deliberately-added cell output is staged and
  committed; the local hook is confirmed to strip that output before the
  commit completes, or to block the commit until it's stripped.
- If the local hook does not work as configured, `.pre-commit-config.yaml`
  is fixed and the above is re-verified.
- A CI check is added that fails if any `lcats/notebooks/*.ipynb` file
  carries cell output, independent of whether the local hook is installed.
- The outcome is documented in `lcats/docs/secrets-setup.md`, replacing
  the current unverified caveat.
- `lrh validate` reports 0 errors.

## Validation

- `pip install pre-commit && pre-commit install`
- `pre-commit run nbstripout --all-files`
- Manual test: add a cell with real output to a notebook, `git add`,
  `git commit`, confirm the committed diff shows stripped output (or the
  commit was blocked pending stripping)
- The new CI check, run against a deliberately-dirty notebook in a
  disposable branch/PR, confirmed to fail the build
- `lrh validate`
