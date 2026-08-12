"""Event-Role-World object schemas for extractor stages 1-9.

Implements the object responsibilities sketched in the governing proposal's
"Core schema sketch" (project/design/proposals/proposed/
lcats-event-role-world-extractor/00_proposal.md): entities/participants,
events/semantic roles, temporal/spatial anchors (WI-EVENT-0024); relations,
speech acts, explanation discourse, and SF world-model tags (WI-EVENT-0026);
the optional stage-8 hypothesis object (belief/uncertainty/perspective/
emotion) (WI-EVENT-0027); and the story-level cross-segment relation pass
(WI-EVENT-0029).
"""

from __future__ import annotations

import dataclasses

from typing import Any, Dict, List, Optional

_MALFORMED_ITEM_REPR_MAX_CHARS = 200


def describe_malformed_item(path: str, item: Any) -> str:
    """Return a one-line description of a non-dict tool-result array item.

    Used by every build_*() function in this package (entity_extractor,
    event_extractor, relation_extractor, discourse_extractor,
    story_relation_extractor, hypothesis_extractor) at each array-item
    site where the tool result is iterated - see WI-EVENT-0032. A
    malformed item is skipped rather than crashing (the
    AttributeError: 'str' object has no attribute 'get' class of bug this
    guards against), but the skip must still surface as an explicit
    extraction error, not silently read as a clean, complete result -
    see this repo's ERW pipeline structured-output reliability audit,
    Category B.

    Args:
        path: Dotted/bracketed location of the item, e.g.
            "entities[2]" or "entities[0].mentions[1]".
        item: The malformed item itself (any non-dict value).

    Returns:
        A single-line string naming the path, the item's actual type, and
        a truncated repr - long enough to diagnose, short enough not to
        flood a log with a multi-kilobyte truncated-JSON string (the
        actual failure mode this was built to describe).
    """
    item_repr = repr(item)
    if len(item_repr) > _MALFORMED_ITEM_REPR_MAX_CHARS:
        item_repr = item_repr[:_MALFORMED_ITEM_REPR_MAX_CHARS] + "...<truncated>"
    return f"{path} is not an object (got {type(item).__name__}): {item_repr}"


