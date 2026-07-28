"""Stratified cross-segment relation density pilot (WI-EVENT-0030).

See README.md in this directory for full usage instructions. Quick start
(from the repo root, conda environment active, API key configured):

    python experiments/03_cross_segment_relation_pilot/run_pilot.py \
        --sample-size 5 --output experiments/03_cross_segment_relation_pilot/results

Optional flags:

    --data-dir DIR          Corpus directory to sample from (default: lcats/data)
    --sample-size N         Target stories per genre (default: 5)
    --max-candidates N      Cap on how many candidate files to genre-scan before
                            giving up on filling every stratum (default: 200)
    --seed N                Shuffle seed for candidate order (default: 42)
    --backend NAME          "anthropic" (default) or "openai"
    --model NAME            Model string (default: claude-opus-4-8 / gpt-4o)
    --nlp-backend NAME      "spacy", "stanza", or "fake", for stage-2 surface
                            features. Defaults to "spacy" for a real run, or
                            "fake" (nlp_backend.FakeNLPBackend - zero
                            dependencies, no spacy/stanza import at all) for
                            --dry-run. Pass --nlp-backend spacy/stanza
                            explicitly alongside --dry-run to smoke-test a
                            real NLP toolkit install with zero API cost.
    --output DIR            Results directory (default: ./results next to this script)
    --dry-run               Skip real genre detection and use a FakeBackend for the
                            whole pipeline (including a stubbed single-segment
                            stage-1 segmentation, so stages 2-7 of the
                            Event-Role-World pipeline run for real). Does NOT
                            exercise the story-level cross-segment relation
                            pass - that needs events in >= 2 distinct
                            segments, which a single stubbed segment with an
                            empty fake LLM response can never produce.
                            Exercises the script's control flow and output
                            files with zero API cost. Produces meaningless
                            (empty) extraction results - never use its output
                            as a real finding. Defaults --nlp-backend to
                            "fake" (see above) unless overridden.

Genre strata are fixed to the four genres lcats assess --genre actually
classifies (science fiction, horror, western, romance - see
lcats.analysis.corpus.assess.VALID_GENRES). Genre is detected per-candidate
story via assess_story() in detect mode (an LLM call), not read from any
pre-existing label, since the corpus carries no genre metadata today.

Requires:
    - lcats installed (run scripts/develop if not)
    - ANTHROPIC_API_KEY or OPENAI_API_KEY set in environment, or present in
      .secrets/anthropic_api_keys.env / .secrets/openai_api_keys.env
      (see docs/secrets-setup.md) - not required for --dry-run.

Cost note: this script makes real LLM API calls for genre detection (one
call per candidate story scanned), scene/sequel segmentation (one call per
sampled story), and the full Event-Role-World pipeline (4 calls per
segment - entities, events, relations, discourse; the optional stage-8
hypothesis pass is disabled since this pilot doesn't use hypothesis data -
plus one story-level cross-segment-relation call per story). Across 4
genres x 5-10 stories each, this is a real cost and latency expenditure -
see the Risk Notes in WI-EVENT-0030 and the README in this directory
before running against the full target sample size. --model and the
--backend-specific default are propagated to every call, including the
ERW pipeline's own extractors (see _build_erw_extractors/_run_erw_pipeline
below) - processor.process_segments() itself hardcodes gpt-4o for these
regardless of backend, which would send an invalid model ID to a
non-OpenAI backend.

Exit codes:
    0   pilot completed (individual story exclusions are noted, not fatal)
    1   prerequisite check failed (missing install, missing key)
    2   could not fill every genre stratum before exhausting --max-candidates
    3   aborted early on a fatal API error (bad credentials or exhausted
        account balance/quota) - see FatalPilotError below. Any story
        results gathered before the abort are still written out.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import random
import sys
import time

from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Path bootstrap - allow running as `python experiments/.../run_pilot.py` from
# the repo root without requiring a prior `pip install -e .`.
# ---------------------------------------------------------------------------
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lcats" / "src"))

from lcats.analysis import scene_analysis
from lcats.analysis import story_analysis
from lcats.analysis.corpus import assess as corpus_assess
from lcats.analysis.event_role_world import discourse_extractor as erw_discourse
from lcats.analysis.event_role_world import entity_extractor as erw_entity
from lcats.analysis.event_role_world import event_extractor as erw_event
from lcats.analysis.event_role_world import nlp_backend as erw_nlp_backend
from lcats.analysis.event_role_world import processor as erw_processor
from lcats.analysis.event_role_world import relation_extractor as erw_relation
from lcats.analysis.event_role_world import schema as erw_schema
from lcats.analysis.event_role_world import (
    story_relation_extractor as erw_story_relation,
)
from lcats.analysis.event_role_world import surface_feature_extractor as erw_surface
from lcats.utils.secrets import load_secrets

GENRES = (
    corpus_assess.VALID_GENRES
)  # ("science fiction", "horror", "western", "romance")

# JSONPromptExtractor's own default (4096) is far below what a content-dense
# segment can need for entity/event/relation extraction, and silently
# truncating mid-tool-call now raises TruncatedResponseError (see
# lcats.llm.backend) instead of returning malformed JSON - so a request that
# used to fail data-integrity checks downstream now fails loudly and
# immediately unless given real headroom. 16384 is well under
# claude-opus-4-8's 128k output ceiling and costs nothing extra for calls
# that finish early (Anthropic bills actual output tokens generated, not
# this ceiling).
_ERW_MAX_TOKENS = 16384

# Substrings of an API error message that mean "stop the whole run", not
# "skip this one story": bad/expired credentials or an exhausted account
# balance/quota. Every remaining candidate would fail identically, so
# continuing just burns time (and, with real credentials, still-billable
# request attempts) for no new information. Deliberately as broad as
# lcats.analysis.llm_extractor.JSONPromptExtractor._classify_api_error's own
# quota/auth checks (not narrower) - a fatal-error detector that's too
# narrow silently degrades back into per-story exclusions, which is exactly
# the failure mode this exists to prevent. Covers both providers' actual
# wording: Anthropic's "Your credit balance is too low..." (a 400
# invalid_request_error, not the OpenAI-shaped insufficient_quota/402 the
# classifier was originally written for) and common auth-failure phrasing
# ("authentication failed", "Incorrect API key provided").
_FATAL_ERROR_SUBSTRINGS = (
    "credit balance",
    "insufficient_quota",
    "quota",
    "api key",
    "authentication",
)


class FatalPilotError(RuntimeError):
    """Raised to abort the whole run on a non-retryable, account-level API
    error, mirroring the should_abort_batch convention already used by
    lcats.analysis.corpus.processing.process_corpus_directory (see
    api_error.get("should_abort_batch") there) - this pilot script predates
    that convention and previously had no equivalent, so a single exhausted
    API key/balance silently produced a full sample of "excluded" stories
    with no top-level indication of why.

    Carries `usage_rows`: PassUsage records (in the same tagged shape as
    pilot_usage.jsonl rows) already accumulated for the current story before
    the abort. A quota/auth failure can happen partway through a
    multi-segment story after several earlier passes already succeeded and
    spent real tokens - raising bare would silently drop that cost/latency
    data. Defaults to empty; callers with nothing accumulated yet (genre
    detection, segmentation) leave it unset.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.usage_rows: List[Dict[str, Any]] = []


