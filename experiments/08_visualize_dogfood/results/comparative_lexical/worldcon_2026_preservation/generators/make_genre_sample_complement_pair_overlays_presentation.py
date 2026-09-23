"""Regenerate the preserved Worldcon genre-pair presentation figures.

This is the historical figure generator, retained with the corresponding
outputs.  New reusable comparison behavior belongs in ``lcats.visualize``.
"""

from __future__ import annotations

import ast
import collections
import csv
import json
import os
import pathlib
import re

os.environ.setdefault("MPLCONFIGDIR", "/tmp/lcats-matplotlib")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS


GENERATOR_DIR = pathlib.Path(__file__).resolve().parent
PRESERVATION_ROOT = GENERATOR_DIR.parent
ROOT = PRESERVATION_ROOT.parents[4]
FIGURES_ROOT = PRESERVATION_ROOT / "figures"
CORPORA = ROOT / "corpora"
MANIFEST = (
    ROOT
    / "experiments/05_metadata_genre_prefilter/results/full_scan/genre_balanced_manifest.jsonl"
)
TOKENIZER_SOURCE = ROOT / "lcats/src/lcats/analysis/story_analysis.py"
TOP_K = 20
PAIRS = (
    ("horror", "humor"),
    ("mystery", "romance"),
    ("western", "adventure"),
)
EXPECTED_STORIES = {
    "adventure": 6,
    "fantasy": 20,
    "horror": 20,
    "humor": 20,
    "mystery": 20,
    "romance": 20,
    "science fiction": 20,
    "western": 20,
}


def load_lcats_stopwords() -> frozenset[str]:
    module = ast.parse(TOKENIZER_SOURCE.read_text(encoding="utf-8"))
    for node in module.body:
        if (
            isinstance(node, ast.AnnAssign)
            and getattr(node.target, "id", None) == "_STOPWORDS"
        ):
            call = node.value
            if isinstance(call, ast.Call) and call.args:
                return frozenset(ast.literal_eval(call.args[0]))
    raise RuntimeError("Could not locate LCATS _STOPWORDS literal")


STOPWORDS = load_lcats_stopwords() | frozenset(ENGLISH_STOP_WORDS)


def keywords(text: str) -> list[str]:
    raw = re.split(r"[^A-Za-z]+", text.lower())
    return [term for term in raw if len(term) >= 3 and term not in STOPWORDS]


