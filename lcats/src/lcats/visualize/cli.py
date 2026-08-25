"""CLI for lcats visualize."""

import argparse
import csv
import json
import pathlib
import sys
from typing import Optional, Sequence

import matplotlib.pyplot as plt

from lcats.visualize import analysis
from lcats.visualize import comparison
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

    tfidf_parser = visualize_subparsers.add_parser(
        "tfidf",
        add_help=True,
        help="Visualize TF-IDF top distinguishing terms as a bar chart.",
        description=(
            "Visualize the top TF-IDF-ranked terms for a comparison group: "
            "by default the whole corpus, or a genre subset selected with "
            "--genre, as a conventional bar chart. Story is the document "
            "unit; IDF is fit across the whole corpus regardless of "
            "--genre, so a genre-subset run ranks terms distinguishing "
            "that subset from the corpus at large. Preprocessing defaults (from "
            "lcats.analysis.story_analysis.get_keywords): terms are "
            "lowercased, restricted to ASCII alphabetic tokens, require a "
            "minimum length of 3 characters, and are filtered through a "
            "hardcoded stopword set."
        ),
    )
    tfidf_parser.add_argument(
        "--corpus-root",
        default=sources.DEFAULT_CORPORA_ROOT,
        help=f"Root directory of story collections (default: {sources.DEFAULT_CORPORA_ROOT}).",
    )
    tfidf_parser.add_argument(
        "--genre",
        default=None,
        help=(
            "If provided, rank terms for stories whose candidate genres "
            "(from candidates.jsonl) include this genre. Omit to rank terms "
            "across the whole corpus."
        ),
    )
    tfidf_parser.add_argument(
        "--candidates-jsonl",
        default=sources.DEFAULT_CANDIDATES_JSONL_PATH,
        help=(
            "Path to the full-scan candidates.jsonl (used only with "
            f"--genre; default: {sources.DEFAULT_CANDIDATES_JSONL_PATH})."
        ),
    )
    tfidf_parser.add_argument(
        "--top-k",
        type=int,
        default=20,
        help="Number of top terms to include; must be >= 1 (default: 20).",
    )
    tfidf_parser.add_argument(
        "--contrast",
        action="store_true",
        help=(
            "Rank terms by group-vs-complement mean TF-IDF difference "
            "instead of within-group mean salience -- a genuine comparison "
            "against the rest of the corpus, not just the selected group's "
            "own terms. Requires --genre (or another comparison-group "
            "selector); a whole-corpus run has no complement to contrast "
            "against."
        ),
    )
    tfidf_parser.add_argument(
        "--output-dir",
        default="tfidf_viz",
        help="Directory to write output figures to (default: tfidf_viz).",
    )
    tfidf_parser.add_argument(
        "--formats",
        default=DEFAULT_FORMATS,
        help=(
            "Comma-separated output formats, e.g. png,svg,pdf "
            f"(default: {DEFAULT_FORMATS})."
        ),
    )

    topics_parser = visualize_subparsers.add_parser(
        "topics",
        add_help=True,
        help="Visualize a classical topic-model baseline as per-topic bar charts.",
        description=(
            "Visualize a classical topic-model baseline (scikit-learn NMF) "
            "over the whole corpus as one top-weighted-term bar chart per "
            "topic. This is a baseline, not a final technique choice -- "
            "embedding-based topic models (e.g. BERTopic) are explicitly "
            "deferred. Preprocessing defaults (from "
            "lcats.analysis.story_analysis.get_keywords): terms are "
            "lowercased, restricted to ASCII alphabetic tokens, require a "
            "minimum length of 3 characters, and are filtered through a "
            "hardcoded stopword set. NMF's initialization strategy is a "
            "documented CLI option (--init); note that scikit-learn's "
            "nndsvd-family initializers (the default and its variants) "
            "compute their starting point via a randomized SVD seeded by "
            "--seed, so --seed affects the fitted topics under every "
            "--init choice, not only 'random'."
        ),
    )
    topics_parser.add_argument(
        "--corpus-root",
        default=sources.DEFAULT_CORPORA_ROOT,
        help=f"Root directory of story collections (default: {sources.DEFAULT_CORPORA_ROOT}).",
    )
    topics_parser.add_argument(
        "--n-topics",
        type=int,
        default=analysis.DEFAULT_N_TOPICS,
        help=(
            "Number of topics to fit; must be >= 1 "
            f"(default: {analysis.DEFAULT_N_TOPICS})."
        ),
    )
    topics_parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Number of top terms per topic to include; must be >= 1 (default: 10).",
    )
    topics_parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help=(
            "Random seed for the NMF solver and its initialization " "(default: 42)."
        ),
    )
    topics_parser.add_argument(
        "--init",
        choices=analysis.NMF_INIT_CHOICES,
        default=analysis.DEFAULT_NMF_INIT,
        help=(
            "NMF initialization strategy " f"(default: {analysis.DEFAULT_NMF_INIT})."
        ),
    )
    topics_parser.add_argument(
        "--max-iter",
        type=int,
        default=analysis.DEFAULT_NMF_MAX_ITER,
        help=(
            "Maximum NMF solver iterations; must be >= 1 "
            f"(default: {analysis.DEFAULT_NMF_MAX_ITER})."
        ),
    )
    topics_parser.add_argument(
        "--output-dir",
        default="topics_viz",
        help="Directory to write output figures to (default: topics_viz).",
    )
    topics_parser.add_argument(
        "--formats",
        default=DEFAULT_FORMATS,
        help=(
            "Comma-separated output formats, e.g. png,svg,pdf "
            f"(default: {DEFAULT_FORMATS})."
        ),
    )

    compare_parser = visualize_subparsers.add_parser(
        "compare",
        add_help=True,
        help="Render aligned comparative lexical bar charts.",
        description=(
            "Render mirrored or reference-overlay lexical comparisons from an "
            "explicit universe and selectors. The command writes figures plus "
            "the authoritative comparison CSV and manifest used to draw them."
        ),
    )
    compare_parser.add_argument(
        "--corpus-root",
        default=sources.DEFAULT_CORPORA_ROOT,
        help=f"Root directory of story collections (default: {sources.DEFAULT_CORPORA_ROOT}).",
    )
    compare_parser.add_argument(
        "--candidates-jsonl",
        default=sources.DEFAULT_CANDIDATES_JSONL_PATH,
        help=(
            "Path to the full-scan candidates.jsonl "
            f"(default: {sources.DEFAULT_CANDIDATES_JSONL_PATH})."
        ),
    )
    compare_parser.add_argument(
        "--universe",
        choices=("corpus", "manifest"),
        default="corpus",
        help="Comparison universe source (default: corpus).",
    )
    compare_parser.add_argument(
        "--manifest",
        default=None,
        help="Manifest JSONL path when --universe manifest is used.",
    )
    compare_parser.add_argument(
        "--left-genre",
        default=None,
        help="Left/reference genre selector. Omit for all stories unless --right-reference is set.",
    )
    compare_parser.add_argument(
        "--right-genre",
        default=None,
        help="Right/target genre selector. Omit for all stories.",
    )
    compare_parser.add_argument(
        "--membership-mode",
        choices=tuple(mode.value for mode in comparison.MembershipMode),
        default=comparison.MembershipMode.CANDIDATE.value,
        help="Genre membership semantics for genre selectors (default: candidate).",
    )
    compare_parser.add_argument(
        "--right-reference",
        choices=("none", "complement", "universe"),
        default="none",
        help=(
            "Derive the left/reference selector from the right selector: "
            "none, complement, or universe (default: none)."
        ),
    )
    compare_parser.add_argument(
        "--metric",
        choices=tuple(metric.value for metric in comparison.MetricName),
        default=comparison.MetricName.RAW_COUNT.value,
        help="Metric for both sides unless side-specific flags override it.",
    )
    compare_parser.add_argument(
        "--left-metric",
        choices=tuple(metric.value for metric in comparison.MetricName),
        default=None,
        help="Metric for the left/reference side.",
    )
    compare_parser.add_argument(
        "--right-metric",
        choices=tuple(metric.value for metric in comparison.MetricName),
        default=None,
        help="Metric for the right/target side.",
    )
    compare_parser.add_argument(
        "--style",
        choices=("mirrored", "reference-overlay"),
        default="mirrored",
        help="Chart style to render (default: mirrored).",
    )
    compare_parser.add_argument(
        "--top-k",
        type=int,
        default=20,
        help="Number of aligned terms to include; must be >= 1 (default: 20).",
    )
    compare_parser.add_argument(
        "--vocabulary",
        choices=tuple(policy.value for policy in comparison.VocabularyPolicy),
        default=comparison.VocabularyPolicy.TOP_ABSOLUTE_DIFFERENCE.value,
        help="Vocabulary policy used before rendering.",
    )
    compare_parser.add_argument(
        "--order-by",
        choices=tuple(ordering.value for ordering in comparison.Ordering),
        default=comparison.Ordering.ABSOLUTE_DIFFERENCE.value,
        help="Term ordering policy (default: absolute_difference).",
    )
    compare_parser.add_argument(
        "--include-stopwords",
        action="store_true",
        help="Include stopwords in lexical tokenization.",
    )
    compare_parser.add_argument(
        "--min-length",
        type=int,
        default=3,
        help="Minimum alphabetic token length (default: 3).",
    )
    compare_parser.add_argument(
        "--output-dir",
        default="compare_viz",
        help="Directory to write output figures and data to (default: compare_viz).",
    )
    compare_parser.add_argument(
        "--formats",
        default=DEFAULT_FORMATS,
        help=(
            "Comma-separated figure output formats, e.g. png,svg,pdf "
            f"(default: {DEFAULT_FORMATS})."
        ),
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
                "candidates.jsonl -- requires a complete one-to-one join: "
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


def run_tfidf(args) -> int:
    """Run the tfidf subcommand."""
    if args.top_k < 1:
        raise ValueError(f"--top-k must be >= 1, got {args.top_k}.")
    if args.contrast and not args.genre:
        raise ValueError(
            "--contrast requires --genre (or another comparison-group "
            "selector): a whole-corpus run has no complement to contrast "
            "against."
        )

    corpus = sources.load_corpus_stories(args.corpus_root)
    story_ids = list(corpus.texts.keys())
    corpus_texts = [corpus.texts[story_id] for story_id in story_ids]

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
                "candidates.jsonl -- requires a complete one-to-one join: "
                f"{len(missing_from_corpus)} candidates.jsonl story_id(s) not "
                f"found in the corpus (e.g. {missing_from_corpus[:3]!r}), "
                f"{len(missing_from_candidates)} corpus story_id(s) not found "
                f"in candidates.jsonl (e.g. {missing_from_candidates[:3]!r})."
            )
        group_indices = [
            i
            for i, story_id in enumerate(story_ids)
            if args.genre in membership.story_genres[story_id]
        ]
    else:
        group_indices = list(range(len(story_ids)))

    scores = analysis.tfidf_top_terms(
        corpus_texts, group_indices, top_k=args.top_k, contrast=args.contrast
    )
    if not scores:
        raise ValueError(
            "No TF-IDF terms to visualize: the selected stories "
            f"(story_count={len(group_indices)}) yielded no usable tokens "
            "after preprocessing, or (in --contrast mode) no term scored "
            "higher in the group than in its complement. Try a different "
            "--genre or check the corpus contents."
        )

    output_dir = pathlib.Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    formats = _parse_formats(args.formats)

    for fmt in formats:
        fig, _ = rendering.plot_tfidf_bar_chart(
            scores,
            save_path=str(output_dir / f"tfidf_bar.{fmt}"),
        )
        plt.close(fig)

    manifest = {
        "corpus_source_path": corpus.source_path,
        "corpus_source_revision": corpus.source_revision,
        "story_count": len(group_indices),
        "top_terms": scores,
        "formats": formats,
        "top_k": args.top_k,
        "mode": "contrast" if args.contrast else "salience",
    }
    if membership is not None:
        manifest["genre"] = args.genre
        manifest["candidates_source_path"] = membership.source_path
        manifest["candidates_source_revision"] = membership.source_revision

    manifest_path = output_dir / "tfidf_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(json.dumps(manifest, indent=2))
    return 0


