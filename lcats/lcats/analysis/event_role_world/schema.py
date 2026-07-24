"""Event-Role-World object schemas for extractor stages 1-7 and 9.

Implements the object responsibilities sketched in the governing proposal's
"Core schema sketch" (project/design/proposals/proposed/
lcats-event-role-world-extractor/00_proposal.md): entities/participants,
events/semantic roles, temporal/spatial anchors (WI-EVENT-0024), plus
relations, speech acts, explanation discourse, and SF world-model tags
(WI-EVENT-0026). The stage-8 hypothesis object (belief/uncertainty/
perspective/emotion) remains out of scope (WI-EVENT-0026 forbidden_actions:
implement_stage_8_hypothesis_pass).
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
class EventRelation:
    """Links two events with a controlled causal/temporal relation type.

    Attributes:
        certainty: One of "explicit", "strongly_implied", or
            "weakly_inferred". Per the proposal's causality tradeoff table,
            explicit/strongly_implied relations belong in the main relations
            layer; weakly_inferred relations are partitioned into a
            separate list (see SegmentWorldAnnotation.weakly_inferred_relations)
            rather than the stage-8 Hypothesis dataclass — this is a storage
            split on EventRelation itself, not a stage-8 concept.
    """

    relation_id: str
    source_event_id: str
    target_event_id: str
    relation_type: str
    evidence: EvidenceSpan
    certainty: str = "explicit"
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "relation_id": self.relation_id,
            "source_event_id": self.source_event_id,
            "target_event_id": self.target_event_id,
            "relation_type": self.relation_type,
            "evidence": self.evidence.to_dict(),
            "certainty": self.certainty,
            "confidence": self.confidence,
        }


@dataclasses.dataclass
class SpeechAct:
    """A speech act: who said what to whom, and its function."""

    speech_act_id: str
    act_type: str
    evidence: EvidenceSpan
    speaker_entity_id: Optional[str] = None
    addressee_entity_ids: List[str] = dataclasses.field(default_factory=list)
    linked_event_id: Optional[str] = None
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "speech_act_id": self.speech_act_id,
            "act_type": self.act_type,
            "evidence": self.evidence.to_dict(),
            "speaker_entity_id": self.speaker_entity_id,
            "addressee_entity_ids": self.addressee_entity_ids,
            "linked_event_id": self.linked_event_id,
            "confidence": self.confidence,
        }


@dataclasses.dataclass
class ExplanationDiscourse:
    """Marks an explanatory passage (mechanism or rationale)."""

    explanation_id: str
    topic: str
    mechanism_or_rationale_type: str
    evidence: EvidenceSpan
    linked_entity_ids: List[str] = dataclasses.field(default_factory=list)
    linked_event_ids: List[str] = dataclasses.field(default_factory=list)
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "explanation_id": self.explanation_id,
            "topic": self.topic,
            "mechanism_or_rationale_type": self.mechanism_or_rationale_type,
            "evidence": self.evidence.to_dict(),
            "linked_entity_ids": self.linked_entity_ids,
            "linked_event_ids": self.linked_event_ids,
            "confidence": self.confidence,
        }


@dataclasses.dataclass
class SFWorldModelTag:
    """A controlled SF world-model tag (e.g. anomaly_or_novum, ontological_rule).

    Attributes:
        status: "extractive" if the text states the tag explicitly,
            "hypothesis" if inferred — per the proposal's fact/hypothesis
            distinction, interpretive tags are hypotheses unless the text
            states them explicitly.
    """

    tag_id: str
    tag: str
    evidence: EvidenceSpan
    linked_entity_ids: List[str] = dataclasses.field(default_factory=list)
    linked_event_ids: List[str] = dataclasses.field(default_factory=list)
    status: str = "hypothesis"
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tag_id": self.tag_id,
            "tag": self.tag,
            "evidence": self.evidence.to_dict(),
            "linked_entity_ids": self.linked_entity_ids,
            "linked_event_ids": self.linked_event_ids,
            "status": self.status,
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
    """Collects all Event-Role-World annotations for one segment.

    Attributes:
        relations: EventRelation instances with certainty "explicit" or
            "strongly_implied" — the main causal/relation layer.
        weakly_inferred_relations: EventRelation instances with certainty
            "weakly_inferred", stored separately per the proposal's
            causality tradeoff table. This is a storage partition on
            EventRelation itself, not the stage-8 Hypothesis dataclass.
        speech_acts: SpeechAct instances extracted by the discourse pass.
        explanations: ExplanationDiscourse instances extracted by the
            discourse pass.
        sf_tags: SFWorldModelTag instances extracted by the discourse pass.
        extraction_errors: Backend/API-level failures (e.g. a transient
            provider error, an empty tool result) for any LLM-backed pass
            on this segment. Distinct from validation_errors: an
            extraction_error means a pass may not have run at all — its
            "zero results" must not be read as "the pass ran and found
            nothing."
        validation_errors: ID-resolution and evidence-alignment failures
            found by validate_segment_annotation, given whatever entities/
            events/anchors/relations/discourse were actually extracted.
    """

    segment_id: Any
    surface_features: Optional[SurfaceFeatures] = None
    entities: List[Entity] = dataclasses.field(default_factory=list)
    mentions: List[EntityMention] = dataclasses.field(default_factory=list)
    events: List[Event] = dataclasses.field(default_factory=list)
    temporal_anchors: List[TemporalAnchor] = dataclasses.field(default_factory=list)
    spatial_anchors: List[SpatialAnchor] = dataclasses.field(default_factory=list)
    relations: List[EventRelation] = dataclasses.field(default_factory=list)
    weakly_inferred_relations: List[EventRelation] = dataclasses.field(
        default_factory=list
    )
    speech_acts: List[SpeechAct] = dataclasses.field(default_factory=list)
    explanations: List[ExplanationDiscourse] = dataclasses.field(default_factory=list)
    sf_tags: List[SFWorldModelTag] = dataclasses.field(default_factory=list)
    extraction_errors: List[str] = dataclasses.field(default_factory=list)
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
            "relations": [r.to_dict() for r in self.relations],
            "weakly_inferred_relations": [
                r.to_dict() for r in self.weakly_inferred_relations
            ],
            "speech_acts": [s.to_dict() for s in self.speech_acts],
            "explanations": [e.to_dict() for e in self.explanations],
            "sf_tags": [t.to_dict() for t in self.sf_tags],
            "extraction_errors": self.extraction_errors,
            "validation_errors": self.validation_errors,
        }


def resolve_evidence(
    quote: str,
    segment_text: str,
    source: str = "segment",
    search_from: int = 0,
) -> Optional[EvidenceSpan]:
    """Locate `quote` in `segment_text` and build an EvidenceSpan.

    Args:
        quote: Exact substring an LLM extraction claimed as evidence.
        segment_text: The text to search within.
        source: EvidenceSpan.source value.
        search_from: Character offset to start searching from. When a
            segment repeats the same quote (e.g. "he" mentioned several
            times), passing the previous match's end_char here resolves
            each successive claim to the next occurrence instead of
            silently collapsing every claim onto occurrence 0. Callers
            resolving multiple evidence spans for the same segment should
            track a per-quote cursor (see EvidenceCursor).

    Returns:
        An EvidenceSpan if `quote` is found at or after `search_from`, else
        None.
    """
    if not quote:
        return None
    start = segment_text.find(quote, search_from)
    if start < 0:
        return None
    return EvidenceSpan(
        start_char=start, end_char=start + len(quote), quote=quote, source=source
    )


class EvidenceCursor:
    """Tracks per-quote search positions so repeated quotes within one
    segment resolve to successive occurrences rather than all collapsing
    onto the first match.

    Usage: construct one EvidenceCursor per segment (not shared across
    segments — each segment's text is searched independently), and call
    `.resolve(quote, segment_text)` for every evidence claim in that
    segment, in the order the extraction produced them.
    """

    def __init__(self) -> None:
        self._next_search_from: Dict[str, int] = {}

    def resolve(
        self, quote: str, segment_text: str, source: str = "segment"
    ) -> Optional[EvidenceSpan]:
        """Resolve `quote`, advancing this cursor's position for `quote`."""
        search_from = self._next_search_from.get(quote, 0)
        evidence = resolve_evidence(quote, segment_text, source, search_from)
        if evidence is not None:
            self._next_search_from[quote] = evidence.end_char
        return evidence


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
    event_ids = {e.event_id for e in annotation.events}

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

    relation_buckets = [
        (annotation.relations, False),
        (annotation.weakly_inferred_relations, True),
    ]
    for bucket, is_weakly_inferred_bucket in relation_buckets:
        for relation in bucket:
            span_error = relation.evidence.validate(segment_text)
            if span_error:
                errors.append(f"relation {relation.relation_id!r}: {span_error}")
            if relation.source_event_id not in event_ids:
                errors.append(
                    f"relation {relation.relation_id!r} references unknown "
                    f"source event {relation.source_event_id!r}"
                )
            if relation.target_event_id not in event_ids:
                errors.append(
                    f"relation {relation.relation_id!r} references unknown "
                    f"target event {relation.target_event_id!r}"
                )
            is_weakly_inferred_certainty = relation.certainty == "weakly_inferred"
            if is_weakly_inferred_certainty != is_weakly_inferred_bucket:
                errors.append(
                    f"relation {relation.relation_id!r} has certainty "
                    f"{relation.certainty!r} but is stored in the "
                    f"{'weakly_inferred_relations' if is_weakly_inferred_bucket else 'relations'} "
                    "list"
                )

    for speech_act in annotation.speech_acts:
        span_error = speech_act.evidence.validate(segment_text)
        if span_error:
            errors.append(f"speech act {speech_act.speech_act_id!r}: {span_error}")
        if (
            speech_act.speaker_entity_id
            and speech_act.speaker_entity_id not in entity_ids
        ):
            errors.append(
                f"speech act {speech_act.speech_act_id!r} references unknown "
                f"speaker entity {speech_act.speaker_entity_id!r}"
            )
        for addressee_id in speech_act.addressee_entity_ids:
            if addressee_id not in entity_ids:
                errors.append(
                    f"speech act {speech_act.speech_act_id!r} references "
                    f"unknown addressee entity {addressee_id!r}"
                )
        if speech_act.linked_event_id and speech_act.linked_event_id not in event_ids:
            errors.append(
                f"speech act {speech_act.speech_act_id!r} references unknown "
                f"linked event {speech_act.linked_event_id!r}"
            )

    for explanation in annotation.explanations:
        span_error = explanation.evidence.validate(segment_text)
        if span_error:
            errors.append(f"explanation {explanation.explanation_id!r}: {span_error}")
        for eid in explanation.linked_entity_ids:
            if eid not in entity_ids:
                errors.append(
                    f"explanation {explanation.explanation_id!r} references "
                    f"unknown entity {eid!r}"
                )
        for evid in explanation.linked_event_ids:
            if evid not in event_ids:
                errors.append(
                    f"explanation {explanation.explanation_id!r} references "
                    f"unknown event {evid!r}"
                )

    for tag in annotation.sf_tags:
        span_error = tag.evidence.validate(segment_text)
        if span_error:
            errors.append(f"SF tag {tag.tag_id!r}: {span_error}")
        for eid in tag.linked_entity_ids:
            if eid not in entity_ids:
                errors.append(
                    f"SF tag {tag.tag_id!r} references unknown entity {eid!r}"
                )
        for evid in tag.linked_event_ids:
            if evid not in event_ids:
                errors.append(
                    f"SF tag {tag.tag_id!r} references unknown event {evid!r}"
                )

    return errors


@dataclasses.dataclass
class StoryWorldAnnotation:
    """Story-level reconciliation of per-segment Event-Role-World annotations.

    Reconciles entities across segment boundaries (same canonical name,
    case-insensitively, is treated as the same real-world entity) and
    re-qualifies relations with story-scoped event IDs, since Event IDs are
    only unique within one segment. This is the executable story-level
    reconciliation the proposal requires beyond just holding per-segment
    results in a list — see reconcile_story_annotations().

    Attributes:
        story_id: Identifier for the story these segments belong to.
        segment_annotations: The per-segment annotations, in segment order.
        entities: Reconciled entities, one per distinct canonical name
            (case-insensitive) observed across all segments. entity_id on
            each is a story-scoped global ID (e.g. "global_e0").
        entity_alias_map: Maps "{segment_id}:{local_entity_id}" to the
            reconciled global entity_id, so callers can translate a
            per-segment entity reference into the story-level entity.
        relations: All relations (main + weakly_inferred) across every
            segment, with source_event_id/target_event_id re-qualified to
            "{segment_id}:{local_event_id}" so they remain unambiguous at
            story scope (event IDs are otherwise only unique per segment).
        validation_errors: Story-level validation failures (see
            validate_story_annotation).
    """

    story_id: Any
    segment_annotations: List[SegmentWorldAnnotation] = dataclasses.field(
        default_factory=list
    )
    entities: List[Entity] = dataclasses.field(default_factory=list)
    entity_alias_map: Dict[str, str] = dataclasses.field(default_factory=dict)
    relations: List[EventRelation] = dataclasses.field(default_factory=list)
    validation_errors: List[str] = dataclasses.field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "story_id": self.story_id,
            "segment_annotations": [a.to_dict() for a in self.segment_annotations],
            "entities": [e.to_dict() for e in self.entities],
            "entity_alias_map": dict(self.entity_alias_map),
            "relations": [r.to_dict() for r in self.relations],
            "validation_errors": self.validation_errors,
        }


