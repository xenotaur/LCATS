"""Date-aware Heinlein record: premises judged against the author's world.

This module implements the contract and the deterministic derivations of
``PROP-LCATS-HEINLEIN-TEMPORAL-REFERENCE``. It makes no model call. A later
stage supplies the model-asserted inputs (premises with standing timelines, a
composition interval, and the ``essential`` and ``causal`` statuses); every
status, relation, flag, profile category and verdict below is derived by
Python from those inputs, so a stored derived value can always be re-derived
and checked.

The five-criterion ``heinlein-five-v1`` record is unchanged and still the
source of ``human``. This contract treats ``human``, ``existing_statuses`` and
the premise anchors as stored inputs and checks only their shape: matching
``human`` to the selected Heinlein analysis, and anchors to the story text,
belong to the stage that produces the record (WI-SF-0127). Rule numbers (R1 to R8) and decision numbers (D1 to D9)
refer to the proposal.

Profile category names (R7). The machine tokens are stored in the record; the
plain names are what reports and documentation show. The table that derives
them is ``profile_category``:

=========================================  ============================================
Token                                      Name (plausibility as written P1, today P3)
=========================================  ============================================
``evergreen``                              evergreen (P1 present, P3 present)
``overtaken``                              overtaken (P1 present, P3 absent)
``plausible_when_written_today_undetermined``
                                           plausible when written, today undetermined
                                           (P1 present, P3 ambiguous or not assessable)
``plausible_only_in_retrospect``           plausible only in retrospect
                                           (P1 absent, P3 present)
``fails_when_written``                     fails when written (P1 absent, P3 not present)
``undetermined``                           undetermined (P1 ambiguous or not assessable)
``not_applicable``                         not applicable (no speculative premises)
=========================================  ============================================
"""

from __future__ import annotations

import calendar
import dataclasses
import re
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

from lcats.analysis.science_fiction import models

TEMPORAL_RUBRIC_VERSION = "heinlein-temporal-v1"

PREMISE_KINDS = frozenset({"ordinary", "counterfactual_divergence"})
STANDINGS = frozenset({"supported", "open", "contested", "contradicted"})
BASES = frozenset({"model_asserted", "table_confirmed", "owner_supplied"})
NOVELTY_VALUES = frozenset({"true", "false", "unknown"})
RELATIONS = frozenset(
    {"stable", "still_open", "realized", "falsified", "not_assessable"}
)
SOURCE_KINDS = frozenset(
    {"owner_supplied", "bibliographic", "author_lifespan", "internal_evidence"}
)
COUNTED_MATERIALITY = frozenset({"central", "substantial"})
# The borrowed ``human`` status adds one value to the decision states: the
# existing record may be missing or failed (R8).
NOT_COMPUTED = "not_computed"
HUMAN_STATUSES = models.DECISION_STATES | {NOT_COMPUTED}

TODAY_REASON_ALL_EXPIRED = "all_counted_expired"

CATEGORY_EVERGREEN = "evergreen"
CATEGORY_OVERTAKEN = "overtaken"
CATEGORY_WHEN_WRITTEN_TODAY_UNDETERMINED = "plausible_when_written_today_undetermined"
CATEGORY_ONLY_IN_RETROSPECT = "plausible_only_in_retrospect"
CATEGORY_FAILS_WHEN_WRITTEN = "fails_when_written"
CATEGORY_UNDETERMINED = "undetermined"
CATEGORY_NOT_APPLICABLE = "not_applicable"
PROFILE_CATEGORIES = frozenset(
    {
        CATEGORY_EVERGREEN,
        CATEGORY_OVERTAKEN,
        CATEGORY_WHEN_WRITTEN_TODAY_UNDETERMINED,
        CATEGORY_ONLY_IN_RETROSPECT,
        CATEGORY_FAILS_WHEN_WRITTEN,
        CATEGORY_UNDETERMINED,
        CATEGORY_NOT_APPLICABLE,
    }
)

