"""Gather-time text normalization for extracted story bodies.

This module applies the conservative, measured repair rules from
``lcats.analysis.corpus.repairs`` to a story body at gather time, before the
story JSON is first written. Because ``data/`` is cleared and regenerated
after major changes, repairs must be replayable inputs to regeneration rather
than one-off edits to stored files (see WS-SPECIALS-CLEANUP).

The hook reuses the same suggestion/apply code path as ``lcats
repair-specials``, so the dry-run report and the applied normalization always
agree. It is idempotent: a body with no mojibake findings yields no
suggestions and is returned unchanged.
"""

import collections

from lcats.analysis.corpus import repairs

# Identifies which rule set produced a story's normalization provenance, so a
# regenerated corpus can be traced back to the rules that shaped it.
RULE_SOURCE = "lcats.analysis.corpus.repairs.DEFAULT_REPAIR_RULES"


def normalize_body(body, rules=repairs.DEFAULT_REPAIR_RULES):
    """Return ``(normalized_body, applied)`` for one story body.

    ``applied`` is a deterministic list of ``{"rule_id", "replacement",
    "count"}`` dicts, one per rule that fired, sorted by ``rule_id``. When no
    rule fires the original ``body`` object is returned unchanged and
    ``applied`` is empty.

    Args:
        body: The extracted story body text.
        rules: Repair rules to apply (defaults to the measured rule table).

    Returns:
        A tuple of the normalized body and the applied-rule provenance list.
    """
    if not isinstance(body, str):
        return body, []

    suggestions = repairs.suggest_repairs_for_text(body, rules=rules)
    if not suggestions:
        return body, []

    normalized = repairs.apply_repair_suggestions(body, suggestions)

    counts = collections.Counter()
    replacements = {}
    for suggestion in suggestions:
        counts[suggestion.rule_id] += 1
        replacements[suggestion.rule_id] = suggestion.replacement_text

    applied = [
        {
            "rule_id": rule_id,
            "replacement": replacements[rule_id],
            "count": counts[rule_id],
        }
        for rule_id in sorted(counts)
    ]
    return normalized, applied


def normalize_story_dict(data_to_save, rules=repairs.DEFAULT_REPAIR_RULES):
    """Normalize the ``body`` field of a story dict in place, recording provenance.

    The story ``body`` is replaced with its normalized form. When one or more
    rules fire and ``metadata`` is a dict, a ``normalization`` provenance block
    is added under ``metadata``. Stories with no findings are left untouched,
    including their metadata, so clean output stays byte-identical.

    Args:
        data_to_save: The story dict (``name``/``body``/``metadata``) about to
            be written to JSON.
        rules: Repair rules to apply (defaults to the measured rule table).

    Returns:
        The same ``data_to_save`` dict, mutated in place.
    """
    body = data_to_save.get("body")
    normalized, applied = normalize_body(body, rules=rules)
    if not applied:
        return data_to_save

    data_to_save["body"] = normalized
    metadata = data_to_save.get("metadata")
    if isinstance(metadata, dict):
        metadata["normalization"] = {
            "rule_source": RULE_SOURCE,
            "rules_applied": applied,
        }
    return data_to_save
