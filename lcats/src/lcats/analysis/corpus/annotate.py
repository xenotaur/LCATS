"""Fast-path annotation: genre + scene/sequel sidecars for story buckets.

Runs the two extractors mature enough to trust at scale -- `lcats assess`
(genre) and `scene_analysis` (scene/sequel segmentation) -- over story
buckets under a collection directory, writing `genre.json`/`scenes.json`
sidecars plus a per-bucket `README.md`, per WI-ANNOTATE-0051.

Checkpoint/output split (review-driven design decision, not incidental):
checkpoint.resolve_roots() refuses a working_root under data/ or corpora/
(data/ is a disposable cache, corpora/ is wholesale-copied by `lcats
promote` -- see checkpoint.py's own docstring), so checkpoint bookkeeping
lives in a dedicated --checkpoint-dir (default `.annotate_checkpoints/`,
never data/corpora/cache), separate from the real sidecar files this
module writes directly into each story's bucket directory under data/.
A checkpoint's own `data` field holds the actual computed sidecar
content, so re-materializing the sidecar file from an already-successful
checkpoint is always cheap and idempotent -- no re-payment for a paid
LLM call, even if a prior run was interrupted between recording the
checkpoint and writing the sidecar file itself.
"""

from __future__ import annotations

import dataclasses
import datetime
import hashlib
import json
import os
import pathlib
import tempfile
from typing import Any, Optional

from lcats.analysis import scene_analysis
from lcats.analysis.corpus import assess, discovery
from lcats.analysis.corpus import cli as corpus_cli
from lcats.analysis.corpus import genre_sidecar
from lcats.utils import checkpoint

# Explicit defaults, passed through to assess_story/make_segment_extractor
# and included in their fingerprints -- otherwise a future change to
# either function's own default would silently go unnoticed by an
# existing checkpoint (review finding, PR #241).
DEFAULT_GENRE_MAX_TOKENS = 4096
DEFAULT_SCENES_MAX_TOKENS = 16384

# Sidecar filename constants live in discovery.py, not here, so
# promote.py can reference them without importing this module's own
# extractor/LLM dependency chain (review finding, PR #248).
GENRE_SIDECAR_FILENAME = discovery.GENRE_SIDECAR_FILENAME
SCENES_SIDECAR_FILENAME = discovery.SCENES_SIDECAR_FILENAME

# Bumped whenever assess_story()'s own post-processing of the raw tool
# result changes in a way that should invalidate every cached "genre"
# checkpoint, even though _genre_fingerprint's tool_schema_hash (below)
# is unchanged - a Python-side behavior change (not a schema change) is
# otherwise invisible to that fingerprint.
#
# v2: WI-LLM-0058 added secondary_genre sanitization to assess_story() (a
# corrupted value is now stripped to "" and flagged, not left as-is) - a
# checkpoint written under v1 may have cached a pre-fix, unsanitized
# (corrupted) secondary_genre value; bumping forces a resumed `lcats
# annotate` run to re-classify rather than silently rewriting a corrupted
# genre.json forever (review finding, PR #267).
_GENRE_POSTPROCESS_VERSION = "v2"


class EmptyCollectionError(ValueError):
    """Raised when a requested collection directory is missing or
    contains no canonical story buckets -- mirrors promote.survey_
    collection's story_count > 0 guard, so `lcats annotate <collection>`
    cannot silently succeed while doing nothing (review finding, PR #241)."""