_DATE_PATTERN = re.compile(r"(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?", re.ASCII)
_UNSETTLED = frozenset({"open", "contested"})
_NEG_INF = -(10**9)
_POS_INF = 10**9


def _require_non_empty_string(value: Any, field_name: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string")


def _require_choice(value: Any, choices: frozenset[str], field_name: str) -> None:
    if value not in choices:
        raise ValueError(f"{field_name} must be one of {sorted(choices)!r}")


def _require_unique_strings(values: tuple[str, ...], field_name: str) -> None:
    for value in values:
        _require_non_empty_string(value, field_name)
    if len(set(values)) != len(values):
        raise ValueError(f"{field_name} must be unique")


# --- dates --------------------------------------------------------------


def month_range(text: str) -> tuple[int, int]:
    """Return the inclusive month-index range a date covers.

    A bare year covers all twelve of its months (R1); a year and month, or a
    full date, covers its one month. Indexes compare directly, so two
    boundaries are always compared at the finer granularity both give.
    """

    match = _DATE_PATTERN.fullmatch(text) if isinstance(text, str) else None
    if match is None:
        raise ValueError(f"invalid date {text!r}; expected YYYY, YYYY-MM or YYYY-MM-DD")
    year = int(match.group(1))
    month = match.group(2)
    if month is None:
        return year * 12, year * 12 + 11
    if not 1 <= int(month) <= 12:
        raise ValueError(f"invalid month in date {text!r}")
    day = match.group(3)
    if (
        day is not None
        and not 1 <= int(day) <= calendar.monthrange(year, int(month))[1]
    ):
        raise ValueError(f"invalid day in date {text!r}")
    index = year * 12 + int(month) - 1
    return index, index


# --- records ------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class StandingPeriod:
    """One period of a premise's standing timeline (R1)."""

    standing: str
    basis: str = "model_asserted"
    from_date: str | None = None
    to_date: str | None = None
    source: str = ""

    def __post_init__(self) -> None:
        _require_choice(self.standing, STANDINGS, "standing")
        _require_choice(self.basis, BASES, "basis")
        for value in (self.from_date, self.to_date):
            if value is not None:
                month_range(value)
        if self.start > self.end:
            raise ValueError("a standing period must not end before it starts")

    @property
    def start(self) -> int:
        return _NEG_INF if self.from_date is None else month_range(self.from_date)[0]

    @property
    def end(self) -> int:
        return _POS_INF if self.to_date is None else month_range(self.to_date)[1]

    def to_dict(self) -> dict[str, Any]:
        return {
            "from": self.from_date,
            "to": self.to_date,
            "standing": self.standing,
            "basis": self.basis,
            "source": self.source,
        }


def validate_timeline(timeline: tuple[StandingPeriod, ...]) -> None:
    """Require an ordered timeline that covers all time without a gap (R1)."""

    if not timeline:
        raise ValueError("a premise needs at least one standing period")
    if timeline[0].from_date is not None or timeline[-1].to_date is not None:
        raise ValueError("a standing timeline must cover all time (open at both ends)")
    for previous, current in zip(timeline, timeline[1:], strict=False):
        if previous.to_date is None or current.from_date is None:
            raise ValueError(
                "only the first period may be open at the start and the last at the end"
            )
        if current.start < previous.start:
            raise ValueError("standing periods must be ordered by start")
        if current.start > previous.end + 1:
            raise ValueError("standing periods must not leave a gap")


@dataclasses.dataclass(frozen=True)
class DatedPrediction:
    """A claim that a stated date will bring something about (R5)."""

    date: str
    claim: str

    def __post_init__(self) -> None:
        month_range(self.date)
        _require_non_empty_string(self.claim, "claim")

    def to_dict(self) -> dict[str, str]:
        return {"date": self.date, "claim": self.claim}


@dataclasses.dataclass(frozen=True)
class PremiseAnchor:
    """Where in the story a premise is grounded."""

    offset: int
    quote: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.offset, int)
            or isinstance(self.offset, bool)
            or self.offset < 0
        ):
            raise ValueError("anchor offset must be a non-negative integer")
        _require_non_empty_string(self.quote, "quote")

    def to_dict(self) -> dict[str, Any]:
        return {"offset": self.offset, "quote": self.quote}


