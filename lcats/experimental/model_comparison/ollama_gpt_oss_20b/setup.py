"""Prerequisite check for the ollama_gpt_oss_20b candidate. Run before benchmark.py.

Verifies the Ollama server is reachable and the gpt-oss:20b model has been
pulled. Does NOT install Ollama or pull the model itself - both are
multi-hundred-MB-to-multi-GB downloads that should be a deliberate,
explicit step (see this directory's README.md), not a side effect of
running a check.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

OLLAMA_HOST = "http://localhost:11434"
MODEL = "gpt-oss:20b"


def main() -> int:
    try:
        with urllib.request.urlopen(f"{OLLAMA_HOST}/api/tags", timeout=5) as resp:
            payload = json.loads(resp.read())
    except (urllib.error.URLError, TimeoutError):
        print(
            f"FAIL: no Ollama server reachable at {OLLAMA_HOST}.\n"
            "  Install: brew install ollama\n"
            "  Start:   ollama serve   (or open the Ollama app)"
        )
        return 1

    installed = {m.get("name") for m in payload.get("models", []) if m.get("name")}
    if MODEL not in installed:
        print(
            f"FAIL: {MODEL} not found among installed models: {sorted(installed) or '(none)'}\n"
            f"  Pull it with: ollama pull {MODEL}"
        )
        return 1

    print(f"OK: Ollama reachable at {OLLAMA_HOST} and {MODEL} is installed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
