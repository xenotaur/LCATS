"""Pipeline orchestration for Event-Role-World extractor stages 1-9.

Stage 1 (input contract) reuses the existing segment/evidence substrate
(lcats.analysis.story_processors, lcats.analysis.text_segmenter) rather than
reimplementing segmentation — this module accepts already-produced segments
(scene/sequel, or fixed_chunk from baseline.py) and runs stages 2-8 over
each one's sliced text, then stage 9's story-level reconciliation over the
resulting segment annotations, followed by the optional story-level
cross-segment relation pass (WI-EVENT-0029) that runs once per story rather
than once per segment.
"""

from __future__ import annotations

import dataclasses
import time

from typing import Any, Dict, List, Optional

from lcats.analysis.event_role_world import (
    discourse_extractor as discourse_extractor_module,
)
from lcats.analysis.event_role_world import entity_extractor as entity_extractor_module
from lcats.analysis.event_role_world import event_extractor as event_extractor_module
from lcats.analysis.event_role_world import (
    hypothesis_extractor as hypothesis_extractor_module,
)
from lcats.analysis.event_role_world import nlp_backend as nlp_backend_module
from lcats.analysis.event_role_world import (
    relation_extractor as relation_extractor_module,
)
from lcats.analysis.event_role_world import schema
from lcats.analysis.event_role_world import surface_feature_extractor
from lcats.analysis.event_role_world import (
    story_relation_extractor as story_relation_extractor_module,
)


@dataclasses.dataclass
class PassUsage:
    """Cost/usage record for one annotator pass on one segment.

    Per the governing proposal's Cost and baseline requirements: call
    counts alone do not make cost/latency visible, so this records token
    counts, model, and elapsed time for every LLM-backed pass, and marks
    NLP-only passes explicitly so they are not miscounted as free.
    """

    segment_id: Any
    pass_name: str
    is_llm_backed: bool
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    elapsed_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


