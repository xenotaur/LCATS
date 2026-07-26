---
id: PROP-LCATS-PACKAGING-MODERNIZATION
type: design_proposal
title: LCATS Python Packaging Modernization — src-layout, dynamic versioning, and PEP 621/639 metadata
status: proposed
created_on: 2026-07-26
updated_on: 2026-07-26
implementation_status: not_started
implemented_by: []
supersedes: []
superseded_by: null
related_design: []
---

## Summary

Bring `lcats/pyproject.toml` and the package layout up to current PyPA/PEP
621/PEP 639 best practice and parity with the sibling `lrh` project's own
packaging setup, delivered as three independently-mergeable phases ordered
by risk.

## Background / Motivation

A review of `lcats/pyproject.toml` and `lcats/setup.py` against PyPA
guidance and against `logical_robotics_harness/pyproject.toml` found nine
gaps:

1. Flat package layout (`lcats/lcats/`) rather than src-layout, carrying the
   import-shadowing risk PyPA describes in
   [src-layout vs flat-layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/).
2. `version = "0.1"` in `pyproject.toml`, which `git log -p --follow` shows
   has never changed since it was first added.
3. A redundant, hand-maintained `setup.py` duplicating metadata already
   declared in `pyproject.toml` (name, entry point, `find_packages()`).
4. A deprecated `license = {text = "MIT"}` table; PEP 639 wants the SPDX
   string form plus `license-files`.
