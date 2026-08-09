"""Full-corpus genre census under the current 8-genre classifier (WI-ASSESS-0051).

See README.md in this directory for full usage instructions. Quick start
(from the repository root, conda environment active, API key configured):

    python experiments/04_genre_census/run_census.py --sample-size 20 --dry-run
    python experiments/04_genre_census/run_census.py --sample-size 20
    python experiments/04_genre_census/run_census.py --full

Two mutually exclusive, gated modes - exactly one of --sample-size/--full is
required on every invocation (neither given exits immediately with usage
information; this is the whole point of the cost gate this item exists to
enforce, not an oversight):

    --sample-size N   Run a small, population-weighted stratified sample of
                       N stories (proportional to each collection's real
                       share of the corpus, not equal-per-collection - see
                       build_population_weighted_sample) through detect-mode
                       assess_story(), measure real per-story token
                       cost/latency, and extrapolate to the full corpus.
                       Meant to be reviewed by a human BEFORE --full is ever
                       run.
    --full             Run every discovered story (resuming from any
                       existing checkpoints under --output). Real API cost
                       for ~1,868 stories - only run this after reviewing a
                       --sample-size estimate.

Other flags:

    --data-dir DIR    Corpus directory to scan (default: corpora - the
                       actual populated bucket-layout corpus at the repo
                       root; NOT run_pilot.py's "lcats/data" default, which
                       does not exist in this checkout - data/ regenerates
                       from cache and isn't checked in).
    --seed N          Sample-selection shuffle seed (default: 42).
    --backend NAME    "anthropic" (default) or "openai".
    --model NAME      Model string (default: claude-opus-4-8 / gpt-4o).
    --output DIR      Results/checkpoint directory (default: ./results next
                       to this script).
    --dry-run         Use a FakeBackend (zero API cost) instead of a real
                       one. Must be paired with --sample-size or --full -
                       zero-cost smoke test of file discovery and checkpoint
                       wiring, not a mode of its own.

Checkpointing: every story's genre-census classification is checkpointed
independently via lcats.utils.checkpoint under a single "genre_census"
stage - a crash or Ctrl-C preserves every already-classified story, and a
resumed run (same --output, same --data-dir) skips already-checkpointed,
successfully-completed stories instead of re-issuing their LLM call.
Checkpoints are written under --output (this script's own results
directory, never data/ or corpora/ directly - see
checkpoint.resolve_roots's write-guard); --data-dir is read-only input.

Cost note: this script makes one real LLM API call per story assessed
(detect-mode genre classification only - no segmentation, no
Event-Role-World extraction). See the local pricing constant below and the
README in this directory for the cost-estimation methodology, and the Risk
Notes in WI-ASSESS-0051 before running --full.

Exit codes:
    0   census completed (individual story failures are excluded and
        reported, not fatal)
    1   prerequisite check failed (missing install, missing key, bad flag
        combination, zero stories discovered, or an --output pointed at the
        protected data/corpora roots)
    3   aborted early on a fatal API error (bad credentials or exhausted
        account balance/quota) - every remaining story would fail
        identically. Any story results gathered before the abort are still
        written out.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import pathlib
import random
import sys
import time

from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Path bootstrap - allow running as `python experiments/.../run_census.py`
# from the repo root without requiring a prior `pip install -e .`.
# ---------------------------------------------------------------------------
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lcats" / "src"))

from lcats.analysis.corpus import assess as corpus_assess
from lcats.analysis.corpus import discovery
from lcats.utils import checkpoint
from lcats.utils.secrets import load_secrets

# Bumped whenever assess.py's classifier (prompts, schema, VALID_GENRES) OR
# assess_story()'s own post-processing of the raw tool result changes in a
# way that should invalidate every cached genre_census checkpoint - folded
# into this script's fingerprint below, mirroring run_pilot.py's own
# _CLASSIFIER_VERSION (experiments/03_cross_segment_relation_pilot/run_pilot.py,
# see _CLASSIFIER_VERSION there).
#
# v2: WI-LLM-0058 added secondary_genre sanitization to assess_story() - a
# checkpoint written under v1 may have cached a pre-fix, unsanitized
# (corrupted) secondary_genre value; bumping forces a resumed run to
# re-classify rather than silently serving that stale value forever.
_CLASSIFIER_VERSION = "v2"

# Approximate expected full-corpus story count (find corpora -iname
# story.json | wc -l, per WI-ASSESS-0051's own scoping) - used only as a
# sanity-check band, not an exact requirement, since the corpus can grow
# between when this was written and when the script runs.
_EXPECTED_STORY_COUNT_BAND = (1000, 5000)

# Substrings of an API error message that mean "stop the whole run", not
# "skip this one story" - mirrors run_pilot.py's own
# _FATAL_ERROR_SUBSTRINGS/_check_fatal (same rationale: continuing after a
# bad key/exhausted quota just burns time for no new information, since
# every remaining call would fail identically).
_FATAL_ERROR_SUBSTRINGS = (
    "credit balance",
    "insufficient_quota",
    "quota",
    "api key",
    "authentication",
)

# Approximate USD price per 1M tokens, as of when this script was written
# (2026-08) - NOT a durable pricing source of truth. There is no shared
# pricing/cost-tracking module anywhere in this codebase
# (PROP-LCATS-PIPELINE-CHECKPOINTING's Category E1 was explicitly deferred
# and remains unbuilt); this constant is deliberately script-local and
# scoped to this one-off survey, per WI-ASSESS-0051's Non-Goals. Check
# current provider pricing before trusting a cost estimate derived from
# this for a real budgeting decision.
_PRICING_USD_PER_MILLION_TOKENS: Dict[str, Tuple[float, float]] = {
    # model prefix -> (input $/1M tokens, output $/1M tokens)
    "claude-opus-4": (15.0, 75.0),
    "claude-sonnet-4": (3.0, 15.0),
    "claude-haiku-4": (0.8, 4.0),
    "gpt-4o": (2.5, 10.0),
}
# Fallback for an unrecognized model string: the most expensive tier known
# above, so an unrecognized model never silently understates the cost
# estimate.
_DEFAULT_PRICING_USD_PER_MILLION_TOKENS: Tuple[float, float] = (15.0, 75.0)


class FatalCensusError(RuntimeError):
    """Raised to abort the whole run on a non-retryable, account-level API
    error - mirrors run_pilot.py's FatalPilotError."""


