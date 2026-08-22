"""Source adapters converting real LCATS/corpus artifacts into genre-count data.

Genre labels are not part of the native LCATS story representation
(``lcats.stories.Story``/``Corpora`` load only ``story.json``). This module
reads whichever real, checked-in artifact actually carries genre counts,
rather than assuming genre already lives on ``Story``.
"""

import dataclasses
import hashlib
import json
import pathlib

DEFAULT_FULL_SCAN_SUMMARY_PATH = (
    "experiments/05_metadata_genre_prefilter/results/full_scan/summary.json"
)


@dataclasses.dataclass(frozen=True)
class GenreCounts:
    """Genre-label counts from a named source, with reproducibility metadata."""

    counts: dict
    total_stories: int
    source_path: str
    source_revision: str
    no_usable_signal_count: int


def load_full_scan_genre_counts(
    summary_json_path: str = DEFAULT_FULL_SCAN_SUMMARY_PATH,
) -> GenreCounts:
    """Load a non-overlapping, full-corpus genre distribution.

    Reads ``genre_coverage.primary_target_genre_counts`` plus
    ``genre_coverage.no_usable_signal_count`` from the full-scan
    ``summary.json`` produced by ``experiments/05_metadata_genre_prefilter``.

    This deliberately does not use the sibling ``target_candidate_counts``
    field: that field is multi-label (a story with more than one candidate
    genre is counted once per label), so it sums to less than the corpus
    size and would double-count some stories if rendered as a distribution.
    ``primary_target_genre_counts`` plus ``no_usable_signal_count`` is
    non-overlapping and sums to the full ``story_count``.
    """
    path = pathlib.Path(summary_json_path)
    raw_bytes = path.read_bytes()
    data = json.loads(raw_bytes)

    genre_coverage = data["genre_coverage"]
    counts = dict(genre_coverage["primary_target_genre_counts"])
    no_usable_signal_count = genre_coverage["no_usable_signal_count"]
    total_stories = data["story_count"]

    return GenreCounts(
        counts=counts,
        total_stories=total_stories,
        source_path=str(path),
        source_revision=hashlib.sha256(raw_bytes).hexdigest(),
        no_usable_signal_count=no_usable_signal_count,
    )
