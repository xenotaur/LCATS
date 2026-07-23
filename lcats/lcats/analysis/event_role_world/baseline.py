"""Fixed-chunk-vs-segment baseline comparison.

Per the governing proposal's "Cost and baseline requirements" section: a
genre-comparison claim built on scene/sequel segments is not publishable
without a control showing the effect is not an artifact of chunking
strategy. This module produces fixed-token chunks over the same story text
and lets the same extractor pipeline run over both, so callers can compare
normalized rates (entities/1000 words, events/1000 words, ...) between the
two chunking strategies.
"""

from __future__ import annotations

from typing import Any, Dict, List

from lcats.analysis import story_analysis
from lcats.analysis.event_role_world import schema


def make_fixed_token_chunks(
    text: str, chunk_size_tokens: int = 500
) -> List[Dict[str, Any]]:
    """Split `text` into contiguous, non-overlapping fixed-token chunks.

    Args:
        text: Full story text to chunk.
        chunk_size_tokens: Target token count per chunk (final chunk may be
            shorter).

    Returns:
        A list of dicts shaped like scene/sequel segments (segment_id,
        segment_type, start_char, end_char) so the same pipeline machinery
        can consume either. segment_type is always "fixed_chunk".
    """
    if not text:
        return []

    encoder = story_analysis.get_encoder()
    tokens = encoder.encode(text)
    chunks: List[Dict[str, Any]] = []

    chunk_id = 1
    for token_start in range(0, len(tokens), chunk_size_tokens):
        token_end = min(token_start + chunk_size_tokens, len(tokens))
        chunk_tokens = tokens[token_start:token_end]
        chunk_text = encoder.decode(chunk_tokens)

        # Locate this decoded chunk's char span within the original text.
        # tiktoken decode/encode round-trips are not always byte-identical
        # to a naive substring search, so anchor on the first token's
        # decoded text (short and reliably findable) rather than the full
        # chunk, then extend by the chunk's decoded length.
        anchor = encoder.decode(chunk_tokens[:1]) if chunk_tokens else ""
        search_from = chunks[-1]["end_char"] if chunks else 0
        start_char = text.find(anchor, search_from) if anchor else search_from
        if start_char < 0:
            start_char = search_from
        end_char = min(len(text), start_char + len(chunk_text))

        chunks.append(
            {
                "segment_id": chunk_id,
                "segment_type": "fixed_chunk",
                "start_char": start_char,
                "end_char": end_char,
            }
        )
        chunk_id += 1

    return chunks


def _rate_per_1000_words(count: int, word_count: int) -> float:
    """Normalize a raw count to a per-1000-word rate."""
    if word_count <= 0:
        return 0.0
    return (count / word_count) * 1000.0


def summarize_annotations(
    annotations: List[schema.SegmentWorldAnnotation],
) -> Dict[str, Any]:
    """Compute normalized rates for a list of segment/chunk annotations.

    Args:
        annotations: SegmentWorldAnnotation instances produced by running
            the pipeline over either scene/sequel segments or fixed chunks.

    Returns:
        A dict with unit_count, total_word_count, and per-1000-word rates
        for entities, events, temporal_anchors, and spatial_anchors.
    """
    total_words = sum(
        (a.surface_features.word_count if a.surface_features else 0)
        for a in annotations
    )
    total_entities = sum(len(a.entities) for a in annotations)
    total_events = sum(len(a.events) for a in annotations)
    total_temporal = sum(len(a.temporal_anchors) for a in annotations)
    total_spatial = sum(len(a.spatial_anchors) for a in annotations)

    return {
        "unit_count": len(annotations),
        "total_word_count": total_words,
        "entities_per_1000_words": _rate_per_1000_words(total_entities, total_words),
        "events_per_1000_words": _rate_per_1000_words(total_events, total_words),
        "temporal_anchors_per_1000_words": _rate_per_1000_words(
            total_temporal, total_words
        ),
        "spatial_anchors_per_1000_words": _rate_per_1000_words(
            total_spatial, total_words
        ),
    }


def compare_chunking_strategies(
    segment_annotations: List[schema.SegmentWorldAnnotation],
    chunk_annotations: List[schema.SegmentWorldAnnotation],
) -> Dict[str, Any]:
    """Compare normalized rates between segment-based and fixed-chunk runs.

    Args:
        segment_annotations: Annotations from running the pipeline over
            scene/sequel segments.
        chunk_annotations: Annotations from running the same pipeline over
            fixed-token chunks of the same story.

    Returns:
        A dict with "segment" and "fixed_chunk" summaries (see
        summarize_annotations) so a caller can see whether entity/event/
        anchor rates diverge between chunking strategies.
    """
    return {
        "segment": summarize_annotations(segment_annotations),
        "fixed_chunk": summarize_annotations(chunk_annotations),
    }