def _check_fatal(message: str, context: str) -> None:
    lowered = message.lower()
    if any(s in lowered for s in _FATAL_ERROR_SUBSTRINGS):
        raise FatalCensusError(f"{context}: {message}")


def _price_for_model(model: str) -> Tuple[float, float]:
    for prefix, price in _PRICING_USD_PER_MILLION_TOKENS.items():
        if model.startswith(prefix):
            return price
    return _DEFAULT_PRICING_USD_PER_MILLION_TOKENS


def _estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    input_price, output_price = _price_for_model(model)
    return (input_tokens / 1_000_000) * input_price + (
        output_tokens / 1_000_000
    ) * output_price


def _story_identity(path: pathlib.Path) -> str:
    """Collection-qualified, checkpoint-safe identity for a canonical
    bucket story file (<collection>/<story>/story.json).

    Every bucket file's own leaf filename is literally "story.json" for
    every story, so path.stem alone collapses to "story" regardless of
    which story it is - mirrors run_pilot.py's own _story_identity fix for
    the same problem (see run_pilot.py's own _story_identity).
    """
    return f"{path.parent.parent.name}__{path.parent.name}"


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def _fingerprint(model: str, backend_name: str, raw_text: str) -> Dict[str, Any]:
    """Fingerprint hashes the actual story text (not just model/backend
    config) so a story corrected in place invalidates its own cached
    classification, plus a classifier-version marker so an assess.py
    classifier change invalidates every cached genre_census checkpoint."""
    return {
        "model": model,
        "backend": backend_name,
        "classifier_version": _CLASSIFIER_VERSION,
        "raw_text_hash": _hash_text(raw_text),
    }


def _is_valid_cache_payload(data: Any) -> bool:
    return isinstance(data, dict) and "detected_genre" in data


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

    return (
        fake_backend.FakeBackend(
            tool_result={"verdict": "keep", "detected_genre": "other"}
        ),
        "fake-1.0",
    )


def _iter_candidate_files(data_dir: pathlib.Path) -> List[pathlib.Path]:
    """List every canonical story file under data_dir, sorted for
    deterministic ordering.

    Uses discovery.find_json_files (bucket-aware), not the broader
    discovery.find_corpus_stories, per this project's own established
    convention - the broader selector is wrong whenever "is this a real
    story" is the actual question.
    """
    files = list(discovery.find_json_files([data_dir]))
    files.sort()
    return files


