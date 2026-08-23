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
    --model-genre-detect NAME
                            Override --model for genre detection only.
    --model-segment NAME    Override --model for segmentation only.
    --model-entity NAME     Override --model for the ERW entity extractor only.
    --model-event NAME      Override --model for the ERW event extractor only.
    --model-relation NAME   Override --model for the ERW relation extractor only.
    --model-discourse NAME  Override --model for the ERW discourse extractor only.
    --model-cross-segment NAME
                            Override --model for the story-level cross-segment
                            relation pass only.
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
    --story COLLECTION/NAME Target one real story directly, bypassing the
                            stratified genre-detect scan entirely (a cheap,
                            reproducible way to validate a change against a
                            specific real story). Requires --genre - no
                            implicit genre-detect call is made. Mutually
                            exclusive with --story-list.
    --story-list [FILE]     Target several stories from a manifest file (one
                            "<collection>/<name>:<genre>" entry per line),
                            bypassing the stratified genre-detect scan
                            entirely. Given with no FILE, defaults to this
                            script's own committed fixture set
                            (fixtures/manifest.txt - see fixtures/README.md)
                            - the zero-config default within targeted mode
                            only; this script's own no-argument invocation
                            is unchanged. Mutually exclusive with --story.
    --genre NAME            Genre label for --story (one of GENRES below).
                            Not used with --story-list, whose manifest
                            carries genre per entry.

Genre strata are pinned to the original four genres this pilot (WI-EVENT-0030)
was scoped against (science fiction, horror, western, romance) via the
module-level GENRES constant below, deliberately independent of
lcats.analysis.corpus.assess.VALID_GENRES, which has since grown to 8 genres
(WI-ASSESS-0031). Re-scoping this pilot to the full genre set is its own
separate follow-up (Gap 3 in
project/design/event-role-world-genre-target-reconciliation.md), not
something a VALID_GENRES change should do implicitly. Genre is detected
per-candidate story via assess_story() in detect mode (an LLM call), not
read from any pre-existing label, since the corpus carries no genre metadata
today.

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

Checkpointing (WI-PIPELINE-0041): every story's genre-detection,
segmentation, ERW-extraction, and cross-segment-relation stages are now
checkpointed independently via lcats.utils.checkpoint - a crash or Ctrl-C
preserves every already-completed stage's output, and a resumed run
(same --output, same --data-dir) skips already-checkpointed,
successfully-completed stages instead of re-issuing their LLM calls.
Checkpoints are written under --output (this script's own results
directory, never data/ or corpora/ directly - see checkpoint.resolve_roots's
write-guard); --data-dir is read-only input.

Exit codes:
    0   pilot completed (individual story exclusions are noted, not fatal)
    1   prerequisite check failed (missing install, missing key, or an
        --output pointed at the protected data/corpora roots)
    2   could not fill every genre stratum before exhausting --max-candidates
    3   aborted early on a fatal API error (bad credentials or exhausted
        account balance/quota) - see FatalPilotError below. Any story
        results gathered before the abort are still written out.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import random
import sys
import time

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Path bootstrap - allow running as `python experiments/.../run_pilot.py` from
# the repo root without requiring a prior `pip install -e .`.
# ---------------------------------------------------------------------------
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lcats" / "src"))

from lcats.analysis import scene_analysis
from lcats.analysis import story_analysis
from lcats.analysis.corpus import assess as corpus_assess
from lcats.analysis.corpus import discovery
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
from lcats.utils import checkpoint
from lcats.utils import run_log
from lcats.utils.secrets import load_secrets

GENRES = ("science fiction", "horror", "western", "romance")
# Deliberately NOT corpus_assess.VALID_GENRES (now 8 genres as of
# WI-ASSESS-0031) - this pilot is still scoped to WI-EVENT-0030's original
# four strata; see the module docstring above.

# argparse.const for --story-list given with no FILE argument - distinct
# from `None` (flag not given at all), which argparse can't distinguish
# from "given with no value" without nargs="?"/const (WI-PILOT-0051). A
# real, non-string object (not a string like "__FIXTURES_DEFAULT__") so
# it can never collide with an actual filename a user passes as the FILE
# argument - argparse always stores a given value as a str, so `is`
# identity against this object is unambiguous (review finding, PR #244).
_STORY_LIST_DEFAULT_SENTINEL = object()

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
    data. Defaults to empty; genre-detection failures (in
    build_stratified_sample, before any per-story usage exists yet) leave
    it unset - segmentation and ERW-extraction failures pass their own
    already-accumulated usage_rows explicitly (WI-PILOT-0051).
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.usage_rows: List[Dict[str, Any]] = []


@dataclass(frozen=True)
class StageModels:
    """Resolved model choice for each LLM-backed pilot stage.

    Every field defaults to the global --model value unless an explicit
    per-stage override is supplied. Keeping this as one value avoids
    accidentally default-enabling model tiering while still making tiered
    experiment runs checkpoint-safe and auditable.
    """

    genre_detect: str
    segment: str
    entity: str
    event: str
    relation: str
    discourse: str
    cross_segment_relation: str

    @classmethod
    def from_global(
        cls,
        model: str,
        *,
        genre_detect: Optional[str] = None,
        segment: Optional[str] = None,
        entity: Optional[str] = None,
        event: Optional[str] = None,
        relation: Optional[str] = None,
        discourse: Optional[str] = None,
        cross_segment_relation: Optional[str] = None,
    ) -> "StageModels":
        return cls(
            genre_detect=genre_detect or model,
            segment=segment or model,
            entity=entity or model,
            event=event or model,
            relation=relation or model,
            discourse=discourse or model,
            cross_segment_relation=cross_segment_relation or model,
        )

    def to_dict(self) -> Dict[str, str]:
        return {
            "genre_detect": self.genre_detect,
            "segment": self.segment,
            "entity": self.entity,
            "event": self.event,
            "relation": self.relation,
            "discourse": self.discourse,
            "cross_segment_relation": self.cross_segment_relation,
        }

    def erw_extract_models(self) -> Dict[str, str]:
        return {
            "entity": self.entity,
            "event": self.event,
            "relation": self.relation,
            "discourse": self.discourse,
        }


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


# Bumped whenever a prompt/schema/extractor-version change should
# invalidate every existing checkpoint for this pilot, even under an
# unchanged model - there is no existing per-module version tracking
# elsewhere in lcats to reuse, so this is a script-local proxy.
#
# Feeds into _base_fingerprint(), which every stage's _stage_fingerprint()
# call uses - bumping this invalidates genre_detect, segment, erw_extract,
# AND cross_segment_relation checkpoints together. Use _CLASSIFIER_VERSION
# below instead for a change scoped to assess.py's classifier alone, so a
# resumed run doesn't re-pay for expensive segmentation/ERW/relation calls
# whose own upstream inputs never changed (review finding, PR #224).
_PIPELINE_VERSION = "v1"

