"""Source adapters converting real LCATS/corpus artifacts into analysis data.

Genre labels are not part of the native LCATS story representation
(``lcats.stories.Story``/``Corpora`` load only ``story.json``). This module
reads whichever real, checked-in artifact actually carries genre counts,
rather than assuming genre already lives on ``Story``.

For per-story identity (needed to join external artifacts like
``candidates.jsonl`` to loaded story text), this module derives ``story_id``
directly from ``discovery.iter_collection_story_files``'s yielded paths, not
from ``lcats.stories.Corpora.get_corpora()``: it discards story paths
entirely, returning bare ``Story`` objects (``name``/``body``/``metadata``
only), and both title-matching and deriving identity from ``metadata.name``
are demonstrably ambiguous/lossy against the real corpus. Story *content* is
still consumed through ``lcats.stories.Story`` itself (``Story.from_dict``)
rather than a parallel hand-rolled parse -- only the per-story identity
comes from ``discovery`` instead of ``Corpora``.
"""

import dataclasses
import hashlib
import json
import pathlib

from lcats.analysis.corpus import discovery
from lcats.stories import Story
from lcats.visualize import comparison

DEFAULT_FULL_SCAN_SUMMARY_PATH = (
    "experiments/05_metadata_genre_prefilter/results/full_scan/summary.json"
)
DEFAULT_CANDIDATES_JSONL_PATH = (
    "experiments/05_metadata_genre_prefilter/results/full_scan/candidates.jsonl"
)
DEFAULT_CORPORA_ROOT = "corpora"


@dataclasses.dataclass(frozen=True)
class GenreCounts:
    """Genre-label counts from a named source, with reproducibility metadata."""

    counts: dict
    total_stories: int
    source_path: str
    source_revision: str
    no_usable_signal_count: int


@dataclasses.dataclass(frozen=True)
class CorpusSnapshot:
    """Full-corpus story text keyed by story_id, with reproducibility metadata."""

    texts: dict
    source_path: str
    source_revision: str


@dataclasses.dataclass(frozen=True)
class GenreMembership:
    """Per-story genre-candidate membership, with reproducibility metadata."""

    story_genres: dict
    source_path: str
    source_revision: str


@dataclasses.dataclass(frozen=True)
class ManifestSelection:
    """Story IDs and selection genres loaded from a manifest JSONL file."""

    story_ids: tuple[str, ...]
    selection_genres: dict[str, list[str]]
    source_path: str
    source_revision: str


def _resolve_repo_relative_path(path_str: str) -> pathlib.Path:
    """Resolve a (possibly repo-root-relative) path.

    ``AGENTS.md`` documents running ``lcats`` commands from inside the
    ``lcats/`` package directory, but checked-in artifacts outside the
    package (``experiments/``, ``corpora/``) live at repository-root-relative
    paths (siblings of ``lcats/``, not inside it). If the path doesn't
    resolve against the current working directory, fall back to resolving
    it against the repository root -- one level above the installed
    ``lcats/`` package directory that this module itself lives under -- so
    documented defaults work regardless of which of those two directories
    the command is run from.
    """
    candidate = pathlib.Path(path_str)
    if candidate.is_absolute() or candidate.exists():
        return candidate
    repo_root = pathlib.Path(__file__).resolve().parents[4]
    repo_relative = repo_root / path_str
    if repo_relative.exists():
        return repo_relative
    return candidate


def _resolve_summary_json_path(summary_json_path: str) -> pathlib.Path:
    """Resolve a (possibly repo-root-relative) summary.json path."""
    return _resolve_repo_relative_path(summary_json_path)


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
    path = _resolve_summary_json_path(summary_json_path)
    raw_bytes = path.read_bytes()
    data = json.loads(raw_bytes)

    genre_coverage = data["genre_coverage"]
    counts = dict(genre_coverage["primary_target_genre_counts"])
    no_usable_signal_count = genre_coverage["no_usable_signal_count"]
    total_stories = data["story_count"]

    counted_total = sum(counts.values()) + no_usable_signal_count
    if counted_total != total_stories:
        raise ValueError(
            f"{path}: primary_target_genre_counts ({sum(counts.values())}) + "
            f"no_usable_signal_count ({no_usable_signal_count}) = "
            f"{counted_total}, expected story_count ({total_stories}) -- "
            "the artifact may be inconsistent or partially updated."
        )

    return GenreCounts(
        counts=counts,
        total_stories=total_stories,
        source_path=str(path),
        source_revision=hashlib.sha256(raw_bytes).hexdigest(),
        no_usable_signal_count=no_usable_signal_count,
    )


def load_corpus_stories(
    corpora_root: str = DEFAULT_CORPORA_ROOT,
) -> CorpusSnapshot:
    """Load every story's body text, keyed by a stable ``story_id``.

    ``story_id`` is derived directly from ``discovery.iter_collection_story_files``'s
    yielded paths (``<collection>/<slug>``), not from ``Corpora``, which
    discards this identity entirely. This is the only reliable join key
    against external per-story artifacts such as ``candidates.jsonl``.

    ``source_revision`` is a content hash over every consumed story file
    (sorted ``story_id:sha256(file_bytes)`` pairs, hashed together), so any
    change to the story set or any story's content changes the revision.
    """
    root = _resolve_repo_relative_path(corpora_root)
    texts = {}
    file_hashes = []
    for collection_dir in sorted(
        p for p in root.iterdir() if p.is_dir() and not p.is_symlink()
    ):
        for story_path in discovery.iter_collection_story_files(collection_dir):
            story_id = f"{collection_dir.name}/{story_path.parent.name}"
            raw_bytes = story_path.read_bytes()
            story = Story.from_dict(json.loads(raw_bytes))
            texts[story_id] = story.body
            file_hashes.append(f"{story_id}:{hashlib.sha256(raw_bytes).hexdigest()}")

    revision = hashlib.sha256(
        "\n".join(sorted(file_hashes)).encode("utf-8")
    ).hexdigest()
    return CorpusSnapshot(
        texts=texts,
        source_path=str(root),
        source_revision=revision,
    )


