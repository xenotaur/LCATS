"""Theory-neutral evidence records for science-fiction analysis."""

from __future__ import annotations

import dataclasses
import hashlib
import json
from typing import Any, Iterable, Protocol

from lcats.analysis.science_fiction import preparation

EVIDENCE_SET_VERSION = "science-fiction-evidence-set-v1"
STRUCTURED_OUTPUT_SCHEMA_VERSION = "science-fiction-evidence-output-v1"

EVIDENCE_TYPES = frozenset(
    {
        "storyworld_change",
        "scientific_or_technical_explanation",
        "inquiry_or_scientific_method",
        "temporal_or_spatial_displacement",
        "extrapolative_consequence",
        "catastrophe",
        "character_reaction",
        "reader_facing_contrast",
    }
)


@dataclasses.dataclass(frozen=True)
class EvidenceExtractionRequest:
    """Backend-independent input for a neutral evidence extraction pass."""

    story_hash: str
    chunk_id: str
    paragraph_ids: tuple[str, ...]
    text: str
    schema_version: str = STRUCTURED_OUTPUT_SCHEMA_VERSION

    @classmethod
    def from_chunk(
        cls,
        prepared_story: preparation.StoryPreparation,
        chunk: preparation.ChunkPlan,
    ) -> "EvidenceExtractionRequest":
        return cls(
            story_hash=prepared_story.story_hash,
            chunk_id=chunk.chunk_id,
            paragraph_ids=chunk.paragraph_ids,
            text=chunk.text,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "story_hash": self.story_hash,
            "chunk_id": self.chunk_id,
            "paragraph_ids": list(self.paragraph_ids),
            "text": self.text,
        }


@dataclasses.dataclass(frozen=True)
class EvidenceCandidate:
    """One model- or adapter-produced neutral evidence candidate."""

    evidence_type: str
    quote: str
    paraphrase: str
    confidence: float
    source_chunk_id: str | None = None
    paragraph_ids: tuple[str, ...] = ()
    start_char: int | None = None
    end_char: int | None = None
    entity_ids: tuple[str, ...] = ()
    event_ids: tuple[str, ...] = ()
    raw_id: str | None = None
    source: str = "model"
    schema_errors: tuple[str, ...] = ()

    @classmethod
    def from_mapping(
        cls,
        data: dict[str, Any],
        *,
        default_source_chunk_id: str | None = None,
        source: str = "model",
    ) -> "EvidenceCandidate":
        paragraph_ids, paragraph_errors = _string_tuple_field(data, "paragraph_ids")
        entity_ids, entity_errors = _string_tuple_field(data, "entity_ids")
        event_ids, event_errors = _string_tuple_field(data, "event_ids")
        evidence_type, evidence_type_errors = _required_string_field(
            data, "evidence_type"
        )
        quote, quote_errors = _required_string_field(data, "quote")
        paraphrase, paraphrase_errors = _required_string_field(data, "paraphrase")
        return cls(
            evidence_type=evidence_type,
            quote=quote,
            paraphrase=paraphrase,
            confidence=_coerce_confidence(data.get("confidence", 0.0)),
            source_chunk_id=_optional_string(
                data.get("source_chunk_id"), default_source_chunk_id
            ),
            paragraph_ids=paragraph_ids,
            start_char=_optional_int(data.get("start_char")),
            end_char=_optional_int(data.get("end_char")),
            entity_ids=entity_ids,
            event_ids=event_ids,
            raw_id=_optional_string(data.get("raw_id")),
            source=source,
            schema_errors=(
                evidence_type_errors
                + quote_errors
                + paraphrase_errors
                + paragraph_errors
                + entity_errors
                + event_errors
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_id": self.raw_id,
            "evidence_type": self.evidence_type,
            "quote": self.quote,
            "paragraph_ids": list(self.paragraph_ids),
            "start_char": self.start_char,
            "end_char": self.end_char,
            "paraphrase": self.paraphrase,
            "entity_ids": list(self.entity_ids),
            "event_ids": list(self.event_ids),
            "confidence": self.confidence,
            "source_chunk_id": self.source_chunk_id,
            "source": self.source,
            "schema_errors": list(self.schema_errors),
        }


@dataclasses.dataclass(frozen=True)
class EvidenceProvenance:
    """Records where an evidence candidate came from."""

    source: str
    source_chunk_id: str | None = None
    raw_id: str | None = None
    backend: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "source_chunk_id": self.source_chunk_id,
            "raw_id": self.raw_id,
            "backend": self.backend,
        }


