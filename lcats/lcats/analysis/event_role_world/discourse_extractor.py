"""Stage 7: speech act, explanation discourse, and SF world-model tag extraction.

Uses lcats.analysis.llm_extractor.JSONPromptExtractor's tool_schema
parameter (schema-checked structured output) rather than json_object mode,
per the governing proposal's Implementation prerequisites section. Speech
acts, explanations, and SF tags are extracted in one call since they share
the same segment context and may reference the same entities/events.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from lcats.analysis import llm_extractor
from lcats.analysis.event_role_world import schema

DISCOURSE_TOOL_SCHEMA: Dict[str, Any] = {
    "name": "extract_discourse",
    "description": (
        "Extract speech acts, explanatory passages, and SF world-model "
        "tags from a story segment."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "speech_acts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "speech_act_id": {"type": "string"},
                        "act_type": {
                            "type": "string",
                            "description": (
                                "e.g. assertion, question, command, promise, " "warning"
                            ),
                        },
                        "quote": {"type": "string"},
                        "speaker_entity_id": {"type": "string"},
                        "addressee_entity_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "linked_event_id": {"type": "string"},
                        "confidence": {"type": "number"},
                    },
                    "required": ["speech_act_id", "act_type", "quote"],
                },
            },
            "explanations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "explanation_id": {"type": "string"},
                        "topic": {"type": "string"},
                        "mechanism_or_rationale_type": {
                            "type": "string",
                            "description": (
                                "e.g. scientific_mechanism, technical_operation, "
                                "personal_rationale, historical_cause"
                            ),
                        },
                        "quote": {"type": "string"},
                        "linked_entity_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "linked_event_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "confidence": {"type": "number"},
                    },
                    "required": [
                        "explanation_id",
                        "topic",
                        "mechanism_or_rationale_type",
                        "quote",
                    ],
                },
            },
            "sf_tags": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "tag_id": {"type": "string"},
                        "tag": {
                            "type": "string",
                            "description": (
                                "Controlled tag, e.g. anomaly_or_novum, "
                                "ontological_rule, technology_as_agent, "
                                "nonhuman_actant"
                            ),
                        },
                        "quote": {"type": "string"},
                        "linked_entity_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "linked_event_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "status": {
                            "type": "string",
                            "enum": ["extractive", "hypothesis"],
                            "description": (
                                "extractive if the text states the tag "
                                "explicitly, hypothesis if inferred"
                            ),
                        },
                        "confidence": {"type": "number"},
                    },
                    "required": ["tag_id", "tag", "quote"],
                },
            },
        },
        "required": [],
    },
}

DISCOURSE_SYSTEM_PROMPT = """You are extracting discourse-level features from
a segment of a story for structured narrative analysis: speech acts
(who said/asked/commanded what, to whom), explanatory passages (mechanisms,
rationales, technical or scientific explanations), and SF world-model tags
(controlled tags marking science-fictional elements such as anomalies,
ontological rules, or nonhuman/technological actants). Only link speech acts,
explanations, and tags to entity/event IDs already identified for this
segment. Mark an SF tag's status as "extractive" only if the text states it
explicitly; otherwise mark it "hypothesis". Quote exact segment text for
every claim."""

DISCOURSE_USER_PROMPT_TEMPLATE = """Segment text:
---
{story_text}
---

Known entity IDs for this segment: {entity_ids}
Known event IDs for this segment: {event_ids}

Extract speech acts, explanations, and SF world-model tags per the
extract_discourse tool schema. Only use entity/event IDs from the known
lists above for any linked_entity_ids/linked_event_ids/speaker_entity_id/
addressee_entity_ids/linked_event_id fields."""


def make_discourse_extractor(backend: Any) -> llm_extractor.JSONPromptExtractor:
    """Create a JSONPromptExtractor configured for stage-7 discourse extraction.

    Args:
        backend: LLMBackend satisfying lcats.llm.backend.LLMBackend Protocol.

    Returns:
        Configured JSONPromptExtractor using the tool= structured-output path.
    """
    return llm_extractor.JSONPromptExtractor(
        backend,
        system_prompt=DISCOURSE_SYSTEM_PROMPT,
        user_prompt_template=DISCOURSE_USER_PROMPT_TEMPLATE,
        default_model="gpt-4o",
        temperature=0.2,
        tool_schema=DISCOURSE_TOOL_SCHEMA,
    )


def build_discourse(tool_result: Dict[str, Any], segment_text: str) -> Tuple[
    List[schema.SpeechAct],
    List[schema.ExplanationDiscourse],
    List[schema.SFWorldModelTag],
]:
    """Convert a raw extract_discourse tool result into schema objects.

    Args:
        tool_result: The dict returned by the extract_discourse tool call.
        segment_text: The segment text quotes are resolved against.

    Returns:
        (speech_acts, explanations, sf_tags) — any item whose quote cannot
        be located in `segment_text` is dropped (not fabricated with a
        guessed span). Repeated identical quotes across all three resolve
        to successive occurrences via a per-segment EvidenceCursor shared
        across all three, not all onto the first match.
    """
    cursor = schema.EvidenceCursor()

    speech_acts: List[schema.SpeechAct] = []
    for raw in tool_result.get("speech_acts") or []:
        evidence = cursor.resolve(raw.get("quote", ""), segment_text)
        if evidence is None:
            continue
        speech_acts.append(
            schema.SpeechAct(
                speech_act_id=raw["speech_act_id"],
                act_type=raw.get("act_type", "other"),
                evidence=evidence,
                speaker_entity_id=raw.get("speaker_entity_id"),
                addressee_entity_ids=raw.get("addressee_entity_ids") or [],
                linked_event_id=raw.get("linked_event_id"),
                confidence=raw.get("confidence", 1.0),
            )
        )

    explanations: List[schema.ExplanationDiscourse] = []
    for raw in tool_result.get("explanations") or []:
        evidence = cursor.resolve(raw.get("quote", ""), segment_text)
        if evidence is None:
            continue
        explanations.append(
            schema.ExplanationDiscourse(
                explanation_id=raw["explanation_id"],
                topic=raw.get("topic", ""),
                mechanism_or_rationale_type=raw.get(
                    "mechanism_or_rationale_type", "other"
                ),
                evidence=evidence,
                linked_entity_ids=raw.get("linked_entity_ids") or [],
                linked_event_ids=raw.get("linked_event_ids") or [],
                confidence=raw.get("confidence", 1.0),
            )
        )

    sf_tags: List[schema.SFWorldModelTag] = []
    for raw in tool_result.get("sf_tags") or []:
        evidence = cursor.resolve(raw.get("quote", ""), segment_text)
        if evidence is None:
            continue
        sf_tags.append(
            schema.SFWorldModelTag(
                tag_id=raw["tag_id"],
                tag=raw.get("tag", "other"),
                evidence=evidence,
                linked_entity_ids=raw.get("linked_entity_ids") or [],
                linked_event_ids=raw.get("linked_event_ids") or [],
                status=raw.get("status", "hypothesis"),
                confidence=raw.get("confidence", 1.0),
            )
        )

    return speech_acts, explanations, sf_tags
