"""CLI for the lcats assess subcommand."""

from __future__ import annotations

import argparse
import csv
import json
import os
import pathlib
import sys
from typing import Optional, Sequence

import tqdm

from lcats.analysis.corpus import discovery
from lcats.analysis.corpus.assess import (
    VALID_GENRES,
    AssessmentResult,
    assess_story,
    run_preflight,
)

TSV_COLUMNS = [
    "file_path",
    "title",
    "author",
    "target_genre",
    "verdict",
    "genre_match",
    "genre_confidence",
    "wellformed",
    "specials_verdict",
    "summary",
    "exclude_reason",
    "genre_suggestion",
    "issues_count",
    "url",
    "error",
]


def build_parser(add_help: bool = True) -> argparse.ArgumentParser:
    """Build parser for the assess subcommand."""
    parser = argparse.ArgumentParser(
        description=(
            "Assess corpus story JSON files for quality and genre fit using the Claude API."
        ),
        add_help=add_help,
        epilog=(
            "Examples:\n"
            "  lcats assess corpora/sherlock --genre 'science fiction'\n"
            "  lcats assess data/ --genre horror --format tsv --output horror_assessment.tsv\n"
            "  lcats assess corpora/sherlock --genre western --dry-run\n"
            "  ANTHROPIC_API_KEY=sk-... lcats assess data/ --genre romance --model claude-haiku-4-5"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "directories",
        nargs="*",
        default=["data/"],
        help="Directories or JSON files to assess (default: data/).",
    )
    parser.add_argument(
        "--genre",
        required=True,
        choices=list(VALID_GENRES),
        metavar="GENRE",
        help=(
            f"Target genre for assessment. Choices: {', '.join(VALID_GENRES)}. "
            "Quote multi-word genres: --genre 'science fiction'."
        ),
    )
    parser.add_argument(
        "--model",
        default="claude-opus-4-8",
        help="Claude model to use (default: claude-opus-4-8).",
    )
    parser.add_argument(
        "--max-body-chars",
        type=int,
        default=100_000,
        help="Max story body characters sent to the API (default: 100000).",
    )
    parser.add_argument(
        "--format",
        choices=["jsonl", "json", "tsv", "human"],
        default="jsonl",
        help="Output format (default: jsonl).",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Write output to FILE instead of stdout.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run pre-flight QA checks and list files without calling the API.",
    )
    parser.add_argument("--progress", dest="progress", action="store_true")
    parser.add_argument("--no-progress", dest="progress", action="store_false")
    parser.set_defaults(progress=None)
    return parser


def _show_progress(progress_arg: Optional[bool]) -> bool:
    if progress_arg is not None:
        return progress_arg
    return sys.stderr.isatty()


def _result_to_tsv_row(result: AssessmentResult) -> dict:
    return {
        "file_path": result.file_path,
        "title": result.title,
        "author": result.author,
        "target_genre": result.target_genre,
        "verdict": result.verdict,
        "genre_match": result.genre_match,
        "genre_confidence": f"{result.genre_confidence:.2f}",
        "wellformed": "yes" if result.wellformed else "no",
        "specials_verdict": result.specials_verdict,
        "summary": result.summary,
        "exclude_reason": result.exclude_reason,
        "genre_suggestion": result.genre_suggestion,
        "issues_count": str(len(result.issues)),
        "url": result.url,
        "error": result.error,
    }


def _dry_run_preview(file_path: pathlib.Path, genre: str, out) -> None:
    try:
        title, author, url, findings, _body = run_preflight(file_path)
        print(f"[dry-run] {file_path}", file=out)
        print(f"  Title:    {title}", file=out)
        print(f"  Author:   {author}", file=out)
        print(f"  Genre:    {genre}", file=out)
        if findings:
            print(f"  QA findings ({len(findings)}):", file=out)
            for f in findings:
                print(f"    [{f.severity.upper()}] {f.kind}: {f.message}", file=out)
        else:
            print("  QA findings: none", file=out)
    except Exception as exc:
        print(f"[dry-run] {file_path} — ERROR: {exc}", file=out)
    print(file=out)


def _write_human(out, result: AssessmentResult) -> None:
    symbol = {"include": "✓", "exclude": "✗", "review": "?"}.get(result.verdict, "?")
    print(f"{symbol} [{result.verdict.upper()}] {result.title}", file=out)
    print(f"  Author:  {result.author}", file=out)
    print(
        f"  Genre:   {result.target_genre} → {result.genre_match} "
        f"({result.genre_confidence:.0%})",
        file=out,
    )
    if result.summary:
        print(f"  Summary: {result.summary}", file=out)
    for issue in result.issues:
        print(
            f"  Issue [{issue['severity']}]: {issue['type']} — {issue['description']}",
            file=out,
        )
    if result.exclude_reason:
        print(f"  Reason:  {result.exclude_reason}", file=out)
    if result.error:
        print(f"  ERROR:   {result.error}", file=out)
    print(file=out)


def run(
    argv: Optional[Sequence[str]] = None,
    parsed_args: Optional[argparse.Namespace] = None,
) -> int:
    """Run the assess subcommand."""
    parser = build_parser()
    args = parsed_args if parsed_args is not None else parser.parse_args(argv)

    if args.max_body_chars < 0:
        print(
            "error: --max-body-chars must be >= 0 (use 0 for no truncation)",
            file=sys.stderr,
        )
        return 1

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not args.dry_run and not api_key:
        print(
            "error: ANTHROPIC_API_KEY environment variable is not set.\n"
            "       Set it or use --dry-run to preview without API calls.",
            file=sys.stderr,
        )
        return 1

    backend = None
    if not args.dry_run:
        try:
            from lcats.llm import anthropic_backend

            backend = anthropic_backend.AnthropicBackend(api_key=api_key)
        except ImportError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

    files = list(discovery.find_json_files(args.directories))
    if not files:
        print("No JSON files found in the specified paths.", file=sys.stderr)
        return 0

    output_stream = sys.stdout
    try:
        if args.output:
            output_stream = pathlib.Path(args.output).open(
                "w", encoding="utf-8", newline=""
            )

        tsv_writer = None
        if args.format == "tsv":
            tsv_writer = csv.DictWriter(
                output_stream,
                fieldnames=TSV_COLUMNS,
                delimiter="\t",
                extrasaction="ignore",
            )
            tsv_writer.writeheader()

        all_results = []
        for file_path in tqdm.tqdm(files, disable=not _show_progress(args.progress)):
            if args.dry_run:
                _dry_run_preview(file_path, args.genre, output_stream)
                continue

            result = assess_story(
                file_path=file_path,
                genre=args.genre,
                backend=backend,
                model=args.model,
                max_body_chars=args.max_body_chars,
            )

            if args.format == "jsonl":
                print(json.dumps(result.to_dict()), file=output_stream)
                output_stream.flush()
            elif args.format == "json":
                all_results.append(result.to_dict())
            elif args.format == "tsv":
                tsv_writer.writerow(_result_to_tsv_row(result))
                output_stream.flush()
            elif args.format == "human":
                _write_human(output_stream, result)

        if args.format == "json" and all_results:
            json.dump(all_results, output_stream, indent=2)
            print(file=output_stream)

        return 0

    except BrokenPipeError:
        return 141
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    finally:
        if output_stream is not sys.stdout:
            output_stream.close()
