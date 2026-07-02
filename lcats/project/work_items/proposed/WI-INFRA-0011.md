---
id: WI-INFRA-0011
title: Add secrets utility and contributor guide for .secrets/ pattern
type: deliverable
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
blocked: false
blocked_reason: null
resolution: null
expected_actions:
  - create_file
  - edit_file
  - run_tests
  - write_docs
forbidden_actions:
  - force_push
  - delete_branch
  - overhaul_notebooks
  - add_key_format_validation
  - modify_gitignore
acceptance:
  - "lcats/lcats/utils/secrets.py exists with a load_secrets(secrets_dir=None) function"
  - "load_secrets() does not override already-exported shell variables"
  - "smoke_test.py calls load_secrets() instead of inlining dotenv calls"
  - "python-dotenv is in pyproject.toml main dependencies (not only dev)"
  - "tests/utils/test_secrets.py passes using tmp_path; no real .secrets/ required"
  - "docs/secrets-setup.md explains the pattern and how to populate .secrets/"
  - "lrh validate reports 0 errors"
  - "scripts/test passes"
required_evidence:
  - test_output
  - lrh_validate
  - manual_review
artifacts_expected:
  - lcats/lcats/utils/secrets.py
  - tests/utils/test_secrets.py
  - lcats/pyproject.toml
  - experiments/02_llm_backend_comparison/smoke_test.py
  - lcats/docs/secrets-setup.md
---

# Work Item: WI-INFRA-0011

## Summary

Add a `load_secrets()` utility to `lcats/utils/` that loads API keys from the
project's gitignored `.secrets/` directory, update `smoke_test.py` to use it,
and write `docs/secrets-setup.md` as the authoritative contributor guide for
the `.secrets/` pattern.

## Problem / Context

The project stores API keys in a gitignored `.secrets/` directory
(`.secrets/anthropic_api_keys.env`, `.secrets/openai_api_keys.env`) loaded by
notebooks via `dotenv.load_dotenv()`. Experiment scripts such as
`experiments/02_llm_backend_comparison/smoke_test.py` do not share this
mechanism: they require the user to `export` each key in their shell before
running, which is non-obvious and error-prone (sourcing a `.env` file without
`export` sets shell variables that child Python processes cannot see).

The pattern is also undocumented: new contributors have no guide explaining
what `.secrets/` is, how to populate it, or that it works for both scripts and
notebooks. The fix is a small shared utility and a committed documentation file.

## Scope

- Add `lcats/lcats/utils/secrets.py` with a single public function
  `load_secrets(secrets_dir: Path | None = None) -> None`.
- Add `python-dotenv` to main `[project.dependencies]` in `pyproject.toml`.
- Update `smoke_test.py` to call `load_secrets()` before the key check.
- Write `lcats/docs/secrets-setup.md` documenting the `.secrets/` pattern for
  contributors.
- Add `tests/utils/test_secrets.py` covering the utility.

## Required Changes

1. **`lcats/pyproject.toml`** — add `python-dotenv` to `[project.dependencies]`
   (not only the `dev` extras).

2. **`lcats/lcats/utils/secrets.py`** (new) — implement
   `load_secrets(secrets_dir: Path | None = None) -> None`:
   - Default `secrets_dir` to `<repo_root>/.secrets/` detected via
     `Path(__file__)` traversal.
   - Glob `*.env` files sorted alphabetically; call `dotenv.load_dotenv(path)`
     on each (default: does not override already-exported variables).
   - No-op silently if `secrets_dir` does not exist (clean CI/CD behaviour).

3. **`tests/utils/test_secrets.py`** (new) — tests using `tmp_path`:
   - Keys not already in environment are loaded from `.env` files.
   - Keys already exported in the environment are not overridden.
   - Missing `secrets_dir` silently no-ops rather than raising.
   - Explicit `secrets_dir` argument is respected.

4. **`experiments/02_llm_backend_comparison/smoke_test.py`** — replace any
   inline dotenv loading with a call to `lcats.utils.secrets.load_secrets()`
   before `_check_keys()`. Update the `Requires:` docstring to list `.secrets/`
   as the alternative to `export`.

5. **`lcats/docs/secrets-setup.md`** (new) — contributor guide covering:
   - What `.secrets/` is and why it is gitignored.
   - How to create the two `.env` files and where to get the keys.
   - That `load_secrets()` is called automatically by experiment scripts.
   - That `export VAR=...` still works and takes precedence.
   - That notebooks use `dotenv.load_dotenv()` directly (pre-dates the utility)
     and may be migrated opportunistically.

## Non-Goals

- Do not overhaul existing notebooks to use `load_secrets()` — notebooks work
  today; migrate opportunistically in future sessions.
- Do not add API key format validation (e.g., prefix regex checks) — key
  formats change without notice; the API is the authoritative validator.
- Do not modify `.gitignore` — `.secrets/` is already excluded.
- Do not add a `.secrets/README.md.template` — `docs/secrets-setup.md` serves
  this purpose as a committed, discoverable file.
- Do not create a `WORKSTREAM-INFRA` — this is a self-contained task.

## Acceptance Criteria

- `lcats/lcats/utils/secrets.py` exists and exports `load_secrets()`.
- `load_secrets()` does not override shell-exported variables (verified by
  test: set `os.environ[key]` before calling, assert value unchanged after).
- `smoke_test.py` works end-to-end without `export` when `.secrets/` is
  populated with valid keys.
- `python-dotenv` appears in `pyproject.toml` `[project.dependencies]`.
- `tests/utils/test_secrets.py` passes without a real `.secrets/` directory.
- `lcats/docs/secrets-setup.md` exists and covers creation, usage, and the
  relationship to the `export` fallback.
- `lrh validate` reports 0 errors.
- `scripts/test` passes.

## Validation

- `scripts/version tools`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`
- `python -c "from lcats.utils.secrets import load_secrets; print('ok')"`

## Risk Notes

- `python-dotenv` moves from `dev` extras to main dependencies. It is
  MIT-licensed, stdlib-only, and ~50 KB — minimal risk for a research package.
- The utility uses `Path(__file__)` traversal to find the repo root. This
  assumes `lcats/lcats/utils/secrets.py` is always three levels below the
  `lcats/` package root. A future repo restructure could break this; document
  the assumption in a comment.
