"""Regenerate the preserved Worldcon SF-versus-complement poster figure.

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
OUTPUT_DIR = PRESERVATION_ROOT / "figures/science_fiction_vs_complement"
CORPORA = ROOT / "corpora"
MANIFEST = (
    ROOT
    / "experiments/05_metadata_genre_prefilter/results/full_scan/genre_balanced_manifest.jsonl"
)
TOKENIZER_SOURCE = ROOT / "lcats/src/lcats/analysis/story_analysis.py"
SAVED_DATA = OUTPUT_DIR / "lcats_146_science_fiction_overlay_data.csv"
OUTPUT_STEM = OUTPUT_DIR / "lcats_146_non_sf_vs_science_fiction_overlay_poster"
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
    sf_counts: collections.Counter[str] = collections.Counter()
    complement_counts: collections.Counter[str] = collections.Counter()
    sample_tokens = sf_tokens = complement_tokens = 0
    sample_stories = sf_stories = complement_stories = 0

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

        if row["selection_genre"] == "science fiction":
            sf_counts.update(tokens)
            sf_tokens += len(tokens)
            sf_stories += 1
        else:
            complement_counts.update(tokens)
            complement_tokens += len(tokens)
            complement_stories += 1

    assert sample_stories == 146
    assert sf_stories == 20
    assert complement_stories == 126
    assert sample_tokens == sf_tokens + complement_tokens
    assert sample_counts == sf_counts + complement_counts
    return {
        "sample": (sample_counts, sample_tokens, sample_stories),
        "sf": (sf_counts, sf_tokens, sf_stories),
        "complement": (complement_counts, complement_tokens, complement_stories),
    }


def rates(
    counts: collections.Counter[str], total: int, terms: list[str]
) -> list[float]:
    return [counts[term] * 1_000_000 / total for term in terms]


def verify_saved_data(
    terms: list[str],
    sample_rates: list[float],
    complement_rates: list[float],
    sf_rates: list[float],
) -> float:
    with SAVED_DATA.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert [row["term"] for row in rows] == terms

    max_difference = 0.0
    for row, computed in zip(rows, zip(sample_rates, complement_rates, sf_rates)):
        saved = (
            float(row["sample_rate_per_million"]),
            float(row["non_sf_rate_per_million"]),
            float(row["science_fiction_rate_per_million"]),
        )
        max_difference = max(
            max_difference,
            *(
                abs(computed_value - saved_value)
                for computed_value, saved_value in zip(computed, saved)
            ),
        )
    assert max_difference < 5.1e-7
    return max_difference


def render(
    terms: list[str], complement_rates: list[float], sf_rates: list[float]
) -> None:
    deltas = [
        (science_fiction / baseline - 1.0) * 100.0
        for baseline, science_fiction in zip(complement_rates, sf_rates)
    ]
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
    grid = fig.add_gridspec(1, 3, width_ratios=[1, 0.25, 1.15], wspace=0.012)
    left = fig.add_subplot(grid[0, 0])
    middle = fig.add_subplot(grid[0, 1], sharey=left)
    right = fig.add_subplot(grid[0, 2], sharey=left)

    baseline_color = "#276FBF"
    baseline_edge = "#174A7E"
    reference_color = "#D1D5DB"
    reference_edge = "#64748B"
    sf_color = "#D97706"
    sf_edge = "#7C3F00"

    left.barh(
        y,
        complement_rates,
        color=baseline_color,
        edgecolor=baseline_edge,
        linewidth=1.1,
        height=0.72,
    )
    right.barh(
        y,
        complement_rates,
        color=reference_color,
        edgecolor=reference_edge,
        linewidth=1.1,
        height=0.72,
        zorder=2,
    )
    right.barh(
        y,
        sf_rates,
        color=sf_color,
        edgecolor=sf_edge,
        linewidth=1.1,
        hatch="///",
        height=0.42,
        zorder=3,
    )

    shared_max = max(max(complement_rates), max(sf_rates)) * 1.31
    left.set_xlim(shared_max, 0)
    right.set_xlim(0, shared_max)
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
        axis.set_xlabel(
            "Occurrences per Million Usable Tokens",
            fontsize=18,
            fontweight="medium",
            labelpad=15,
        )

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

    label_offset = shared_max * 0.018
    for yi, baseline_rate, sf_rate, delta in zip(y, complement_rates, sf_rates, deltas):
        right.text(
            max(baseline_rate, sf_rate) + label_offset,
            yi,
            f"{delta:+.1f}%",
            ha="left",
            va="center",
            fontsize=14.5,
            color=sf_edge if delta >= 0 else "#475569",
            fontweight="bold",
        )

    left.set_title(
        "Non-SF Complement",
        fontsize=22,
        fontweight="bold",
        color=baseline_edge,
        pad=20,
    )
    right.set_title(
        "Science Fiction Relative to Baseline",
        fontsize=22,
        fontweight="bold",
        color=sf_edge,
        pad=20,
    )
    fig.suptitle(
        "Science Fiction Versus the Non-SF Complement of the LCATS Sample",
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
                label="Non-SF baseline",
            ),
            Patch(
                facecolor=sf_color,
                edgecolor=sf_edge,
                hatch="///",
                label="Science-fiction rate",
            ),
        ],
        loc="lower right",
        bbox_to_anchor=(0.995, 0.012),
        frameon=True,
        facecolor="white",
        edgecolor="#CBD5E1",
        framealpha=0.97,
        fontsize=14,
        handlelength=1.8,
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


def main() -> None:
    groups = load_counts()
    sample_counts, sample_tokens, sample_stories = groups["sample"]
    sf_counts, sf_tokens, sf_stories = groups["sf"]
    complement_counts, complement_tokens, complement_stories = groups["complement"]

    terms = [term for term, _ in sample_counts.most_common(TOP_K)]
    sample_rates = rates(sample_counts, sample_tokens, terms)
    sf_rates = rates(sf_counts, sf_tokens, terms)
    complement_rates = rates(complement_counts, complement_tokens, terms)
    max_difference = verify_saved_data(terms, sample_rates, complement_rates, sf_rates)
    render(terms, complement_rates, sf_rates)

    print(
        json.dumps(
            {
                "sample_stories": sample_stories,
                "science_fiction_stories": sf_stories,
                "non_sf_complement_stories": complement_stories,
                "sample_usable_tokens": sample_tokens,
                "science_fiction_usable_tokens": sf_tokens,
                "non_sf_complement_usable_tokens": complement_tokens,
                "terms": terms,
                "max_abs_rate_difference_vs_saved_csv": max_difference,
                "outputs": [
                    str(OUTPUT_STEM.with_suffix(f".{ext}"))
                    for ext in ("png", "pdf", "svg")
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