def coerce_list_field(value: Any, path: str, item_errors: List[str]) -> list:
    """Normalize a tool-result field expected to be an array to a list.

    Companion guard to describe_malformed_item(), one level up: that
    function handles a malformed *item* inside an array; this one handles
    a malformed *container* - the field itself not being an array at all.
    Every build_*() call site in this package used to write
    `enumerate(tool_result.get(field) or [])` directly, which relies on
    `or []` substituting a default only when the value is falsy. A
    non-empty string is truthy, so a string returned in place of an
    expected array was iterated character-by-character, and each
    resulting character then failed the caller's own
    `isinstance(raw, dict)` check (the guard describe_malformed_item()'s
    message describes, but does not itself perform) - hundreds of bogus
    per-character errors from one malformed field (see WI-EVENT-0061).
    This function centralizes the fix: a present-but-non-list value
    records one clear error here instead.

    Args:
        value: The raw field value, e.g. tool_result.get("entities") or
            raw_entity.get("mentions") - not yet defaulted with `or []`.
        path: Dotted/bracketed location of the field, e.g. "entities" or
            "entities[0].mentions".
        item_errors: The caller's error-collection list; a container-level
            error is appended to it in place, matching how callers already
            collect per-item errors from describe_malformed_item().

    Returns:
        `value` itself if it is already a list; `[]` with no error if the
        field is genuinely absent (`None` - a missing key or an explicit
        JSON `null`); `[]` with one error appended to `item_errors` for
        any other non-list value, **including a falsy one** (`""`, `0`,
        `False`, `{}`) - those are still present-but-wrong, not absent,
        and must not silently pass as an empty-but-valid result (review
        finding, PR #274: the prior `if not value` check conflated
        "missing" with "falsy," letting a malformed `""`/`{}`/`0` value
        through with no recorded error at all).
    """
    if value is None:
        return []
    if not isinstance(value, list):
        item_errors.append(f"{path} is not an array (got {type(value).__name__})")
        return []
    return value


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
class Hypothesis:
    """An optional belief, uncertainty, perspective, or emotion/appraisal claim.

    Per the proposal's fact/hypothesis distinction and risk table
    ("confusing interpretive hypotheses with extractive facts"), a
    Hypothesis is never an extractive fact even when confidently stated —
    it is kept in its own field on SegmentWorldAnnotation
    (`hypotheses`), separate from every extractive layer, and callers must
    opt in explicitly to include it in any quantitative reporting (see
    baseline.py's own hypotheses_per_1000_words, reported alongside but
    never merged into the extractive-layer rates).

    Attributes:
        hypothesis_type: One of "belief", "uncertainty", "perspective", or
            "emotion_appraisal".
        subject_entity_id: Optional entity ID the hypothesis is about or
            attributed to (e.g. who holds the belief/perspective).
        proposition_or_target: The claim's content in free text — a
            proposition (for belief/uncertainty) or a target (for
            perspective/emotion_appraisal).
        linked_entity_ids: Other entities referenced by the hypothesis.
        linked_event_ids: Events referenced by the hypothesis.
    """

    hypothesis_id: str
    hypothesis_type: str
    proposition_or_target: str
    evidence: EvidenceSpan
    subject_entity_id: Optional[str] = None
    linked_entity_ids: List[str] = dataclasses.field(default_factory=list)
    linked_event_ids: List[str] = dataclasses.field(default_factory=list)
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "hypothesis_type": self.hypothesis_type,
            "proposition_or_target": self.proposition_or_target,
            "evidence": self.evidence.to_dict(),
            "subject_entity_id": self.subject_entity_id,
            "linked_entity_ids": self.linked_entity_ids,
            "linked_event_ids": self.linked_event_ids,
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
        hypotheses: Hypothesis instances extracted by the optional stage-8
            hypothesis pass — belief, uncertainty, perspective, or
            emotion/appraisal claims, never extractive facts.
        extraction_errors: Backend/API-level failures (e.g. a transient
            provider error, an empty tool result) for any LLM-backed pass
            on this segment. Distinct from validation_errors: an
            extraction_error means a pass may not have run at all — its
            "zero results" must not be read as "the pass ran and found
            nothing."
        structured_extraction_errors: The subset of extraction_errors that
            originated as a structured api_error dict (from
            llm_extractor.JSONPromptExtractor._classify_api_error) rather
            than an item-level string description - carrying its
            category/can_retry/should_abort_batch fields so a caller can
            act on them directly instead of re-deriving fatality by
            substring-matching extraction_errors' plain-text messages
            (WI-EVENT-0032). Purely additive: extraction_errors keeps
            every failure as a human-readable string as before; this list
            is a parallel, structured view of the ones that have one.
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
    hypotheses: List[Hypothesis] = dataclasses.field(default_factory=list)
    extraction_errors: List[str] = dataclasses.field(default_factory=list)
    structured_extraction_errors: List[Dict[str, Any]] = dataclasses.field(
        default_factory=list
    )
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
            "hypotheses": [h.to_dict() for h in self.hypotheses],
            "extraction_errors": self.extraction_errors,
            "structured_extraction_errors": self.structured_extraction_errors,
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

    for hypothesis in annotation.hypotheses:
        span_error = hypothesis.evidence.validate(segment_text)
        if span_error:
            errors.append(f"hypothesis {hypothesis.hypothesis_id!r}: {span_error}")
        if (
            hypothesis.subject_entity_id
            and hypothesis.subject_entity_id not in entity_ids
        ):
            errors.append(
                f"hypothesis {hypothesis.hypothesis_id!r} references unknown "
                f"subject entity {hypothesis.subject_entity_id!r}"
            )
        for eid in hypothesis.linked_entity_ids:
            if eid not in entity_ids:
                errors.append(
                    f"hypothesis {hypothesis.hypothesis_id!r} references "
                    f"unknown entity {eid!r}"
                )
        for evid in hypothesis.linked_event_ids:
            if evid not in event_ids:
                errors.append(
                    f"hypothesis {hypothesis.hypothesis_id!r} references "
                    f"unknown event {evid!r}"
                )

    return errors


