"""Bounded model-tiering quality/cost comparison for WI-PILOT-0060.

Runs only the two stages Decision 5 scopes for cheaper-model evaluation:
genre detection and scene/sequel segmentation. The committed
WI-PILOT-0051 fixture set has two stories, so a real comparison is
bounded to 8 Anthropic generation calls: 2 models * 2 stories * 2 stages.

**Requires real, paid Anthropic API calls when run without --dry-run.**
Do not omit --dry-run without explicit, in-session human approval.

Usage:
    python measure_model_tiering.py --dry-run
    python measure_model_tiering.py \
        --baseline-model claude-opus-4-8 \
        --candidate-model claude-haiku-4-5-20251001
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import run_pilot  # noqa: E402 - see sys.path.insert above

from lcats.analysis import story_analysis  # noqa: E402
from lcats.analysis.corpus import assess as corpus_assess  # noqa: E402
from lcats.llm import backend as llm_backend  # noqa: E402
from lcats.utils import secrets  # noqa: E402

_DEFAULT_BASELINE_MODEL = "claude-opus-4-8"
_DEFAULT_CANDIDATE_MODEL = "claude-haiku-4-5-20251001"

# $/MTok. Defaults mirror Decision 5's cited comparison; callers can
# override pricing in the JSON post-processing if Anthropic changes rates.
_MODEL_PRICING_PER_MTOK: Dict[str, Dict[str, float]] = {
    "claude-opus-4-8": {"input": 5.0, "output": 25.0},
    "claude-haiku-4-5-20251001": {"input": 1.0, "output": 5.0},
}


def _fixtures_dir() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent / "fixtures"


def _repo_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[2]


def _display_path(path: pathlib.Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(_repo_root()))
    except ValueError:
        return str(resolved)


def _fixture_stories(fixtures_dir: Optional[pathlib.Path] = None) -> List[pathlib.Path]:
    root = fixtures_dir if fixtures_dir is not None else _fixtures_dir()
    return sorted(root.glob("*/story.json"))


def _ground_truth_path(fixtures_dir: Optional[pathlib.Path] = None) -> pathlib.Path:
    root = fixtures_dir if fixtures_dir is not None else _fixtures_dir()
    return root / "genre_ground_truth.json"


def _load_ground_truth(fixtures_dir: Optional[pathlib.Path] = None) -> Dict[str, Any]:
    path = _ground_truth_path(fixtures_dir)
    return json.loads(path.read_text(encoding="utf-8"))


def _story_key(path: pathlib.Path) -> str:
    return path.parent.name


def _is_truncation(error: Any) -> bool:
    if not error:
        return False
    if isinstance(error, dict):
        return error.get("code") == "truncated_output" or (
            error.get("category") == "truncated_output"
        )
    text = str(error).lower()
    return "truncated" in text or "max_tokens" in text


def _compute_cost_usd(
    input_tokens: int, output_tokens: int, model: str
) -> Optional[float]:
    pricing = _MODEL_PRICING_PER_MTOK.get(model)
    if pricing is None:
        return None
    return (
        input_tokens * pricing["input"] + output_tokens * pricing["output"]
    ) / 1_000_000


def _expected_json_type(schema_type: Any) -> Tuple[type, ...]:
    if isinstance(schema_type, list):
        return tuple(
            expected for item in schema_type for expected in _expected_json_type(item)
        )
    if schema_type == "object":
        return (dict,)
    if schema_type == "array":
        return (list,)
    if schema_type == "string":
        return (str,)
    if schema_type == "number":
        return (int, float)
    if schema_type == "integer":
        return (int,)
    if schema_type == "boolean":
        return (bool,)
    return (object,)


def _validate_schema_subset(
    value: Any, schema: Dict[str, Any], path: str = "$"
) -> List[str]:
    """Validate the JSON-schema subset used by ASSESSMENT_TOOL.

    This deliberately validates the raw tool arguments before assess_story()
    applies defaults and Python coercions, so malformed structured output
    cannot be counted as schema-valid in the model-tiering measurement.
    """
    errors: List[str] = []
    schema_type = schema.get("type")
    expected = _expected_json_type(schema_type)
    if expected != (object,) and not isinstance(value, expected):
        errors.append(f"{path} expected {schema_type}, got {type(value).__name__}")
        return errors
    if schema_type == "number" and isinstance(value, bool):
        errors.append(f"{path} expected number, got bool")
        return errors
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path} value {value!r} not in enum {schema['enum']!r}")
    if schema_type == "object":
        properties = schema.get("properties") or {}
        required = schema.get("required") or []
        for key in required:
            if key not in value:
                errors.append(f"{path}.{key} missing required field")
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in properties:
                    errors.append(f"{path}.{key} unexpected field")
        for key, child_schema in properties.items():
            if key in value:
                errors.extend(
                    _validate_schema_subset(value[key], child_schema, f"{path}.{key}")
                )
    if schema_type == "array":
        item_schema = schema.get("items") or {}
        for index, item in enumerate(value):
            errors.extend(
                _validate_schema_subset(item, item_schema, f"{path}[{index}]")
            )
    return errors


def _validate_assessment_tool_result(raw_tool_result: Any) -> List[str]:
    if raw_tool_result is None:
        return ["$ expected object, got None"]
    return _validate_schema_subset(
        raw_tool_result, corpus_assess.ASSESSMENT_TOOL["input_schema"]
    )


class _RecordingBackend:
    """Record every real/fake backend call while preserving behavior."""

    def __init__(self, inner: Any):
        self._inner = inner
        self.calls: List[Dict[str, Any]] = []

    def complete(self, **kwargs: Any):
        response = self._inner.complete(**kwargs)
        tool = kwargs.get("tool") or {}
        self.calls.append(
            {
                "tool_name": tool.get("name"),
                "requested_model": kwargs.get("model"),
                "model": response.model,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "tool_result": response.tool_result,
            }
        )
        return response


class _DryRunFakeBackend:
    """Schema-valid zero-cost backend for the two measured stages."""

    def complete(self, **kwargs: Any) -> llm_backend.BackendResponse:
        tool = kwargs.get("tool") or {}
        tool_name = tool.get("name")
        if tool_name == "record_story_assessment":
            tool_result = {
                "verdict": "include",
                "wellformed": True,
                "detected_genre": "science fiction",
                "detected_genre_confidence": 0.9,
                "genre_verdict": "detected",
                "secondary_genre": "",
                "specials_verdict": "none",
                "summary": "Dry-run fixture.",
                "issues": [],
            }
        elif tool_name == "record_segments":
            tool_result = {
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
                        "summary": "Dry-run placeholder.",
                        "cohesion": {"time": "", "place": "", "characters": []},
                        "gacd": None,
                        "erac": None,
                        "reason": "dry-run",
                        "confidence": 0.8,
                    }
                ]
            }
        else:
            tool_result = {}
        return llm_backend.BackendResponse(
            text="",
            tool_result=tool_result,
            model=kwargs.get("model", "fake-1.0"),
            input_tokens=10,
            output_tokens=3,
            raw=None,
        )


def _run_genre_detection(
    story_path: pathlib.Path,
    backend: Any,
    model: str,
    ground_truth: Dict[str, Any],
) -> Dict[str, Any]:
    result = corpus_assess.assess_story(story_path, backend=backend, model=model)
    raw_call = (getattr(backend, "calls", None) or [{}])[-1]
    raw_validation_errors = _validate_assessment_tool_result(
        raw_call.get("tool_result")
    )
    truth = ground_truth[_story_key(story_path)]
    schema_valid = not result.error and not raw_validation_errors
    genre_matches = result.detected_genre == truth["validated_genre"]
    return {
        "story_id": run_pilot._story_identity(story_path),
        "stage": "genre_detect",
        "schema_valid": bool(schema_valid),
        "raw_schema_valid": not raw_validation_errors,
        "raw_schema_errors": raw_validation_errors,
        "truncated": _is_truncation(result.error),
        "detected_genre": result.detected_genre,
        "secondary_genre_sanitized": result.secondary_genre_sanitized,
        "validated_genre": truth["validated_genre"],
        "genre_matches_ground_truth": bool(genre_matches),
        "wellformed": result.wellformed,
        "validated_wellformed": truth["wellformed"],
        "error": result.error,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "model": result.backend_model or model,
    }


def _run_segmentation(
    story_path: pathlib.Path, backend: Any, model: str
) -> Dict[str, Any]:
    story = json.loads(story_path.read_text(encoding="utf-8"))
    body = story_analysis.coerce_text(story.get("body", ""))
    segments, error, usage = run_pilot._segment_story(body, backend, model)
    return {
        "story_id": run_pilot._story_identity(story_path),
        "stage": "segment",
        "schema_valid": not error and bool(segments),
        "truncated": _is_truncation(error),
        "segment_count": len(segments),
        "error": error,
        "input_tokens": (usage or {}).get("input_tokens", 0) or 0,
        "output_tokens": (usage or {}).get("output_tokens", 0) or 0,
        "model": model,
    }


def _summarize_stage(
    rows: List[Dict[str, Any]], *, include_accuracy: bool
) -> Dict[str, Any]:
    total = len(rows)
    summary = {
        "total": total,
        "schema_valid_count": sum(1 for row in rows if row["schema_valid"]),
        "schema_valid_rate": (
            sum(1 for row in rows if row["schema_valid"]) / total if total else 0.0
        ),
        "truncation_count": sum(1 for row in rows if row["truncated"]),
        "truncation_rate": (
            sum(1 for row in rows if row["truncated"]) / total if total else 0.0
        ),
    }
    if include_accuracy:
        summary["genre_accuracy_count"] = sum(
            1 for row in rows if row["genre_matches_ground_truth"]
        )
        summary["genre_accuracy_rate"] = (
            summary["genre_accuracy_count"] / total if total else 0.0
        )
        summary["secondary_genre_sanitized_count"] = sum(
            1 for row in rows if row.get("secondary_genre_sanitized")
        )
        summary["secondary_genre_sanitized_rate"] = (
            summary["secondary_genre_sanitized_count"] / total if total else 0.0
        )
    return summary


def _summarize_run(stage_rows: List[Dict[str, Any]], model: str) -> Dict[str, Any]:
    input_tokens = sum(row["input_tokens"] for row in stage_rows)
    output_tokens = sum(row["output_tokens"] for row in stage_rows)
    genre_rows = [row for row in stage_rows if row["stage"] == "genre_detect"]
    segment_rows = [row for row in stage_rows if row["stage"] == "segment"]
    return {
        "model": model,
        "calls": len(stage_rows),
        "total_input_tokens": input_tokens,
        "total_output_tokens": output_tokens,
        "cost_usd": _compute_cost_usd(input_tokens, output_tokens, model),
        "stages": {
            "genre_detect": _summarize_stage(genre_rows, include_accuracy=True),
            "segment": _summarize_stage(segment_rows, include_accuracy=False),
        },
    }


def run_comparison(
    *,
    baseline_model: str,
    candidate_model: str,
    fixture_root: pathlib.Path,
    dry_run: bool,
    backend_factory: Optional[Any] = None,
) -> Dict[str, Any]:
    stories = _fixture_stories(fixture_root)
    if not stories:
        raise RuntimeError(f"No fixture stories found under {fixture_root}")
    ground_truth = _load_ground_truth(fixture_root)

    def _make_backend() -> Any:
        if backend_factory is not None:
            return backend_factory()
        if dry_run:
            return _DryRunFakeBackend()
        from lcats.llm import anthropic_backend

        return anthropic_backend.AnthropicBackend()

    report: Dict[str, Any] = {
        "baseline_model": baseline_model,
        "candidate_model": candidate_model,
        "stories": [run_pilot._story_identity(story) for story in stories],
        "fixture_root": _display_path(fixture_root),
        "ground_truth_path": _display_path(_ground_truth_path(fixture_root)),
        "runs": {},
    }

    for label, model in (
        ("baseline", baseline_model),
        ("candidate", candidate_model),
    ):
        backend = _RecordingBackend(_make_backend())
        stage_rows: List[Dict[str, Any]] = []
        for story_path in stories:
            stage_rows.append(
                _run_genre_detection(story_path, backend, model, ground_truth)
            )
            stage_rows.append(_run_segmentation(story_path, backend, model))
        run_summary = _summarize_run(stage_rows, model)
        run_summary["results"] = stage_rows
        run_summary["backend_calls"] = backend.calls
        report["runs"][label] = run_summary

    baseline_cost = report["runs"]["baseline"]["cost_usd"]
    candidate_cost = report["runs"]["candidate"]["cost_usd"]
    report["cost_delta_usd"] = (
        candidate_cost - baseline_cost
        if baseline_cost is not None and candidate_cost is not None
        else None
    )
    report["cost_savings_usd"] = (
        baseline_cost - candidate_cost
        if baseline_cost is not None and candidate_cost is not None
        else None
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-model", default=_DEFAULT_BASELINE_MODEL)
    parser.add_argument("--candidate-model", default=_DEFAULT_CANDIDATE_MODEL)
    parser.add_argument("--fixture-root", default=str(_fixtures_dir()))
    parser.add_argument(
        "--output-dir",
        default=str(
            pathlib.Path(__file__).resolve().parent / "results" / "model_tiering_eval"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Exercise wiring with a FakeBackend at zero cost. Omit only "
            "after explicit human approval for real, paid Anthropic calls."
        ),
    )
    args = parser.parse_args()

    if not args.dry_run:
        secrets.load_secrets()

    output_dir = pathlib.Path(args.output_dir)
    report = run_comparison(
        baseline_model=args.baseline_model,
        candidate_model=args.candidate_model,
        fixture_root=pathlib.Path(args.fixture_root),
        dry_run=args.dry_run,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "model_tiering_comparison.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Wrote comparison report to {report_path}")
    for label, run in report["runs"].items():
        cost = f"${run['cost_usd']:.4f}" if run["cost_usd"] is not None else "unpriced"
        print(
            f"  {label}: {run['calls']} calls, "
            f"input={run['total_input_tokens']}, "
            f"output={run['total_output_tokens']}, "
            f"cost={cost}"
        )
        for stage, stats in run["stages"].items():
            extra = ""
            if stage == "genre_detect":
                extra = f", genre_accuracy={stats['genre_accuracy_rate']:.0%}"
            print(
                f"    {stage}: schema_valid={stats['schema_valid_rate']:.0%}, "
                f"truncation={stats['truncation_rate']:.0%}{extra}"
            )
    if report["cost_savings_usd"] is not None:
        print(f"  savings (baseline - candidate): ${report['cost_savings_usd']:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
