"""Story-level cross-segment relation pass (WI-EVENT-0029).

Runs once per story, after schema.reconcile_story_annotations has produced
the story's global entity IDs and segment-qualified event list, to discover
causal/enabling/preventing/temporal/motivational/explanatory relations whose
source and target events live in *different* segments — something stage 6's
per-segment relation_extractor structurally cannot represent, since it only
ever receives its own segment's event IDs (see relation_extractor.py and the
"Known limitation" this pass resolves on schema.StoryWorldAnnotation).

Uses lcats.analysis.llm_extractor.JSONPromptExtractor's tool_schema
parameter (schema-checked structured output), consistent with every other
extraction pass in this package.

Unlike the per-segment passes, this pass has no single segment text to
ground quotes against — instead it reuses each event's own already-resolved
EvidenceSpan (from the per-segment extraction that discovered it) as the
relation's evidence, and works from a compact textual index of every
story-level event rather than raw segment text. This sidesteps the hardest
grounding problem in any cross-segment design (a fresh quote search across a
multi-segment text blob) almost entirely.
"""

from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple

from lcats.analysis import llm_extractor
from lcats.analysis.event_role_world import schema
from lcats.llm import tool_schema as tool_schema_module

STORY_RELATION_TOOL_SCHEMA: Dict[str, Any] = tool_schema_module.strict_tool_schema(
    {
        "name": "extract_story_relations",
        "description": (
            "Extract causal, enabling, preventing, temporal, motivational, and "
            "explanatory links between events that belong to DIFFERENT segments "
            "of the same story. Same-segment relations are already handled by a "
            "separate pass and must not be repeated here."
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
                            "source_event_id": {
                                "type": "string",
                                "description": (
                                    'Qualified event ID ("segment_id:event_id") '
                                    "from the known events list."
                                ),
                            },
                            "target_event_id": {
                                "type": "string",
                                "description": (
                                    'Qualified event ID ("segment_id:event_id") '
                                    "from the known events list, in a DIFFERENT "
                                    "segment than source_event_id."
                                ),
                            },
                            "relation_type": {
                                "type": "string",
                                "description": (
                                    "e.g. causes, enables, prevents, precedes, "
                                    "motivates, explains"
                                ),
                            },
                            "certainty": {
                                "type": "string",
                                "enum": [
                                    "explicit",
                                    "strongly_implied",
                                    "weakly_inferred",
                                ],
                            },
                            "confidence": {"type": "number"},
                        },
                        "required": [
                            "relation_id",
                            "source_event_id",
                            "target_event_id",
                            "relation_type",
                        ],
                    },
                }
            },
            "required": ["relations"],
        },
    }
)

STORY_RELATION_SYSTEM_PROMPT = """You are extracting cross-segment causal and
temporal relations between events from different segments of the same story,
for structured narrative analysis. You are given a compact list of events
already identified across every segment, each labeled with a globally
qualified event ID ("segment_id:event_id"), its predicate and event type,
which segment it belongs to, and a short quote grounding it in that segment.
Only propose relations whose source and target events belong to DIFFERENT
segments — same-segment relations are already handled by a separate pass and
must not be repeated here. Only use the exact qualified event IDs given; do
not invent new ones. For each relation, classify its certainty: "explicit" if
the text directly implies the link across the events described,
"strongly_implied" if a careful reader would confidently infer it, or
"weakly_inferred" if it is a plausible but speculative reading."""

STORY_RELATION_USER_PROMPT_TEMPLATE = """Known events across the story
(qualified_event_id | predicate [event_type] | segment=segment_id | "quote"):
---
{story_text}
---

Extract only relations whose source_event_id and target_event_id come from
DIFFERENT segments, per the extract_story_relations tool schema. Use the
exact qualified event IDs listed above."""


def make_story_relation_extractor(backend: Any) -> llm_extractor.JSONPromptExtractor:
    """Create a JSONPromptExtractor configured for the story-level relation pass.

    Args:
        backend: LLMBackend satisfying lcats.llm.backend.LLMBackend Protocol.

    Returns:
        Configured JSONPromptExtractor using the tool= structured-output path.
    """
    return llm_extractor.JSONPromptExtractor(
        backend,
        system_prompt=STORY_RELATION_SYSTEM_PROMPT,
        user_prompt_template=STORY_RELATION_USER_PROMPT_TEMPLATE,
        default_model="gpt-4o",
        temperature=0.2,
        tool_schema=STORY_RELATION_TOOL_SCHEMA,
    )


