"""Event-Role-World object schemas for extractor stages 1-5.

Implements the object responsibilities sketched in the governing proposal's
"Core schema sketch" (project/design/proposals/proposed/
lcats-event-role-world-extractor/00_proposal.md), scoped to the stages this
work item covers: entities/participants, events/semantic roles, and
temporal/spatial anchors. Relation, discourse, SF-tag, and hypothesis
objects are out of scope (WI-EVENT-0024 forbidden_actions).
"""

from __future__ import annotations

import dataclasses

from typing import Any, Dict, List, Optional


@dataclasses.dataclass
class EvidenceSpan:
    """Grounds a claim with a character span and quoted text.

    Attributes:
        start_char: 0-based start offset into the segment text.
        end_char: 0-based end offset (exclusive) into the segment text.
        quote: The exact substring the span points to.
        source: One of "story", "segment", "model_pass", "external_annotation".
        paragraph_ids: Optional paragraph IDs the span falls within.
    """

    start_char: int
    end_char: int
    quote: str
    source: str = "segment"
    paragraph_ids: Optional[List[int]] = None

    def validate(self, text: str) -> Optional[str]:
        """Return an error string if this span is invalid against `text`."""
        if self.start_char < 0 or self.end_char > len(text):
            return (
                f"evidence span [{self.start_char}:{self.end_char}] out of "
                f"bounds for text of length {len(text)}"
            )
        if self.start_char >= self.end_char:
            return f"evidence span [{self.start_char}:{self.end_char}] is empty or inverted"
        actual = text[self.start_char : self.end_char]
        if self.quote and actual != self.quote:
            return f"evidence span text mismatch: expected {self.quote!r}, found {actual!r}"
        return None

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class EntityMention:
    """A surface mention of an entity within a segment."""

    mention_id: str
    entity_id: str
    text: str
    evidence: EvidenceSpan
    mention_form: Optional[str] = None
    grammatical_role: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mention_id": self.mention_id,
            "entity_id": self.entity_id,
            "text": self.text,
            "evidence": self.evidence.to_dict(),
            "mention_form": self.mention_form,
            "grammatical_role": self.grammatical_role,
        }


@dataclasses.dataclass
class Entity:
    """Reconciles participant mentions into a canonical entity."""

    entity_id: str
    canonical_name: str
    entity_type: str
    aliases: List[str] = dataclasses.field(default_factory=list)
    mention_ids: List[str] = dataclasses.field(default_factory=list)
    actant_roles: List[str] = dataclasses.field(default_factory=list)
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class SemanticRole:
    """Binds an event to an entity or literal filler with a controlled role."""

    role: str
    evidence: EvidenceSpan
    filler_entity_id: Optional[str] = None
    filler_text: Optional[str] = None
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "evidence": self.evidence.to_dict(),
            "filler_entity_id": self.filler_entity_id,
            "filler_text": self.filler_text,
            "confidence": self.confidence,
        }


@dataclasses.dataclass
class Event:
    """A salient predicate with semantic roles and anchors."""

    event_id: str
    predicate: str
    event_type: str
    evidence: EvidenceSpan
    lemma: Optional[str] = None
    semantic_roles: List[SemanticRole] = dataclasses.field(default_factory=list)
    temporal_anchor_ids: List[str] = dataclasses.field(default_factory=list)
    spatial_anchor_ids: List[str] = dataclasses.field(default_factory=list)
    modality: str = "actual"
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "predicate": self.predicate,
            "event_type": self.event_type,
            "evidence": self.evidence.to_dict(),
            "lemma": self.lemma,
            "semantic_roles": [r.to_dict() for r in self.semantic_roles],
            "temporal_anchor_ids": self.temporal_anchor_ids,
            "spatial_anchor_ids": self.spatial_anchor_ids,
            "modality": self.modality,
            "confidence": self.confidence,
        }


@dataclasses.dataclass
class TemporalAnchor:
    """Records a normalized or textual time reference."""

    anchor_id: str
    text: str
    evidence: EvidenceSpan
    normalized: Optional[str] = None
    granularity: Optional[str] = None
    relative_or_absolute: str = "relative"
    scale: Optional[str] = None
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "anchor_id": self.anchor_id,
            "text": self.text,
            "evidence": self.evidence.to_dict(),
            "normalized": self.normalized,
            "granularity": self.granularity,
            "relative_or_absolute": self.relative_or_absolute,
            "scale": self.scale,
            "confidence": self.confidence,
        }


@dataclasses.dataclass
class SpatialAnchor:
    """Records a place or spatial frame."""

    anchor_id: str
    text: str
    evidence: EvidenceSpan
    linked_entity_id: Optional[str] = None
    containment_or_scale: Optional[str] = None
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "anchor_id": self.anchor_id,
            "text": self.text,
            "evidence": self.evidence.to_dict(),
            "linked_entity_id": self.linked_entity_id,
            "containment_or_scale": self.containment_or_scale,
            "confidence": self.confidence,
        }