def load_counts():
    sample_counts: collections.Counter[str] = collections.Counter()
    genre_counts = {genre: collections.Counter() for genre in EXPECTED_STORIES}
    genre_tokens = {genre: 0 for genre in EXPECTED_STORIES}
    genre_stories = {genre: 0 for genre in EXPECTED_STORIES}
    sample_tokens = 0
    sample_stories = 0

    rows = [
        json.loads(line)
        for line in MANIFEST.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    for row in rows:
        story = json.loads((CORPORA / row["story_path"]).read_text(encoding="utf-8"))
        tokens = keywords(story["body"])
        genre = row["selection_genre"]
        sample_counts.update(tokens)
        sample_tokens += len(tokens)
        sample_stories += 1
        genre_counts[genre].update(tokens)
        genre_tokens[genre] += len(tokens)
        genre_stories[genre] += 1

    assert sample_stories == 146
    assert genre_stories == EXPECTED_STORIES
    return (
        sample_counts,
        sample_tokens,
        sample_stories,
        genre_counts,
        genre_tokens,
        genre_stories,
    )


def rates(
    counts: collections.Counter[str], total: int, terms: list[str]
) -> list[float]:
    return [counts[term] * 1_000_000 / total for term in terms]


def display_name(genre: str) -> str:
    return genre.title()


def slug(genre: str) -> str:
    return genre.replace(" ", "_")


def render_panel(
    axis,
    *,
    y,
    baseline_rates,
    genre_rates,
    color,
    edge,
    hatch,
    shared_max,
    reversed_axis,
):
    reference_color = "#D1D5DB"
    reference_edge = "#64748B"
    axis.barh(
        y,
        baseline_rates,
        color=reference_color,
        edgecolor=reference_edge,
        linewidth=1.1,
        height=0.72,
        zorder=2,
    )
    axis.barh(
        y,
        genre_rates,
        color=color,
        edgecolor=edge,
        linewidth=1.1,
        hatch=hatch,
        height=0.42,
        zorder=3,
    )
    axis.set_xlim(shared_max, 0) if reversed_axis else axis.set_xlim(0, shared_max)

    deltas = []
    label_offset = shared_max * 0.018
    for yi, baseline_rate, genre_rate in zip(y, baseline_rates, genre_rates):
        delta = (genre_rate / baseline_rate - 1.0) * 100.0
        deltas.append(delta)
        axis.text(
            max(baseline_rate, genre_rate) + label_offset,
            yi,
            f"{delta:+.1f}%",
            ha="right" if reversed_axis else "left",
            va="center",
            fontsize=14.5,
            color=edge if delta >= 0 else "#475569",
            fontweight="bold",
        )
    return deltas


def render_pair(
    *,
    left_genre,
    right_genre,
    terms,
    left_rates,
    left_baseline_rates,
    right_rates,
    right_baseline_rates,
    output_stem,
):
    y = list(range(len(terms)))
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
        }
    )
    fig = plt.figure(figsize=(18, 12), facecolor="white")
    grid = fig.add_gridspec(1, 3, width_ratios=[1.15, 0.36, 1.15], wspace=0.012)
    left = fig.add_subplot(grid[0, 0])
    middle = fig.add_subplot(grid[0, 1], sharey=left)
    right = fig.add_subplot(grid[0, 2], sharey=left)

    left_color, left_edge = "#D97706", "#7C3F00"
    right_color, right_edge = "#276FBF", "#174A7E"
    reference_color, reference_edge = "#D1D5DB", "#64748B"
    shared_max = (
        max(
            *left_rates,
            *left_baseline_rates,
            *right_rates,
            *right_baseline_rates,
        )
        * 1.31
    )

    left_deltas = render_panel(
        left,
        y=y,
        baseline_rates=left_baseline_rates,
        genre_rates=left_rates,
        color=left_color,
        edge=left_edge,
        hatch="///",
        shared_max=shared_max,
        reversed_axis=True,
    )
    right_deltas = render_panel(
        right,
        y=y,
        baseline_rates=right_baseline_rates,
        genre_rates=right_rates,
        color=right_color,
        edge=right_edge,
        hatch="\\\\\\",
        shared_max=shared_max,
        reversed_axis=False,
    )
    left.set_ylim(len(terms) - 0.35, -0.65)

    for axis in (left, right):
        axis.set_yticks(y)
        axis.tick_params(axis="y", left=False, labelleft=False)
        axis.grid(axis="x", color="#D6DCE3", linewidth=0.9, alpha=0.95)
        axis.set_axisbelow(True)
        axis.spines[["top", "left", "right"]].set_visible(False)
        axis.spines["bottom"].set_color("#7A8490")
        axis.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:,.0f}"))
        axis.tick_params(axis="x", labelsize=15, colors="#334155", pad=7)

    middle.set_xlim(0, 1)
    middle.set_ylim(len(terms) - 0.35, -0.65)
    middle.axis("off")
    for yi, term in zip(y, terms):
        middle.text(
            0.5,
            yi,
            term,
            ha="center",
            va="center",
            fontsize=18,
            color="#111827",
            fontweight="medium",
        )

    left_name, right_name = display_name(left_genre), display_name(right_genre)
    left.set_title(
        f"{left_name} Relative to Baseline",
        fontsize=22,
        fontweight="bold",
        color=left_edge,
        pad=20,
    )
    right.set_title(
        f"{right_name} Relative to Baseline",
        fontsize=22,
        fontweight="bold",
        color=right_edge,
        pad=20,
    )
    fig.suptitle(
        f"{left_name} and {right_name} Versus Their LCATS Sample Complements",
        fontsize=27,
        fontweight="bold",
        color="#111827",
        y=0.977,
    )
    right.legend(
        handles=[
            Patch(
                facecolor=reference_color,
                edgecolor=reference_edge,
                label="Respective complement",
            ),
            Patch(
                facecolor=left_color,
                edgecolor=left_edge,
                hatch="///",
                label=f"{left_name} rate",
            ),
            Patch(
                facecolor=right_color,
                edgecolor=right_edge,
                hatch="\\\\\\",
                label=f"{right_name} rate",
            ),
        ],
        loc="lower right",
        bbox_to_anchor=(0.995, 0.012),
        frameon=True,
        facecolor="white",
        edgecolor="#CBD5E1",
        framealpha=0.97,
        fontsize=13.5,
        handlelength=1.8,
    )
    fig.text(
        0.5,
        0.025,
        "Occurrences per Million Usable Tokens",
        ha="center",
        fontsize=18,
        fontweight="medium",
        color="#111827",
    )
    fig.subplots_adjust(top=0.885, bottom=0.095, left=0.052, right=0.975)
    for extension in ("png", "pdf", "svg"):
        kwargs = {"dpi": 240} if extension == "png" else {}
        fig.savefig(
            output_stem.with_suffix(f".{extension}"),
            facecolor="white",
            bbox_inches="tight",
            pad_inches=0.15,
            **kwargs,
        )
    plt.close(fig)
    return left_deltas, right_deltas