def build_population_weighted_sample(
    files: List[pathlib.Path], sample_size: int, seed: int
) -> List[pathlib.Path]:
    """Select sample_size stories, allocated proportionally to each
    collection's real share of the corpus (largest-remainder rounding),
    then randomly chosen within each collection.

    Deliberately NOT equal-per-collection: mass_quantities alone holds
    ~89% of the corpus with the rest split across ~11 much smaller
    collections, and body length (therefore token cost) varies by
    collection - an equal-per-collection sample would systematically
    misrepresent the corpus-wide average cost per story.
    """
    by_collection: Dict[str, List[pathlib.Path]] = collections.defaultdict(list)
    for f in files:
        by_collection[f.parent.parent.name].append(f)

    total = len(files)
    collection_names = sorted(by_collection)
    raw_allocation = {
        name: sample_size * len(by_collection[name]) / total
        for name in collection_names
    }
    allocation = {name: int(raw_allocation[name]) for name in collection_names}
    remainder = sample_size - sum(allocation.values())
    # Largest-remainder method: give the leftover slots to the collections
    # with the largest fractional part, so the total still sums exactly to
    # sample_size.
    by_fraction = sorted(
        collection_names,
        key=lambda name: raw_allocation[name] - allocation[name],
        reverse=True,
    )
    for name in by_fraction[:remainder]:
        allocation[name] += 1

    rng = random.Random(seed)
    sample: List[pathlib.Path] = []
    for name in collection_names:
        pool = list(by_collection[name])
        rng.shuffle(pool)
        sample.extend(pool[: allocation[name]])
    rng.shuffle(sample)
    return sample


def _classify_story(
    path: pathlib.Path,
    backend: Any,
    model: str,
    backend_name: str,
    roots: checkpoint.CheckpointRoots,
) -> Dict[str, Any]:
    """Classify one story (checkpointed), returning a per-story record dict.

    Raises FatalCensusError on an account-level API failure (bad
    credentials, exhausted quota) - every remaining story would fail
    identically, so the caller should stop the whole run rather than churn
    through the rest.
    """
    item_id = _story_identity(path)
    try:
        raw_text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return {
            "story_id": item_id,
            "file_path": str(path),
            "detected_genre": "other",
            "detected_genre_confidence": 0.0,
            "secondary_genre": "",
            "secondary_genre_sanitized": False,
            "error": f"could not read file: {exc}",
            "input_tokens": 0,
            "output_tokens": 0,
            "estimated_cost_usd": 0.0,
            "elapsed_seconds": 0.0,
            "backend_model": "",
            "from_cache": False,
        }

    fingerprint = _fingerprint(model, backend_name, raw_text)
    cached = checkpoint.read_checkpoint(
        roots.working_root, item_id, "genre_census", fingerprint
    )
    if cached.done and _is_valid_cache_payload(cached.data):
        record = dict(cached.data)
        record["from_cache"] = True
        return record

    start = time.perf_counter()
    result = corpus_assess.assess_story(path, genre="", backend=backend, model=model)
    elapsed = time.perf_counter() - start

    if result.error:
        _check_fatal(result.error, context=f"genre-census {path.name}")

    cost = _estimate_cost_usd(
        result.backend_model or model, result.input_tokens, result.output_tokens
    )
    record = {
        "story_id": item_id,
        "file_path": str(path),
        "detected_genre": result.detected_genre,
        "detected_genre_confidence": result.detected_genre_confidence,
        "secondary_genre": result.secondary_genre,
        "secondary_genre_sanitized": result.secondary_genre_sanitized,
        "error": result.error,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "estimated_cost_usd": cost,
        "elapsed_seconds": elapsed,
        "backend_model": result.backend_model or model,
        "from_cache": False,
    }
    checkpoint.write_checkpoint(
        roots.working_root,
        item_id,
        "genre_census",
        outcome="failure" if result.error else "success",
        fingerprint=fingerprint,
        data=record,
    )
    return record


