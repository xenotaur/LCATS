# LCATS: agent guidance (read before making changes)

## High-level goals
- Prefer small, reviewable PRs.
- Avoid drive-by refactors. If a refactor is required for testability, keep it minimal and justify it in the PR description.

## Commands (source of truth)
- Run the full test suite with: `scripts/test`
- Do not claim tests passed unless you ran `scripts/test` successfully.
- If tests fail, fix the implementation or the test. Do not suppress or skip failing tests.

## Python style
- If formatting changes are needed, run Black.
- If lint issues are introduced, fix them using Ruff.
- Do not introduce new formatting/lint tools unless explicitly requested.
- Do not reformat unrelated files.

## Imports (project rule)
- Prefer module imports over member imports.
- Always import the module, not individual functions or classes.
- Use `from package import module` syntax for project modules.
- Avoid `import package.module as module` syntax for project modules.

Example:
  - ✅ `from lcats.lcats.utils import names`
  - Use as: `names.normalize_basename(...)`
  - ❌ `import lcats.lcats.utils.names as names`
  - ❌ `from lcats.lcats.utils.names import normalize_basename`
  
- Keep imports stable; do not reorder or rewrite existing import style unless necessary.
- Follow community conventions for well-known libraries (e.g., `import numpy as np`).
- Do not change existing import style in this project to match external conventions.

## Mocking / test philosophy
- Avoid heavy mocking. Tests should validate behavior, not that mocks were called.
- Mock only at true boundaries (network, external services), and only if unavoidable.

## Notebooks
- Do not edit Jupyter notebooks unless explicitly requested.
- Prefer testing the library code used by notebooks.

## Test-only PRs
- When adding tests, do not modify production code unless strictly required.
- If a change to production code is required for determinism or testability, keep it minimal and explain why in the PR description.