def run_topics(args) -> int:
    """Run the topics subcommand."""
    if args.n_topics < 1:
        raise ValueError(f"--n-topics must be >= 1, got {args.n_topics}.")
    if args.top_k < 1:
        raise ValueError(f"--top-k must be >= 1, got {args.top_k}.")
    if args.max_iter < 1:
        raise ValueError(f"--max-iter must be >= 1, got {args.max_iter}.")

    corpus = sources.load_corpus_stories(args.corpus_root)
    corpus_texts = list(corpus.texts.values())

    topics = analysis.topic_model(
        corpus_texts,
        n_topics=args.n_topics,
        top_k=args.top_k,
        seed=args.seed,
        max_iter=args.max_iter,
        init=args.init,
    )
    if not topics:
        raise ValueError(
            "No topics to visualize: the corpus "
            f"(story_count={len(corpus_texts)}) yielded no usable tokens "
            "after preprocessing, or no topic could be fit. Check the "
            "corpus contents or --n-topics."
        )

    output_dir = pathlib.Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    formats = _parse_formats(args.formats)

    for topic_label, term_weights in topics.items():
        for fmt in formats:
            fig, _ = rendering.plot_topic_bar_chart(
                term_weights,
                topic_label=topic_label,
                save_path=str(output_dir / f"{topic_label}_bar.{fmt}"),
            )
            plt.close(fig)

    manifest = {
        "corpus_source_path": corpus.source_path,
        "corpus_source_revision": corpus.source_revision,
        "story_count": len(corpus_texts),
        "n_topics": len(topics),
        "topics": topics,
        "formats": formats,
        "top_k": args.top_k,
        "seed": args.seed,
        "max_iter": args.max_iter,
        "init": args.init,
    }
    manifest_path = output_dir / "topics_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(json.dumps(manifest, indent=2))
    return 0


