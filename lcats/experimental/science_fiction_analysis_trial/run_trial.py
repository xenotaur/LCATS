"""Run the no-cost science-fiction sidecar fixture trial.

This experiment-local runner intentionally supports only fixture-backed,
zero-cost execution. It exercises deterministic sidecar assembly,
checkpoint reuse, publication, and validation without touching corpus or
production promotion paths.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import dataclasses
import hashlib
import json
import pathlib
import sys
from typing import Any, Iterable

from lcats.analysis.science_fiction import evidence
from lcats.analysis.science_fiction import knight
from lcats.analysis.science_fiction import models
from lcats.analysis.science_fiction import novum
from lcats.analysis.science_fiction import pipeline
from lcats.analysis.science_fiction import sidecar
from lcats.utils import checkpoint
from lcats.utils import paths

MANIFEST_VERSION = "science-fiction-trial-manifest-v1"
SUMMARY_VERSION = "science-fiction-trial-summary-v1"
FIXTURE_BACKEND = "fixture"
MAX_CONCURRENCY = 8
MAX_RETRIES = 3

FIXTURE_DIR = pathlib.Path(__file__).resolve().parent / "fixtures"
DEFAULT_MANIFEST = FIXTURE_DIR / "manifest.json"


@dataclasses.dataclass(frozen=True)
class TrialCase:
    case_id: str
    lcats_id: str
    story_path: str
    story_hash: str
    scenario: str
    tags: tuple[str, ...]
    expect_failure_kind: str | None = None


@dataclasses.dataclass(frozen=True)
class TrialManifest:
    manifest_path: pathlib.Path
    cases: tuple[TrialCase, ...]
    backend: str = FIXTURE_BACKEND
    estimated_cost_usd: float = 0.0
    version: str = MANIFEST_VERSION


@dataclasses.dataclass(frozen=True)
class RunnerOptions:
    manifest_path: pathlib.Path
    output_root: pathlib.Path
    dry_run: bool = False
    resume: bool = False
    max_retries: int = 0
    concurrency: int = 1


@dataclasses.dataclass(frozen=True)
class CaseResult:
    case_id: str
    lcats_id: str
    checkpoint_item_id: str
    status: str
    reused_checkpoint: bool
    attempts: int
    sidecar_path: str | None
    failure_kind: str | None
    validation_valid: bool | None

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    options = RunnerOptions(
        manifest_path=args.manifest,
        output_root=args.output_root,
        dry_run=args.dry_run,
        resume=args.resume,
        max_retries=args.max_retries,
        concurrency=args.concurrency,
    )
    summary = run_trial(options)
    sys.stdout.write(_stable_json(summary))
    return 0 if summary["status"] in {"dry_run", "complete"} else 1


def run_trial(options: RunnerOptions) -> dict[str, Any]:
    _validate_bounds(options)
    manifest = load_manifest(options.manifest_path)
    _validate_no_cost_fixture_manifest(manifest)
    output_root = _resolve_safe_output_root(options.output_root)
    manifest_fingerprint = _manifest_fingerprint(manifest)
    plan = {
        "case_count": len(manifest.cases),
        "concurrency": options.concurrency,
        "estimated_cost_usd": manifest.estimated_cost_usd,
        "manifest_fingerprint": manifest_fingerprint,
        "max_retries": options.max_retries,
        "resume": options.resume,
    }
    if options.dry_run:
        return _summary(
            status="dry_run",
            manifest=manifest,
            output_root=output_root,
            plan=plan,
            case_results=(),
        )

    case_results = _run_cases(manifest.cases, output_root, options)
    status = (
        "complete"
        if all(
            item.status in {"published", "expected_failure"} for item in case_results
        )
        else "failed"
    )
    summary = _summary(
        status=status,
        manifest=manifest,
        output_root=output_root,
        plan=plan,
        case_results=case_results,
    )
    _write_summary(output_root, summary)
    return summary


def load_manifest(path: pathlib.Path) -> TrialManifest:
    manifest_path = pathlib.Path(path)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if data.get("version") != MANIFEST_VERSION:
        raise ValueError(f"manifest version must be {MANIFEST_VERSION}")
    cases = tuple(_load_case(item) for item in data.get("cases", ()))
    case_ids = [item.case_id for item in cases]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("manifest case_id values must be unique")
    return TrialManifest(
        manifest_path=manifest_path,
        cases=cases,
        backend=data.get("backend", FIXTURE_BACKEND),
        estimated_cost_usd=float(data.get("estimated_cost_usd", 0.0)),
    )


def fixture_coverage(manifest: TrialManifest) -> set[str]:
    return {tag for case in manifest.cases for tag in case.tags}


def _load_case(data: dict[str, Any]) -> TrialCase:
    return TrialCase(
        case_id=_required_string(data, "case_id"),
        lcats_id=_required_string(data, "lcats_id"),
        story_path=_required_string(data, "story_path"),
        story_hash=_required_string(data, "story_hash"),
        scenario=_required_string(data, "scenario"),
        tags=tuple(data.get("tags", ())),
        expect_failure_kind=data.get("expect_failure_kind"),
    )


def _run_cases(
    cases: tuple[TrialCase, ...],
    output_root: pathlib.Path,
    options: RunnerOptions,
) -> tuple[CaseResult, ...]:
    if options.concurrency == 1:
        return tuple(_run_case(case, output_root, options) for case in cases)

    results_by_case_id: dict[str, CaseResult] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=options.concurrency) as pool:
        futures = {
            pool.submit(_run_case, case, output_root, options): case.case_id
            for case in cases
        }
        for future in concurrent.futures.as_completed(futures):
            results_by_case_id[futures[future]] = future.result()
    return tuple(results_by_case_id[case.case_id] for case in cases)


def _run_case(
    case: TrialCase,
    output_root: pathlib.Path,
    options: RunnerOptions,
) -> CaseResult:
    checkpoint_item_id = _checkpoint_item_id(case)
    attempts = 0
    max_attempts = options.max_retries + 1
    last_error: Exception | None = None
    while attempts < max_attempts:
        attempts += 1
        try:
            inputs = _fixture_inputs(case, options)
            result = pipeline.run_checkpointed_assembly(
                working_root=output_root,
                item_id=checkpoint_item_id,
                inputs=inputs,
            )
            path = pipeline.publish_sidecar(
                output_root=output_root,
                item_id=case.lcats_id,
                data=result.data,
            )
            validation = sidecar.validate_sidecar(result.data)
            return CaseResult(
                case_id=case.case_id,
                lcats_id=case.lcats_id,
                checkpoint_item_id=checkpoint_item_id,
                status="published",
                reused_checkpoint=result.reused,
                attempts=attempts,
                sidecar_path=str(path),
                failure_kind=None,
                validation_valid=validation.valid,
            )
        except Exception as error:
            last_error = error
            if (
                case.expect_failure_kind
                and _failure_kind(error) == case.expect_failure_kind
            ):
                return CaseResult(
                    case_id=case.case_id,
                    lcats_id=case.lcats_id,
                    checkpoint_item_id=checkpoint_item_id,
                    status="expected_failure",
                    reused_checkpoint=False,
                    attempts=attempts,
                    sidecar_path=None,
                    failure_kind=_failure_kind(error),
                    validation_valid=False,
                )
            if attempts >= max_attempts:
                break

    return CaseResult(
        case_id=case.case_id,
        lcats_id=case.lcats_id,
        checkpoint_item_id=checkpoint_item_id,
        status="failed",
        reused_checkpoint=False,
        attempts=attempts,
        sidecar_path=None,
        failure_kind=_failure_kind(last_error),
        validation_valid=False,
    )


def _fixture_inputs(
    case: TrialCase, options: RunnerOptions
) -> pipeline.SidecarAssemblyInputs:
    if case.scenario == "interrupted_stage":
        raise RuntimeError("interrupted_stage")
    evidence_set = _evidence_set(case)
    knight_analyses = _knight_analyses(case, evidence_set)
    suvin_analyses = _suvin_analyses(case, evidence_set)
    partial_success = _partial_success(case)
    story_hash = (
        f"{case.story_hash}-stale"
        if case.scenario == "stale_story_hash"
        else case.story_hash
    )
    return pipeline.SidecarAssemblyInputs(
        lcats_id=case.lcats_id,
        story_path=case.story_path,
        story_hash=story_hash,
        evidence_sets=(evidence_set,),
        knight_analyses=knight_analyses,
        suvin_novum_analyses=suvin_analyses,
        partial_success=partial_success,
        configuration={
            "backend": FIXTURE_BACKEND,
            "manifest_version": MANIFEST_VERSION,
            "resume": options.resume,
            "scenario": case.scenario,
        },
    )


def _evidence_set(case: TrialCase) -> evidence.EvidenceSet:
    records = (
        _record(
            "criterion_1",
            "storyworld_change",
            case,
            "The city moved beneath a second artificial sun.",
        ),
        _record(
            "criterion_2",
            "scientific_or_technical_explanation",
            case,
            "The engineers tuned the gravity lattice by measured increments.",
        ),
        _record(
            "criterion_3",
            "inquiry_or_scientific_method",
            case,
            "Mara repeated the trial until the readings matched.",
        ),
        _record(
            "novelty",
            "storyworld_change",
            case,
            "No village had ever grown memories in glass before.",
        ),
        _record(
            "cognition",
            "scientific_or_technical_explanation",
            case,
            "The process followed published neural chemistry.",
        ),
        _record(
            "hegemony",
            "extrapolative_consequence",
            case,
            "Every law in the colony bent around the memory harvest.",
        ),
        _record(
            "reader",
            "reader_facing_contrast",
            case,
            "To ordinary visitors, grief had become a public utility.",
        ),
        _record(
            "reaction",
            "character_reaction",
            case,
            "Jon stepped back from the speaking machine.",
        ),
    )
    quarantined = ()
    conflicts = ()
    if case.scenario == "malformed_model_output":
        quarantined = (
            evidence.QuarantinedEvidence(
                reason="missing quote",
                candidate=evidence.EvidenceCandidate(
                    evidence_type="storyworld_change",
                    quote="",
                    paraphrase="fixture malformed candidate",
                    confidence=0.0,
                    source="fixture",
                    schema_errors=("quote is required",),
                ),
            ),
        )
    if case.scenario == "overlap_duplicate_conflict":
        conflicts = (
            evidence.EvidenceConflict(
                conflict_id="conflict-overlap-1",
                evidence_ids=("novelty", "cognition"),
            ),
        )
    return evidence.EvidenceSet(
        evidence_set_id=f"{case.case_id}-evidence-v1",
        story_hash=case.story_hash,
        records=records,
        quarantined=quarantined,
        conflicts=conflicts,
    )


def _record(
    evidence_id: str,
    evidence_type: str,
    case: TrialCase,
    quote: str,
) -> evidence.EvidenceRecord:
    offset = len(evidence_id)
    return evidence.EvidenceRecord(
        evidence_id=evidence_id,
        evidence_type=evidence_type,
        quote=quote,
        anchor=evidence.EvidenceAnchor(
            paragraph_ids=_paragraph_ids(case, evidence_id),
            start_char=offset,
            end_char=offset + len(quote),
        ),
        paraphrase=f"{case.scenario} fixture evidence for {evidence_id}.",
        confidence=0.9,
        provenance=(
            evidence.EvidenceProvenance(
                source="fixture",
                source_chunk_id=_source_chunk_id(case, evidence_id),
                backend=FIXTURE_BACKEND,
            ),
        ),
    )


def _paragraph_ids(case: TrialCase, evidence_id: str) -> tuple[str, ...]:
    if case.scenario == "cross_chunk_evidence" and evidence_id in {
        "cognition",
        "hegemony",
    }:
        return (f"{case.case_id}-p0002",)
    return (f"{case.case_id}-p0001",)


def _source_chunk_id(case: TrialCase, evidence_id: str) -> str:
    if case.scenario == "cross_chunk_evidence" and evidence_id in {
        "cognition",
        "hegemony",
    }:
        return f"{case.case_id}-chunk-0002"
    return f"{case.case_id}-chunk-0001"


def _knight_analyses(
    case: TrialCase,
    evidence_set: evidence.EvidenceSet,
) -> tuple[models.KnightAnalysis, ...]:
    provenance = _provenance(case, models.KNIGHT_RUBRIC_VERSION)
    if case.scenario == "partial_knight_failure":
        return (
            knight.failed_analysis(
                analysis_id=f"{case.case_id}-knight-v1",
                story_hash=case.story_hash,
                evidence_set_id=evidence_set.evidence_set_id,
                provenance=provenance,
                failure=models.FailureRecord(
                    stage="knight",
                    kind="pipeline_failure",
                    message="fixture Knight failure",
                    recoverable=True,
                ),
            ),
        )
    decisions = tuple(
        knight.CriterionAdjudication(
            criterion_id=criterion_id,
            status=_criterion_status(case, index),
            materiality=(
                "central" if _criterion_status(case, index) == "present" else None
            ),
            supporting_evidence_ids=(
                ("criterion_1",) if _criterion_status(case, index) == "present" else ()
            ),
            rationale=f"{case.scenario} fixture Knight decision.",
        )
        for index, criterion_id in enumerate(models.KNIGHT_CRITERION_IDS, start=1)
    )
    return (
        knight.build_analysis(
            analysis_id=f"{case.case_id}-knight-v1",
            story_hash=case.story_hash,
            evidence_set=evidence_set,
            decisions=decisions,
            provenance=provenance,
        ),
    )


def _criterion_status(case: TrialCase, index: int) -> str:
    if case.scenario == "no_novum_control":
        return "absent"
    if case.scenario == "ambiguous_cognitive_validation" and index in {3, 4}:
        return "ambiguous"
    return "present" if index in {1, 2, 3} else "absent"


def _suvin_analyses(
    case: TrialCase,
    evidence_set: evidence.EvidenceSet,
) -> tuple[models.SuvinNovumAnalysis, ...]:
    if case.scenario == "partial_suvin_failure":
        return (
            novum.failed_analysis(
                analysis_id=f"{case.case_id}-suvin-v1",
                story_hash=case.story_hash,
                evidence_set_id=evidence_set.evidence_set_id,
                provenance=_provenance(case, models.SUVIN_RUBRIC_VERSION),
                failure=models.FailureRecord(
                    stage="suvin_novum",
                    kind="malformed_model_output",
                    message="fixture malformed Suvin output",
                    recoverable=True,
                ),
            ),
        )
    candidates = (_candidate(case, "novum-1"),)
    systems: tuple[novum.NovumSystemAdjudication, ...] = ()
    dominant = (
        "novum-1"
        if case.scenario
        not in {
            "no_novum_control",
            "supernatural_contrast",
            "ambiguous_cognitive_validation",
            "incidental_technology",
        }
        else None
    )
    if case.scenario == "multiple_novum_system":
        candidates = (_candidate(case, "novum-1"), _candidate(case, "novum-2"))
        dominant = "novum-1"
        systems = (
            novum.NovumSystemAdjudication(
                system_id="system-1",
                candidate_ids=("novum-1", "novum-2"),
                rationale="Fixture candidates operate as one system.",
            ),
        )
    return (
        novum.build_analysis(
            analysis_id=f"{case.case_id}-suvin-v1",
            story_hash=case.story_hash,
            evidence_set=evidence_set,
            candidates=candidates,
            provenance=_provenance(case, models.SUVIN_RUBRIC_VERSION),
            dominant_novum_id=dominant,
            novum_systems=systems,
        ),
    )


def _candidate(case: TrialCase, candidate_id: str) -> novum.CandidateAdjudication:
    statuses = {
        "no_novum_control": ("absent", "absent", "absent"),
        "supernatural_contrast": ("present", "absent", "present"),
        "ambiguous_cognitive_validation": ("present", "ambiguous", "present"),
        "incidental_technology": ("present", "present", "absent"),
    }.get(case.scenario, ("present", "present", "present"))
    novelty, cognition, hegemony = statuses
    return novum.CandidateAdjudication(
        candidate_id=candidate_id,
        description=f"{case.scenario} fixture candidate {candidate_id}.",
        novelty=_dimension(novelty, "novelty"),
        cognitive_validation=_dimension(cognition, "cognition"),
        narrative_hegemony=_dimension(hegemony, "hegemony"),
        estrangement=novum.EstrangementAdjudication(
            reader_facing_evidence_ids=("reader",),
            character_reaction_evidence_ids=("reaction",),
        ),
        evidence_ids=("novelty", "cognition", "hegemony"),
    )


def _dimension(status: str, evidence_id: str) -> novum.DimensionAdjudication:
    return novum.DimensionAdjudication(
        status=status,
        supporting_evidence_ids=(evidence_id,) if status == "present" else (),
        rationale=f"Fixture {evidence_id} dimension is {status}.",
    )


def _partial_success(case: TrialCase) -> models.PartialSuccessRecord | None:
    if case.scenario == "partial_suvin_failure":
        return models.PartialSuccessRecord(
            completed_stages=("preparation", "evidence", "knight"),
            failed_stages=(
                models.FailureRecord(
                    stage="suvin_novum",
                    kind="malformed_model_output",
                    message="fixture malformed Suvin output",
                    recoverable=True,
                ),
            ),
        )
    if case.scenario == "partial_knight_failure":
        return models.PartialSuccessRecord(
            completed_stages=("preparation", "evidence", "suvin_novum"),
            failed_stages=(
                models.FailureRecord(
                    stage="knight",
                    kind="pipeline_failure",
                    message="fixture Knight failure",
                    recoverable=True,
                ),
            ),
        )
    return None


def _provenance(case: TrialCase, rubric_version: str) -> models.ProvenanceRecord:
    return models.ProvenanceRecord(
        run_id=f"{case.case_id}-{rubric_version}",
        rubric_version=rubric_version,
        code_commit="fixture",
        backend=FIXTURE_BACKEND,
        model=None,
        token_usage={"input": 0, "output": 0},
        estimated_cost_usd=0.0,
        generated_at="2026-08-23T00:00:00Z",
    )


def _summary(
    *,
    status: str,
    manifest: TrialManifest,
    output_root: pathlib.Path,
    plan: dict[str, Any],
    case_results: Iterable[CaseResult],
) -> dict[str, Any]:
    results = tuple(case_results)
    return {
        "version": SUMMARY_VERSION,
        "status": status,
        "backend": manifest.backend,
        "estimated_cost_usd": manifest.estimated_cost_usd,
        "manifest_path": str(manifest.manifest_path),
        "output_root": str(output_root),
        "plan": plan,
        "fixture_coverage": sorted(fixture_coverage(manifest)),
        "cases": [item.to_dict() for item in results],
    }


def _write_summary(output_root: pathlib.Path, summary: dict[str, Any]) -> pathlib.Path:
    output_root.mkdir(parents=True, exist_ok=True)
    path = output_root / "run_summary.json"
    path.write_text(_stable_json(summary), encoding="utf-8")
    return path


def _validate_no_cost_fixture_manifest(manifest: TrialManifest) -> None:
    if manifest.backend != FIXTURE_BACKEND:
        raise ValueError(
            "science-fiction Phase 1F runner only supports fixture backend"
        )
    if manifest.estimated_cost_usd != 0.0:
        raise ValueError(
            "science-fiction Phase 1F runner refuses nonzero cost manifests"
        )


def _resolve_safe_output_root(output_root: pathlib.Path) -> pathlib.Path:
    resolved = pathlib.Path(output_root).resolve()
    if resolved.exists() and not resolved.is_dir():
        raise ValueError("output_root must be a directory")
    checkpoint.resolve_roots(resolved)
    repo_root = paths.find_pyproject_root(__file__).resolve()
    if resolved == repo_root:
        raise ValueError("output_root must not be the LCATS package root")
    return resolved


def _validate_bounds(options: RunnerOptions) -> None:
    if options.concurrency < 1 or options.concurrency > MAX_CONCURRENCY:
        raise ValueError(f"concurrency must be between 1 and {MAX_CONCURRENCY}")
    if options.max_retries < 0 or options.max_retries > MAX_RETRIES:
        raise ValueError(f"max_retries must be between 0 and {MAX_RETRIES}")


def _manifest_fingerprint(manifest: TrialManifest) -> str:
    payload = {
        "backend": manifest.backend,
        "cases": [dataclasses.asdict(case) for case in manifest.cases],
        "estimated_cost_usd": manifest.estimated_cost_usd,
        "version": manifest.version,
    }
    return hashlib.sha256(_stable_json(payload).encode("utf-8")).hexdigest()


def _checkpoint_item_id(case: TrialCase) -> str:
    digest = hashlib.sha256(case.lcats_id.encode("utf-8")).hexdigest()[:12]
    return f"{case.case_id}-{digest}"


def _failure_kind(error: Exception | None) -> str | None:
    if error is None:
        return None
    message = str(error)
    if message == "interrupted_stage":
        return "interrupted_stage"
    if "failed validation" in message:
        return "story_hash_mismatch"
    return type(error).__name__


def _stable_json(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def _required_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the no-cost science-fiction sidecar fixture trial."
    )
    parser.add_argument("--manifest", type=pathlib.Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-root", type=pathlib.Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-retries", type=int, default=0)
    parser.add_argument("--concurrency", type=int, default=1)
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