@dataclasses.dataclass(frozen=True)
class Premise:
    """A material factual premise the story relies on (D2, R1, R4)."""

    premise_id: str
    claim: str
    anchor: PremiseAnchor
    materiality: str
    novel_at_composition: str
    timeline: tuple[StandingPeriod, ...]
    kind: str = "ordinary"
    dated_prediction: DatedPrediction | None = None

    def __post_init__(self) -> None:
        _require_non_empty_string(self.premise_id, "premise_id")
        _require_non_empty_string(self.claim, "claim")
        _require_choice(self.kind, PREMISE_KINDS, "kind")
        _require_choice(self.materiality, models.MATERIALITY_STATES, "materiality")
        _require_choice(
            self.novel_at_composition, NOVELTY_VALUES, "novel_at_composition"
        )
        if (
            self.kind == "counterfactual_divergence"
            and self.novel_at_composition != "true"
        ):
            # A stipulated departure from the author's real history is novel by
            # definition (R4); its timeline describes its enabling mechanism (R1).
            raise ValueError("a counterfactual_divergence premise must be novel")
        validate_timeline(self.timeline)

    @property
    def counted(self) -> bool:
        """Only central and substantial premises count (D2)."""

        return self.materiality in COUNTED_MATERIALITY

    def to_dict(self) -> dict[str, Any]:
        return {
            "premise_id": self.premise_id,
            "kind": self.kind,
            "claim": self.claim,
            "anchor": self.anchor.to_dict(),
            "materiality": self.materiality,
            "novel_at_composition": self.novel_at_composition,
            "dated_prediction": (
                None
                if self.dated_prediction is None
                else self.dated_prediction.to_dict()
            ),
            "timeline": [period.to_dict() for period in self.timeline],
        }


@dataclasses.dataclass(frozen=True)
class CompositionSource:
    """One source of the composition-date interval (D4)."""

    kind: str
    value: str
    basis: str
    hard_bound: bool = False
    confidence: float | None = None

    def __post_init__(self) -> None:
        _require_choice(self.kind, SOURCE_KINDS, "kind")
        _require_non_empty_string(self.value, "value")
        _require_non_empty_string(self.basis, "basis")
        if self.confidence is not None and (
            isinstance(self.confidence, bool)
            or not isinstance(self.confidence, int | float)
            or not 0.0 <= self.confidence <= 1.0
        ):
            raise ValueError("confidence must be a number between 0 and 1")
        if not isinstance(self.hard_bound, bool):
            raise ValueError("hard_bound must be a boolean")

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "value": self.value,
            "hard_bound": self.hard_bound,
            "basis": self.basis,
            "confidence": self.confidence,
        }


@dataclasses.dataclass(frozen=True)
class CompositionInterval:
    """The interval in which the story was composed; unknown ends stay null (D4)."""

    earliest: str | None = None
    latest: str | None = None
    sources: tuple[CompositionSource, ...] = ()
    override: bool = False
    caveats: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for value in (self.earliest, self.latest):
            if value is not None:
                month_range(value)
        if not isinstance(self.override, bool):
            raise ValueError("override must be a boolean")
        if self.start > self.end:
            raise ValueError("the composition interval must not end before it starts")

    @property
    def start(self) -> int:
        return _NEG_INF if self.earliest is None else month_range(self.earliest)[0]

    @property
    def end(self) -> int:
        return _POS_INF if self.latest is None else month_range(self.latest)[1]

    def to_dict(self) -> dict[str, Any]:
        return {
            "earliest": self.earliest,
            "latest": self.latest,
            "sources": [source.to_dict() for source in self.sources],
            "override": self.override,
            "caveats": list(self.caveats),
        }