def reconcile_story_annotations(
    story_id: Any, segment_annotations: List[SegmentWorldAnnotation]
) -> StoryWorldAnnotation:
    """Reconcile per-segment annotations into one story-level annotation.

    Args:
        story_id: Identifier for the story.
        segment_annotations: Per-segment annotations, in segment order.

    Returns:
        A StoryWorldAnnotation with entities merged across segments by
        case-insensitive canonical_name (a simple, deterministic alias
        heuristic — not full coreference resolution, which remains the
        existing scene/sequel substrate's job, not this pipeline's), and
        every relation re-qualified with segment-scoped event IDs.

    Merging is deterministic given the same input: entities are visited in
    segment order, then within-segment list order, and the first-seen
    canonical_name (case-insensitively) for a given normalized key becomes
    the reconciled entity's canonical_name. Running this function twice on
    the same input produces identical global_entity_ids and ordering.
    """
    entities_by_key: Dict[str, Entity] = {}
    entity_alias_map: Dict[str, str] = {}
    relations: List[EventRelation] = []

    for segment in segment_annotations:
        for entity in segment.entities:
            key = entity.canonical_name.strip().lower()
            if key not in entities_by_key:
                global_id = f"global_e{len(entities_by_key)}"
                entities_by_key[key] = Entity(
                    entity_id=global_id,
                    canonical_name=entity.canonical_name,
                    entity_type=entity.entity_type,
                    aliases=list(entity.aliases),
                    actant_roles=list(entity.actant_roles),
                    confidence=entity.confidence,
                )
            else:
                merged = entities_by_key[key]
                for alias in entity.aliases:
                    if alias not in merged.aliases:
                        merged.aliases.append(alias)
                for role in entity.actant_roles:
                    if role not in merged.actant_roles:
                        merged.actant_roles.append(role)
                merged.confidence = max(merged.confidence, entity.confidence)
            entity_alias_map[f"{segment.segment_id}:{entity.entity_id}"] = (
                entities_by_key[key].entity_id
            )

        for relation in segment.relations + segment.weakly_inferred_relations:
            relations.append(
                dataclasses.replace(
                    relation,
                    source_event_id=f"{segment.segment_id}:{relation.source_event_id}",
                    target_event_id=f"{segment.segment_id}:{relation.target_event_id}",
                )
            )

    story = StoryWorldAnnotation(
        story_id=story_id,
        segment_annotations=list(segment_annotations),
        entities=list(entities_by_key.values()),
        entity_alias_map=entity_alias_map,
        relations=relations,
    )
    story.validation_errors = validate_story_annotation(story)
    return story