@dataclasses.dataclass(frozen=True)
class EvidenceAnchor:
    """Canonical location of a quote in prepared story text."""

    paragraph_ids: tuple[str, ...]
    start_char: int
    end_char: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "paragraph_ids": list(self.paragraph_ids),
            "start_char": self.start_char,
            "end_char": self.end_char,
        }


@dataclasses.dataclass(frozen=True)
class EvidenceRecord:
    """Validated neutral evidence anchored to one prepared story."""

    evidence_id: str
    evidence_type: str
    quote: str
    anchor: EvidenceAnchor
    paraphrase: str
    confidence: float
    provenance: tuple[EvidenceProvenance, ...]
    entity_ids: tuple[str, ...] = ()
    event_ids: tuple[str, ...] = ()

    def identity_key(self) -> tuple[Any, ...]:
        return (
            self.evidence_type,
            self.quote,
            self.anchor.paragraph_ids,
            self.anchor.start_char,
            self.anchor.end_char,
            self.paraphrase,
            self.entity_ids,
            self.event_ids,
        )

    def conflict_key(self) -> tuple[Any, ...]:
        return (
            self.evidence_type,
            self.quote,
            self.anchor.paragraph_ids,
            self.anchor.start_char,
            self.anchor.end_char,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "evidence_type": self.evidence_type,
            "quote": self.quote,
            "anchor": self.anchor.to_dict(),
            "paraphrase": self.paraphrase,
            "entity_ids": list(self.entity_ids),
            "event_ids": list(self.event_ids),
            "confidence": self.confidence,
            "provenance": [item.to_dict() for item in self.provenance],
        }


@dataclasses.dataclass(frozen=True)
class QuarantinedEvidence:
    """A candidate that could not be safely included in the evidence set."""

    reason: str
    candidate: EvidenceCandidate

    def to_dict(self) -> dict[str, Any]:
        return {"reason": self.reason, "candidate": self.candidate.to_dict()}


@dataclasses.dataclass(frozen=True)
class EvidenceConflict:
    """A same-anchor disagreement intentionally retained for adjudicators."""

    conflict_id: str
    evidence_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "conflict_id": self.conflict_id,
            "evidence_ids": list(self.evidence_ids),
        }


@dataclasses.dataclass(frozen=True)
class EvidenceSet:
    """Validated neutral evidence for one prepared story."""

    evidence_set_id: str
    story_hash: str
    records: tuple[EvidenceRecord, ...]
    quarantined: tuple[QuarantinedEvidence, ...]
    conflicts: tuple[EvidenceConflict, ...]
    version: str = EVIDENCE_SET_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "evidence_set_id": self.evidence_set_id,
            "story_hash": self.story_hash,
            "records": [record.to_dict() for record in self.records],
            "quarantined": [item.to_dict() for item in self.quarantined],
            "conflicts": [item.to_dict() for item in self.conflicts],
        }


class NeutralEvidenceExtractor(Protocol):
    """Backend boundary for no-cost fixtures, local adapters, or model clients."""

    def extract(
        self, request: EvidenceExtractionRequest
    ) -> Iterable[EvidenceCandidate | dict[str, Any]]:
        """Return candidate evidence without doing deterministic validation."""


