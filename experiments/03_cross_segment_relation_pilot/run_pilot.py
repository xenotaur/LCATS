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
    --nlp-backend NAME      "spacy" (default) or "stanza", for stage-2 surface features
    --output DIR            Results directory (default: ./results next to this script)
    --dry-run               Skip real genre detection and use a FakeBackend for the
                            whole pipeline, so the script's control flow and output
                            files can be exercised with zero API cost. Produces
                            meaningless (empty) extraction results - never use its
                            output as a real finding.

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
call per candidate story scanned), scene/sequel segmentation (one or two
calls per sampled story), and the full Event-Role-World pipeline (roughly
5-6 calls per segment plus one story-level cross-segment-relation call per
story). Across 4 genres x 5-10 stories each, this is a real cost and
latency expenditure - see the Risk Notes in WI-EVENT-0030 and the README
in this directory before running against the full target sample size.

Exit codes:
    0   pilot completed (individual story exclusions are noted, not fatal)
    1   prerequisite check failed (missing install, missing key)
    2   could not fill every genre stratum before exhausting --max-candidates
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
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lcats"))

from lcats.analysis import scene_analysis
from lcats.analysis import story_analysis
from lcats.analysis.corpus import assess as corpus_assess
from lcats.analysis.event_role_world import processor as erw_processor
from lcats.utils.secrets import load_secrets

GENRES = (
    corpus_assess.VALID_GENRES
)  # ("science fiction", "horror", "western", "romance")


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


def run_story(
    path: pathlib.Path,
    genre: str,
    backend: Any,
    model: str,
    nlp_backend_name: str,
) -> Dict[str, Any]:
    """Run the full pipeline for one story; return a result row dict."""
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
        return row

    body = story_analysis.coerce_text(data.get("body", ""))
    word_count = story_analysis.word_count(body)
    row["word_count"] = word_count

    if not body.strip():
        row["excluded"] = True
        row["exclude_reason"] = "empty story body"
        return row

    segments, seg_error = _segment_story(body, backend, model)
    if seg_error or not segments:
        row["excluded"] = True
        row["exclude_reason"] = f"segmentation failed: {seg_error}"
        return row

    pipeline_result = erw_processor.process_segments(
        body,
        segments,
        nlp_backend_name=nlp_backend_name,
        llm_backend=backend,
        story_id=path.stem,
        include_cross_segment_relations=True,
    )

    extraction_errors = _has_extraction_errors(pipeline_result)
    if extraction_errors:
        row["excluded"] = True
        row["exclude_reason"] = "; ".join(extraction_errors)
        return row

    row.update(_compute_story_metrics(pipeline_result, word_count))
    row["segment_count"] = len(segments)
    return row


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
        else:
            mean_cross = mean_weak_cross = mean_folded = 0.0
        summary[genre] = {
            "included_count": len(included),
            "excluded_count": len(excluded),
            "mean_cross_segment_density_per_1000_words": mean_cross,
            "mean_weakly_inferred_cross_segment_density_per_1000_words": mean_weak_cross,
            "mean_folded_relations_per_1000_words": mean_folded,
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
    parser.add_argument("--nlp-backend", choices=["spacy", "stanza"], default="spacy")
    parser.add_argument(
        "--output",
        default=str(pathlib.Path(__file__).resolve().parent / "results"),
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

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
    sample, scanned = build_stratified_sample(
        data_dir,
        backend,
        model,
        args.sample_size,
        args.max_candidates,
        args.seed,
        args.dry_run,
    )
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

    rows: List[Dict[str, Any]] = []
    for genre in GENRES:
        for path in sample[genre]:
            print(f"Running pipeline: [{genre}] {path.name}")
            t0 = time.monotonic()
            row = run_story(path, genre, backend, model, args.nlp_backend)
            row["elapsed_seconds"] = time.monotonic() - t0
            rows.append(row)
            if row["excluded"]:
                print(f"  excluded: {row['exclude_reason']}")

    stories_path = output_dir / "pilot_stories.jsonl"
    with stories_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")

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
            f"folded_total={stats['mean_folded_relations_per_1000_words']:.3f}"
        )
    print(f"\nWrote {stories_path}")
    print(f"Wrote {summary_path}")

    if incomplete_genres and not args.dry_run:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