def load_candidates_genre_membership(
    candidates_jsonl_path: str = DEFAULT_CANDIDATES_JSONL_PATH,
) -> GenreMembership:
    """Load per-story genre-candidate membership from ``candidates.jsonl``.

    Reads ``story_id`` and ``metadata_assessment.result.target_candidates``
    from each row. ``target_candidates`` is multi-label -- a story may
    belong to more than one genre's subset; this is preserved as-is, not
    deduplicated or reduced to a single "primary" genre.

    Raises ``ValueError`` if the same ``story_id`` appears in more than one
    row: silently keeping the last row would make the selected genre and
    resulting frequencies depend on file order, while a later join-coverage
    check comparing key sets alone could not detect the ambiguity.
    """
    path = _resolve_repo_relative_path(candidates_jsonl_path)
    raw_bytes = path.read_bytes()
    story_genres = {}
    for line in raw_bytes.decode("utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        story_id = row["story_id"]
        if story_id in story_genres:
            raise ValueError(
                f"{path}: duplicate story_id {story_id!r} -- candidates.jsonl "
                "must contain at most one row per story_id for an "
                "unambiguous join."
            )
        candidates = row["metadata_assessment"]["result"]["target_candidates"]
        story_genres[story_id] = list(candidates)

    return GenreMembership(
        story_genres=story_genres,
        source_path=str(path),
        source_revision=hashlib.sha256(raw_bytes).hexdigest(),
    )


def load_manifest_selection(manifest_jsonl_path: str) -> ManifestSelection:
    """Load story IDs and selection labels from a JSONL selection manifest."""
    path = _resolve_repo_relative_path(manifest_jsonl_path)
    raw_bytes = path.read_bytes()
    story_ids = []
    selection_genres = {}
    for line in raw_bytes.decode("utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        story_id = row["story_id"]
        if story_id in selection_genres:
            raise ValueError(
                f"{path}: duplicate story_id {story_id!r} -- manifest story IDs "
                "must be unique for deterministic comparison selection."
            )
        story_ids.append(story_id)
        genre = row.get("selection_genre")
        selection_genres[story_id] = [genre] if genre else []
    return ManifestSelection(
        story_ids=tuple(story_ids),
        selection_genres=selection_genres,
        source_path=str(path),
        source_revision=hashlib.sha256(raw_bytes).hexdigest(),
    )


def load_comparison_corpus(
    *,
    corpora_root: str = DEFAULT_CORPORA_ROOT,
    candidates_jsonl_path: str = DEFAULT_CANDIDATES_JSONL_PATH,
    manifest_jsonl_path: str | None = None,
) -> comparison.ComparisonCorpus:
    """Load corpus text and genre metadata for comparative lexical analysis."""
    corpus = load_corpus_stories(corpora_root)
    membership = load_candidates_genre_membership(candidates_jsonl_path)
    manifest_selection = (
        load_manifest_selection(manifest_jsonl_path) if manifest_jsonl_path else None
    )

    corpus_ids = set(corpus.texts)
    membership_ids = set(membership.story_genres)
    missing_from_corpus = sorted(membership_ids - corpus_ids)
    missing_from_candidates = sorted(corpus_ids - membership_ids)
    if missing_from_corpus or missing_from_candidates:
        raise ValueError(
            "join coverage incomplete between the corpus snapshot and "
            "candidates.jsonl -- requires a complete one-to-one join: "
            f"{len(missing_from_corpus)} candidates.jsonl story_id(s) not found "
            f"in the corpus (e.g. {missing_from_corpus[:3]!r}), "
            f"{len(missing_from_candidates)} corpus story_id(s) not found "
            f"in candidates.jsonl (e.g. {missing_from_candidates[:3]!r})."
        )

    manifest_story_ids: set[str] = set()
    if manifest_selection is not None:
        manifest_story_ids = set(manifest_selection.story_ids)
        missing_manifest_ids = sorted(manifest_story_ids - corpus_ids)
        if missing_manifest_ids:
            raise ValueError(
                f"{manifest_selection.source_path}: {len(missing_manifest_ids)} "
                "manifest story_id(s) not found in the corpus "
                f"(e.g. {missing_manifest_ids[:3]!r})."
            )

    documents = []
    for story_id, text in corpus.texts.items():
        selection_genres = ()
        if manifest_selection is not None and story_id in manifest_story_ids:
            selection_genres = tuple(manifest_selection.selection_genres[story_id])
        documents.append(
            comparison.ComparisonDocument(
                story_id=story_id,
                text=text,
                candidate_genres=tuple(membership.story_genres[story_id]),
                selection_genres=selection_genres,
            )
        )

    source_parts = [corpus.source_path, membership.source_path]
    revision_parts = [corpus.source_revision, membership.source_revision]
    if manifest_selection is not None:
        source_parts.append(manifest_selection.source_path)
        revision_parts.append(manifest_selection.source_revision)
    return comparison.ComparisonCorpus(
        documents=tuple(documents),
        source_path=";".join(source_parts),
        source_revision=hashlib.sha256(
            "\n".join(revision_parts).encode("utf-8")
        ).hexdigest(),
    )
