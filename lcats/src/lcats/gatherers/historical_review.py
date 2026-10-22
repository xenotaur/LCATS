"""Explain historical differences without editing either compared text.

The typography rule preserves source scene separators in the selected output.
A comparison-only projection reproduces the legacy omission; it is never the
published text. Exact whole-string equality after this finite projection proves
that no other characters differ. This is historical evidence, not a literary
assessment or authority to publish. Callers must validate source/selection hashes,
normalization context and publication readiness independently.
"""

import re

from lcats.gatherers import readiness

RULE = "source-preserved-typography-v1"
MAX_CHARACTERS = 4_000_000
# Match one complete, blank-line-delimited paragraph. The old parser discarded
# any paragraph containing this pattern; deliberately do NOT reproduce its
# dangerous substring deletion of paragraphs containing narrative as well.
_SEPARATOR = re.compile(
    r"(?m)(?<=\n\n)       \*       \*       \*       \*       \*(?=\n\n)"
)
_BOUNDARY = " \t\n"


def _piece(text, start, end, kind):
    return {
        "span": [start, end],
        "kind": kind,
        "sha256": readiness.text_sha256(text[start:end]),
        "text": text[start:end],
    }


def _projection(text, *, separators):
    """Return comparison-only text and a complete record of ignored ranges."""
    left = len(text) - len(text.lstrip(_BOUNDARY))
    right = len(text.rstrip(_BOUNDARY))
    pieces = []
    if left:
        pieces.append(_piece(text, 0, left, "boundary_whitespace"))
    if right < len(text) and right >= left:
        pieces.append(_piece(text, right, len(text), "boundary_whitespace"))
    if separators:
        pieces.extend(
            _piece(text, m.start(), m.end(), "preserved_scene_separator")
            for m in _SEPARATOR.finditer(text)
            if left <= m.start() < m.end() <= right
        )
    pieces.sort(key=lambda p: p["span"])
    cursor, retained = 0, []
    for piece in pieces:
        start, end = piece["span"]
        retained.append(text[cursor:start])
        cursor = end
    retained.append(text[cursor:])
    return "".join(retained), pieces


def explain_typography(selected, historical):
    """Return exact historical accounting and diagnostic residual shape.

    Args:
        selected: Exact reconstructed source text, before normalization.
        historical: Verified historical baseline text in the same text domain.

    Returns:
        JSON evidence binding both texts, all comparison-only ranges and the
        projection hashes. ``complete`` means the finite explanation covers the
        whole difference; it never implies publication approval. Residual shape
        labels describe exact relationships, never editorial roles.

    Raises:
        ValueError: Inputs are not strings or exceed the bounded text budget.
    """
    if any(
        not isinstance(t, str) or len(t) > MAX_CHARACTERS
        for t in (selected, historical)
    ):
        raise ValueError("historical comparison requires bounded strings")
    projected, selected_ranges = _projection(selected, separators=True)
    baseline, historical_ranges = _projection(historical, separators=False)
    equal = selected == historical
    complete = bool(projected and baseline) and (equal or projected == baseline)
    # Diagnostic substring matches help rank review groups but carry no approval
    # authority. In particular, an added prefix may be a blurb OR narrative.
    prefix = suffix = None
    if complete:
        shape = "exact_equality" if equal else "explained_typography"
    elif baseline and baseline in projected:
        at = projected.index(baseline)
        prefix, suffix = at, len(projected) - at - len(baseline)
        shape = "additional_boundary_text"
    elif projected and projected in baseline:
        shape = "missing_boundary_text"
    else:
        shape = "mixed_or_unclassified"
    return {
        "schema_version": 1,
        "rule": RULE,
        "offset_basis": "each_input_unicode_characters",
        "selected_sha256": readiness.text_sha256(selected),
        "historical_sha256": readiness.text_sha256(historical),
        "selected_characters": len(selected),
        "historical_characters": len(historical),
        "comparison_selected_sha256": readiness.text_sha256(projected),
        "comparison_historical_sha256": readiness.text_sha256(baseline),
        "selected_comparison_ranges": selected_ranges,
        "historical_comparison_ranges": historical_ranges,
        "complete": complete,
        "residual_shape": shape,
        "additional_prefix_characters": prefix,
        "additional_suffix_characters": suffix,
        "publication_approved": False,
    }
