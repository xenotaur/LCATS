"""Bounded, explicitly-approved real measurement of Anthropic prompt
caching against the WI-PILOT-0051 fixture set (WI-PILOT-0057, Decision 3
of PROP-LCATS-PILOT-COST-SUSTAINABILITY).

Runs the real entity/event/relation/discourse extraction sequence
(experiments/03_cross_segment_relation_pilot's own run_pilot.py machinery,
unmodified) over the fixture set twice - once with prompt caching enabled,
once without - recording every real call's cache_creation_input_tokens/
cache_read_input_tokens/input_tokens/output_tokens via _RecordingBackend,
a thin wrapper around any LLMBackend. Segmentation runs once and is
checkpointed (WI-PIPELINE-0040/0041), so it is not re-billed for the
second (disabled) comparison run.

_RecordingBackend preserves the real per-segment interleaved call order
(entity -> event_anchor -> relation -> discourse per segment, across
every segment/story) that lcats.analysis.event_role_world.processor
naturally produces - not an artificially same-extractor-grouped
sequence, which would overstate any real cache-hit rate given the
5-minute cache TTL (see the governing work item's own Risk Notes).

**Requires real, paid Anthropic API calls when run without --dry-run.**
Do not run against the real API without explicit, in-session human
approval - see WI-PILOT-0057's own forbidden_actions
(run_real_llm_calls_without_explicit_approval). --dry-run exercises the
full wiring with a FakeBackend at zero cost, for validating this script
itself before any real spend.

Usage:
    python measure_prompt_caching.py --dry-run
    python measure_prompt_caching.py --output-dir results/caching_eval
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

from typing import Any, Dict, List, Optional

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import run_pilot  # noqa: E402 - see sys.path.insert above

from lcats.utils import checkpoint  # noqa: E402
from lcats.utils import secrets  # noqa: E402


class _RecordingBackend:
    """Wraps any LLMBackend, recording every complete() call's
    BackendResponse fields in real chronological order.

    Delegates the actual call through unchanged - this is purely an
    observer, not a behavior change, so it is safe to wrap either a real
    backend or a FakeBackend for testing.
    """

    def __init__(self, inner: Any):
        self._inner = inner
        self.calls: List[Dict[str, Any]] = []

    def complete(self, **kwargs: Any):
        response = self._inner.complete(**kwargs)
        tool = kwargs.get("tool") or {}
        self.calls.append(
            {
                "tool_name": tool.get("name"),
                "model": response.model,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "cache_creation_input_tokens": response.cache_creation_input_tokens,
                "cache_read_input_tokens": response.cache_read_input_tokens,
            }
        )
        return response


_DRY_RUN_SEGMENT_RESULT = {
    "segments": [
        {
            "segment_id": 1,
            "segment_type": "narrative_scene",
            "start_par_id": 1,
            "end_par_id": 1,
            "start_exact": "",
            "end_exact": "",
            "start_prefix": "",
            "end_suffix": "",
            "start_char": 0,
            "end_char": 1,
            "summary": "dry-run placeholder segment",
            "cohesion": {"time": "", "place": "", "characters": []},
            "gacd": None,
            "erac": None,
            "reason": "dry-run",
            "confidence": 0.5,
        }
    ]
}


class _DryRunFakeBackend:
    """Zero-cost stand-in for the real Anthropic backend under --dry-run.

    A plain FakeBackend(tool_result={}) fails segmentation's own hard
    "produced no segments" check (run_pilot._segment_story), so this
    returns a fixed single-segment result specifically for the
    "record_segments" tool call, and an empty-but-schema-tolerant result
    for every other call - real extraction stages handle an empty
    tool_result as "nothing found", not an error. Dispatches on the
    requested tool's name rather than call order/count, so a checkpoint
    hit on a later comparison run (which skips the segmentation call
    entirely - see run_pilot._segment_story_cached) can't shift which
    call this fake thinks is "the segmentation call".
    """

    def complete(self, **kwargs: Any):
        from lcats.llm import backend as llm_backend

        tool = kwargs.get("tool") or {}
        is_segment_call = tool.get("name") == "record_segments"
        tool_result = _DRY_RUN_SEGMENT_RESULT if is_segment_call else {}
        return llm_backend.BackendResponse(
            text="",
            tool_result=tool_result,
            model="fake-1.0",
            input_tokens=5,
            output_tokens=2,
            cache_creation_input_tokens=None,
            cache_read_input_tokens=None if is_segment_call else 0,
            raw=None,
        )


# Verified 2026-08-09 against platform.claude.com/docs/en/about-claude/pricing
# ("Model pricing" and "Prompt caching" tables). $/MTok. Cache-write uses the
# 5-minute-TTL multiplier (1.25x base input) - this script never sets a
# non-default `ttl` on CacheControlEphemeralParam (see anthropic_backend.py),
# so every real cache write here is a 5-minute write, never the 1-hour rate.
_MODEL_PRICING_PER_MTOK: Dict[str, Dict[str, float]] = {
    "claude-opus-4-8": {
        "input": 5.0,
        "output": 25.0,
        "cache_write": 5.0 * 1.25,
        "cache_read": 5.0 * 0.1,
    },
}


def _compute_cost_usd(run_totals: Dict[str, int], model: str) -> Optional[float]:
    """Real measured cost in USD for one comparison arm's totals, per
    Anthropic's published per-model pricing - not just a raw token sum,
    since input/output/cache-write/cache-read are billed at different
    rates (WI-PILOT-0057, review finding). Returns None for a model this
    script doesn't have verified pricing for, rather than guessing."""
    pricing = _MODEL_PRICING_PER_MTOK.get(model)
    if pricing is None:
        return None
    return (
        run_totals["total_input_tokens"] * pricing["input"]
        + run_totals["total_output_tokens"] * pricing["output"]
        + run_totals["total_cache_creation_input_tokens"] * pricing["cache_write"]
        + run_totals["total_cache_read_input_tokens"] * pricing["cache_read"]
    ) / 1_000_000


