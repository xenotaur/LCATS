"""Versioned rubric metadata with primary-source gates.

The source-dependent Knight and Suvin governing text is intentionally absent
until approved primary-source excerpts and citations are supplied.
"""

from __future__ import annotations

import dataclasses
from typing import Any

from lcats.analysis.science_fiction import models

SOURCE_STATUS_PENDING = "pending_primary_source"


@dataclasses.dataclass(frozen=True)
class RubricTextSlot:
    """One source-dependent rubric text slot."""

    slot_id: str
    label: str
    source_status: str = SOURCE_STATUS_PENDING
    governing_text: str | None = None
    citation: str | None = None

    def __post_init__(self) -> None:
        if not self.slot_id:
            raise ValueError("slot_id must be non-empty")
        if not self.label:
            raise ValueError("label must be non-empty")
        if self.source_status == SOURCE_STATUS_PENDING:
            if self.governing_text is not None or self.citation is not None:
                raise ValueError("pending rubric slots cannot include governing text")
        elif not self.governing_text or not self.citation:
            raise ValueError("resolved rubric slots require text and citation")

    @property
    def resolved(self) -> bool:
        return self.source_status != SOURCE_STATUS_PENDING

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class RubricDefinition:
    """A versioned rubric definition and its unresolved source slots."""

    rubric_id: str
    source_status: str
    text_slots: tuple[RubricTextSlot, ...]
    source_note: str

    def __post_init__(self) -> None:
        if not self.rubric_id:
            raise ValueError("rubric_id must be non-empty")
        if not self.text_slots:
            raise ValueError("text_slots must be non-empty")
        slot_ids = [slot.slot_id for slot in self.text_slots]
        if len(set(slot_ids)) != len(slot_ids):
            raise ValueError("text slot ids must be unique")
        if not self.source_note:
            raise ValueError("source_note must be non-empty")

    @property
    def source_ready(self) -> bool:
        return self.source_status != SOURCE_STATUS_PENDING and all(
            slot.resolved for slot in self.text_slots
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "rubric_id": self.rubric_id,
            "source_status": self.source_status,
            "source_ready": self.source_ready,
            "text_slots": [slot.to_dict() for slot in self.text_slots],
            "source_note": self.source_note,
        }


KNIGHT_SEVEN = RubricDefinition(
    rubric_id=models.KNIGHT_RUBRIC_VERSION,
    source_status=SOURCE_STATUS_PENDING,
    text_slots=tuple(
        RubricTextSlot(
            slot_id=criterion_id,
            label=f"Knight criterion {index}",
        )
        for index, criterion_id in enumerate(models.KNIGHT_CRITERION_IDS, start=1)
    ),
    source_note=(
        "Exact Knight criterion descriptions, edition, and page citations must be "
        "supplied from an approved primary source before rubric text is frozen."
    ),
)

SUVIN_NOVUM = RubricDefinition(
    rubric_id=models.SUVIN_RUBRIC_VERSION,
    source_status=SOURCE_STATUS_PENDING,
    text_slots=(
        RubricTextSlot("novelty", "Ontological novelty"),
        RubricTextSlot("cognitive_validation", "Cognitive validation"),
        RubricTextSlot("narrative_hegemony", "Narrative hegemony"),
    ),
    source_note=(
        "Exact Suvin theoretical definitions, edition, and page citations must be "
        "supplied from an approved primary source before rubric text is frozen."
    ),
)