def build_evidence_set(
    prepared_story: preparation.StoryPreparation,
    candidates: Iterable[EvidenceCandidate | dict[str, Any]],
    *,
    backend: str | None = None,
) -> EvidenceSet:
    """Validate, anchor, quarantine, and de-duplicate neutral evidence."""

    records_by_key: dict[tuple[Any, ...], EvidenceRecord] = {}
    quarantined: list[QuarantinedEvidence] = []
    for raw_candidate in candidates:
        candidate = _coerce_candidate(raw_candidate)
        reason = _candidate_schema_error(candidate)
        if reason is not None:
            quarantined.append(QuarantinedEvidence(reason=reason, candidate=candidate))
            continue

        anchor = locate_quote(prepared_story, candidate)
        if anchor is None:
            quarantined.append(
                QuarantinedEvidence(
                    reason="quote could not be located in prepared story",
                    candidate=candidate,
                )
            )
            continue

        record = _record_from_candidate(
            candidate,
            anchor,
            backend=backend,
        )
        existing = records_by_key.get(record.identity_key())
        if existing is None:
            records_by_key[record.identity_key()] = record
        else:
            records_by_key[record.identity_key()] = _merge_duplicate(existing, record)

    records = tuple(
        sorted(records_by_key.values(), key=lambda record: record.evidence_id)
    )
    conflicts = _find_conflicts(records)
    evidence_set_id = _stable_id(
        "sfes",
        {
            "story_hash": prepared_story.story_hash,
            "record_ids": [record.evidence_id for record in records],
            "quarantined": _sorted_quarantine_payload(quarantined),
        },
    )
    return EvidenceSet(
        evidence_set_id=evidence_set_id,
        story_hash=prepared_story.story_hash,
        records=records,
        quarantined=tuple(quarantined),
        conflicts=conflicts,
    )


def extract_evidence_set(
    extractor: NeutralEvidenceExtractor,
    prepared_story: preparation.StoryPreparation,
    *,
    backend: str | None = None,
) -> EvidenceSet:
    """Run an extractor over prepared chunks and aggregate validated evidence."""

    candidates: list[EvidenceCandidate | dict[str, Any]] = []
    for chunk in prepared_story.chunks:
        request = EvidenceExtractionRequest.from_chunk(prepared_story, chunk)
        candidates.extend(
            _coerce_candidate(candidate, default_source_chunk_id=chunk.chunk_id)
            for candidate in extractor.extract(request)
        )
    return build_evidence_set(prepared_story, candidates, backend=backend)


def locate_quote(
    prepared_story: preparation.StoryPreparation,
    candidate: EvidenceCandidate,
) -> EvidenceAnchor | None:
    """Locate a candidate's exact quote against prepared story anchors."""

    quote = candidate.quote
    if not quote:
        return None

    if candidate.start_char is not None or candidate.end_char is not None:
        if candidate.start_char is None or candidate.end_char is None:
            return None
        start = candidate.start_char
        end = candidate.end_char
        if not _valid_span_bounds(prepared_story, start, end):
            return None
        if prepared_story.normalized_text[start:end] != quote:
            return None
        anchor = EvidenceAnchor(
            paragraph_ids=_paragraph_ids_for_span(prepared_story, start, end),
            start_char=start,
            end_char=end,
        )
        if not _anchor_satisfies_candidate(prepared_story, candidate, anchor):
            return None
        return anchor

    ranges = _candidate_search_ranges(prepared_story, candidate)
    if ranges is None:
        return None
    for start_bound, end_bound in ranges:
        search_from = start_bound
        while search_from < end_bound:
            found_at = prepared_story.normalized_text.find(
                quote, search_from, end_bound
            )
            if found_at == -1:
                break
            end = found_at + len(quote)
            anchor = EvidenceAnchor(
                paragraph_ids=_paragraph_ids_for_span(prepared_story, found_at, end),
                start_char=found_at,
                end_char=end,
            )
            if _anchor_satisfies_candidate(prepared_story, candidate, anchor):
                return anchor
            search_from = found_at + 1
    return None


