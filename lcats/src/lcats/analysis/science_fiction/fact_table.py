"""A curated table of facts whose standing changed, and an audit against it.

The opt-in date-aware Heinlein stage (WI-SF-0127) asks a model to say when a
fact became established or was contradicted, and records every such date as
``model_asserted``. A model can recall a date wrongly, which would make a
reading look surer than it is. This module is the audit layer
``PROP-LCATS-HEINLEIN-TEMPORAL-REFERENCE`` R10 describes: a small curated table
of known cases, and a matcher that compares a premise's timeline with it.

What the audit does and does not do:

* It **reports**. A premise whose claim matches exactly one table entry and
  whose timeline agrees is marked ``table_confirmed`` (the periods since the
  change only; an earlier period keeps its ``model_asserted`` basis);
  a premise that matches and disagrees gets a ``disagreement`` audit with the
  reasons; a claim that matches several entries gets ``ambiguous_match`` and is
  left alone; a premise with no timeline gets ``not_comparable``; a claim that
  matches nothing is untouched and gets no audit at all.
* It **never changes a derived status.** A basis label is not an input to any
  derivation in ``heinlein_temporal``, and the model's timeline is never
  rewritten. A disagreement is a flag for a human, not a correction.
* It enforces only what an opened source supports: the standing the fact ends
  in, and the boundary at which it changed. The earlier standing is recorded for
  context (``before_standing``) and flagged unconfirmed unless an opened source
  states it; the matcher does not enforce it.

Matching a free-text claim to an entry is fuzzy, so it is deliberately strict.
The stage does not supply a stable claim identifier, so each entry names TERM
GROUPS: a claim matches only if every group has at least one term present as a
whole word (case-insensitive, an optional plural ``s``/``es``). There is no
similarity score. A false match could mark a wrong claim ``table_confirmed``,
so keep groups tight, and note that the match method is recorded in every
audit so a later stage-supplied fact identifier can replace it.

Known limits of the term matcher (it is an audit aid, not a reader):

* **Negation.** A claim containing a negator (``not``, ``no``, ``never``,
  ``without``, ``cannot``, ``n't``, ``neither``, ``nor``) is never matched, so
  "Mars does not have a thick atmosphere" is simply not audited. This avoids
  both a false disagreement and a false confirmation. Typographic apostrophes
  (for example ``doesn’t``) are normalised first, so they count too.
* **Counterfactual premises.** A ``counterfactual_divergence`` premise's
  timeline describes the standing of its enabling mechanism, not the historical
  claim (R1), so a match is reported ``not_comparable`` and never compared.
* **Co-occurrence only.** The groups test that words appear together, not that
  they are in the same clause: "Mars air, thick with dust" matches, and so does
  a sentence that names an unrelated body beside the right terms.
* **Word senses.** "Mercury" the metal and "mercury" the planet are not
  distinguished except by the other groups, so keep every entry's last group
  specific.
* **Boundaries.** ``change_at`` is the date of the first measurement the cited
  sources report, not necessarily the first time anyone doubted the fact; a
  model that dates the doubt earlier is reported as a disagreement for a human
  to judge, never corrected.

Adding an entry (``facts/heinlein_fact_table.json``, version
``lcats-heinlein-fact-table-v1``):

1. Open and read a source. Add it to ``sources`` with an ``id``, ``title``,
   ``url``, the ``retrieved`` date, ``opened: true`` and a short ``evidence``
   paraphrase of what the page said. A source you did not open is recorded with
   ``opened: false`` and is not counted toward an entry; never cite one as
   evidence.
2. Add a ``facts`` entry: ``fact_id`` (unique), ``claim``, ``match`` (term
   groups, every group must hit), ``change_at`` (a year or year-month),
   ``final_standing`` (``supported``, ``open``, ``contested`` or
   ``contradicted``), ``before_standing`` with ``before_confirmed`` and a
   ``before_note``, ``source_ids`` (at least one opened source) and a ``note``
   on any inference the sources do not state outright.
3. Add a test in ``fact_table_test.py`` for the new entry's agreement and
   disagreement, and run the loader test, which validates the shipped table.
"""

from __future__ import annotations

import dataclasses
import functools
import json
import pathlib
import re
from collections.abc import Mapping
from typing import Any

