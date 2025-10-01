"""Processor factories for file / corpus analysis."""

from typing import Any, Callable, Dict

from lcats.analysis import scene_analysis
from lcats.analysis import story_analysis


def story_summarizer(data: Dict[str, Any]) -> Dict[str, Any]:
    """Transform a story JSON object into a compact summary.

    Args:
        data: Parsed story JSON (expects keys like 'name', 'author', 'body').

    Returns:
        A JSON-serializable dict with:
            - title: str
            - authors: List[str]
            - body_length_chars: int
            - body_length_words: int
            - top_keywords: List[{"term": str, "count": int}]
    """
    title = data.get("name", "<Untitled>")
    authors = story_analysis.extract_authors(
        data.get("author") or (data.get("metadata") or {}).get("author")
    )

    body = story_analysis.coerce_text(data.get("body", ""))
    body_chars = len(body)
    word_count = story_analysis.word_count(body)
    encoder = story_analysis.get_encoder()
    token_count = story_analysis.token_count(body, encoder)
    paragraph_count = story_analysis.count_paragraph(body)
    keywords = story_analysis.get_keywords(body)
    top_keywords = story_analysis.top_keywords(keywords, k=5)

    summary: Dict[str, Any] = {
        "title": title,
        "authors": authors,
        "body_length_chars": body_chars,
        "body_length_words": word_count,
        "body_length_tokens": token_count,
        "body_length_paragraphs": paragraph_count,
        "top_keywords": top_keywords,
    }
    return summary


def make_annotated_segment_extractor(
    client: Any,
    *,
    segment_model: str = "gpt-4o",
    semantic_model: str = "gpt-4o",
    include_validation: bool = True,
) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    """Create a processor_function that returns annotated segments for a story.

    The returned callable accepts one story JSON (dict) and returns a JSON-
    serializable dict containing the extracted segments annotated with a
    per-segment semantic judgment.

    Args:
        client: OpenAI-like client (supports chat.completions.create).
        segment_model: Model name to use for story-level segmentation.
        semantic_model: Model name to use for per-segment semantic labeling.
        include_validation: If True, include segmentation validation report.

    Returns:
        A callable `processor_function(data: Dict[str, Any]) -> Dict[str, Any]`
        suitable for use with `process_file(s)`.

    Raises:
        None at factory time. Runtime exceptions inside the processor are
        captured into an `"error"` string in the returned payload.
    """
    seg_extractor = scene_analysis.make_segment_extractor(client)
    sem_extractor = scene_analysis.make_semantics_extractor(client)

    def processor_function(data: Dict[str, Any]) -> Dict[str, Any]:
        """Produce annotated segments for a single story JSON.

        Args:
            data: Story JSON object with keys like 'name', 'author', 'body',
                and optional 'metadata'.

        Returns:
            JSON-serializable dict with:
                {
                  "title": str,
                  "authors": List[str],
                  "models": {
                    "segment_model": str,
                    "semantic_model": str
                  },
                  "segmentation": {
                    "parsing_error": Optional[str],
                    "extraction_error": Optional[str],
                    "alignment_error": Optional[str],
                    "validation_report": Optional[dict]
                  },
                  "segments": List[dict]  # each segment annotated with 'semantic'
                }

            On unexpected errors, an "error" string is included alongside any
            partial results that were obtained before the error.
        """
        title = data.get("name", "<Untitled>")
        authors = story_analysis.extract_authors(data.get("author"))
        body = story_analysis.coerce_text(data.get("body", ""))
        body_chars = len(body)
        word_count = story_analysis.word_count(body)
        paragraph_count = story_analysis.count_paragraph(body)
        encoder = story_analysis.get_encoder()
        token_count = story_analysis.token_count(body, encoder)
        keywords = story_analysis.get_keywords(body)
        top_keywords = story_analysis.top_keywords(keywords, k=5)

        result: Dict[str, Any] = {
            "title": title,
            "authors": authors,
            "body_length_chars": body_chars,
            "body_length_words": word_count,
            "body_length_tokens": token_count,
            "body_length_paragraphs": paragraph_count,
            "top_keywords": top_keywords,

            "models": {
                "segment_model": segment_model,
                "semantic_model": semantic_model,
            },
            "segmentation": {
                "parsing_error": None,
                "extraction_error": None,
                "alignment_error": None,
                "validation_report": None,
            },
            "segments": [],
        }

        try:
            # 1) Story-level segmentation (with alignment + optional validation).
            seg_extraction = seg_extractor.extract(
                body, model_name=segment_model)
            segments = seg_extraction.get("extracted_output") or []
            result["segmentation"]["parsing_error"] = seg_extraction.get(
                "parsing_error")
            result["segmentation"]["extraction_error"] = seg_extraction.get(
                "extraction_error"
            )
            result["segmentation"]["alignment_error"] = seg_extraction.get(
                "alignment_error"
            )
            if include_validation:
                result["segmentation"]["validation_report"] = seg_extraction.get(
                    "validation_report"
                )

            # 2) Per-segment semantic judgments (text-only, no external labels).
            annotated = scene_analysis.annotate_segments_with_semantics(
                story_text=body,
                segments=segments,
                extractor=sem_extractor,
                model_name=semantic_model,
            )
            result["segments"] = annotated

        except Exception as exc:  # noqa: BLE001
            # Capture error but keep whatever partial results exist.
            result["error"] = f"{type(exc).__name__}: {exc}"

        return result

    return processor_function
