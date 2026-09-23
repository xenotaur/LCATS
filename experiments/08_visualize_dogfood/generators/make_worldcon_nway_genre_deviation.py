"""Generate the Worldcon N-way genre frequency-deviation prototype.

The experiment-specific code in this file only chooses LCATS inputs, genres,
and output names.  Analysis and rendering live in ``lcats.visualize`` so another
experiment can construct the same result from its own ``ComparisonCorpus``.
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import json
import os
import pathlib

os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/lcats-matplotlib")

import matplotlib.pyplot as plt

from lcats.visualize import comparison
from lcats.visualize import rendering
from lcats.visualize import sources


ROOT = pathlib.Path(__file__).resolve().parents[3]
DEFAULT_MANIFEST = (
    ROOT
    / "experiments/05_metadata_genre_prefilter/results/full_scan/genre_balanced_manifest.jsonl"
)
DEFAULT_OUTPUT_DIR = (
    ROOT / "experiments/08_visualize_dogfood/figures/nway_genre_deviation"
)
DEFAULT_GENRES = (
    "adventure",
    "fantasy",
    "horror",
    "humor",
    "mystery",
    "romance",
    "science fiction",
    "western",
)


def repo_relative_source_path(source_path: str) -> str:
    """Keep in-repo provenance stable instead of recording a checkout path."""
    normalized = []
    for item in source_path.split(";"):
        path = pathlib.Path(item)
        if path.is_absolute() and path.is_relative_to(ROOT):
            normalized.append(str(path.relative_to(ROOT)))
        else:
            normalized.append(item)
    return ";".join(normalized)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--genres", nargs="+", default=list(DEFAULT_GENRES))
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument(
        "--highlight",
        choices=[mode.value for mode in rendering.ExtremaHighlight],
        default=rendering.ExtremaHighlight.PER_GENRE.value,
    )
    parser.add_argument(
        "--formats",
        nargs="+",
        choices=("png", "svg", "pdf"),
        default=("png", "svg", "pdf"),
    )
    return parser.parse_args()


def build_result(
    *, manifest_path: str, genres: list[str], top_k: int
) -> comparison.NWayComparisonResult:
    """Load the balanced sample and compute normalized genre deviations."""
    if top_k < 1:
        raise ValueError("top_k must be >= 1")
    if not genres:
        raise ValueError("at least one genre is required")
    selection = sources.load_manifest_selection(manifest_path)
    corpus = sources.load_comparison_corpus(manifest_jsonl_path=manifest_path)
    corpus = dataclasses.replace(
        corpus, source_path=repo_relative_source_path(corpus.source_path)
    )
    spec = comparison.NWayComparisonSpec(
        universe=comparison.UniverseSpec(
            kind="manifest",
            story_ids=selection.story_ids,
            source_path=repo_relative_source_path(selection.source_path),
            source_revision=selection.source_revision,
        ),
        reference=comparison.Selector(
            comparison.SelectorKind.ALL,
            label=f"Full {len(selection.story_ids)}-story sample",
        ),
        panels=tuple(
            comparison.NWayPanelSpec(
                key=genre.replace(" ", "_"),
                selector=comparison.Selector(
                    comparison.SelectorKind.MANIFEST_GENRE,
                    genre=genre,
                    membership_mode=comparison.MembershipMode.SELECTION,
                    label=genre.title(),
                ),
            )
            for genre in genres
        ),
        metric=comparison.MetricSpec(comparison.MetricName.PER_MILLION),
        vocabulary=comparison.NWayVocabularySpec(
            policy=comparison.NWayVocabularyPolicy.REFERENCE_VALUE,
            top_k=top_k,
        ),
        ordering=comparison.NWayOrderingSpec(
            by=comparison.NWayOrdering.REFERENCE_VALUE
        ),
    )
    return comparison.compare_many(corpus, spec)


def write_outputs(
    result: comparison.NWayComparisonResult,
    *,
    output_dir: pathlib.Path,
    highlight: str,
    formats: list[str] | tuple[str, ...],
) -> None:
    """Write one figure, long-form data, and disclosed rendering provenance."""
    output_dir.mkdir(parents=True, exist_ok=True)
    story_count = result.manifest["universe"]["story_count"]
    stem = f"lcats_{story_count}_nway_genre_deviation_{highlight.replace('-', '_')}"
    fig, _ = rendering.plot_nway_deviation_comparison(
        result,
        title=f"Genre deviations from the full {story_count}-story sample",
        highlight=highlight,
    )
    for output_format in formats:
        fig.savefig(
            output_dir / f"{stem}.{output_format}",
            dpi=180,
            bbox_inches="tight",
        )
    plt.close(fig)

    records = result.long_table()
    with (output_dir / f"{stem}.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)

    highlighted = rendering.nway_extrema_cells(result, highlight)
    cells = {
        (panel.panel_key, row.term): panel
        for row in result.rows
        for panel in row.panels
    }
    rendering_manifest = {
        "highlight_mode": highlight,
        "highlighted_cells": [
            {
                "panel_key": panel_key,
                "term": term,
                "deviation": cells[(panel_key, term)].deviation,
            }
            for panel_key, term in sorted(highlighted)
        ],
        "deviation_scale": {
            "kind": "joint_symmetric",
            "absolute_limit": max(
                abs(panel.deviation) for row in result.rows for panel in row.panels
            ),
        },
        "reference_scale": "independent_nonnegative",
        "formats": list(formats),
    }
    manifest = {**result.manifest, "rendering": rendering_manifest}
    (output_dir / f"{stem}_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> None:
    args = parse_args()
    result = build_result(
        manifest_path=args.manifest,
        genres=args.genres,
        top_k=args.top_k,
    )
    write_outputs(
        result,
        output_dir=pathlib.Path(args.output_dir),
        highlight=args.highlight,
        formats=args.formats,
    )


if __name__ == "__main__":
    main()
