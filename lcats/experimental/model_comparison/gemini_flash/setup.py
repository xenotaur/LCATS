"""Prerequisite check for the gemini_flash candidate. Run before benchmark.py.

Verifies the `openai` package is importable (used as the client SDK
against Google's OpenAI-compatible endpoint - no separate Google SDK
needed) and a GEMINI_API_KEY is available (env var or
.secrets/gemini-api-key.env - see lcats/docs/secrets-setup.md). Makes no API
calls itself.
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
    if not os.environ.get("GEMINI_API_KEY"):
        print(
            "FAIL: GEMINI_API_KEY not set. Get one from Google AI Studio "
            "(https://aistudio.google.com/apikey), then export it or add "
            "it to .secrets/gemini-api-key.env (see lcats/docs/secrets-setup.md)."
        )
        return 1

    print("OK: openai package installed and GEMINI_API_KEY is set.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
