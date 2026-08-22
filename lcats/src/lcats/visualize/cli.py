"""CLI for lcats visualize."""

import argparse
import json
import pathlib
import sys
from typing import Optional, Sequence

import matplotlib.pyplot as plt

from lcats.visualize import analysis
from lcats.visualize import rendering
from lcats.visualize import sources

DEFAULT_FORMATS = "png,svg"
DEFAULT_OUTPUT_DIR = "genre_viz"


def build_visualize_parser(add_help: bool = True) -> argparse.ArgumentParser:
    """Build parser for the visualize command family."""
    parser = argparse.ArgumentParser(
        prog="lcats visualize",
        description="Corpus and document text visualization commands.",
        add_help=add_help,
    )
    visualize_subparsers = parser.add_subparsers(dest="visualize_command")

    genres_parser = visualize_subparsers.add_parser(
        "genres",
        # Always True: `genres` is a leaf subcommand of its own subparsers
        # group, not merged via `parents=[...]` like `visualize` itself, so
        # it needs its own -h regardless of the outer parser's add_help.
        add_help=True,
        help="Visualize genre distribution as a word cloud and bar chart.",
        description=(
            "Visualize the full-corpus genre distribution from the "
            "metadata-genre-prefilter full scan as a word cloud and a "
            "conventional bar chart, each in PNG and (where supported) "
            "vector formats."
        ),
    )
    genres_parser.add_argument(
        "--summary-json",
        default=sources.DEFAULT_FULL_SCAN_SUMMARY_PATH,
        help=(
            "Path to the full-scan summary.json produced by "
            "experiments/05_metadata_genre_prefilter "
            f"(default: {sources.DEFAULT_FULL_SCAN_SUMMARY_PATH})."
        ),
    )
    genres_parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory to write output figures to (default: {DEFAULT_OUTPUT_DIR}).",
    )
    genres_parser.add_argument(
        "--formats",
        default=DEFAULT_FORMATS,
        help=(
            "Comma-separated output formats, e.g. png,svg,pdf "
            f"(default: {DEFAULT_FORMATS})."
        ),
    )
    genres_parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Deterministic random seed for word-cloud layout (default: 42).",
    )

    return parser


def _parse_formats(formats: str) -> list[str]:
    return [fmt.strip().lower() for fmt in formats.split(",") if fmt.strip()]


def run_genres(args) -> int:
    """Run the genres subcommand."""
    genre_counts = sources.load_full_scan_genre_counts(args.summary_json)
    counts_with_signal = analysis.counts_with_no_signal(
        genre_counts.counts, genre_counts.no_usable_signal_count
    )

    output_dir = pathlib.Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    formats = _parse_formats(args.formats)

    for fmt in formats:
        wordcloud_fig, _ = rendering.plot_genre_wordcloud(
            genre_counts.counts,
            seed=args.seed,
            save_path=str(output_dir / f"genres_wordcloud.{fmt}"),
        )
        plt.close(wordcloud_fig)
        bar_fig, _ = rendering.plot_genre_bar_chart(
            counts_with_signal,
            save_path=str(output_dir / f"genres_bar.{fmt}"),
        )
        plt.close(bar_fig)

    manifest = {
        "source_path": genre_counts.source_path,
        "source_revision": genre_counts.source_revision,
        "total_stories": genre_counts.total_stories,
        "counted_total": analysis.total_count(counts_with_signal),
        "no_usable_signal_count": genre_counts.no_usable_signal_count,
        "counts": dict(analysis.sorted_counts(counts_with_signal)),
        "formats": formats,
        "seed": args.seed,
    }
    manifest_path = output_dir / "genres_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(json.dumps(manifest, indent=2))
    return 0


def run(
    argv: Optional[Sequence[str]] = None,
    parsed_args: Optional[argparse.Namespace] = None,
) -> int:
    """Run the visualize command family."""
    parser = build_visualize_parser()
    args = parsed_args if parsed_args is not None else parser.parse_args(argv)

    if getattr(args, "visualize_command", None) == "genres":
        return run_genres(args)

    parser.print_help(file=sys.stderr)
    return 1
