"""Experimental, non-production prompt variant for WI-SEGMENT-0101.

`scene_analysis.SCENE_SEQUEL_SYSTEM_PROMPT` documents `start_par_id`/
`end_par_id` and `start_exact`/`end_exact` as two independently-generated
"location selectors" with no instruction requiring them to agree
(`lcats/src/lcats/analysis/scene_analysis.py:99-105`). WI-SEGMENT-0098
found this lets them silently drift apart: the model's claimed
`end_par_id` undercounts by 1-2 paragraphs relative to where its own
`end_exact` text actually lands, in 6 of 10 real alignment failures.

This module defines a REWORDED variant of only the location-selector
instructions - `start_par_id`/`end_par_id` are redefined as values the
model must derive from `start_exact`/`end_exact`'s own location, with an
explicit first-character/last-character rule for anchors that themselves
straddle a paragraph break (review finding, PR #415, on
`the_voice_in_the_fog__leverage` segment 3). This is deliberately NOT an
edit to `scene_analysis.SCENE_SEQUEL_SYSTEM_PROMPT` - per WI-SEGMENT-0101's
own `forbidden_actions: implement_production_prompt_change`, the reworded
text lives only here, as an isolated variant for the ablation.

Every other part of the pipeline (user prompt template, tool schema,
alignment/validation, paragraph indexer) is reused unchanged from
`scene_analysis`/`text_segmenter`, so the ablation isolates exactly one
variable: the wording of these four bullet points.
"""

from __future__ import annotations

from typing import Any, Dict, List

from lcats.analysis import llm_extractor
from lcats.analysis import scene_analysis
from lcats.analysis import text_segmenter

_ORIGINAL_LOCATION_SELECTOR_BLOCK = """\
# --- Robust location selectors (PRIMARY) ---
- start_par_id: integer paragraph id where the segment begins (inclusive).
- end_par_id: integer paragraph id where the segment ends (inclusive).
- start_exact: the FIRST ≤120 characters of the segment, COPIED VERBATIM from the STORY text.
- end_exact: the LAST ≤120 characters of the segment, COPIED VERBATIM from the STORY text.
- start_prefix: ≤60 characters immediately BEFORE start_exact in the STORY ("" if none).
- end_suffix: ≤60 characters immediately AFTER end_exact in the STORY ("" if none).

Rules for anchors:
- Copy characters EXACTLY as they appear in the STORY (whitespace/punctuation included).
- Do NOT include paragraph id markers like [P0001] in start_exact/end_exact/prefix/suffix.\
"""

_REWORDED_LOCATION_SELECTOR_BLOCK = """\
# --- Robust location selectors (PRIMARY) ---
- start_exact: the FIRST ≤120 characters of the segment, COPIED VERBATIM from the STORY text.
- end_exact: the LAST ≤120 characters of the segment, COPIED VERBATIM from the STORY text.
- start_par_id: the [PNNNN] paragraph marker number of the paragraph that contains
  the FIRST character of start_exact. Do NOT judge this independently of
  start_exact: first locate start_exact's exact position in the STORY text, then
  read off the paragraph marker that covers that position.
- end_par_id: the [PNNNN] paragraph marker number of the paragraph that contains
  the LAST character of end_exact. If end_exact's text spans more than one
  paragraph, use the paragraph containing its LAST character, not its first.
  Do NOT judge this independently of end_exact: first locate end_exact's exact
  position in the STORY text, then read off the paragraph marker that covers
  its final character.
- start_prefix: ≤60 characters immediately BEFORE start_exact in the STORY ("" if none).
- end_suffix: ≤60 characters immediately AFTER end_exact in the STORY ("" if none).

Rules for anchors:
- Copy characters EXACTLY as they appear in the STORY (whitespace/punctuation included).
- Do NOT include paragraph id markers like [P0001] in start_exact/end_exact/prefix/suffix.
- start_par_id and end_par_id MUST be physically derived from where start_exact/
  end_exact are actually located in the STORY text - NOT from which narrative
  scene or beat you judge the text to "belong to". Two paragraphs can belong to
  the same scene while still being different paragraph numbers; report the
  number, not the scene grouping.\
"""


def _build_reworded_system_prompt() -> str:
    original = scene_analysis.SCENE_SEQUEL_SYSTEM_PROMPT
    if _ORIGINAL_LOCATION_SELECTOR_BLOCK not in original:
        raise ValueError(
            "SCENE_SEQUEL_SYSTEM_PROMPT no longer contains the expected "
            "location-selector block verbatim - this experimental variant "
            "is out of sync with production and must be re-derived, not "
            "silently applied against stale assumptions."
        )
    return original.replace(
        _ORIGINAL_LOCATION_SELECTOR_BLOCK, _REWORDED_LOCATION_SELECTOR_BLOCK
    )


REWORDED_SYSTEM_PROMPT = _build_reworded_system_prompt()


def _result_aligner(
    parsed_output: Dict[str, Any], story_text: str, index_meta: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Duplicated from scene_analysis._segment_result_aligner (private,
    not imported directly - see module docstring) so this experimental
    script does not depend on another module's private API surface."""
    aligned = text_segmenter.segments_result_aligner(
        parsed_output, story_text, index_meta
    )
    return list(aligned.get("segments") or [])


def _result_validator(
    parsed_output: List[Dict[str, Any]], story_text: str, index_meta: Dict[str, Any]
) -> Dict[str, Any]:
    """Duplicated from scene_analysis._segment_result_validator - see
    _result_aligner's docstring."""
    return text_segmenter.segments_auditor(
        {"segments": parsed_output}, story_text, index_meta
    )


def make_reworded_segment_extractor(
    backend: Any, max_tokens: int = 16384
) -> llm_extractor.JSONPromptExtractor:
    """Build a JSONPromptExtractor identical to
    scene_analysis.make_segment_extractor except for the reworded
    location-selector instructions above - every other prompt section,
    the tool schema, the paragraph indexer, and the alignment/validation
    logic are the unchanged production versions, so the ablation isolates
    exactly one variable."""
    return llm_extractor.JSONPromptExtractor(
        backend,
        system_prompt=REWORDED_SYSTEM_PROMPT,
        user_prompt_template=scene_analysis.SCENE_SEQUEL_USER_PROMPT_TEMPLATE,
        output_key="segments",
        default_model="gpt-4o",
        temperature=0.2,
        max_tokens=max_tokens,
        text_indexer=text_segmenter.paragraph_text_indexer,
        result_aligner=_result_aligner,
        result_validator=_result_validator,
        tool_schema=scene_analysis.SEGMENT_TOOL_SCHEMA,
    )