# Bumped whenever assess.py's classifier (prompts, schema, VALID_GENRES)
# changes in a way that should invalidate only genre_detect checkpoints -
# folded into that stage's own fingerprint below, not _base_fingerprint(),
# so segment/erw_extract/cross_segment_relation checkpoints stay valid
# across a classifier-only change.
#
# v2: WI-ASSESS-0031 changed assess.py's classifier (VALID_GENRES 4->8,
# new secondary_genre field, updated prompts) - a genre_detect checkpoint
# from v1 reflects the old 4-genre classification and must not be reused.
#
# v3: WI-LLM-0058 added secondary_genre sanitization to assess_story() (a
# corrupted value is now stripped to "" and flagged, not left as-is) - a
# genre_detect checkpoint from v2 may have cached a pre-fix, unsanitized
# (corrupted) secondary_genre value; bumping forces a resumed run to
# re-classify rather than silently serving a stale corrupted value
# forever (this same gap was independently found and fixed in
# run_census.py's _CLASSIFIER_VERSION and annotate.py's
# _GENRE_POSTPROCESS_VERSION - review finding, PR #267).
_CLASSIFIER_VERSION = "v3"


def _story_identity(path: pathlib.Path) -> str:
    """Return a stable, flattened, checkpoint-safe identity for a canonical
    bucket story file (<collection>/<story>/story.json).

    Post PROP-LCATS-STORY-BUCKET-LAYOUT, every canonical story file's own
    leaf filename is literally "story.json" for every story - path.stem
    alone collapses to "story" regardless of which story it is (the exact
    identity-collapse problem PROP-LCATS-STORY-BUCKET-LAYOUT's Decision 2
    already fixed in the core package's own discovery/identity logic, but
    this script builds its own row["story_id"]/checkpoint item_id
    independently of that, so the collapse recurs here unless fixed).
    Combines the collection name (path.parent.parent.name) with the
    story's own bucket directory name (path.parent.name), joined with
    "__" since checkpoint item_ids must be a single path segment (see
    checkpoint._validate_path_component) and a bare "/" join would not be
    a valid item_id.
    """
    return f"{path.parent.parent.name}__{path.parent.name}"


def _is_valid_cache_payload(data: Any, required_keys: Tuple[str, ...]) -> bool:
    """Return True if data is a dict containing every key in required_keys.

    checkpoint.read_checkpoint() reports outcome="success" for any
    well-formed JSON record with a recognized outcome/fingerprint - it has
    no way to know THIS script's own expected data shape. A checkpoint
    file could still be malformed relative to that shape (hand-edited, or
    written by a different version of this script) while passing every
    check checkpoint.py itself performs. Treating that as an unusable
    cache miss - never a KeyError/TypeError crash - keeps this migration's
    integration consistent with checkpoint.py's own "never raise on an
    incomplete/unexpected checkpoint" contract (review finding, PR #217).
    """
    return isinstance(data, dict) and all(key in data for key in required_keys)


def _hash_json(obj: Any) -> str:
    """Deterministic hash of a JSON-serializable value, for checkpoint
    fingerprints that must invalidate when an upstream pipeline stage's
    own output changes (Decision 2) - not a security hash, just change
    detection."""
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def _base_fingerprint(model: Any, backend_name: str) -> Dict[str, Any]:
    """Configuration-identity fingerprint shared by every stage: model,
    backend, and this script's own pipeline version (see
    _PIPELINE_VERSION). A stage whose only upstream is raw, unchanging
    corpus content (genre-detection, segmentation) uses this alone; a
    stage whose upstream is an earlier pipeline stage's own output
    (ERW-extraction, cross-segment-relation) extends it via
    _stage_fingerprint's upstream parameter, per Decision 2."""
    return {
        "model": model,
        "backend": backend_name,
        "pipeline_version": _PIPELINE_VERSION,
    }


def _stage_fingerprint(
    model: Any, backend_name: str, upstream: Optional[Any] = None
) -> Dict[str, Any]:
    """_base_fingerprint, extended with a hash of `upstream` (an earlier
    pipeline stage's own output) when given - so correcting an earlier
    stage's output under an unchanged model configuration still
    invalidates this stage's checkpoint, per Decision 2."""
    fingerprint = _base_fingerprint(model, backend_name)
    if upstream is not None:
        fingerprint["upstream_hash"] = _hash_json(upstream)
    return fingerprint


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


def _resolve_stage_models(model: str, args: argparse.Namespace) -> StageModels:
    return StageModels.from_global(
        model,
        genre_detect=args.model_genre_detect,
        segment=args.model_segment,
        entity=args.model_entity,
        event=args.model_event,
        relation=args.model_relation,
        discourse=args.model_discourse,
        cross_segment_relation=args.model_cross_segment,
    )


def _iter_candidate_files(data_dir: pathlib.Path, seed: int) -> List[pathlib.Path]:
    """List and shuffle every canonical story file under data_dir.

    Uses discovery.find_json_files (bucket-aware, per Decision 3/4 of
    PROP-LCATS-STORY-BUCKET-LAYOUT) rather than a bare recursive
    ``rglob("*.json")`` - the latter would pick up sidecar files
    (audit.json, scenes.json, etc.) alongside a story's own story.json as
    if they were separate stories once data_dir is populated by the
    bucket-writing DataGatherer (review finding, PR #210).
    """
    files = list(discovery.find_json_files([data_dir]))
    files.sort()
    rng = random.Random(seed)
    rng.shuffle(files)
    return files