def validate_story_annotation(story: StoryWorldAnnotation) -> List[str]:
    """Validate story-level ID resolution for a StoryWorldAnnotation.

    Per the proposal's Artifact validation section: all entity/event/
    relation IDs must resolve, and causal links must carry evidence and
    certainty (already enforced by EventRelation's required fields — this
    checks that every relation's referenced qualified event ID actually
    corresponds to a real event in some segment).

    Args:
        story: The StoryWorldAnnotation to validate.

    Returns:
        A list of human-readable error strings; empty if valid.
    """
    errors: List[str] = []

    qualified_event_ids = {
        f"{segment.segment_id}:{event.event_id}"
        for segment in story.segment_annotations
        for event in segment.events
    }
    global_entity_ids = {e.entity_id for e in story.entities}

    for relation in story.relations:
        if relation.source_event_id not in qualified_event_ids:
            errors.append(
                f"story relation {relation.relation_id!r} references unknown "
                f"source event {relation.source_event_id!r}"
            )
        if relation.target_event_id not in qualified_event_ids:
            errors.append(
                f"story relation {relation.relation_id!r} references unknown "
                f"target event {relation.target_event_id!r}"
            )

    for alias_key, global_id in story.entity_alias_map.items():
        if global_id not in global_entity_ids:
            errors.append(
                f"entity_alias_map entry {alias_key!r} references unknown "
                f"global entity {global_id!r}"
            )

    return errors