def _hash_text(text: str) -> str:
    """Deterministic hash of text, for checkpoint fingerprints -- not a
    security hash, just change detection (matches the pattern established
    in experiments/03_cross_segment_relation_pilot/run_pilot.py's
    _hash_json)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def story_item_id(collection_name: str, story_dir_name: str) -> str:
    """Flatten (collection, story) into a single checkpoint-safe item_id.

    Every canonical story file's own leaf filename is literally
    "story.json" post PROP-LCATS-STORY-BUCKET-LAYOUT, so identity must
    come from the bucket directory names, not the file itself. Combines
    collection + story bucket name with "__", since checkpoint item_ids
    must be a single path segment (see checkpoint._validate_path_component)
    -- the same pattern run_pilot.py's _story_identity already
    established for this identical collision risk.
    """
    return f"{collection_name}__{story_dir_name}"


@dataclasses.dataclass(frozen=True)
class AnnotateStoryResult:
    """Outcome of annotating a single story bucket."""

    story_path: pathlib.Path
    genre_error: Optional[str] = None
    scenes_error: Optional[str] = None

    @property
    def clean(self) -> bool:
        return self.genre_error is None and self.scenes_error is None


def _hash_json(obj: Any) -> str:
    """Deterministic hash of a JSON-serializable value (e.g. a tool
    schema), for checkpoint fingerprints."""
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def _genre_fingerprint(
    model: str, max_tokens: int, story_data: dict, body: str
) -> dict:
    """Fingerprint the complete effective assessment input, not just body
    -- assess_story also sends author/url (from metadata) to the model
    and stores them in AssessmentResult, so a metadata-only change (no
    body change) must still invalidate the checkpoint (review finding,
    PR #241). Title is intentionally excluded: infer_story_title derives
    it purely from the bucket directory name, already encoded in
    item_id -- it cannot change independently of that."""
    metadata = story_data.get("metadata") or {}
    return {
        "model": model,
        "max_tokens": max_tokens,
        "system_prompt_hash": _hash_text(assess.DETECT_SYSTEM_PROMPT),
        "tool_schema_hash": _hash_json(assess.ASSESSMENT_TOOL),
        "postprocess_version": _GENRE_POSTPROCESS_VERSION,
        "author": metadata.get("author", "Unknown"),
        "url": metadata.get("url", ""),
        "body_hash": _hash_text(body),
    }


def _scenes_fingerprint(model: str, max_tokens: int, body: str) -> dict:
    return {
        "model": model,
        "max_tokens": max_tokens,
        "system_prompt_hash": _hash_text(scene_analysis.SCENE_SEQUEL_SYSTEM_PROMPT),
        "user_prompt_template_hash": _hash_text(
            scene_analysis.SCENE_SEQUEL_USER_PROMPT_TEMPLATE
        ),
        "tool_schema_hash": _hash_json(scene_analysis.SEGMENT_TOOL_SCHEMA),
        "body_hash": _hash_text(body),
    }


def _annotate_genre(
    *,
    story_path: pathlib.Path,
    item_id: str,
    story_data: dict,
    body: str,
    backend: Any,
    model: str,
    max_tokens: int,
    roots: checkpoint.CheckpointRoots,
) -> tuple[Optional[dict], Optional[str], bool]:
    """Return (genre_data, error, from_cache). genre_data is the sidecar
    payload to write; error is set (genre_data is None) only on an
    unrecoverable failure. A checkpoint hit skips the paid assess_story
    call entirely and returns from_cache=True, so callers can tell a
    genuinely fresh assessment (a real new observation, worth appending)
    apart from a resumed no-op replay of a prior one (nothing new to
    append -- see annotate_story's own use of this flag, review finding,
    PR #350's WI-GENRE-0076 self-review)."""
    fingerprint = _genre_fingerprint(model, max_tokens, story_data, body)
    cached = checkpoint.read_checkpoint(
        roots.working_root, item_id, "genre", fingerprint
    )
    if cached.done and isinstance(cached.data, dict):
        return cached.data, None, True

    result = assess.assess_story(
        story_path, genre="", backend=backend, model=model, max_tokens=max_tokens
    )
    if result.error:
        checkpoint.write_checkpoint(
            roots.working_root,
            item_id,
            "genre",
            outcome="failure",
            fingerprint=fingerprint,
            data={"error": result.error},
        )
        return None, result.error, False

    data = result.to_dict()
    checkpoint.write_checkpoint(
        roots.working_root,
        item_id,
        "genre",
        outcome="success",
        fingerprint=fingerprint,
        data=data,
    )
    return data, None, False


def _error_message(error: Any) -> str:
    """Extract a clean, human-readable message from an error value.

    api_error is a structured dict with its own "message" key; str()-ing
    the whole dict produces noisy Python-repr output and throws away that
    field (review finding, PR #241). extraction_error/alignment_error/
    validation_error are already plain strings.
    """
    if isinstance(error, dict):
        return str(error.get("message", error))
    return str(error)


def _annotate_scenes(
    *,
    item_id: str,
    body: str,
    backend: Any,
    model: str,
    max_tokens: int,
    roots: checkpoint.CheckpointRoots,
) -> tuple[Optional[dict], Optional[str]]:
    """Return (scenes_data, error), mirroring _annotate_genre's contract."""
    fingerprint = _scenes_fingerprint(model, max_tokens, body)
    cached = checkpoint.read_checkpoint(
        roots.working_root, item_id, "scenes", fingerprint
    )
    if cached.done and isinstance(cached.data, dict):
        return cached.data, None

    seg_extractor = scene_analysis.make_segment_extractor(
        backend, max_tokens=max_tokens
    )
    seg_result = seg_extractor.extract(body, model_name=model)
    # Check alignment_error/validation_error too, not just api_error/
    # extraction_error -- JSONPromptExtractor.extract() still sets
    # extracted_output on an alignment/validation exception (the raw,
    # un-aligned parsed value), which is truthy and would otherwise be
    # recorded as a successful checkpoint (review finding, PR #241).
    error = (
        seg_result.get("api_error")
        or seg_result.get("extraction_error")
        or seg_result.get("alignment_error")
        or seg_result.get("validation_error")
    )
    segments = seg_result.get("extracted_output") or []
    if error or not segments:
        error_message = (
            _error_message(error) if error else "segmentation produced no segments"
        )
        checkpoint.write_checkpoint(
            roots.working_root,
            item_id,
            "scenes",
            outcome="failure",
            fingerprint=fingerprint,
            # Preserve the full structured error (not just the extracted
            # message) so a later diagnosis has the complete detail
            # (review finding, PR #241).
            data={"error": error_message, "error_detail": error},
        )
        return None, error_message

    usage = seg_result.get("usage") or {}
    data = {
        "segments": segments,
        "segment_count": len(segments),
        "model": model,
        # Mirrors _annotate_genre's AssessmentResult.to_dict() fields, so
        # scenes.json carries the same cost-visibility data genre.json
        # already does -- previously omitted even though
        # JSONPromptExtractor.extract() already returns it in "usage"
        # (review finding, PR #253).
        "input_tokens": usage.get("input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
    }
    checkpoint.write_checkpoint(
        roots.working_root,
        item_id,
        "scenes",
        outcome="success",
        fingerprint=fingerprint,
        data=data,
    )
    return data, None


def _atomic_write_text(path: pathlib.Path, text: str) -> None:
    """Atomically publish a text file -- a plain write_text can leave a
    torn file if interrupted mid-write, even though (for a sidecar) the
    success checkpoint was already published (review finding, PR #241).
    Mirrors checkpoint.write_checkpoint's own tempfile+os.replace
    pattern; used for both JSON sidecars and README.md, since an
    interrupted README write is the identical failure mode (review
    finding, PR #241)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
            tmp_file.write(text)
        os.replace(tmp_name, path)
    except BaseException:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise


def _write_json(path: pathlib.Path, data: dict) -> None:
    _atomic_write_text(path, json.dumps(data, indent=2))


def _remove_if_exists(path: pathlib.Path) -> None:
    path.unlink(missing_ok=True)


def _write_readme(
    bucket_dir: pathlib.Path, story_data: dict, story_path: pathlib.Path
) -> None:
    """Write/update the bucket's README.md summarizing story.json plus
    whatever sidecars exist. Never matched by any JSON-only selector
    (find_json_files, iter_collection_story_files), so this is purely
    additive -- no discovery/promote/stats changes needed."""
    title = corpus_cli.infer_story_title(story_data, story_path)
    lines = [f"# {title}", ""]

    genre_path = bucket_dir / GENRE_SIDECAR_FILENAME
    if genre_path.is_file():
        genre_data = json.loads(genre_path.read_text(encoding="utf-8"))
        # genre-sidecar-v1's fields live nested under the latest
        # assessment's result, not at the top level -- reading the
        # top-level keys directly (the legacy-only shape) would silently
        # render blank/default values once a story's genre.json becomes
        # v1-shaped (review finding, PR #348).
        result = _latest_genre_assessment_result(genre_data)
        lines.append("## genre.json")
        lines.append(
            f"- detected_genre: {result.get('detected_genre', '')}"
            f" (confidence {result.get('detected_genre_confidence', 0)})"
        )
        lines.append(f"- verdict: {result.get('verdict', '')}")
        lines.append("")

    scenes_path = bucket_dir / SCENES_SIDECAR_FILENAME
    if scenes_path.is_file():
        scenes_data = json.loads(scenes_path.read_text(encoding="utf-8"))
        lines.append("## scenes.json")
        lines.append(f"- segment_count: {scenes_data.get('segment_count', 0)}")
        lines.append("")

    _atomic_write_text(bucket_dir / "README.md", "\n".join(lines))


# method.name/version recorded on every model-sourced assessment this
# module builds -- distinct from _GENRE_POSTPROCESS_VERSION (which
# invalidates checkpoints) since this is sidecar-record provenance, not
# cache-fingerprint input.
_MODEL_ASSESSMENT_METHOD = {
    "name": "lcats.analysis.corpus.assess.assess_story",
    "version": "v1",
}


def lcats_story_id(collection_name: str, bucket_dir_name: str) -> str:
    """Return the canonical genre-sidecar-v1 lcats_id for a story bucket:
    "<collection>/<bucket>", matching the real evidence already committed
    in experiments/05_metadata_genre_prefilter/results/full_scan/ -- a
    different separator convention from story_item_id()'s checkpoint-safe
    "<collection>__<bucket>" (checkpoint item_ids must be a single path
    segment; genre-sidecar-v1 lcats_ids intentionally are not)."""
    return f"{collection_name}/{bucket_dir_name}"


def build_model_genre_assessment(
    result: dict,
    *,
    lcats_id: str,
    story_path_str: str,
    generated_at: Optional[str] = None,
    run_id: Optional[str] = None,
) -> dict:
    """Wrap one assess_story() result (an AssessmentResult.to_dict()
    payload) as a genre-sidecar-v1 model-sourced assessment record.

    `result` becomes the assessment's own `result` field verbatim, so
    every field assess_story() ever produces stays available to
    consumers (e.g. _write_readme below) without a second hand-maintained
    field list drifting out of sync with AssessmentResult.
    """
    generated_at = (
        generated_at or datetime.datetime.now(datetime.timezone.utc).isoformat()
    )
    run_id = run_id or generated_at
    return {
        "assessment_id": f"model_detect:{lcats_id.replace('/', '__')}:{run_id}",
        "label": "model_detect",
        "generated_at": generated_at,
        "scope": "story",
        "method": dict(_MODEL_ASSESSMENT_METHOD),
        "provenance": {
            "backend_model": result.get("backend_model", ""),
            "input_tokens": result.get("input_tokens", 0),
            "output_tokens": result.get("output_tokens", 0),
            "run_id": run_id,
            "story_id": lcats_id,
            "story_path": story_path_str,
        },
        "evidence": {"error": result.get("error", "")},
        "result": result,
        "run_id": run_id,
    }


def build_human_genre_assessment(
    result: dict,
    *,
    lcats_id: str,
    story_path_str: str,
    reviewer: str,
    generated_at: Optional[str] = None,
) -> dict:
    """Wrap a human reviewer's genre judgment as a genre-sidecar-v1
    human-sourced assessment record. Exercised by this item's own tests
    only -- WI-GENRE-0076's Non-Goals exclude building an adjudication UI
    around this; the append mechanism itself must simply support both
    sources (acceptance criterion 6)."""
    generated_at = (
        generated_at or datetime.datetime.now(datetime.timezone.utc).isoformat()
    )
    return {
        "assessment_id": f"human_review:{lcats_id.replace('/', '__')}:{generated_at}",
        "label": "human_review",
        "generated_at": generated_at,
        "scope": "story",
        "method": {"name": "manual_review", "version": "v1"},
        "provenance": {
            "reviewer": reviewer,
            "story_id": lcats_id,
            "story_path": story_path_str,
        },
        "evidence": {},
        "result": result,
    }


def _legacy_flat_sidecar_to_assessment(
    legacy_data: dict,
    *,
    lcats_id: str,
    story_path_str: str,
    sidecar_path: pathlib.Path,
) -> dict:
    """Wrap an existing legacy flat AssessmentResult.to_dict() sidecar as
    one genre-sidecar-v1 assessment, preserving its content verbatim so
    conversion never discards prior evidence (acceptance criterion 2).
    The legacy shape never recorded generated_at/run_id, so both are
    synthesized from the sidecar file's own mtime -- the closest
    available proxy for when that assessment was actually produced."""
    try:
        generated_at = datetime.datetime.fromtimestamp(
            sidecar_path.stat().st_mtime, tz=datetime.timezone.utc
        ).isoformat()
    except OSError:
        generated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    run_id = f"legacy-conversion:{generated_at}"
    return build_model_genre_assessment(
        legacy_data,
        lcats_id=lcats_id,
        story_path_str=story_path_str,
        generated_at=generated_at,
        run_id=run_id,
    )


def merge_genre_sidecar(
    bucket_dir: pathlib.Path,
    *,
    lcats_id: str,
    story_path_str: str,
    new_assessment: dict,
) -> tuple[Optional[dict], Optional[str]]:
    """Return (sidecar_data, error): the genre-sidecar-v1 payload to write
    at bucket_dir/genre.json, merging `new_assessment` into whatever
    already exists there.

    - No existing file, or an unreadable/corrupt one: wraps a fresh v1
      record containing only `new_assessment` (acceptance criterion 3) --
      an unreadable file is treated the same as "nothing usable exists"
      rather than raised, since a torn/corrupt sidecar from an earlier
      interrupted run must not block annotation from proceeding.
    - A legacy flat sidecar: converts it to one assessment (preserving
      its evidence), then appends `new_assessment` (acceptance
      criterion 2).
    - A valid existing genre-sidecar-v1 record: appends `new_assessment`
      to its assessments[] list (acceptance criterion 1).
    - Anything else (a dict that is neither a valid v1 record nor a
      legacy flat sidecar): refuses to touch it, returning an error
      rather than silently overwriting content this module cannot
      recognize.

    The returned `sidecar_data` is always re-validated via
    genre_sidecar.validate_sidecar() before being returned; if that
    re-validation itself fails, returns (None, error) instead so the
    caller refuses to write (acceptance criterion 4).
    """
    sidecar_path = bucket_dir / GENRE_SIDECAR_FILENAME
    existing: Optional[dict] = None
    if sidecar_path.is_file():
        try:
            existing = json.loads(sidecar_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            existing = None

    if existing is None:
        assessments = [new_assessment]
    elif genre_sidecar.is_legacy_flat_sidecar(existing):
        legacy_assessment = _legacy_flat_sidecar_to_assessment(
            existing,
            lcats_id=lcats_id,
            story_path_str=story_path_str,
            sidecar_path=sidecar_path,
        )
        assessments = [legacy_assessment, new_assessment]
    else:
        validation = genre_sidecar.validate_sidecar(existing)
        if not validation.valid:
            findings = "; ".join(
                f"{finding.path}: {finding.message}" for finding in validation.findings
            )
            return None, (
                f"existing {GENRE_SIDECAR_FILENAME} is neither a valid "
                f"genre-sidecar-v1 record nor a legacy flat sidecar; "
                f"refusing to touch it ({findings})"
            )
        assessments = list(existing.get("assessments", [])) + [new_assessment]

    sidecar_data = {
        "schema_version": genre_sidecar.SCHEMA_VERSION,
        "lcats_id": lcats_id,
        "story_path": story_path_str,
        "assessments": assessments,
    }
    # A valid existing v1 record may carry a human adjudication pointer
    # -- rebuilding sidecar_data from scratch above must not silently
    # drop it (review finding, PR #350's WI-GENRE-0076 self-review).
    # Neither "no existing file" nor "legacy flat" can have one: the
    # legacy shape predates this field entirely.
    if isinstance(existing, dict) and existing.get("current_adjudication") is not None:
        sidecar_data["current_adjudication"] = existing["current_adjudication"]

    validation = genre_sidecar.validate_sidecar(sidecar_data)
    if not validation.valid:
        findings = "; ".join(
            f"{finding.path}: {finding.message}" for finding in validation.findings
        )
        return None, (
            f"merged genre-sidecar-v1 record failed validation, refusing "
            f"to write ({findings})"
        )
    return sidecar_data, None


def _latest_genre_assessment_result(genre_data: dict) -> dict:
    """Return the `result` fields to render in README.md's genre.json
    section, regardless of whether genre_data on disk is the legacy flat
    shape or a genre-sidecar-v1 record.

    v1's assessments[] is an append-only ledger in write order (this
    module's own merge_genre_sidecar always appends, never reorders or
    removes), so the most recently written assessment -- and therefore
    the one whose result best reflects the sidecar's current state -- is
    always its last element."""
    if genre_sidecar.is_legacy_flat_sidecar(genre_data):
        return genre_data
    assessments = genre_data.get("assessments")
    if isinstance(assessments, list) and assessments:
        last = assessments[-1]
        if isinstance(last, dict) and isinstance(last.get("result"), dict):
            return last["result"]
    return {}


def annotate_story(
    story_path: pathlib.Path,
    *,
    collection_name: str,
    backend: Any,
    model: str,
    roots: checkpoint.CheckpointRoots,
    genre_max_tokens: int = DEFAULT_GENRE_MAX_TOKENS,
    scenes_max_tokens: int = DEFAULT_SCENES_MAX_TOKENS,
) -> AnnotateStoryResult:
    """Annotate one story bucket: write genre.json, scenes.json, README.md.

    story_path is the story's own story.json file; sidecars are written
    into its parent (bucket) directory.
    """
    bucket_dir = story_path.parent
    item_id = story_item_id(collection_name, bucket_dir.name)

    story_data = corpus_cli.read_story_data(story_path)
    body = corpus_cli.coerce_story_text(story_data.get("body", ""))

    genre_data, genre_error, genre_from_cache = _annotate_genre(
        story_path=story_path,
        item_id=item_id,
        story_data=story_data,
        body=body,
        backend=backend,
        model=model,
        max_tokens=genre_max_tokens,
        roots=roots,
    )
    # A failed recompute of a *legacy* single-result sidecar must not
    # leave a stale file from a prior, differently-configured run in
    # place -- the bucket would otherwise silently mix a new-config
    # scenes.json with an old-config genre.json (review finding, PR
    # #241). But an existing *valid v1* ledger is not "stale" the same
    # way: it holds independently-valid prior assessments that a new,
    # unrelated failed attempt did not invalidate, so it must survive
    # untouched rather than being deleted by that same cleanup (review
    # finding, PR #357) -- and a checkpoint hit only counts as "nothing
    # new to append" when the existing file is already that valid v1
    # shape; a pre-WI-GENRE-0076 legacy sidecar still needs converting
    # even on a cache hit, or it would never migrate (review finding, PR
    # #357).
    genre_sidecar_path = bucket_dir / GENRE_SIDECAR_FILENAME
    existing_is_valid_v1 = False
    if genre_sidecar_path.is_file():
        try:
            existing_genre_data = json.loads(
                genre_sidecar_path.read_text(encoding="utf-8")
            )
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            existing_genre_data = None
        if existing_genre_data is not None:
            existing_is_valid_v1 = genre_sidecar.validate_sidecar(
                existing_genre_data
            ).valid

    if genre_data is not None and genre_from_cache and existing_is_valid_v1:
        # A checkpoint hit against an already-migrated, valid v1 ledger
        # is a resumed no-op replay of a prior observation, not a new
        # one -- appending here would pile up a content-identical
        # assessment on every re-run of an unchanged config, defeating
        # this module's own checkpoint idempotency guarantee.
        pass
    elif genre_data is not None:
        lcats_id = lcats_story_id(collection_name, bucket_dir.name)
        story_path_str = f"{lcats_id}/{discovery.CANONICAL_STORY_FILENAME}"
        new_assessment = build_model_genre_assessment(
            genre_data, lcats_id=lcats_id, story_path_str=story_path_str
        )
        sidecar_data, merge_error = merge_genre_sidecar(
            bucket_dir,
            lcats_id=lcats_id,
            story_path_str=story_path_str,
            new_assessment=new_assessment,
        )
        if sidecar_data is not None:
            _write_json(bucket_dir / GENRE_SIDECAR_FILENAME, sidecar_data)
        else:
            genre_error = merge_error
    elif genre_error is not None and not existing_is_valid_v1:
        _remove_if_exists(genre_sidecar_path)

    scenes_data, scenes_error = _annotate_scenes(
        item_id=item_id,
        body=body,
        backend=backend,
        model=model,
        max_tokens=scenes_max_tokens,
        roots=roots,
    )
    if scenes_data is not None:
        _write_json(bucket_dir / SCENES_SIDECAR_FILENAME, scenes_data)
    elif scenes_error is not None:
        _remove_if_exists(bucket_dir / SCENES_SIDECAR_FILENAME)

    _write_readme(bucket_dir, story_data, story_path)

    return AnnotateStoryResult(
        story_path=story_path, genre_error=genre_error, scenes_error=scenes_error
    )


def annotate_collection(
    collection_dir: pathlib.Path,
    *,
    backend: Any,
    model: str,
    roots: checkpoint.CheckpointRoots,
    genre_max_tokens: int = DEFAULT_GENRE_MAX_TOKENS,
    scenes_max_tokens: int = DEFAULT_SCENES_MAX_TOKENS,
) -> list[AnnotateStoryResult]:
    """Annotate every story bucket in one collection directory.

    Uses discovery.iter_collection_story_files, the same narrower
    bucket-only selector promote.survey_collection uses -- deliberately
    not find_json_files, and deliberately called once per collection
    (never directly against a multi-collection root; see
    annotate_collections below).

    Raises:
        EmptyCollectionError: collection_dir is missing or contains no
            canonical story buckets -- a silent empty result would
            otherwise let `lcats annotate <collection>` appear to
            succeed while doing nothing (review finding, PR #241).
    """
    collection_name = collection_dir.name
    story_paths = list(discovery.iter_collection_story_files(collection_dir))
    if not story_paths:
        raise EmptyCollectionError(
            f"collection {collection_name!r} ({collection_dir}) is missing or "
            "contains no canonical story buckets"
        )
    return [
        annotate_story(
            story_path,
            collection_name=collection_name,
            backend=backend,
            model=model,
            roots=roots,
            genre_max_tokens=genre_max_tokens,
            scenes_max_tokens=scenes_max_tokens,
        )
        for story_path in story_paths
    ]


def annotate_collections(
    source_root: pathlib.Path,
    *,
    backend: Any,
    model: str,
    roots: checkpoint.CheckpointRoots,
    collection_names: Optional[list[str]] = None,
) -> dict[str, list[AnnotateStoryResult]]:
    """Annotate every requested collection under source_root.

    Enumerates collection directories first (mirroring
    promote.promote_collections's pattern) and calls
    annotate_collection once per collection -- discovery.
    iter_collection_story_files silently yields nothing if given a
    multi-collection root directly, since it only checks one level of
    nesting (review finding, PR #226).
    """
    if collection_names is None:
        collection_names = sorted(
            entry.name for entry in source_root.iterdir() if entry.is_dir()
        )

    return {
        name: annotate_collection(
            source_root / name, backend=backend, model=model, roots=roots
        )
        for name in collection_names
    }