5. An old `setuptools>=42` build-system pin, predating reliable PEP 621
   `[project]` table support and, more strictly, predating PEP 639
   `license`/`license-files` support (added in setuptools 77.0.0 per the
   [setuptools changelog](https://setuptools.pypa.io/en/latest/history.html)).
6. No `[tool.ruff]` / `[tool.black] required-version` self-enforcement.
   `pyproject.toml` pins `black==25.11.0` in the `test`/`dev` extras
   (matching `lint.yml`'s CI pin) but leaves `ruff` unpinned there, and
   neither tool has a `required-version` declared in `pyproject.toml`
   itself — so a local `ruff`/`black` invocation has no way to fail fast on
   version skew; the version only gets checked, and can silently diverge,
   in CI.
7. Byte-identical duplicate `test` and `dev` optional-dependency lists.
8. `gutenbergpy` pinned to a mutable branch ref
   (`git+...@LCATS/TitleFix`) rather than a commit SHA or tag.
9. Thinner `[project]` metadata (no `project.urls`, fewer classifiers) than
   LRH's own `pyproject.toml`.

Full findings and the confirmed blast radius — CI's
`working-directory: lcats` (meaning workflow YAML needs no changes),
`scripts/lint`/`scripts/format`'s default target list, `secrets.py`'s
hardcoded `parents[3]` depth count for locating the repo root, and the
untracked/gitignored `lcats.egg-info` (safe to regenerate) — were
established in conversation with the user before this proposal was drafted.

## Prior Art Check

### Duplication search
- In-repo: No existing implementation found.
- Sibling repos: `logical_robotics_harness/pyproject.toml` already
  implements src-layout, `setuptools-scm`, and PEP 639 license declaration —
  used here as the reference pattern, not duplicated work.
- External libraries: None identified — this is project packaging
  configuration, not a library concern.
- Recommendation: Proceed.

### Demand search
- Work items: None found (`project/work_items/`).
- Proposals: None found (`project/design/proposals/`).
- Backlog: No matching entries (`project/design/backlog.md`).
- Recommendation: No action.

## Design Decisions

### Decision 1: Package layout

Options considered:
- Keep flat layout (`lcats/lcats/`) — status quo, but carries the
  import-shadowing risk PyPA warns about.
- Move to src-layout (`lcats/src/lcats/`) — matches PyPA recommendation and
  the `lrh` sibling project's own layout.

**Chosen: src-layout.** Eliminates the risk that `import lcats` inside the
checkout silently resolves to the on-disk directory instead of the
installed distribution, and aligns LCATS with LRH's existing convention.

### Decision 2: Versioning

Options considered:
- Keep the static `version = "0.1"` string.
- Move to `dynamic = ["version"]` via `setuptools-scm`, as LRH does.

**Chosen: `setuptools-scm`.** The installed version now reflects actual git
state instead of a frozen string that has never been updated;
`fallback_version` covers tag-less clones and sdists.

### Decision 3: `setup.py`

Options considered:
- Keep `setup.py` alongside `pyproject.toml`.
- Remove it once `pyproject.toml` is self-sufficient.

**Chosen: remove**, once dynamic versioning removes the last reason
`setup.py` might diverge from `pyproject.toml`. Current setuptools fully
supports declarative `pyproject.toml`-only configuration, as LRH already
demonstrates.

### Decision 4: License declaration

Options considered:
- Keep `license = {text = "MIT"}`.
- Switch to the PEP 639 form: `license = "MIT"` plus `license-files`.

**Chosen: PEP 639 form.** `lcats/LICENSE` already exists on disk; it was
just never correctly declared.

### Decision 5: Tool-version enforcement

Options considered:
- Keep pinning `ruff`/`black` versions only in CI YAML.
- Add `required-version` to `[tool.ruff]` / `[tool.black]` in
  `pyproject.toml`, as LRH does.

**Chosen: `pyproject.toml` `required-version`.** Local runs now fail fast on
version skew instead of silently reformatting differently and only
surfacing the mismatch in CI or via a pre-commit hook rewrite.

### Decision 6: Delivery sequencing

Options considered:
- Single PR covering all nine items.
- Three phased PRs ordered by risk.

**Chosen: three phases** — (1) metadata/config only, (2) src-layout move,
(3) dynamic versioning + `setup.py` removal — so tool-version
self-enforcement lands before the higher-risk layout move, and `setup.py`
removal lands only once it is unambiguously redundant.

## Non-Goals

- Does not change LCATS's runtime dependencies or supported Python version
  floor (`requires-python = ">=3.10"` stays as-is).
- Does not migrate LCATS to a different build backend (e.g., Hatch, PDM) —
  stays on setuptools, matching LRH.
- Does not fix `secrets.py`'s parent-depth-counting pattern beyond the
  one-line index bump required by the layout move — a more robust
  anchor-on-`pyproject.toml` approach is a candidate follow-up, not in scope
  here.
- Does not modify CI workflow YAML — confirmed unnecessary, since
  `working-directory: lcats` in `tests.yml`, `coverage.yml`, and `lint.yml`
  already treats `lcats/` as the project root regardless of internal layout.

## Implementation Plan

Multi-stage; delivered as three sequential work items against a governing
workstream:

1. **Metadata/config fixes** — PEP 639 license form, bumping the
   `build-system.requires` pin to `setuptools>=77` (the version that added
   PEP 639 `license`/`license-files` support — `setuptools>=68` is
   insufficient for this specific change), `[tool.ruff]`/`[tool.black]
   required-version` pins (and pinning `ruff` in the `test`/`dev` extras to
   match CI), dedupe `test`/`dev` extras, pin `gutenbergpy` to a commit SHA,
   add `project.urls` and classifiers. No code or CI changes.
2. **src-layout move** — `lcats/lcats/` → `lcats/src/lcats/`;
   `[tool.setuptools] package-dir`/`[tool.setuptools.packages.find] where`;
   update `scripts/lint` and `scripts/format` default targets; update
   `secrets.py`'s `parents[N]` depth count; audit `.pre-commit-config.yaml`,
   `tools/sourcetree_surveyor.py`, `tools/create_request.py`,
   `experiments/02_llm_backend_comparison/run_comparison.py`, and
   `experiments/03_cross_segment_relation_pilot/run_pilot.py` for
   `lcats/lcats` path literals or `sys.path` bootstraps that assume the
   package lives at `<repo>/lcats` (the two `experiments/*/run_*.py` scripts
   each do `sys.path.insert(0, ... / "lcats")` to support direct execution
   without an editable install, and must point at `.../lcats/src` instead);
   reinstall editable package; run the full test suite.
3. **Dynamic versioning + `setup.py` removal** — `dynamic = ["version"]`,
   adding `setuptools-scm` to `build-system.requires` (required so the PEP
   517 isolated build environment can actually invoke the SCM plugin — it
   is not implied by `[tool.setuptools_scm]` alone), `[tool.setuptools_scm]`
   with `fallback_version`, cut a first git tag, delete `lcats/setup.py`.

Given three sequential, individually-scoped work items with cross-item
ordering constraints, this is medium/large scope: a governing workstream is
recommended, with one work item per phase.

## Cross-References

- Reference implementation pattern:
  `logical_robotics_harness/pyproject.toml` (sibling `lrh` project).
- The version-skew rationale in gap 6 above is drawn from prior first-hand
  observation of a pre-commit hook reformatting files because the local
  `black`/`ruff` install diverged from CI's pinned versions — not from a
  repo-discoverable artifact, so it is stated inline rather than
  cross-referenced.
