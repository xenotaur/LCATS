"""Stage 6: causal/temporal relation extraction between events.

Uses lcats.analysis.llm_extractor.JSONPromptExtractor's tool_schema
parameter (schema-checked structured output) rather than json_object mode,
per the governing proposal's Implementation prerequisites section.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from lcats.analysis import llm_extractor
from lcats.analysis.event_role_world import schema

RELATION_TOOL_SCHEMA: Dict[str, Any] = {
    "name": "extract_relations",
    "description": (
        "Extract causal, enabling, preventing, temporal, motivational, and "
        "explanatory links between events already identified in a story "
        "segment."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "relations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "relation_id": {"type": "string"},
                        "source_event_id": {"type": "string"},
                        "target_event_id": {"type": "string"},
                        "relation_type": {
                            "type": "string",
                            "description": (
                                "e.g. causes, enables, prevents, precedes, "
                                "motivates, explains"
                            ),
                        },
                        "quote": {
                            "type": "string",
                            "description": (
                                "Exact substring of the segment text that "
                                "grounds this relation."
                            ),
                        },
                        "certainty": {
                            "type": "string",
                            "enum": ["explicit", "strongly_implied", "weakly_inferred"],
                        },
                        "confidence": {"type": "number"},
                    },
                    "required": [
                        "relation_id",
                        "source_event_id",
                        "target_event_id",
                        "relation_type",
                        "quote",
                    ],
                },
            }
        },
        "required": ["relations"],
    },
}

RELATION_SYSTEM_PROMPT = """You are extracting causal and temporal relations
between events from a segment of a story for structured narrative analysis.
Only link events using the event IDs already identified for this segment.
For each relation, classify its certainty: "explicit" if the text states the
relation directly, "strongly_implied" if a careful reader would confidently
infer it, or "weakly_inferred" if it is a plausible but speculative reading.
Quote exact segment text for every claim; do not infer relations between
events not both present in the provided event ID list."""

RELATION_USER_PROMPT_TEMPLATE = """Segment text:
---
{story_text}
---

Known event IDs for this segment: {event_ids}

Extract relations between these events per the extract_relations tool
schema. Only use source_event_id/target_event_id values from the known
event IDs above."""


def make_relation_extractor(backend: Any) -> llm_extractor.JSONPromptExtractor:
    """Create a JSONPromptExtractor configured for stage-6 relation extraction.

    Args:
        backend: LLMBackend satisfying lcats.llm.backend.LLMBackend Protocol.

    Returns:
        Configured JSONPromptExtractor using the tool= structured-output path.
    """
    return llm_extractor.JSONPromptExtractor(
        backend,
        system_prompt=RELATION_SYSTEM_PROMPT,
        user_prompt_template=RELATION_USER_PROMPT_TEMPLATE,
        default_model="gpt-4o",
        temperature=0.2,
        tool_schema=RELATION_TOOL_SCHEMA,
    )


def build_relations(
    tool_result: Dict[str, Any], segment_text: str
) -> Tuple[List[schema.EventRelation], List[schema.EventRelation]]:
    """Convert a raw extract_relations tool result into schema objects.

    Args:
        tool_result: The dict returned by the extract_relations tool call.
        segment_text: The segment text quotes are resolved against.

    Returns:
        (relations, weakly_inferred_relations) — relations whose quote
        cannot be located in `segment_text` are dropped (not fabricated
        with a guessed span). Relations with certainty "explicit" or
        "strongly_implied" go in the first list (the main relations
        layer); "weakly_inferred" relations are partitioned into the
        second list per the proposal's causality tradeoff table. Repeated
        identical quotes resolve to successive occurrences via a
        per-segment EvidenceCursor.
    """
    cursor = schema.EvidenceCursor()

    relations: List[schema.EventRelation] = []
    weakly_inferred_relations: List[schema.EventRelation] = []

    for raw in tool_result.get("relations") or []:
        evidence = cursor.resolve(raw.get("quote", ""), segment_text)
        if evidence is None:
            continue
        certainty = raw.get("certainty", "explicit")
        relation = schema.EventRelation(
            relation_id=raw["relation_id"],
            source_event_id=raw["source_event_id"],
            target_event_id=raw["target_event_id"],
            relation_type=raw.get("relation_type", "other"),
            evidence=evidence,
            certainty=certainty,
            confidence=raw.get("confidence", 1.0),
        )
        if certainty == "weakly_inferred":
            weakly_inferred_relations.append(relation)
        else:
            relations.append(relation)

    return relations, weakly_inferred_relations
