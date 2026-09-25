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
import typing

from lcats.analysis.corpus import cli
from lcats.analysis.corpus import discovery
from lcats.analysis.corpus import genre_sidecar
from lcats.analysis.corpus import sidecar_validators
from lcats.analysis.corpus import specials
from lcats.utils import run_log

BLOCKING_CLASSIFICATION = "likely_repairable"

# Outside both --source (data/) and --dest (corpora/ by default), both
# protected by run_log.RunLog's own re-validation - "logs" is a plain
# sibling directory, relative to the current working directory like
# every other env-overridable root in lcats.utils.env (WI-RUNLOG-0083).
DEFAULT_PROMOTE_LOG_DIR = pathlib.Path("logs") / "promote"

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
class OrphanedSidecarFinding:
    """One registered sidecar kind present at the destination for a story
    but absent from the corresponding source -- a wholesale replace that
    proceeded would silently delete it (WI-PROMOTE-0101, Decision 6 of
    PROP-LCATS-PROMOTE-MODE-REDESIGN)."""

    lcats_id: str
    sidecar_name: str


@dataclasses.dataclass(frozen=True)
class CollectionSurveyResult:
    """Survey outcome for one collection directory."""

    collection: str
    story_count: int
    findings: tuple[BlockingFinding, ...]
    sidecar_findings: tuple[MalformedSidecarFinding, ...] = ()
    orphaned_sidecar_findings: tuple[OrphanedSidecarFinding, ...] = ()

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

        An orphaned sidecar (WI-PROMOTE-0101) blocks the same way --
        ``orphaned_sidecar_findings`` is always empty from
        ``survey_collection()`` itself (a source-only pass with no
        destination awareness); ``promote_collections()`` populates it via
        ``dataclasses.replace()`` after a separate destination-aware check,
        so this property still correctly reflects promotability once that
        happens.
        """
        return (
            not self.findings
            and not self.sidecar_findings
            and not self.orphaned_sidecar_findings
            and self.story_count > 0
        )


def _validate_sidecars(story_path: pathlib.Path) -> list[MalformedSidecarFinding]:
    """Check a story bucket's genre.json/scenes.json -- when present --
    for basic parse/shape validity. Not a schema-validation pass (per
    WI-ANNOTATE-0052's Non-Goals): parses as JSON, is a dict, and has the
    one required top-level key each sidecar's real writer (annotate.py)
    always populates, with the expected value type -- key presence alone
    would still wave through e.g. {"segments": null} (review finding, PR
    #248). A missing sidecar is not itself a finding -- most of data/
    predates lcats annotate and has no sidecars at all.

    genre.json is a special case as of WI-GENRE-0076: `lcats annotate` now
    writes the append-only genre-sidecar-v1 shape (nested
    assessments[].result), which never carries the legacy top-level
    detected_genre key this function otherwise requires -- a v1-shaped
    genre.json would be wrongly reported malformed by the plain
    required-key check below. Any genre.json that isn't the legacy flat
    shape is instead checked via genre_sidecar.validate_sidecar()
    (review finding, PR #357); scenes.json's check is unaffected."""
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
        if sidecar_name == discovery.GENRE_SIDECAR_FILENAME and not (
            genre_sidecar.is_legacy_flat_sidecar(data)
        ):
            validation = genre_sidecar.validate_sidecar(data)
            if not validation.valid:
                findings.append(
                    MalformedSidecarFinding(
                        story_path=story_path,
                        sidecar_name=sidecar_name,
                        error="; ".join(
                            f"{finding.path}: {finding.message}"
                            for finding in validation.findings
                        ),
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


def _validate_log_dir_outside_promotion_roots(
    log_dir: pathlib.Path, source_root: pathlib.Path, dest_root: pathlib.Path
) -> None:
    """Raise ValueError if log_dir is source_root/dest_root themselves, or
    nested inside either.

    run_log.RunLog's own protected-root guard only checks against the
    canonical environment data/corpora roots (checkpoint.py's
    _protected_roots(), anchored to this project's own pyproject.toml) --
    not against whatever source_root/dest_root this specific call was
    given, which may be arbitrary caller-supplied paths (e.g. in tests,
    or a custom --source/--dest). Without this check, a log_dir nested
    under source_root would get silently wholesale-copied into dest_root
    by _copy_collection's own unfiltered copytree, contaminating the
    promoted corpus with an operational log file that was never part of
    the source collection (review finding, PR #407).
    """
    resolved_log_dir = log_dir.resolve()
    for label, root in (("source_root", source_root), ("dest_root", dest_root)):
        resolved_root = root.resolve()
        if (
            resolved_log_dir == resolved_root
            or resolved_root in resolved_log_dir.parents
        ):
            raise ValueError(
                f"log_dir ({resolved_log_dir}) is {label} ({resolved_root}) "
                "or is nested inside it; refusing to write the run log "
                "there, since it could be wholesale-copied into a "
                "promoted collection."
            )


def _copy_collection(source_dir: pathlib.Path, dest_dir: pathlib.Path) -> None:
    """Wholesale-replace dest_dir with a copy of source_dir's contents."""
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    shutil.copytree(source_dir, dest_dir)


def _find_orphaned_sidecars(
    source_dir: pathlib.Path, dest_dir: pathlib.Path
) -> list[OrphanedSidecarFinding]:
    """Compare a destination collection's registered sidecars against the
    corresponding source story buckets, returning every sidecar that
    exists at the destination for a story but is missing from source --
    exactly what ``replace``'s wholesale ``rmtree``+``copytree`` would
    silently delete (``WI-PROMOTE-0101``, Decision 6 of
    ``PROP-LCATS-PROMOTE-MODE-REDESIGN``).

    Iterates the *destination* collection's own story buckets, not the
    source's -- the opposite traversal direction from every other check
    in this module, since a sidecar can only be orphaned by existing at
    the destination in the first place. A destination collection that
    doesn't exist yet (a first-time promotion) trivially returns no
    findings -- there is nothing to orphan. Only *registered* sidecar
    kinds (via ``sidecar_validators.registered_filenames()``) are
    checked -- not a generic "any destination-only file" diff, which was
    rejected for false-positive risk on legitimate corpora-only content
    unrelated to sidecar promotion.

    A destination-only story -- one with no ``story.json`` at all in the
    corresponding source bucket -- is never flagged, even if it has a
    registered sidecar (review finding, PR #416): a wholesale ``replace``
    legitimately removes a story that's been retired from source entirely,
    and that is not the "sidecar quietly lost while the story itself
    survives" scenario this guard exists to catch. Only a story that
    exists in *both* trees, with the sidecar present at destination and
    missing from that same source bucket, counts as orphaned.
    """
    if not dest_dir.is_dir():
        return []
    findings: list[OrphanedSidecarFinding] = []
    registered = sidecar_validators.registered_filenames()
    for dest_story_path in discovery.iter_collection_story_files(dest_dir):
        bucket_dir = dest_story_path.parent
        lcats_id = f"{dest_dir.name}/{bucket_dir.name}"
        source_bucket_dir = source_dir / bucket_dir.name
        if not (source_bucket_dir / discovery.CANONICAL_STORY_FILENAME).is_file():
            # Destination-only story -- replace is expected to remove it
            # wholesale, sidecars included; not an orphan.
            continue
        for sidecar_name in registered:
            if (bucket_dir / sidecar_name).is_file() and not (
                source_bucket_dir / sidecar_name
            ).is_file():
                findings.append(
                    OrphanedSidecarFinding(lcats_id=lcats_id, sidecar_name=sidecar_name)
                )
    return findings


def promote_collections(
    source_root: pathlib.Path,
    dest_root: pathlib.Path,
    collection_names: list[str] | None = None,
    dry_run: bool = False,
    log_dir: pathlib.Path | None = None,
    allow_orphaned_sidecar_deletion: bool = False,
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

    Unless ``allow_orphaned_sidecar_deletion`` is True, a collection that is
    otherwise clean is additionally blocked if the wholesale replace would
    delete a registered sidecar kind present at the destination for a story
    but absent from source (see ``_find_orphaned_sidecars``,
    ``WI-PROMOTE-0101``) -- the actual scenario a live Copilot review finding
    on PR #362 described, made concrete by an imminent whole-corpus
    ``linguistics.json`` rollout. This orphan check never applies when
    ``allow_orphaned_sidecar_deletion`` is True, and never runs at all for a
    destination collection that doesn't exist yet (nothing to orphan on a
    first-time promotion).

    The whole call (surveying and copying both) is wrapped in a
    run_log.RunLog scope, log path ``<log_dir>/promote_run_log.jsonl``
    (outside both source_root/dest_root, typically data/ and corpora/,
    both protected roots by default) - a crash mid-copy (a destructive
    local rmtree-then-copytree per collection) leaves a readable partial
    log showing which collections completed and which was in flight
    (WI-RUNLOG-0083). promote.py has no FatalPromoteError/account-level
    fatal exception class, so any uncaught exception here -- from
    surveying or from _copy_collection -- is classified
    run_aborted_unexpected, never left uncategorized.

    Args:
        source_root: Root directory containing collection subdirectories
            (typically data/).
        dest_root: Root directory to promote clean collections into
            (typically corpora/).
        collection_names: Collection directory names to consider; defaults to
            every subdirectory of source_root.
        dry_run: When True, survey and report but do not copy any files.
        log_dir: Directory for the run-event log; None (the default)
            resolves to DEFAULT_PROMOTE_LOG_DIR at call time -- not bound
            as the parameter's own default value, so a test can patch
            the module-level constant instead of passing an explicit
            override at every one of this function's many call sites.
        allow_orphaned_sidecar_deletion: When True, skips the
            orphaned-sidecar guard entirely, restoring today's unguarded
            wholesale-replace behavior for every otherwise-clean
            collection.

    Returns:
        A PromotionReport listing promoted collection names and blocked
        CollectionSurveyResult entries.

    Raises:
        ValueError: If source_root and dest_root are the same or nested,
            or if log_dir is nested inside either.
    """
    if log_dir is None:
        log_dir = DEFAULT_PROMOTE_LOG_DIR
    _validate_distinct_roots(source_root, dest_root)
    _validate_log_dir_outside_promotion_roots(log_dir, source_root, dest_root)

    if collection_names is None:
        collection_names = sorted(
            entry.name for entry in source_root.iterdir() if entry.is_dir()
        )

    promoted: list[str] = []
    blocked: list[CollectionSurveyResult] = []
    with run_log.RunLog(
        log_dir,
        "promote_run_log.jsonl",
        collection_names=list(collection_names),
        dry_run=dry_run,
    ) as log:
        # Loading the allowlist config lives inside the RunLog scope too
        # (not before it), so an unexpected failure here is captured as
        # run_aborted_unexpected instead of escaping the run log
        # entirely (review finding, PR #407).
        allowlist = specials.load_allowlist_config(
            specials.default_allowlist_config_path()
        )
        results = [
            survey_collection(source_root / name, allowlist=allowlist)
            for name in collection_names
        ]

        for name, result in zip(collection_names, results):
            if not result.clean:
                blocked.append(result)
                log.event(
                    "collection_blocked",
                    collection=name,
                    finding_count=len(result.findings),
                    sidecar_finding_count=len(result.sidecar_findings),
                    orphaned_sidecar_finding_count=len(
                        result.orphaned_sidecar_findings
                    ),
                )
                continue

            if not allow_orphaned_sidecar_deletion:
                orphaned_findings = _find_orphaned_sidecars(
                    source_root / name, dest_root / destination_name(name)
                )
                if orphaned_findings:
                    result = dataclasses.replace(
                        result,
                        orphaned_sidecar_findings=tuple(orphaned_findings),
                    )
                    blocked.append(result)
                    log.event(
                        "collection_blocked",
                        collection=name,
                        finding_count=len(result.findings),
                        sidecar_finding_count=len(result.sidecar_findings),
                        orphaned_sidecar_finding_count=len(
                            result.orphaned_sidecar_findings
                        ),
                    )
                    continue

            log.event("promote_start", collection=name)
            if not dry_run:
                _copy_collection(source_root / name, dest_root / destination_name(name))
            log.event("promote_end", collection=name)
            promoted.append(name)

    return PromotionReport(promoted=tuple(promoted), blocked=tuple(blocked))


@dataclasses.dataclass(frozen=True)
class SidecarPromotionFinding:
    """One manifest envelope rejected during sidecar promotion."""

    lcats_id: str
    error: str


@dataclasses.dataclass(frozen=True)
class SidecarTranchePromotionReport:
    """Outcome of an insert/upsert sidecar-manifest promotion run."""

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


def _sidecar_filename_is_safe(sidecar_filename: str) -> bool:
    """Return True if ``sidecar_filename`` is safe to join onto a
    destination story bucket directory.

    Every currently-registered filename is already a single, hardcoded
    path component with no separators, so this only matters for the
    ``--allow-unvalidated`` path: an arbitrary, un-registered
    ``--sidecar`` value could otherwise be an absolute path, contain
    ``..``/``/`` components (escaping the story bucket), or name the
    canonical ``story.json`` itself (letting ``upsert --allow-unvalidated``
    silently overwrite the story rather than a sidecar) -- review finding,
    PR #405."""
    if not sidecar_filename or sidecar_filename in (".", ".."):
        return False
    if "/" in sidecar_filename or "\\" in sidecar_filename:
        return False
    if pathlib.PurePosixPath(sidecar_filename).name != sidecar_filename:
        return False
    if sidecar_filename == discovery.CANONICAL_STORY_FILENAME:
        return False
    return True


def _iter_manifest_records(
    manifest_path: pathlib.Path,
) -> typing.Iterator[tuple[str, dict | None, str | None]]:
    """Yield ``(label, envelope, error)`` triples from a JSONL manifest
    file, one per non-blank line -- the manifest-file source for
    ``_promote_sidecar_records``. ``label`` is ``"<line N>"``; ``error`` is
    set (with ``envelope`` None) only for a line that fails to parse as
    JSON, so a single malformed line is a per-record rejection, not a
    fatal abort of the whole manifest (matching every other per-record
    rejection this engine already makes)."""
    with manifest_path.open("r", encoding="utf-8") as manifest_file:
        for line_number, raw_line in enumerate(manifest_file, start=1):
            line = raw_line.strip()
            if not line:
                continue
            label = f"<line {line_number}>"
            try:
                envelope = json.loads(line)
            except json.JSONDecodeError as exc:
                yield label, None, f"could not parse manifest line as JSON: {exc}"
                continue
            yield label, envelope, None


def _iter_scanned_sidecar_envelopes(
    source_root: pathlib.Path, sidecar_filename: str
) -> typing.Iterator[tuple[str, dict | None, str | None]]:
    """Yield ``(label, envelope, error)`` triples by scanning
    ``source_root/<collection>/<story>/<sidecar_filename>`` for every
    story bucket under every collection directory in ``source_root`` --
    the live-directory-scan source for ``_promote_sidecar_records``
    (``WI-PROMOTE-0100``, Decision 8 of
    ``PROP-LCATS-PROMOTE-MODE-REDESIGN``).

    A bucket is only considered if it already has the sidecar file
    present -- buckets without it are silently skipped, not reported,
    since "does this story have this sidecar yet" is exactly what a scan
    is for, not an error condition. Every bucket that has the sidecar
    file is yielded, letting the downstream escape-check and
    destination-story-exists check in ``_promote_sidecar_records`` decide
    promotability the same way a manifest record would -- this function
    performs no validation of its own.

    ``label``/routing ``lcats_id`` is the bucket's path relative to
    ``source_root`` (POSIX-style, e.g. ``"anderson/bell"``), matching the
    identity convention manifest envelopes already use. ``envelope`` is
    built directly as ``{"lcats_id": label, "payload": <parsed sidecar
    content>}`` -- always the full envelope shape, even for a payload kind
    that could self-identify via the bare-record compatibility path,
    since a scan already knows the correct routing identity from the
    bucket's own location and has no reason to rely on the payload's
    possibly-stale or absent own fields.
    """
    for collection_dir in sorted(
        entry for entry in source_root.iterdir() if entry.is_dir()
    ):
        for story_path in discovery.iter_collection_story_files(collection_dir):
            bucket_dir = story_path.parent
            sidecar_path = bucket_dir / sidecar_filename
            if not sidecar_path.is_file():
                continue
            label = bucket_dir.relative_to(source_root).as_posix()
            try:
                payload = json.loads(sidecar_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                yield (
                    label,
                    None,
                    f"could not parse {sidecar_path} as JSON: {exc}",
                )
                continue
            yield label, {"lcats_id": label, "payload": payload}, None


def _promote_sidecar_records(
    records: typing.Iterable[tuple[str, dict | None, str | None]],
    dest_root: pathlib.Path,
    sidecar_filename: str,
    *,
    overwrite: bool,
    allow_unvalidated: bool,
    dry_run: bool,
) -> SidecarTranchePromotionReport:
    """Shared engine for ``insert``/``upsert``: promote sidecars described
    by ``records`` into corpora/, without touching any other file in the
    destination collection directory. ``records`` may come from a JSONL
    manifest file (``_iter_manifest_records``) or a live directory scan
    (``_iter_scanned_sidecar_envelopes``) -- both sources feed this one
    engine, so validation/escape-check/identity-agreement/overwrite logic
    is never duplicated between them (``WI-PROMOTE-0100`` acceptance).

    Each record's ``envelope`` is normally the manifest-envelope shape,
    ``{"lcats_id": "<destination story id>", "payload": {<sidecar
    content>}}`` -- not a bare sidecar record -- so that destination
    routing works uniformly across every registered sidecar kind,
    including ones whose payload carries no identity field of its own
    (e.g. ``scenes.json``; review finding, PR #401, ``WI-PROMOTE-0097``).

    **Bare-record compatibility path** (review finding, PR #405): an
    ``envelope`` with no ``"payload"`` field is also accepted when it
    carries its own non-empty top-level ``lcats_id`` -- the whole record is
    then treated as the payload, and that same ``lcats_id`` is used for
    routing. This keeps existing genre-sidecar-v1 manifests (e.g.
    ``WI-GENRE-0004``'s ``validation_results.jsonl``, produced by
    ``experiments/05_metadata_genre_prefilter/run_prefilter.py`` and
    consumed by ``WI-GENRE-0077``) promotable without a migration. A
    payload with no identity field of its own (``scenes.json``) has no way
    to use this path and must be enveloped.

    ``payload`` is validated via ``sidecar_validators``' registry, then
    written as-is. When ``payload`` is a dict carrying its own top-level
    ``lcats_id``, that value must agree with the envelope/routing
    ``lcats_id`` -- a mismatch is rejected, not silently written (review
    finding, PR #405: an identity-bearing payload for one story could
    otherwise be routed to a different story's bucket). A legacy flat
    ``genre.json`` already present at a promotion destination is refused
    explicitly (with a clear error), never silently overwritten --
    converting a legacy sidecar in place is ``lcats annotate``'s job
    (``WI-GENRE-0076``), not this function's.

    Args:
        records: An iterable of ``(label, envelope, error)`` triples. When
            ``error`` is set, ``envelope`` is ignored and the record is
            rejected under ``label`` with that error. Otherwise ``label``
            is used only as the rejection identifier for an envelope-level
            failure that occurs before a real ``lcats_id`` can be
            determined (a malformed envelope, or one missing an
            ``lcats_id``) -- once a real ``lcats_id`` is determined, it
            replaces ``label`` for every subsequent rejection or success.
        dest_root: Root directory to promote into (typically ``corpora/``).
        sidecar_filename: The registered sidecar filename to write (already
            resolved via ``sidecar_validators.resolve_sidecar_filename``).
        overwrite: False for insert (create-only, refuses on conflict);
            True for upsert (create-or-overwrite).
        allow_unvalidated: When True, permits promoting a sidecar kind with
            no registered validator. Never bypasses a registered
            validator's own rejection of malformed content.
        dry_run: When True, validate and report but write nothing.

    Returns:
        A SidecarTranchePromotionReport listing promoted ``lcats_id``
        values and rejected ``SidecarPromotionFinding`` entries.

    Raises:
        ValueError: If ``sidecar_filename`` has no registered validator and
            ``allow_unvalidated`` is False, or if ``sidecar_filename`` is
            not a single safe path component.
    """
    if not _sidecar_filename_is_safe(sidecar_filename):
        raise ValueError(
            f"unsafe sidecar filename {sidecar_filename!r}: must be a single "
            "path component with no '..'/'/' and not the canonical story "
            "filename"
        )

    validator = sidecar_validators.get_validator(sidecar_filename)
    if validator is None and not allow_unvalidated:
        raise ValueError(
            f"no registered validator for sidecar kind {sidecar_filename!r}; "
            "pass allow_unvalidated=True (--allow-unvalidated) to promote it "
            "unvalidated"
        )

    promoted: list[str] = []
    rejected: list[SidecarPromotionFinding] = []

    for label, envelope, error in records:
        if error is not None:
            rejected.append(SidecarPromotionFinding(lcats_id=label, error=error))
            continue

        if not isinstance(envelope, dict):
            rejected.append(
                SidecarPromotionFinding(
                    lcats_id=label,
                    error=(
                        "expected a JSON object envelope, got "
                        f"{type(envelope).__name__}"
                    ),
                )
            )
            continue

        if "payload" in envelope:
            lcats_id = envelope.get("lcats_id")
            if not isinstance(lcats_id, str) or not lcats_id:
                rejected.append(
                    SidecarPromotionFinding(
                        lcats_id=label,
                        error="envelope has no non-empty top-level lcats_id",
                    )
                )
                continue
            payload = envelope["payload"]
        else:
            # Bare-record compatibility path (review finding, PR #405)
            # -- see this function's own docstring.
            bare_lcats_id = envelope.get("lcats_id")
            if not isinstance(bare_lcats_id, str) or not bare_lcats_id:
                rejected.append(
                    SidecarPromotionFinding(
                        lcats_id=label,
                        error=(
                            "record has no 'payload' field and no "
                            "non-empty top-level lcats_id"
                        ),
                    )
                )
                continue
            lcats_id = bare_lcats_id
            payload = envelope

        escape_error = _lcats_id_escape_error(lcats_id, dest_root)
        if escape_error is not None:
            rejected.append(
                SidecarPromotionFinding(lcats_id=lcats_id, error=escape_error)
            )
            continue

        if isinstance(payload, dict) and "lcats_id" in payload:
            payload_lcats_id = payload.get("lcats_id")
            if payload_lcats_id != lcats_id:
                rejected.append(
                    SidecarPromotionFinding(
                        lcats_id=lcats_id,
                        error=(
                            f"payload's own lcats_id {payload_lcats_id!r} "
                            f"does not match routing lcats_id {lcats_id!r}"
                        ),
                    )
                )
                continue

        if validator is not None:
            validation = validator(payload)
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

        dest_path = dest_dir / sidecar_filename
        if dest_path.is_file():
            if sidecar_filename == discovery.GENRE_SIDECAR_FILENAME:
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
            if not overwrite:
                rejected.append(
                    SidecarPromotionFinding(
                        lcats_id=lcats_id,
                        error=(
                            f"refusing to promote: {dest_path} already exists "
                            "(insert mode is create-only; use upsert to overwrite)"
                        ),
                    )
                )
                continue

        if not dry_run:
            try:
                serialized = json.dumps(payload, indent=2)
                _atomic_write_text(dest_path, serialized)
            except (TypeError, ValueError, OverflowError, OSError) as exc:
                rejected.append(
                    SidecarPromotionFinding(
                        lcats_id=lcats_id,
                        error=f"failed to write sidecar: {exc}",
                    )
                )
                continue
        promoted.append(lcats_id)

    return SidecarTranchePromotionReport(
        promoted=tuple(promoted), rejected=tuple(rejected)
    )


def _resolve_sidecar_records(
    manifest_path: pathlib.Path | None,
    scan_source: pathlib.Path | None,
    sidecar_filename: str,
) -> typing.Iterable[tuple[str, dict | None, str | None]]:
    """Return the record source for ``promote_sidecar_insert``/``upsert``:
    exactly one of ``manifest_path`` (a JSONL manifest file) or
    ``scan_source`` (a live directory scan root) must be given -- the two
    sourcing modes are mutually exclusive (``WI-PROMOTE-0100`` acceptance).
    The CLI already enforces this via an ``argparse`` mutually-exclusive
    group; this is the library-level guard for direct callers."""
    if (manifest_path is None) == (scan_source is None):
        raise ValueError("exactly one of manifest_path or scan_source must be given")
    if manifest_path is not None:
        return _iter_manifest_records(manifest_path)
    return _iter_scanned_sidecar_envelopes(scan_source, sidecar_filename)


def promote_sidecar_insert(
    manifest_path: pathlib.Path | None,
    dest_root: pathlib.Path,
    sidecar: str,
    allow_unvalidated: bool = False,
    dry_run: bool = False,
    *,
    scan_source: pathlib.Path | None = None,
) -> SidecarTranchePromotionReport:
    """Create-only: write named sidecars into existing story buckets,
    refusing (not overwriting) any that already exist. Never touches any
    other file in the destination bucket or collection. Records come from
    exactly one of ``manifest_path`` (a JSONL manifest of envelopes) or
    ``scan_source`` (a live directory scan of
    ``<collection>/<story>/<sidecar-filename>`` under that root) -- pass
    ``None`` for ``manifest_path`` to use ``scan_source`` instead. See
    ``_promote_sidecar_records`` for the shared engine and manifest
    envelope shape."""
    sidecar_filename = sidecar_validators.resolve_sidecar_filename(sidecar)
    records = _resolve_sidecar_records(manifest_path, scan_source, sidecar_filename)
    return _promote_sidecar_records(
        records,
        dest_root,
        sidecar_filename,
        overwrite=False,
        allow_unvalidated=allow_unvalidated,
        dry_run=dry_run,
    )


def promote_sidecar_upsert(
    manifest_path: pathlib.Path | None,
    dest_root: pathlib.Path,
    sidecar: str,
    allow_unvalidated: bool = False,
    dry_run: bool = False,
    *,
    scan_source: pathlib.Path | None = None,
) -> SidecarTranchePromotionReport:
    """Create-or-overwrite: write named sidecars into existing story
    buckets, whole-file overwrite only (no in-sidecar content merge).
    Never touches or deletes any other file in the destination bucket or
    collection. Records come from exactly one of ``manifest_path`` (a
    JSONL manifest of envelopes) or ``scan_source`` (a live directory scan
    of ``<collection>/<story>/<sidecar-filename>`` under that root) -- pass
    ``None`` for ``manifest_path`` to use ``scan_source`` instead. See
    ``_promote_sidecar_records`` for the shared engine and manifest
    envelope shape."""
    sidecar_filename = sidecar_validators.resolve_sidecar_filename(sidecar)
    records = _resolve_sidecar_records(manifest_path, scan_source, sidecar_filename)
    return _promote_sidecar_records(
        records,
        dest_root,
        sidecar_filename,
        overwrite=True,
        allow_unvalidated=allow_unvalidated,
        dry_run=dry_run,
    )