def process_segment(
    segment_id: Any,
    segment_text: str,
    *,
    nlp_backend: nlp_backend_module.NLPBackend,
    nlp_backend_name: str,
    entity_llm_extractor: Any,
    event_llm_extractor: Any,
    relation_llm_extractor: Any,
    discourse_llm_extractor: Any,
    hypothesis_llm_extractor: Any,
    include_hypotheses: bool = True,
) -> "tuple[schema.SegmentWorldAnnotation, List[PassUsage]]":
    """Run stages 2-8 over one segment's text.

    Args:
        segment_id: The segment's ID, carried through to the annotation.
        segment_text: The exact text of this segment (story_text sliced by
            the segment's start_char/end_char).
        nlp_backend: NLPBackend for stage 2 (surface features).
        nlp_backend_name: Label recorded on the SurfaceFeatures result and
            usage records (e.g. "stanza", "spacy").
        entity_llm_extractor: A JSONPromptExtractor configured via
            entity_extractor.make_entity_extractor.
        event_llm_extractor: A JSONPromptExtractor configured via
            event_extractor.make_event_extractor.
        relation_llm_extractor: A JSONPromptExtractor configured via
            relation_extractor.make_relation_extractor.
        discourse_llm_extractor: A JSONPromptExtractor configured via
            discourse_extractor.make_discourse_extractor.
        hypothesis_llm_extractor: A JSONPromptExtractor configured via
            hypothesis_extractor.make_hypothesis_extractor.
        include_hypotheses: Whether to run stage 8 at all. Stage 8 is
            optional per the proposal — defaulting this to True preserves
            this function's existing behavior for current callers, but
            callers that only need the extractive pipeline can pass False
            to skip the extra LLM request, its cost/latency, and having a
            hypothesis-provider failure appear in extraction_errors for a
            layer they never opted into.

    Returns:
        (annotation, usage_records) — annotation.validation_errors is
        populated by schema.validate_segment_annotation before returning.
    """
    usage_records: List[PassUsage] = []

    # Stage 2: surface features (NLP-only, not LLM-backed).
    t0 = time.monotonic()
    surface_features = surface_feature_extractor.extract_surface_features(
        segment_text, nlp_backend, backend_name=nlp_backend_name
    )
    usage_records.append(
        PassUsage(
            segment_id=segment_id,
            pass_name="surface_feature",
            is_llm_backed=False,
            model=nlp_backend_name,
            elapsed_seconds=time.monotonic() - t0,
        )
    )

    extraction_errors: List[str] = []
    structured_extraction_errors: List[Dict[str, Any]] = []

    # Stage 3: entities/participants (LLM-backed).
    t0 = time.monotonic()
    entity_result = entity_llm_extractor.extract(segment_text)
    usage_records.append(
        _pass_usage_from_extraction(segment_id, "entity", entity_result, t0)
    )
    entity_error = entity_result.get("api_error") or entity_result.get(
        "extraction_error"
    )
    if entity_error:
        # A failed entity pass must not silently read as "zero entities
        # found" — an empty result here is meaningfully different from an
        # extraction that never ran/succeeded.
        _record_extraction_error(
            extraction_errors, structured_extraction_errors, "entity", entity_error
        )
    entities, mentions, entity_item_errors = entity_extractor_module.build_entities(
        entity_result.get("extracted_output") or {}, segment_text
    )
    extraction_errors.extend(entity_item_errors)

    # Stages 4-5: events/semantic-roles + temporal/spatial anchors (LLM-backed).
    # JSONPromptExtractor.extract() only substitutes {story_text}/
    # {indexed_story_text}; entity IDs are interpolated via a dedicated
    # helper that still routes through extract() (see
    # _extract_with_placeholders), so this makes exactly one backend
    # call, not two, and keeps extract()'s exception/api_error handling
    # intact rather than letting a transient failure abort process_segments
    # for every remaining segment.
    entity_ids = [e.entity_id for e in entities]
    t0 = time.monotonic()
    event_result = _extract_with_placeholders(
        event_llm_extractor, segment_text, {"entity_ids": entity_ids}
    )
    usage_records.append(
        _pass_usage_from_extraction(segment_id, "event_anchor", event_result, t0)
    )
    event_error = event_result.get("api_error") or event_result.get("extraction_error")
    if event_error:
        _record_extraction_error(
            extraction_errors,
            structured_extraction_errors,
            "event/anchor",
            event_error,
        )
    events, temporal_anchors, spatial_anchors, event_item_errors = (
        event_extractor_module.build_events_and_anchors(
            event_result.get("extracted_output") or {}, segment_text
        )
    )
    extraction_errors.extend(event_item_errors)

    # Stage 6: relations between events (LLM-backed). Same routed-through-
    # extract() pattern as the event/anchor pass, so a transient failure is
    # caught and recorded rather than aborting process_segments().
    event_ids = [e.event_id for e in events]
    t0 = time.monotonic()
    relation_result = _extract_with_placeholders(
        relation_llm_extractor, segment_text, {"event_ids": event_ids}
    )
    usage_records.append(
        _pass_usage_from_extraction(segment_id, "relation", relation_result, t0)
    )
    relation_error = relation_result.get("api_error") or relation_result.get(
        "extraction_error"
    )
    if relation_error:
        _record_extraction_error(
            extraction_errors,
            structured_extraction_errors,
            "relation",
            relation_error,
        )
    relations, weakly_inferred_relations, relation_item_errors = (
        relation_extractor_module.build_relations(
            relation_result.get("extracted_output") or {}, segment_text
        )
    )
    extraction_errors.extend(relation_item_errors)

    # Stage 7: speech acts, explanations, and SF world-model tags (LLM-backed).
    t0 = time.monotonic()
    discourse_result = _extract_with_placeholders(
        discourse_llm_extractor,
        segment_text,
        {"entity_ids": entity_ids, "event_ids": event_ids},
    )
    usage_records.append(
        _pass_usage_from_extraction(segment_id, "discourse", discourse_result, t0)
    )
    discourse_error = discourse_result.get("api_error") or discourse_result.get(
        "extraction_error"
    )
    if discourse_error:
        _record_extraction_error(
            extraction_errors,
            structured_extraction_errors,
            "discourse",
            discourse_error,
        )
    speech_acts, explanations, sf_tags, discourse_item_errors = (
        discourse_extractor_module.build_discourse(
            discourse_result.get("extracted_output") or {}, segment_text
        )
    )
    extraction_errors.extend(discourse_item_errors)

    # Stage 8 (optional): belief, uncertainty, perspective, and emotion/
    # appraisal hypotheses (LLM-backed). Same routed-through-extract()
    # pattern as every other pass. Only runs at all if the caller opted in
    # via include_hypotheses — stage 8 is optional per the proposal, so a
    # caller that never requested it should not pay its LLM cost/latency,
    # nor have a hypothesis-provider failure surface in extraction_errors.
    hypotheses: List[schema.Hypothesis] = []
    if include_hypotheses:
        t0 = time.monotonic()
        hypothesis_result = _extract_with_placeholders(
            hypothesis_llm_extractor,
            segment_text,
            {"entity_ids": entity_ids, "event_ids": event_ids},
        )
        usage_records.append(
            _pass_usage_from_extraction(segment_id, "hypothesis", hypothesis_result, t0)
        )
        hypothesis_error = hypothesis_result.get("api_error") or hypothesis_result.get(
            "extraction_error"
        )
        if hypothesis_error:
            _record_extraction_error(
                extraction_errors,
                structured_extraction_errors,
                "hypothesis",
                hypothesis_error,
            )
        hypotheses, hypothesis_item_errors = (
            hypothesis_extractor_module.build_hypotheses(
                hypothesis_result.get("extracted_output") or {}, segment_text
            )
        )
        extraction_errors.extend(hypothesis_item_errors)

    annotation = schema.SegmentWorldAnnotation(
        segment_id=segment_id,
        surface_features=surface_features,
        entities=entities,
        mentions=mentions,
        events=events,
        temporal_anchors=temporal_anchors,
        spatial_anchors=spatial_anchors,
        relations=relations,
        weakly_inferred_relations=weakly_inferred_relations,
        speech_acts=speech_acts,
        explanations=explanations,
        sf_tags=sf_tags,
        hypotheses=hypotheses,
        extraction_errors=extraction_errors,
        structured_extraction_errors=structured_extraction_errors,
    )
    annotation.validation_errors = schema.validate_segment_annotation(
        annotation, segment_text
    )

    return annotation, usage_records


