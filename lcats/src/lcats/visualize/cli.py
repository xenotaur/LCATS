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

    words_parser = visualize_subparsers.add_parser(
        "words",
        add_help=True,
        help="Visualize word frequency as a word cloud and bar chart.",
        description=(
            "Visualize word frequency across the whole corpus, or a genre "
            "subset, as a word cloud and a conventional ranked-frequency "
            "bar chart, each in PNG and (where supported) vector formats. "
            "Preprocessing defaults (from lcats.analysis.story_analysis."
            "get_keywords): terms are lowercased, restricted to ASCII "
            "alphabetic tokens, require a minimum length of 3 characters, "
            "and are filtered through a hardcoded stopword set."
        ),
    )
    words_parser.add_argument(
        "--corpus-root",
        default=sources.DEFAULT_CORPORA_ROOT,
        help=f"Root directory of story collections (default: {sources.DEFAULT_CORPORA_ROOT}).",
    )
    words_parser.add_argument(
        "--genre",
        default=None,
        help=(
            "If provided, restrict to stories whose candidate genres "
            "(from candidates.jsonl) include this genre. Omit for the "
            "whole-corpus view."
        ),
    )
    words_parser.add_argument(
        "--candidates-jsonl",
        default=sources.DEFAULT_CANDIDATES_JSONL_PATH,
        help=(
            "Path to the full-scan candidates.jsonl (used only with "
            f"--genre; default: {sources.DEFAULT_CANDIDATES_JSONL_PATH})."
        ),
    )
    words_parser.add_argument(
        "--top-k",
        type=int,
        default=50,
        help="Number of top words to include; must be >= 1 (default: 50).",
    )
    words_parser.add_argument(
        "--output-dir",
        default="words_viz",
        help="Directory to write output figures to (default: words_viz).",
    )
    words_parser.add_argument(
        "--formats",
        default=DEFAULT_FORMATS,
        help=(
            "Comma-separated output formats, e.g. png,svg,pdf "
            f"(default: {DEFAULT_FORMATS})."
        ),
    )
    words_parser.add_argument(
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


def run_words(args) -> int:
    """Run the words subcommand."""
    if args.top_k < 1:
        raise ValueError(f"--top-k must be >= 1, got {args.top_k}.")

    corpus = sources.load_corpus_stories(args.corpus_root)

    membership = None
    if args.genre:
        membership = sources.load_candidates_genre_membership(args.candidates_jsonl)
        candidate_ids = set(membership.story_genres)
        corpus_ids = set(corpus.texts)
        missing_from_corpus = sorted(candidate_ids - corpus_ids)
        missing_from_candidates = sorted(corpus_ids - candidate_ids)
        if missing_from_corpus or missing_from_candidates:
            raise ValueError(
                "join coverage incomplete between the corpus snapshot and "
                "candidates.jsonl -- required a complete one-to-one join: "
                f"{len(missing_from_corpus)} candidates.jsonl story_id(s) not "
                f"found in the corpus (e.g. {missing_from_corpus[:3]!r}), "
                f"{len(missing_from_candidates)} corpus story_id(s) not found "
                f"in candidates.jsonl (e.g. {missing_from_candidates[:3]!r})."
            )
        selected_ids = [
            story_id
            for story_id, genres in membership.story_genres.items()
            if args.genre in genres
        ]
        texts = [corpus.texts[story_id] for story_id in selected_ids]
    else:
        selected_ids = list(corpus.texts.keys())
        texts = list(corpus.texts.values())

    frequencies = analysis.word_frequencies(texts, top_k=args.top_k)
    if not frequencies:
        raise ValueError(
            "No word frequencies to visualize: the selected stories "
            f"(story_count={len(texts)}) yielded no usable tokens after "
            "preprocessing. Try a different --genre or check the corpus "
            "contents."
        )

    output_dir = pathlib.Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    formats = _parse_formats(args.formats)

    for fmt in formats:
        wordcloud_fig, _ = rendering.plot_word_frequency_wordcloud(
            frequencies,
            seed=args.seed,
            save_path=str(output_dir / f"words_wordcloud.{fmt}"),
        )
        plt.close(wordcloud_fig)
        bar_fig, _ = rendering.plot_word_frequency_bar_chart(
            frequencies,
            save_path=str(output_dir / f"words_bar.{fmt}"),
        )
        plt.close(bar_fig)

    manifest = {
        "corpus_source_path": corpus.source_path,
        "corpus_source_revision": corpus.source_revision,
        "story_count": len(texts),
        "top_words": frequencies,
        "formats": formats,
        "seed": args.seed,
        "top_k": args.top_k,
    }
    if membership is not None:
        manifest["genre"] = args.genre
        manifest["candidates_source_path"] = membership.source_path
        manifest["candidates_source_revision"] = membership.source_revision

    manifest_path = output_dir / "words_manifest.json"
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

    visualize_command = getattr(args, "visualize_command", None)
    if visualize_command == "genres":
        return run_genres(args)
    if visualize_command == "words":
        return run_words(args)

    parser.print_help(file=sys.stderr)
    return 1
