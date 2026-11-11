"""Composition-date sources for the date-aware Heinlein record.

``PROP-LCATS-HEINLEIN-TEMPORAL-REFERENCE`` (D4) builds a story's composition
interval from sources, strongest first: an owner-supplied date, a bibliographic
first-publication record, the author's lifespan, and internal evidence. This
module loads the owner-supplied dates from a reviewable file and intersects the
sources into a ``heinlein_temporal.CompositionInterval``. It is pure: it never
reads the network, and no source is queried by the pipeline (WI-SF-0128).

What each source bounds:

* **Owner-supplied** earliest and latest dates replace the computed result
  entirely and are recorded as an override. Nothing outranks them.
* **Bibliographic first publication** is an UPPER bound only. A story's first
  publication is the latest it can have been composed, never the earliest.
* **Author lifespan**: birth is the lower bound and death is a hard upper bound
  (``hard_bound``). Career milestones (adulthood, the author's debut) are
  context, not bounds, and are deliberately not accepted here: a debut may have
  been written years before it was published, or while the author was a minor.
* **Internal evidence** the model can see gives a lower and/or upper bound.

The sources are intersected in that order. A source that would empty the
interval (it contradicts the stronger sources before it) is not applied and is
named in a caveat; the module never picks a side silently and never guesses. A
story with no usable source gets an unbounded interval and a caveat saying so.
Every applied source is recorded with its kind, value, basis and confidence,
including a source that is consistent with the others but does not narrow the
interval (it is evidence that agreed, not a bound that was used).

Comparisons are at MONTH granularity, like ``heinlein_temporal.month_range``: a
bare year covers its twelve months and a day inside a month is treated as that
whole month, so two day-level dates in one month never conflict with each other.

Owner-supplied file format (``lcats-composition-dates-v1``), JSON so it is easy
to review in a diff. The record below is an ILLUSTRATION of the format, not a
real owner decision::

    {
      "version": "lcats-composition-dates-v1",
      "stories": {
        "mass_quantities/a_case_of_sunburn__fontenay": {
          "earliest": "1956",
          "latest": "1957-04",
          "basis": "Illustration only: cite what the owner checked",
          "caveats": ["Illustration only: add a caveat if one applies"]
        }
      }
    }

Dates are ``YYYY``, ``YYYY-MM`` or ``YYYY-MM-DD``. Unknown keys, a duplicate
story ID, a missing basis, and an entry with neither date are rejected.
"""

from __future__ import annotations

import dataclasses
import json
import pathlib
from collections.abc import Mapping
from typing import Any

from lcats.analysis.science_fiction import heinlein_temporal

OWNER_DATES_VERSION = "lcats-composition-dates-v1"

UNBOUNDED_CAVEAT = "no composition date source was available; the interval is unbounded"