def run_compare(args) -> int:
    """Run the compare subcommand."""
    if args.top_k < 1:
        raise ValueError(f"--top-k must be >= 1, got {args.top_k}.")
    if args.min_length < 1:
        raise ValueError(f"--min-length must be >= 1, got {args.min_length}.")
    if args.universe == "manifest" and not args.manifest:
        raise ValueError("--universe manifest requires --manifest.")
    if args.membership_mode == comparison.MembershipMode.PRIMARY.value:
        raise ValueError(
            "--membership-mode primary is not available from the current "
            "comparison source adapters; use candidate or selection."
        )
    if (
        args.membership_mode == comparison.MembershipMode.SELECTION.value
        and not args.manifest
    ):
        raise ValueError("--membership-mode selection requires --manifest.")
    if args.order_by == comparison.Ordering.EXPLICIT.value:
        raise ValueError(
            "--order-by explicit requires an explicit term list, which the "
            "compare CLI does not expose yet."
        )

    corpus = sources.load_comparison_corpus(
        corpora_root=args.corpus_root,
        candidates_jsonl_path=args.candidates_jsonl,
        manifest_jsonl_path=args.manifest,
    )
    spec = _build_comparison_spec(args)
    result = analysis.compare_lexical(corpus, spec)
    if not result.rows:
        raise ValueError(
            "No comparison terms to visualize: the selected universe and "
            "selectors yielded no aligned vocabulary after preprocessing."
        )

    output_dir = pathlib.Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    formats = _parse_formats(args.formats)

    style_slug = spec.style.value
    for fmt in formats:
        figure_path = output_dir / f"comparison_{style_slug}.{fmt}"
        if spec.style == comparison.ComparisonStyle.REFERENCE_OVERLAY:
            fig, _ = rendering.plot_reference_overlay_comparison(
                result,
                title=_comparison_title(result),
                save_path=str(figure_path),
            )
        else:
            fig, _ = rendering.plot_mirrored_comparison(
                result,
                title=_comparison_title(result),
                save_path=str(figure_path),
            )
        plt.close(fig)

    csv_path = output_dir / "comparison.csv"
    _write_comparison_csv(result, csv_path)
    manifest = {
        **result.manifest,
        "cli": {
            "command": "lcats visualize compare",
            "outputs": {
                "csv": str(csv_path),
                "figures": [
                    str(output_dir / f"comparison_{style_slug}.{fmt}")
                    for fmt in formats
                ],
            },
        },
    }
    manifest_path = output_dir / "comparison_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(json.dumps(manifest, indent=2))
    return 0


