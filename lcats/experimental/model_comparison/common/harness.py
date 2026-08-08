"""Shared benchmark harness reused by every candidate/*/benchmark.py.

Each candidate directory (anthropic_opus/, ollama_qwen3_8b/, ...) builds its
own LLMBackend and calls this module's run_*() functions with it, so adding
a new model to compare means adding one new directory, not touching this
file.

Three stages covered so far: run_entity_extraction() (stage 3 of the
Event-Role-World pipeline - see
experiments/03_cross_segment_relation_pilot/run_pilot.py), run_genre_detection()
(the corpus-quality-assessor's detect mode), and run_segmentation() (the
scene/sequel segmenter). Each reuses the exact production call path
(JSONPromptExtractor.extract() or corpus_assess.assess_story()'s own
backend.complete() call), not a synthetic schema, so a "does this
backend/model handle our actual tool schema" answer here transfers
directly. Event/relation/discourse extraction and the cross-segment pass
remain uncovered - widen the same way if/when needed.

Uses a REAL, single scene/sequel segment (see sample_segment.json,
generated once by generate_sample_segment.py from the real stage-1
segmenter) rather than a whole story - entity_extractor's own system
prompt describes its input as "a segment of a story"
(entity_extractor.py's ENTITY_SYSTEM_PROMPT), and the real pipeline
(run_pilot.py's _run_erw_extraction) only ever passes one segment to this
extractor, never a full story. Benchmarking against the wrong input size
inflated cost/latency for every candidate and gave a smaller/weaker local
model a harder, more diffuse task than it will ever actually face.
"""

from __future__ import annotations

import dataclasses
import json
import pathlib
import sys
import time

from typing import Any, Dict, Optional

# Path bootstrap - allow running `python <candidate>/benchmark.py` directly
# without a prior `pip install -e .`, matching
# experiments/03_cross_segment_relation_pilot/run_pilot.py's convention.
_LCATS_SRC = pathlib.Path(__file__).resolve().parents[3] / "src"
if str(_LCATS_SRC) not in sys.path:
    sys.path.insert(0, str(_LCATS_SRC))

from lcats.analysis.corpus import assess as corpus_assess  # noqa: E402
from lcats.analysis.event_role_world import entity_extractor as erw_entity  # noqa: E402
from lcats.analysis import scene_analysis  # noqa: E402
from lcats.llm import backend as llm_backend  # noqa: E402

# A real, single scene/sequel segment - see this module's docstring and
# generate_sample_segment.py. Regenerate only if DEFAULT_SAMPLE_STORY
# (below) changes.
DEFAULT_SAMPLE_SEGMENT = pathlib.Path(__file__).resolve().parent / "sample_segment.json"

# The whole story generate_sample_segment.py drew DEFAULT_SAMPLE_SEGMENT
# from - kept only for that regeneration step, not used as benchmark input
# directly (see the module docstring for why a whole story is the wrong
# input size for this stage).
DEFAULT_SAMPLE_STORY = (
    pathlib.Path(__file__).resolve().parents[3].parent
    / "corpora"
    / "sherlock"
    / "five_orange_pips"
    / "story.json"
)

# A middle ground: entity_extractor.make_entity_extractor()'s own factory
# default (4096) turned out too low even for claude-opus-4-8 on a real
# ~600-word segment - confirmed live, it truncated
# (TruncatedResponseError) with entities/mentions/quotes still mid-
# generation - which is exactly why run_pilot.py raises it to 16384 in
# the first place (its own comment: "JSONPromptExtractor's own default
# (4096) is far below what a content-dense segment can need"). But
# 16384 (run_pilot.py's _ERW_MAX_TOKENS, tuned for whole-story-sized
# input) let one local-model run ramble for ~29 minutes before finally
# emitting a tool call on the old, oversized whole-story input this
# harness used to send. 8192 is a segment-appropriate middle ground,
# confirmed sufficient for both candidates on the real sample segment.
DEFAULT_MAX_TOKENS = 8192