def _check_fatal(
    message: str,
    context: str,
    usage_rows: Optional[List[Dict[str, Any]]] = None,
) -> None:
    """Raise FatalPilotError if `message` names a fatal, account-level
    failure rather than a per-story problem."""
    lowered = message.lower()
    if any(s in lowered for s in _FATAL_ERROR_SUBSTRINGS):
        exc = FatalPilotError(f"{context}: {message}")
        exc.usage_rows = list(usage_rows or [])
        raise exc


def _build_backend(backend_name: str, model: Optional[str]):
    if backend_name == "anthropic":
        from lcats.llm import anthropic_backend

        return anthropic_backend.AnthropicBackend(), model or "claude-opus-4-8"
    if backend_name == "openai":
        from lcats.llm import openai_backend

        return openai_backend.OpenAIBackend(), model or "gpt-4o"
    raise ValueError(f"Unknown backend: {backend_name!r}")


def _build_fake_backend():
    from lcats.llm import fake_backend

    return fake_backend.FakeBackend(tool_result={}), "fake-1.0"


def _iter_candidate_files(data_dir: pathlib.Path, seed: int) -> List[pathlib.Path]:
    files = sorted(data_dir.rglob("*.json"))
    rng = random.Random(seed)
    rng.shuffle(files)
    return files


