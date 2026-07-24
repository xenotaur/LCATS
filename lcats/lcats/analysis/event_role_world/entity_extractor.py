"""Stage 3: entity/participant extraction via the backend's tool= path.

Uses lcats.analysis.llm_extractor.JSONPromptExtractor's tool_schema
parameter (schema-checked structured output) rather than json_object mode,
per the governing proposal's Implementation prerequisites section.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from lcats.analysis import llm_extractor
from lcats.analysis.event_role_world import schema

ENTITY_TOOL_SCHEMA: Dict[str, Any] = {
    "name": "extract_entities",
    "description": (
        "Extract salient entities, participants, and aliases from a story "
        "segment, with actant roles and quoted evidence for each mention."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "entities": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "entity_id": {"type": "string"},
                        "canonical_name": {"type": "string"},
                        "entity_type": {
                            "type": "string",
                            "description": (
                                "e.g. human, nonhuman_animal, alien, "
                                "machine_or_artifact, institution, "
                                "environment, abstract_force"
                            ),
                        },
                        "aliases": {"type": "array", "items": {"type": "string"}},
                        "actant_roles": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": (
                                "e.g. protagonist, opponent, helper, "
                                "instrument, victim, observer"
                            ),
                        },
                        "confidence": {"type": "number"},
                        "mentions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "mention_id": {"type": "string"},
                                    "text": {"type": "string"},
                                    "quote": {
                                        "type": "string",
                                        "description": (
                                            "Exact substring of the segment "
                                            "text this mention refers to."
                                        ),
                                    },
                                    "mention_form": {"type": "string"},
                                    "grammatical_role": {"type": "string"},
                                },
                                "required": ["mention_id", "text", "quote"],
                            },
                        },
                    },
                    "required": [
                        "entity_id",
                        "canonical_name",
                        "entity_type",
                        "mentions",
                    ],
                },
            }
        },
        "required": ["entities"],
    },
}

ENTITY_SYSTEM_PROMPT = """You are extracting entities and participants from a
segment of a story for structured narrative analysis. Identify every salient
entity: people, nonhuman animals, aliens, machines/artifacts, institutions,
environments, or abstract forces that act or are acted upon. For each entity,
list every surface mention with the exact quoted text from the segment. Use
only the provided segment text as evidence; do not infer entities not
mentioned in it."""

ENTITY_USER_PROMPT_TEMPLATE = """Segment text:
---
{story_text}
---

Extract entities and their mentions per the extract_entities tool schema."""


def make_entity_extractor(backend: Any) -> llm_extractor.JSONPromptExtractor:
    """Create a JSONPromptExtractor configured for stage-3 entity extraction.

    Args:
        backend: LLMBackend satisfying lcats.llm.backend.LLMBackend Protocol.

    Returns:
        Configured JSONPromptExtractor using the tool= structured-output path.
    """
    return llm_extractor.JSONPromptExtractor(
        backend,
        system_prompt=ENTITY_SYSTEM_PROMPT,
        user_prompt_template=ENTITY_USER_PROMPT_TEMPLATE,
        default_model="gpt-4o",
        temperature=0.2,
        tool_schema=ENTITY_TOOL_SCHEMA,
    )


def build_entities(
    tool_result: Dict[str, Any], segment_text: str
) -> Tuple[List[schema.Entity], List[schema.EntityMention]]:
    """Convert a raw extract_entities tool result into schema objects.

    Args:
        tool_result: The dict returned by the extract_entities tool call
            (JSONPromptExtractor.extract(...)['extracted_output']).
        segment_text: The segment text mention quotes are resolved against.

    Returns:
        (entities, mentions) — mentions whose quote cannot be located in
        `segment_text` are dropped (not fabricated with a guessed span).
        An entity whose every mention was dropped this way is itself
        dropped: an entity with zero grounded mentions is ungrounded and
        would otherwise inflate entity-rate metrics for output the
        evidence check already rejected. Repeated identical quotes within
        one entity's mentions resolve to successive occurrences via a
        per-segment EvidenceCursor, not all onto the first match.
    """
    entities: List[schema.Entity] = []
    mentions: List[schema.EntityMention] = []
    cursor = schema.EvidenceCursor()

    for raw_entity in tool_result.get("entities") or []:
        mention_ids: List[str] = []
        for raw_mention in raw_entity.get("mentions") or []:
            evidence = cursor.resolve(raw_mention.get("quote", ""), segment_text)
            if evidence is None:
                continue
            mention = schema.EntityMention(
                mention_id=raw_mention["mention_id"],
                entity_id=raw_entity["entity_id"],
                text=raw_mention.get("text", raw_mention.get("quote", "")),
                evidence=evidence,
                mention_form=raw_mention.get("mention_form"),
                grammatical_role=raw_mention.get("grammatical_role"),
            )
            mentions.append(mention)
            mention_ids.append(mention.mention_id)

        if not mention_ids:
            # Every mention's quote was unresolvable: this entity has no
            # grounded evidence at all. Drop it rather than keep an
            # ungrounded entity that would inflate entity-rate metrics.
            continue

        entities.append(
            schema.Entity(
                entity_id=raw_entity["entity_id"],
                canonical_name=raw_entity["canonical_name"],
                entity_type=raw_entity.get("entity_type", "other"),
                aliases=raw_entity.get("aliases") or [],
                mention_ids=mention_ids,
                actant_roles=raw_entity.get("actant_roles") or [],
                confidence=raw_entity.get("confidence", 1.0),
            )
        )

    return entities, mentions
