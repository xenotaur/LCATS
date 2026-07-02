"""Load API keys from the project's gitignored .secrets/ directory.

The .secrets/ directory lives at the repo root and is excluded from version
control. Each provider has its own .env file:

    .secrets/anthropic_api_keys.env   — ANTHROPIC_API_KEY=sk-ant-...
    .secrets/openai_api_keys.env      — OPENAI_API_KEY=sk-proj-...

call load_secrets() early in any script that needs API keys. It does not
override keys that are already set in the environment, so shell exports and
CI/CD secrets managers take precedence automatically.

See lcats/docs/secrets-setup.md for setup instructions.
"""

from __future__ import annotations

import pathlib

# .secrets/ is three package dirs above this file, then one more to the repo root:
#   lcats/lcats/utils/secrets.py
#       parents[0] = lcats/lcats/utils/
#       parents[1] = lcats/lcats/
#       parents[2] = lcats/        (package root, contains pyproject.toml)
#       parents[3] = LCATS/LCATS/  (repo root, contains .secrets/)
_DEFAULT_SECRETS_DIR = pathlib.Path(__file__).resolve().parents[3] / ".secrets"


def load_secrets(secrets_dir: pathlib.Path | None = None) -> None:
    """Load *.env files from secrets_dir into os.environ.

    Already-exported variables are not overridden (python-dotenv default).
    Silently no-ops if secrets_dir does not exist, so CI/CD environments
    that inject keys via the environment work without any local .secrets/ dir.

    Args:
        secrets_dir: directory containing .env files. Defaults to
            <repo_root>/.secrets/ relative to this file's location.
    """
    import dotenv

    target = secrets_dir if secrets_dir is not None else _DEFAULT_SECRETS_DIR
    if not target.is_dir():
        return
    for env_file in sorted(target.glob("*.env")):
        dotenv.load_dotenv(env_file)
