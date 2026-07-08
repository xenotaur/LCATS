# Documentation Audit — LCATS

- Prompt ID: `PROMPT(AD_HOC:REQUEST_AUDIT_DOCS)[2026-05-26T00:00:00+00:00]`
- Audit date: 2026-05-26
- Repository root discovered: `lcats/` (execution root nested under top-level repo)
- Requested inputs:
  - `repo_root`: `.`
  - `project_root`: `lcats`
  - `docs_root`: `lcats/docs` (missing)
  - `control_root`: `lcats/project`
  - `package_root`: `lcats/lcats`

## 1) Scope and method

This audit inspects:
- top-level documentation and package READMEs
- control-plane documentation under `lcats/project/`
- package/module layout under `lcats/lcats/`
- scripts/tooling docs under `lcats/scripts/` and `lcats/tools/`
- implemented CLI surface from source (`lcats/lcats/cli.py`) and packaging metadata (`lcats/pyproject.toml`)

No documentation reorganization was performed in this PR.

## 2) Layout reality vs assumed paths

### Observed layout reality

- Top-level repo root is **not** the execution root; active Python project is nested at `lcats/`.
- `docs_root` (`lcats/docs`) does not exist.
- Control-plane directory `lcats/project` exists and is actively used.
- Package root `lcats/lcats` exists and contains implementation modules.

### Impact

- External contributors may assume `README.md` at repository root and `docs/` conventions that do not exist here.
- Existing docs must explicitly teach the nested execution root to avoid incorrect command execution context.

## 3) Documentation inventory and coverage

### Present docs

- General/project:
  - `lcats/README.md`
- Control plane:
  - `lcats/project/README.md`
  - `lcats/project/design/README.md`
  - `lcats/project/work_items/README.md`
- Operational/tooling:
  - `lcats/scripts/README.md`
  - `lcats/tools/README.md`
- Subsystem deep dive:
  - `lcats/lcats/analysis/corpus/README.md`

### Not present

- No centralized docs tree (`lcats/docs/` missing).
- No dedicated API/reference index for package modules.
- No architecture index at project root linking code modules to control-plane artifacts.

## 4) Accuracy checks: docs vs implementation

### Confirmed accurate areas

- README and scripts docs consistently indicate commands should run from nested `lcats/` execution root.
- Tooling docs explain `scripts/lint`, `scripts/format`, and `scripts/test` usage in a way that aligns with repository scripts documentation.
- Corpus analysis README distinguishes implemented behavior from planned behavior explicitly.

### Accuracy mismatches / staleness

1. **Python version guidance drift**
   - `lcats/README.md` says "Python > 3.6(ish)".
   - `lcats/pyproject.toml` defines `requires-python = ">=3.6"`.
   - This is technically compatible but wording in README is informal/ambiguous and can mislead automation readers.

2. **Test framework mismatch in requirements prose**
   - `lcats/README.md` still references installing `pytest` via conda while project testing workflow and style guidance center on `unittest` and `scripts/test`.
   - The test command itself is correct, but mention of pytest in Requirements may create confusion about canonical test runner.

3. **Potential stale script docs section risk**
   - `scripts/README.md` includes rich examples but should be periodically validated against each script's actual `--help` output (particularly optional flags like `--extra`, argument forms, and supported target types).

4. **CLI capabilities not summarized in top-level docs with implemented/planned split**
   - `lcats/lcats/cli.py` contains implemented subcommands (`info`, `gather`, `inspect`, `display`, `survey`, `stats`, `repair-specials`, `meta register`) and explicitly not-yet-implemented commands (`index`, `advise`, `eval`).
   - Top-level docs mention some commands but do not provide a concise "implemented vs placeholder" matrix.

## 5) Navigation and link-gap audit

### Gaps

- No singular "Docs Home" page to route users to:
  - getting started
  - CLI reference
  - control-plane concepts
  - subsystem technical references
- Control-plane docs are discoverable only if user already knows `project/` exists.
- Subsystem reference (`analysis/corpus/README.md`) is isolated and not indexed from a central docs map.

### Link risks

- Because docs are spread across multiple roots without a docs index, relative path changes (e.g., future move of control-plane docs or package docs) are more likely to introduce orphaned knowledge even if links are not currently broken.

## 6) Diátaxis classification (current state)

