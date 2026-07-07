"""Run an assess pipeline comparison across LLM backends.

Usage (from the repo root):
    python experiments/02_llm_backend_comparison/run_comparison.py \
        --backend anthropic --model claude-opus-4-8 \
        --genre horror --corpus-dir lcats/data/lovecraft \
        --sample 5 --output experiments/02_llm_backend_comparison/results/

The first N story JSON files (sorted alphabetically, .json only) from
--corpus-dir are assessed and written to
  <output>/<backend>-<model>-<genre>-<N>.jsonl

Each line is a JSON-serialised AssessmentResult dict augmented with
backend/model/token fields for cost and latency analysis.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lcats"))

from lcats.analysis.corpus import assess


def _build_backend(backend_name: str, model: str):
    if backend_name == "anthropic":
        from lcats.llm import anthropic_backend

        return anthropic_backend.AnthropicBackend()
    elif backend_name == "openai":
        from lcats.llm import openai_backend

        return openai_backend.OpenAIBackend()
    else:
        raise ValueError(f"Unknown backend: {backend_name!r}")


def _output_filename(backend_name: str, model: str, genre: str, n: int) -> str:
    safe_model = model.replace("/", "-")
    safe_genre = genre.replace(" ", "_")
    return f"{backend_name}-{safe_model}-{safe_genre}-{n}.jsonl"


def run(args: argparse.Namespace) -> int:
    corpus_dir = pathlib.Path(args.corpus_dir)
    if not corpus_dir.is_dir():
        print(f"error: --corpus-dir {corpus_dir} does not exist", file=sys.stderr)
        return 1

    output_dir = pathlib.Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    story_files = sorted(f for f in corpus_dir.iterdir() if f.suffix == ".json")
    if not story_files:
        print(f"error: no .json files found in {corpus_dir}", file=sys.stderr)
        return 1

    stories = story_files[: args.sample]
    print(
        f"[{args.backend}/{args.model}] genre={args.genre!r} "
        f"corpus={corpus_dir.name} sample={len(stories)}",
        file=sys.stderr,
    )

    try:
        backend = _build_backend(args.backend, args.model)
    except ImportError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    out_path = output_dir / _output_filename(
        args.backend, args.model, args.genre, len(stories)
    )
    cwd = pathlib.Path.cwd()
    written = 0
    with out_path.open("w", encoding="utf-8") as fh:
        for story_path in stories:
            print(f"  assessing {story_path.name} ...", file=sys.stderr)
            try:
                rel_path = story_path.relative_to(cwd)
            except ValueError:
                rel_path = story_path
            result = assess.assess_story(
                file_path=rel_path,
                genre=args.genre,
                backend=backend,
                model=args.model,
                max_body_chars=args.max_body_chars,
            )
            row = result.to_dict()
            fh.write(json.dumps(row) + "\n")
            fh.flush()
            written += 1

    print(f"wrote {written} records → {out_path}", file=sys.stderr)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the assess pipeline on a corpus sample using one LLM backend.",
    )
    parser.add_argument(
        "--backend",
        required=True,
        choices=["anthropic", "openai"],
        help="Which LLMBackend to use.",
    )
    parser.add_argument(
        "--model",
        required=True,
        help="Model string to pass to the backend (e.g. claude-opus-4-8, gpt-4o-2024-08-06).",
    )
    parser.add_argument(
        "--genre",
        required=True,
        choices=list(assess.VALID_GENRES),
        metavar="GENRE",
        help=f"Target genre. Choices: {', '.join(assess.VALID_GENRES)}.",
    )
    parser.add_argument(
        "--corpus-dir",
        required=True,
        help="Directory of story .json files to sample from.",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=5,
        help="Number of stories to assess (first N alphabetically). Default: 5.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Directory to write the JSONL result file.",
    )
    parser.add_argument(
        "--max-body-chars",
        type=int,
        default=100_000,
        help="Max story body characters sent to the API. Default: 100000.",
    )
    return parser


if __name__ == "__main__":
    sys.exit(run(build_parser().parse_args()))