@dataclasses.dataclass(frozen=True)
class CriterionAssessment:
    """A model-assessed criterion status that cites the premises it rests on (R8, R9)."""

    status: str
    premise_ids: tuple[str, ...] = ()
    rationale: str = ""

    def __post_init__(self) -> None:
        _require_choice(self.status, models.DECISION_STATES, "status")
        _require_unique_strings(self.premise_ids, "premise_ids")
        if self.status == "present" and not self.premise_ids:
            raise ValueError("a present criterion must cite supporting premises")

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "premise_ids": list(self.premise_ids),
            "rationale": self.rationale,
        }


@dataclasses.dataclass(frozen=True)
class BorrowedHuman:
    """The ``human`` status taken from the existing Heinlein record (R8)."""

    status: str = NOT_COMPUTED
    source_heinlein_analysis_id: str | None = None

    def __post_init__(self) -> None:
        _require_choice(self.status, HUMAN_STATUSES, "status")
        if self.status != NOT_COMPUTED:
            _require_non_empty_string(
                self.source_heinlein_analysis_id or "", "source_heinlein_analysis_id"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source_heinlein_analysis_id": self.source_heinlein_analysis_id,
        }


# --- derivations --------------------------------------------------------


def _analysis_month(analysis_date: str) -> int:
    return month_range(analysis_date)[0]


def standings_over(
    timeline: tuple[StandingPeriod, ...], start: int, end: int
) -> tuple[str, ...]:
    """Return the standings of every period that overlaps ``[start, end]``.

    Touching boundaries overlap (R2).
    """

    return tuple(
        period.standing
        for period in timeline
        if period.start <= end and start <= period.end
    )


def status_from_standings(standings: tuple[str, ...]) -> str:
    """R2: ``present`` if all supported or open, ``absent`` if all contradicted.

    Any other mix, including any ``contested`` period, is ``ambiguous``.
    """

    if not standings:
        return "not_assessable"
    if all(standing in {"supported", "open"} for standing in standings):
        return "present"
    if all(standing == "contradicted" for standing in standings):
        return "absent"
    return "ambiguous"


def _composition_window(
    composition: CompositionInterval, analysis_date: str
) -> tuple[int, int]:
    """The composition interval, ending at the analysis date when unbounded (R2)."""

    end = (
        _analysis_month(analysis_date)
        if composition.latest is None
        else composition.end
    )
    return composition.start, end


def _unsettled_beyond_cutoff(
    premise: Premise, analysis_date: str, model_knowledge_cutoff: str | None
) -> bool:
    """True when today's standing lies beyond what the model could know (R2).

    A claim whose latest period is ``open`` or ``contested`` may have been
    settled after the cutoff, so its standing today cannot be stated. A
    settled (``supported`` or ``contradicted``) latest period is treated as
    stable; that is a stated limit of the rule, not a guarantee.
    """

    if model_knowledge_cutoff is None:
        return False
    if _analysis_month(analysis_date) <= month_range(model_knowledge_cutoff)[1]:
        return False
    return premise.timeline[-1].standing in _UNSETTLED


def status_as_written(
    premise: Premise, composition: CompositionInterval, analysis_date: str
) -> str:
    start, end = _composition_window(composition, analysis_date)
    return status_from_standings(standings_over(premise.timeline, start, end))


def status_today(
    premise: Premise, analysis_date: str, model_knowledge_cutoff: str | None
) -> str:
    if _unsettled_beyond_cutoff(premise, analysis_date, model_knowledge_cutoff):
        return "not_assessable"
    month = _analysis_month(analysis_date)
    return status_from_standings(standings_over(premise.timeline, month, month))


def _single_standing(standings: tuple[str, ...]) -> str | None:
    distinct = set(standings)
    return next(iter(distinct)) if len(distinct) == 1 else None


