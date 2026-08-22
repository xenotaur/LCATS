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
import json
import os
import pathlib
import shutil
import tempfile

from lcats.analysis.corpus import cli
from lcats.analysis.corpus import discovery
from lcats.analysis.corpus import genre_sidecar
from lcats.analysis.corpus import specials

BLOCKING_CLASSIFICATION = "likely_repairable"

# (sidecar filename, required top-level key, expected value type) --
# parse/shape-level checks only (per WI-ANNOTATE-0052's Non-Goals: no
# schema-validation library), but enough to catch a truncated/corrupted/
# wrong-shape sidecar before it's wholesale-copied to corpora/. Filenames
# come from discovery.py's own named constants (not annotate.py's -- that
# module pulls in the full extractor/LLM dependency chain, unnecessary
# just to promote already-computed files; review finding, PR #248), so
# the two modules' conventions can't silently drift apart. The value
# type check (not just key presence) catches e.g. {"segments": null} or
# {"detected_genre": 42}, which the writer never produces but a
# presence-only check would still wave through (review finding, PR #248).
_SIDECAR_REQUIRED_KEYS = (
    (discovery.GENRE_SIDECAR_FILENAME, "detected_genre", str),
    (discovery.SCENES_SIDECAR_FILENAME, "segments", list),
)


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
class MalformedSidecarFinding:
    """One malformed genre.json/scenes.json sidecar that blocks a
    collection from promotion, distinct from a mojibake BlockingFinding
    (WI-ANNOTATE-0052) so CollectionSurveyResult reporting stays clear
    about which kind of problem blocked promotion."""

    story_path: pathlib.Path
    sidecar_name: str
    error: str


@dataclasses.dataclass(frozen=True)
class CollectionSurveyResult:
    """Survey outcome for one collection directory."""

    collection: str
    story_count: int
    findings: tuple[BlockingFinding, ...]
    sidecar_findings: tuple[MalformedSidecarFinding, ...] = ()

    @property
    def clean(self) -> bool:
        """Return True when the collection has no blocking findings and at
        least one story.

        A zero-story collection is never clean, even with no findings -- a
        writer regression or a stale/mid-migration collection would
        otherwise report `findings=()` and be promoted (wholesale-copied)
        undetected. This is a standing check on every survey, not a
        one-time step (Decision 6 of PROP-LCATS-STORY-BUCKET-LAYOUT).

        A malformed sidecar blocks promotion the same way a mojibake
        finding does (WI-ANNOTATE-0052) -- a story with valid prose but a
        corrupted genre.json/scenes.json is not safe to wholesale-copy
        into corpora/ either.
        """
        return not self.findings and not self.sidecar_findings and self.story_count > 0


