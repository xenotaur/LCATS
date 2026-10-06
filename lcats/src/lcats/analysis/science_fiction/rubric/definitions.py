"""Versioned rubric metadata with primary-source gates.

The source-dependent Knight and Suvin governing text is intentionally absent
until approved primary-source excerpts and citations are supplied. The Heinlein
rubric is resolved against a cited reprint of the primary source; see
``HEINLEIN_FIVE`` and its ``source_note``.
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

HEINLEIN_CITATION = (
    'Robert A. Heinlein, "On the Writing of Speculative Fiction," in Of Worlds '
    "Beyond: The Science of Science-Fiction Writing (Chicago: Advent "
    "Publishers, 1964), pp. 13-19 (first collected 1947); conditions checked "
    "against the text of the 1964 Advent printing supplied by the work item "
    "owner, whose cover blurb states that its text is photo-reproduced from "
    "the Fantasy Press original, and against the English reprint in (n.t.) "
    "Revista Nota do Tradutor, no. 24 (2022), printed pp. 129-130."
)
SOURCE_STATUS_VERIFIED_REPRINT = "verified_primary_reprint"

HEINLEIN_FIVE = RubricDefinition(
    rubric_id=models.HEINLEIN_RUBRIC_VERSION,
    source_status=SOURCE_STATUS_VERIFIED_REPRINT,
    text_slots=(
        RubricTextSlot(
            "different",
            "Conditions different from the here and now",
            source_status=SOURCE_STATUS_VERIFIED_REPRINT,
            governing_text=(
                "The conditions must be different from here-and-now in some "
                "respect; the difference may lie only in an invention made in "
                "the course of the story."
            ),
            citation=HEINLEIN_CITATION,
        ),
        RubricTextSlot(
            "essential",
            "New conditions essential to the story",
            source_status=SOURCE_STATUS_VERIFIED_REPRINT,
            governing_text=(
                "The new conditions must be an essential part of the story."
            ),
            citation=HEINLEIN_CITATION,
        ),
        RubricTextSlot(
            "human",
            "Problem is a human problem",
            source_status=SOURCE_STATUS_VERIFIED_REPRINT,
            governing_text=("The problem itself, the plot, must be a human problem."),
            citation=HEINLEIN_CITATION,
        ),
        RubricTextSlot(
            "causal",
            "Human problem created or indispensably affected by the new conditions",
            source_status=SOURCE_STATUS_VERIFIED_REPRINT,
            governing_text=(
                "The human problem must be one created by, or indispensably "
                "affected by, the new conditions."
            ),
            citation=HEINLEIN_CITATION,
        ),
        RubricTextSlot(
            "plausible",
            "No established fact violated",
            source_status=SOURCE_STATUS_VERIFIED_REPRINT,
            governing_text=(
                "No established fact shall be violated; a contrary new theory "
                "must be made reasonably plausible and must explain established "
                "facts as satisfactorily as the theory it replaces. The theory "
                "may be far-fetched or fantastic, but it must not be at "
                "variance with observed facts."
            ),
            citation=HEINLEIN_CITATION,
        ),
    ),
    source_note=(
        "Wording verified against the text of the 1964 Advent printing of Of "
        "Worlds Beyond supplied by the work item owner, and against the English "
        "reprint in Nota do Tradutor 24. Conditions 1-4 match word for word; "
        "condition 5 differs by one word in its illustrative example only. The "
        "owner reports the Advent cover blurb says its text is photo-reproduced "
        "from the Fantasy Press original, so the wording is treated as "
        "edition-final on the owner's report. That report and the transcription "
        "from the owner's physical copy have not been independently checked "
        "and no digital copy exists for an agent to review; reopen if either is "
        "shown to be wrong. Heinlein calls the result the 'Simon-pure science "
        "fiction story'. See definitions.md in the science_fiction_analysis_trial "
        "experiment for the comparison and the rule for minting a v2 id."
    ),
)