def relation_to_today(
    premise: Premise,
    composition: CompositionInterval,
    analysis_date: str,
    model_knowledge_cutoff: str | None,
) -> str:
    """R3: derive the outcome relation from the two standings, never the model."""

    start, end = _composition_window(composition, analysis_date)
    written = _single_standing(standings_over(premise.timeline, start, end))
    if _unsettled_beyond_cutoff(premise, analysis_date, model_knowledge_cutoff):
        return "not_assessable"
    month = _analysis_month(analysis_date)
    today = _single_standing(standings_over(premise.timeline, month, month))
    if written is None or today is None:
        return "not_assessable"
    pair = (written, today)
    if pair in {("supported", "supported"), ("contradicted", "contradicted")}:
        return "stable"
    if pair == ("open", "open"):
        return "still_open"
    if pair in {("open", "supported"), ("contradicted", "supported")}:
        return "realized"
    if written in {"supported", "open"} and today == "contradicted":
        return "falsified"
    return "not_assessable"


def calendar_expired(premise: Premise, analysis_date: str) -> bool:
    """R5: a dated prediction whose date lies wholly before the analysis month."""

    if premise.dated_prediction is None:
        return False
    return month_range(premise.dated_prediction.date)[1] < _analysis_month(
        analysis_date
    )


def combine_statuses(statuses: tuple[str, ...]) -> str:
    """D5: ``absent`` if any is absent, ``present`` if all are, else ``ambiguous``.

    This mirrors the conjunction in ``models.heinlein_verdict``. An empty set
    is ``present`` vacuously (D7).
    """

    if "absent" in statuses:
        return "absent"
    if all(status == "present" for status in statuses):
        return "present"
    return "ambiguous"


def different_as_written(premises: tuple[Premise, ...]) -> str:
    """R4: ``different`` from the author's real world, never from today's.

    The time of a story's setting is not itself a difference, in either
    direction: only a premise that departs from the author's real world,
    including the author's real past, is novel.
    """

    counted = [premise for premise in premises if premise.counted]
    novelty = [premise.novel_at_composition for premise in counted]
    if "true" in novelty:
        return "present"
    if "unknown" in novelty:
        return "ambiguous"
    return "absent"


def is_speculative(
    premise: Premise, composition: CompositionInterval, analysis_date: str
) -> bool:
    """R6: novel at composition, or not ``supported`` at some date in the interval."""

    if premise.novel_at_composition == "true":
        return True
    start, end = _composition_window(composition, analysis_date)
    return any(
        standing != "supported"
        for standing in standings_over(premise.timeline, start, end)
    )


def speculative_flag(
    premises: tuple[Premise, ...], composition: CompositionInterval, analysis_date: str
) -> dict[str, Any]:
    """R6: ``{has, counted, by_materiality}``, before any calendar-expired exclusion."""

    by_materiality = {"central": 0, "substantial": 0}
    for premise in premises:
        if premise.counted and is_speculative(premise, composition, analysis_date):
            by_materiality[premise.materiality] += 1
    counted = sum(by_materiality.values())
    return {"has": counted > 0, "counted": counted, "by_materiality": by_materiality}


def profile_category(
    plausible_written: str, plausible_today: str, speculative: bool
) -> str:
    """R7: derive the profile category from plausibility as written and today."""

    if not speculative:
        return CATEGORY_NOT_APPLICABLE
    if plausible_written in {"ambiguous", "not_assessable"}:
        return CATEGORY_UNDETERMINED
    if plausible_written == "present":
        if plausible_today == "present":
            return CATEGORY_EVERGREEN
        if plausible_today == "absent":
            return CATEGORY_OVERTAKEN
        return CATEGORY_WHEN_WRITTEN_TODAY_UNDETERMINED
    if plausible_today == "present":
        return CATEGORY_ONLY_IN_RETROSPECT
    return CATEGORY_FAILS_WHEN_WRITTEN