@dataclasses.dataclass
class SurfaceFeatures:
    """Lexical, syntactic, and morphological features for a segment.

    Not part of the governing proposal's "Core schema sketch" (which lists
    no schema for the surface-feature pass) — this shape is this work
    item's own design, populated by whichever NLPBackend produced it.

    Attributes:
        word_count: Number of tokens in the segment.
        sentence_count: Number of sentences in the segment.
        avg_sentence_length: Mean tokens per sentence.
        avg_word_length: Mean characters per token.
        tokens: Per-token records as produced by an NLPBackend: each dict
            has keys text, lemma, upos, xpos, feats, head_index, deprel.
        backend_name: Which NLPBackend produced `tokens` (e.g. "stanza",
            "spacy").
    """

    word_count: int
    sentence_count: int
    avg_sentence_length: float
    avg_word_length: float
    tokens: List[Dict[str, Any]] = dataclasses.field(default_factory=list)
    backend_name: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class SegmentWorldAnnotation:
    """Collects all Event-Role-World annotations for one segment."""

    segment_id: Any
    surface_features: Optional[SurfaceFeatures] = None
    entities: List[Entity] = dataclasses.field(default_factory=list)
    mentions: List[EntityMention] = dataclasses.field(default_factory=list)
    events: List[Event] = dataclasses.field(default_factory=list)
    temporal_anchors: List[TemporalAnchor] = dataclasses.field(default_factory=list)
    spatial_anchors: List[SpatialAnchor] = dataclasses.field(default_factory=list)
    validation_errors: List[str] = dataclasses.field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "segment_id": self.segment_id,
            "surface_features": (
                self.surface_features.to_dict() if self.surface_features else None
            ),
            "entities": [e.to_dict() for e in self.entities],
            "mentions": [m.to_dict() for m in self.mentions],
            "events": [e.to_dict() for e in self.events],
            "temporal_anchors": [a.to_dict() for a in self.temporal_anchors],
            "spatial_anchors": [a.to_dict() for a in self.spatial_anchors],
            "validation_errors": self.validation_errors,
        }


def resolve_evidence(
    quote: str, segment_text: str, source: str = "segment"
) -> Optional[EvidenceSpan]:
    """Locate `quote` in `segment_text` and build an EvidenceSpan.

    Args:
        quote: Exact substring an LLM extraction claimed as evidence.
        segment_text: The text to search within.
        source: EvidenceSpan.source value.

    Returns:
        An EvidenceSpan if `quote` is found (first occurrence), else None.
    """
    if not quote:
        return None
    start = segment_text.find(quote)
    if start < 0:
        return None
    return EvidenceSpan(
        start_char=start, end_char=start + len(quote), quote=quote, source=source
    )


def validate_segment_annotation(
    annotation: SegmentWorldAnnotation, segment_text: str
) -> List[str]:
    """Validate ID resolution and evidence-span alignment for one segment.

    Args:
        annotation: The annotation to validate.
        segment_text: The exact segment text evidence spans are offset into.

    Returns:
        A list of human-readable error strings; empty if valid.
    """
    errors: List[str] = []

    entity_ids = {e.entity_id for e in annotation.entities}
    mention_ids = {m.mention_id for m in annotation.mentions}
    anchor_ids = {a.anchor_id for a in annotation.temporal_anchors} | {
        a.anchor_id for a in annotation.spatial_anchors
    }

    for mention in annotation.mentions:
        if mention.entity_id not in entity_ids:
            errors.append(
                f"mention {mention.mention_id!r} references unknown entity "
                f"{mention.entity_id!r}"
            )
        span_error = mention.evidence.validate(segment_text)
        if span_error:
            errors.append(f"mention {mention.mention_id!r}: {span_error}")

    for entity in annotation.entities:
        for mid in entity.mention_ids:
            if mid not in mention_ids:
                errors.append(
                    f"entity {entity.entity_id!r} references unknown mention {mid!r}"
                )

    for event in annotation.events:
        span_error = event.evidence.validate(segment_text)
        if span_error:
            errors.append(f"event {event.event_id!r}: {span_error}")
        for role in event.semantic_roles:
            if role.filler_entity_id and role.filler_entity_id not in entity_ids:
                errors.append(
                    f"event {event.event_id!r} role {role.role!r} references "
                    f"unknown entity {role.filler_entity_id!r}"
                )
            role_span_error = role.evidence.validate(segment_text)
            if role_span_error:
                errors.append(
                    f"event {event.event_id!r} role {role.role!r}: {role_span_error}"
                )
        for aid in event.temporal_anchor_ids + event.spatial_anchor_ids:
            if aid not in anchor_ids:
                errors.append(
                    f"event {event.event_id!r} references unknown anchor {aid!r}"
                )

    for anchor in annotation.temporal_anchors:
        span_error = anchor.evidence.validate(segment_text)
        if span_error:
            errors.append(f"temporal anchor {anchor.anchor_id!r}: {span_error}")

    for anchor in annotation.spatial_anchors:
        span_error = anchor.evidence.validate(segment_text)
        if span_error:
            errors.append(f"spatial anchor {anchor.anchor_id!r}: {span_error}")

    return errors