def _non_empty(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _optional_date(value: Any, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a date string or null")
    heinlein_temporal.month_range(value)
    return value


def _caveats(value: Any, name: str) -> tuple[str, ...]:
    if not isinstance(value, list | tuple) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise ValueError(f"{name} must be a list of non-empty strings")
    return tuple(value)


def _confidence(value: Any) -> float | None:
    if value is None:
        return None
    if (
        isinstance(value, bool)
        or not isinstance(value, int | float)
        or not 0.0 <= value <= 1.0
    ):
        raise ValueError("confidence must be a number between 0 and 1")
    return float(value)


# --- source records ------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class OwnerDates:
    """Owner-supplied composition dates; they override every other source."""

    story_id: str
    earliest: str | None
    latest: str | None
    basis: str
    caveats: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _non_empty(self.story_id, "story_id")
        _non_empty(self.basis, "basis")
        _optional_date(self.earliest, "earliest")
        _optional_date(self.latest, "latest")
        object.__setattr__(self, "caveats", _caveats(self.caveats, "caveats"))
        if self.earliest is None and self.latest is None:
            raise ValueError("owner dates need an earliest or a latest date")
        # Reject an inverted range now rather than when the interval is built.
        heinlein_temporal.CompositionInterval(
            earliest=self.earliest, latest=self.latest
        )


@dataclasses.dataclass(frozen=True)
class BibliographicRecord:
    """A first-publication record: an upper bound on composition, never a lower."""

    first_publication: str
    basis: str
    confidence: float | None = None
    caveats: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _optional_date(_non_empty(self.first_publication, "first_publication"), "date")
        _non_empty(self.basis, "basis")
        _confidence(self.confidence)
        _caveats(self.caveats, "caveats")


@dataclasses.dataclass(frozen=True)
class AuthorLifespan:
    """Birth (lower bound) and death (hard upper bound); either may be unknown."""

    born: str | None
    died: str | None
    basis: str
    confidence: float | None = None
    caveats: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _optional_date(self.born, "born")
        _optional_date(self.died, "died")
        _non_empty(self.basis, "basis")
        _confidence(self.confidence)
        _caveats(self.caveats, "caveats")
        if self.born is None and self.died is None:
            raise ValueError("a lifespan needs a birth or a death date")
        heinlein_temporal.CompositionInterval(earliest=self.born, latest=self.died)


@dataclasses.dataclass(frozen=True)
class InternalEvidence:
    """A lower and/or upper bound read from the story's own text."""

    earliest: str | None
    latest: str | None
    basis: str
    confidence: float | None = None
    caveats: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _optional_date(self.earliest, "earliest")
        _optional_date(self.latest, "latest")
        _non_empty(self.basis, "basis")
        _confidence(self.confidence)
        _caveats(self.caveats, "caveats")
        if self.earliest is None and self.latest is None:
            raise ValueError("internal evidence needs an earliest or a latest date")
        heinlein_temporal.CompositionInterval(
            earliest=self.earliest, latest=self.latest
        )


# --- owner-supplied file -------------------------------------------------

_OWNER_FILE_KEYS = {"version", "stories"}
_OWNER_ENTRY_KEYS = {"earliest", "latest", "basis", "caveats"}


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key {key!r} in owner dates file")
        result[key] = value
    return result


def owner_dates_from_dict(data: Any) -> dict[str, OwnerDates]:
    """Validate a parsed owner-dates file; unknown keys are rejected."""

    if not isinstance(data, Mapping):
        raise ValueError("owner dates file must be a JSON object")
    extra = set(data) - _OWNER_FILE_KEYS
    if extra:
        raise ValueError(f"owner dates file has unexpected keys: {sorted(extra)!r}")
    if data.get("version") != OWNER_DATES_VERSION:
        raise ValueError(f"owner dates file version must be {OWNER_DATES_VERSION!r}")
    stories = data.get("stories")
    if not isinstance(stories, Mapping):
        raise ValueError("owner dates file needs a 'stories' object")
    result: dict[str, OwnerDates] = {}
    for story_id, entry in stories.items():
        if not isinstance(entry, Mapping):
            raise ValueError(f"owner dates for {story_id!r} must be an object")
        extra = set(entry) - _OWNER_ENTRY_KEYS
        if extra:
            raise ValueError(
                f"owner dates for {story_id!r} have unexpected keys: {sorted(extra)!r}"
            )
        missing = {"basis"} - set(entry)
        if missing:
            raise ValueError(f"owner dates for {story_id!r} are missing a basis")
        result[story_id] = OwnerDates(
            story_id=story_id,
            earliest=entry.get("earliest"),
            latest=entry.get("latest"),
            basis=entry["basis"],
            caveats=_caveats(entry.get("caveats", []), "caveats"),
        )
    return result


def load_owner_dates(path: pathlib.Path | str) -> dict[str, OwnerDates]:
    """Read a reviewable owner-dates file; a duplicate story ID is an error."""

    text = pathlib.Path(path).read_text(encoding="utf-8")
    return owner_dates_from_dict(json.loads(text, object_pairs_hook=_no_duplicates))


# --- interval construction -----------------------------------------------


@dataclasses.dataclass(frozen=True)
class _Bounds:
    """One source's contribution: a lower and/or upper bound, in month terms."""

    source: heinlein_temporal.CompositionSource
    lower: str | None
    upper: str | None
    caveats: tuple[str, ...]


def _lower_month(date: str | None) -> int | None:
    return None if date is None else heinlein_temporal.month_range(date)[0]


def _upper_month(date: str | None) -> int | None:
    return None if date is None else heinlein_temporal.month_range(date)[1]


def _bounds_in_order(
    bibliographic: BibliographicRecord | None,
    lifespan: AuthorLifespan | None,
    internal: InternalEvidence | None,
) -> list[_Bounds]:
    ordered: list[_Bounds] = []
    if bibliographic is not None:
        ordered.append(
            _Bounds(
                source=heinlein_temporal.CompositionSource(
                    kind="bibliographic",
                    value=f"first published {bibliographic.first_publication}",
                    basis=bibliographic.basis,
                    confidence=_confidence(bibliographic.confidence),
                ),
                lower=None,
                upper=bibliographic.first_publication,
                caveats=bibliographic.caveats,
            )
        )
    if lifespan is not None:
        parts = []
        if lifespan.born is not None:
            parts.append(f"born {lifespan.born}")
        if lifespan.died is not None:
            parts.append(f"died {lifespan.died}")
        ordered.append(
            _Bounds(
                source=heinlein_temporal.CompositionSource(
                    kind="author_lifespan",
                    value="; ".join(parts),
                    basis=lifespan.basis,
                    hard_bound=lifespan.died is not None,
                    confidence=_confidence(lifespan.confidence),
                ),
                lower=lifespan.born,
                upper=lifespan.died,
                caveats=lifespan.caveats,
            )
        )
    if internal is not None:
        ordered.append(
            _Bounds(
                source=heinlein_temporal.CompositionSource(
                    kind="internal_evidence",
                    value=f"{internal.earliest or 'unknown'} to "
                    f"{internal.latest or 'unknown'}",
                    basis=internal.basis,
                    confidence=_confidence(internal.confidence),
                ),
                lower=internal.earliest,
                upper=internal.latest,
                caveats=internal.caveats,
            )
        )
    return ordered


def _computed_interval(
    bibliographic: BibliographicRecord | None,
    lifespan: AuthorLifespan | None,
    internal: InternalEvidence | None,
) -> heinlein_temporal.CompositionInterval:
    lower: str | None = None
    upper: str | None = None
    sources: list[heinlein_temporal.CompositionSource] = []
    caveats: list[str] = []
    for bounds in _bounds_in_order(bibliographic, lifespan, internal):
        new_lower, new_upper = lower, upper
        if bounds.lower is not None and (
            lower is None or _lower_month(bounds.lower) > _lower_month(lower)
        ):
            new_lower = bounds.lower
        if bounds.upper is not None and (
            upper is None or _upper_month(bounds.upper) < _upper_month(upper)
        ):
            new_upper = bounds.upper
        if (
            new_lower is not None
            and new_upper is not None
            and _lower_month(new_lower) > _upper_month(new_upper)
        ):
            caveats.append(
                f"{bounds.source.kind} ({bounds.source.value}) conflicts with the "
                "stronger sources and was not applied"
            )
            continue
        lower, upper = new_lower, new_upper
        sources.append(bounds.source)
        caveats.extend(bounds.caveats)
    if not sources:
        caveats.insert(0, UNBOUNDED_CAVEAT)
    return heinlein_temporal.CompositionInterval(
        earliest=lower,
        latest=upper,
        sources=tuple(sources),
        override=False,
        caveats=tuple(caveats),
    )


def _describe(interval: heinlein_temporal.CompositionInterval) -> str:
    return f"{interval.earliest or 'unknown'} to {interval.latest or 'unknown'}"


def build_interval(
    *,
    owner: OwnerDates | None = None,
    bibliographic: BibliographicRecord | None = None,
    lifespan: AuthorLifespan | None = None,
    internal: InternalEvidence | None = None,
) -> heinlein_temporal.CompositionInterval:
    """Build the composition interval from the sources, strongest first (D4).

    Owner-supplied dates replace the computed result and are recorded as an
    override; when other sources were also given, the caveats say which computed
    interval was replaced. Otherwise the supplied sources are intersected, and
    with no usable source the interval is unbounded, never guessed.
    """

    computed = _computed_interval(bibliographic, lifespan, internal)
    if owner is None:
        return computed
    caveats = list(owner.caveats)
    if computed.sources:
        caveats.append(f"overrides the computed interval {_describe(computed)}")
    return heinlein_temporal.CompositionInterval(
        earliest=owner.earliest,
        latest=owner.latest,
        sources=(
            heinlein_temporal.CompositionSource(
                kind="owner_supplied",
                value=f"{owner.earliest or 'unknown'} to {owner.latest or 'unknown'}",
                basis=owner.basis,
            ),
        ),
        override=True,
        caveats=tuple(caveats),
    )