from lcats.analysis.science_fiction import heinlein_temporal

TABLE_VERSION = "lcats-heinlein-fact-table-v1"
MATCH_METHOD = "terms"
DEFAULT_TABLE_PATH = (
    pathlib.Path(__file__).parent / "facts" / "heinlein_fact_table.json"
)


def _non_empty(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _unexpected(data: Mapping[str, Any], allowed: set[str], name: str) -> None:
    extra = set(data) - allowed
    if extra:
        raise ValueError(f"{name} has unexpected keys: {sorted(extra)!r}")


def _require_keys(data: Mapping[str, Any], keys: set[str], name: str) -> None:
    missing = keys - set(data)
    if missing:
        raise ValueError(f"{name} is missing keys: {sorted(missing)!r}")


@dataclasses.dataclass(frozen=True)
class FactSource:
    """A source the table cites; only an opened one counts as evidence."""

    source_id: str
    title: str
    url: str
    retrieved: str
    opened: bool
    evidence: str

    def __post_init__(self) -> None:
        _non_empty(self.source_id, "source id")
        _non_empty(self.title, "source title")
        _non_empty(self.url, "source url")
        _non_empty(self.retrieved, "source retrieved date")
        _non_empty(self.evidence, "source evidence")
        if not isinstance(self.opened, bool):
            raise ValueError("source opened must be a boolean")


@dataclasses.dataclass(frozen=True)
class FactEntry:
    """One known case of a fact whose standing changed."""

    fact_id: str
    claim: str
    match: tuple[tuple[str, ...], ...]
    change_at: str
    final_standing: str
    before_standing: str
    before_confirmed: bool
    before_note: str
    source_ids: tuple[str, ...]
    note: str

    def __post_init__(self) -> None:
        _non_empty(self.fact_id, "fact_id")
        _non_empty(self.claim, "claim")
        _non_empty(self.before_note, "before_note")
        _non_empty(self.note, "note")
        heinlein_temporal.month_range(self.change_at)
        for name, value in (
            ("final_standing", self.final_standing),
            ("before_standing", self.before_standing),
        ):
            if value not in heinlein_temporal.STANDINGS:
                raise ValueError(f"{name} {value!r} is not a standing")
        if not isinstance(self.before_confirmed, bool):
            raise ValueError("before_confirmed must be a boolean")
        if not self.match or not all(group for group in self.match):
            raise ValueError("match needs at least one non-empty term group")
        for group in self.match:
            for term in group:
                _non_empty(term, "match term")
                if term != term.lower():
                    raise ValueError(f"match term {term!r} must be lowercase")
        if not self.source_ids:
            raise ValueError("an entry needs at least one source id")


@dataclasses.dataclass(frozen=True)
class FactTable:
    """The validated table: every entry cites a source that was opened."""

    sources: tuple[FactSource, ...]
    facts: tuple[FactEntry, ...]

    def __post_init__(self) -> None:
        by_id = {source.source_id: source for source in self.sources}
        if len(by_id) != len(self.sources):
            raise ValueError("duplicate source id")
        fact_ids = [fact.fact_id for fact in self.facts]
        if len(set(fact_ids)) != len(fact_ids):
            raise ValueError("duplicate fact_id")
        for fact in self.facts:
            unknown = set(fact.source_ids) - set(by_id)
            if unknown:
                raise ValueError(
                    f"{fact.fact_id} cites unknown sources: {sorted(unknown)!r}"
                )
            if not any(by_id[source_id].opened for source_id in fact.source_ids):
                raise ValueError(
                    f"{fact.fact_id} has no source that was opened and read"
                )

    def source(self, source_id: str) -> FactSource:
        return next(item for item in self.sources if item.source_id == source_id)


# --- loading -------------------------------------------------------------

_TABLE_KEYS = {"version", "note", "sources", "facts"}
_SOURCE_KEYS = {"id", "title", "url", "retrieved", "opened", "evidence"}
_FACT_KEYS = {
    "fact_id",
    "claim",
    "match",
    "change_at",
    "final_standing",
    "before_standing",
    "before_confirmed",
    "before_note",
    "source_ids",
    "note",
}


def _list(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")
    return value


def table_from_dict(data: Any) -> FactTable:
    """Validate a parsed table; unknown or missing keys are rejected."""

    if not isinstance(data, Mapping):
        raise ValueError("fact table must be a JSON object")
    _unexpected(data, _TABLE_KEYS, "fact table")
    if data.get("version") != TABLE_VERSION:
        raise ValueError(f"fact table version must be {TABLE_VERSION!r}")
    sources = []
    for item in _list(data.get("sources"), "sources"):
        if not isinstance(item, Mapping):
            raise ValueError("a source must be an object")
        _unexpected(item, _SOURCE_KEYS, "source")
        _require_keys(item, _SOURCE_KEYS, "source")
        sources.append(
            FactSource(
                source_id=item["id"],
                title=item["title"],
                url=item["url"],
                retrieved=item["retrieved"],
                opened=item["opened"],
                evidence=item["evidence"],
            )
        )
    facts = []
    for item in _list(data.get("facts"), "facts"):
        if not isinstance(item, Mapping):
            raise ValueError("a fact must be an object")
        _unexpected(item, _FACT_KEYS, "fact")
        _require_keys(item, _FACT_KEYS, "fact")
        groups = tuple(
            tuple(_list(group, "match group"))
            for group in _list(item["match"], "match")
        )
        facts.append(
            FactEntry(
                fact_id=item["fact_id"],
                claim=item["claim"],
                match=groups,
                change_at=item["change_at"],
                final_standing=item["final_standing"],
                before_standing=item["before_standing"],
                before_confirmed=item["before_confirmed"],
                before_note=item["before_note"],
                source_ids=tuple(_list(item["source_ids"], "source_ids")),
                note=item["note"],
            )
        )
    return FactTable(sources=tuple(sources), facts=tuple(facts))


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key {key!r} in fact table")
        result[key] = value
    return result


def load_table(path: pathlib.Path | str) -> FactTable:
    """Read and validate a fact table file."""

    text = pathlib.Path(path).read_text(encoding="utf-8")
    return table_from_dict(json.loads(text, object_pairs_hook=_no_duplicates))


@functools.lru_cache(maxsize=1)
def default_table() -> FactTable:
    """The table shipped with the package."""

    return load_table(DEFAULT_TABLE_PATH)


# --- matching ------------------------------------------------------------


def _term_pattern(term: str) -> re.Pattern[str]:
    words = r"\s+".join(re.escape(word) for word in term.split())
    return re.compile(rf"(?<![\w-]){words}(?:s|es)?(?![\w-])", re.IGNORECASE)


# Typographic apostrophes and quotes a model may emit in place of ``'``.
_APOSTROPHES = str.maketrans(
    {
        "\u2019": "'",
        "\u2018": "'",
        "\u02bc": "'",
        "\u2032": "'",
        "\uff07": "'",
        "\u00b4": "'",
        "`": "'",
    }
)

_NEGATION = re.compile(
    r"(?<![\w-])(?:not|no|never|without|cannot|neither|nor)(?![\w-])|n't\b",
    re.IGNORECASE,
)


def claim_matches(claim: str, entry: FactEntry) -> bool:
    """True when every term group has a term and the claim is not negated."""

    claim = claim.translate(_APOSTROPHES)
    if _NEGATION.search(claim):
        return False
    return all(
        any(_term_pattern(term).search(claim) for term in group)
        for group in entry.match
    )


def _months_overlap(first: str, second: str) -> bool:
    a_start, a_end = heinlein_temporal.month_range(first)
    b_start, b_end = heinlein_temporal.month_range(second)
    return a_start <= b_end and b_start <= a_end


def _final_run_start(timeline: tuple[heinlein_temporal.StandingPeriod, ...]) -> int:
    """Index of the first period of the trailing run of equal standings.

    Two adjacent periods with the same standing are one standing for audit
    purposes, so a fact contradicted in two consecutive periods changed once,
    when the first of them began.
    """

    index = len(timeline) - 1
    while index > 0 and timeline[index - 1].standing == timeline[index].standing:
        index -= 1
    return index


def _opened_source_ids(entry: FactEntry, table: FactTable) -> tuple[str, ...]:
    """Only a source that was opened and read is offered as evidence."""

    return tuple(
        source_id for source_id in entry.source_ids if table.source(source_id).opened
    )


def audit_premise(
    premise: heinlein_temporal.Premise, table: FactTable | None = None
) -> heinlein_temporal.FactAudit | None:
    """Audit one premise against the table; ``None`` when nothing matches."""

    table = table or default_table()
    matches = [entry for entry in table.facts if claim_matches(premise.claim, entry)]
    if not matches:
        return None
    if len(matches) > 1:
        return heinlein_temporal.FactAudit(
            premise_id=premise.premise_id,
            outcome="ambiguous_match",
            method=MATCH_METHOD,
            reasons=(
                "the claim matches several table entries: "
                + ", ".join(entry.fact_id for entry in matches),
            ),
        )
    entry = matches[0]
    if not premise.timeline:
        return heinlein_temporal.FactAudit(
            premise_id=premise.premise_id,
            outcome="not_comparable",
            method=MATCH_METHOD,
            fact_id=entry.fact_id,
            reasons=("the premise has no timeline to compare",),
        )
    if premise.kind == "counterfactual_divergence":
        return heinlein_temporal.FactAudit(
            premise_id=premise.premise_id,
            outcome="not_comparable",
            method=MATCH_METHOD,
            fact_id=entry.fact_id,
            reasons=(
                "a counterfactual_divergence timeline describes its enabling "
                "mechanism, not the historical claim, so it is not compared",
            ),
        )
    last = premise.timeline[-1]
    run_start = _final_run_start(premise.timeline)
    reasons: list[str] = []
    if last.standing != entry.final_standing:
        reasons.append(
            f"the table records {entry.fact_id} as {entry.final_standing} after "
            f"{entry.change_at}; the premise ends {last.standing}"
        )
    if run_start == 0:
        reasons.append(
            f"the premise records no change; the table records a change at "
            f"{entry.change_at}"
        )
    else:
        boundary = premise.timeline[run_start].from_date
        if boundary is not None and not _months_overlap(boundary, entry.change_at):
            reasons.append(
                f"the premise changes to {last.standing} at {boundary}; the table "
                f"records {entry.change_at} (the date of the first measurement "
                "its sources report)"
            )
    if reasons:
        return heinlein_temporal.FactAudit(
            premise_id=premise.premise_id,
            outcome="disagreement",
            method=MATCH_METHOD,
            fact_id=entry.fact_id,
            reasons=tuple(reasons),
        )
    return heinlein_temporal.FactAudit(
        premise_id=premise.premise_id,
        outcome="table_confirmed",
        method=MATCH_METHOD,
        fact_id=entry.fact_id,
        reasons=(
            f"agrees with {entry.fact_id}: {entry.final_standing} from "
            f"{entry.change_at} (opened sources: "
            f"{', '.join(_opened_source_ids(entry, table))})",
        ),
    )


def _mark_since_change(
    premise: heinlein_temporal.Premise,
) -> heinlein_temporal.Premise:
    """Label the periods since the change ``table_confirmed``; keep the timeline."""

    start = _final_run_start(premise.timeline)
    marked = tuple(
        dataclasses.replace(period, basis="table_confirmed")
        for period in premise.timeline[start:]
    )
    return dataclasses.replace(premise, timeline=premise.timeline[:start] + marked)


def apply_to_analysis(
    analysis: heinlein_temporal.HeinleinTemporalAnalysis,
    table: FactTable | None = None,
) -> heinlein_temporal.HeinleinTemporalAnalysis:
    """Audit every premise; an analysis with nothing to report is returned as is.

    A confirmed premise's periods since the change are relabelled
    ``table_confirmed``. The
    timeline, and so every derived status, is unchanged; disagreements and
    ambiguous matches are recorded in ``fact_audit`` for a human to review.
    """

    table = table or default_table()
    audits: list[heinlein_temporal.FactAudit] = []
    premises = []
    for premise in analysis.premises:
        audit = audit_premise(premise, table)
        if audit is None:
            premises.append(premise)
            continue
        audits.append(audit)
        premises.append(
            _mark_since_change(premise)
            if audit.outcome == "table_confirmed"
            else premise
        )
    if not audits:
        return analysis
    return dataclasses.replace(
        analysis, premises=tuple(premises), fact_audit=tuple(audits)
    )