def build_stratified_sample(
    data_dir: pathlib.Path,
    backend: Any,
    model: str,
    backend_name: str,
    roots: checkpoint.CheckpointRoots,
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

    Each real classification is checkpointed under roots.working_root
    (stage "genre_detect", item_id per _story_identity), so a resumed run
    with the same --seed scans candidates in the same deterministic order
    and serves already-classified candidates from their checkpoint instead
    of re-issuing the LLM call.
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
        item_id = _story_identity(path)
        # Hash the raw file text (not just model/backend/version) so a
        # story corrected in place - re-edited JSON, fixed body text -
        # invalidates its genre_detect cache instead of silently serving a
        # classification computed against stale content (review finding,
        # PR #217). Also folds in _CLASSIFIER_VERSION so an assess.py
        # classifier change invalidates genre_detect specifically, without
        # touching _PIPELINE_VERSION and therefore without invalidating
        # every other stage's checkpoints too (review finding, PR #224).
        try:
            raw_text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            raw_text = ""
        fingerprint = _stage_fingerprint(
            model,
            backend_name,
            upstream={"raw_text": raw_text, "classifier_version": _CLASSIFIER_VERSION},
        )
        cached = checkpoint.read_checkpoint(
            roots.working_root, item_id, "genre_detect", fingerprint
        )
        if cached.done and _is_valid_cache_payload(cached.data, ("genre",)):
            genre = cached.data["genre"]
        else:
            try:
                result = corpus_assess.assess_story(path, backend=backend, model=model)
            except Exception as exc:  # noqa: BLE001 - skip this candidate on failure
                print(
                    f"  [genre-detect] {path}: failed ({exc}), skipping",
                    file=sys.stderr,
                )
                checkpoint.write_checkpoint(
                    roots.working_root,
                    item_id,
                    "genre_detect",
                    outcome="failure",
                    fingerprint=fingerprint,
                    data={"error": str(exc)},
                )
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
                checkpoint.write_checkpoint(
                    roots.working_root,
                    item_id,
                    "genre_detect",
                    outcome="failure",
                    fingerprint=fingerprint,
                    data={"error": result.error},
                )
                continue
            genre = result.detected_genre
            checkpoint.write_checkpoint(
                roots.working_root,
                item_id,
                "genre_detect",
                outcome="success",
                fingerprint=fingerprint,
                data={"genre": genre},
            )
        if genre in sample and len(sample[genre]) < sample_size:
            sample[genre].append(path)
            print(
                f"  [genre-detect] {path.name} -> {genre} ({len(sample[genre])}/{sample_size})"
            )

    return sample, scanned


def _segment_story(
    body: str, backend: Any, model: str
) -> Tuple[List[Dict[str, Any]], Optional[str], Optional[Dict[str, Any]]]:
    """Run scene/sequel segmentation; return (segments, error_or_None, usage_or_None).

    usage is the extractor's raw {"input_tokens", "output_tokens"} dict
    (None if the backend call itself never returned one, e.g. a fake
    backend), for the caller to fold into a PassUsage-style record -
    closes the pilot_usage.jsonl gap for this stage (backlog P2,
    WI-PILOT-0051).

    Not checkpointed itself - see _segment_story_cached, which wraps this
    with the "segment" stage's checkpoint read/write. Kept as a separate,
    un-wrapped function so existing direct tests of the raw extraction
    behavior (see run_pilot_test.py) are unaffected by the checkpointing
    migration.
    """
    seg_extractor = scene_analysis.make_segment_extractor(backend)
    seg_result = seg_extractor.extract(body, model_name=model)
    # alignment_error must be checked here too, not just api_error/
    # extraction_error: this function's own "error" return contract
    # requires the real cause to be reported explicitly rather than the
    # generic "segmentation produced no segments" fallback that would
    # otherwise fire silently (extracted_output is already cleared to
    # None on an alignment failure by JSONPromptExtractor.extract()
    # itself, WI-SEGMENT-0059).
    error = (
        seg_result.get("api_error")
        or seg_result.get("extraction_error")
        or seg_result.get("alignment_error")
    )
    segments = seg_result.get("extracted_output") or []
    usage = seg_result.get("usage")
    if error or not segments:
        return [], error or "segmentation produced no segments", usage
    return segments, error, usage


def _segment_story_cached(
    path: pathlib.Path,
    body: str,
    backend: Any,
    model: str,
    backend_name: str,
    roots: checkpoint.CheckpointRoots,
) -> Tuple[List[Dict[str, Any]], Optional[Any], Optional[Dict[str, Any]]]:
    """_segment_story, checkpointed under stage "segment" (item_id per
    _story_identity(path)) - a resumed run with an unchanged model
    configuration skips this story's segmentation LLM call entirely.

    The third return value is a PassUsage-shaped dict (segment_id="story",
    pass_name="segment") for a fresh (non-cached) call, or None on a
    cache hit - a cache hit makes no new LLM call, so there is no new
    cost to report, and re-reporting the original call's cost on every
    replay would double-count it in pilot_usage.jsonl (see WI-PILOT-0051's
    Risk Notes).
    """
    item_id = _story_identity(path)
    # Hash the segmentation input text itself, not just model/backend/
    # version - otherwise correcting a story's body without changing the
    # model configuration would still serve stale segments (review
    # finding, PR #217).
    fingerprint = _stage_fingerprint(model, backend_name, upstream=body)
    cached = checkpoint.read_checkpoint(
        roots.working_root, item_id, "segment", fingerprint
    )
    if cached.done and _is_valid_cache_payload(cached.data, ("segments",)):
        return cached.data["segments"], None, None

    t0 = time.monotonic()
    segments, error, usage = _segment_story(body, backend, model)
    elapsed = time.monotonic() - t0
    pass_usage = {
        "segment_id": "story",
        "pass_name": "segment",
        "is_llm_backed": True,
        "model": model,
        "input_tokens": (usage or {}).get("input_tokens", 0) or 0,
        "output_tokens": (usage or {}).get("output_tokens", 0) or 0,
        "elapsed_seconds": elapsed,
    }
    if not segments:
        checkpoint.write_checkpoint(
            roots.working_root,
            item_id,
            "segment",
            outcome="failure",
            fingerprint=fingerprint,
            data={"error": error},
        )
        return segments, error, pass_usage
    checkpoint.write_checkpoint(
        roots.working_root,
        item_id,
        "segment",
        outcome="success",
        fingerprint=fingerprint,
        data={"segments": segments},
    )
    return segments, error, pass_usage


def _has_extraction_errors(pipeline_result: Dict[str, Any]) -> List[str]:
    """Collect every segment- and story-level extraction_errors entry."""
    errors: List[str] = []
    for seg in pipeline_result["segments"]:
        errors.extend(seg.get("extraction_errors") or [])
    errors.extend(pipeline_result["story"].get("extraction_errors") or [])
    return errors


_EXCLUDE_REASON_PRINT_MAX_CHARS = 500
_EXCLUDE_REASON_SEPARATOR = "; "


def _capped_exclude_reason(reason: str) -> str:
    """Cap a printed exclude_reason so one malformed story can't flood the
    console (WI-EVENT-0061): `extraction_errors` joins every item- and
    container-level error collected across a story's extraction passes
    (see schema.describe_malformed_item()/coerce_list_field()) into one
    "; "-separated string, which can still be numerous for a large story.
    Only this console echo is capped -- the row's own uncapped
    exclude_reason is unaffected, since it is persisted to
    pilot_stories.jsonl for later analysis.
    """
    if len(reason) <= _EXCLUDE_REASON_PRINT_MAX_CHARS:
        return reason
    truncated = reason[:_EXCLUDE_REASON_PRINT_MAX_CHARS]
    total_segments = reason.count(_EXCLUDE_REASON_SEPARATOR) + 1
    shown_segments = truncated.count(_EXCLUDE_REASON_SEPARATOR) + 1
    # If the cutoff fell inside the last already-counted segment rather
    # than before a "; " boundary, no additional segment was actually
    # omitted -- only text within one segment was cut. Report a plain
    # truncation, not a fabricated "...0 more errors" (or, with a naive
    # floor, a fabricated "...1 more error") (review finding, PR #274).
    more_count = total_segments - shown_segments
    if more_count <= 0:
        return f"{truncated}...(truncated)"
    suffix = "s" if more_count != 1 else ""
    return f"{truncated}...{more_count} more error{suffix}"


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


def _build_erw_extractors(
    backend: Any, model: str, stage_models: Optional[StageModels] = None
) -> Dict[str, Any]:
    """Build the Event-Role-World extractors, with model overrides replacing each
    factory's own hardcoded default_model (e.g. "gpt-4o") and max_tokens
    raised to _ERW_MAX_TOKENS (each factory's own default of 4096 is too
    low for content-dense segments and risks TruncatedResponseError - see
    lcats.llm.backend). Each extractor's tool_schema is already strict at
    the source (WI-EVENT-0032) - this function used to additionally apply
    a runtime strict-schema override for --backend anthropic only, now
    removed as redundant.

    processor.process_segments() now accepts a model= override too
    (WI-EVENT-0032), but not a per-extractor max_tokens override, which
    this pilot also needs (see the comment above _ERW_MAX_TOKENS).
    Building the extractors here and driving processor.process_segment()
    (singular - it accepts pre-built extractor instances) per segment
    ourselves keeps both overrides available, without waiting on
    process_segments() to grow a max_tokens parameter of its own.
    """
    models = stage_models or StageModels.from_global(model)
    entity = erw_entity.make_entity_extractor(backend)
    event = erw_event.make_event_extractor(backend)
    relation = erw_relation.make_relation_extractor(backend)
    discourse = erw_discourse.make_discourse_extractor(backend)
    story_relation = erw_story_relation.make_story_relation_extractor(backend)
    for extractor, extractor_model in (
        (entity, models.entity),
        (event, models.event),
        (relation, models.relation),
        (discourse, models.discourse),
        (story_relation, models.cross_segment_relation),
    ):
        extractor.default_model = extractor_model
        extractor.max_tokens = _ERW_MAX_TOKENS
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


def _run_erw_extraction(
    body: str,
    segments: List[Dict[str, Any]],
    extractors: Dict[str, Any],
    nlp_backend: Any,
    nlp_backend_name: str,
    story_id: str,
) -> Dict[str, Any]:
    """Run stages 2-9 (per-segment entity/event/relation/discourse
    extraction + story-level reconciliation) for one story - the
    "ERW-extraction" checkpoint stage. Does NOT include the story-level
    cross-segment-relation pass; see _apply_cross_segment_relations for
    that, checkpointed as its own separate stage (WI-PIPELINE-0041,
    Decision 3 - a resumed run must not collapse the whole per-story
    pipeline into one checkpointed unit).

    `extractors` (built by _build_erw_extractors(), with `model` already
    overriding each extractor's own hardcoded default) and `nlp_backend`
    are passed in already-built rather than constructed here - this
    function itself takes no `model` parameter. `extractors` and
    `nlp_backend` are built ONCE by the caller (main()) and reused across
    every story in the sample - constructing a fresh nlp_backend per story
    here previously reloaded Stanza's full neural pipeline
    (tokenize/mwt/pos/lemma/depparse, ~15-30s) on every single story, since
    StanzaBackend.__init__ builds a real stanza.Pipeline; spaCy's per-story
    reload was smaller (~1-5s) but the same waste.

    Returns {"segments": [...], "usage": [...], "story": {...} (no
    cross_segment_relations/weakly_inferred_cross_segment_relations yet),
    "processed_segment_count": int, "segment_ids_with_events": [...],
    "_story_obj": <the real StoryWorldAnnotation, not JSON-serializable -
    see that key's own comment on the return statement>} -
    processed_segment_count is the number of segments actually processed
    (process_segment() silently skips any segment missing
    start_char/end_char, so len(segments) alone can overstate how many
    were really run); segment_ids_with_events lets
    _apply_cross_segment_relations decide, without recomputing, whether
    the >= 2-segments-with-events gate for the cross-segment pass is met.
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
    segment_ids_with_events = sorted(
        {segment.segment_id for segment in annotations if segment.events}
    )

    return {
        "segments": [a.to_dict() for a in annotations],
        "usage": [u.to_dict() for u in all_usage],
        "story": story.to_dict(),
        "processed_segment_count": processed_segment_count,
        "segment_ids_with_events": segment_ids_with_events,
        # Not JSON-serializable - the real object, for _apply_cross_segment_
        # relations's full-validation path when computed fresh in this same
        # run. Callers MUST pop this before passing the rest to
        # checkpoint.write_checkpoint (see run_story), or json.dump raises.
        "_story_obj": story,
    }


class _MiniEvent:
    """Just enough of Event's shape for build_event_index/build_story_relations."""

    def __init__(self, data: Dict[str, Any]) -> None:
        self.event_id = data["event_id"]
        self.predicate = data["predicate"]
        self.event_type = data["event_type"]
        evidence = data["evidence"]
        self.evidence = erw_schema.EvidenceSpan(
            start_char=evidence["start_char"],
            end_char=evidence["end_char"],
            quote=evidence["quote"],
            source=evidence.get("source", "segment"),
            paragraph_ids=evidence.get("paragraph_ids"),
        )


class _MiniSegment:
    """Just enough of SegmentWorldAnnotation's shape for the same two functions."""

    def __init__(self, data: Dict[str, Any]) -> None:
        self.segment_id = data["segment_id"]
        self.events = [_MiniEvent(e) for e in data.get("events", [])]


class _MiniStory:
    """Just enough of StoryWorldAnnotation's shape for the same two functions."""

    def __init__(self, segment_annotations: List[_MiniSegment]) -> None:
        self.segment_annotations = segment_annotations


def _story_for_cross_segment_pass(story_dict: Dict[str, Any]) -> _MiniStory:
    """Build the minimal object shape
    erw_story_relation.build_event_index/build_story_relations actually
    dereference (story.segment_annotations[].segment_id/.events[]
    .event_id/.predicate/.event_type/.evidence), from a checkpoint-
    persisted plain dict (schema.StoryWorldAnnotation.to_dict()'s own
    output shape).

    Not a general StoryWorldAnnotation deserializer - schema.py has no
    from_dict for its dataclass hierarchy, and building one for all 14
    dataclasses would be substantially more than this stage's own resume
    path needs. Scoped exactly to what these two story_relation_extractor
    functions read, confirmed directly against their source. Reusing this
    on a fresh, same-process story (not read from a checkpoint) would also
    work, but callers should prefer the real
    schema.reconcile_story_annotations() output when it's already in
    memory - this exists specifically for the disk-only resume case.
    """
    return _MiniStory(
        [_MiniSegment(s) for s in story_dict.get("segment_annotations", [])]
    )


def _apply_cross_segment_relations(
    extraction_result: Dict[str, Any],
    extractors: Dict[str, Any],
    story_id: str,
    story_obj: Optional[erw_schema.StoryWorldAnnotation] = None,
    upstream_usage: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Run the story-level cross-segment-relation pass - the
    "cross_segment_relation" checkpoint stage, separate from
    _run_erw_extraction (WI-PIPELINE-0041, Decision 3).

    Takes `extraction_result` (the dict _run_erw_extraction returns, or an
    equivalent dict read back from that stage's own checkpoint) and
    returns {"story": {...} (updated with cross_segment_relations/
    weakly_inferred_cross_segment_relations/extraction_errors, and
    validation_errors when story_obj is given - see below), "usage": [...]}.
    Gated on segment_ids_with_events (from extraction_result) containing
    at least 2 distinct segments; below that, returns the story unchanged
    and empty usage - a no-op, not an error, matching the prior combined
    function's own behavior.

    `story_obj`: the real, in-memory schema.StoryWorldAnnotation this
    story_id's _run_erw_extraction call just produced, when available
    (i.e. this stage's checkpoint is being computed fresh in the same
    run as erw_extract, not resumed from a prior process's checkpoint).
    When given, this function updates it in place and runs the FULL
    validate_story_annotation check, exactly matching this pipeline's
    pre-checkpointing behavior. When not given (a resumed run whose
    erw_extract checkpoint was already done in an earlier process, so
    only its plain-dict form exists on disk), falls back to
    _story_for_cross_segment_pass's minimal reconstruction - sufficient
    for build_event_index/build_story_relations (confirmed against their
    source: they only ever touch segment_id/events[].event_id/.predicate/
    .event_type/.evidence), but NOT for validate_story_annotation, which
    needs entities/relations context this minimal path doesn't
    reconstruct. In that disk-only-resume case, story-level validation is
    deliberately skipped rather than run against an incomplete stand-in
    that could report misleading errors - validation_errors is left as
    whatever _run_erw_extraction already set (empty, since that stage
    never populates it). This is a narrow, honestly-scoped gap: it only
    applies to a process restart landing in the specific window between
    this story's erw_extract checkpoint being written and its own
    cross_segment_relation checkpoint being written - not a lost
    validation, just a deferred one that would resurface if this
    resumed-then-cached story were later re-validated some other way.

    `upstream_usage`: erw_extract's own already-accumulated usage rows
    (plain dicts, e.g. extraction_result["usage"]), folded into the usage
    reported to _check_fatal if the story-relation call itself hits a
    fatal (account-level) error - otherwise that already-paid-for cost
    data would be silently dropped from the abort's usage_rows (review
    finding, PR #217).
    """
    story_dict = dict(extraction_result["story"])
    all_usage: List[erw_processor.PassUsage] = []

    if len(extraction_result.get("segment_ids_with_events") or []) < 2:
        return {"story": story_dict, "usage": []}

    story: Any = (
        story_obj
        if story_obj is not None
        else _story_for_cross_segment_pass(story_dict)
    )
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

    extraction_errors = list(story_dict.get("extraction_errors") or [])
    if story_relation_error:
        extraction_errors.append(
            f"story relation extraction failed: {story_relation_error}"
        )
        _check_fatal(
            str(story_relation_error),
            context=f"pipeline {story_id} story-relation",
            usage_rows=(upstream_usage or []) + [u.to_dict() for u in all_usage],
        )

    (
        cross_segment_relations,
        weakly_inferred_cross_segment_relations,
        story_relation_item_errors,
    ) = erw_story_relation.build_story_relations(
        story_relation_result.get("extracted_output") or {}, story
    )
    extraction_errors.extend(story_relation_item_errors)

    story_dict["cross_segment_relations"] = [
        r.to_dict() for r in cross_segment_relations
    ]
    story_dict["weakly_inferred_cross_segment_relations"] = [
        r.to_dict() for r in weakly_inferred_cross_segment_relations
    ]
    story_dict["extraction_errors"] = extraction_errors

    if story_obj is not None:
        story_obj.cross_segment_relations = cross_segment_relations
        story_obj.weakly_inferred_cross_segment_relations = (
            weakly_inferred_cross_segment_relations
        )
        story_obj.extraction_errors = extraction_errors
        story_obj.validation_errors = erw_schema.validate_story_annotation(story_obj)
        story_dict["validation_errors"] = story_obj.validation_errors

    return {"story": story_dict, "usage": [u.to_dict() for u in all_usage]}


def _run_erw_pipeline(
    body: str,
    segments: List[Dict[str, Any]],
    extractors: Dict[str, Any],
    nlp_backend: Any,
    nlp_backend_name: str,
    story_id: str,
) -> Dict[str, Any]:
    """Backward-compatible combined entry point: run stages 2-9 plus the
    story-level cross-segment pass for one story in a single call,
    composing _run_erw_extraction and _apply_cross_segment_relations (with
    the real, freshly-computed StoryWorldAnnotation, so full validation
    runs exactly as it did before the WI-PIPELINE-0041 checkpointing
    split). Kept for the existing direct regression test of this combined
    behavior (run_pilot_test.py's TestRunErwPipelineStoryRelationCallSite);
    run_story() itself calls the two stages separately, checkpointed
    independently - see WI-PIPELINE-0041.

    Returns the same combined shape this function had before the split:
    {"segments": [...], "usage": [...] (both stages' usage combined),
    "story": {...}, "processed_segment_count": int}.
    """
    extraction_result = _run_erw_extraction(
        body, segments, extractors, nlp_backend, nlp_backend_name, story_id
    )
    story_obj = extraction_result.pop("_story_obj")
    cross_segment_result = _apply_cross_segment_relations(
        extraction_result,
        extractors,
        story_id,
        story_obj=story_obj,
        upstream_usage=extraction_result["usage"],
    )
    return {
        "segments": extraction_result["segments"],
        "usage": extraction_result["usage"] + cross_segment_result["usage"],
        "story": cross_segment_result["story"],
        "processed_segment_count": extraction_result["processed_segment_count"],
    }


def run_story(
    path: pathlib.Path,
    genre: str,
    backend: Any,
    model: str,
    backend_name: str,
    roots: checkpoint.CheckpointRoots,
    extractors: Dict[str, Any],
    nlp_backend: Any,
    nlp_backend_name: str,
    stage_models: Optional[StageModels] = None,
    dry_run: bool = False,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Run the full pipeline for one story.

    Returns (row, usage_rows) - row is the per-story result dict for
    pilot_stories.jsonl; usage_rows is one dict per PassUsage record (tagged
    with story_id/genre) for pilot_usage.jsonl, preserved even for excluded
    stories so cost/latency on a failed paid run is not lost.

    Each of this story's four stages (segmentation, ERW-extraction, and
    cross-segment-relation - genre-detection is checkpointed separately in
    build_stratified_sample, before this function is ever called for this
    story) is checkpointed independently under roots.working_root, per
    WI-PIPELINE-0041/Decision 3: a crash or Ctrl-C preserves every
    already-completed stage's output, and a resumed run with an unchanged
    model configuration skips re-issuing an already-checkpointed stage's
    LLM call.

    In --dry-run mode, real stage-1 segmentation is skipped (a FakeBackend
    cannot produce one - its single fixed response can't satisfy the
    segmentation extractor's JSON-text parsing) and a single dummy segment
    spanning the whole body is used instead, so stages 2-7 still run for
    real (against the FakeBackend) in the zero-cost smoke test, rather
    than every dry-run story returning early at segmentation - these later
    stages are still checkpointed the same as a real run. This does NOT
    reach the story-level cross-segment relation pass: that pass only
    fires when events exist in >= 2 distinct segments, and a single
    stubbed segment with an empty fake LLM response never produces any
    events at all - see running_the_pilot.md's Step 2a for the same
    caveat.
    """
    models = stage_models or StageModels.from_global(model)
    item_id = _story_identity(path)
    row: Dict[str, Any] = {
        "path": str(path),
        "story_id": item_id,
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

    seg_stage_usage: List[Dict[str, Any]] = []
    if dry_run:
        segments: List[Dict[str, Any]] = [
            {"segment_id": 1, "start_char": 0, "end_char": len(body)}
        ]
    else:
        segments, seg_error, seg_pass_usage = _segment_story_cached(
            path, body, backend, models.segment, backend_name, roots
        )
        if seg_pass_usage is not None:
            seg_stage_usage.append(
                {"story_id": item_id, "genre": genre, **seg_pass_usage}
            )
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
                exc = FatalPilotError(f"segmentation {path.name}: {seg_error_text}")
                exc.usage_rows = seg_stage_usage
                raise exc
            _check_fatal(
                seg_error_text,
                context=f"segmentation {path.name}",
                usage_rows=seg_stage_usage,
            )
            row["excluded"] = True
            row["exclude_reason"] = f"segmentation failed: {seg_error_text}"
            # Preserve this stage's cost/latency for the excluded row -
            # matches run_story()'s own docstring guarantee that usage_rows
            # is "preserved even for excluded stories."
            return row, seg_stage_usage

    _erw_keys = (
        "segments",
        "usage",
        "story",
        "processed_segment_count",
        "segment_ids_with_events",
    )
    _cross_keys = ("story", "usage")

    try:
        # nlp_backend_name is folded in explicitly (not just via
        # `segments`) since the NLP surface-feature backend choice affects
        # process_segment()'s output even when segmentation itself is
        # unchanged (review finding, PR #217).
        erw_fingerprint = _stage_fingerprint(
            models.erw_extract_models(),
            backend_name,
            upstream={"segments": segments, "nlp_backend": nlp_backend_name},
        )
        cached_erw = checkpoint.read_checkpoint(
            roots.working_root, item_id, "erw_extract", erw_fingerprint
        )
        if cached_erw.done and _is_valid_cache_payload(cached_erw.data, _erw_keys):
            extraction_result = cached_erw.data
            story_obj: Optional[erw_schema.StoryWorldAnnotation] = None
        else:
            extraction_result = _run_erw_extraction(
                body, segments, extractors, nlp_backend, nlp_backend_name, item_id
            )
            story_obj = extraction_result.pop("_story_obj")
            # A transient extraction error should be retried on the next
            # run, not served forever from a "successful" checkpoint - see
            # _has_extraction_errors (review finding, PR #217).
            erw_outcome = (
                "failure" if _has_extraction_errors(extraction_result) else "success"
            )
            checkpoint.write_checkpoint(
                roots.working_root,
                item_id,
                "erw_extract",
                outcome=erw_outcome,
                fingerprint=erw_fingerprint,
                data=extraction_result,
            )

        cross_fingerprint = _stage_fingerprint(
            models.cross_segment_relation,
            backend_name,
            upstream=extraction_result["story"],
        )
        cached_cross = checkpoint.read_checkpoint(
            roots.working_root, item_id, "cross_segment_relation", cross_fingerprint
        )
        if cached_cross.done and _is_valid_cache_payload(
            cached_cross.data, _cross_keys
        ):
            cross_segment_result = cached_cross.data
        else:
            cross_segment_result = _apply_cross_segment_relations(
                extraction_result,
                extractors,
                item_id,
                story_obj=story_obj,
                upstream_usage=extraction_result["usage"],
            )
            cross_outcome = (
                "failure"
                if cross_segment_result["story"].get("extraction_errors")
                else "success"
            )
            checkpoint.write_checkpoint(
                roots.working_root,
                item_id,
                "cross_segment_relation",
                outcome=cross_outcome,
                fingerprint=cross_fingerprint,
                data=cross_segment_result,
            )
    except FatalPilotError as exc:
        exc.usage_rows = seg_stage_usage + [
            {"story_id": item_id, "genre": genre, **usage} for usage in exc.usage_rows
        ]
        raise
    except Exception as exc:
        # An unexpected (non-FatalPilotError) exception here - e.g. while
        # processing ERW stages or writing a checkpoint - must not
        # silently drop the segmentation cost already paid for and
        # recorded in seg_stage_usage. _run_stories's generic per-story
        # exception handler reads this attribute back out (review
        # finding, PR #244) - it is not part of FatalPilotError's own
        # contract, so it is set generically here rather than requiring
        # every caller to know about a special exception subclass.
        exc.usage_rows = seg_stage_usage  # type: ignore[attr-defined]
        raise

    pipeline_result = {
        "segments": extraction_result["segments"],
        "usage": extraction_result["usage"] + cross_segment_result["usage"],
        "story": cross_segment_result["story"],
        "processed_segment_count": extraction_result["processed_segment_count"],
    }
    usage_rows = seg_stage_usage + [
        {"story_id": item_id, "genre": genre, **usage}
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


def _run_stories(
    story_genre_pairs: List[Tuple[str, pathlib.Path]],
    backend: Any,
    model: str,
    backend_name: str,
    roots: checkpoint.CheckpointRoots,
    extractors: Dict[str, Any],
    nlp_backend: Any,
    nlp_backend_name: str,
    stage_models: Optional[StageModels],
    dry_run: bool,
    log: run_log.RunLog,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], bool]:
    """Run run_story() over every (genre, path) pair in order, handling
    FatalPilotError (abort, preserving already-accumulated usage) and any
    other per-story exception (record a minimal excluded row, continue) -
    shared by both the full stratified-sample path and the targeted
    --story/--story-list path (WI-PILOT-0051), so this error-handling
    logic exists in exactly one place.

    Also appends one event per story to ``log`` (a
    ``lcats.utils.run_log.RunLog``, per-run-scoped by the caller) - a
    human-readable, append-and-flush record of what happened and when,
    distinct from the per-item checkpoints run_story() itself writes:
    checkpoints answer "is this item done and resume-safe?", this log
    answers "what happened, in order, including why the run stopped?"
    ``run_start``/``run_end`` are the caller's responsibility (via
    ``log``'s own context-manager lifecycle), not this function's - see
    ``main()``.

    Returns (rows, usage_rows, aborted).
    """
    rows: List[Dict[str, Any]] = []
    usage_rows: List[Dict[str, Any]] = []
    aborted = False
    for genre, path in story_genre_pairs:
        if aborted:
            break
        print(f"Running pipeline: [{genre}] {path.name}")
        t0 = time.monotonic()
        try:
            row, story_usage_rows = run_story(
                path,
                genre,
                backend,
                model,
                backend_name,
                roots,
                extractors,
                nlp_backend,
                nlp_backend_name,
                stage_models=stage_models,
                dry_run=dry_run,
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
            log.event(
                "run_aborted_fatal",
                story_id=_story_identity(path),
                genre=genre,
                error=str(exc),
            )
            aborted = True
            break
        except Exception as exc:  # noqa: BLE001 - see docstring below
            # Any exception other than FatalPilotError is an
            # unexpected, per-story failure - not an account-level
            # one. Previously this propagated straight out of main(),
            # skipping the write block below entirely and discarding
            # every already-completed, already-paid-for story's
            # results, not just this one's (WI-EVENT-0032, audit's
            # Category B update finding). Record a minimal excluded
            # row (matching run_story()'s own row shape - see its
            # "could not read/parse story JSON" branch) and continue
            # to the next story instead.
            print(
                f"  error: unexpected failure on {path.name}: {exc}",
                file=sys.stderr,
            )
            # run_story() attaches usage_rows to any exception raised
            # after a real segmentation call succeeded (see its own
            # except Exception branch) - recover it here so an
            # unexpected failure mid-pipeline doesn't silently drop
            # already-paid-for segmentation cost from pilot_usage.jsonl
            # (review finding, PR #244).
            usage_rows.extend(getattr(exc, "usage_rows", None) or [])
            rows.append(
                {
                    "path": str(path),
                    "story_id": _story_identity(path),
                    "genre": genre,
                    "excluded": True,
                    "exclude_reason": f"unexpected error: {exc!r}",
                    "elapsed_seconds": time.monotonic() - t0,
                }
            )
            log.event(
                "story_unexpected_error",
                story_id=_story_identity(path),
                genre=genre,
                error=repr(exc),
            )
            continue
        row["elapsed_seconds"] = time.monotonic() - t0
        rows.append(row)
        usage_rows.extend(story_usage_rows)
        if row["excluded"]:
            print(f"  excluded: {_capped_exclude_reason(row['exclude_reason'])}")
        log.event(
            "story_completed",
            story_id=row["story_id"],
            genre=genre,
            excluded=row["excluded"],
            exclude_reason=row.get("exclude_reason"),
        )

    return rows, usage_rows, aborted


def _resolve_target_story(
    spec: str, data_dir: pathlib.Path, fixtures_dir: pathlib.Path
) -> pathlib.Path:
    """Resolve a `<collection>/<name>` targeting spec to a real story.json
    path (bucket layout: <root>/<collection>/<name>/story.json).

    A spec starting with "fixtures/" resolves against fixtures_dir (this
    script's own committed fixture set); anything else resolves against
    data_dir (the normal corpus root, same as a full-sample run reads
    from), so --story can target any real story in the corpus, not just
    the fixture set.
    """
    if spec.startswith("fixtures/"):
        rest = spec[len("fixtures/") :]
        return fixtures_dir / rest / "story.json"
    return data_dir / spec / "story.json"


def _parse_story_list(
    list_path: pathlib.Path, data_dir: pathlib.Path, fixtures_dir: pathlib.Path
) -> List[Tuple[str, pathlib.Path]]:
    """Parse a --story-list manifest file into (genre, path) pairs, in file
    order. Format: one `<collection>/<name>:<genre>` entry per line; blank
    lines and lines starting with `#` are ignored. Raises ValueError on a
    malformed line (missing `:genre`) or an unresolvable genre (not one of
    GENRES) - fail loudly rather than silently skip a bad manifest entry.
    """
    pairs: List[Tuple[str, pathlib.Path]] = []
    for lineno, raw_line in enumerate(
        list_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(
                f"{list_path}:{lineno}: malformed entry (expected "
                f"'<collection>/<name>:<genre>'): {line!r}"
            )
        spec, genre = line.rsplit(":", 1)
        spec = spec.strip()
        genre = genre.strip()
        if genre not in GENRES:
            raise ValueError(
                f"{list_path}:{lineno}: genre {genre!r} is not one of " f"{GENRES}"
            )
        pairs.append((genre, _resolve_target_story(spec, data_dir, fixtures_dir)))
    return pairs


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
        "--model-genre-detect",
        default=None,
        help="Override --model for the genre-detection stage only.",
    )
    parser.add_argument(
        "--model-segment",
        default=None,
        help="Override --model for the scene/sequel segmentation stage only.",
    )
    parser.add_argument(
        "--model-entity",
        default=None,
        help="Override --model for the ERW entity extractor only.",
    )
    parser.add_argument(
        "--model-event",
        default=None,
        help="Override --model for the ERW event extractor only.",
    )
    parser.add_argument(
        "--model-relation",
        default=None,
        help="Override --model for the ERW relation extractor only.",
    )
    parser.add_argument(
        "--model-discourse",
        default=None,
        help="Override --model for the ERW discourse extractor only.",
    )
    parser.add_argument(
        "--model-cross-segment",
        default=None,
        help="Override --model for the story-level cross-segment relation pass only.",
    )
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
    parser.add_argument(
        "--story",
        default=None,
        metavar="COLLECTION/NAME",
        help=(
            "Target one real story directly (bucket layout: "
            "<data-dir>/<collection>/<name>/story.json), bypassing the "
            "stratified genre-detect scan entirely. Requires --genre "
            "(no implicit genre-detect call is made). Mutually exclusive "
            "with --story-list."
        ),
    )
    parser.add_argument(
        "--story-list",
        nargs="?",
        const=_STORY_LIST_DEFAULT_SENTINEL,
        default=None,
        metavar="FILE",
        help=(
            "Target several stories from a manifest file (one "
            "'<collection>/<name>:<genre>' entry per line), bypassing the "
            "stratified genre-detect scan entirely. Given with no FILE, "
            "defaults to this script's own committed fixture set "
            "(fixtures/manifest.txt) - the zero-config default within "
            "targeted mode only; run_pilot.py's own no-argument invocation "
            "(neither flag given) is unchanged. Mutually exclusive with "
            "--story."
        ),
    )
    parser.add_argument(
        "--genre",
        choices=GENRES,
        default=None,
        help="Genre label for --story (ignored/rejected with --story-list, whose manifest carries genre per entry).",
    )
    args = parser.parse_args()

    if args.nlp_backend is None:
        args.nlp_backend = "fake" if args.dry_run else "spacy"

    if args.story and args.story_list is not None:
        print("error: --story and --story-list are mutually exclusive", file=sys.stderr)
        return 1
    if args.story and not args.genre:
        print(
            "error: --story requires --genre (no implicit genre-detect call is made)",
            file=sys.stderr,
        )
        return 1
    if args.story_list is not None and args.genre:
        print(
            "error: --genre is not used with --story-list (genre comes from the manifest file)",
            file=sys.stderr,
        )
        return 1

    load_secrets()

    targeted_mode = bool(args.story) or args.story_list is not None

    data_dir = pathlib.Path(args.data_dir)
    # Only the full stratified-sample path unconditionally scans data_dir -
    # a targeted run against the committed fixture set never touches it,
    # so requiring it to exist would defeat that mode's own point (a
    # cheap, self-contained, offline smoke test). A targeted spec that
    # does need data_dir (a non-"fixtures/"-prefixed --story, or a custom
    # --story-list manifest referencing real corpus stories) still fails
    # clearly below when its specific story.json can't be found.
    if not targeted_mode and not data_dir.exists():
        print(f"error: data dir not found: {data_dir}", file=sys.stderr)
        return 1

    fixtures_dir = pathlib.Path(__file__).resolve().parent / "fixtures"

    output_dir = pathlib.Path(args.output)

    # Guard BEFORE creating output_dir - checkpoint.resolve_roots() does
    # not require the path to exist (pathlib.Path.resolve() works on a
    # non-existent path), so creating the directory first would let a
    # rejected --output still mutate the protected corpus tree before the
    # guard ever fires (review finding, PR #217).
    try:
        roots = checkpoint.resolve_roots(working_root=output_dir, source_root=data_dir)
    except (checkpoint.ProtectedRootError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

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

    stage_models = _resolve_stage_models(model, args)

    incomplete_genres: List[str] = []
    if targeted_mode:
        try:
            if args.story:
                path = _resolve_target_story(args.story, data_dir, fixtures_dir)
                if not path.is_file():
                    print(f"error: story not found: {path}", file=sys.stderr)
                    return 1
                story_genre_pairs = [(args.genre, path)]
            else:
                list_path = (
                    fixtures_dir / "manifest.txt"
                    if args.story_list is _STORY_LIST_DEFAULT_SENTINEL
                    else pathlib.Path(args.story_list)
                )
                # is_file(), not exists() - a path that exists but is a
                # directory (or otherwise not a readable regular file)
                # must fail cleanly here, not crash _parse_story_list's
                # .read_text() with an unhandled OSError (review finding,
                # PR #244).
                if not list_path.is_file():
                    print(f"error: story list not found: {list_path}", file=sys.stderr)
                    return 1
                story_genre_pairs = _parse_story_list(list_path, data_dir, fixtures_dir)
                missing = [p for _, p in story_genre_pairs if not p.is_file()]
                if missing:
                    for p in missing:
                        print(f"error: story not found: {p}", file=sys.stderr)
                    return 1
        except (ValueError, OSError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        scanned = 0
        print(
            f"Targeted mode: {len(story_genre_pairs)} story/stories, no genre-detect scan."
        )
    else:
        print(f"Building stratified sample (target {args.sample_size} per genre)...")
        try:
            sample, scanned = build_stratified_sample(
                data_dir,
                backend,
                stage_models.genre_detect,
                args.backend,
                roots,
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
                    f"{g}={len(sample[g])}/{args.sample_size}"
                    for g in incomplete_genres
                ),
                file=sys.stderr,
            )
        story_genre_pairs = [
            (genre, path) for genre in GENRES for path in sample[genre]
        ]

    # Built ONCE and reused across every story - constructing these per
    # story previously reloaded Stanza's full neural pipeline (~15-30s) or
    # spaCy's model (~1-5s) on every single story. See _run_erw_pipeline's
    # docstring. Model/pipeline loading now happens here, before the
    # per-story timer starts below, so per-story elapsed_seconds no longer
    # includes it - print an explicit confirmation instead, since spaCy
    # (unlike Stanza) prints no loading banner of its own.
    extractors = _build_erw_extractors(backend, model, stage_models)
    print(f"Loading NLP backend: {args.nlp_backend}...")
    nlp_backend = _make_nlp_backend(args.nlp_backend)
    print(f"NLP backend ready: {args.nlp_backend}")
    # RunLog wraps both _run_stories() and the pilot_stories.jsonl/
    # pilot_usage.jsonl write block below in one scope: an exception
    # anywhere in either -- including during output writing, not just the
    # per-story loop -- still produces a terminal event, and run_end is
    # only ever emitted once both have actually succeeded (mirrors
    # run_prefilter.py's RunLog wrapping, review finding, PR #352 on
    # WI-RUNLOG-0079).
    with run_log.RunLog(
        roots,
        "pilot_run_log.jsonl",
        model=model,
        backend_name=args.backend,
        story_count=len(story_genre_pairs),
        dry_run=args.dry_run,
    ) as log:
        rows, usage_rows, aborted = _run_stories(
            story_genre_pairs,
            backend,
            model,
            args.backend,
            roots,
            extractors,
            nlp_backend,
            args.nlp_backend,
            stage_models,
            args.dry_run,
            log,
        )

        stories_path = output_dir / "pilot_stories.jsonl"
        with stories_path.open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, sort_keys=True) + "\n")

        usage_path = output_dir / "pilot_usage.jsonl"
        with usage_path.open("w", encoding="utf-8") as f:
            for usage_row in usage_rows:
                f.write(json.dumps(usage_row, sort_keys=True) + "\n")

        # Manually logged (not RunLog's own automatic bare run_end) so an
        # aborted run's log carries an explicit aborted=True marker as its
        # final event, instead of leaving a bare run_end that's
        # indistinguishable from a fully successful run without scanning
        # every earlier event (review finding, PR #371 - mirrors
        # run_prefilter.py's own run_end payload from WI-RUNLOG-0079).
        log.event(
            "run_end",
            aborted=aborted,
            processed_count=len(rows),
        )

    summary = summarize_by_genre(rows)
    summary_path = output_dir / "pilot_summary.json"
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "sample_size_target": args.sample_size,
                "candidates_scanned": scanned,
                "backend": args.backend,
                "model": model,
                "stage_models": stage_models.to_dict(),
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
