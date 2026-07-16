"""Survey-gated promotion of data/ collections into corpora/.

``corpora/`` is a periodic release snapshot; ``data/`` is the live working
corpus, cleared and regenerated after major changes (see
``project/design/design.md``'s State and Persistence Boundary). Promotion must
be gated on a passing special-character survey, or drift like the pre-2026-07
``corpora/`` snapshot (148 stories of stale mojibake) recurs at every release.

Collection-name mapping is identity: the ``data/`` collection name is the
``corpora/`` collection name. As of 2026-07 (before any external release) two
legacy ``corpora/`` names diverged from their current ``data/`` counterparts
(``corpora/ohenry`` for ``data/ohenry-four_million``,
``corpora/wilde`` for ``data/wilde_happy_prince``), and ``data/ohenry-whirligigs``
-- a second O. Henry collection, not a merge target -- was never promoted at
all. See ``docs/reference/corpus-promotion.md`` for the one-time manual cleanup
this implies at the first gated promotion.
"""

import dataclasses
import pathlib
import shutil

from lcats.analysis.corpus import cli
from lcats.analysis.corpus import discovery
from lcats.analysis.corpus import specials

BLOCKING_CLASSIFICATION = "likely_repairable"


def destination_name(source_collection_name: str) -> str:
    """Return the corpora/ directory name for a data/ collection name.

    Identity mapping: every collection promotes under its data/ name.
    """
    return source_collection_name


@dataclasses.dataclass(frozen=True)
class BlockingFinding:
    """One mojibake finding that blocks a collection from promotion."""

    story_path: pathlib.Path
    codepoint: str
    character: str
    context: str


@dataclasses.dataclass(frozen=True)
class CollectionSurveyResult:
    """Survey outcome for one collection directory."""

    collection: str
    story_count: int
    findings: tuple[BlockingFinding, ...]

    @property
    def clean(self) -> bool:
        """Return True when the collection has no blocking findings."""
        return not self.findings


def survey_collection(
    collection_dir: pathlib.Path,
    allowlist: specials.AllowlistConfig | None = None,
) -> CollectionSurveyResult:
    """Survey one collection directory for blocking (mojibake) findings.

    Scoped to ``likely_repairable`` findings only, matching this work item's
    mojibake-only gate; structural/boundary checks are a separate concern.

    Args:
        collection_dir: Path to one collection directory under data/.
        allowlist: Allowlist to apply; defaults to the packaged corpus
            allowlist (the same default ``lcats survey`` uses).

    Returns:
        A CollectionSurveyResult with any blocking findings.
    """
    effective_allowlist = (
        allowlist
        if allowlist is not None
        else specials.load_allowlist_config(specials.default_allowlist_config_path())
    )
    story_paths = discovery.find_corpus_stories(collection_dir)
    findings: list[BlockingFinding] = []
    for story_path in story_paths:
        data = cli.read_story_data(story_path)
        text = cli.coerce_story_text(data.get("body", ""))
        for result in specials.iter_special_characters(
            text=text,
            allow_smart=True,
            excluded=set(),
            allowlist=effective_allowlist,
            context=10,
            name_width=0,
        ):
            if result.classification != BLOCKING_CLASSIFICATION:
                continue
            findings.append(
                BlockingFinding(
                    story_path=story_path,
                    codepoint=result.codepoint,
                    character=result.character,
                    context=result.context,
                )
            )

    return CollectionSurveyResult(
        collection=collection_dir.name,
        story_count=len(story_paths),
        findings=tuple(findings),
    )


@dataclasses.dataclass(frozen=True)
class PromotionReport:
    """Outcome of a promotion run across one or more collections."""

    promoted: tuple[str, ...]
    blocked: tuple[CollectionSurveyResult, ...]

    @property
    def all_promoted(self) -> bool:
        """Return True when every considered collection promoted cleanly."""
        return not self.blocked


def _copy_collection(source_dir: pathlib.Path, dest_dir: pathlib.Path) -> None:
    """Wholesale-replace dest_dir with a copy of source_dir's contents."""
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    shutil.copytree(source_dir, dest_dir)


def promote_collections(
    source_root: pathlib.Path,
    dest_root: pathlib.Path,
    collection_names: list[str] | None = None,
    dry_run: bool = False,
) -> PromotionReport:
    """Survey and promote data/ collections into corpora/.

    Each requested collection is surveyed independently; a collection with any
    blocking (mojibake) finding is skipped and reported, all others are
    promoted. Promotion wholesale-replaces the destination collection
    directory under its identity-mapped name (see ``destination_name``) so
    stale files from a prior promotion cannot linger.

    Args:
        source_root: Root directory containing collection subdirectories
            (typically data/).
        dest_root: Root directory to promote clean collections into
            (typically corpora/).
        collection_names: Collection directory names to consider; defaults to
            every subdirectory of source_root.
        dry_run: When True, survey and report but do not copy any files.

    Returns:
        A PromotionReport listing promoted collection names and blocked
        CollectionSurveyResult entries.
    """
    if collection_names is None:
        collection_names = sorted(
            entry.name for entry in source_root.iterdir() if entry.is_dir()
        )

    promoted: list[str] = []
    blocked: list[CollectionSurveyResult] = []
    allowlist = specials.load_allowlist_config(specials.default_allowlist_config_path())

    for name in collection_names:
        collection_dir = source_root / name
        result = survey_collection(collection_dir, allowlist=allowlist)
        if not result.clean:
            blocked.append(result)
            continue

        if not dry_run:
            _copy_collection(collection_dir, dest_root / destination_name(name))
        promoted.append(name)

    return PromotionReport(promoted=tuple(promoted), blocked=tuple(blocked))