def adapt_erw_annotation(
    annotation: Any,
    *,
    source_chunk_id: str | None = None,
    segment_start_char: int = 0,
) -> tuple[EvidenceCandidate, ...]:
    """Adapt optional ERW discourse tags/explanations into neutral candidates.

    The adapter uses duck typing so importing or running ERW is not required.
    Callers that never produce ERW output can simply skip this function.
    """

    candidates: list[EvidenceCandidate] = []
    for raw_tag in getattr(annotation, "sf_tags", ()) or ():
        tag = str(getattr(raw_tag, "tag", ""))
        evidence_type = _erw_tag_to_evidence_type(tag)
        if evidence_type is None:
            continue
        evidence_span = getattr(raw_tag, "evidence", None)
        quote, quote_errors = _required_string_value(
            getattr(evidence_span, "quote", None), "quote"
        )
        paragraph_ids, paragraph_errors = _string_tuple_value(
            getattr(evidence_span, "paragraph_ids", ()), "paragraph_ids"
        )
        entity_ids, entity_errors = _string_tuple_value(
            getattr(raw_tag, "linked_entity_ids", ()), "entity_ids"
        )
        event_ids, event_errors = _string_tuple_value(
            getattr(raw_tag, "linked_event_ids", ()), "event_ids"
        )
        candidates.append(
            EvidenceCandidate(
                evidence_type=evidence_type,
                quote=quote,
                paraphrase=tag.replace("_", " "),
                confidence=_coerce_confidence(getattr(raw_tag, "confidence", 0.0)),
                source_chunk_id=source_chunk_id,
                paragraph_ids=paragraph_ids,
                start_char=_translated_erw_offset(
                    getattr(evidence_span, "start_char", None), segment_start_char
                ),
                end_char=_translated_erw_offset(
                    getattr(evidence_span, "end_char", None), segment_start_char
                ),
                entity_ids=entity_ids,
                event_ids=event_ids,
                raw_id=_optional_string(getattr(raw_tag, "tag_id", None)),
                source="erw",
                schema_errors=(
                    quote_errors + paragraph_errors + entity_errors + event_errors
                ),
            )
        )

    for raw_explanation in getattr(annotation, "explanations", ()) or ():
        evidence_span = getattr(raw_explanation, "evidence", None)
        quote, quote_errors = _required_string_value(
            getattr(evidence_span, "quote", None), "quote"
        )
        paraphrase, paraphrase_errors = _required_string_value(
            getattr(raw_explanation, "topic", None), "paraphrase"
        )
        paragraph_ids, paragraph_errors = _string_tuple_value(
            getattr(evidence_span, "paragraph_ids", ()), "paragraph_ids"
        )
        entity_ids, entity_errors = _string_tuple_value(
            getattr(raw_explanation, "linked_entity_ids", ()), "entity_ids"
        )
        event_ids, event_errors = _string_tuple_value(
            getattr(raw_explanation, "linked_event_ids", ()), "event_ids"
        )
        candidates.append(
            EvidenceCandidate(
                evidence_type="scientific_or_technical_explanation",
                quote=quote,
                paraphrase=paraphrase,
                confidence=_coerce_confidence(
                    getattr(raw_explanation, "confidence", 0.0)
                ),
                source_chunk_id=source_chunk_id,
                paragraph_ids=paragraph_ids,
                start_char=_translated_erw_offset(
                    getattr(evidence_span, "start_char", None), segment_start_char
                ),
                end_char=_translated_erw_offset(
                    getattr(evidence_span, "end_char", None), segment_start_char
                ),
                entity_ids=entity_ids,
                event_ids=event_ids,
                raw_id=_optional_string(
                    getattr(raw_explanation, "explanation_id", None)
                ),
                source="erw",
                schema_errors=(
                    quote_errors
                    + paraphrase_errors
                    + paragraph_errors
                    + entity_errors
                    + event_errors
                ),
            )
        )
    return tuple(candidates)


def _candidate_schema_error(candidate: EvidenceCandidate) -> str | None:
    if candidate.schema_errors:
        return candidate.schema_errors[0]
    if candidate.evidence_type not in EVIDENCE_TYPES:
        return f"unsupported neutral evidence type: {candidate.evidence_type!r}"
    if not candidate.quote:
        return "quote is required"
    if not candidate.paraphrase:
        return "paraphrase is required"
    if not 0.0 <= candidate.confidence <= 1.0:
        return "confidence must be between 0 and 1"
    return None


