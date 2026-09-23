"""Generate the checked Worldcon N-way genre reference-deviation examples.

The experiment-specific code in this file only chooses LCATS inputs, genres,
policies, and output names.  Analysis, rendering, CSV, and manifest writing
live in ``lcats.visualize`` so another experiment can construct the same
result from its own ``ComparisonCorpus`` or run ``lcats visualize
compare-many`` directly.

The PR #442 prototype outputs (``lcats_146_nway_genre_deviation_per_genre.*``)
are preserved historical artifacts; the examples below use distinct stems and
never overwrite them.
"""

from __future__ import annotations

import argparse
import dataclasses
import os
import pathlib
import sys

os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/lcats-matplotlib")

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "lcats" / "src"))

from lcats.visualize import comparison  # noqa: E402
from lcats.visualize import nway_outputs  # noqa: E402
from lcats.visualize import rendering  # noqa: E402
from lcats.visualize import sources  # noqa: E402

DEFAULT_MANIFEST = (
    ROOT
    / "experiments/05_metadata_genre_prefilter/results/full_scan/genre_balanced_manifest.jsonl"
)
DEFAULT_OUTPUT_DIR = (
    ROOT / "experiments/08_visualize_dogfood/figures/nway_genre_deviation"
)
ALL_GENRES = (
    "adventure",
    "fantasy",
    "horror",
    "humor",
    "mystery",
    "romance",
    "science fiction",
    "western",
)


@dataclasses.dataclass(frozen=True)
class Example:
    """One checked example: data selection, policies, and presentation."""

    genres: tuple[str, ...]
    membership_mode: comparison.MembershipMode
    panel_mode: comparison.NWayPanelMode
    reference_policy: comparison.NWayReferencePolicy
    render_spec: rendering.NWayRenderSpec
    title: str


EXAMPLES = {
    "kabob_direct": Example(
        genres=ALL_GENRES,
        membership_mode=comparison.MembershipMode.SELECTION,
        panel_mode=comparison.NWayPanelMode.DIRECT,
        reference_policy=comparison.NWayReferencePolicy.COMMON,
        render_spec=rendering.NWayRenderSpec.from_preset("kabob"),
        title="Genre deviations from the full {n}-story sample",
    ),
    "wrapped_direct": Example(
        genres=ALL_GENRES,
        membership_mode=comparison.MembershipMode.SELECTION,
        panel_mode=comparison.NWayPanelMode.DIRECT,
        reference_policy=comparison.NWayReferencePolicy.COMMON,
        render_spec=rendering.NWayRenderSpec(highlight="global", max_columns=3),
        title="Genre deviations from the full {n}-story sample (wrapped)",
    ),
    "complement_common": Example(
        genres=("fantasy", "horror", "science fiction"),
        membership_mode=comparison.MembershipMode.SELECTION,
        panel_mode=comparison.NWayPanelMode.COMPLEMENT,
        reference_policy=comparison.NWayReferencePolicy.COMMON,
        render_spec=rendering.NWayRenderSpec.from_preset("kabob"),
        title="Complement (U - genre) deviations from the full {n}-story sample",
    ),
    "candidate_per_panel_complement": Example(
        genres=("adventure", "romance", "humor"),
        membership_mode=comparison.MembershipMode.CANDIDATE,
        panel_mode=comparison.NWayPanelMode.DIRECT,
        reference_policy=comparison.NWayReferencePolicy.PER_PANEL_COMPLEMENT,
        render_spec=rendering.NWayRenderSpec.from_preset("kabob"),
        title="Overlapping candidate genres vs. each genre's complement",
    ),
}


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
    parser.add_argument(
        "--examples",
        nargs="+",
        choices=sorted(EXAMPLES),
        default=list(EXAMPLES),
        help="Checked examples to regenerate (default: all).",
    )
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument(
        "--formats",
        nargs="+",
        choices=nway_outputs.SUPPORTED_FORMATS,
        default=list(nway_outputs.SUPPORTED_FORMATS),
    )
    return parser.parse_args()


def build_result(
    *,
    manifest_path: str,
    example: Example,
    top_k: int,
) -> comparison.NWayComparisonResult:
    """Load the balanced sample and compute one example's aligned result."""
    if top_k < 1:
        raise ValueError("top_k must be >= 1")
    selection = sources.load_manifest_selection(manifest_path)
    corpus = sources.load_comparison_corpus(manifest_jsonl_path=manifest_path)
    corpus = dataclasses.replace(
        corpus, source_path=repo_relative_source_path(corpus.source_path)
    )
    ranking = {
        comparison.NWayReferencePolicy.COMMON: "reference_value",
        comparison.NWayReferencePolicy.PER_PANEL_COMPLEMENT: "max_absolute_deviation",
        comparison.NWayReferencePolicy.NONE: "max_panel_value",
    }[example.reference_policy]
    reference = None
    if example.reference_policy == comparison.NWayReferencePolicy.COMMON:
        reference = comparison.Selector(
            comparison.SelectorKind.ALL,
            label=f"Full {len(selection.story_ids)}-story sample",
        )
    spec = comparison.NWayComparisonSpec(
        universe=comparison.UniverseSpec(
            kind="manifest",
            story_ids=selection.story_ids,
            source_path=repo_relative_source_path(selection.source_path),
            source_revision=selection.source_revision,
        ),
        reference=reference,
        panels=tuple(
            comparison.NWayPanelSpec(
                key=genre.replace(" ", "_"),
                selector=comparison.Selector(
                    comparison.SelectorKind.MANIFEST_GENRE,
                    genre=genre,
                    membership_mode=example.membership_mode,
                    label=genre.title(),
                ),
            )
            for genre in example.genres
        ),
        metric=comparison.MetricSpec(comparison.MetricName.PER_MILLION),
        vocabulary=comparison.NWayVocabularySpec(
            policy=comparison.NWayVocabularyPolicy(ranking), top_k=top_k
        ),
        ordering=comparison.NWayOrderingSpec(by=comparison.NWayOrdering(ranking)),
        panel_mode=example.panel_mode,
        reference_policy=example.reference_policy,
    )
    return comparison.compare_many(corpus, spec)


def main() -> None:
    args = parse_args()
    for name in args.examples:
        example = EXAMPLES[name]
        result = build_result(
            manifest_path=args.manifest, example=example, top_k=args.top_k
        )
        story_count = result.manifest["universe"]["story_count"]
        nway_outputs.write_nway_outputs(
            result,
            output_dir=args.output_dir,
            stem=f"lcats_{story_count}_nway_{name}",
            render_spec=example.render_spec,
            formats=args.formats,
            title=example.title.format(n=story_count),
            extra_manifest={
                "generator": (
                    "experiments/08_visualize_dogfood/generators/"
                    "make_worldcon_nway_genre_deviation.py"
                ),
                "example": name,
            },
        )


if __name__ == "__main__":
    main()
