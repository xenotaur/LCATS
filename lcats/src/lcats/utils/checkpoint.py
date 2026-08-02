# lcats/src/lcats/utils/checkpoint.py
"""Shared checkpoint helper for LCATS's LLM-driven batch scripts.

Generalizes ``DataGatherer``'s dual-root bucket-directory + file-existence
pattern (``lcats.gatherers.downloaders``) into a reusable, per-item/per-stage
checkpoint mechanism for staged pipelines (segment -> extract -> relate,
etc.), so a crash or interruption discards only the in-flight stage, not
every already-completed one.

Design decisions (see ``project/memory/decision_log.md``'s 2026-08-02
entry and ``PROP-LCATS-PIPELINE-CHECKPOINTING``):

- **Dual root.** Callers pass a required ``working_root`` (where checkpoint
  files are written) and an optional ``source_root`` (where upstream/input
  content lives), via :func:`resolve_roots`. ``source_root`` defaults to
  ``working_root`` when omitted, implying in-place checkpointing. This
  module never reads ``source_root`` itself -- it exists purely so a
  caller's own input-reading logic (e.g. via
  ``lcats.analysis.corpus.discovery``) has somewhere to point that is
  independent of where checkpoints get written.
- **Write-guard, working_root only.** ``source_root`` is deliberately never
  guarded: pointing it at ``data/`` or ``corpora/`` as a read-only input is
  the whole reason for the dual-root split. ``working_root`` is guarded
  because ``lcats promote``'s ``_copy_collection``
  (``lcats.analysis.corpus.promote``) does an unfiltered ``shutil.copytree``
  of an entire bucket directory -- any sidecar written into a ``data/``
  bucket ships to ``corpora/`` with no filtering -- and because ``data/``
  is documented as a disposable, regenerable cache, not durable storage
  (``project/design/design.md``: "``data/`` regenerates from cache").
- **CWD-independent protected roots.** The guard does not use
  ``lcats.utils.env.data_root()``/``corpora_root()`` directly: both resolve
  their defaults relative to the *process's* current working directory,
  but ``run_pilot.py`` is documented to run from the repo root with a
  default ``--data-dir=lcats/data``, a different directory than
  ``env.data_root()`` resolves to from that CWD (review finding, PR #210).
  Instead this module reuses ``env.py``'s own default relative-path
  strings (``"data"``, ``"../corpora"``, including their
  ``LCATS_DATA_DIR``/``LCATS_CORPORA_DIR`` overrides) but resolves them
  against ``paths.find_pyproject_root(__file__)`` -- this module's own
  file location, never the caller's CWD -- the same pattern
  ``lcats.utils.secrets``/``lcats.utils.test_utils`` already use.
- **Fingerprint required, contents caller-defined.** Every checkpoint write
  takes an explicit ``fingerprint`` argument (never a silent default). A
  falsy fingerprint (``None``, ``{}``) is a caller's deliberate,
  visible opt-out of mismatch invalidation, not an omitted parameter --
  see :func:`read_checkpoint`. Fingerprints are compared after a JSON
  round-trip on both sides (:func:`_normalize_fingerprint`), so a
  fingerprint containing tuples or int dict keys still matches its own
  previously-recorded form.
- **A recorded failure is not "done."** ``read_checkpoint`` only reports
  ``done=True`` for a recorded "success" -- a recorded "failure" is
  recoverable and must be recomputed on resume, not silently skipped
  just because a checkpoint file exists.
- **Atomic publication.** Writes go to a temp file in the same directory as
  the target and are moved into place via ``os.replace`` only after the
  write completes, so an interruption mid-write never leaves a torn
  checkpoint file in place of a real one.
"""

from __future__ import annotations

import dataclasses
import json
import os
import pathlib
import tempfile
from typing import Any, Optional, Union

from lcats.utils import paths

PathLike = Union[str, pathlib.Path]

_SUCCESS = "success"
_FAILURE = "failure"
_VALID_OUTCOMES = (_SUCCESS, _FAILURE)


class ProtectedRootError(ValueError):
    """Raised when working_root resolves under a protected data/corpora root."""


@dataclasses.dataclass(frozen=True)
class CheckpointRoots:
    """A resolved (working_root, source_root) pair for a pipeline run.

    ``source_root`` defaults to ``working_root`` when the caller omits it,
    implying in-place checkpointing. Only ``working_root`` is subject to
    the protected-root write-guard -- see :func:`resolve_roots`.
    """

    working_root: pathlib.Path
    source_root: pathlib.Path