def _fixtures_dir() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent / "fixtures"


def _fixture_stories(fixtures_dir: Optional[pathlib.Path] = None) -> List[pathlib.Path]:
    """The WI-PILOT-0051 fixture set's committed stories, in a fixed,
    reproducible order (sorted by name) - not the manifest file, which
    also carries genre labels this measurement doesn't need.

    fixtures_dir defaults to _fixtures_dir() but honors a caller-supplied
    root (e.g. run_comparison's own source_root), so a caller pointing at
    a different fixture root doesn't also have to separately inject
    stories= to make discovery consistent with it (review finding)."""
    root = fixtures_dir if fixtures_dir is not None else _fixtures_dir()
    return sorted(root.glob("*/story.json"))


def preflight_prefix_token_counts(model: str) -> Dict[str, int]:
    """Count each ERW extractor's tools+system prefix token size via the
    Anthropic SDK's free (non-generation) count_tokens endpoint, before
    any real measurement call - a prefix below Anthropic's minimum
    cacheable-prefix length makes a zero cache_read_input_tokens result
    the *correct*, expected outcome, not a signal to investigate further
    (WI-PILOT-0057, Required Change 3).

    Still a real, live API call (network + auth), even though it is not
    a billed generation call - do not call this without the same
    explicit human approval real measurement calls require.
    """
    import anthropic

    client = anthropic.Anthropic()
    # backend=None: only .system_prompt/.tool_schema are read below: no
    # extractor.complete()/.extract() call is made, so no real backend
    # instance is needed to build these extractor objects.
    extractors = run_pilot._build_erw_extractors(None, model)
    counts: Dict[str, int] = {}
    for name, extractor in extractors.items():
        if extractor.tool_schema is None:
            continue
        tool = {**extractor.tool_schema, "cache_control": {"type": "ephemeral"}}
        result = client.messages.count_tokens(
            model=model,
            system=[
                {
                    "type": "text",
                    "text": extractor.system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=[tool],
            messages=[{"role": "user", "content": "x"}],
        )
        counts[name] = result.input_tokens
    return counts


def _warm_segmentation_checkpoints(
    stories: List[pathlib.Path],
    model: str,
    roots: checkpoint.CheckpointRoots,
    backend: Any,
) -> None:
    """Segment every story once, before either comparison arm starts
    recording, so both arms see identical, already-cached segmentation.

    Without this, whichever arm runs first pays for (and records) real
    segmentation calls that the second arm then skips entirely via
    run_pilot._segment_story_cached's own checkpoint reuse - confounding
    the comparison with a workload difference that has nothing to do
    with caching (review finding, PR #271). Segmentation itself is never
    part of what this evaluation measures: Decision 3 scopes caching to
    the ERW extractors' tools+system prefix only, and segmentation uses
    an entirely different tool schema (record_segments), so it was never
    a caching-eligible call in the first place - it just needs to be
    equally absent from both arms' recorded totals, not present in one
    and missing from the other.
    """
    for story_path in stories:
        story = json.loads(story_path.read_text(encoding="utf-8"))
        body = story["body"]
        _segments, seg_error, _seg_usage = run_pilot._segment_story_cached(
            story_path, body, backend, model, "anthropic", roots
        )
        if seg_error:
            raise RuntimeError(f"{story_path}: segmentation failed: {seg_error}")


def _extract_and_relate(
    story_path: pathlib.Path,
    backend: Any,
    model: str,
    roots: checkpoint.CheckpointRoots,
) -> Dict[str, Any]:
    """Run the real ERW extraction sequence AND the story-level
    cross-segment-relation pass for one fixture story, via
    run_pilot._run_erw_pipeline - the same composed, already-tested
    function main()'s own real pipeline uses (not just
    _run_erw_extraction alone, which explicitly excludes the
    cross-segment pass per its own docstring - review finding, PR #271:
    story_relation is a real, preflighted extractor that must actually
    be exercised, not built and never called).

    Assumes this story's segmentation checkpoint is already warm (see
    _warm_segmentation_checkpoints) - reads it via the same
    _segment_story_cached call, which is then guaranteed to hit the
    checkpoint and make no new call, so no segmentation call is ever
    recorded here."""
    story = json.loads(story_path.read_text(encoding="utf-8"))
    body = story["body"]
    story_id = run_pilot._story_identity(story_path)

    segments, seg_error, _seg_usage = run_pilot._segment_story_cached(
        story_path, body, backend, model, "anthropic", roots
    )
    if seg_error:
        raise RuntimeError(f"{story_path}: segmentation failed: {seg_error}")

    extractors = run_pilot._build_erw_extractors(backend, model)
    nlp_backend = run_pilot._make_nlp_backend("fake")
    return run_pilot._run_erw_pipeline(
        body, segments, extractors, nlp_backend, "fake", story_id
    )


def run_comparison(
    *,
    model: str,
    working_root: pathlib.Path,
    source_root: pathlib.Path,
    dry_run: bool,
    stories: Optional[List[pathlib.Path]] = None,
    backend_factory: Optional[Any] = None,
) -> Dict[str, Any]:
    """Run the real (or fake, under a caller-supplied backend_factory)
    comparison and return a JSON-serializable report: per-run call lists
    plus a summary.

    stories/backend_factory are injectable so tests can point this at a
    small synthetic fixture with a fully-known fake response sequence,
    without touching the real committed WI-PILOT-0051 fixture set (whose
    real segment counts a naive single-response FakeBackend cannot
    satisfy - segmentation and each extraction stage need distinct,
    schema-appropriate tool_results).
    """
    roots = checkpoint.resolve_roots(working_root, source_root=source_root)
    stories = stories if stories is not None else _fixture_stories(source_root)
    if not stories:
        raise RuntimeError(f"No fixture stories found under {source_root}")

    run_model = model if (backend_factory is not None or not dry_run) else "fake-1.0"

    def _build_backend(enable_caching: bool) -> Any:
        if backend_factory is not None:
            return backend_factory(enable_caching)
        if dry_run:
            return _DryRunFakeBackend()
        from lcats.llm import anthropic_backend

        return anthropic_backend.AnthropicBackend(enable_prompt_caching=enable_caching)

    # Warm segmentation once, before either arm starts recording, so
    # both arms see identical already-cached segmentation and neither
    # arm's own totals are confounded by which one happened to pay for
    # it (review finding, PR #271). Caching doesn't apply to
    # segmentation either way (different tool schema), so
    # enable_caching=False here is just a fixed, arbitrary choice, not
    # a meaningful one.
    _warm_segmentation_checkpoints(stories, run_model, roots, _build_backend(False))

    report: Dict[str, Any] = {
        "model": model,
        "stories": [run_pilot._story_identity(s) for s in stories],
        "runs": {},
    }

    for label, enable_caching in (
        ("caching_disabled", False),
        ("caching_enabled", True),
    ):
        recorder = _RecordingBackend(_build_backend(enable_caching))
        for story_path in stories:
            _extract_and_relate(story_path, recorder, run_model, roots)

        run_totals = {
            "enable_prompt_caching": enable_caching,
            "calls": recorder.calls,
            "total_input_tokens": sum(c["input_tokens"] for c in recorder.calls),
            "total_output_tokens": sum(c["output_tokens"] for c in recorder.calls),
            "total_cache_creation_input_tokens": sum(
                c["cache_creation_input_tokens"] or 0 for c in recorder.calls
            ),
            "total_cache_read_input_tokens": sum(
                c["cache_read_input_tokens"] or 0 for c in recorder.calls
            ),
        }
        run_totals["cost_usd"] = _compute_cost_usd(run_totals, model)
        report["runs"][label] = run_totals

    disabled_cost = report["runs"]["caching_disabled"]["cost_usd"]
    enabled_cost = report["runs"]["caching_enabled"]["cost_usd"]
    report["cost_delta_usd"] = (
        enabled_cost - disabled_cost
        if disabled_cost is not None and enabled_cost is not None
        else None
    )

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="claude-opus-4-8")
    parser.add_argument(
        "--output-dir",
        default=str(
            pathlib.Path(__file__).resolve().parent / "results" / "caching_eval"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Exercise the full wiring with a FakeBackend at zero cost - "
            "does NOT make any real API calls. Omit this flag only with "
            "explicit human approval for real, paid Anthropic API calls."
        ),
    )
    args = parser.parse_args()

    output_dir = pathlib.Path(args.output_dir)

    if not args.dry_run:
        secrets.load_secrets()
        # Preflight, per Required Change 3: a prefix below Anthropic's
        # minimum cacheable length makes a later zero cache_read result
        # expected, not a signal something is wrong - record it
        # alongside the measurement, not just print-and-discard it.
        prefix_token_counts = preflight_prefix_token_counts(args.model)
        print(
            "Preflight tools+system prefix token counts (before any real measurement call):"
        )
        for name, count in prefix_token_counts.items():
            print(f"  {name}: {count} tokens")
    else:
        prefix_token_counts = None

    report = run_comparison(
        model=args.model,
        working_root=output_dir,
        source_root=_fixtures_dir(),
        dry_run=args.dry_run,
    )
    report["preflight_prefix_token_counts"] = prefix_token_counts

    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "caching_comparison.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote comparison report to {report_path}")
    for label, run in report["runs"].items():
        cost = f"${run['cost_usd']:.4f}" if run["cost_usd"] is not None else "unpriced"
        print(
            f"  {label}: {len(run['calls'])} calls, "
            f"input={run['total_input_tokens']}, "
            f"output={run['total_output_tokens']}, "
            f"cache_creation={run['total_cache_creation_input_tokens']}, "
            f"cache_read={run['total_cache_read_input_tokens']}, "
            f"cost={cost}"
        )
    if report["cost_delta_usd"] is not None:
        print(f"  cost delta (enabled - disabled): ${report['cost_delta_usd']:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