def _coerce_candidate(
    raw_candidate: EvidenceCandidate | dict[str, Any],
    *,
    default_source_chunk_id: str | None = None,
) -> EvidenceCandidate:
    if isinstance(raw_candidate, EvidenceCandidate):
        if (
            raw_candidate.source_chunk_id is None
            and default_source_chunk_id is not None
        ):
            return dataclasses.replace(
                raw_candidate, source_chunk_id=default_source_chunk_id
            )
        return raw_candidate
    if isinstance(raw_candidate, dict):
        return EvidenceCandidate.from_mapping(
            raw_candidate, default_source_chunk_id=default_source_chunk_id
        )
    return EvidenceCandidate(
        evidence_type="",
        quote="",
        paraphrase=f"malformed candidate of type {type(raw_candidate).__name__}",
        confidence=0.0,
        source="malformed",
        source_chunk_id=default_source_chunk_id,
        schema_errors=(
            f"candidate must be an object, got {type(raw_candidate).__name__}",
        ),
    )


def _record_from_candidate(
    candidate: EvidenceCandidate,
    anchor: EvidenceAnchor,
    *,
    backend: str | None,
) -> EvidenceRecord:
    identity = {
        "type": candidate.evidence_type,
        "quote": candidate.quote,
        "anchor": anchor.to_dict(),
        "paraphrase": candidate.paraphrase,
        "entity_ids": list(candidate.entity_ids),
        "event_ids": list(candidate.event_ids),
    }
    return EvidenceRecord(
        evidence_id=_stable_id("sfev", identity),
        evidence_type=candidate.evidence_type,
        quote=candidate.quote,
        anchor=anchor,
        paraphrase=candidate.paraphrase,
        entity_ids=candidate.entity_ids,
        event_ids=candidate.event_ids,
        confidence=candidate.confidence,
        provenance=(
            EvidenceProvenance(
                source=candidate.source,
                source_chunk_id=candidate.source_chunk_id,
                raw_id=candidate.raw_id,
                backend=backend,
            ),
        ),
    )


def _merge_duplicate(first: EvidenceRecord, second: EvidenceRecord) -> EvidenceRecord:
    provenance = tuple(
        sorted(
            {*first.provenance, *second.provenance},
            key=lambda item: (
                item.source,
                item.source_chunk_id or "",
                item.raw_id or "",
                item.backend or "",
            ),
        )
    )
    return dataclasses.replace(
        first,
        confidence=max(first.confidence, second.confidence),
        provenance=provenance,
    )


def _find_conflicts(
    records: tuple[EvidenceRecord, ...],
) -> tuple[EvidenceConflict, ...]:
    groups: dict[tuple[Any, ...], list[EvidenceRecord]] = {}
    for record in records:
        groups.setdefault(record.conflict_key(), []).append(record)

    conflicts: list[EvidenceConflict] = []
    for key, group in groups.items():
        if len(group) < 2:
            continue
        evidence_ids = tuple(record.evidence_id for record in group)
        conflicts.append(
            EvidenceConflict(
                conflict_id=_stable_id("sfconflict", {"key": key}),
                evidence_ids=evidence_ids,
            )
        )
    return tuple(sorted(conflicts, key=lambda conflict: conflict.conflict_id))


def _candidate_search_ranges(
    prepared_story: preparation.StoryPreparation,
    candidate: EvidenceCandidate,
) -> tuple[tuple[int, int], ...] | None:
    bounds: tuple[int, int] | None = None
    if candidate.source_chunk_id:
        chunk = _chunk_by_id(prepared_story, candidate.source_chunk_id)
        if chunk is None:
            return None
        bounds = _intersect_bounds(bounds, (chunk.start_char, chunk.end_char))
    if candidate.paragraph_ids:
        paragraph_bounds = _paragraph_bounds_for_ids(prepared_story, candidate)
        if paragraph_bounds is None:
            return None
        bounds = _intersect_bounds(bounds, paragraph_bounds)
    if bounds is None:
        bounds = (0, len(prepared_story.normalized_text))
    if bounds[0] >= bounds[1]:
        return None
    return (bounds,)