@dataclasses.dataclass(frozen=True)
class CheckpointResult:
    """The outcome of checking whether a checkpoint is already done.

    ``done`` is False for: no checkpoint file, a checkpoint file that
    fails to parse (I/O error, JSON/Unicode decode error, unexpected
    shape), a checkpoint whose recorded fingerprint does not match the
    caller's current fingerprint, or a checkpoint recording a "failure"
    outcome. None of these are raised as errors -- an incomplete/stale/
    failed checkpoint is exactly the "not done yet" case a caller should
    recompute for, not a hard failure. ``outcome``/``data`` are still
    populated for a recorded failure (unlike the other False cases),
    since it does exist and may be worth inspecting.
    """

    done: bool
    outcome: Optional[str] = None
    data: Any = None


def _protected_roots() -> tuple[pathlib.Path, pathlib.Path]:
    """Return the canonical (data_root, corpora_root) paths.

    Reuses env.py's own default relative-path strings and env-var
    overrides (LCATS_DATA_DIR default "data", LCATS_CORPORA_DIR default
    "../corpora"), but resolves them against this module's own file
    location via paths.find_pyproject_root, not the process's CWD -- see
    this module's docstring for why env.data_root()/env.corpora_root()
    themselves are not used directly here.
    """
    anchor = paths.find_pyproject_root(__file__)
    data_default = os.environ.get("LCATS_DATA_DIR", "data")
    corpora_default = os.environ.get("LCATS_CORPORA_DIR", "../corpora")
    return (
        (anchor / data_default).resolve(),
        (anchor / corpora_default).resolve(),
    )


def _is_under(candidate: pathlib.Path, root: pathlib.Path) -> bool:
    """Return True if candidate is root itself or nested inside it."""
    return candidate == root or root in candidate.parents


def _check_working_root_allowed(
    working_root: pathlib.Path, allow_protected_root: bool
) -> None:
    if allow_protected_root:
        return
    resolved = working_root.resolve()
    try:
        protected_roots = _protected_roots()
    except FileNotFoundError as error:
        raise RuntimeError(
            "cannot determine the protected data/corpora roots for the "
            "working_root write-guard: no pyproject.toml found in any "
            "ancestor of lcats.utils.checkpoint's own file location. This "
            "usually means lcats is installed as a non-editable package "
            "outside its source checkout. Pass allow_protected_root=True "
            "if you have independently confirmed working_root is safe."
        ) from error
    for protected in protected_roots:
        if _is_under(resolved, protected):
            raise ProtectedRootError(
                f"working_root ({resolved}) resolves under the protected "
                f"root {protected}; refusing to write checkpoints there "
                "(data/ is a disposable cache and corpora/ is copied "
                "wholesale by `lcats promote` -- see this module's "
                "docstring). Pass allow_protected_root=True to override "
                "this deliberately."
            )


def resolve_roots(
    working_root: PathLike,
    source_root: Optional[PathLike] = None,
    *,
    allow_protected_root: bool = False,
) -> CheckpointRoots:
    """Resolve and validate a (working_root, source_root) pair.

    Raises:
        ProtectedRootError: working_root resolves under the canonical
            data/ or corpora/ root and allow_protected_root was not set.
        RuntimeError: the protected data/corpora roots could not be
            determined at all (e.g. a non-editable install with no
            source tree to walk) -- distinct from ProtectedRootError,
            since allow_protected_root cannot fix a situation where the
            guard couldn't run in the first place.
    """
    working_root = pathlib.Path(working_root)
    _check_working_root_allowed(working_root, allow_protected_root)

    resolved_source = (
        pathlib.Path(source_root) if source_root is not None else working_root
    )
    return CheckpointRoots(working_root=working_root, source_root=resolved_source)


def _validate_path_component(value: str, name: str) -> None:
    """Raise ValueError if value is not safe to use as a single path segment.

    item_id/stage are caller-supplied identifiers, not paths -- without
    this check, a value containing a path separator, "..", or an
    absolute path could escape working_root entirely (e.g.
    item_id="/tmp" ignoring working_root altogether; review finding,
    PR #213).
    """
    parts = pathlib.PurePath(value).parts
    if len(parts) != 1 or value in (".", ".."):
        raise ValueError(
            f"{name} must be a single, relative path segment, got {value!r}"
        )


def checkpoint_path(working_root: PathLike, item_id: str, stage: str) -> pathlib.Path:
    """Return the path a checkpoint for (item_id, stage) is stored at.

    item_id is used as-is as the subdirectory name under working_root,
    reusing the same directory-slug identity
    lcats.analysis.corpus.discovery's canonical story-bucket selector
    uses for a story's own bucket directory -- this module does not
    invent a second identity scheme.

    Raises:
        ValueError: item_id or stage is not a safe single path segment.
    """
    _validate_path_component(item_id, "item_id")
    _validate_path_component(stage, "stage")
    return pathlib.Path(working_root) / item_id / f"{stage}.json"