def verdict_as_written(statuses: Mapping[str, str]) -> tuple[str, str, list[list[str]]]:
    """R8: the conjunction over five statuses in the author's frame.

    Returns ``(verdict, consistency, violations)``. A prerequisite violation,
    for example ``essential`` present while ``different`` is absent, reports
    ``inconsistent`` and an ``indeterminate`` verdict instead of forcing one.
    A ``not_computed`` status counts as not assessable.
    """

    normalized = {
        criterion_id: (
            "not_assessable"
            if statuses[criterion_id] == NOT_COMPUTED
            else statuses[criterion_id]
        )
        for criterion_id in models.HEINLEIN_CRITERION_IDS
    }
    violations = models.heinlein_dependency_violations(normalized)
    if violations:
        return "indeterminate", "inconsistent", [list(pair) for pair in violations]
    return models.heinlein_verdict(normalized), "consistent", []


def premise_condition(
    premise: Premise, composition: CompositionInterval, analysis_date: str
) -> str | None:
    """State why an as-written status is ambiguous, from the periods it spans."""

    start, end = _composition_window(composition, analysis_date)
    standings = standings_over(premise.timeline, start, end)
    if status_from_standings(standings) != "ambiguous":
        return None
    spans = [
        f"{period.standing} from {period.from_date or 'the beginning'} "
        f"to {period.to_date or 'now'}"
        for period in premise.timeline
        if period.start <= end and start <= period.end
    ]
    return f"{premise.premise_id}: composition interval spans " + "; ".join(spans)


# --- the analysis record ------------------------------------------------


@dataclasses.dataclass(frozen=True)
class HeinleinTemporalAnalysis:
    """The date-aware Heinlein profile for one story (proposal Record shapes)."""

    analysis_id: str
    story_hash: str
    evidence_set_id: str
    provenance: models.ProvenanceRecord
    analysis_date: str
    premises: tuple[Premise, ...]
    essential: CriterionAssessment
    causal: CriterionAssessment
    human: BorrowedHuman = dataclasses.field(default_factory=BorrowedHuman)
    composition: CompositionInterval = dataclasses.field(
        default_factory=CompositionInterval
    )
    model_knowledge_cutoff: str | None = None
    existing_statuses: Mapping[str, str] = dataclasses.field(default_factory=dict)
    status: str = "complete"
    failures: tuple[models.FailureRecord, ...] = ()

    def __post_init__(self) -> None:
        _require_non_empty_string(self.analysis_id, "analysis_id")
        _require_non_empty_string(self.story_hash, "story_hash")
        _require_non_empty_string(self.evidence_set_id, "evidence_set_id")
        _require_choice(self.status, models.ANALYSIS_STATES, "status")
        if self.provenance.rubric_version != TEMPORAL_RUBRIC_VERSION:
            raise ValueError(
                "Heinlein temporal analysis must use heinlein-temporal-v1 provenance"
            )
        month_range(self.analysis_date)
        if self.model_knowledge_cutoff is not None:
            month_range(self.model_knowledge_cutoff)
        premise_ids = tuple(premise.premise_id for premise in self.premises)
        _require_unique_strings(premise_ids, "premise_id")
        for name, criterion in (("essential", self.essential), ("causal", self.causal)):
            unknown = set(criterion.premise_ids) - set(premise_ids)
            if unknown:
                raise ValueError(f"{name} cites unknown premises: {sorted(unknown)!r}")
        existing = dict(self.existing_statuses)
        for criterion_id, value in existing.items():
            _require_choice(
                criterion_id,
                frozenset(models.HEINLEIN_CRITERION_IDS),
                "existing criterion",
            )
            _require_choice(value, models.DECISION_STATES, "existing status")
        object.__setattr__(self, "existing_statuses", MappingProxyType(existing))

    @property
    def counted_premises(self) -> tuple[Premise, ...]:
        return tuple(premise for premise in self.premises if premise.counted)

    def assessment(self) -> dict[str, Any]:
        """Return the assessment block; every derived value comes from Python."""

        composition = self.composition
        date = self.analysis_date
        cutoff = self.model_knowledge_cutoff
        per_premise = []
        for premise in self.premises:
            expired = calendar_expired(premise, date)
            per_premise.append(
                {
                    "premise_id": premise.premise_id,
                    "status_as_written": status_as_written(premise, composition, date),
                    "status_today": status_today(premise, date, cutoff),
                    "relation": relation_to_today(premise, composition, date, cutoff),
                    "calendar_expired": expired,
                    "condition": premise_condition(premise, composition, date),
                }
            )
        by_id = {item["premise_id"]: item for item in per_premise}
        counted = self.counted_premises
        written = combine_statuses(
            tuple(by_id[p.premise_id]["status_as_written"] for p in counted)
        )
        remaining = [p for p in counted if not by_id[p.premise_id]["calendar_expired"]]
        today_reason: str | None = None
        if counted and not remaining:
            plausible_today = "not_assessable"
            today_reason = TODAY_REASON_ALL_EXPIRED
        else:
            plausible_today = combine_statuses(
                tuple(by_id[p.premise_id]["status_today"] for p in remaining)
            )
        speculative = speculative_flag(self.premises, composition, date)
        different = different_as_written(self.premises)
        statuses = {
            "different": different,
            "essential": self.essential.status,
            "human": self.human.status,
            "causal": self.causal.status,
            "plausible": written,
        }
        verdict, consistency, violations = verdict_as_written(statuses)
        conditions = [item["condition"] for item in per_premise if item["condition"]]
        return {
            "plausible_as_written": written,
            "plausible_today": plausible_today,
            "different_as_written": different,
            "condition": "; ".join(conditions) if conditions else None,
            "per_premise": per_premise,
            "essential_as_written": self.essential.to_dict(),
            "causal_as_written": self.causal.to_dict(),
            "human": self.human.to_dict(),
            "comparison_with_existing": self._comparison(statuses),
            "today_reason": today_reason,
            "speculative_premises": speculative,
            "category": profile_category(written, plausible_today, speculative["has"]),
            "verdict_as_written": verdict,
            "consistency": {"status": consistency, "violations": violations},
        }

    def _comparison(self, statuses: Mapping[str, str]) -> list[dict[str, str]]:
        """Where this record's five statuses differ from the existing record's."""

        return [
            {
                "criterion_id": criterion_id,
                "temporal": statuses[criterion_id],
                "existing": self.existing_statuses[criterion_id],
            }
            for criterion_id in models.HEINLEIN_CRITERION_IDS
            if criterion_id in self.existing_statuses
            and self.existing_statuses[criterion_id] != statuses[criterion_id]
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "analysis_id": self.analysis_id,
            "story_hash": self.story_hash,
            "evidence_set_id": self.evidence_set_id,
            "provenance": self.provenance.to_dict(),
            "status": self.status,
            "failures": [failure.to_dict() for failure in self.failures],
            "analysis_date": self.analysis_date,
            "model_knowledge_cutoff": self.model_knowledge_cutoff,
            "composition": self.composition.to_dict(),
            "premises": [premise.to_dict() for premise in self.premises],
            "existing_statuses": dict(self.existing_statuses),
            "assessment": self.assessment(),
        }