# entity_extractor.py's own factory default. Appropriate for Anthropic/
# OpenAI's mature structured-output paths, but well below Qwen3's own
# officially recommended sampling settings (temperature 0.6 thinking /
# 0.7 non-thinking - see https://huggingface.co/Qwen/Qwen3-8B) and below
# Ollama's own bundled Modelfile default for qwen3:8b (`ollama show
# qwen3:8b --parameters` on this machine reports temperature 0.6, top_k
# 20, top_p 0.95, i.e. Ollama already ships the model card's own
# recommendation - our request's explicit `temperature=0.2` was
# overriding a better-tuned default). Qwen3's model card explicitly warns
# against near-greedy decoding: "Do NOT use greedy decoding, as it can
# lead to performance degradation and endless repetitions." Candidates
# for models with their own documented sampling recommendation should
# override this via `temperature=` rather than inherit the pipeline's
# Anthropic/OpenAI-tuned default.
DEFAULT_TEMPERATURE = 0.2

# Truncated in results.json so a failed/malformed run can be diagnosed
# after the fact without needing a live rerun (the prior version of this
# harness discarded raw model output entirely).
_RAW_OUTPUT_PREVIEW_CHARS = 4000

# corpus_assess.assess_story()'s own factory default. A genre-detection
# call's response (verdict/genre/summary/issues) is far smaller than an
# entity-extraction tool call, so the entity-extraction-tuned
# DEFAULT_MAX_TOKENS (8192) is not assumed to transfer - see this WI's
# Risk Notes.
DEFAULT_GENRE_MAX_TOKENS = 4096

# scene_analysis.make_segment_extractor()'s own factory default, tuned
# against real corpus stories (WI-ANNOTATE-0050) - a segmentation
# response covers every segment in the whole story, not one segment's
# worth of entities, so this is intentionally much higher than
# DEFAULT_MAX_TOKENS.
DEFAULT_SEGMENTATION_MAX_TOKENS = 16384

# Appended to the segmentation system prompt on retry only, after a first
# attempt fails with error_type="no_tool_call" (Ollama's tool_choice
# silently ignored despite the model producing schema-shaped free text -
# see WI-LLM-0051). WI-LLM-0051 tested this exact mitigation live: 0/5
# baseline attempts succeeded, 2/5 succeeded with this reminder appended
# - a real, substantial (not total) improvement, not a guaranteed fix.
# Investigated but explicitly not tried: falling back to Ollama's native
# /api/chat endpoint for the retry (WI-LLM-0051's other named strategy) -
# out of this pass's scope, left as a follow-up if the reminder alone
# proves insufficient at scale.
_SEGMENTATION_RETRY_REMINDER = (
    "\n\nCRITICAL INSTRUCTION: You MUST call the record_segments "
    "function/tool to submit your answer. Do NOT reply with plain text "
    "or a JSON object in your message content - your response will be "
    "discarded and considered a failure unless it is a function/tool "
    "call to record_segments."
)


@dataclasses.dataclass
class BenchmarkResult:
    """One candidate's outcome for one stage/segment - written to results.json."""

    candidate: str
    backend_kind: str
    model: str
    story_name: str
    stage: str
    success: bool
    latency_seconds: float
    input_tokens: int = 0
    output_tokens: int = 0
    entity_count: Optional[int] = None
    segment_count: Optional[int] = None
    detected_genre: Optional[str] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    raw_output_preview: Optional[str] = None
    # Set only by run_segmentation()'s retry path (WI-LLM-0051). None
    # when no retry was attempted (first call succeeded, or failed for a
    # reason other than error_type="no_tool_call" that a reminder
    # wouldn't plausibly fix).
    retry_attempted: bool = False
    retry_succeeded: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


def load_sample_story(path: pathlib.Path = DEFAULT_SAMPLE_STORY) -> tuple:
    """Return (story_name, story_body) from a story.json ({name, body, metadata}).

    Used by generate_sample_segment.py to regenerate DEFAULT_SAMPLE_SEGMENT,
    and directly as benchmark input by run_genre_detection()/
    run_segmentation() (both operate over a whole story, unlike
    run_entity_extraction(), which correctly uses a single segment).
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["name"], data["body"]


def load_sample_segment(path: pathlib.Path = DEFAULT_SAMPLE_SEGMENT) -> tuple:
    """Return (label, segment_text) from a sample_segment.json fixture.

    `label` combines the source story name and segment type/id for
    result readability, e.g. "Sherlock Holmes - The Five Orange Pips
    [segment 3, dramatic_sequel]".
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    label = (
        f"{data['source_story']} "
        f"[segment {data['segment_id']}, {data['segment_type']}]"
    )
    return label, data["body"]


