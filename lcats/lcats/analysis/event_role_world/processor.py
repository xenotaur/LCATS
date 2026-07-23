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

    # Stage 3: entities/participants (LLM-backed).
    t0 = time.monotonic()
    entity_result = entity_llm_extractor.extract(segment_text)
    usage_records.append(
        _pass_usage_from_extraction(segment_id, "entity", entity_result, t0)
    )
    entities, mentions = entity_extractor_module.build_entities(
        entity_result.get("extracted_output") or {}, segment_text
    )

    # Stages 4-5: events/semantic-roles + temporal/spatial anchors (LLM-backed).
    # JSONPromptExtractor.extract() only substitutes {story_text}/
    # {indexed_story_text}; entity IDs are interpolated via a dedicated
    # helper rather than extract() itself, so this makes exactly one
    # backend call, not two.
    entity_ids = [e.entity_id for e in entities]
    t0 = time.monotonic()
    event_result = _extract_events_with_entity_ids(
        event_llm_extractor, segment_text, entity_ids
    )
    usage_records.append(
        _pass_usage_from_extraction(segment_id, "event_anchor", event_result, t0)
    )
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
    {indexed_story_text} into user_prompt_template; {entity_ids} is
    resolved here by temporarily formatting the template with both story
    text and entity IDs, then calling the backend directly with the
    resulting content — bypassing extract()'s own template formatting for
    this one extra placeholder.
    """
    content = event_llm_extractor.user_prompt_template.format(
        story_text=segment_text,
        indexed_story_text=segment_text,
        entity_ids=", ".join(entity_ids) if entity_ids else "(none known yet)",
    )
    messages = [
        {"role": "system", "content": event_llm_extractor.system_prompt},
        {"role": "user", "content": content},
    ]
    event_llm_extractor.last_messages = messages
    backend_response = event_llm_extractor.backend.complete(
        system=event_llm_extractor.system_prompt,
        messages=[{"role": "user", "content": content}],
        model=event_llm_extractor.default_model,
        temperature=event_llm_extractor.temperature,
        max_tokens=event_llm_extractor.max_tokens,
        tool=event_llm_extractor.tool_schema,
    )
    event_llm_extractor.last_response = backend_response
    return {
        "extracted_output": backend_response.tool_result,
        "model_name": backend_response.model,
        "usage": {
            "input_tokens": backend_response.input_tokens,
            "output_tokens": backend_response.output_tokens,
        },
    }


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
