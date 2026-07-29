"""Stage 8 (optional): belief, uncertainty, perspective, and emotion/appraisal.

Uses lcats.analysis.llm_extractor.JSONPromptExtractor's tool_schema
parameter (schema-checked structured output) rather than json_object mode,
per the governing proposal's Implementation prerequisites section.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from lcats.analysis import llm_extractor
from lcats.analysis.event_role_world import schema
from lcats.llm import tool_schema as tool_schema_module

HYPOTHESIS_TOOL_SCHEMA: Dict[str, Any] = tool_schema_module.strict_tool_schema(
    {
        "name": "extract_hypotheses",
        "description": (
            "Extract optional belief, uncertainty, perspective, or emotion/"
            "appraisal annotations from a story segment. These are never "
            "extractive facts, even when confidently stated."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "hypotheses": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "hypothesis_id": {"type": "string"},
                            "hypothesis_type": {
                                "type": "string",
                                "enum": [
                                    "belief",
                                    "uncertainty",
                                    "perspective",
                                    "emotion_appraisal",
                                ],
                            },
                            "proposition_or_target": {
                                "type": "string",
                                "description": (
                                    "The claim's content: a proposition (for "
                                    "belief/uncertainty) or a target (for "
                                    "perspective/emotion_appraisal)."
                                ),
                            },
                            "quote": {
                                "type": "string",
                                "description": (
                                    "Exact substring of the segment text that "
                                    "grounds this hypothesis."
                                ),
                            },
                            "subject_entity_id": {
                                "type": "string",
                                "description": (
                                    "Entity who holds the belief/perspective, "
                                    "if known."
                                ),
                            },
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
                            "hypothesis_id",
                            "hypothesis_type",
                            "proposition_or_target",
                            "quote",
                        ],
                    },
                }
            },
            "required": ["hypotheses"],
        },
    }
)

HYPOTHESIS_SYSTEM_PROMPT = """You are extracting optional interpretive
hypotheses from a segment of a story for structured narrative analysis:
belief (what a character believes), uncertainty (what a character or the
narration is unsure of), perspective (whose point of view frames a claim),
or emotion/appraisal (an emotional reaction or evaluative judgment). These
are never extractive facts, even when confidently stated in the text - mark
every claim as a hypothesis. Only link hypotheses to entity/event IDs
already identified for this segment. Quote exact segment text for every
claim; do not infer hypotheses about entities or events not in the provided
lists."""

HYPOTHESIS_USER_PROMPT_TEMPLATE = """Segment text:
---
{story_text}
---

Known entity IDs for this segment: {entity_ids}
Known event IDs for this segment: {event_ids}

Extract belief, uncertainty, perspective, and emotion/appraisal hypotheses
per the extract_hypotheses tool schema. Only use entity/event IDs from the
known lists above for subject_entity_id/linked_entity_ids/linked_event_ids."""


def make_hypothesis_extractor(backend: Any) -> llm_extractor.JSONPromptExtractor:
    """Create a JSONPromptExtractor configured for stage-8 hypothesis extraction.

    Args:
        backend: LLMBackend satisfying lcats.llm.backend.LLMBackend Protocol.

    Returns:
        Configured JSONPromptExtractor using the tool= structured-output path.
    """
    return llm_extractor.JSONPromptExtractor(
        backend,
        system_prompt=HYPOTHESIS_SYSTEM_PROMPT,
        user_prompt_template=HYPOTHESIS_USER_PROMPT_TEMPLATE,
        default_model="gpt-4o",
        temperature=0.2,
        tool_schema=HYPOTHESIS_TOOL_SCHEMA,
    )


def build_hypotheses(
    tool_result: Dict[str, Any], segment_text: str
) -> Tuple[List[schema.Hypothesis], List[str]]:
    """Convert a raw extract_hypotheses tool result into schema objects.

    Args:
        tool_result: The dict returned by the extract_hypotheses tool call.
        segment_text: The segment text quotes are resolved against.

    Returns:
        (hypotheses, item_errors) — hypotheses whose quote cannot be
        located in `segment_text` are dropped (not fabricated with a
        guessed span). Repeated identical quotes resolve to successive
        occurrences via a per-segment EvidenceCursor, private to this
        pass — not shared with any other stage's cursor. item_errors
        describes any "hypotheses" array item that was not a dict -
        skipped rather than crashing, but surfaced explicitly (see
        schema.describe_malformed_item).
    """
    cursor = schema.EvidenceCursor()

    hypotheses: List[schema.Hypothesis] = []
    item_errors: List[str] = []
    for i, raw in enumerate(tool_result.get("hypotheses") or []):
        if not isinstance(raw, dict):
            item_errors.append(schema.describe_malformed_item(f"hypotheses[{i}]", raw))
            continue
        evidence = cursor.resolve(raw.get("quote", ""), segment_text)
        if evidence is None:
            continue
        hypotheses.append(
            schema.Hypothesis(
                hypothesis_id=raw["hypothesis_id"],
                hypothesis_type=raw.get("hypothesis_type", "belief"),
                proposition_or_target=raw.get("proposition_or_target", ""),
                evidence=evidence,
                subject_entity_id=raw.get("subject_entity_id"),
                linked_entity_ids=raw.get("linked_entity_ids") or [],
                linked_event_ids=raw.get("linked_event_ids") or [],
                confidence=raw.get("confidence", 1.0),
            )
        )

    return hypotheses, item_errors