def _validate_sidecars(story_path: pathlib.Path) -> list[MalformedSidecarFinding]:
    """Check a story bucket's genre.json/scenes.json -- when present --
    for basic parse/shape validity. Not a schema-validation pass (per
    WI-ANNOTATE-0052's Non-Goals): parses as JSON, is a dict, and has the
    one required top-level key each sidecar's real writer (annotate.py)
    always populates, with the expected value type -- key presence alone
    would still wave through e.g. {"segments": null} (review finding, PR
    #248). A missing sidecar is not itself a finding -- most of data/
    predates lcats annotate and has no sidecars at all."""
    bucket_dir = story_path.parent
    findings: list[MalformedSidecarFinding] = []
    for sidecar_name, required_key, expected_type in _SIDECAR_REQUIRED_KEYS:
        sidecar_path = bucket_dir / sidecar_name
        if not sidecar_path.is_file():
            continue
        try:
            data = json.loads(sidecar_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            findings.append(
                MalformedSidecarFinding(
                    story_path=story_path,
                    sidecar_name=sidecar_name,
                    error=f"could not parse as JSON: {exc}",
                )
            )
            continue
        if not isinstance(data, dict):
            findings.append(
                MalformedSidecarFinding(
                    story_path=story_path,
                    sidecar_name=sidecar_name,
                    error=f"expected a JSON object, got {type(data).__name__}",
                )
            )
            continue
        if required_key not in data:
            findings.append(
                MalformedSidecarFinding(
                    story_path=story_path,
                    sidecar_name=sidecar_name,
                    error=f"missing required key {required_key!r}",
                )
            )
        elif not isinstance(data[required_key], expected_type):
            findings.append(
                MalformedSidecarFinding(
                    story_path=story_path,
                    sidecar_name=sidecar_name,
                    error=(
                        f"{required_key!r} expected {expected_type.__name__}, "
                        f"got {type(data[required_key]).__name__}"
                    ),
                )
            )
    return findings


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
    # Use the canonical bucket-only selector, not find_corpus_stories's
    # broad recursive JSON match -- a bucket directory holding only
    # sidecars (audit.json etc.) and no story.json is exactly the
    # writer-regression case Decision 6's story_count > 0 check exists to
    # catch, and find_corpus_stories would silently count the sidecar as
    # a story instead. iter_collection_story_files is the same selector
    # Corpora.get_corpora uses, applied here to a single known collection
    # directory (no root-level ambiguity risk).
    story_paths = list(discovery.iter_collection_story_files(collection_dir))
    findings: list[BlockingFinding] = []
    sidecar_findings: list[MalformedSidecarFinding] = []
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
        sidecar_findings.extend(_validate_sidecars(story_path))

    return CollectionSurveyResult(
        collection=collection_dir.name,
        story_count=len(story_paths),
        findings=tuple(findings),
        sidecar_findings=tuple(sidecar_findings),
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


def _validate_distinct_roots(
    source_root: pathlib.Path, dest_root: pathlib.Path
) -> None:
    """Raise ValueError if source_root and dest_root are equal or nested.

    ``_copy_collection`` removes the destination before copying; if source and
    destination resolve to the same directory (or one contains the other), a
    per-collection ``rmtree`` would delete source data before ``copytree`` can
    run it, destroying the collection with no recovery path.
    """
    resolved_source = source_root.resolve()
    resolved_dest = dest_root.resolve()
    if resolved_source == resolved_dest:
        raise ValueError(
            f"--source and --dest resolve to the same directory "
            f"({resolved_source}); refusing to promote to avoid deleting "
            "the source before copying."
        )
    if (
        resolved_dest in resolved_source.parents
        or resolved_source in resolved_dest.parents
    ):
        raise ValueError(
            f"--source ({resolved_source}) and --dest ({resolved_dest}) are "
            "nested inside one another; refusing to promote."
        )


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

    Every requested collection is surveyed first; only once all surveys are
    complete does copying begin, so a mid-run error cannot leave a collection
    half-copied. Each collection is still gated **independently**: a
    collection with any blocking (mojibake) finding is skipped and reported,
    while every other clean collection is still promoted -- this is a
    deliberate, documented mode (see docs/reference/corpus-promotion.md), not
    an all-or-nothing whole-corpus gate, so that already-clean collections
    are not held hostage by an unrelated collection that still needs
    regeneration. Promotion wholesale-replaces the destination collection
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

    Raises:
        ValueError: If source_root and dest_root are the same or nested.
    """
    _validate_distinct_roots(source_root, dest_root)

    if collection_names is None:
        collection_names = sorted(
            entry.name for entry in source_root.iterdir() if entry.is_dir()
        )

    allowlist = specials.load_allowlist_config(specials.default_allowlist_config_path())

    results = [
        survey_collection(source_root / name, allowlist=allowlist)
        for name in collection_names
    ]

    promoted: list[str] = []
    blocked: list[CollectionSurveyResult] = []
    for name, result in zip(collection_names, results):
        if not result.clean:
            blocked.append(result)
            continue

        if not dry_run:
            _copy_collection(source_root / name, dest_root / destination_name(name))
        promoted.append(name)

    return PromotionReport(promoted=tuple(promoted), blocked=tuple(blocked))


@dataclasses.dataclass(frozen=True)
class SidecarPromotionFinding:
    """One tranche-manifest record rejected during sidecar promotion."""

    lcats_id: str
    error: str


@dataclasses.dataclass(frozen=True)
class SidecarTranchePromotionReport:
    """Outcome of a sidecar-tranche promotion run."""

    promoted: tuple[str, ...]
    rejected: tuple[SidecarPromotionFinding, ...]

    @property
    def all_promoted(self) -> bool:
        """Return True when every manifest record promoted cleanly."""
        return not self.rejected


def _atomic_write_text(path: pathlib.Path, text: str) -> None:
    """Atomically publish a text file -- mirrors annotate.py's own
    tempfile+os.replace pattern (review finding, PR #241) so an
    interrupted write during tranche promotion can't leave a torn
    genre.json behind."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
            tmp_file.write(text)
        os.replace(tmp_name, path)
    except BaseException:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise


def _lcats_id_escape_error(lcats_id: str, dest_root: pathlib.Path) -> str | None:
    """Return an error message if ``lcats_id`` could place a write outside
    ``dest_root``, else None. ``validate_sidecar()`` only requires a
    non-empty string, so an absolute path or ``..``/``.`` component in an
    otherwise schema-valid manifest record must be rejected here before it
    is ever joined onto ``dest_root`` (review finding, PR #350)."""
    candidate = pathlib.PurePosixPath(lcats_id)
    if candidate.is_absolute() or not candidate.parts or ".." in candidate.parts:
        return (
            f"lcats_id {lcats_id!r} must be a non-empty relative path with "
            "no '..' components"
        )
    resolved_dest_root = dest_root.resolve()
    resolved_candidate = (dest_root / lcats_id).resolve()
    try:
        resolved_candidate.relative_to(resolved_dest_root)
    except ValueError:
        return f"lcats_id {lcats_id!r} resolves outside dest_root ({dest_root})"
    return None


def promote_sidecar_tranche(
    manifest_path: pathlib.Path,
    dest_root: pathlib.Path,
    dry_run: bool = False,
) -> SidecarTranchePromotionReport:
    """Promote selected stories' genre.json sidecars from a JSONL manifest
    into corpora/, without touching any other file in the destination
    collection directory.

    Unlike ``promote_collections``' whole-directory wholesale replacement,
    this promotes exactly the ``genre.json`` sidecars named in the
    manifest -- one ``genre-sidecar-v1`` record per line, each already
    carrying its own ``lcats_id`` -- and nothing else. Every record is
    validated via ``genre_sidecar.validate_sidecar()`` before being
    written; an invalid record is rejected and reported, not silently
    written. A legacy flat ``genre.json`` already present at a promotion
    destination is refused explicitly (with a clear error), never
    silently overwritten or silently left stale -- converting a legacy
    sidecar in place is ``lcats annotate``'s job (``WI-GENRE-0076``), not
    this function's.

    Args:
        manifest_path: Path to a JSONL file, one ``genre-sidecar-v1`` JSON
            object per line (e.g. ``experiments/05_metadata_genre_prefilter``'s
            ``validation_results.jsonl``).
        dest_root: Root directory to promote into (typically ``corpora/``).
        dry_run: When True, validate and report but write nothing.

    Returns:
        A SidecarTranchePromotionReport listing promoted ``lcats_id``
        values and rejected ``SidecarPromotionFinding`` entries.
    """
    promoted: list[str] = []
    rejected: list[SidecarPromotionFinding] = []

    with manifest_path.open("r", encoding="utf-8") as manifest_file:
        for line_number, raw_line in enumerate(manifest_file, start=1):
            line = raw_line.strip()
            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                rejected.append(
                    SidecarPromotionFinding(
                        lcats_id=f"<line {line_number}>",
                        error=f"could not parse manifest line as JSON: {exc}",
                    )
                )
                continue

            lcats_id = record.get("lcats_id") if isinstance(record, dict) else None
            if not isinstance(lcats_id, str) or not lcats_id:
                rejected.append(
                    SidecarPromotionFinding(
                        lcats_id=f"<line {line_number}>",
                        error="record has no non-empty top-level lcats_id",
                    )
                )
                continue

            escape_error = _lcats_id_escape_error(lcats_id, dest_root)
            if escape_error is not None:
                rejected.append(
                    SidecarPromotionFinding(lcats_id=lcats_id, error=escape_error)
                )
                continue

            validation = genre_sidecar.validate_sidecar(record)
            if not validation.valid:
                rejected.append(
                    SidecarPromotionFinding(
                        lcats_id=lcats_id,
                        error="; ".join(
                            f"{finding.path}: {finding.message}"
                            for finding in validation.findings
                        ),
                    )
                )
                continue

            dest_dir = dest_root / lcats_id
            if not (dest_dir / discovery.CANONICAL_STORY_FILENAME).is_file():
                rejected.append(
                    SidecarPromotionFinding(
                        lcats_id=lcats_id,
                        error=(
                            f"refusing to promote: no {discovery.CANONICAL_STORY_FILENAME} "
                            f"at {dest_dir} -- lcats_id must name an existing story bucket, "
                            "not create one"
                        ),
                    )
                )
                continue

            dest_path = dest_dir / discovery.GENRE_SIDECAR_FILENAME
            if dest_path.is_file():
                try:
                    existing = json.loads(dest_path.read_text(encoding="utf-8"))
                except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                    existing = None
                if existing is not None and genre_sidecar.is_legacy_flat_sidecar(
                    existing
                ):
                    rejected.append(
                        SidecarPromotionFinding(
                            lcats_id=lcats_id,
                            error=(
                                f"refusing to promote: {dest_path} already holds "
                                "a legacy flat genre.json; convert it via lcats "
                                "annotate before promoting a v1 sidecar here"
                            ),
                        )
                    )
                    continue

            if not dry_run:
                _atomic_write_text(dest_path, json.dumps(record, indent=2))
            promoted.append(lcats_id)

    return SidecarTranchePromotionReport(
        promoted=tuple(promoted), rejected=tuple(rejected)
    )
