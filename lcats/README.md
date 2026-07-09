# LCATS Python package 'lcats'
Python implementation of LCATS, a large language model version of the 
Captain's Advisory Tool System. This includes tools for extracting data
from various sources into local corpora, and will later contain more
sophisticated tools built on top of these corpora.

## Requirements
Right now, some requirements are via pip and others via conda. :-/
- Python >= 3.10 (several modules use `X | None` union-type syntax evaluated at import time,
  which requires 3.10+; `pyproject.toml` and `setup.py` still declare `>=3.6` — that's stale and
  not fixed here, since this is a docs-only change)
- pip install build  # can be conda installed: conda install conda-forge::python-build
- pip install twine  # can be conda installed: conda install conda-forge::twine
- pip install beautifulsoup4
- pip install lxml
- conda install conda-forge::parameterized

Tests use Python's built-in `unittest` (see `STYLE.md`), not `pytest` — no `pytest` install is
required. CI runs Python 3.11.


## Building
```
# Get the repository
gh repo clone xenotaur/LCATS

# Change to the Python pacakge directory.
cd LCATS/lcats

# Tests using the unittest package
scripts/test

# Local development using an editable local pip installation.
scripts/clean && scripts/build && scripts/develop
lcats info
lcats gather

# Register a repository in the workspace meta registry
lcats meta register <repo_locator>
```
Publishing this package to PyPI is not yet supported because we don't yet have extensive enough tests.


## Documentation

LCATS documentation is being organized under `docs/`.

- Docs hub: [`docs/index.md`](docs/index.md)
- CLI implementation status reference: [`docs/reference/cli-status.md`](docs/reference/cli-status.md)
- LRH control-plane docs: [`project/README.md`](project/README.md)

The execution root remains `lcats/` (for example: `cd LCATS/lcats`).

## Optional pre-commit checks (local convenience only)

`pre-commit` runs lightweight checks automatically before each commit. In LCATS, this is only a local convenience layer.

**Pre-commit is OPTIONAL. CI is authoritative.**  
Project scripts (`scripts/lint`, `scripts/format`, `scripts/test`) and GitHub Actions remain the source of truth.

### Setup

```bash
pip install pre-commit
pre-commit install
```

Or use the helper:

```bash
scripts/precommit
```

### Run manually

```bash
pre-commit run --all-files
```

Or with the helper:

```bash
scripts/precommit --all-files
```

### What happens on commit

When installed, pre-commit runs configured hooks on changed files. If a hook fails:

1. Read the error output.
2. Apply fixes (some hooks auto-fix).
3. Re-stage files and commit again.

If you need to bypass hooks temporarily, use:

```bash
git commit --no-verify
```

### Scope of this pilot

- Minimal hooks only (Ruff + Black + basic file hygiene checks).
- Python checks are limited to files under `lcats/`.
- No extra type-checking or heavy checks.
- Easy rollback: remove `.pre-commit-config.yaml` and run `pre-commit uninstall`.
