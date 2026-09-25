"""Regenerate the preserved Worldcon SF/Fantasy complement-overlay figure.

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

import preservation_guard


GENERATOR_DIR = pathlib.Path(__file__).resolve().parent
PRESERVATION_ROOT = GENERATOR_DIR.parent
ROOT = PRESERVATION_ROOT.parents[4]
OUTPUT_DIR = PRESERVATION_ROOT / "figures/science_fiction_vs_fantasy"
CORPORA = ROOT / "corpora"
MANIFEST = (
    ROOT
    / "experiments/05_metadata_genre_prefilter/results/full_scan/genre_balanced_manifest.jsonl"
)
TOKENIZER_SOURCE = ROOT / "lcats/src/lcats/analysis/story_analysis.py"
OUTPUT_STEM = (
    OUTPUT_DIR / "lcats_146_science_fiction_vs_fantasy_complement_overlay_poster"
)
OUTPUT_DATA = OUTPUT_STEM.with_suffix(".csv")
TOP_K = 20


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


def load_counts() -> dict[str, tuple[collections.Counter[str], int, int]]:
    sample_counts: collections.Counter[str] = collections.Counter()
    genre_counts = {
        "science fiction": collections.Counter(),
        "fantasy": collections.Counter(),
    }
    genre_tokens = {"science fiction": 0, "fantasy": 0}
    genre_stories = {"science fiction": 0, "fantasy": 0}
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
        sample_counts.update(tokens)
        sample_tokens += len(tokens)
        sample_stories += 1

        genre = row["selection_genre"]
        if genre in genre_counts:
            genre_counts[genre].update(tokens)
            genre_tokens[genre] += len(tokens)
            genre_stories[genre] += 1

    assert sample_stories == 146
    assert genre_stories == {"science fiction": 20, "fantasy": 20}

    result = {"sample": (sample_counts, sample_tokens, sample_stories)}
    for genre in ("science fiction", "fantasy"):
        complement_counts = sample_counts - genre_counts[genre]
        complement_tokens = sample_tokens - genre_tokens[genre]
        complement_stories = sample_stories - genre_stories[genre]
        assert complement_stories == 126
        assert sample_counts == genre_counts[genre] + complement_counts
        result[genre] = (genre_counts[genre], genre_tokens[genre], genre_stories[genre])
        result[f"non-{genre}"] = (
            complement_counts,
            complement_tokens,
            complement_stories,
        )
    return result


def rates(
    counts: collections.Counter[str], total: int, terms: list[str]
) -> list[float]:
    return [counts[term] * 1_000_000 / total for term in terms]


def render_panel(
    axis,
    *,
    y: list[int],
    baseline_rates: list[float],
    genre_rates: list[float],
    color: str,
    edge: str,
    hatch: str,
    shared_max: float,
    reversed_axis: bool,
) -> list[float]:
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

    deltas = [
        (genre_rate / baseline_rate - 1.0) * 100.0
        for baseline_rate, genre_rate in zip(baseline_rates, genre_rates)
    ]
    label_offset = shared_max * 0.018
    for yi, baseline_rate, genre_rate, delta in zip(
        y, baseline_rates, genre_rates, deltas
    ):
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


def render(
    terms: list[str],
    sf_rates: list[float],
    non_sf_rates: list[float],
    fantasy_rates: list[float],
    non_fantasy_rates: list[float],
) -> tuple[list[float], list[float]]:
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

    sf_color = "#D97706"
    sf_edge = "#7C3F00"
    fantasy_color = "#276FBF"
    fantasy_edge = "#174A7E"
    reference_color = "#D1D5DB"
    reference_edge = "#64748B"
    shared_max = (
        max(
            *sf_rates,
            *non_sf_rates,
            *fantasy_rates,
            *non_fantasy_rates,
        )
        * 1.31
    )

    sf_deltas = render_panel(
        left,
        y=y,
        baseline_rates=non_sf_rates,
        genre_rates=sf_rates,
        color=sf_color,
        edge=sf_edge,
        hatch="///",
        shared_max=shared_max,
        reversed_axis=True,
    )
    fantasy_deltas = render_panel(
        right,
        y=y,
        baseline_rates=non_fantasy_rates,
        genre_rates=fantasy_rates,
        color=fantasy_color,
        edge=fantasy_edge,
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

    left.set_title(
        "Science Fiction Relative to Baseline",
        fontsize=22,
        fontweight="bold",
        color=sf_edge,
        pad=20,
    )
    right.set_title(
        "Fantasy Relative to Baseline",
        fontsize=22,
        fontweight="bold",
        color=fantasy_edge,
        pad=20,
    )
    fig.suptitle(
        "Science Fiction and Fantasy Versus Their LCATS Sample Complements",
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
                facecolor=sf_color,
                edgecolor=sf_edge,
                hatch="///",
                label="Science-fiction rate",
            ),
            Patch(
                facecolor=fantasy_color,
                edgecolor=fantasy_edge,
                hatch="\\\\\\",
                label="Fantasy rate",
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
            OUTPUT_STEM.with_suffix(f".{extension}"),
            facecolor="white",
            bbox_inches="tight",
            pad_inches=0.15,
            **kwargs,
        )
    plt.close(fig)
    return sf_deltas, fantasy_deltas


def write_data(
    terms: list[str],
    sf_rates: list[float],
    non_sf_rates: list[float],
    sf_deltas: list[float],
    fantasy_rates: list[float],
    non_fantasy_rates: list[float],
    fantasy_deltas: list[float],
) -> None:
    with OUTPUT_DATA.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(
            [
                "rank",
                "term",
                "non_sf_complement_rate_per_million",
                "science_fiction_rate_per_million",
                "science_fiction_vs_complement_percent",
                "non_fantasy_complement_rate_per_million",
                "fantasy_rate_per_million",
                "fantasy_vs_complement_percent",
            ]
        )
        for row in zip(
            range(1, TOP_K + 1),
            terms,
            non_sf_rates,
            sf_rates,
            sf_deltas,
            non_fantasy_rates,
            fantasy_rates,
            fantasy_deltas,
        ):
            rank, term, non_sf, sf, sf_delta, non_fantasy, fantasy, fantasy_delta = row
            writer.writerow(
                [
                    rank,
                    term,
                    f"{non_sf:.6f}",
                    f"{sf:.6f}",
                    f"{sf_delta:.6f}",
                    f"{non_fantasy:.6f}",
                    f"{fantasy:.6f}",
                    f"{fantasy_delta:.6f}",
                ]
            )


def main() -> None:
    preservation_guard.verify_inputs(
        preservation_root=PRESERVATION_ROOT,
        corpora_root=CORPORA,
        selection_manifest=MANIFEST,
        tokenizer_source=TOKENIZER_SOURCE,
    )
    groups = load_counts()
    sample_counts, sample_tokens, sample_stories = groups["sample"]
    sf_counts, sf_tokens, sf_stories = groups["science fiction"]
    non_sf_counts, non_sf_tokens, non_sf_stories = groups["non-science fiction"]
    fantasy_counts, fantasy_tokens, fantasy_stories = groups["fantasy"]
    non_fantasy_counts, non_fantasy_tokens, non_fantasy_stories = groups["non-fantasy"]

    terms = [term for term, _ in sample_counts.most_common(TOP_K)]
    sf_rates = rates(sf_counts, sf_tokens, terms)
    non_sf_rates = rates(non_sf_counts, non_sf_tokens, terms)
    fantasy_rates = rates(fantasy_counts, fantasy_tokens, terms)
    non_fantasy_rates = rates(non_fantasy_counts, non_fantasy_tokens, terms)
    sf_deltas, fantasy_deltas = render(
        terms,
        sf_rates,
        non_sf_rates,
        fantasy_rates,
        non_fantasy_rates,
    )
    write_data(
        terms,
        sf_rates,
        non_sf_rates,
        sf_deltas,
        fantasy_rates,
        non_fantasy_rates,
        fantasy_deltas,
    )

    print(
        json.dumps(
            {
                "sample": {"stories": sample_stories, "usable_tokens": sample_tokens},
                "science_fiction": {"stories": sf_stories, "usable_tokens": sf_tokens},
                "non_sf_complement": {
                    "stories": non_sf_stories,
                    "usable_tokens": non_sf_tokens,
                },
                "fantasy": {
                    "stories": fantasy_stories,
                    "usable_tokens": fantasy_tokens,
                },
                "non_fantasy_complement": {
                    "stories": non_fantasy_stories,
                    "usable_tokens": non_fantasy_tokens,
                },
                "terms": terms,
                "outputs": [
                    str(OUTPUT_STEM.with_suffix(f".{ext}"))
                    for ext in ("png", "pdf", "svg", "csv")
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
