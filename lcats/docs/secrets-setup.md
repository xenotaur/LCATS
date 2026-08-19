# API Key Setup — `.secrets/` Pattern

LCATS uses a gitignored `.secrets/` directory at the repo root to store API
keys locally. This lets you run notebooks and experiment scripts without
exporting keys in your shell each time, and without any risk of accidentally
committing them.

## Why `.secrets/` and not `export`?

Sourcing a `.env` file with `source .secrets/file.env` sets *shell* variables.
Python's `os.environ` only sees *process environment* variables (those marked
with `export`). The `.secrets/` pattern uses `python-dotenv` to load files
directly into `os.environ`, so keys are available to Python without the
manual `export` step.

Shell-exported keys always take precedence — `python-dotenv` does not override
variables already present in the environment, so CI/CD secrets managers and
explicit `export` commands continue to work unchanged.

## Directory structure

```
.secrets/                          ← gitignored; never committed
├── anthropic_api_keys.env         ← Anthropic API key
└── openai_api_keys.env            ← OpenAI API key
```

The `.secrets/` directory is listed in `.gitignore` at the repo root. Git will
never stage or commit its contents.

## Setup

Create the directory and one file per provider:

```bash
mkdir -p .secrets

# Anthropic
echo "ANTHROPIC_API_KEY=sk-ant-..." > .secrets/anthropic_api_keys.env

# OpenAI
echo "OPENAI_API_KEY=sk-proj-..." > .secrets/openai_api_keys.env
```

Replace `sk-ant-...` and `sk-proj-...` with your actual keys. Get them from:

- Anthropic: https://console.anthropic.com/settings/keys
- OpenAI: https://platform.openai.com/api-keys

## How it works

`lcats.utils.secrets.load_secrets()` globs all `*.env` files in `.secrets/`
alphabetically and calls `dotenv.load_dotenv()` on each. It is called
automatically at the top of experiment scripts such as
`experiments/02_llm_backend_comparison/smoke_test.py`.

You can also call it directly:

```python
from lcats.utils.secrets import load_secrets

load_secrets()  # loads from <repo_root>/.secrets/ by default
```

Or point it at a different directory:

```python
import pathlib
load_secrets(secrets_dir=pathlib.Path("/path/to/my/keys"))
```

If `.secrets/` does not exist, `load_secrets()` silently no-ops — no error,
no warning. This is the correct behaviour in CI/CD environments where keys
come from the environment directly.

## Notebooks

Notebooks in `lcats/notebooks/` pre-date this utility and load the OpenAI key
directly via `dotenv.load_dotenv()`. They continue to work without change.
Migrating them to `load_secrets()` is welcome but not required.

Do not `print()` the raw key value in a notebook cell — a printed key gets
saved into the notebook's JSON as cell output and committed along with it.
This is exactly how a real key ended up leaked in this repo's history; see
[Secrets hygiene](how-to/secrets-hygiene.md). If you need to confirm a key
loaded, check for presence only:

```python
print('OPENAI_API_KEY:', 'set' if OPENAI_API_KEY else 'MISSING')
```

As a backstop, `nbstripout` runs as a pre-commit hook on everything under
`lcats/notebooks/*.ipynb` (see `.pre-commit-config.yaml`) and strips all
cell outputs before a notebook can be committed, regardless of what a cell
printed. **Verified** (`WI-INFRA-0012`): installing the hook and running
`pre-commit run nbstripout --all-files` for real modified 15 notebooks, of
which 2 (`04_rag_expt.ipynb`, `06_story_analysis.ipynb`) actually carried
unstripped cell output from before this hook existed; the other 13 were
only rewritten for `execution_count`/cell-ID/source-array-format
normalization, a side effect of nbstripout re-serializing a file it
touches at all, not evidence of a leak. This confirms both that the hook
works and that a real (if narrower than initially reported) gap was live
until it was run.
A deliberate commit-time test (staging a notebook with fresh cell output)
confirmed the hook blocks the commit and strips the output in the same
step; re-staging and committing again then succeeds clean.

Because `lcats/README.md` states pre-commit is optional and CI is
authoritative, protection does not stop at the local hook: CI
(`.github/workflows/lint.yml`) independently runs
`nbstripout --verify notebooks/*.ipynb`, which fails the build if any
notebook carries output — regardless of whether a given contributor ever
ran `pre-commit install`.

## Verifying setup

After populating `.secrets/`, run:

```bash
python -c "
from lcats.utils.secrets import load_secrets
import os
load_secrets()
print('ANTHROPIC_API_KEY:', 'set' if os.environ.get('ANTHROPIC_API_KEY') else 'MISSING')
print('OPENAI_API_KEY:', 'set' if os.environ.get('OPENAI_API_KEY') else 'MISSING')
"
```

Both lines should print `set`. If a key shows `MISSING`, check that the
corresponding `.env` file exists and contains a non-empty value.