def build_event_index(story: schema.StoryWorldAnnotation) -> str:
    """Build a compact, qualified-event-ID-keyed text index for `story`.

    Args:
        story: A StoryWorldAnnotation whose segment_annotations' events are
            indexed. Must be called after schema.reconcile_story_annotations
            so segment_annotations is populated.

    Returns:
        One line per event, in segment order: "segment_id:event_id |
        predicate [event_type] | segment=segment_id | \"quote\"" — this text
        is passed as the pass's `story_text` argument (there is no single
        segment text for a story-level pass; this compact index stands in
        for it).
    """
    lines: List[str] = []
    for segment in story.segment_annotations:
        for event in segment.events:
            qualified_id = f"{segment.segment_id}:{event.event_id}"
            lines.append(
                f"{qualified_id} | {event.predicate} [{event.event_type}] | "
                f'segment={segment.segment_id} | "{event.evidence.quote}"'
            )
    return "\n".join(lines)


def build_story_relations(
    tool_result: Dict[str, Any], story: schema.StoryWorldAnnotation
) -> Tuple[List[schema.EventRelation], List[schema.EventRelation], List[str]]:
    """Convert a raw extract_story_relations tool result into schema objects.

    Args:
        tool_result: The dict returned by the extract_story_relations tool
            call.
        story: The StoryWorldAnnotation the qualified event IDs and
            per-event evidence spans are resolved against. Must be called
            after schema.reconcile_story_annotations.

    Returns:
        (cross_segment_relations, weakly_inferred_cross_segment_relations,
        item_errors) — relations whose source_event_id/target_event_id do
        not both
        resolve to known qualified event IDs are dropped, as are relations
        whose source and target resolve to the SAME segment (the model may
        occasionally violate its instructions; this pass's contract is
        cross-segment only, so such a claim is discarded rather than
        silently accepted). The tool schema does not forbid the model from
        returning the same relation_id more than once in a single call, so
        a raw relation_id already seen earlier in this same tool_result is
        also dropped — deduplicated here, before storing or counting,
        rather than merely detected later by validate_story_annotation.
        Each surviving relation's relation_id is qualified with a "story:"
        prefix so it can never collide with a per-segment relation's raw ID
        once both appear in exported tables — this pass's output is kept
        in its own StoryWorldAnnotation fields entirely separate from
        `relations`, so no cross-source deduplication is needed to combine
        their counts (only the within-this-call dedup above is needed).
        Evidence is reused directly from the source event's own
        already-resolved EvidenceSpan (the "already-resolved evidence
        spans" reuse WI-EVENT-0028's evaluation recommended), not a fresh
        quote search — there is no single text blob to search across
        segments against. item_errors describes any "relations" array
        item that was not a dict - skipped rather than crashing, but
        surfaced explicitly (see schema.describe_malformed_item).
    """
    event_by_qualified_id: Dict[str, schema.Event] = {
        f"{segment.segment_id}:{event.event_id}": event
        for segment in story.segment_annotations
        for event in segment.events
    }

    cross_segment_relations: List[schema.EventRelation] = []
    weakly_inferred_cross_segment_relations: List[schema.EventRelation] = []
    seen_raw_relation_ids: Set[str] = set()
    item_errors: List[str] = []

    for i, raw in enumerate(tool_result.get("relations") or []):
        if not isinstance(raw, dict):
            item_errors.append(schema.describe_malformed_item(f"relations[{i}]", raw))
            continue
        source_id = raw.get("source_event_id", "")
        target_id = raw.get("target_event_id", "")
        source_event = event_by_qualified_id.get(source_id)
        target_event = event_by_qualified_id.get(target_id)
        if source_event is None or target_event is None:
            continue

        source_segment_id = source_id.split(":", 1)[0]
        target_segment_id = target_id.split(":", 1)[0]
        if source_segment_id == target_segment_id:
            continue

        raw_relation_id = raw["relation_id"]
        if raw_relation_id in seen_raw_relation_ids:
            continue
        seen_raw_relation_ids.add(raw_relation_id)

        certainty = raw.get("certainty", "explicit")
        relation = schema.EventRelation(
            relation_id=f"story:{raw_relation_id}",
            source_event_id=source_id,
            target_event_id=target_id,
            relation_type=raw.get("relation_type", "other"),
            evidence=source_event.evidence,
            certainty=certainty,
            confidence=raw.get("confidence", 1.0),
        )
        if certainty == "weakly_inferred":
            weakly_inferred_cross_segment_relations.append(relation)
        else:
            cross_segment_relations.append(relation)

    return cross_segment_relations, weakly_inferred_cross_segment_relations, item_errors
