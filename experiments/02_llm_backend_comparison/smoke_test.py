"""End-to-end smoke test for the LLM backend comparison experiment.

Runs `assess_story` on a small sample from two corpora using both
AnthropicBackend and OpenAIBackend, then prints per-genre agreement-rate
summaries.

Usage (from the repo root with the conda environment active):

    python experiments/02_llm_backend_comparison/smoke_test.py

Optional flags:

    --sample N          Stories per leg (default: 5)
    --output DIR        Results directory (default: experiments/02_llm_backend_comparison/results)
    --anthropic-model   Anthropic model string (default: claude-opus-4-8)
    --openai-model      OpenAI model string (default: gpt-4o-2024-08-06)

Requires:
    - lcats installed (run scripts/develop if not)
    - ANTHROPIC_API_KEY and OPENAI_API_KEY set in environment OR present in
      .secrets/anthropic_api_keys.env and .secrets/openai_api_keys.env
      (see lcats/docs/secrets-setup.md)

Exit codes:
    0   all legs completed (individual story errors are noted, not fatal)
    1   prerequisite check failed (missing install, missing key)
    2   one or more legs failed entirely
"""

from __future__ import annotations

import argparse
import os
import pathlib
import sys

# ---------------------------------------------------------------------------
# Path bootstrap — allow running as `python experiments/.../smoke_test.py`
# from the lcats/ directory without requiring a prior `pip install -e .`.
# ---------------------------------------------------------------------------
_HERE = pathlib.Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parents[1]  # …/LCATS/LCATS/
_LCATS_ROOT = _REPO_ROOT / "lcats"  # …/LCATS/LCATS/lcats/
sys.path.insert(0, str(_LCATS_ROOT))
sys.path.insert(0, str(_HERE))

# ---------------------------------------------------------------------------
# Prerequisite checks — done before any other import so failures are clear.
# ---------------------------------------------------------------------------

try:
    from lcats.analysis.corpus import assess  # noqa: F401
except ImportError:
    sys.exit(
        "error: lcats package not found.\n"
        "       Activate your conda environment and run: scripts/develop"
    )

from lcats.utils.secrets import load_secrets  # noqa: E402

load_secrets()  # no-op if .secrets/ absent or keys already exported

import run_comparison  # noqa: E402  (local module, after path bootstrap)
import compare_results  # noqa: E402


def _check_keys() -> dict[str, str]:
    """Return {backend: key} for both providers, or exit with a clear message."""
    missing = []
    keys: dict[str, str] = {}
    for var, label in [
        ("ANTHROPIC_API_KEY", "anthropic"),
        ("OPENAI_API_KEY", "openai"),
    ]:
        val = os.environ.get(var, "")
        if not val:
            missing.append(f"  {var}  (required for {label} leg)")
        else:
            keys[label] = val
    if missing:
        sys.exit(
            "error: the following environment variables are not set:\n"
            + "\n".join(missing)
            + "\nSet them and re-run."
        )
    return keys


# ---------------------------------------------------------------------------
# Experiment configuration
# ---------------------------------------------------------------------------

_RUNS = [
    {
        "label": "Horror — Lovecraft corpus",
        "genre": "horror",
        "corpus_subdir": "data/lovecraft",
    },
    {
        "label": "Western — London corpus",
        "genre": "western",
        "corpus_subdir": "data/london",
    },
]


def _actual_sample(corpus_dir: pathlib.Path, requested: int) -> int:
    """Return the number of stories that run_comparison will actually assess."""
    return min(requested, len(sorted(corpus_dir.glob("*.json"))))


def _result_path(
    output_dir: pathlib.Path, backend: str, model: str, genre: str, n: int
) -> pathlib.Path:
    return output_dir / run_comparison._output_filename(backend, model, genre, n)


def _run_leg(
    args: argparse.Namespace,
    backend: str,
    model: str,
    genre: str,
    corpus_dir: pathlib.Path,
) -> int:
    leg_args = argparse.Namespace(
        backend=backend,
        model=model,
        genre=genre,
        corpus_dir=str(corpus_dir),
        sample=args.sample,
        output=str(args.output_dir),
        max_body_chars=100_000,
    )
    return run_comparison.run(leg_args)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Smoke-test the LLM backend comparison pipeline end-to-end.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "For a manual equivalent of this script, see the 'Manual smoke test'\n"
            "section of experiments/02_llm_backend_comparison/README.md."
        ),
    )
    parser.add_argument(
        "--sample", type=int, default=5, help="Stories per leg (default: 5)."
    )
    parser.add_argument(
        "--output",
        dest="output_dir",
        type=pathlib.Path,
        default=_HERE / "results",
        help="Results directory (default: experiments/02_llm_backend_comparison/results).",
    )
    parser.add_argument(
        "--anthropic-model",
        default="claude-opus-4-8",
        metavar="MODEL",
        help="Anthropic model string (default: claude-opus-4-8).",
    )
    parser.add_argument(
        "--openai-model",
        default="gpt-4o-2024-08-06",
        metavar="MODEL",
        help="OpenAI model string (default: gpt-4o-2024-08-06).",
    )
    args = parser.parse_args(argv)

    _check_keys()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    backends = [
        ("anthropic", args.anthropic_model),
        ("openai", args.openai_model),
    ]

    failed_legs: list[str] = []

    for run_cfg in _RUNS:
        genre = run_cfg["genre"]
        corpus_dir = _LCATS_ROOT / run_cfg["corpus_subdir"]
        print(f"\n{'='*60}")
        print(f"  {run_cfg['label']} — {args.sample} stories")
        print(f"{'='*60}\n")

        actual_n = _actual_sample(corpus_dir, args.sample)
        result_files: list[pathlib.Path] = []
        for backend, model in backends:
            print(f"--- {backend} / {model} ---")
            rc = _run_leg(args, backend, model, genre, corpus_dir)
            if rc != 0:
                msg = f"{backend}/{model} on {genre}"
                print(f"FAILED: {msg}", file=sys.stderr)
                failed_legs.append(msg)
            else:
                result_files.append(
                    _result_path(args.output_dir, backend, model, genre, actual_n)
                )

        if len(result_files) == 2:
            print(
                f"\n--- Agreement: {backends[0][0]} vs {backends[1][0]} ({genre}) ---\n"
            )
            compare_results.compare(result_files[0], result_files[1])

    print(f"\n{'='*60}")
    if failed_legs:
        print(f"Smoke test INCOMPLETE — {len(failed_legs)} leg(s) failed:")
        for leg in failed_legs:
            print(f"  • {leg}")
        return 2
    print("Smoke test PASSED — all legs completed.")
    print(f"Results written to: {args.output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