def _normalize_fingerprint(fingerprint: Any) -> Any:
    """Round-trip fingerprint through JSON so comparisons match what
    would actually be recorded on disk.

    Without this, a fingerprint containing a tuple or an int dict key
    compares unequal to its own just-written, JSON-decoded form (tuples
    become lists, int keys become strings), so a checkpoint would never
    be honored and expensive stages would be recomputed on every resume
    (review finding, PR #213).

    A non-JSON-serializable fingerprint (e.g. containing a set) falls
    back to the original value unchanged rather than raising -- it won't
    normalize identically to a stored one, but read_checkpoint's contract
    is that a mismatch is treated as "not done," not a crash (independent
    review finding after PR #213's own fix round).
    """
    if not fingerprint:
        return fingerprint
    try:
        return json.loads(json.dumps(fingerprint))
    except TypeError:
        return fingerprint


def read_checkpoint(
    working_root: PathLike,
    item_id: str,
    stage: str,
    fingerprint: Any,
) -> CheckpointResult:
    """Check whether (item_id, stage) already has a completed checkpoint
    under working_root matching fingerprint.

    ``done`` is True only for a recorded "success" outcome. A recorded
    "failure" is not done -- the governing design treats a recorded
    failure as recoverable and requires it be recomputed on resume, not
    silently treated as complete just because a checkpoint file exists
    (review finding, PR #213); its outcome/data are still returned for
    inspection, distinguishing it from a checkpoint that doesn't exist
    at all.

    fingerprint here is the caller's *current* configuration identity,
    compared (after JSON-normalizing both sides -- see
    _normalize_fingerprint) against whatever was recorded when the
    checkpoint was written. If the checkpoint was written with an
    empty/no-op fingerprint (write_checkpoint's own opt-out -- see its
    docstring), the recorded fingerprint is falsy and the mismatch check
    never invalidates the checkpoint, regardless of what is passed here,
    since there is nothing to compare against. A fingerprint mismatch is
    treated as if the checkpoint did not exist at all -- unlike a
    recorded failure, no outcome/data is returned.

    Only working_root is consulted; source_root is never read here (see
    this module's docstring).
    """
    path = checkpoint_path(working_root, item_id, stage)
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return CheckpointResult(done=False)

    if not isinstance(record, dict) or record.get("outcome") not in _VALID_OUTCOMES:
        return CheckpointResult(done=False)

    recorded_fingerprint = record.get("fingerprint")
    if recorded_fingerprint:
        if recorded_fingerprint != _normalize_fingerprint(fingerprint):
            return CheckpointResult(done=False)

    outcome = record["outcome"]
    return CheckpointResult(
        done=(outcome == _SUCCESS), outcome=outcome, data=record.get("data")
    )


def write_checkpoint(
    working_root: PathLike,
    item_id: str,
    stage: str,
    outcome: str,
    fingerprint: Any,
    data: Any = None,
) -> pathlib.Path:
    """Atomically record a checkpoint outcome for (item_id, stage).

    Writes to a temporary file in the same directory as the checkpoint
    target and moves it into place via os.replace only once the write
    completes, so an interruption mid-write (including one that raises
    BaseException, e.g. KeyboardInterrupt) never leaves a torn file where
    the checkpoint would be read from -- the temp file is cleaned up
    instead, leaving the prior state (checkpoint present or absent)
    unchanged.

    Args:
        working_root: Directory the checkpoint is written under. Callers
            are expected to have already validated this via
            resolve_roots(); this function does not re-check the
            protected-root guard, so it must not be called with a
            working_root that has not passed that check.
        item_id: Directory slug identifying the item (e.g. a story).
        stage: Name of the pipeline stage this checkpoint covers.
        outcome: "success" or "failure".
        fingerprint: Caller-defined configuration identity (e.g. model
            name plus a prompt/schema version). Required on every call --
            pass None or {} to explicitly record "no fingerprint tracked
            for this checkpoint" rather than omitting the argument.
        data: Optional JSON-serializable payload to store alongside the
            outcome (e.g. the actual extracted result for this stage).

    Returns:
        The path the checkpoint was written to.

    Raises:
        ValueError: outcome is not "success"/"failure", or item_id/stage
            is not a safe single path segment (see checkpoint_path).
    """
    if outcome not in _VALID_OUTCOMES:
        raise ValueError(f"outcome must be one of {_VALID_OUTCOMES}, got {outcome!r}")

    target = checkpoint_path(working_root, item_id, stage)
    item_dir = target.parent
    paths.makedirs(item_dir)

    record = {"outcome": outcome, "fingerprint": fingerprint, "data": data}

    fd, tmp_name = tempfile.mkstemp(dir=item_dir, prefix=f".{stage}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
            json.dump(record, tmp_file)
        os.replace(tmp_name, target)
    except BaseException:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise

    return target
