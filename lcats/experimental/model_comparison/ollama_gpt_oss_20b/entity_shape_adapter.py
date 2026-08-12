"""Candidate-scoped entity output adapter for ``gpt-oss:20b`` diagnostics.

The committed WI-LLM-0064 best-config runs show one specific malformed
shape from this candidate: entity objects may use ``name`` instead of
``canonical_name`` and may put exact mention strings directly in
``mentions``. This adapter converts only that observed shape into the
production ``build_entities()`` input shape. It does not invent spans:
string mentions are converted only when the string is a verbatim substring
of the source segment.
"""

from __future__ import annotations

import re

from typing import Any, Dict, Tuple


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _stable_id(prefix: str, index: int, value: str) -> str:
    slug = _SLUG_RE.sub("_", value.lower()).strip("_")
    if not slug:
        slug = f"item_{index + 1}"
    return f"{prefix}_{index + 1}_{slug[:48]}"


def _normalize_string_mention(
    mention: str, *, entity_id: str, mention_index: int, segment_text: str
) -> tuple[dict[str, Any] | None, str | None]:
    quote = mention.strip()
    if not quote:
        return None, "empty_string_mention"
    if quote not in segment_text:
        return None, f"ungrounded_string_mention:{quote[:80]}"
    return (
        {
            "mention_id": f"{entity_id}_mention_{mention_index + 1}",
            "text": quote,
            "quote": quote,
        },
        None,
    )


def _normalize_dict_mention(
    mention: dict[str, Any],
    *,
    entity_id: str,
    mention_index: int,
    segment_text: str,
) -> tuple[dict[str, Any], str | None]:
    normalized = dict(mention)
    mention_id = normalized.get("mention_id")
    if not isinstance(mention_id, str) or not mention_id.strip():
        normalized["mention_id"] = f"{entity_id}_mention_{mention_index + 1}"

    quote = normalized.get("quote")
    if isinstance(quote, str) and quote.strip():
        return normalized, None

    text = normalized.get("text") or normalized.get("surface")
    if isinstance(text, str) and text.strip() and text.strip() in segment_text:
        normalized.setdefault("text", text.strip())
        normalized["quote"] = text.strip()
        return normalized, None

    return normalized, "dict_mention_missing_grounded_quote"


