"""Prerequisite check for the anthropic_opus candidate. Run before benchmark.py.

Verifies the `anthropic` package is importable and an API key is available
(env var or .secrets/anthropic_api_keys.env - see docs/secrets-setup.md).
Makes no API calls itself.
"""

from __future__ import annotations

import os
import pathlib
import sys

_LCATS_SRC = pathlib.Path(__file__).resolve().parents[3] / "src"
if str(_LCATS_SRC) not in sys.path:
    sys.path.insert(0, str(_LCATS_SRC))

from lcats.utils import secrets  # noqa: E402


def main() -> int:
    try:
        import anthropic  # noqa: F401
    except ImportError:
        print("FAIL: `anthropic` package not installed (pip install anthropic).")
        return 1

    secrets.load_secrets()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(
            "FAIL: ANTHROPIC_API_KEY not set. Export it, or add it to "
            ".secrets/anthropic_api_keys.env (see docs/secrets-setup.md)."
        )
        return 1

    print("OK: anthropic package installed and ANTHROPIC_API_KEY is set.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