def build_stratified_sample(
    data_dir: pathlib.Path,
    backend: Any,
    model: str,
    sample_size: int,
    max_candidates: int,
    seed: int,
    dry_run: bool,
) -> Tuple[Dict[str, List[pathlib.Path]], int]:
    """Select up to `sample_size` stories per genre in GENRES.

    Returns (genre -> list of file paths, candidates_scanned). Scans
    candidates in shuffled order, classifying each with a real detect-mode
    assess_story() call (skipped in --dry-run, where the first
    len(GENRES) * sample_size candidates are round-robin assigned instead,
    with zero API calls), stopping once every genre has sample_size stories
    or max_candidates is exhausted.
    """
    sample: Dict[str, List[pathlib.Path]] = {g: [] for g in GENRES}
    candidates = _iter_candidate_files(data_dir, seed)

    if dry_run:
        needed = sample_size * len(GENRES)
        for i, path in enumerate(candidates[:needed]):
            sample[GENRES[i % len(GENRES)]].append(path)
        return sample, min(needed, len(candidates))

    scanned = 0
    for path in candidates:
        if scanned >= max_candidates:
            break
        if all(len(sample[g]) >= sample_size for g in GENRES):
            break
        scanned += 1
        try:
            result = corpus_assess.assess_story(path, backend=backend, model=model)
        except Exception as exc:  # noqa: BLE001 - skip this candidate on failure
            print(f"  [genre-detect] {path}: failed ({exc}), skipping", file=sys.stderr)
            continue
        if result.error:
            # assess_story() catches API exceptions internally and reports
            # them via AssessmentResult.error rather than raising, so a
            # fatal error here would otherwise never reach the except above
            # - it would just silently fail to classify every remaining
            # candidate (detected_genre defaults to "other", which isn't in
            # GENRES, so nothing prints and nothing is added to any bucket).
            _check_fatal(result.error, context=f"genre-detect {path.name}")
            print(
                f"  [genre-detect] {path.name}: failed ({result.error}), skipping",
                file=sys.stderr,
            )
            continue
        genre = result.detected_genre
        if genre in sample and len(sample[genre]) < sample_size:
            sample[genre].append(path)
            print(
                f"  [genre-detect] {path.name} -> {genre} ({len(sample[genre])}/{sample_size})"
            )

    return sample, scanned