def run_entity_extraction(
    *,
    candidate: str,
    backend_kind: str,
    backend: llm_backend.LLMBackend,
    model: str,
    segment_path: pathlib.Path = DEFAULT_SAMPLE_SEGMENT,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = DEFAULT_TEMPERATURE,
) -> BenchmarkResult:
    """Run the real ERW stage-3 entity extractor's tool-schema call once.

    Uses the same make_entity_extractor()/extract() path run_pilot.py's real
    pipeline uses - the only things a candidate substitutes are `backend`,
    `model`, and optionally `temperature` (see DEFAULT_TEMPERATURE's
    docstring - override this for models with their own documented
    sampling recommendation).
    """
    story_name, segment_text = load_sample_segment(segment_path)

    extractor = erw_entity.make_entity_extractor(backend)
    extractor.default_model = model
    extractor.max_tokens = max_tokens
    extractor.temperature = temperature

    start = time.monotonic()
    try:
        result = extractor.extract(segment_text, model_name=model)
    except Exception as exc:  # noqa: BLE001 - benchmark harness records, not raises
        latency = time.monotonic() - start
        return BenchmarkResult(
            candidate=candidate,
            backend_kind=backend_kind,
            model=model,
            story_name=story_name,
            stage="entity_extraction",
            success=False,
            latency_seconds=latency,
            error_type=type(exc).__name__,
            error_message=str(exc),
        )
    latency = time.monotonic() - start

    api_error = result.get("api_error")
    parsed = result.get("extracted_output") or result.get("parsed_output") or {}
    entities = parsed.get("entities") if isinstance(parsed, dict) else None
    usage = result.get("usage") or {}
    raw_output = result.get("raw_output") or ""

    # A tool call can come back schema-conformant enough to avoid api_error
    # (parses as JSON, no truncation) while still not matching
    # ENTITY_TOOL_SCHEMA - e.g. "entities" missing or not a list. That is
    # exactly the local-runtime tool-schema unreliability this harness
    # exists to catch, so it must not read as success.
    schema_error = None
    if api_error is None and not isinstance(entities, list):
        schema_error = "malformed_tool_result"

    return BenchmarkResult(
        candidate=candidate,
        backend_kind=backend_kind,
        model=model,
        story_name=story_name,
        stage="entity_extraction",
        success=api_error is None and schema_error is None,
        latency_seconds=latency,
        input_tokens=usage.get("input_tokens", 0) or 0,
        output_tokens=usage.get("output_tokens", 0) or 0,
        entity_count=len(entities) if isinstance(entities, list) else None,
        error_type=(api_error or {}).get("code") if api_error else schema_error,
        error_message=(
            (api_error or {}).get("message")
            if api_error
            else (
                "Tool result parsed but 'entities' was missing or not a "
                f"list (got {type(entities).__name__ if entities is not None else 'None'})."
                if schema_error
                else None
            )
        ),
        raw_output_preview=(raw_output[:_RAW_OUTPUT_PREVIEW_CHARS] or None),
    )