def summarize(
    records: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Aggregate per-story records into per-genre counts and cost/latency
    totals. Failed records (error populated) are excluded from the genre
    counts but still counted toward cost/latency (a failed-but-billed call
    still consumed real tokens)."""
    genre_counts: Dict[str, int] = collections.Counter()
    excluded: List[Dict[str, str]] = []
    total_cost = 0.0
    total_input_tokens = 0
    total_output_tokens = 0
    total_elapsed = 0.0
    billed_count = 0
    secondary_genre_sanitized_count = 0

    for record in records:
        total_cost += record.get("estimated_cost_usd", 0.0)
        total_input_tokens += record.get("input_tokens", 0)
        total_output_tokens += record.get("output_tokens", 0)
        total_elapsed += record.get("elapsed_seconds", 0.0)
        if record.get("input_tokens", 0) > 0 or record.get("output_tokens", 0) > 0:
            billed_count += 1
        # WI-LLM-0058: count sanitized (corrupted-then-repaired)
        # secondary_genre values separately, so a census run reports its
        # own observed corruption rate rather than making a sanitized "",
        # a genuine "no secondary genre applies" "", indistinguishable.
        if record.get("secondary_genre_sanitized"):
            secondary_genre_sanitized_count += 1
        if record.get("error"):
            excluded.append({"story_id": record["story_id"], "reason": record["error"]})
            continue
        genre_counts[record.get("detected_genre", "other")] += 1

    for genre in corpus_assess.VALID_GENRES:
        genre_counts.setdefault(genre, 0)
    genre_counts.setdefault("other", 0)

    included_count = len(records) - len(excluded)
    exclusion_rate = len(excluded) / len(records) if records else 0.0

    # Flag a non-random-looking exclusion pattern: correlated with a
    # specific collection, rather than spread roughly evenly - a biased
    # exclusion pattern could skew the per-genre counts even if the
    # overall exclusion rate looks low.
    excluded_by_collection: Dict[str, int] = collections.Counter()
    for record in records:
        if record.get("error"):
            collection = record["story_id"].split("__", 1)[0]
            excluded_by_collection[collection] += 1

    return {
        "story_count": len(records),
        "included_count": included_count,
        "excluded_count": len(excluded),
        "exclusion_rate": exclusion_rate,
        "excluded_stories": excluded,
        "excluded_by_collection": dict(excluded_by_collection),
        "secondary_genre_sanitized_count": secondary_genre_sanitized_count,
        "genre_counts": dict(genre_counts),
        "total_estimated_cost_usd": total_cost,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "total_elapsed_seconds": total_elapsed,
        "billed_call_count": billed_count,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--data-dir", default="corpora")
    parser.add_argument("--sample-size", type=int, default=None)
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--backend", choices=["anthropic", "openai"], default="anthropic"
    )
    parser.add_argument("--model", default=None)
    parser.add_argument(
        "--output",
        default=str(pathlib.Path(__file__).resolve().parent / "results"),
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.sample_size is None and not args.full:
        parser.print_usage(sys.stderr)
        print(
            "error: exactly one of --sample-size N or --full is required "
            "(neither given) - this gate exists specifically so the paid "
            "full-corpus run never starts by accident.",
            file=sys.stderr,
        )
        return 1
    if args.sample_size is not None and args.full:
        print("error: --sample-size and --full are mutually exclusive", file=sys.stderr)
        return 1

    load_secrets()

    data_dir = pathlib.Path(args.data_dir)
    if not data_dir.exists():
        print(f"error: data dir not found: {data_dir}", file=sys.stderr)
        return 1

    output_dir = pathlib.Path(args.output)

    # Guard BEFORE creating output_dir - checkpoint.resolve_roots() does not
    # require the path to exist, so creating the directory first would let
    # a rejected --output still mutate the protected corpus tree before the
    # guard ever fires.
    try:
        roots = checkpoint.resolve_roots(working_root=output_dir, source_root=data_dir)
    except (checkpoint.ProtectedRootError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"Scanning {data_dir} for canonical story files...")
    files = _iter_candidate_files(data_dir)
    if not files:
        print(
            f"error: discovered 0 stories under {data_dir} - refusing to "
            "proceed with an empty result. Check --data-dir.",
            file=sys.stderr,
        )
        return 1
    low, high = _EXPECTED_STORY_COUNT_BAND
    if not (low <= len(files) <= high):
        print(
            f"warning: discovered {len(files)} stories, outside the expected "
            f"~1,868 sanity band ({low}-{high}) - double-check --data-dir "
            "before trusting this run's results.",
            file=sys.stderr,
        )
    print(f"Discovered {len(files)} stories.")

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

    if args.sample_size is not None:
        mode = "sample"
        targets = build_population_weighted_sample(files, args.sample_size, args.seed)
        print(
            f"Sample mode: {len(targets)} stories, population-weighted across "
            f"{len({f.parent.parent.name for f in files})} collections."
        )
    else:
        mode = "full"
        targets = files
        print(f"Full mode: {len(targets)} stories (resuming from any checkpoints).")

    records: List[Dict[str, Any]] = []
    aborted = False
    for i, path in enumerate(targets, start=1):
        try:
            record = _classify_story(path, backend, model, args.backend, roots)
        except FatalCensusError as exc:
            print(f"\nfatal: {exc}", file=sys.stderr)
            print(
                "Aborting - this looks like a bad/expired API key or an "
                "exhausted account balance/quota, not a per-story problem. "
                "Every remaining story would fail identically.",
                file=sys.stderr,
            )
            aborted = True
            break
        records.append(record)
        tag = "cached" if record.get("from_cache") else "billed"
        print(
            f"  [{i}/{len(targets)}] {record['story_id']} -> "
            f"{record['detected_genre']} ({tag})"
        )

    summary = summarize(records)
    summary["mode"] = mode
    summary["backend"] = args.backend
    summary["model"] = model
    summary["dry_run"] = args.dry_run
    summary["corpus_story_count"] = len(files)

    if mode == "sample" and records:
        # Use only freshly-classified (non-cached) records for the
        # extrapolation mean, not summary["total_..."] over every record: a
        # cache hit (served from a prior interrupted/re-run sample sharing
        # the same --output/--seed) contributes $0 new spend this run, and
        # averaging it in with len(records) as the denominator would dilute
        # the mean and silently understate the cost estimate this script's
        # entire cost gate depends on. A genuine $0 story (e.g. a file-read
        # error) is NOT excluded here - that is a real, representative
        # zero-cost outcome the full corpus will also see at roughly the
        # same rate, unlike a cache hit.
        fresh_records = [r for r in records if not r.get("from_cache")]
        if not fresh_records:
            print(
                "warning: every sampled story was served from a prior "
                "checkpoint cache - this run measured $0 new spend, so the "
                "extrapolated estimate below reflects no fresh signal. "
                "Use --output pointed at a fresh directory for a real "
                "cost estimate.",
                file=sys.stderr,
            )
        denominator_records = fresh_records or records
        fresh_cost = sum(r.get("estimated_cost_usd", 0.0) for r in denominator_records)
        fresh_elapsed = sum(r.get("elapsed_seconds", 0.0) for r in denominator_records)
        mean_cost = fresh_cost / len(denominator_records)
        mean_elapsed = fresh_elapsed / len(denominator_records)
        summary["extrapolated_full_corpus_cost_usd"] = mean_cost * len(files)
        summary["extrapolated_full_corpus_wall_clock_seconds"] = mean_elapsed * len(
            files
        )

    stories_path = output_dir / f"census_{mode}_stories.jsonl"
    with stories_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, sort_keys=True) + "\n")

    summary_path = output_dir / f"census_{mode}_summary.json"
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, sort_keys=True)

    print("\nPer-genre counts:")
    for genre in list(corpus_assess.VALID_GENRES) + ["other"]:
        print(f"  {genre:16s} {summary['genre_counts'].get(genre, 0)}")
    print(
        f"\nIncluded: {summary['included_count']}  Excluded: "
        f"{summary['excluded_count']} ({summary['exclusion_rate']:.1%})"
    )
    if summary["excluded_by_collection"]:
        print(f"Excluded by collection: {summary['excluded_by_collection']}")
    if summary["secondary_genre_sanitized_count"]:
        print(
            f"secondary_genre sanitized (corrupted tool-call output "
            f"repaired, WI-LLM-0058): {summary['secondary_genre_sanitized_count']}"
        )
    print(
        f"Measured cost: ${summary['total_estimated_cost_usd']:.4f} over "
        f"{summary['billed_call_count']} billed call(s), "
        f"{summary['total_elapsed_seconds']:.1f}s wall clock."
    )
    if mode == "sample" and records:
        print(
            f"\nExtrapolated FULL CORPUS estimate ({len(files)} stories): "
            f"${summary['extrapolated_full_corpus_cost_usd']:.2f}, "
            f"~{summary['extrapolated_full_corpus_wall_clock_seconds'] / 60:.1f} "
            "minutes wall clock.\n"
            "Review this estimate before running with --full."
        )
    print(f"\nWrote {stories_path}")
    print(f"Wrote {summary_path}")

    if aborted:
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