# --- parsing ------------------------------------------------------------


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    return value


def _sequence(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")
    return value


def _unexpected(data: Mapping[str, Any], allowed: set[str], name: str) -> None:
    extra = set(data) - allowed
    if extra:
        raise ValueError(f"{name} has unexpected keys: {sorted(extra)!r}")


def _period_from_dict(data: Any) -> StandingPeriod:
    data = _mapping(data, "standing period")
    _unexpected(data, {"from", "to", "standing", "basis", "source"}, "standing period")
    return StandingPeriod(
        standing=data.get("standing"),
        basis=data.get("basis", "model_asserted"),
        from_date=data.get("from"),
        to_date=data.get("to"),
        source=data.get("source", ""),
    )


def _premise_from_dict(data: Any) -> Premise:
    data = _mapping(data, "premise")
    _unexpected(
        data,
        {
            "premise_id",
            "kind",
            "claim",
            "anchor",
            "materiality",
            "novel_at_composition",
            "dated_prediction",
            "timeline",
        },
        "premise",
    )
    anchor = _mapping(data.get("anchor"), "anchor")
    prediction = data.get("dated_prediction")
    return Premise(
        premise_id=data.get("premise_id"),
        kind=data.get("kind", "ordinary"),
        claim=data.get("claim"),
        anchor=PremiseAnchor(offset=anchor.get("offset"), quote=anchor.get("quote")),
        materiality=data.get("materiality"),
        novel_at_composition=data.get("novel_at_composition"),
        dated_prediction=(
            None
            if prediction is None
            else DatedPrediction(
                date=_mapping(prediction, "dated_prediction").get("date"),
                claim=prediction.get("claim"),
            )
        ),
        timeline=tuple(
            _period_from_dict(item)
            for item in _sequence(data.get("timeline"), "timeline")
        ),
    )


def _composition_from_dict(data: Any) -> CompositionInterval:
    data = _mapping(data, "composition")
    _unexpected(
        data, {"earliest", "latest", "sources", "override", "caveats"}, "composition"
    )
    sources = []
    for item in _sequence(data.get("sources", []), "sources"):
        item = _mapping(item, "composition source")
        sources.append(
            CompositionSource(
                kind=item.get("kind"),
                value=item.get("value"),
                basis=item.get("basis"),
                hard_bound=item.get("hard_bound", False),
                confidence=item.get("confidence"),
            )
        )
    return CompositionInterval(
        earliest=data.get("earliest"),
        latest=data.get("latest"),
        sources=tuple(sources),
        override=data.get("override", False),
        caveats=tuple(_sequence(data.get("caveats", []), "caveats")),
    )


def analysis_from_dict(data: Mapping[str, Any]) -> HeinleinTemporalAnalysis:
    """Rebuild an analysis from its serialized form, validating every input.

    Only the model-asserted inputs are read; the derived ``assessment`` values
    are recomputed, so a caller can compare them with the stored ones.
    """

    data = _mapping(data, "analysis")
    _unexpected(
        data,
        {
            "analysis_id",
            "story_hash",
            "evidence_set_id",
            "provenance",
            "status",
            "failures",
            "analysis_date",
            "model_knowledge_cutoff",
            "composition",
            "premises",
            "existing_statuses",
            "assessment",
        },
        "analysis",
    )
    assessment = _mapping(data.get("assessment"), "assessment")
    essential = _mapping(assessment.get("essential_as_written"), "essential_as_written")
    causal = _mapping(assessment.get("causal_as_written"), "causal_as_written")
    human = _mapping(assessment.get("human"), "human")
    try:
        provenance = models.ProvenanceRecord(
            **dict(_mapping(data.get("provenance"), "provenance"))
        )
        failures = tuple(
            models.FailureRecord(**dict(_mapping(item, "failure")))
            for item in _sequence(data.get("failures", []), "failures")
        )
    except TypeError as error:
        raise ValueError(str(error)) from error
    return HeinleinTemporalAnalysis(
        analysis_id=data.get("analysis_id"),
        story_hash=data.get("story_hash"),
        evidence_set_id=data.get("evidence_set_id"),
        provenance=provenance,
        analysis_date=data.get("analysis_date"),
        model_knowledge_cutoff=data.get("model_knowledge_cutoff"),
        composition=_composition_from_dict(data.get("composition")),
        premises=tuple(
            _premise_from_dict(item)
            for item in _sequence(data.get("premises"), "premises")
        ),
        essential=CriterionAssessment(
            status=essential.get("status"),
            premise_ids=tuple(
                _sequence(essential.get("premise_ids", []), "premise_ids")
            ),
            rationale=essential.get("rationale", ""),
        ),
        causal=CriterionAssessment(
            status=causal.get("status"),
            premise_ids=tuple(_sequence(causal.get("premise_ids", []), "premise_ids")),
            rationale=causal.get("rationale", ""),
        ),
        human=BorrowedHuman(
            status=human.get("status"),
            source_heinlein_analysis_id=human.get("source_heinlein_analysis_id"),
        ),
        existing_statuses=_mapping(
            data.get("existing_statuses", {}), "existing_statuses"
        ),
        status=data.get("status"),
        failures=failures,
    )
