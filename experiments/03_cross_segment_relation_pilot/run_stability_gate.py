"""Run and validate the WI-PILOT-0067 bounded stability gate.

This script deliberately stays outside the production package. It wraps
the existing WI-PILOT-0051 targeted pilot harness, runs the separate
genre-detection check that targeted mode bypasses, validates the output
artifacts, and writes the stability-gate JSON/Markdown reports.

Real mode makes paid Anthropic API calls. Do not run without --dry-run
until an in-session human has approved the model choices, story count,
expected call count, expected artifacts, and estimated spend.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import time

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lcats" / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import run_pilot  # noqa: E402

from lcats.analysis.corpus import assess as corpus_assess  # noqa: E402
from lcats.llm import backend as llm_backend  # noqa: E402
from lcats.utils import secrets  # noqa: E402


DEFAULT_MODEL = "claude-opus-4-8"
EXPECTED_STORY_COUNT = 2
EXPECTED_STORY_IDS = ("fixtures__king_of_the_hill", "fixtures__unwelcomed_visitor")
STABILITY_MANIFEST = "stability_gate_manifest.txt"
EXPECTED_STAGES = {
    "segment",
    "surface_feature",
    "entity",
    "event_anchor",
    "relation",
    "discourse",
    "story_relation",
}
RESULT_FILES = (
    "pilot_stories.jsonl",
    "pilot_usage.jsonl",
    "pilot_summary.json",
    "genre_detection_results.json",
    "stability_gate_results.json",
    "stability_gate_report.md",
)

# Verified for prior WI-PILOT-0057/0060 cost work against Anthropic's
# published pricing. This gate only prices raw input/output generation.
MODEL_PRICING_PER_MTOK: Dict[str, Dict[str, float]] = {
    "claude-opus-4-8": {"input": 5.0, "output": 25.0},
}

THRESHOLDS = {
    "fixture_story_completion_rate": 1.0,
    "parseable_artifacts": True,
    "fatal_pilot_errors": 0,
    "schema_invalid_or_truncation_marked_final_artifacts": 0,
    "genre_correctness_rate": 1.0,
    "source_supported_semantic_output": True,
    "intended_purpose_fit": True,
}


@dataclass(frozen=True)
class FixtureStory:
    story_id: str
    manifest_spec: str
    genre: str
    path: pathlib.Path


class _DryRunGenreBackend:
    def __init__(self, expected_genres: Dict[str, str]):
        self.expected_genres = expected_genres

    def complete(self, **kwargs: Any) -> llm_backend.BackendResponse:
        message_text = "\n".join(
            str(m.get("content", "")) for m in kwargs.get("messages", [])
        )
        detected = "science fiction"
        for story_id, genre in self.expected_genres.items():
            title = story_id.removeprefix("fixtures__").replace("_", " ")
            if title in message_text.lower():
                detected = genre
                break
        return llm_backend.BackendResponse(
            text="",
            tool_result={
                "verdict": "include",
                "exclude_reason": "",
                "wellformed": True,
                "detected_genre": detected,
                "detected_genre_confidence": 1.0,
                "genre_verdict": "detected",
                "genre_suggestion": "",
                "secondary_genre": "",
                "specials_verdict": "none",
                "summary": "Dry-run genre assessment.",
                "issues": [],
            },
            model="fake-1.0",
            input_tokens=10,
            output_tokens=3,
            raw=None,
        )


def _experiment_dir() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent


def _repo_root() -> pathlib.Path:
    return _experiment_dir().parents[1]


def _fixtures_dir() -> pathlib.Path:
    return _experiment_dir() / "fixtures"


def _default_results_dir() -> pathlib.Path:
    return _experiment_dir() / "results" / "stability_gate"


def _repo_rel(path: pathlib.Path) -> str:
    try:
        return str(path.resolve().relative_to(_repo_root()))
    except ValueError:
        return str(path)


def _repo_rel_text(text: str) -> str:
    root = str(_repo_root())
    return text.replace(root + "/", "")


def _read_json(path: pathlib.Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: pathlib.Path) -> List[Dict[str, Any]]:
    rows = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
    return rows


def _load_story_set(fixtures_dir: pathlib.Path) -> List[FixtureStory]:
    manifest = fixtures_dir / STABILITY_MANIFEST
    truth = _read_json(fixtures_dir / "genre_ground_truth.json")
    stories: List[FixtureStory] = []
    for raw_line in manifest.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        spec, genre = line.split(":", 1)
        path = fixtures_dir.parent / spec / "story.json"
        story_id = run_pilot._story_identity(path)
        entry = truth.get(story_id.removeprefix("fixtures__"))
        if entry is None:
            raise ValueError(f"{story_id}: missing genre ground truth")
        if not entry.get("wellformed"):
            raise ValueError(f"{story_id}: fixture is not validated well-formed")
        if genre != entry.get("validated_genre"):
            raise ValueError(
                f"{story_id}: manifest genre {genre!r} does not match ground truth"
            )
        stories.append(FixtureStory(story_id, spec, genre, path))
    if len(stories) != EXPECTED_STORY_COUNT:
        raise ValueError(
            f"stability gate requires exactly {EXPECTED_STORY_COUNT} stories, "
            f"found {len(stories)}"
        )
    return stories


def _compute_cost_usd(input_tokens: int, output_tokens: int, model: str) -> Optional[float]:
    pricing = MODEL_PRICING_PER_MTOK.get(model)
    if pricing is None:
        return None
    return (
        input_tokens * pricing["input"] + output_tokens * pricing["output"]
    ) / 1_000_000


def _run_pilot(
    *,
    output_dir: pathlib.Path,
    model: str,
    dry_run: bool,
    nlp_backend: str,
) -> Dict[str, Any]:
    cmd = [
        sys.executable,
        str(_experiment_dir() / "run_pilot.py"),
        "--backend",
        "anthropic",
        "--model",
        model,
        "--story-list",
        str(_fixtures_dir() / STABILITY_MANIFEST),
        "--nlp-backend",
        nlp_backend,
        "--output",
        str(output_dir),
    ]
    if dry_run:
        cmd.append("--dry-run")
    started = time.monotonic()
    completed = subprocess.run(
        cmd,
        cwd=_repo_root(),
        text=True,
        capture_output=True,
        check=False,
    )
    display_cmd = []
    for part in cmd:
        if part == sys.executable:
            display_cmd.append("python")
        elif part.endswith(".py") or "/" in part:
            display_cmd.append(_repo_rel(pathlib.Path(part)))
        else:
            display_cmd.append(part)
    return {
        "command": display_cmd,
        "returncode": completed.returncode,
        "elapsed_seconds": time.monotonic() - started,
        "stdout": _repo_rel_text(completed.stdout),
        "stderr": _repo_rel_text(completed.stderr),
    }


def _genre_backend(dry_run: bool, stories: Iterable[FixtureStory]) -> Any:
    if dry_run:
        return _DryRunGenreBackend({story.story_id: story.genre for story in stories})
    from lcats.llm import anthropic_backend

    return anthropic_backend.AnthropicBackend()


def _run_genre_detection(
    stories: List[FixtureStory], *, model: str, dry_run: bool
) -> Dict[str, Any]:
    backend = _genre_backend(dry_run, stories)
    results = []
    for story in stories:
        assessed = corpus_assess.assess_story(story.path, backend=backend, model=model)
        result = assessed.to_dict()
        result["story_id"] = story.story_id
        result["file_path"] = _repo_rel(pathlib.Path(result["file_path"]))
        result["expected_genre"] = story.genre
        result["genre_correct"] = (
            not assessed.error and assessed.detected_genre == story.genre
        )
        result["schema_valid"] = not bool(assessed.error)
        result["truncation_marked"] = "truncat" in assessed.error.lower()
        results.append(result)
    input_tokens = sum(int(r.get("input_tokens", 0) or 0) for r in results)
    output_tokens = sum(int(r.get("output_tokens", 0) or 0) for r in results)
    return {
        "model": "fake-1.0" if dry_run else model,
        "dry_run": dry_run,
        "results": results,
        "total_input_tokens": input_tokens,
        "total_output_tokens": output_tokens,
        "cost_usd": _compute_cost_usd(input_tokens, output_tokens, model)
        if not dry_run
        else 0.0,
    }


def _contains_truncation_marker(value: Any) -> bool:
    if isinstance(value, str):
        return "truncat" in value.lower()
    if isinstance(value, dict):
        return any(_contains_truncation_marker(v) for v in value.values())
    if isinstance(value, list):
        return any(_contains_truncation_marker(v) for v in value)
    return False


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value)


def _is_nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and value >= 0


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _validate_summary_shape(summary: Any) -> List[str]:
    errors: List[str] = []
    if not isinstance(summary, dict):
        return ["pilot_summary.json: expected object"]
    required = {
        "backend": _is_nonempty_string,
        "by_genre": lambda value: isinstance(value, dict),
        "candidates_scanned": _is_nonnegative_int,
        "dry_run": lambda value: isinstance(value, bool),
        "model": _is_nonempty_string,
        "sample_size_target": _is_nonnegative_int,
        "stage_models": lambda value: isinstance(value, dict),
    }
    for key, predicate in required.items():
        if key not in summary:
            errors.append(f"pilot_summary.json: missing required field {key!r}")
        elif not predicate(summary[key]):
            errors.append(f"pilot_summary.json: invalid field {key!r}")

    by_genre = summary.get("by_genre")
    if isinstance(by_genre, dict):
        for genre in run_pilot.GENRES:
            item = by_genre.get(genre)
            if not isinstance(item, dict):
                errors.append(f"pilot_summary.json: missing by_genre entry {genre!r}")
                continue
            for key in (
                "included_count",
                "excluded_count",
                "mean_cross_segment_density_per_1000_words",
                "mean_weakly_inferred_cross_segment_density_per_1000_words",
                "mean_folded_relations_per_1000_words",
                "mean_folded_weakly_inferred_relations_per_1000_words",
            ):
                if key not in item:
                    errors.append(
                        f"pilot_summary.json: missing by_genre[{genre!r}][{key!r}]"
                    )
                elif not _is_number(item[key]):
                    errors.append(
                        f"pilot_summary.json: invalid by_genre[{genre!r}][{key!r}]"
                    )

    stage_models = summary.get("stage_models")
    if isinstance(stage_models, dict):
        for key in (
            "genre_detect",
            "segment",
            "entity",
            "event",
            "relation",
            "discourse",
            "cross_segment_relation",
        ):
            if not _is_nonempty_string(stage_models.get(key)):
                errors.append(f"pilot_summary.json: invalid stage_models[{key!r}]")
    return errors


def _validate_story_row_shape(row: Any, index: int) -> List[str]:
    prefix = f"pilot_stories.jsonl row {index}"
    errors: List[str] = []
    if not isinstance(row, dict):
        return [f"{prefix}: expected object"]
    required = {
        "story_id": _is_nonempty_string,
        "genre": _is_nonempty_string,
        "path": _is_nonempty_string,
        "word_count": _is_nonnegative_int,
        "excluded": lambda value: isinstance(value, bool),
        "exclude_reason": lambda value: isinstance(value, str),
    }
    for key, predicate in required.items():
        if key not in row:
            errors.append(f"{prefix}: missing required field {key!r}")
        elif not predicate(row[key]):
            errors.append(f"{prefix}: invalid field {key!r}")
    if not row.get("excluded"):
        for key in (
            "segment_count",
            "cross_segment_relation_count",
            "weakly_inferred_cross_segment_relation_count",
        ):
            if key not in row:
                errors.append(f"{prefix}: missing required field {key!r}")
            elif not _is_nonnegative_int(row[key]):
                errors.append(f"{prefix}: invalid field {key!r}")
        for key in (
            "cross_segment_density_per_1000_words",
            "weakly_inferred_cross_segment_density_per_1000_words",
            "folded_relations_per_1000_words",
            "folded_weakly_inferred_relations_per_1000_words",
        ):
            if key not in row:
                errors.append(f"{prefix}: missing required field {key!r}")
            elif not _is_number(row[key]):
                errors.append(f"{prefix}: invalid field {key!r}")
    return errors


def _validate_usage_row_shape(row: Any, index: int) -> List[str]:
    prefix = f"pilot_usage.jsonl row {index}"
    errors: List[str] = []
    if not isinstance(row, dict):
        return [f"{prefix}: expected object"]
    required = {
        "story_id": _is_nonempty_string,
        "pass_name": _is_nonempty_string,
        "input_tokens": _is_nonnegative_int,
        "output_tokens": _is_nonnegative_int,
        "is_llm_backed": lambda value: isinstance(value, bool),
        "model": _is_nonempty_string,
    }
    for key, predicate in required.items():
        if key not in row:
            errors.append(f"{prefix}: missing required field {key!r}")
        elif not predicate(row[key]):
            errors.append(f"{prefix}: invalid field {key!r}")
    return errors


def _checkpoint_outcome(output_dir: pathlib.Path, story_id: str, filename: str) -> str:
    path = output_dir / story_id / filename
    if not path.is_file():
        return ""
    try:
        payload = _read_json(path)
    except (OSError, json.JSONDecodeError):
        return ""
    if not isinstance(payload, dict):
        return ""
    outcome = payload.get("outcome")
    return outcome if isinstance(outcome, str) else ""


def _checkpoint_covers_stage(
    output_dir: pathlib.Path, story_id: str, stage: str, *, model: str, backend: str
) -> bool:
    stage_file = {
        "segment": "segment.json",
        "surface_feature": "erw_extract.json",
        "entity": "erw_extract.json",
        "event_anchor": "erw_extract.json",
        "relation": "erw_extract.json",
        "discourse": "erw_extract.json",
        "story_relation": "cross_segment_relation.json",
    }.get(stage)
    if not stage_file:
        return False
    path = output_dir / story_id / stage_file
    if not path.is_file():
        return False
    try:
        payload = _read_json(path)
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(payload, dict) or payload.get("outcome") != "success":
        return False
    fingerprint = payload.get("fingerprint")
    return (
        isinstance(fingerprint, dict)
        and fingerprint.get("model") == model
        and fingerprint.get("backend") == backend
    )


def _manual_review_from_existing(output_dir: pathlib.Path) -> Dict[str, Any]:
    path = output_dir / "stability_gate_results.json"
    if not path.is_file():
        return {}
    try:
        existing = _read_json(path)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(existing, dict):
        return {}
    semantic = existing.get("semantic_review")
    if not isinstance(semantic, dict):
        return {}
    status = semantic.get("status")
    if status not in {"reviewed_fail", "reviewed_pass"}:
        return {}
    return {
        "semantic_review": semantic,
        "final_recommendation": existing.get("final_recommendation"),
    }


def _apply_manual_review(
    results: Dict[str, Any], manual_review: Dict[str, Any]
) -> Dict[str, Any]:
    semantic = manual_review.get("semantic_review")
    if isinstance(semantic, dict):
        results["semantic_review"] = semantic
    recommendation = manual_review.get("final_recommendation")
    if isinstance(recommendation, str) and recommendation:
        results["final_recommendation"] = recommendation
    return results


def _validate_outputs(
    output_dir: pathlib.Path,
    stories: List[FixtureStory],
    pilot_run: Dict[str, Any],
    genre_results: Dict[str, Any],
    model: str,
    dry_run: bool,
) -> Dict[str, Any]:
    expected_ids = {story.story_id for story in stories}
    errors: List[str] = []
    missing_artifacts: List[str] = []
    parse_errors: List[str] = []
    parsed: Dict[str, Any] = {}

    for filename in ("pilot_stories.jsonl", "pilot_usage.jsonl", "pilot_summary.json"):
        path = output_dir / filename
        if not path.is_file():
            missing_artifacts.append(filename)
            errors.append(f"missing artifact: {filename}")
            continue
        try:
            parsed[filename] = (
                _read_jsonl(path) if filename.endswith(".jsonl") else _read_json(path)
            )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            parse_errors.append(str(exc))
            errors.append(str(exc))

    story_rows = parsed.get("pilot_stories.jsonl", [])
    usage_rows = parsed.get("pilot_usage.jsonl", [])
    summary = parsed.get("pilot_summary.json", {})
    if "pilot_summary.json" in parsed:
        errors.extend(_validate_summary_shape(summary))
    for index, row in enumerate(story_rows, 1):
        errors.extend(_validate_story_row_shape(row, index))
    for index, row in enumerate(usage_rows, 1):
        errors.extend(_validate_usage_row_shape(row, index))

    if len(story_rows) != len(stories):
        errors.append(f"expected {len(stories)} story rows, found {len(story_rows)}")
    invalid_story_id_count = sum(
        1
        for row in story_rows
        if not isinstance(row, dict) or not _is_nonempty_string(row.get("story_id"))
    )
    if invalid_story_id_count:
        errors.append(f"{invalid_story_id_count} story row(s) have invalid story_id")
    row_ids = {
        row.get("story_id")
        for row in story_rows
        if isinstance(row, dict) and _is_nonempty_string(row.get("story_id"))
    }
    if row_ids != expected_ids:
        errors.append(
            f"story ids mismatch: expected {sorted(expected_ids)}, got {sorted(row_ids)}"
        )

    excluded_rows = [
        row for row in story_rows if isinstance(row, dict) and row.get("excluded")
    ]
    truncation_rows = [row for row in story_rows if _contains_truncation_marker(row)]
    if excluded_rows:
        errors.append(f"{len(excluded_rows)} story row(s) were excluded")
    if truncation_rows:
        errors.append(f"{len(truncation_rows)} story row(s) contain truncation markers")

    expected_stages = (
        EXPECTED_STAGES - {"segment", "story_relation"} if dry_run else EXPECTED_STAGES
    )
    excluded_ids = {
        row.get("story_id")
        for row in excluded_rows
        if _is_nonempty_string(row.get("story_id"))
    }
    checkpointed_stages_by_story: Dict[str, List[str]] = {
        story.story_id: [] for story in stories
    }
    stages_by_story: Dict[str, List[str]] = {story.story_id: [] for story in stories}
    for usage in usage_rows:
        if not isinstance(usage, dict):
            continue
        story_id = usage.get("story_id")
        if story_id in stages_by_story:
            stages_by_story[story_id].append(str(usage.get("pass_name", "")))
    for story_id, stages in stages_by_story.items():
        missing = expected_stages - set(stages)
        checkpointed = {
            stage
            for stage in missing
            if story_id not in excluded_ids
            and _checkpoint_covers_stage(
                output_dir,
                story_id,
                stage,
                model=model,
                backend=str(parsed.get("pilot_summary.json", {}).get("backend", "")),
            )
        }
        if checkpointed:
            checkpointed_stages_by_story[story_id] = sorted(checkpointed)
            missing -= checkpointed
        if missing:
            errors.append(f"{story_id}: missing usage stages {sorted(missing)}")

    checkpointed_stage_count = sum(
        len(stages) for stages in checkpointed_stages_by_story.values()
    )
    spend_evidence_complete = checkpointed_stage_count == 0
    if checkpointed_stage_count and not dry_run:
        errors.append(
            "actual spend evidence is incomplete because "
            f"{checkpointed_stage_count} required stage(s) were satisfied by "
            "cached checkpoints without current usage rows"
        )

    genre_items = genre_results["results"]
    genre_errors = [
        item
        for item in genre_items
        if not item["schema_valid"]
        or item["truncation_marked"]
        or not item["genre_correct"]
        or not item.get("wellformed", False)
    ]
    if genre_errors:
        errors.append(f"{len(genre_errors)} genre-detection result(s) failed")

    if pilot_run["returncode"] != 0:
        errors.append(f"pilot returned nonzero exit code {pilot_run['returncode']}")

    pilot_input = sum(int(row.get("input_tokens", 0) or 0) for row in usage_rows)
    pilot_output = sum(int(row.get("output_tokens", 0) or 0) for row in usage_rows)
    genre_input = int(genre_results["total_input_tokens"])
    genre_output = int(genre_results["total_output_tokens"])
    total_input = pilot_input + genre_input
    total_output = pilot_output + genre_output
    actual_cost = (
        _compute_cost_usd(total_input, total_output, model) if not dry_run else 0.0
    )

    mechanical = {
        "parseable_artifacts": not missing_artifacts and not parse_errors,
        "missing_artifacts": missing_artifacts,
        "parse_errors": parse_errors,
        "story_count": len(story_rows),
        "completed_story_count": len(story_rows) - len(excluded_rows),
        "fatal_pilot_errors": 1 if pilot_run["returncode"] == 3 else 0,
        "schema_invalid_or_truncation_marked_final_artifacts": len(truncation_rows)
        + sum(
            1
            for item in genre_items
            if not item["schema_valid"] or item["truncation_marked"]
        ),
        "genre_correct_count": sum(1 for item in genre_items if item["genre_correct"]),
        "genre_total_count": len(genre_items),
        "wellformed_count": sum(1 for item in genre_items if item.get("wellformed")),
        "excluded_story_reasons": {
            row.get("story_id"): row.get("exclude_reason", "")
            for row in excluded_rows
            if _is_nonempty_string(row.get("story_id"))
        },
        "usage_stages_by_story": stages_by_story,
        "checkpointed_stages_by_story": checkpointed_stages_by_story,
        "spend_evidence_complete": spend_evidence_complete,
        "errors": errors,
    }
    mechanical["mechanical_pass"] = not errors
    mechanical_pass = bool(mechanical["mechanical_pass"])
    semantic_status = (
        "not_applicable_dry_run"
        if dry_run
        else "pending_manual_review"
        if mechanical_pass
        else "blocked_by_mechanical_validation"
    )
    recommendation = (
        "dry_run_only"
        if dry_run
        else "pending_manual_review"
        if mechanical_pass
        else "fail_no_go"
    )

    return {
        "dry_run": dry_run,
        "model": model,
        "story_set": [
            story.__dict__ | {"path": _repo_rel(story.path)} for story in stories
        ],
        "thresholds": THRESHOLDS,
        "pilot_run": pilot_run,
        "mechanical_validation": mechanical,
        "usage_totals": {
            "pilot_input_tokens": pilot_input,
            "pilot_output_tokens": pilot_output,
            "genre_input_tokens": genre_input,
            "genre_output_tokens": genre_output,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "actual_cost_usd": actual_cost,
        },
        "semantic_review": {
            "status": semantic_status,
            "source_supported_semantic_output": None if mechanical_pass else False,
            "intended_purpose_fit": None if mechanical_pass else False,
            "notes": [],
        },
        "final_recommendation": recommendation,
    }


def _write_json(path: pathlib.Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _normalize_pilot_story_paths(output_dir: pathlib.Path) -> None:
    path = output_dir / "pilot_stories.jsonl"
    if not path.is_file():
        return
    rows = _read_jsonl(path)
    for row in rows:
        if "path" in row:
            row["path"] = _repo_rel(pathlib.Path(row["path"]))
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def _render_report(results: Dict[str, Any], genre_results: Dict[str, Any]) -> str:
    validation = results["mechanical_validation"]
    usage = results["usage_totals"]
    semantic = results["semantic_review"]
    mode = "dry run" if results["dry_run"] else "real run"
    cost = usage["actual_cost_usd"]
    cost_text = "unpriced" if cost is None else f"${cost:.4f}"
    source_supported = semantic["source_supported_semantic_output"]
    intended_purpose = semantic["intended_purpose_fit"]
    lines = [
        "# WI-PILOT-0067 Stability Gate Report",
        "",
        "## Predeclared Run Plan",
        "",
        f"- Mode: {mode}",
        f"- Model: `{results['model']}`",
        "- Story count: 2 validated, well-formed fixture stories",
        "- Story set: `king_of_the_hill`, `unwelcomed_visitor`",
        "- Expected real call count: about 12-22 Anthropic calls "
        "(2 genre-detect + 2 segmentation + 4 ERW calls per segment + "
        "up to 1 cross-segment relation call per story)",
        "- Expected artifacts: " + ", ".join(f"`{name}`" for name in RESULT_FILES),
        "- Checkpoint policy: isolate the run under "
        "`results/stability_gate/`; stage fingerprints include model/backend/input "
        "state, so dry-run fake checkpoints do not satisfy the real Opus run.",
        "",
        "## Predeclared Thresholds",
        "",
    ]
    lines.extend(f"- `{key}`: `{value}`" for key, value in THRESHOLDS.items())
    lines.extend(
        [
            "",
            "## Mechanical Results",
            "",
            f"- Mechanical pass: `{validation['mechanical_pass']}`",
            f"- Completed stories: {validation['completed_story_count']}/{EXPECTED_STORY_COUNT}",
            f"- Genre correctness: {validation['genre_correct_count']}/{validation['genre_total_count']}",
            f"- Independent well-formedness pass: {validation['wellformed_count']}/{validation['genre_total_count']}",
            f"- Fatal pilot errors: {validation['fatal_pilot_errors']}",
            "- Schema/truncation-marked final artifacts: "
            f"{validation['schema_invalid_or_truncation_marked_final_artifacts']}",
            f"- Spend evidence complete: `{validation['spend_evidence_complete']}`",
            f"- Total input/output tokens: {usage['total_input_tokens']} / {usage['total_output_tokens']}",
            f"- Actual spend: {cost_text}",
            "",
            "## Genre Detection",
            "",
        ]
    )
    for item in genre_results["results"]:
        lines.append(
            f"- `{item['story_id']}`: expected `{item['expected_genre']}`, "
            f"detected `{item['detected_genre']}`, correct `{item['genre_correct']}`"
        )
    lines.extend(["", "## Validation Errors", ""])
    if validation["errors"]:
        lines.extend(f"- {error}" for error in validation["errors"])
    else:
        lines.append("- None")
    blocking_lines: List[str] = []
    for story_id, reason in validation["excluded_story_reasons"].items():
        if reason:
            blocking_lines.append(f"`{story_id}` did not complete the pipeline: {reason}.")
    for item in genre_results["results"]:
        if not item.get("wellformed", False):
            issue_text = ""
            issues = item.get("issues")
            if isinstance(issues, list) and issues:
                first_issue = issues[0]
                if isinstance(first_issue, dict):
                    issue_text = str(first_issue.get("description", ""))
            blocking_lines.append(
                f"`{item['story_id']}` was independently marked "
                f"`wellformed: false`/`verdict: {item.get('verdict', '')}`"
                + (f": {issue_text}" if issue_text else ".")
            )
    if blocking_lines:
        lines.extend(["", "Blocking failure modes:", ""])
        lines.extend(f"- {line}" for line in blocking_lines)
    lines.extend(
        [
            "",
            "## Semantic Review",
            "",
            f"- Status: `{semantic['status']}`",
            f"- Source-supported semantic output: `{source_supported}`",
            f"- Intended-purpose fit: `{intended_purpose}`",
            "",
        ]
    )
    if semantic["notes"]:
        lines.extend(f"- {note}" for note in semantic["notes"])
    else:
        lines.append("- No semantic notes recorded yet.")
    lines.extend(
        [
            "",
            "## Recommendation",
            "",
            f"`{results['final_recommendation']}`",
            "",
        ]
    )
    return "\n".join(lines)


def run_gate(*, output_dir: pathlib.Path, model: str, dry_run: bool, nlp_backend: str) -> Dict[str, Any]:
    if not dry_run:
        secrets.load_secrets()
    output_dir.mkdir(parents=True, exist_ok=True)
    manual_review = _manual_review_from_existing(output_dir)
    stories = _load_story_set(_fixtures_dir())
    pilot_run = _run_pilot(
        output_dir=output_dir,
        model=model,
        dry_run=dry_run,
        nlp_backend=nlp_backend,
    )
    _normalize_pilot_story_paths(output_dir)
    genre_results = _run_genre_detection(stories, model=model, dry_run=dry_run)
    _write_json(output_dir / "genre_detection_results.json", genre_results)
    results = _validate_outputs(output_dir, stories, pilot_run, genre_results, model, dry_run)
    if not dry_run:
        results = _apply_manual_review(results, manual_review)
    _write_json(output_dir / "stability_gate_results.json", results)
    (output_dir / "stability_gate_report.md").write_text(
        _render_report(results, genre_results), encoding="utf-8"
    )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--output-dir", type=pathlib.Path, default=_default_results_dir())
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run fake-backend validation only; no real API calls.",
    )
    parser.add_argument(
        "--nlp-backend",
        default=None,
        choices=["fake", "spacy", "stanza"],
        help="Defaults to fake for --dry-run and spacy for real runs.",
    )
    args = parser.parse_args()

    nlp_backend = args.nlp_backend or ("fake" if args.dry_run else "spacy")
    results = run_gate(
        output_dir=args.output_dir,
        model=args.model,
        dry_run=args.dry_run,
        nlp_backend=nlp_backend,
    )
    print(f"Wrote stability gate artifacts to {args.output_dir}")
    if results["mechanical_validation"]["mechanical_pass"]:
        print("Mechanical validation passed.")
        return 0
    print("Mechanical validation failed.", file=sys.stderr)
    for error in results["mechanical_validation"]["errors"]:
        print(f"  - {error}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
