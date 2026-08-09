"""Prerequisite check for the openai_gpt55 candidate. Run before benchmark.py.

Verifies the `openai` package is importable and an API key is available
(env var or .secrets/openai_api_keys.env - see lcats/docs/secrets-setup.md).
Makes no API calls itself.
"""

from __future__ import annotations

import os
import pathlib
import sys

_LCATS_SRC = pathlib.Path(__file__).resolve().parents[3] / "src"
if str(_LCATS_SRC) not in sys.path:
    sys.path.insert(0, str(_LCATS_SRC))

from lcats.utils import secrets as secrets_module  # noqa: E402


def main() -> int:
    try:
        import openai  # noqa: F401
    except ImportError:
        print("FAIL: `openai` package not installed (pip install openai).")
        return 1

    secrets_module.load_secrets()
    if not os.environ.get("OPENAI_API_KEY"):
        print(
            "FAIL: OPENAI_API_KEY not set. Export it, or add it to "
            ".secrets/openai_api_keys.env (see lcats/docs/secrets-setup.md)."
        )
        return 1

    print("OK: openai package installed and OPENAI_API_KEY is set.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
