"""Load API keys from the project's gitignored .secrets/ directory.

The .secrets/ directory lives at the repo root and is excluded from version
control. Each provider has its own .env file:

    .secrets/anthropic_api_keys.env   — ANTHROPIC_API_KEY=sk-ant-...
    .secrets/openai_api_keys.env      — OPENAI_API_KEY=sk-proj-...

Call load_secrets() early in any script that needs API keys. It does not
override keys that are already set in the environment, so shell exports and
CI/CD secrets managers take precedence automatically.

See lcats/docs/secrets-setup.md for setup instructions.
"""

from __future__ import annotations

import pathlib

from lcats.utils import paths

# .secrets/ lives one level above the package root (the directory that
# contains pyproject.toml), at the actual git repo root. A non-editable
# install (wheel or `pip install .` outside the checkout) has no
# pyproject.toml ancestor on disk at all, so find_pyproject_root raises --
# fall back to None rather than letting that propagate out of a module
# import, and treat None the same as "directory doesn't exist" below.
try:
    _DEFAULT_SECRETS_DIR = paths.find_pyproject_root(__file__).parent / ".secrets"
except FileNotFoundError:
    _DEFAULT_SECRETS_DIR = None


def load_secrets(secrets_dir: pathlib.Path | None = None) -> None:
    """Load *.env files from secrets_dir into os.environ.

    Already-exported variables are not overridden (python-dotenv default).
    Silently no-ops if secrets_dir does not exist, so CI/CD environments
    that inject keys via the environment work without any local .secrets/ dir.

    Args:
        secrets_dir: directory containing .env files. Defaults to
            <repo_root>/.secrets/ relative to this file's location.
    """
    target = secrets_dir if secrets_dir is not None else _DEFAULT_SECRETS_DIR
    if target is None or not target.is_dir():
        return
    import dotenv

    for env_file in sorted(target.glob("*.env")):
        dotenv.load_dotenv(env_file, override=False)