def write_data(
    *,
    output_stem,
    terms,
    left_genre,
    left_baseline_rates,
    left_rates,
    left_deltas,
    right_genre,
    right_baseline_rates,
    right_rates,
    right_deltas,
):
    left_slug, right_slug = slug(left_genre), slug(right_genre)
    with output_stem.with_suffix(".csv").open(
        "w", encoding="utf-8", newline=""
    ) as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(
            [
                "rank",
                "term",
                f"non_{left_slug}_complement_rate_per_million",
                f"{left_slug}_rate_per_million",
                f"{left_slug}_vs_complement_percent",
                f"non_{right_slug}_complement_rate_per_million",
                f"{right_slug}_rate_per_million",
                f"{right_slug}_vs_complement_percent",
            ]
        )
        for row in zip(
            range(1, TOP_K + 1),
            terms,
            left_baseline_rates,
            left_rates,
            left_deltas,
            right_baseline_rates,
            right_rates,
            right_deltas,
        ):
            writer.writerow([row[0], row[1], *[f"{value:.6f}" for value in row[2:]]])


def main() -> None:
    (
        sample_counts,
        sample_tokens,
        sample_stories,
        genre_counts,
        genre_tokens,
        genre_stories,
    ) = load_counts()
    terms = [term for term, _ in sample_counts.most_common(TOP_K)]
    summary = {
        "sample": {"stories": sample_stories, "usable_tokens": sample_tokens},
        "terms": terms,
        "pairs": [],
    }

    for left_genre, right_genre in PAIRS:
        pair_data = {}
        for genre in (left_genre, right_genre):
            complement_counts = sample_counts - genre_counts[genre]
            complement_tokens = sample_tokens - genre_tokens[genre]
            complement_stories = sample_stories - genre_stories[genre]
            assert sample_counts == genre_counts[genre] + complement_counts
            pair_data[genre] = {
                "rates": rates(genre_counts[genre], genre_tokens[genre], terms),
                "baseline_rates": rates(complement_counts, complement_tokens, terms),
                "stories": genre_stories[genre],
                "tokens": genre_tokens[genre],
                "complement_stories": complement_stories,
                "complement_tokens": complement_tokens,
            }

        output_dir = FIGURES_ROOT / f"{slug(left_genre)}_vs_{slug(right_genre)}"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_stem = output_dir / (
            f"lcats_146_{slug(left_genre)}_vs_{slug(right_genre)}"
            "_complement_overlay_presentation"
        )
        left_deltas, right_deltas = render_pair(
            left_genre=left_genre,
            right_genre=right_genre,
            terms=terms,
            left_rates=pair_data[left_genre]["rates"],
            left_baseline_rates=pair_data[left_genre]["baseline_rates"],
            right_rates=pair_data[right_genre]["rates"],
            right_baseline_rates=pair_data[right_genre]["baseline_rates"],
            output_stem=output_stem,
        )
        write_data(
            output_stem=output_stem,
            terms=terms,
            left_genre=left_genre,
            left_baseline_rates=pair_data[left_genre]["baseline_rates"],
            left_rates=pair_data[left_genre]["rates"],
            left_deltas=left_deltas,
            right_genre=right_genre,
            right_baseline_rates=pair_data[right_genre]["baseline_rates"],
            right_rates=pair_data[right_genre]["rates"],
            right_deltas=right_deltas,
        )
        summary["pairs"].append(
            {
                "genres": [left_genre, right_genre],
                left_genre: {
                    key: value
                    for key, value in pair_data[left_genre].items()
                    if key not in {"rates", "baseline_rates"}
                },
                right_genre: {
                    key: value
                    for key, value in pair_data[right_genre].items()
                    if key not in {"rates", "baseline_rates"}
                },
                "outputs": [
                    str(output_stem.with_suffix(f".{extension}"))
                    for extension in ("png", "pdf", "svg", "csv")
                ],
            }
        )

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