@dataclasses.dataclass
class StoryWorldAnnotation:
    """Story-level reconciliation of per-segment Event-Role-World annotations.

    Reconciles entities across segment boundaries (matching on canonical
    name OR any alias, case-insensitively — see reconcile_story_annotations)
    and re-qualifies relations with story-scoped event IDs, since Event IDs
    are only unique within one segment. This is the executable story-level
    reconciliation the proposal requires beyond just holding per-segment
    results in a list — see reconcile_story_annotations().

    Known limitation, now resolved by WI-EVENT-0029's story-level relation
    pass: prior to that work item, relation qualification here only made
    segment-local relations safely representable at story scope — it did
    not, and could not, discover genuinely cross-segment causal relations
    (cause in one segment, effect in another), since stage 6's
    relation_extractor only ever receives its own segment's event IDs, so
    a relation's source_event_id/target_event_id could never actually
    reference a different segment's event. Every relation this function
    qualifies is, by construction, entirely local to the one segment it
    came from — genuinely cross-segment relations are discovered by a
    separate story-level pass (see cross_segment_relations below) and kept
    in their own field rather than merged into `relations`, so the two
    lists can never collide on relation_id and no deduplication logic is
    needed to combine their counts.

    Attributes:
        story_id: Identifier for the story these segments belong to.
        segment_annotations: The per-segment annotations, in segment order.
        entities: Reconciled entities, one per distinct real-world entity
            inferred by matching canonical names/aliases across segments
            (see reconcile_story_annotations). entity_id on each is a
            story-scoped global ID (e.g. "global_e0").
        entity_alias_map: Maps "{segment_id}:{local_entity_id}" to the
            reconciled global entity_id, so callers can translate a
            per-segment entity reference into the story-level entity.
        relations: All same-segment relations (main + weakly_inferred)
            across every segment, with source_event_id/target_event_id
            re-qualified to "{segment_id}:{local_event_id}" so they remain
            unambiguous at story scope (event IDs are otherwise only
            unique per segment).
        cross_segment_relations: Genuinely cross-segment relations
            (certainty "explicit" or "strongly_implied") discovered by the
            story-level pass (WI-EVENT-0029), whose source_event_id and
            target_event_id belong to two different segments. Kept
            separate from `relations` — never merged into it — so the two
            lists are disjoint by construction and can be summed for a
            density metric without any relation_id deduplication.
        weakly_inferred_cross_segment_relations: The weakly_inferred-
            certainty counterpart to cross_segment_relations, partitioned
            separately per the same causality tradeoff table that splits
            `relations`/`weakly_inferred_relations` at segment scope.
        extraction_errors: Backend/API-level failures for the story-level
            pass (e.g. a transient provider error, an empty tool result).
            Distinct from validation_errors: an extraction_error means the
            story-level pass may not have run at all — its "zero results"
            must not be read as "the pass ran and found nothing."
        structured_extraction_errors: The subset of extraction_errors that
            originated as a structured api_error dict, mirroring
            SegmentWorldAnnotation.structured_extraction_errors at story
            scope (WI-EVENT-0032).
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
    cross_segment_relations: List[EventRelation] = dataclasses.field(
        default_factory=list
    )
    weakly_inferred_cross_segment_relations: List[EventRelation] = dataclasses.field(
        default_factory=list
    )
    extraction_errors: List[str] = dataclasses.field(default_factory=list)
    structured_extraction_errors: List[Dict[str, Any]] = dataclasses.field(
        default_factory=list
    )
    validation_errors: List[str] = dataclasses.field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "story_id": self.story_id,
            "segment_annotations": [a.to_dict() for a in self.segment_annotations],
            "entities": [e.to_dict() for e in self.entities],
            "entity_alias_map": dict(self.entity_alias_map),
            "relations": [r.to_dict() for r in self.relations],
            "cross_segment_relations": [
                r.to_dict() for r in self.cross_segment_relations
            ],
            "weakly_inferred_cross_segment_relations": [
                r.to_dict() for r in self.weakly_inferred_cross_segment_relations
            ],
            "extraction_errors": self.extraction_errors,
            "structured_extraction_errors": self.structured_extraction_errors,
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
        case-insensitive name matching (a simple, deterministic alias
        heuristic — not full coreference resolution, which remains the
        existing scene/sequel substrate's job, not this pipeline's), and
        every relation re-qualified with segment-scoped event IDs.

    Merging matches an incoming entity against any *previously seen* name
    for an existing global entity — its own canonical_name or any of its
    aliases, case-insensitively — not canonical_name alone. This handles
    the case where the same participant is given a different canonical
    name across segments (e.g. canonical "Elizabeth" in one segment, then
    canonical "Liz" with alias "Elizabeth" in another): matching on
    canonical_name alone would never notice the alias overlap and would
    fragment the two into separate global entities.

    Every alias/canonical name an entity has ever been merged under is
    registered so later segments can match through any of them — this
    only extends transitively forward (a name becomes matchable once
    something using it has been merged), it does not retroactively
    reconcile two already-created global entities that turn out to share
    a name only discovered later.

    Merged entities also carry segment-qualified mention IDs
    ("{segment_id}:{local_mention_id}") rather than dropping them, so
    story.entities[i].mention_ids stays traceable back to
    segment_annotations[*].mentions — the qualification avoids collisions
    since mention IDs, like entity/event IDs, are only unique per segment.

    Merging is deterministic given the same input: entities are visited in
    segment order, then within-segment list order, name-lookup order is a
    list (canonical_name first, then aliases in order) rather than set
    iteration, and the first-seen canonical_name for a given matched global
    entity becomes its canonical_name. Running this function twice on the
    same input produces identical global_entity_ids and ordering.
    """
    entities_by_global_id: Dict[str, Entity] = {}
    name_to_global_id: Dict[str, str] = {}
    entity_alias_map: Dict[str, str] = {}
    relations: List[EventRelation] = []

    for segment in segment_annotations:
        for entity in segment.entities:
            candidate_names = [entity.canonical_name.strip().lower()] + [
                alias.strip().lower() for alias in entity.aliases
            ]

            global_id = None
            for name in candidate_names:
                if name in name_to_global_id:
                    global_id = name_to_global_id[name]
                    break

            qualified_mention_ids = [
                f"{segment.segment_id}:{mid}" for mid in entity.mention_ids
            ]

            if global_id is None:
                global_id = f"global_e{len(entities_by_global_id)}"
                entities_by_global_id[global_id] = Entity(
                    entity_id=global_id,
                    canonical_name=entity.canonical_name,
                    entity_type=entity.entity_type,
                    aliases=list(entity.aliases),
                    mention_ids=list(qualified_mention_ids),
                    actant_roles=list(entity.actant_roles),
                    confidence=entity.confidence,
                )
            else:
                merged = entities_by_global_id[global_id]
                new_aliases = list(entity.aliases)
                if entity.canonical_name != merged.canonical_name:
                    new_aliases.append(entity.canonical_name)
                for alias in new_aliases:
                    if alias not in merged.aliases:
                        merged.aliases.append(alias)
                for mid in qualified_mention_ids:
                    if mid not in merged.mention_ids:
                        merged.mention_ids.append(mid)
                for role in entity.actant_roles:
                    if role not in merged.actant_roles:
                        merged.actant_roles.append(role)
                merged.confidence = max(merged.confidence, entity.confidence)

            for name in candidate_names:
                name_to_global_id[name] = global_id
            entity_alias_map[f"{segment.segment_id}:{entity.entity_id}"] = global_id

        # Every relation qualified here is, by construction, entirely
        # local to `segment`: stage 6's relation_extractor only ever
        # receives this segment's own event IDs (see relation_extractor.py
        # and processor.py's per-segment placeholder interpolation), so
        # relation.source_event_id/target_event_id can never actually
        # reference a different segment's event. Qualifying both endpoints
        # with `segment.segment_id` is therefore correct for every relation
        # this pipeline can produce today — see the "Known limitation" note
        # on StoryWorldAnnotation for what this does not do (discover
        # genuinely cross-segment causal relations).
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
        entities=list(entities_by_global_id.values()),
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
    corresponds to a real event in some segment). Also validates
    cross_segment_relations/weakly_inferred_cross_segment_relations (the
    story-level pass's own output, WI-EVENT-0029): endpoint ID resolution,
    certainty/bucket consistency (mirroring validate_segment_annotation's
    same check for segment-level relations), relation_id uniqueness against
    every other relation on this story (defense in depth — the two fields
    are populated from a disjoint source and should never collide), and
    that source/target genuinely belong to different segments, since a
    same-segment link here would indicate the story-level pass violated its
    own scope.

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

    seen_relation_ids = {r.relation_id for r in story.relations}
    cross_segment_buckets = [
        (story.cross_segment_relations, False),
        (story.weakly_inferred_cross_segment_relations, True),
    ]
    for bucket, is_weakly_inferred_bucket in cross_segment_buckets:
        for relation in bucket:
            if relation.relation_id in seen_relation_ids:
                errors.append(
                    f"cross-segment relation {relation.relation_id!r} collides "
                    "with another relation ID on this story"
                )
            seen_relation_ids.add(relation.relation_id)

            if relation.source_event_id not in qualified_event_ids:
                errors.append(
                    f"cross-segment relation {relation.relation_id!r} references "
                    f"unknown source event {relation.source_event_id!r}"
                )
            if relation.target_event_id not in qualified_event_ids:
                errors.append(
                    f"cross-segment relation {relation.relation_id!r} references "
                    f"unknown target event {relation.target_event_id!r}"
                )

            source_segment_id = relation.source_event_id.split(":", 1)[0]
            target_segment_id = relation.target_event_id.split(":", 1)[0]
            if source_segment_id == target_segment_id:
                errors.append(
                    f"cross-segment relation {relation.relation_id!r} has "
                    f"source and target both in segment {source_segment_id!r} "
                    "— not a genuine cross-segment link"
                )

            is_weakly_inferred_certainty = relation.certainty == "weakly_inferred"
            if is_weakly_inferred_certainty != is_weakly_inferred_bucket:
                errors.append(
                    f"cross-segment relation {relation.relation_id!r} has "
                    f"certainty {relation.certainty!r} but is stored in the "
                    f"{'weakly_inferred_cross_segment_relations' if is_weakly_inferred_bucket else 'cross_segment_relations'} "
                    "list"
                )

    return errors