def _segment_story(
    body: str, backend: Any, model: str
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Run scene/sequel segmentation; return (segments, error_or_None)."""
    seg_extractor = scene_analysis.make_segment_extractor(backend)
    seg_result = seg_extractor.extract(body, model_name=model)
    error = seg_result.get("api_error") or seg_result.get("extraction_error")
    segments = seg_result.get("extracted_output") or []
    if not segments:
        return [], error or "segmentation produced no segments"
    return segments, error


def _has_extraction_errors(pipeline_result: Dict[str, Any]) -> List[str]:
    """Collect every segment- and story-level extraction_errors entry."""
    errors: List[str] = []
    for seg in pipeline_result["segments"]:
        errors.extend(seg.get("extraction_errors") or [])
    errors.extend(pipeline_result["story"].get("extraction_errors") or [])
    return errors


def _compute_story_metrics(
    pipeline_result: Dict[str, Any], word_count: int
) -> Dict[str, Any]:
    """Compute cross-segment-only density directly from the story-level
    cross_segment_relations/weakly_inferred_cross_segment_relations fields,
    kept separate from the folded per-segment-plus-cross-segment total
    reported alongside for context. Mirrors baseline.summarize_annotations'
    certainty split without needing the SegmentWorldAnnotation/
    StoryWorldAnnotation dataclasses themselves - process_segments already
    returns plain dicts (via .to_dict()), and reconstructing dataclasses
    from them would be pure overhead for this read-only aggregation.
    """
    story = pipeline_result["story"]
    segments = pipeline_result["segments"]

    cross_segment_count = len(story.get("cross_segment_relations") or [])
    weakly_inferred_cross_segment_count = len(
        story.get("weakly_inferred_cross_segment_relations") or []
    )

    folded_relations_count = cross_segment_count + sum(
        len(seg.get("relations") or []) for seg in segments
    )
    folded_weakly_inferred_count = weakly_inferred_cross_segment_count + sum(
        len(seg.get("weakly_inferred_relations") or []) for seg in segments
    )

    def per_1000(n: int) -> float:
        return (n / word_count * 1000) if word_count else 0.0

    return {
        "word_count": word_count,
        "cross_segment_relation_count": cross_segment_count,
        "weakly_inferred_cross_segment_relation_count": weakly_inferred_cross_segment_count,
        "cross_segment_density_per_1000_words": per_1000(cross_segment_count),
        "weakly_inferred_cross_segment_density_per_1000_words": per_1000(
            weakly_inferred_cross_segment_count
        ),
        "folded_relations_per_1000_words": per_1000(folded_relations_count),
        "folded_weakly_inferred_relations_per_1000_words": per_1000(
            folded_weakly_inferred_count
        ),
    }


def _close_schema_objects(node: Any) -> Any:
    """Recursively return a deep copy of a JSON Schema fragment with
    additionalProperties: false set on every object (top-level and
    nested) - required by Anthropic's strict tool use before strict: true
    takes effect. See _strict_tool_schema()'s docstring for why this is
    needed.

    Sets additionalProperties unconditionally (not via setdefault) so an
    existing, looser value (e.g. additionalProperties: true, or a schema
    rather than a bare bool) can't silently defeat the requirement this
    exists to enforce. Also matches "object" inside a union `type` list
    (e.g. `type: ["object", "null"]`), not just a bare `type: "object"`
    string, since JSON Schema permits either form.
    """
    if isinstance(node, dict):
        closed = {key: _close_schema_objects(value) for key, value in node.items()}
        node_type = closed.get("type")
        is_object = node_type == "object" or (
            isinstance(node_type, list) and "object" in node_type
        )
        if is_object:
            closed["additionalProperties"] = False
        return closed
    if isinstance(node, list):
        return [_close_schema_objects(item) for item in node]
    return node


def _strict_tool_schema(tool_schema: Dict[str, Any]) -> Dict[str, Any]:
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
    (Anthropic docs, JSON Schema limitations) - none of the ERW tool
    schemas set this today, so _close_schema_objects() adds it here rather
    than editing each schema's module (forbidden by this work item; see
    _build_erw_extractors()'s docstring for the same constraint applied to
    default_model).
    """
    schema = _close_schema_objects(tool_schema)
    schema["strict"] = True
    return schema


def _build_erw_extractors(
    backend: Any, model: str, backend_name: str
) -> Dict[str, Any]:
    """Build the Event-Role-World extractors, with `model` overriding each
    factory's own hardcoded default_model (e.g. "gpt-4o"), max_tokens raised
    to _ERW_MAX_TOKENS (each factory's own default of 4096 is too low for
    content-dense segments and risks TruncatedResponseError - see
    lcats.llm.backend), and, for --backend anthropic only, each extractor's
    tool_schema upgraded to strict: true (see _strict_tool_schema()).

    processor.process_segments() has no model parameter - it builds these
    same extractors internally with each factory's hardcoded default,
    which sends an invalid model ID whenever the caller's backend/model
    choice differs (e.g. --backend anthropic with the default gpt-4o
    baked into every ERW extractor). Building them here instead, then
    driving processor.process_segment() (singular - it accepts pre-built
    extractor instances) per segment ourselves, fixes this without
    touching processor.py or any event_role_world module (forbidden by
    this work item).

    The strict-schema override is gated to backend_name == "anthropic"
    because it is not a no-op for OpenAI: AnthropicBackend.complete()
    forwards the whole tool dict verbatim, so an added top-level `strict`
    key is inert there unless read, but OpenAIBackend.complete() forwards
    `tool["input_schema"]` directly as its function `parameters` - the
    `additionalProperties: false` this same override adds to input_schema
    would reach OpenAI's schema too and could change its behavior in ways
    this fix was never intended to touch or test.
    """
    entity = erw_entity.make_entity_extractor(backend)
    event = erw_event.make_event_extractor(backend)
    relation = erw_relation.make_relation_extractor(backend)
    discourse = erw_discourse.make_discourse_extractor(backend)
    story_relation = erw_story_relation.make_story_relation_extractor(backend)
    for extractor in (entity, event, relation, discourse, story_relation):
        extractor.default_model = model
        extractor.max_tokens = _ERW_MAX_TOKENS
        if backend_name == "anthropic" and extractor.tool_schema is not None:
            extractor.tool_schema = _strict_tool_schema(extractor.tool_schema)
    return {
        "entity": entity,
        "event": event,
        "relation": relation,
        "discourse": discourse,
        "story_relation": story_relation,
    }


def _make_nlp_backend(nlp_backend_name: str) -> Any:
    """Construct the stage-2 NLP backend, including the "fake" pseudo-name.

    "fake" (nlp_backend.FakeNLPBackend, zero dependencies - no spacy/stanza
    import at all) is this script's own addition on top of
    erw_surface.make_nlp_backend()'s "spacy"/"stanza" - main() defaults
    --nlp-backend to "fake" under --dry-run so the zero-cost smoke test
    also needs zero extra dependencies installed, but an explicit
    --nlp-backend spacy/stanza (even combined with --dry-run) still
    selects the real backend, so a real NLP-toolkit install can be
    smoke-tested with zero API cost. See running_the_pilot.md.
    """
    if nlp_backend_name == "fake":
        return erw_nlp_backend.FakeNLPBackend()
    return erw_surface.make_nlp_backend(nlp_backend_name)


def _run_erw_pipeline(
    body: str,
    segments: List[Dict[str, Any]],
    extractors: Dict[str, Any],
    nlp_backend: Any,
    nlp_backend_name: str,
    story_id: str,
) -> Dict[str, Any]:
    """Run stages 2-9 (+ the cross-segment pass) for one story.

    `extractors` (built by _build_erw_extractors(), with `model` already
    overriding each extractor's own hardcoded default) and `nlp_backend`
    are passed in already-built rather than constructed here - this
    function itself takes no `model` parameter.

    Mirrors processor.process_segments()'s own orchestration (per-segment
    process_segment() calls, schema.reconcile_story_annotations(), then the
    story-level cross-segment relation pass gated on events existing in at
    least 2 distinct segments) but built from extractors this script
    constructs itself, so their default_model can be overridden - see
    _build_erw_extractors(). `extractors` and `nlp_backend` are built ONCE
    by the caller (main()) and reused across every story in the sample -
    constructing a fresh nlp_backend per story here previously reloaded
    Stanza's full neural pipeline (tokenize/mwt/pos/lemma/depparse, ~15-30s)
    on every single story, since StanzaBackend.__init__ builds a real
    stanza.Pipeline; spaCy's per-story reload was smaller (~1-5s) but the
    same waste. Returns
    {"segments": [...], "usage": [...], "story": {...},
    "processed_segment_count": int} - the last key is the number of
    segments actually processed (process_segments() silently skips any
    segment missing start_char/end_char, so `len(segments)` alone can
    overstate how many were really run and disagree with relation
    counts/densities computed from them).
    """

    annotations: List[erw_schema.SegmentWorldAnnotation] = []
    all_usage: List[erw_processor.PassUsage] = []
    processed_segment_count = 0

    for segment in segments:
        start_char = segment.get("start_char")
        end_char = segment.get("end_char")
        if start_char is None or end_char is None:
            continue
        processed_segment_count += 1
        segment_text = body[start_char:end_char]
        annotation, usage_records = erw_processor.process_segment(
            segment.get("segment_id"),
            segment_text,
            nlp_backend=nlp_backend,
            nlp_backend_name=nlp_backend_name,
            entity_llm_extractor=extractors["entity"],
            event_llm_extractor=extractors["event"],
            relation_llm_extractor=extractors["relation"],
            discourse_llm_extractor=extractors["discourse"],
            hypothesis_llm_extractor=None,
            include_hypotheses=False,  # this pilot does not use hypothesis data
        )
        annotations.append(annotation)
        all_usage.extend(usage_records)

        # Check after every segment, not after the whole story: entity/
        # event/relation/discourse extraction all run unconditionally per
        # segment (process_segment has no early-exit of its own), so a
        # multi-segment story would otherwise issue several more doomed
        # requests per remaining segment before this function ever returns.
        for err in annotation.extraction_errors:
            _check_fatal(
                str(err),
                context=f"pipeline {story_id} segment {segment.get('segment_id')}",
                usage_rows=[u.to_dict() for u in all_usage],
            )

    story = erw_schema.reconcile_story_annotations(story_id, annotations)

    segment_ids_with_events = {
        segment.segment_id for segment in annotations if segment.events
    }
    if len(segment_ids_with_events) >= 2:
        t0 = time.monotonic()
        event_index_text = erw_story_relation.build_event_index(story)
        story_relation_result = extractors["story_relation"].extract(event_index_text)
        all_usage.append(
            erw_processor._pass_usage_from_extraction(  # noqa: SLF001 - reuse pipeline's own usage-record logic
                "story", "story_relation", story_relation_result, t0
            )
        )
        story_relation_error = story_relation_result.get(
            "api_error"
        ) or story_relation_result.get("extraction_error")
        if story_relation_error:
            story.extraction_errors.append(
                f"story relation extraction failed: {story_relation_error}"
            )
            _check_fatal(
                str(story_relation_error),
                context=f"pipeline {story_id} story-relation",
                usage_rows=[u.to_dict() for u in all_usage],
            )
        cross_segment_relations, weakly_inferred_cross_segment_relations = (
            erw_story_relation.build_story_relations(
                story_relation_result.get("extracted_output") or {}, story
            )
        )
        story.cross_segment_relations = cross_segment_relations
        story.weakly_inferred_cross_segment_relations = (
            weakly_inferred_cross_segment_relations
        )
        story.validation_errors = erw_schema.validate_story_annotation(story)

    return {
        "segments": [a.to_dict() for a in annotations],
        "usage": [u.to_dict() for u in all_usage],
        "story": story.to_dict(),
        "processed_segment_count": processed_segment_count,
    }


def run_story(
    path: pathlib.Path,
    genre: str,
    backend: Any,
    model: str,
    extractors: Dict[str, Any],
    nlp_backend: Any,
    nlp_backend_name: str,
    dry_run: bool = False,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Run the full pipeline for one story.

    Returns (row, usage_rows) - row is the per-story result dict for
    pilot_stories.jsonl; usage_rows is one dict per PassUsage record (tagged
    with story_id/genre) for pilot_usage.jsonl, preserved even for excluded
    stories so cost/latency on a failed paid run is not lost.

    In --dry-run mode, real stage-1 segmentation is skipped (a FakeBackend
    cannot produce one - its single fixed response can't satisfy the
    segmentation extractor's JSON-text parsing) and a single dummy segment
    spanning the whole body is used instead, so _run_erw_pipeline()'s
    stages 2-7 run for real in the zero-cost smoke test, rather than every
    dry-run story returning early at segmentation. This does NOT reach the
    story-level cross-segment relation pass: that pass only fires when
    events exist in >= 2 distinct segments, and a single stubbed segment
    with an empty fake LLM response never produces any events at all - see
    running_the_pilot.md's Step 2a for the same caveat.
    """
    row: Dict[str, Any] = {
        "path": str(path),
        "story_id": path.stem,
        "genre": genre,
        "excluded": False,
        "exclude_reason": "",
    }

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        row["excluded"] = True
        row["exclude_reason"] = f"could not read/parse story JSON: {exc}"
        return row, []

    body = story_analysis.coerce_text(data.get("body", ""))
    word_count = story_analysis.word_count(body)
    row["word_count"] = word_count

    if not body.strip():
        row["excluded"] = True
        row["exclude_reason"] = "empty story body"
        return row, []

    if dry_run:
        segments: List[Dict[str, Any]] = [
            {"segment_id": 1, "start_char": 0, "end_char": len(body)}
        ]
    else:
        segments, seg_error = _segment_story(body, backend, model)
        if seg_error or not segments:
            # seg_error may be the classified api_error dict (see
            # LLMExtractor._classify_api_error) or a plain string, depending
            # on where in extract() the failure occurred.
            seg_error_dict = seg_error if isinstance(seg_error, dict) else None
            seg_error_text = (
                seg_error_dict.get("message", str(seg_error))
                if seg_error_dict is not None
                else str(seg_error)
            )
            if seg_error_dict is not None and seg_error_dict.get("should_abort_batch"):
                # Trust the classifier's own normalized flag directly when
                # it's available, rather than re-deriving fatality from
                # message text (which can miss wordings the classifier
                # already recognizes - see _FATAL_ERROR_SUBSTRINGS).
                raise FatalPilotError(f"segmentation {path.name}: {seg_error_text}")
            _check_fatal(seg_error_text, context=f"segmentation {path.name}")
            row["excluded"] = True
            row["exclude_reason"] = f"segmentation failed: {seg_error_text}"
            return row, []

    try:
        pipeline_result = _run_erw_pipeline(
            body, segments, extractors, nlp_backend, nlp_backend_name, path.stem
        )
    except FatalPilotError as exc:
        exc.usage_rows = [
            {"story_id": path.stem, "genre": genre, **usage} for usage in exc.usage_rows
        ]
        raise
    usage_rows = [
        {"story_id": path.stem, "genre": genre, **usage}
        for usage in pipeline_result["usage"]
    ]

    extraction_errors = _has_extraction_errors(pipeline_result)
    if extraction_errors:
        for err in extraction_errors:
            _check_fatal(err, context=f"pipeline {path.name}", usage_rows=usage_rows)
        row["excluded"] = True
        row["exclude_reason"] = "; ".join(extraction_errors)
        return row, usage_rows

    row.update(_compute_story_metrics(pipeline_result, word_count))
    row["segment_count"] = pipeline_result["processed_segment_count"]
    return row, usage_rows


def summarize_by_genre(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate mean cross-segment-only and folded densities per genre,
    over included (non-excluded) rows only."""
    summary: Dict[str, Any] = {}
    for genre in GENRES:
        included = [r for r in rows if r["genre"] == genre and not r["excluded"]]
        excluded = [r for r in rows if r["genre"] == genre and r["excluded"]]
        if included:
            mean_cross = sum(
                r["cross_segment_density_per_1000_words"] for r in included
            ) / len(included)
            mean_weak_cross = sum(
                r["weakly_inferred_cross_segment_density_per_1000_words"]
                for r in included
            ) / len(included)
            mean_folded = sum(
                r["folded_relations_per_1000_words"] for r in included
            ) / len(included)
            mean_folded_weak = sum(
                r["folded_weakly_inferred_relations_per_1000_words"] for r in included
            ) / len(included)
        else:
            mean_cross = mean_weak_cross = mean_folded = mean_folded_weak = 0.0
        summary[genre] = {
            "included_count": len(included),
            "excluded_count": len(excluded),
            "mean_cross_segment_density_per_1000_words": mean_cross,
            "mean_weakly_inferred_cross_segment_density_per_1000_words": mean_weak_cross,
            "mean_folded_relations_per_1000_words": mean_folded,
            "mean_folded_weakly_inferred_relations_per_1000_words": mean_folded_weak,
        }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--data-dir", default="lcats/data")
    parser.add_argument("--sample-size", type=int, default=5)
    parser.add_argument("--max-candidates", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--backend", choices=["anthropic", "openai"], default="anthropic"
    )
    parser.add_argument("--model", default=None)
    parser.add_argument(
        "--nlp-backend",
        choices=["spacy", "stanza", "fake"],
        default=None,
        help=(
            "Stage-2 surface-feature NLP backend. Defaults to 'spacy' for a "
            "real run, or 'fake' (zero-dependency, no spacy/stanza import at "
            "all) for --dry-run. Pass --nlp-backend spacy/stanza explicitly "
            "with --dry-run to test a real NLP backend install with zero "
            "API cost (LLM calls still use a FakeBackend)."
        ),
    )
    parser.add_argument(
        "--output",
        default=str(pathlib.Path(__file__).resolve().parent / "results"),
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.nlp_backend is None:
        args.nlp_backend = "fake" if args.dry_run else "spacy"

    load_secrets()

    data_dir = pathlib.Path(args.data_dir)
    if not data_dir.exists():
        print(f"error: data dir not found: {data_dir}", file=sys.stderr)
        return 1

    output_dir = pathlib.Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        backend, model = _build_fake_backend()
    else:
        try:
            backend, model = _build_backend(args.backend, args.model)
        except Exception as exc:  # noqa: BLE001
            print(
                f"error: could not construct {args.backend} backend: {exc}",
                file=sys.stderr,
            )
            print(
                "Set ANTHROPIC_API_KEY/OPENAI_API_KEY or populate .secrets/ (see docs/secrets-setup.md).",
                file=sys.stderr,
            )
            return 1

    print(f"Building stratified sample (target {args.sample_size} per genre)...")
    try:
        sample, scanned = build_stratified_sample(
            data_dir,
            backend,
            model,
            args.sample_size,
            args.max_candidates,
            args.seed,
            args.dry_run,
        )
    except FatalPilotError as exc:
        print(f"\nfatal: {exc}", file=sys.stderr)
        print(
            "Aborting - this looks like a bad/expired API key or an "
            "exhausted account balance/quota, not a per-story problem. "
            "Every remaining candidate would fail identically.",
            file=sys.stderr,
        )
        return 3
    print(f"Scanned {scanned} candidates.")

    incomplete_genres = [g for g in GENRES if len(sample[g]) < args.sample_size]
    if incomplete_genres and not args.dry_run:
        print(
            f"warning: could not fill every stratum before exhausting "
            f"--max-candidates ({args.max_candidates}): "
            + ", ".join(
                f"{g}={len(sample[g])}/{args.sample_size}" for g in incomplete_genres
            ),
            file=sys.stderr,
        )

    # Built ONCE and reused across every story - constructing these per
    # story previously reloaded Stanza's full neural pipeline (~15-30s) or
    # spaCy's model (~1-5s) on every single story. See _run_erw_pipeline's
    # docstring. Model/pipeline loading now happens here, before the
    # per-story timer starts below, so per-story elapsed_seconds no longer
    # includes it - print an explicit confirmation instead, since spaCy
    # (unlike Stanza) prints no loading banner of its own.
    extractors = _build_erw_extractors(backend, model, args.backend)
    print(f"Loading NLP backend: {args.nlp_backend}...")
    nlp_backend = _make_nlp_backend(args.nlp_backend)
    print(f"NLP backend ready: {args.nlp_backend}")

    rows: List[Dict[str, Any]] = []
    usage_rows: List[Dict[str, Any]] = []
    aborted = False
    for genre in GENRES:
        if aborted:
            break
        for path in sample[genre]:
            print(f"Running pipeline: [{genre}] {path.name}")
            t0 = time.monotonic()
            try:
                row, story_usage_rows = run_story(
                    path,
                    genre,
                    backend,
                    model,
                    extractors,
                    nlp_backend,
                    args.nlp_backend,
                    dry_run=args.dry_run,
                )
            except FatalPilotError as exc:
                # Preserve cost/latency for any passes that succeeded on
                # this story before the fatal failure - see
                # FatalPilotError's docstring.
                usage_rows.extend(exc.usage_rows)
                print(f"\nfatal: {exc}", file=sys.stderr)
                print(
                    "Aborting - this looks like a bad/expired API key or an "
                    "exhausted account balance/quota, not a per-story "
                    "problem. Every remaining story would fail identically. "
                    "Results gathered so far are still written out below.",
                    file=sys.stderr,
                )
                aborted = True
                break
            row["elapsed_seconds"] = time.monotonic() - t0
            rows.append(row)
            usage_rows.extend(story_usage_rows)
            if row["excluded"]:
                print(f"  excluded: {row['exclude_reason']}")

    stories_path = output_dir / "pilot_stories.jsonl"
    with stories_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")

    usage_path = output_dir / "pilot_usage.jsonl"
    with usage_path.open("w", encoding="utf-8") as f:
        for usage_row in usage_rows:
            f.write(json.dumps(usage_row, sort_keys=True) + "\n")

    summary = summarize_by_genre(rows)
    summary_path = output_dir / "pilot_summary.json"
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "sample_size_target": args.sample_size,
                "candidates_scanned": scanned,
                "backend": args.backend,
                "model": model,
                "dry_run": args.dry_run,
                "by_genre": summary,
            },
            f,
            indent=2,
            sort_keys=True,
        )

    print("\nPer-genre summary (cross-segment-only density, per 1000 words):")
    for genre, stats in summary.items():
        print(
            f"  {genre:16s} included={stats['included_count']} "
            f"excluded={stats['excluded_count']} "
            f"cross_segment={stats['mean_cross_segment_density_per_1000_words']:.3f} "
            f"weakly_inferred_cross_segment={stats['mean_weakly_inferred_cross_segment_density_per_1000_words']:.3f} "
            f"folded_total={stats['mean_folded_relations_per_1000_words']:.3f} "
            f"folded_weakly_inferred={stats['mean_folded_weakly_inferred_relations_per_1000_words']:.3f}"
        )
    print(f"\nWrote {stories_path}")
    print(f"Wrote {usage_path}")
    print(f"Wrote {summary_path}")

    if aborted:
        return 3
    if incomplete_genres and not args.dry_run:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
