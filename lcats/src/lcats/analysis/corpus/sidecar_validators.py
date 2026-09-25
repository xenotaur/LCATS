"""Registry mapping registered sidecar filenames to validator callables.

Built for ``lcats promote``'s ``insert``/``upsert`` modes
(``WI-PROMOTE-0097``, ``PROP-LCATS-PROMOTE-MODE-REDESIGN`` Decision 5):
``promote.py`` imports only this module for validation, never
``genre_sidecar.py`` or ``analysis/linguistics/sidecar.py`` directly, so a
promotion of an unrelated sidecar kind (or a ``replace``-mode invocation,
which never validates at all) never pays the cost of importing
``linguistics/sidecar.py``'s heavier dependency chain
(``lcats.analysis.event_role_world.surface_feature_extractor``). Each
linguistics validator is therefore wrapped in a function that imports
``analysis.linguistics.sidecar`` lazily, inside the call -- not at this
module's own import time.

The two linguistics filenames below duplicate the canonical
``SIDECAR_FILENAME``/``TOKEN_DETAIL_FILENAME`` constants defined in
``analysis/linguistics/sidecar.py``, rather than importing them, for the
same reason: importing that module at all -- even just for its string
constants -- runs its top-level import of ``surface_feature_extractor``.
Both filenames are stable, already-shipped conventions; if either ever
changes, update both this module and its canonical definition together.
"""

from __future__ import annotations

from typing import Any, Callable, Protocol, Sequence

from lcats.analysis.corpus import discovery
from lcats.analysis.corpus import genre_sidecar

# Mirrors analysis/linguistics/sidecar.py's SIDECAR_FILENAME/
# TOKEN_DETAIL_FILENAME -- see module docstring for why these are
# duplicated rather than imported.
LINGUISTICS_SIDECAR_FILENAME = "linguistics.json"
LINGUISTICS_TOKEN_DETAIL_FILENAME = "linguistics.tokens.json"


class _ValidationResultLike(Protocol):
    """Structural shape shared by ``genre_sidecar.ValidationResult`` and
    ``analysis.linguistics.sidecar.ValidationResult`` -- two distinct
    dataclasses (never unified into one type, to keep each validation
    module independent) that both expose ``valid``/``findings``. A
    validator callable may return either concrete class; this Protocol
    describes what callers actually rely on, rather than incorrectly
    claiming every validator returns ``genre_sidecar.ValidationResult``
    specifically (review finding, PR #405)."""

    valid: bool
    findings: Sequence[Any]


ValidatorFn = Callable[[Any], _ValidationResultLike]


def _validate_genre(data: Any) -> genre_sidecar.ValidationResult:
    return genre_sidecar.validate_sidecar(data)


def _validate_linguistics(data: Any) -> genre_sidecar.ValidationResult:
    from lcats.analysis.linguistics import sidecar as linguistics_sidecar

    return linguistics_sidecar.validate_sidecar(data)


def _validate_linguistics_token_detail(data: Any) -> genre_sidecar.ValidationResult:
    from lcats.analysis.linguistics import sidecar as linguistics_sidecar

    return linguistics_sidecar.validate_token_detail(data)


def _validate_scenes(data: Any) -> genre_sidecar.ValidationResult:
    """Adapter mirroring ``promote.py``'s existing
    ``_SIDECAR_REQUIRED_KEYS``-based shape check for ``scenes.json``
    (``segments`` must be a list) -- reimplemented here rather than
    imported from ``promote.py``, since ``promote.py`` imports this
    module and importing back would be circular. Per
    ``PROP-LCATS-PROMOTE-MODE-REDESIGN`` Decision 5, this needs no new
    validation logic invented from scratch, just the existing shape
    check made available through the registry.
    """
    if not isinstance(data, dict):
        return genre_sidecar.ValidationResult(
            valid=False,
            findings=(
                genre_sidecar.ValidationFinding(
                    "$",
                    "error",
                    "wrong_type",
                    f"expected a JSON object, got {type(data).__name__}",
                ),
            ),
        )
    if "segments" not in data:
        return genre_sidecar.ValidationResult(
            valid=False,
            findings=(
                genre_sidecar.ValidationFinding(
                    "$.segments",
                    "error",
                    "missing_required_field",
                    "missing required field",
                ),
            ),
        )
    segments = data["segments"]
    if not isinstance(segments, list):
        return genre_sidecar.ValidationResult(
            valid=False,
            findings=(
                genre_sidecar.ValidationFinding(
                    "$.segments",
                    "error",
                    "wrong_type",
                    f"expected list, got {type(segments).__name__}",
                ),
            ),
        )
    return genre_sidecar.ValidationResult(valid=True, findings=())


# All 4 currently-produced sidecar kinds (WI-PROMOTE-0097 acceptance).
_REGISTRY: dict[str, ValidatorFn] = {
    discovery.GENRE_SIDECAR_FILENAME: _validate_genre,
    discovery.SCENES_SIDECAR_FILENAME: _validate_scenes,
    LINGUISTICS_SIDECAR_FILENAME: _validate_linguistics,
    LINGUISTICS_TOKEN_DETAIL_FILENAME: _validate_linguistics_token_detail,
}


def _check_no_basename_collisions(registry: dict[str, ValidatorFn]) -> None:
    """Guard the ``--sidecar`` bare-name shortcut: two registered kinds
    must never share a basename under different extensions, or a bare
    ``--sidecar <name>`` (which assumes ``.json``) could silently resolve
    to the wrong registered kind."""
    seen: dict[str, str] = {}
    for filename in registry:
        basename = filename.rsplit(".", 1)[0] if "." in filename else filename
        if basename in seen:
            raise ValueError(
                "sidecar validator registry basename collision: "
                f"{seen[basename]!r} and {filename!r} share basename {basename!r}"
            )
        seen[basename] = filename


_check_no_basename_collisions(_REGISTRY)


def resolve_sidecar_filename(sidecar: str) -> str:
    """Apply the ``--sidecar`` bare-name/extension rule: a value with no
    ``.`` assumes ``.json``; a value containing ``.`` is matched exactly,
    with no inference."""
    if "." in sidecar:
        return sidecar
    return f"{sidecar}.json"


def get_validator(sidecar_filename: str) -> ValidatorFn | None:
    """Return the registered validator for an already-resolved sidecar
    filename, or None if no validator is registered for it."""
    return _REGISTRY.get(sidecar_filename)


def registered_filenames() -> tuple[str, ...]:
    """Return every registered sidecar filename, for tests and reporting."""
    return tuple(_REGISTRY)
