"""Frontier-model baseline candidate: claude-opus-4-8 via AnthropicBackend.

Run setup.py first. This makes ONE real, billable Anthropic API call (the
entity-extraction tool-schema stage against a single real scene/sequel
segment - see common/sample_segment.json) - see this directory's
README.md for expected cost.

Usage:
    python lcats/experimental/model_comparison/anthropic_opus/benchmark.py
"""

from __future__ import annotations

import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
_MODEL_COMPARISON = _HERE.parent
sys.path.insert(0, str(_MODEL_COMPARISON))

from common import harness  # noqa: E402
from lcats.llm import anthropic_backend  # noqa: E402
from lcats.utils import secrets  # noqa: E402

MODEL = "claude-opus-4-8"


def main() -> None:
    secrets.load_secrets()
    backend = anthropic_backend.AnthropicBackend()
    result = harness.run_entity_extraction(
        candidate="anthropic_opus",
        backend_kind="anthropic",
        backend=backend,
        model=MODEL,
    )
    out_path = harness.save_result(result, _HERE)
    print(f"Wrote {out_path}")
    print(result.to_dict())


if __name__ == "__main__":
    main()