def run_genre_detection(
    *,
    candidate: str,
    backend_kind: str,
    backend: llm_backend.LLMBackend,
    model: str,
    story_path: pathlib.Path = DEFAULT_SAMPLE_STORY,
    max_tokens: int = DEFAULT_GENRE_MAX_TOKENS,
    temperature: float = DEFAULT_TEMPERATURE,
) -> BenchmarkResult:
    """Run the real genre-detection assessor once, in detect mode.

    Uses the same corpus_assess.assess_story() path lcats assess's detect
    mode uses - the only things a candidate substitutes are `backend`,
    `model`, and optionally `temperature`/`max_tokens` (see this module's
    DEFAULT_TEMPERATURE docstring - override for models with their own
    documented sampling recommendation). assess_story() never raises; it
    always returns an AssessmentResult, with `.error` set on any failure
    (file/API/parsing), so no try/except is needed here.

    `story_name` on the returned BenchmarkResult is the story.json's own
    human-readable `name` field (via load_sample_story()), matching
    run_segmentation()'s/run_entity_extraction()'s convention - not
    `AssessmentResult.title`, which is derived from the corpus bucket
    slug (`infer_story_title()`) and would otherwise make cross-stage
    result comparisons show a different label for the identical story
    (review finding, PR #249).
    """
    story_name, _ = load_sample_story(story_path)

    start = time.monotonic()
    result = corpus_assess.assess_story(
        story_path,
        genre="",
        backend=backend,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    latency = time.monotonic() - start

    success = not bool(result.error)
    return BenchmarkResult(
        candidate=candidate,
        backend_kind=backend_kind,
        model=model,
        story_name=story_name,
        stage="genre_detection",
        success=success,
        latency_seconds=latency,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        detected_genre=result.detected_genre if success else None,
        error_type="assessment_error" if not success else None,
        error_message=result.error or None,
    )


def _run_segmentation_once(
    *,
    candidate: str,
    backend_kind: str,
    backend: llm_backend.LLMBackend,
    model: str,
    story_name: str,
    story_text: str,
    max_tokens: int,
    temperature: float,
    system_prompt_suffix: str = "",
) -> BenchmarkResult:
    """One real scene/sequel segmentation tool-schema call. No retry logic.

    Uses the same make_segment_extractor()/extract() path the real
    stage-1 segmenter uses, against the whole story text (segmentation
    operates over an entire story, not a single segment - unlike
    run_entity_extraction(), which correctly uses a single segment as its
    input). extracted_output is a bare list of segment dicts (see
    scene_analysis.make_segment_extractor()'s docstring).
    """
    extractor = scene_analysis.make_segment_extractor(backend, max_tokens=max_tokens)
    extractor.default_model = model
    extractor.temperature = temperature
    if system_prompt_suffix:
        extractor.system_prompt = extractor.system_prompt + system_prompt_suffix

    start = time.monotonic()
    try:
        result = extractor.extract(story_text, model_name=model)
    except Exception as exc:  # noqa: BLE001 - benchmark harness records, not raises
        latency = time.monotonic() - start
        return BenchmarkResult(
            candidate=candidate,
            backend_kind=backend_kind,
            model=model,
            story_name=story_name,
            stage="segmentation",
            success=False,
            latency_seconds=latency,
            error_type=type(exc).__name__,
            error_message=str(exc),
        )
    latency = time.monotonic() - start

    api_error = result.get("api_error")
    extraction_error = result.get("extraction_error")
    alignment_error = result.get("alignment_error")
    validation_error = result.get("validation_error")
    extracted = result.get("extracted_output")
    usage = result.get("usage") or {}
    raw_output = result.get("raw_output") or ""

    # A tool call can come back structurally valid (no api_error) while
    # still not producing usable segments, in three distinct ways this
    # harness must not conflate with success:
    #   1. extraction_error/alignment_error/validation_error set -
    #      JSONPromptExtractor.extract() still returns the PRE-alignment
    #      extracted_output on an aligner/validator exception (it is
    #      truthy and would otherwise read as a successful benchmark run)
    #      - the exact bug corpus/annotate.py's real production scene path
    #      was fixed for (see annotate.py:211-215), reproduced here as a
    #      review finding (PR #249) rather than caught independently.
    #   2. extracted_output isn't a list at all - SEGMENT_TOOL_SCHEMA/the
    #      aligner's contract broken.
    #   3. extracted_output is an empty list - a schema-conformant call
    #      that segmented nothing is not a useful benchmark success,
    #      matching annotate.py's own `if error or not segments` check.
    schema_error = None
    if api_error is None:
        if extraction_error or alignment_error or validation_error:
            schema_error = "extraction_or_alignment_error"
        elif not isinstance(extracted, list):
            schema_error = "malformed_tool_result"
        elif not extracted:
            schema_error = "empty_segment_list"

    if api_error:
        error_message = (api_error or {}).get("message")
    elif schema_error == "extraction_or_alignment_error":
        error_message = (
            f"extraction_error={extraction_error!r}, "
            f"alignment_error={alignment_error!r}, "
            f"validation_error={validation_error!r}"
        )
    elif schema_error == "malformed_tool_result":
        error_message = (
            "Tool result parsed but extracted_output was not a list "
            f"(got {type(extracted).__name__ if extracted is not None else 'None'})."
        )
    elif schema_error == "empty_segment_list":
        error_message = "Tool call succeeded but returned zero segments."
    else:
        error_message = None

    return BenchmarkResult(
        candidate=candidate,
        backend_kind=backend_kind,
        model=model,
        story_name=story_name,
        stage="segmentation",
        success=api_error is None and schema_error is None,
        latency_seconds=latency,
        input_tokens=usage.get("input_tokens", 0) or 0,
        output_tokens=usage.get("output_tokens", 0) or 0,
        segment_count=len(extracted) if isinstance(extracted, list) else None,
        error_type=(api_error or {}).get("code") if api_error else schema_error,
        error_message=error_message,
        raw_output_preview=(raw_output[:_RAW_OUTPUT_PREVIEW_CHARS] or None),
    )


def run_segmentation(
    *,
    candidate: str,
    backend_kind: str,
    backend: llm_backend.LLMBackend,
    model: str,
    story_path: pathlib.Path = DEFAULT_SAMPLE_STORY,
    max_tokens: int = DEFAULT_SEGMENTATION_MAX_TOKENS,
    temperature: float = DEFAULT_TEMPERATURE,
    retry_with_reminder: bool = True,
) -> BenchmarkResult:
    """Run the real scene/sequel segmenter's tool-schema call, with one
    bounded retry on a specific, real failure mode.

    If the first attempt fails with error_type="no_tool_call" (Ollama's
    tool_choice silently ignored - see WI-LLM-0051), and
    retry_with_reminder is True (the default), retries exactly once with
    an explicit reminder appended to the system prompt. WI-LLM-0051
    tested this live: 0/5 baseline attempts succeeded, 2/5 succeeded with
    the reminder - a real, substantial improvement, not a guaranteed fix,
    so callers should still expect and handle failure even with the
    retry. Any other failure mode (a genuine api_error, a schema/
    validation error, an empty segment list) is NOT retried - a reminder
    about calling the tool has no plausible mechanism to fix those.
    """
    story_name, story_text = load_sample_story(story_path)

    result = _run_segmentation_once(
        candidate=candidate,
        backend_kind=backend_kind,
        backend=backend,
        model=model,
        story_name=story_name,
        story_text=story_text,
        max_tokens=max_tokens,
        temperature=temperature,
    )

    if result.success or not retry_with_reminder or result.error_type != "no_tool_call":
        return result

    retry_result = _run_segmentation_once(
        candidate=candidate,
        backend_kind=backend_kind,
        backend=backend,
        model=model,
        story_name=story_name,
        story_text=story_text,
        max_tokens=max_tokens,
        temperature=temperature,
        system_prompt_suffix=_SEGMENTATION_RETRY_REMINDER,
    )
    retry_result.retry_attempted = True
    retry_result.retry_succeeded = retry_result.success
    return retry_result


def save_result(
    result: BenchmarkResult, candidate_dir: pathlib.Path, filename: str = "results.json"
) -> pathlib.Path:
    """Write result.to_dict() to <candidate_dir>/<filename>, return the path.

    `filename` defaults to "results.json" (run_entity_extraction()'s
    existing convention). Candidates covering more than one stage pass a
    distinct filename per stage (e.g. "results_genre.json",
    "results_segmentation.json") so results from different stages don't
    overwrite each other in the same directory.
    """
    out_path = candidate_dir / filename
    out_path.write_text(json.dumps(result.to_dict(), indent=2) + "\n", encoding="utf-8")
    return out_path
