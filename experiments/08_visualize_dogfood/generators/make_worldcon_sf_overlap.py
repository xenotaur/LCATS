"""Prototype Option 1 + Option 4 Worldcon SF overlap visualization.

This is an experiment-local, read-only join of the 146-story genre validation
records and the persisted Knight/Suvin sidecars.  It writes only under the
experiment's visualization figure directory.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Patch
from matplotlib.ticker import MaxNLocator
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "experiments/08_visualize_dogfood/figures/worldcon_sf_overlap"
GENRE_ROOT = ROOT / "experiments/05_metadata_genre_prefilter/results/full_scan"
SF_ROOT = (
    ROOT
    / "lcats/experimental/science_fiction_analysis_trial/results/worldcon_spike/"
    / "opus_staged/sample-146-20260930T194818Z"
)
GENRES = (
    "adventure",
    "fantasy",
    "horror",
    "humor",
    "mystery",
    "romance",
    "science fiction",
    "western",
)


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def assessments(row: dict) -> dict[str, dict]:
    return {item["label"]: item for item in row["assessments"]}


def knight_band(sidecar: dict) -> tuple[str, int | None, int | None, str]:
    analyses = sidecar.get("analyses", {}).get("knight", [])
    if not analyses:
        return "failed", None, None, "missing"
    analysis = analyses[0]
    interval = analysis.get("interval", {})
    definite = interval.get("definite_count")
    possible = interval.get("possible_count")
    if analysis.get("status") != "complete" or definite is None:
        return "failed", definite, possible, analysis.get("status", "missing")
    if definite == 0:
        band = "0"
    elif definite <= 2:
        band = "1-2"
    elif definite <= 4:
        band = "3-4"
    else:
        band = "5-7"
    return band, definite, possible, analysis.get("status", "complete")


def suvin_outcome(sidecar: dict) -> tuple[str, int | None, str]:
    analyses = sidecar.get("analyses", {}).get("suvin_novum", [])
    if not analyses:
        return "failed", None, "missing"
    analysis = analyses[0]
    if analysis.get("status") != "complete":
        return "failed", None, analysis.get("status", "failed")
    qualified = sum(
        1
        for candidate in analysis.get("candidates", [])
        if all(
            candidate.get(dimension, {}).get("status") == "present"
            for dimension in ("novelty", "cognitive_validation", "narrative_hegemony")
        )
    )
    return ("qualified" if qualified else "not qualified"), qualified, "complete"


def build_rows() -> list[dict]:
    manifest_rows = {
        row["story_id"]: row
        for row in load_jsonl(GENRE_ROOT / "genre_balanced_manifest.jsonl")
    }
    validation_rows = {
        row["lcats_id"]: row
        for row in load_jsonl(GENRE_ROOT / "validation_results.jsonl")
    }
    rows = []
    for story_id, manifest in manifest_rows.items():
        validation = validation_rows[story_id]
        model = assessments(validation)["model_detect"]["result"]
        sidecar = json.loads(
            (SF_ROOT / story_id / "science-fiction.json").read_text(encoding="utf-8")
        )
        band, definite, possible, knight_status = knight_band(sidecar)
        suvin, qualified_count, suvin_status = suvin_outcome(sidecar)
        metadata_candidates = manifest["metadata_assessment"]["result"][
            "target_candidates"
        ]
        rows.append(
            {
                "story_id": story_id,
                "selection_genre": manifest["selection_genre"],
                "metadata_candidates": ";".join(metadata_candidates),
                "model_genre": model["detected_genre"],
                "model_confidence": model.get("detected_genre_confidence", ""),
                "genre_agreement": "agreement"
                if model.get("agrees_with_metadata_rules")
                else "disagreement",
                "knight_band": band,
                "knight_definite": definite,
                "knight_possible": possible,
                "knight_status": knight_status,
                "suvin_outcome": suvin,
                "suvin_qualified_count": qualified_count,
                "suvin_status": suvin_status,
            }
        )
    return sorted(rows, key=lambda row: row["story_id"])


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_contingency(rows: list[dict]) -> None:
    counts = Counter(
        (
            row["selection_genre"],
            row["genre_agreement"],
            row["knight_band"],
            row["suvin_outcome"],
        )
        for row in rows
    )
    output = [
        {
            "selection_genre": genre,
            "genre_agreement": agreement,
            "knight_band": knight,
            "suvin_outcome": suvin,
            "count": counts[(genre, agreement, knight, suvin)],
        }
        for genre in GENRES
        for agreement in ("agreement", "disagreement")
        for knight in ("0", "1-2", "3-4", "5-7", "failed")
        for suvin in ("qualified", "not qualified", "failed")
        if counts[(genre, agreement, knight, suvin)]
    ]
    write_csv(
        OUTPUT / "genre_analysis_contingency.csv",
        output,
        [
            "selection_genre",
            "genre_agreement",
            "knight_band",
            "suvin_outcome",
            "count",
        ],
    )
    markdown = [
        "# Worldcon genre/analysis contingency table",
        "",
        "Long-form counts by metadata-selected genre, metadata/model agreement, "
        "Knight definite-score band, and Suvin outcome.",
        "",
        "| Selected genre | Agreement | Knight band | Suvin outcome | Count |",
        "|---|---|---:|---|---:|",
    ]
    markdown.extend(
        f"| {item['selection_genre']} | {item['genre_agreement']} | "
        f"{item['knight_band']} | {item['suvin_outcome']} | {item['count']} |"
        for item in output
    )
    (OUTPUT / "genre_analysis_contingency.md").write_text(
        "\n".join(markdown) + "\n", encoding="utf-8"
    )


def write_genre_summary(rows: list[dict]) -> None:
    summary = []
    for genre in GENRES:
        selected = [row for row in rows if row["selection_genre"] == genre]
        summary.append(
            {
                "selection_genre": genre,
                "stories": len(selected),
                "agreement": sum(row["genre_agreement"] == "agreement" for row in selected),
                "disagreement": sum(
                    row["genre_agreement"] == "disagreement" for row in selected
                ),
                "knight_0": sum(row["knight_band"] == "0" for row in selected),
                "knight_1_2": sum(row["knight_band"] == "1-2" for row in selected),
                "knight_3_4": sum(row["knight_band"] == "3-4" for row in selected),
                "knight_5_7": sum(row["knight_band"] == "5-7" for row in selected),
                "suvin_qualified": sum(
                    row["suvin_outcome"] == "qualified" for row in selected
                ),
                "suvin_not_qualified": sum(
                    row["suvin_outcome"] == "not qualified" for row in selected
                ),
                "suvin_failed": sum(row["suvin_outcome"] == "failed" for row in selected),
            }
        )
    write_csv(OUTPUT / "genre_analysis_summary.csv", summary, list(summary[0]))


def make_left_figure(rows: list[dict]) -> None:
    """Render the agreement and confusion panels as a readable two-panel figure."""
    plt.style.use("seaborn-v0_8-whitegrid")
    plt.rcParams.update(
        {
            "axes.titlesize": 31,
            "axes.labelsize": 21,
            "xtick.labelsize": 19,
            "ytick.labelsize": 19,
            "legend.fontsize": 17,
            "legend.title_fontsize": 17,
            "axes.titlepad": 16,
            "hatch.linewidth": 2.0,
        }
    )
    fig, axes = plt.subplots(1, 2, figsize=(18, 12), constrained_layout=True)
    x = np.arange(len(GENRES))

    agreement = {
        genre: [
            sum(
                row["selection_genre"] == genre
                and row["genre_agreement"] == status
                for row in rows
            )
            for status in ("agreement", "disagreement")
        ]
        for genre in GENRES
    }
    axes[0].bar(x, [agreement[g][0] for g in GENRES], label="Agreement")
    axes[0].bar(
        x,
        [agreement[g][1] for g in GENRES],
        bottom=[agreement[g][0] for g in GENRES],
        label="Disagreement",
    )
    totals = [sum(agreement[g]) for g in GENRES]
    for index, genre in enumerate(GENRES):
        rate = agreement[genre][0] / totals[index]
        axes[0].text(
            index,
            0.45,
            f"{rate:.0%}",
            ha="center",
            va="bottom",
            color="white",
            fontsize=17,
            fontweight="bold",
        )
    axes[0].set_ylim(0, max(totals))
    axes[0].set_title("Metadata / Model Agreement")
    axes[0].set_ylabel("Stories")
    axes[0].yaxis.set_major_locator(MaxNLocator(integer=True))
    axes[0].set_xticks(x, [genre.title() for genre in GENRES], rotation=55, ha="right")
    agreement_legend = axes[0].legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.26),
        ncol=2,
        handlelength=2.6,
        handleheight=2.6,
        labelspacing=0.5,
        borderpad=0.5,
    )

    matrix = np.zeros((len(GENRES), len(GENRES)), dtype=int)
    positions = {genre: index for index, genre in enumerate(GENRES)}
    for row in rows:
        model_genre = row["model_genre"]
        if model_genre in positions:
            matrix[positions[row["selection_genre"]], positions[model_genre]] += 1
    base_cmap = plt.get_cmap("Blues")
    darker_blues = LinearSegmentedColormap.from_list(
        "darker_blues_left", base_cmap(np.linspace(0.32, 0.95, 256))
    )
    darker_blues.set_bad("white")
    image = axes[1].imshow(
        np.ma.masked_where(matrix == 0, matrix),
        cmap=darker_blues,
        aspect="auto",
    )
    axes[1].set_title("Metadata --> Model Confusion")
    axes[1].set_xlabel("Model detected genre")
    axes[1].set_ylabel("Metadata-selected genre")
    axes[1].set_xticks(x, [genre.title() for genre in GENRES], rotation=55, ha="right")
    axes[1].set_yticks(x, [genre.title() for genre in GENRES])
    for row_index in range(len(GENRES)):
        for column_index in range(len(GENRES)):
            value = matrix[row_index, column_index]
            if value:
                axes[1].text(
                    column_index,
                    row_index,
                    str(value),
                    ha="center",
                    va="center",
                    color="white",
                    fontsize=20,
                    fontweight="bold",
                )
    colorbar = fig.colorbar(
        image,
        ax=axes[1],
        orientation="horizontal",
        fraction=0.08,
        pad=0.05,
        aspect=30,
    )
    colorbar.ax.xaxis.set_major_locator(MaxNLocator(integer=True))

    fig.suptitle("Metadata / Model Genre Labeling", fontsize=36)

    # Align the heatbar's bottom edge with the Agreement/Disagreement legend.
    fig.canvas.draw()
    agreement_bbox = agreement_legend.get_window_extent().transformed(
        fig.transFigure.inverted()
    )
    colorbar_bbox = colorbar.ax.get_position()
    fig.set_constrained_layout(False)
    colorbar.ax.set_position(
        [colorbar_bbox.x0, agreement_bbox.y0, colorbar_bbox.width, colorbar_bbox.height]
    )

    for extension in ("png", "svg", "pdf"):
        fig.savefig(OUTPUT / f"genre_agreement_confusion.{extension}", dpi=180)
    plt.close(fig)


def make_joint_figure(rows: list[dict]) -> None:
    """Render the joint Knight/Suvin panel as a wide standalone figure."""
    plt.style.use("seaborn-v0_8-whitegrid")
    plt.rcParams.update(
        {
            "axes.titlesize": 31,
            "axes.labelsize": 21,
            "xtick.labelsize": 19,
            "ytick.labelsize": 19,
            "legend.fontsize": 17,
            "legend.title_fontsize": 17,
            "axes.titlepad": 16,
        }
    )
    fig, ax = plt.subplots(figsize=(18, 13), constrained_layout=True)
    x = np.arange(len(GENRES))
    knight_bands = ("0", "1-2", "3-4", "5-7")
    knight_colors = ("#1f77b4", "#9ecae1", "#f4a3a3", "#b2182b")
    suvin_outcomes = (
        ("failed", "/"),
        ("not qualified", ""),
        ("qualified", "."),
    )
    bottoms = np.zeros(len(GENRES), dtype=int)
    for band, color in zip(knight_bands, knight_colors):
        for outcome, hatch in suvin_outcomes:
            values = np.array(
                [
                    sum(
                        row["selection_genre"] == genre
                        and row["knight_band"] == band
                        and row["suvin_outcome"] == outcome
                        for row in rows
                    )
                    for genre in GENRES
                ]
            )
            ax.bar(
                x,
                values,
                width=0.72,
                bottom=bottoms,
                color=color,
                edgecolor="white",
                linewidth=0.5,
                hatch=hatch,
            )
            bottoms += values

    ax.set_ylabel("Stories")
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_xticks(x, [genre.title() for genre in GENRES], rotation=55, ha="right")
    knight_legend = ax.legend(
        handles=[
            Patch(facecolor=color, label=f"Knight {band}")
            for band, color in zip(knight_bands, knight_colors)
        ],
        loc="upper center",
        bbox_to_anchor=(0.5, -0.16),
        ncol=4,
        title="Knight Bands",
        title_fontsize=17,
        handlelength=2.6,
        handleheight=2.6,
        labelspacing=0.5,
        borderpad=0.5,
    )
    ax.add_artist(knight_legend)
    ax.legend(
        handles=[
            Patch(
                facecolor="white",
                edgecolor="black",
                hatch=hatch,
                label=f"Suvin {outcome}",
            )
            for outcome, hatch in suvin_outcomes
        ],
        loc="upper center",
        bbox_to_anchor=(0.5, -0.25),
        ncol=3,
        title="Suvin Subdivision",
        title_fontsize=17,
        handlelength=2.6,
        handleheight=2.6,
        labelspacing=0.5,
        borderpad=0.5,
    )

    fig.suptitle("Worldcon Joint Knight/Suvin Distribution", fontsize=36)
    for extension in ("png", "svg", "pdf"):
        fig.savefig(OUTPUT / f"joint_knight_suvin.{extension}", dpi=180)
    plt.close(fig)


def make_figure(rows: list[dict]) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    plt.rcParams.update(
        {
            "axes.titlesize": 17,
            "axes.labelsize": 15,
            "xtick.labelsize": 13,
            "ytick.labelsize": 13,
            "legend.fontsize": 12,
            "legend.title_fontsize": 12,
            "axes.titlepad": 12,
            "hatch.linewidth": 2.0,
        }
    )
    fig, axes = plt.subplots(1, 3, figsize=(18, 9), constrained_layout=True)

    # Panel A: metadata/model agreement by selected genre.
    agreement = {
        genre: [
            sum(
                row["selection_genre"] == genre
                and row["genre_agreement"] == status
                for row in rows
            )
            for status in ("agreement", "disagreement")
        ]
        for genre in GENRES
    }
    x = np.arange(len(GENRES))
    axes[0].bar(x, [agreement[g][0] for g in GENRES], label="Agreement")
    axes[0].bar(
        x,
        [agreement[g][1] for g in GENRES],
        bottom=[agreement[g][0] for g in GENRES],
        label="Disagreement",
    )
    axes[0].set_title("A. Metadata/model agreement")
    axes[0].set_ylabel("Stories")
    axes[0].yaxis.set_major_locator(MaxNLocator(integer=True))
    axes[0].set_xticks(x, [genre.title() for genre in GENRES], rotation=55, ha="right")
    axes[0].legend(
        fontsize=12,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.16),
        ncol=2,
        handlelength=2.6,
        handleheight=2.6,
        labelspacing=0.5,
        borderpad=0.5,
    )

    # Panel B: confusion matrix, selected metadata genre by model genre.
    matrix = np.zeros((len(GENRES), len(GENRES)), dtype=int)
    positions = {genre: index for index, genre in enumerate(GENRES)}
    for row in rows:
        model_genre = row["model_genre"]
        if model_genre in positions:
            matrix[positions[row["selection_genre"]], positions[model_genre]] += 1
    base_cmap = plt.get_cmap("Blues")
    darker_blues = LinearSegmentedColormap.from_list(
        "darker_blues", base_cmap(np.linspace(0.32, 0.95, 256))
    )
    darker_blues.set_bad("white")
    image = axes[1].imshow(
        np.ma.masked_where(matrix == 0, matrix),
        cmap=darker_blues,
        aspect="auto",
    )
    axes[1].set_title("B. Metadata → model genre")
    axes[1].set_xlabel("Model detected genre")
    axes[1].set_ylabel("Metadata-selected genre")
    axes[1].set_xticks(x, [genre.title() for genre in GENRES], rotation=55, ha="right")
    axes[1].set_yticks(x, [genre.title() for genre in GENRES])
    for row_index in range(len(GENRES)):
        for column_index in range(len(GENRES)):
            value = matrix[row_index, column_index]
            if value:
                axes[1].text(
                    column_index,
                    row_index,
                    str(value),
                    ha="center",
                    va="center",
                    color="white",
                    fontsize=14,
                    fontweight="bold",
                )
    colorbar = fig.colorbar(
        image,
        ax=axes[1],
        orientation="horizontal",
        fraction=0.08,
        pad=0.05,
        aspect=30,
    )
    colorbar.ax.xaxis.set_major_locator(MaxNLocator(integer=True))

    # Panel C: exact joint Knight/Suvin distribution.
    knight_bands = ("0", "1-2", "3-4", "5-7")
    knight_colors = ("#1f77b4", "#9ecae1", "#f4a3a3", "#b2182b")
    suvin_outcomes = (
        ("failed", "/"),
        ("not qualified", ""),
        ("qualified", "."),
    )
    suvin_hatches = dict(suvin_outcomes)
    bottoms = np.zeros(len(GENRES), dtype=int)
    for band, color in zip(knight_bands, knight_colors):
        for outcome, hatch in suvin_outcomes:
            values = np.array(
                [
                    sum(
                        row["selection_genre"] == genre
                        and row["knight_band"] == band
                        and row["suvin_outcome"] == outcome
                        for row in rows
                    )
                    for genre in GENRES
                ]
            )
            axes[2].bar(
                x,
                values,
                width=0.72,
                bottom=bottoms,
                color=color,
                edgecolor="white",
                linewidth=0.5,
                hatch=hatch,
            )
            bottoms += values

    axes[2].set_title("C. Joint Knight/Suvin distribution")
    axes[2].set_ylabel("Stories")
    axes[2].yaxis.set_major_locator(MaxNLocator(integer=True))
    axes[2].set_xticks(x, [genre.title() for genre in GENRES], rotation=55, ha="right")
    knight_legend = axes[2].legend(
        handles=[
            Patch(facecolor=color, label=f"Knight {band}")
            for band, color in zip(knight_bands, knight_colors)
        ],
        fontsize=12,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.16),
        ncol=2,
        title="Knight bands",
        title_fontsize=12,
        handlelength=2.6,
        handleheight=2.6,
        labelspacing=0.5,
        borderpad=0.5,
    )
    axes[2].add_artist(knight_legend)
    suvin_legend = axes[2].legend(
        handles=[
            Patch(facecolor="white", edgecolor="black", hatch=hatch, label=f"Suvin {outcome}")
            for outcome, hatch in suvin_hatches.items()
        ],
        fontsize=12,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.40),
        ncol=3,
        title="Suvin subdivision",
        title_fontsize=12,
        handlelength=2.6,
        handleheight=2.6,
        labelspacing=0.5,
        borderpad=0.5,
    )

    fig.suptitle("Worldcon 146-story genre agreement and Knight/Suvin coverage", fontsize=20)

    # Align the heatmap colorbar's bottom edge with the Suvin legend's bottom edge.
    fig.canvas.draw()
    suvin_bbox = suvin_legend.get_window_extent().transformed(fig.transFigure.inverted())
    colorbar_bbox = colorbar.ax.get_position()
    fig.set_constrained_layout(False)
    colorbar.ax.set_position(
        [colorbar_bbox.x0, suvin_bbox.y0 + 0.015, colorbar_bbox.width, colorbar_bbox.height]
    )

    for extension in ("png", "svg", "pdf"):
        fig.savefig(OUTPUT / f"worldcon_sf_overlap.{extension}", dpi=180)
    plt.close(fig)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    rows = build_rows()
    write_csv(
        OUTPUT / "story_level.csv",
        rows,
        list(rows[0].keys()),
    )
    write_csv(
        OUTPUT / "metadata_model_confusion.csv",
        [
            {"selection_genre": genre, "model_genre": model, "count": count}
            for (genre, model), count in sorted(
                Counter((row["selection_genre"], row["model_genre"]) for row in rows).items()
            )
        ],
        ["selection_genre", "model_genre", "count"],
    )
    write_contingency(rows)
    write_genre_summary(rows)
    make_left_figure(rows)
    make_joint_figure(rows)
    make_figure(rows)
    manifest = {
        "prototype": "worldcon-sf-overlap-option-1-plus-option-4-v1",
        "universe": {
            "story_count": len(rows),
            "source_manifest": "experiments/05_metadata_genre_prefilter/results/full_scan/genre_balanced_manifest.jsonl",
            "science_fiction_root": str(SF_ROOT.relative_to(ROOT)),
        },
        "definitions": {
            "metadata_genre": "selection_genre; inclusive candidate memberships remain in metadata_candidates",
            "model_genre": "model_detect.result.detected_genre",
            "agreement": "model_detect.result.agrees_with_metadata_rules",
            "knight_band": "definite Knight interval: 0, 1-2, 3-4, or 5-7",
            "suvin_outcome": "qualified, not qualified, or failed analysis",
            "panel_c": "nested stack: Knight band order with Suvin outcome subdivisions",
        },
        "notes": [
            "Primary/selection genre counts are mutually exclusive.",
            "metadata_candidates preserves multi-genre overlap for a future inclusive view.",
            "This prototype does not interpret genre labels as theoretical truth or human agreement.",
        ],
    }
    (OUTPUT / "worldcon_sf_overlap_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"output": str(OUTPUT), "stories": len(rows)}, indent=2))


if __name__ == "__main__":
    main()