### Tutorials (learn by building)

- **Sparse/partial**: top-level README has setup + command snippets, but lacks end-to-end narrative tutorials.

### How-to guides (task-oriented)

- **Moderate**:
  - `scripts/README.md` provides practical usage recipes.
  - `tools/README.md` includes how-to for request generation and source surveying.

### Reference (facts/specs)

- **Moderate but fragmented**:
  - CLI reality is in code (`lcats/lcats/cli.py`) rather than a dedicated CLI reference doc.
  - Corpus subsystem README provides strong conceptual/behavioral reference for that subsystem.

### Explanations (conceptual/background)

- **Strong in control plane and corpus subsystem**:
  - `project/README.md` explains LRH control-plane purpose.
  - `analysis/corpus/README.md` explains principles, architecture, data flow, and rationale.

### Diátaxis summary

- Strongest quadrant: **explanations**.
- Weakest quadrant: **tutorials** and centralized **reference index**.

## 7) Implemented vs planned behavior separation

### Good existing separation

- `analysis/corpus/README.md` has explicit sections for implemented capabilities, planned enhancements, and intentionally deferred features.

### Missing separation elsewhere

- Top-level CLI docs do not explicitly separate available commands from placeholder commands.
- Control-plane docs describe current state but do not provide a single machine-readable status index linked to code ownership/entrypoints.

## 8) Docs vs control-plane boundary issues

1. **Boundary clarity issue**
   - `project/` is both operational memory and contributor guidance, but this role is not linked from top-level docs as a "control-plane" concept for newcomers.

2. **Traceability issue**
   - Work-item and design docs in `project/` are not cross-indexed with package modules or CLI entry points, limiting discoverability when moving from implementation to planning artifacts.

3. **Missing docs governance index**
   - No explicit "documentation architecture" file describing where user docs vs governance/control-plane docs should live.

## 9) LRH prompt execution record check

- No explicit prompt execution-record convention was discovered in scanned project docs.
- No existing execution record for this exact prompt ID was found.
- Therefore, soft-idempotence could not be applied via a pre-existing execution-log mechanism.

## 10) Recommended target documentation structure

Recommended target (do **not** implement in this PR):

- `lcats/docs/` (new docs hub)
  - `index.md` (global docs map)
  - `tutorials/`
    - `quickstart.md`
    - `first-corpus-survey.md`
  - `how-to/`
    - `run-tests-lint-format.md`
    - `register-project-meta.md`
    - `run-repair-specials.md`
  - `reference/`
    - `cli.md` (generated/maintained from `lcats/lcats/cli.py`)
    - `scripts.md` (checked against `scripts/* --help`)
    - `package-layout.md`
  - `explanation/`
    - `control-plane.md` (what `project/` is and is not)
    - `corpus-analysis-architecture.md` (can link/derive from existing subsystem README)

Keep existing README files, but make them thinner and point to this hub.

## 11) Phased PR plan (recommended)

### Phase 1 (low risk, indexing only)

- Add `lcats/docs/index.md` with a docs map.
- Add a short section in `lcats/README.md` linking to docs hub and clarifying nested execution root.
- Add a CLI status matrix (implemented vs placeholder) in a new reference page.

### Phase 2 (reference normalization)

- Produce canonical CLI reference from `lcats/lcats/cli.py` and verify examples with `--help` outputs.
- Create `docs/reference/package-layout.md` mapping major modules and their responsibilities.
- Cross-link control-plane docs from docs explanation section.

### Phase 3 (tutorial gap closure)

- Add two task-complete tutorials:
  - environment setup + `scripts/develop`
  - run `lcats survey` and interpret findings

### Phase 4 (governance and idempotence)

- Define and document prompt execution record conventions under `project/` (if LRH wants audit trail standardization).
- Add template/checklist for future docs audits.

## 12) Tiny fixes applied in this PR

- None. (Per request, this audit PR avoids doc reorganization and non-essential edits.)

## 13) Evidence map (primary files reviewed)

- `lcats/README.md`
- `lcats/pyproject.toml`
- `lcats/project/README.md`
- `lcats/project/design/README.md`
- `lcats/project/work_items/README.md`
- `lcats/scripts/README.md`
- `lcats/tools/README.md`
- `lcats/lcats/cli.py`
- `lcats/lcats/analysis/corpus/README.md`