def _build_comparison_spec(args) -> comparison.ComparisonSpec:
    membership_mode = comparison.MembershipMode(args.membership_mode)
    right_selector = _genre_or_all_selector(args.right_genre, membership_mode, "right")
    if args.right_reference == "complement":
        left_selector = comparison.Selector(
            comparison.SelectorKind.COMPLEMENT,
            base=right_selector,
            label=f"U - {right_selector.label}",
        )
    elif args.right_reference == "universe":
        left_selector = comparison.Selector(comparison.SelectorKind.ALL, label="U")
    else:
        left_selector = _genre_or_all_selector(args.left_genre, membership_mode, "left")

    left_metric = comparison.MetricSpec(
        comparison.MetricName(args.left_metric or args.metric)
    )
    right_metric = comparison.MetricSpec(
        comparison.MetricName(args.right_metric or args.metric)
    )
    style = comparison.ComparisonStyle(args.style.replace("-", "_"))
    universe = comparison.UniverseSpec(kind=args.universe)
    if args.universe == "manifest":
        manifest_selection = sources.load_manifest_selection(args.manifest)
        universe = comparison.UniverseSpec(
            kind="manifest",
            story_ids=manifest_selection.story_ids,
            source_path=manifest_selection.source_path,
            source_revision=manifest_selection.source_revision,
        )

    return comparison.ComparisonSpec(
        universe=universe,
        left=left_selector,
        right=right_selector,
        left_metric=left_metric,
        right_metric=right_metric,
        token_filter=comparison.TokenFilter(
            include_stopwords=args.include_stopwords,
            min_length=args.min_length,
        ),
        vocabulary=comparison.VocabularySpec(
            policy=comparison.VocabularyPolicy(args.vocabulary),
            top_k=args.top_k,
        ),
        ordering=comparison.OrderingSpec(comparison.Ordering(args.order_by)),
        style=style,
        output_formats=tuple(_parse_formats(args.formats)),
    )


def _genre_or_all_selector(
    genre: str | None,
    membership_mode: comparison.MembershipMode,
    label_prefix: str,
) -> comparison.Selector:
    if genre:
        return comparison.Selector(
            comparison.SelectorKind.GENRE,
            genre=genre,
            membership_mode=membership_mode,
            label=f"{label_prefix}: {membership_mode.value}:{genre}",
        )
    return comparison.Selector(comparison.SelectorKind.ALL, label=f"{label_prefix}: U")


def _write_comparison_csv(
    result: comparison.ComparisonResult, csv_path: pathlib.Path
) -> None:
    rows = result.table()
    fieldnames = list(rows[0])
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _comparison_title(result: comparison.ComparisonResult) -> str:
    left = result.manifest["left"]["label"]
    right = result.manifest["right"]["label"]
    return f"{right} vs {left}"


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
    if visualize_command == "tfidf":
        return run_tfidf(args)
    if visualize_command == "topics":
        return run_topics(args)
    if visualize_command == "compare":
        return run_compare(args)

    parser.print_help(file=sys.stderr)
    return 1
