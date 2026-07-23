"""Pipeline orchestration for Event-Role-World extractor stages 1-5.

Stage 1 (input contract) reuses the existing segment/evidence substrate
(lcats.analysis.story_processors, lcats.analysis.text_segmenter) rather than
reimplementing segmentation — this module accepts already-produced segments
(scene/sequel, or fixed_chunk from baseline.py) and runs stages 2-5 over
each one's sliced text.
"""

from __future__ import annotations

import dataclasses
import time

from typing import Any, Dict, List

from lcats.analysis.event_role_world import entity_extractor as entity_extractor_module
from lcats.analysis.event_role_world import event_extractor as event_extractor_module
from lcats.analysis.event_role_world import nlp_backend as nlp_backend_module
from lcats.analysis.event_role_world import schema
from lcats.analysis.event_role_world import surface_feature_extractor


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
) -> "tuple[schema.SegmentWorldAnnotation, List[PassUsage]]":
    """Run stages 2-5 over one segment's text.

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
        extraction_errors.append(f"entity extraction failed: {entity_error}")
    entities, mentions = entity_extractor_module.build_entities(
        entity_result.get("extracted_output") or {}, segment_text
    )

    # Stages 4-5: events/semantic-roles + temporal/spatial anchors (LLM-backed).
    # JSONPromptExtractor.extract() only substitutes {story_text}/
    # {indexed_story_text}; entity IDs are interpolated via a dedicated
    # helper that still routes through extract() (see
    # _extract_events_with_entity_ids), so this makes exactly one backend
    # call, not two, and keeps extract()'s exception/api_error handling
    # intact rather than letting a transient failure abort process_segments
    # for every remaining segment.
    entity_ids = [e.entity_id for e in entities]
    t0 = time.monotonic()
    event_result = _extract_events_with_entity_ids(
        event_llm_extractor, segment_text, entity_ids
    )
    usage_records.append(
        _pass_usage_from_extraction(segment_id, "event_anchor", event_result, t0)
    )
    event_error = event_result.get("api_error") or event_result.get("extraction_error")
    if event_error:
        extraction_errors.append(f"event/anchor extraction failed: {event_error}")
    events, temporal_anchors, spatial_anchors = (
        event_extractor_module.build_events_and_anchors(
            event_result.get("extracted_output") or {}, segment_text
        )
    )

    annotation = schema.SegmentWorldAnnotation(
        segment_id=segment_id,
        surface_features=surface_features,
        entities=entities,
        mentions=mentions,
        events=events,
        temporal_anchors=temporal_anchors,
        spatial_anchors=spatial_anchors,
        extraction_errors=extraction_errors,
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


def _extract_events_with_entity_ids(
    event_llm_extractor: Any, segment_text: str, entity_ids: List[str]
) -> Dict[str, Any]:
    """Run the event extractor with entity IDs interpolated into the prompt.

    JSONPromptExtractor.extract() only substitutes {story_text}/
    {indexed_story_text} into user_prompt_template. {entity_ids} is
    resolved by temporarily replacing that one placeholder in the template
    with a literal string (leaving {story_text}/{indexed_story_text}
    intact for extract() to fill in as usual), then calling
    extract() itself — not the backend directly — so a transient provider
    failure or missing tool_result produces the same normalized
    api_error/extraction_error result extract() gives every other call,
    instead of an uncaught exception that would abort process_segments()
    for every remaining segment.
    """
    original_template = event_llm_extractor.user_prompt_template
    entity_ids_text = ", ".join(entity_ids) if entity_ids else "(none known yet)"
    event_llm_extractor.user_prompt_template = original_template.replace(
        "{entity_ids}", entity_ids_text
    )
    try:
        return event_llm_extractor.extract(segment_text)
    finally:
        event_llm_extractor.user_prompt_template = original_template


def process_segments(
    story_text: str,
    segments: List[Dict[str, Any]],
    *,
    nlp_backend_name: str,
    llm_backend: Any,
) -> Dict[str, Any]:
    """Run stages 2-5 over every segment in `segments`.

    Args:
        story_text: Full story text; segments are sliced from this by
            start_char/end_char (the stage-1 input contract).
        segments: Segment dicts with segment_id, start_char, end_char (as
            produced by story_processors.make_annotated_segment_extractor,
            or baseline.make_fixed_token_chunks).
        nlp_backend_name: "stanza" or "spacy".
        llm_backend: LLMBackend for the entity/event extraction passes.

    Returns:
        {"segments": [SegmentWorldAnnotation.to_dict(), ...],
         "usage": [PassUsage.to_dict(), ...]}
    """
    nlp_backend = surface_feature_extractor.make_nlp_backend(nlp_backend_name)
    entity_llm_extractor = entity_extractor_module.make_entity_extractor(llm_backend)
    event_llm_extractor = event_extractor_module.make_event_extractor(llm_backend)

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
        )
        annotations.append(annotation)
        all_usage.extend(usage_records)

    return {
        "segments": [a.to_dict() for a in annotations],
        "usage": [u.to_dict() for u in all_usage],
    }