def _pass_usage_from_extraction(
    segment_id: Any, pass_name: str, extraction_result: Dict[str, Any], t0: float
) -> PassUsage:
    """Build a PassUsage record from a JSONPromptExtractor.extract() result."""
    usage = extraction_result.get("usage") or {}
    return PassUsage(
        segment_id=segment_id,
        pass_name=pass_name,
        is_llm_backed=True,
        model=extraction_result.get("model_name", ""),
        input_tokens=usage.get("input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
        elapsed_seconds=time.monotonic() - t0,
    )


def _record_extraction_error(
    extraction_errors: List[str],
    structured_extraction_errors: List[Dict[str, Any]],
    pass_label: str,
    error: Any,
) -> None:
    """Append a pass failure to both extraction_errors and, when the error
    is a structured api_error dict (from llm_extractor._classify_api_error),
    also to structured_extraction_errors - see
    SegmentWorldAnnotation.structured_extraction_errors (WI-EVENT-0032).

    `error` may be a plain string (e.g. "No tool_result returned by
    backend...") or the classified api_error dict; only the latter is
    structured enough to preserve as-is.

    A dict error's own "raw" field can be large (e.g.
    llm_extractor._normalize_api_error sets it to repr(backend_response),
    which can include a full tool_result) - the plain-string
    extraction_errors entry uses only the dict's "message" field, not the
    whole dict, so a single failed pass cannot flood extraction_errors/a
    caller's exclude_reason with megabytes of noise. The full dict
    (including "raw") is still preserved in structured_extraction_errors
    for anyone who needs it. Each structured_extraction_errors entry is
    also tagged with which pass it came from ("pass": pass_label), since
    multiple passes can each contribute an entry and the dict itself
    carries no pass identity of its own.
    """
    if isinstance(error, dict):
        message = error.get("message") or repr(error)
        extraction_errors.append(f"{pass_label} extraction failed: {message}")
        structured_extraction_errors.append({"pass": pass_label, **error})
    else:
        extraction_errors.append(f"{pass_label} extraction failed: {error}")


def _extract_with_placeholders(
    llm_extractor_instance: Any,
    segment_text: str,
    id_placeholders: Dict[str, List[str]],
) -> Dict[str, Any]:
    """Run an extractor with named ID-list placeholders interpolated into the prompt.

    JSONPromptExtractor.extract() only substitutes {story_text}/
    {indexed_story_text} into user_prompt_template. Any other named
    placeholder (e.g. {entity_ids}, {event_ids}) is resolved by temporarily
    replacing it in the template with a literal, comma-joined string
    (leaving {story_text}/{indexed_story_text} intact for extract() to fill
    in as usual), then calling extract() itself — not the backend directly
    — so a transient provider failure or missing tool_result produces the
    same normalized api_error/extraction_error result extract() gives every
    other call, instead of an uncaught exception that would abort
    process_segments() for every remaining segment.

    Args:
        llm_extractor_instance: A JSONPromptExtractor whose
            user_prompt_template contains zero or more of the placeholder
            names in `id_placeholders`.
        segment_text: The segment text to extract from.
        id_placeholders: Maps placeholder name (without braces) to the list
            of IDs to interpolate there, e.g. {"entity_ids": ["e1", "e2"]}.
            A missing/empty list renders as "(none known yet)".

    Returns:
        The dict returned by llm_extractor_instance.extract(segment_text).
    """
    original_template = llm_extractor_instance.user_prompt_template
    template = original_template
    for name, ids in id_placeholders.items():
        ids_text = ", ".join(ids) if ids else "(none known yet)"
        template = template.replace("{" + name + "}", ids_text)
    llm_extractor_instance.user_prompt_template = template
    try:
        return llm_extractor_instance.extract(segment_text)
    finally:
        llm_extractor_instance.user_prompt_template = original_template


def process_segments(
    story_text: str,
    segments: List[Dict[str, Any]],
    *,
    nlp_backend_name: str,
    llm_backend: Any,
    model: Optional[str] = None,
    story_id: Any = None,
    include_hypotheses: bool = True,
    include_cross_segment_relations: bool = True,
) -> Dict[str, Any]:
    """Run stages 2-8 over every segment in `segments`, then reconcile stage 9.

    Args:
        story_text: Full story text; segments are sliced from this by
            start_char/end_char (the stage-1 input contract).
        segments: Segment dicts with segment_id, start_char, end_char (as
            produced by story_processors.make_annotated_segment_extractor,
            or baseline.make_fixed_token_chunks).
        nlp_backend_name: "stanza" or "spacy".
        llm_backend: LLMBackend for the entity/event/relation/discourse/
            hypothesis/story-relation extraction passes.
        model: Optional model override applied to every extractor built
            here, replacing each factory's own hardcoded default (e.g.
            "gpt-4o"). Defaults to None, preserving each factory's own
            default for existing callers. Any non-OpenAI llm_backend
            combined with the default None previously sent an invalid
            model ID on every request (WI-EVENT-0032) -
            experiments/03_cross_segment_relation_pilot/run_pilot.py
            worked around this by building extractors itself; this
            parameter is the source-level fix.
        story_id: Identifier carried onto the reconciled StoryWorldAnnotation.
            Defaults to None if the caller has no natural story ID.
        include_hypotheses: Whether to run the optional stage-8 hypothesis
            pass at all. Defaults to True to preserve existing behavior for
            current callers; pass False to skip the extra LLM request per
            segment entirely (no cost/latency, no hypothesis-provider
            failures in extraction_errors) when only the extractive
            pipeline (stages 1-7 and 9) is needed.
        include_cross_segment_relations: Whether to run the story-level
            cross-segment relation pass (WI-EVENT-0029) after reconciliation.
            Defaults to True; pass False to skip the extra LLM request per
            story entirely when only per-segment relations are needed (e.g.
            a fixed-chunk baseline run where cross-segment context is not
            comparable to the segment run being controlled against). Even
            when True, the pass is skipped (no LLM call, no PassUsage
            record) unless events exist in at least 2 distinct segments,
            since a genuinely cross-segment relation needs events from two
            different segments by definition.

    Returns:
        {"segments": [SegmentWorldAnnotation.to_dict(), ...],
         "usage": [PassUsage.to_dict(), ...],
         "story": StoryWorldAnnotation.to_dict()} — "story" is the stage-9
         story-level reconciliation (alias resolution, cross-segment
         relation qualification) over every segment annotation produced,
         plus the story-level cross-segment relation pass's own output if
         include_cross_segment_relations is True and events exist in at
         least 2 distinct segments.
    """
    nlp_backend = surface_feature_extractor.make_nlp_backend(nlp_backend_name)
    entity_llm_extractor = entity_extractor_module.make_entity_extractor(llm_backend)
    event_llm_extractor = event_extractor_module.make_event_extractor(llm_backend)
    relation_llm_extractor = relation_extractor_module.make_relation_extractor(
        llm_backend
    )
    discourse_llm_extractor = discourse_extractor_module.make_discourse_extractor(
        llm_backend
    )
    hypothesis_llm_extractor = (
        hypothesis_extractor_module.make_hypothesis_extractor(llm_backend)
        if include_hypotheses
        else None
    )
    story_relation_llm_extractor = (
        story_relation_extractor_module.make_story_relation_extractor(llm_backend)
        if include_cross_segment_relations
        else None
    )

    if model is not None:
        for extractor in (
            entity_llm_extractor,
            event_llm_extractor,
            relation_llm_extractor,
            discourse_llm_extractor,
            hypothesis_llm_extractor,
            story_relation_llm_extractor,
        ):
            if extractor is not None:
                extractor.default_model = model

    annotations: List[schema.SegmentWorldAnnotation] = []
    all_usage: List[PassUsage] = []

    for segment in segments:
        start_char = segment.get("start_char")
        end_char = segment.get("end_char")
        if start_char is None or end_char is None:
            continue
        segment_text = story_text[start_char:end_char]

        annotation, usage_records = process_segment(
            segment.get("segment_id"),
            segment_text,
            nlp_backend=nlp_backend,
            nlp_backend_name=nlp_backend_name,
            entity_llm_extractor=entity_llm_extractor,
            event_llm_extractor=event_llm_extractor,
            relation_llm_extractor=relation_llm_extractor,
            discourse_llm_extractor=discourse_llm_extractor,
            hypothesis_llm_extractor=hypothesis_llm_extractor,
            include_hypotheses=include_hypotheses,
        )
        annotations.append(annotation)
        all_usage.extend(usage_records)

    story = schema.reconcile_story_annotations(story_id, annotations)

    # Story-level cross-segment relation pass (optional, WI-EVENT-0029).
    # Runs once per story, after reconciliation has produced the global
    # event index the pass needs — never per segment, since the whole
    # point is discovering links this segment loop cannot see. Skipped
    # entirely (no LLM call, no PassUsage record) unless events exist in at
    # least 2 distinct segments — a genuinely cross-segment relation needs
    # events from two different segments by definition, so a single-segment
    # story (or a multi-segment story where extraction only succeeded in
    # one segment) would guarantee every candidate relation gets discarded
    # by build_story_relations' same-segment check, wasting an LLM call on
    # a result that can only ever be empty.
    segment_ids_with_events = {
        segment.segment_id for segment in annotations if segment.events
    }
    if include_cross_segment_relations and len(segment_ids_with_events) >= 2:
        t0 = time.monotonic()
        event_index_text = story_relation_extractor_module.build_event_index(story)
        story_relation_result = story_relation_llm_extractor.extract(event_index_text)
        all_usage.append(
            _pass_usage_from_extraction(
                "story", "story_relation", story_relation_result, t0
            )
        )
        story_relation_error = story_relation_result.get(
            "api_error"
        ) or story_relation_result.get("extraction_error")
        if story_relation_error:
            # A failed story-relation pass must not silently read as "zero
            # cross-segment relations found" — mirrors the segment-level
            # extraction_errors/validation_errors distinction.
            _record_extraction_error(
                story.extraction_errors,
                story.structured_extraction_errors,
                "story relation",
                story_relation_error,
            )
        (
            cross_segment_relations,
            weakly_inferred_cross_segment_relations,
            story_relation_item_errors,
        ) = story_relation_extractor_module.build_story_relations(
            story_relation_result.get("extracted_output") or {}, story
        )
        story.cross_segment_relations = cross_segment_relations
        story.weakly_inferred_cross_segment_relations = (
            weakly_inferred_cross_segment_relations
        )
        story.extraction_errors.extend(story_relation_item_errors)
        story.validation_errors = schema.validate_story_annotation(story)

    return {
        "segments": [a.to_dict() for a in annotations],
        "usage": [u.to_dict() for u in all_usage],
        "story": story.to_dict(),
    }
