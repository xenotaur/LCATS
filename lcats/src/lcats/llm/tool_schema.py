"""Shared helpers for hardening Anthropic tool-use JSON schemas to strict mode."""

from __future__ import annotations

from typing import Any, Dict


def close_schema_objects(node: Any) -> Any:
    """Recursively return a deep copy of a JSON Schema fragment with
    additionalProperties: false set on every object (top-level and
    nested) - required by Anthropic's strict tool use before strict: true
    takes effect. See strict_tool_schema()'s docstring for why this is
    needed.

    Sets additionalProperties unconditionally (not via setdefault) so an
    existing, looser value (e.g. additionalProperties: true, or a schema
    rather than a bare bool) can't silently defeat the requirement this
    exists to enforce. Also matches "object" inside a union `type` list
    (e.g. `type: ["object", "null"]`), not just a bare `type: "object"`
    string, since JSON Schema permits either form.
    """
    if isinstance(node, dict):
        closed = {key: close_schema_objects(value) for key, value in node.items()}
        node_type = closed.get("type")
        is_object = node_type == "object" or (
            isinstance(node_type, list) and "object" in node_type
        )
        if is_object:
            closed["additionalProperties"] = False
        return closed
    if isinstance(node, list):
        return [close_schema_objects(item) for item in node]
    return node


def strict_tool_schema(tool_schema: Dict[str, Any]) -> Dict[str, Any]:
    """Return a deep copy of `tool_schema` with strict: true enabled.

    Without strict: true, Anthropic's tool use does not guarantee the
    model's tool_use input matches input_schema - "Claude might return
    incompatible types ... or omit required fields, breaking your
    functions and causing runtime errors" (Anthropic docs, Strict tool
    use). This is exactly what happened live: a relations array item came
    back as a plain string instead of the required object, crashing
    relation_extractor.build_relations()'s `raw.get("quote", ...)` with
    AttributeError. Enabling strict: true constrains the model's token
    sampling to schema-valid output via grammar-constrained sampling,
    which would have prevented that malformed item outright.

    strict: true additionally requires additionalProperties: false on
    every object in the schema, including nested ones inside array items
    (Anthropic docs, JSON Schema limitations) - close_schema_objects()
    adds it here so every schema-defining module can wrap its own
    constant at definition time instead of hand-writing
    additionalProperties at every nesting level.

    The returned dict's top-level `strict` key is inert (never read) for
    OpenAIBackend.complete(), which only forwards `input_schema` as its
    function `parameters` - see openai_backend.py. The
    additionalProperties: false this adds inside input_schema does reach
    OpenAI's schema too; this is intentional here (unlike the narrower,
    --backend anthropic-gated runtime override this function's callers
    replace) since the schemas are meant to be strict at the source for
    both backends.
    """
    schema = close_schema_objects(tool_schema)
    schema["strict"] = True
    return schema