def _valid_span_bounds(
    prepared_story: preparation.StoryPreparation,
    start_char: int,
    end_char: int,
) -> bool:
    return 0 <= start_char < end_char <= len(prepared_story.normalized_text)


def _anchor_satisfies_candidate(
    prepared_story: preparation.StoryPreparation,
    candidate: EvidenceCandidate,
    anchor: EvidenceAnchor,
) -> bool:
    if candidate.source_chunk_id:
        chunk = _chunk_by_id(prepared_story, candidate.source_chunk_id)
        if chunk is None:
            return False
        if anchor.start_char < chunk.start_char or anchor.end_char > chunk.end_char:
            return False
    if candidate.paragraph_ids and anchor.paragraph_ids != candidate.paragraph_ids:
        return False
    return True


def _paragraph_bounds_for_ids(
    prepared_story: preparation.StoryPreparation,
    candidate: EvidenceCandidate,
) -> tuple[int, int] | None:
    paragraph_ids = set(candidate.paragraph_ids)
    paragraph_ranges = [
        (paragraph.start_char, paragraph.end_char)
        for paragraph in prepared_story.paragraphs
        if paragraph.paragraph_id in paragraph_ids
    ]
    if len(paragraph_ranges) != len(paragraph_ids):
        return None
    return (paragraph_ranges[0][0], paragraph_ranges[-1][1])


def _intersect_bounds(
    current: tuple[int, int] | None,
    candidate: tuple[int, int],
) -> tuple[int, int]:
    if current is None:
        return candidate
    return (max(current[0], candidate[0]), min(current[1], candidate[1]))


def _paragraph_ids_for_span(
    prepared_story: preparation.StoryPreparation,
    start_char: int,
    end_char: int,
) -> tuple[str, ...]:
    return tuple(
        paragraph.paragraph_id
        for paragraph in prepared_story.paragraphs
        if paragraph.start_char < end_char and paragraph.end_char > start_char
    )


def _chunk_by_id(
    prepared_story: preparation.StoryPreparation, chunk_id: str
) -> preparation.ChunkPlan | None:
    for chunk in prepared_story.chunks:
        if chunk.chunk_id == chunk_id:
            return chunk
    return None


def _erw_tag_to_evidence_type(tag: str) -> str | None:
    mapping = {
        "anomaly_or_novum": "storyworld_change",
        "ontological_rule": "storyworld_change",
        "time_travel_or_temporal_anomaly": "temporal_or_spatial_displacement",
        "cosmic_scale": "temporal_or_spatial_displacement",
        "catastrophe": "catastrophe",
    }
    return mapping.get(tag)


def _sorted_quarantine_payload(
    quarantined: Iterable[QuarantinedEvidence],
) -> list[dict[str, Any]]:
    payload = [item.to_dict() for item in quarantined]
    return sorted(
        payload,
        key=lambda item: (
            item["reason"],
            json.dumps(item["candidate"], sort_keys=True, separators=(",", ":")),
        ),
    )


def _stable_id(prefix: str, payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def _coerce_confidence(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return -1.0


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_string(value: Any, default: str | None = None) -> str | None:
    if value is None:
        return default
    return str(value)


def _string_tuple_field(
    data: dict[str, Any], key: str
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if key not in data:
        return (), ()
    return _string_tuple_value(data[key], key)


def _string_tuple_value(
    value: Any, key: str
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if not isinstance(value, (list, tuple)):
        return (), (f"{key} must be an array of strings",)
    if not all(isinstance(item, str) for item in value):
        return (), (f"{key} must be an array of strings",)
    return tuple(value), ()


def _required_string_field(
    data: dict[str, Any], key: str
) -> tuple[str, tuple[str, ...]]:
    if key not in data:
        return "", (f"{key} is required",)
    return _required_string_value(data[key], key)


def _required_string_value(value: Any, key: str) -> tuple[str, tuple[str, ...]]:
    if not isinstance(value, str):
        return "", (f"{key} must be a string",)
    return value, ()


def _translated_erw_offset(value: Any, segment_start_char: int) -> int | None:
    offset = _optional_int(value)
    if offset is None:
        return None
    return segment_start_char + offset
