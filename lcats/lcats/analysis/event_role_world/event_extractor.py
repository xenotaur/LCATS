"""Stages 4-5: event/semantic-role and temporal/spatial anchor extraction.

Uses lcats.analysis.llm_extractor.JSONPromptExtractor's tool_schema
parameter (schema-checked structured output) rather than json_object mode,
per the governing proposal's Implementation prerequisites section. Events
and anchors are extracted in one call since events reference anchor IDs.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from lcats.analysis import llm_extractor
from lcats.analysis.event_role_world import schema

EVENT_TOOL_SCHEMA: Dict[str, Any] = {
    "name": "extract_events_and_anchors",
    "description": (
        "Extract salient events with semantic roles, and the temporal/"
        "spatial anchors those events occur within, from a story segment."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "temporal_anchors": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "anchor_id": {"type": "string"},
                        "text": {"type": "string"},
                        "quote": {"type": "string"},
                        "normalized": {"type": "string"},
                        "granularity": {"type": "string"},
                        "relative_or_absolute": {
                            "type": "string",
                            "enum": ["relative", "absolute"],
                        },
                        "scale": {"type": "string"},
                        "confidence": {"type": "number"},
                    },
                    "required": ["anchor_id", "text", "quote"],
                },
            },
            "spatial_anchors": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "anchor_id": {"type": "string"},
                        "text": {"type": "string"},
                        "quote": {"type": "string"},
                        "linked_entity_id": {"type": "string"},
                        "containment_or_scale": {"type": "string"},
                        "confidence": {"type": "number"},
                    },
                    "required": ["anchor_id", "text", "quote"],
                },
            },
            "events": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "event_id": {"type": "string"},
                        "predicate": {"type": "string"},
                        "lemma": {"type": "string"},
                        "event_type": {"type": "string"},
                        "quote": {
                            "type": "string",
                            "description": (
                                "Exact substring of the segment text this "
                                "event's predicate occurs in."
                            ),
                        },
                        "modality": {
                            "type": "string",
                            "enum": [
                                "actual",
                                "hypothetical",
                                "negated",
                                "future",
                                "counterfactual",
                            ],
                        },
                        "confidence": {"type": "number"},
                        "temporal_anchor_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "spatial_anchor_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "semantic_roles": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "role": {
                                        "type": "string",
                                        "description": (
                                            "e.g. agent, patient, theme, "
                                            "experiencer, instrument, "
                                            "source, goal, location, "
                                            "cause, result"
                                        ),
                                    },
                                    "filler_entity_id": {"type": "string"},
                                    "filler_text": {"type": "string"},
                                    "quote": {"type": "string"},
                                    "confidence": {"type": "number"},
                                },
                                "required": ["role", "quote"],
                            },
                        },
                    },
                    "required": ["event_id", "predicate", "event_type", "quote"],
                },
            },
        },
        "required": ["events"],
    },
}

EVENT_SYSTEM_PROMPT = """You are extracting events, semantic roles, and
temporal/spatial anchors from a segment of a story for structured narrative
analysis. Identify every salient predicate/event, its participants' semantic
roles (agent, patient, instrument, etc.), and the times/places it occurs
within. Use only the provided segment text and previously-extracted entity
IDs as evidence; quote exact segment text for every claim."""

EVENT_USER_PROMPT_TEMPLATE = """Segment text:
---
{story_text}
---

Known entity IDs for this segment: {entity_ids}

Extract events, semantic roles, and temporal/spatial anchors per the
extract_events_and_anchors tool schema. Use the known entity IDs for
filler_entity_id where a semantic role's filler is one of them."""


def make_event_extractor(backend: Any) -> llm_extractor.JSONPromptExtractor:
    """Create a JSONPromptExtractor configured for stage-4/5 extraction.

    Args:
        backend: LLMBackend satisfying lcats.llm.backend.LLMBackend Protocol.

    Returns:
        Configured JSONPromptExtractor using the tool= structured-output path.
    """
    return llm_extractor.JSONPromptExtractor(
        backend,
        system_prompt=EVENT_SYSTEM_PROMPT,
        user_prompt_template=EVENT_USER_PROMPT_TEMPLATE,
        default_model="gpt-4o",
        temperature=0.2,
        tool_schema=EVENT_TOOL_SCHEMA,
    )


def build_events_and_anchors(
    tool_result: Dict[str, Any], segment_text: str
) -> Tuple[List[schema.Event], List[schema.TemporalAnchor], List[schema.SpatialAnchor]]:
    """Convert a raw extract_events_and_anchors tool result into schema objects.

    Args:
        tool_result: The dict returned by the extract_events_and_anchors
            tool call.
        segment_text: The segment text quotes are resolved against.

    Returns:
        (events, temporal_anchors, spatial_anchors). Events, semantic roles,
        and anchors whose quote cannot be located in `segment_text` are
        dropped (not fabricated with a guessed span).
    """
    temporal_anchors: List[schema.TemporalAnchor] = []
    for raw in tool_result.get("temporal_anchors") or []:
        evidence = schema.resolve_evidence(raw.get("quote", ""), segment_text)
        if evidence is None:
            continue
        temporal_anchors.append(
            schema.TemporalAnchor(
                anchor_id=raw["anchor_id"],
                text=raw.get("text", raw.get("quote", "")),
                evidence=evidence,
                normalized=raw.get("normalized"),
                granularity=raw.get("granularity"),
                relative_or_absolute=raw.get("relative_or_absolute", "relative"),
                scale=raw.get("scale"),
                confidence=raw.get("confidence", 1.0),
            )
        )

    spatial_anchors: List[schema.SpatialAnchor] = []
    for raw in tool_result.get("spatial_anchors") or []:
        evidence = schema.resolve_evidence(raw.get("quote", ""), segment_text)
        if evidence is None:
            continue
        spatial_anchors.append(
            schema.SpatialAnchor(
                anchor_id=raw["anchor_id"],
                text=raw.get("text", raw.get("quote", "")),
                evidence=evidence,
                linked_entity_id=raw.get("linked_entity_id"),
                containment_or_scale=raw.get("containment_or_scale"),
                confidence=raw.get("confidence", 1.0),
            )
        )

    events: List[schema.Event] = []
    for raw_event in tool_result.get("events") or []:
        event_evidence = schema.resolve_evidence(
            raw_event.get("quote", ""), segment_text
        )
        if event_evidence is None:
            continue

        semantic_roles: List[schema.SemanticRole] = []
        for raw_role in raw_event.get("semantic_roles") or []:
            role_evidence = schema.resolve_evidence(
                raw_role.get("quote", ""), segment_text
            )
            if role_evidence is None:
                continue
            semantic_roles.append(
                schema.SemanticRole(
                    role=raw_role["role"],
                    evidence=role_evidence,
                    filler_entity_id=raw_role.get("filler_entity_id"),
                    filler_text=raw_role.get("filler_text"),
                    confidence=raw_role.get("confidence", 1.0),
                )
            )

        events.append(
            schema.Event(
                event_id=raw_event["event_id"],
                predicate=raw_event["predicate"],
                event_type=raw_event.get("event_type", "other"),
                evidence=event_evidence,
                lemma=raw_event.get("lemma"),
                semantic_roles=semantic_roles,
                temporal_anchor_ids=raw_event.get("temporal_anchor_ids") or [],
                spatial_anchor_ids=raw_event.get("spatial_anchor_ids") or [],
                modality=raw_event.get("modality", "actual"),
                confidence=raw_event.get("confidence", 1.0),
            )
        )

    return events, temporal_anchors, spatial_anchors