def normalize_gpt_oss_entity_tool_result(
    tool_result: Dict[str, Any], segment_text: str
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Return a production-shaped copy plus diagnostics for known gpt-oss drift."""
    diagnostics: Dict[str, Any] = {
        "adapter_name": "gpt_oss_20b_string_mentions_to_grounded_mentions",
        "adapter_applied": False,
        "raw_entity_count": None,
        "normalized_entity_count": 0,
        "converted_string_mentions": 0,
        "converted_string_entities": 0,
        "changed_dict_mentions": 0,
        "repaired_dict_mentions": 0,
        "dropped_string_entities": [],
        "dropped_string_mentions": [],
        "unrepaired_dict_mentions": [],
        "unsupported_entity_shapes": [],
        "unsupported_mention_shapes": [],
    }
    raw_entities = tool_result.get("entities")
    if not isinstance(raw_entities, list):
        return tool_result, diagnostics

    diagnostics["raw_entity_count"] = len(raw_entities)
    normalized_entities: list[dict[str, Any]] = []
    for entity_index, raw_entity in enumerate(raw_entities):
        if isinstance(raw_entity, str):
            canonical_name = raw_entity.strip()
            entity_id = _stable_id("gpt_oss_entity", entity_index, canonical_name)
            mention, drop_reason = _normalize_string_mention(
                canonical_name,
                entity_id=entity_id,
                mention_index=0,
                segment_text=segment_text,
            )
            diagnostics["adapter_applied"] = True
            if mention is None:
                diagnostics["dropped_string_entities"].append(
                    {"entity_index": entity_index, "reason": drop_reason}
                )
                continue
            diagnostics["converted_string_entities"] += 1
            normalized_entities.append(
                {
                    "entity_id": entity_id,
                    "canonical_name": canonical_name,
                    "entity_type": "other",
                    "mentions": [mention],
                }
            )
            continue

        if not isinstance(raw_entity, dict):
            diagnostics["unsupported_entity_shapes"].append(
                {"index": entity_index, "type": type(raw_entity).__name__}
            )
            continue

        canonical_name = (
            raw_entity.get("canonical_name")
            or raw_entity.get("name")
            or raw_entity.get("entity")
        )
        if not isinstance(canonical_name, str) or not canonical_name.strip():
            diagnostics["unsupported_entity_shapes"].append(
                {"index": entity_index, "reason": "missing_canonical_name"}
            )
            continue

        entity_id = raw_entity.get("entity_id")
        if not isinstance(entity_id, str) or not entity_id.strip():
            entity_id = _stable_id("gpt_oss_entity", entity_index, canonical_name)
            diagnostics["adapter_applied"] = True

        entity_type = raw_entity.get("entity_type") or raw_entity.get("type")
        if not isinstance(entity_type, str) or not entity_type.strip():
            entity_type = "other"
            diagnostics["adapter_applied"] = True

        raw_mentions = raw_entity.get("mentions")
        normalized_mentions: list[dict[str, Any]] = []
        if isinstance(raw_mentions, list):
            for mention_index, raw_mention in enumerate(raw_mentions):
                if isinstance(raw_mention, str):
                    normalized, drop_reason = _normalize_string_mention(
                        raw_mention,
                        entity_id=entity_id,
                        mention_index=mention_index,
                        segment_text=segment_text,
                    )
                    diagnostics["adapter_applied"] = True
                    if normalized is None:
                        diagnostics["dropped_string_mentions"].append(
                            {
                                "entity_index": entity_index,
                                "mention_index": mention_index,
                                "reason": drop_reason,
                            }
                        )
                    else:
                        diagnostics["converted_string_mentions"] += 1
                        normalized_mentions.append(normalized)
                elif isinstance(raw_mention, dict):
                    raw_quote = raw_mention.get("quote")
                    normalized, repair_error = _normalize_dict_mention(
                        raw_mention,
                        entity_id=entity_id,
                        mention_index=mention_index,
                        segment_text=segment_text,
                    )
                    if normalized != raw_mention:
                        diagnostics["adapter_applied"] = True
                        diagnostics["changed_dict_mentions"] += 1
                    repaired_quote = (
                        not isinstance(raw_quote, str) or not raw_quote.strip()
                    ) and repair_error is None
                    if repaired_quote:
                        diagnostics["repaired_dict_mentions"] += 1
                    if repair_error is not None:
                        diagnostics["unrepaired_dict_mentions"].append(
                            {
                                "entity_index": entity_index,
                                "mention_index": mention_index,
                                "reason": repair_error,
                            }
                        )
                    normalized_mentions.append(normalized)
                else:
                    diagnostics["unsupported_mention_shapes"].append(
                        {
                            "entity_index": entity_index,
                            "mention_index": mention_index,
                            "type": type(raw_mention).__name__,
                        }
                    )
        elif raw_mentions is not None:
            diagnostics["unsupported_mention_shapes"].append(
                {"entity_index": entity_index, "type": type(raw_mentions).__name__}
            )

        normalized_entity = {
            **raw_entity,
            "entity_id": entity_id,
            "canonical_name": canonical_name,
            "entity_type": entity_type,
            "mentions": normalized_mentions,
        }
        normalized_entity.pop("name", None)
        normalized_entity.pop("type", None)
        normalized_entity.pop("entity", None)
        normalized_entities.append(normalized_entity)

    diagnostics["normalized_entity_count"] = len(normalized_entities)
    return {**tool_result, "entities": normalized_entities}, diagnostics
