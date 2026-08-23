"""Tests for science-fiction sidecar validation and checkpointed assembly."""

from __future__ import annotations

import json
import pathlib
import tempfile
import unittest
from dataclasses import replace
from unittest.mock import patch

from lcats.analysis.science_fiction import evidence
from lcats.analysis.science_fiction import knight
from lcats.analysis.science_fiction import models
from lcats.analysis.science_fiction import novum
from lcats.analysis.science_fiction import pipeline
from lcats.analysis.science_fiction import sidecar
from lcats.utils import checkpoint


def _evidence_record(evidence_id: str) -> evidence.EvidenceRecord:
    return evidence.EvidenceRecord(
        evidence_id=evidence_id,
        evidence_type="storyworld_change",
        quote=f"Quote for {evidence_id}.",
        anchor=evidence.EvidenceAnchor(
            paragraph_ids=("p0001",),
            start_char=0,
            end_char=10,
        ),
        paraphrase=f"Paraphrase for {evidence_id}.",
        confidence=0.9,
        provenance=(evidence.EvidenceProvenance(source="fixture"),),
    )


def _evidence_set(story_hash: str = "story-hash") -> evidence.EvidenceSet:
    return evidence.EvidenceSet(
        evidence_set_id="evidence-set-1",
        story_hash=story_hash,
        records=tuple(
            _evidence_record(evidence_id)
            for evidence_id in (
                "criterion_1",
                "novelty",
                "cognition",
                "hegemony",
                "reader",
            )
        ),
        quarantined=(),
        conflicts=(),
    )


def _provenance(rubric_version: str) -> models.ProvenanceRecord:
    return models.ProvenanceRecord(
        run_id=f"run-{rubric_version}",
        rubric_version=rubric_version,
        code_commit="abc1234",
        generated_at="2026-08-23T00:00:00Z",
    )


def _knight_analysis(
    evidence_set: evidence.EvidenceSet,
    *,
    analysis_id: str = "knight-1",
) -> models.KnightAnalysis:
    decisions = tuple(
        knight.CriterionAdjudication(
            criterion_id=criterion_id,
            status="present" if criterion_id == "criterion_1" else "absent",
            materiality="central" if criterion_id == "criterion_1" else None,
            supporting_evidence_ids=(
                ("criterion_1",) if criterion_id == "criterion_1" else ()
            ),
        )
        for criterion_id in models.KNIGHT_CRITERION_IDS
    )
    return knight.build_analysis(
        analysis_id=analysis_id,
        story_hash=evidence_set.story_hash,
        evidence_set=evidence_set,
        decisions=decisions,
        provenance=_provenance(models.KNIGHT_RUBRIC_VERSION),
    )


def _suvin_analysis(
    evidence_set: evidence.EvidenceSet,
    *,
    analysis_id: str = "suvin-1",
) -> models.SuvinNovumAnalysis:
    return novum.build_analysis(
        analysis_id=analysis_id,
        story_hash=evidence_set.story_hash,
        evidence_set=evidence_set,
        candidates=(
            novum.CandidateAdjudication(
                candidate_id="novum-1",
                description="A validated novum governs the story.",
                novelty=novum.DimensionAdjudication(
                    status="present",
                    supporting_evidence_ids=("novelty",),
                ),
                cognitive_validation=novum.DimensionAdjudication(
                    status="present",
                    supporting_evidence_ids=("cognition",),
                ),
                narrative_hegemony=novum.DimensionAdjudication(
                    status="present",
                    supporting_evidence_ids=("hegemony",),
                ),
                estrangement=novum.EstrangementAdjudication(
                    reader_facing_evidence_ids=("reader",)
                ),
            ),
        ),
        provenance=_provenance(models.SUVIN_RUBRIC_VERSION),
        dominant_novum_id="novum-1",
    )


def _inputs(
    *,
    partial_success: models.PartialSuccessRecord | None = None,
) -> pipeline.SidecarAssemblyInputs:
    evidence_set = _evidence_set()
    return pipeline.SidecarAssemblyInputs(
        lcats_id="collection/story",
        story_path="collection/story/story.json",
        story_hash=evidence_set.story_hash,
        evidence_sets=(evidence_set,),
        knight_analyses=(_knight_analysis(evidence_set),),
        suvin_novum_analyses=(_suvin_analysis(evidence_set),),
        partial_success=partial_success,
        configuration={"chunk_config": "fixture"},
    )


class ScienceFictionSidecarValidationTest(unittest.TestCase):
    def test_valid_assembled_sidecar_passes_loaded_validation(self):
        data = pipeline.assemble_sidecar_data(_inputs())

        result = sidecar.validate_sidecar(data)

        self.assertTrue(result.valid)
        self.assertEqual("evidence-set-1", data["current"]["evidence_set_id"])
        self.assertEqual("knight-1", data["current"]["knight_analysis_id"])
        self.assertEqual("suvin-1", data["current"]["suvin_novum_analysis_id"])

    def test_loaded_validation_reports_invalid_references_and_stale_hashes(self):
        data = pipeline.assemble_sidecar_data(_inputs())
        data["story_hash"] = "new-story-hash"
        data["current"]["knight_analysis_id"] = "missing-knight"
        data["analyses"]["suvin_novum"][0]["candidates"][0]["novelty"][
            "supporting_evidence"
        ][0]["evidence_id"] = "missing-evidence"

        result = sidecar.validate_sidecar(data)
        finding_kinds = {finding.kind for finding in result.findings}

        self.assertFalse(result.valid)
        self.assertIn("story_hash_mismatch", finding_kinds)
        self.assertIn("missing_reference", finding_kinds)

    def test_loaded_validation_quarantines_malformed_reference_shape(self):
        data = pipeline.assemble_sidecar_data(_inputs())
        data["analyses"]["knight"][0]["criteria"][0]["supporting_evidence"][0][
            "evidence_set_id"
        ] = None

        result = sidecar.validate_sidecar(data)
        finding_kinds = {finding.kind for finding in result.findings}

        self.assertFalse(result.valid)
        self.assertIn("wrong_type", finding_kinds)

    def test_loaded_validation_rejects_invalid_current_pointer(self):
        evidence_set = _evidence_set()
        failed = knight.failed_analysis(
            analysis_id="knight-failed",
            story_hash=evidence_set.story_hash,
            evidence_set_id=evidence_set.evidence_set_id,
            provenance=_provenance(models.KNIGHT_RUBRIC_VERSION),
            failure=models.FailureRecord(
                stage="knight",
                kind="pipeline_failure",
                message="fixture failure",
            ),
        )
        inputs = replace(
            _inputs(),
            knight_analyses=(failed,),
            current=models.CurrentPointers(
                evidence_set_id="evidence-set-1",
                knight_analysis_id="knight-failed",
            ),
        )
        data = models.ScienceFictionSidecarEnvelope(
            lcats_id=inputs.lcats_id,
            story_path=inputs.story_path,
            story_hash=inputs.story_hash,
            evidence_sets=inputs.evidence_sets,
            knight_analyses=inputs.knight_analyses,
            current=inputs.current or models.CurrentPointers(),
        ).to_dict()

        result = sidecar.validate_sidecar(data)
        finding_kinds = {finding.kind for finding in result.findings}

        self.assertFalse(result.valid)
        self.assertIn("incomplete_current_record", finding_kinds)
        self.assertIn("failed_current_record", finding_kinds)

    def test_partial_success_record_can_publish_one_completed_analysis(self):
        evidence_set = _evidence_set()
        failure = models.FailureRecord(
            stage="suvin_novum",
            kind="pipeline_failure",
            message="malformed model output",
            recoverable=True,
        )
        inputs = pipeline.SidecarAssemblyInputs(
            lcats_id="collection/story",
            story_path="collection/story/story.json",
            story_hash=evidence_set.story_hash,
            evidence_sets=(evidence_set,),
            knight_analyses=(_knight_analysis(evidence_set),),
            partial_success=models.PartialSuccessRecord(
                completed_stages=("evidence", "knight"),
                failed_stages=(failure,),
            ),
        )

        data = pipeline.assemble_sidecar_data(inputs)
        result = sidecar.validate_sidecar(data)

        self.assertTrue(result.valid)
        self.assertEqual("knight-1", data["current"]["knight_analysis_id"])
        self.assertIsNone(data["current"]["suvin_novum_analysis_id"])
        self.assertEqual(
            "suvin_novum", data["partial_success"]["failed_stages"][0]["stage"]
        )

    def test_rendered_json_is_byte_stable(self):
        data = pipeline.assemble_sidecar_data(_inputs())

        self.assertEqual(
            sidecar.render_sidecar_json(data),
            sidecar.render_sidecar_json(data),
        )


class ScienceFictionPipelineCheckpointTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.working_root = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_checkpointed_assembly_reuses_matching_success(self):
        first = pipeline.run_checkpointed_assembly(
            working_root=self.working_root,
            item_id="story_a",
            inputs=_inputs(),
            allow_protected_root=True,
        )
        second = pipeline.run_checkpointed_assembly(
            working_root=self.working_root,
            item_id="story_a",
            inputs=_inputs(),
            allow_protected_root=True,
        )

        self.assertFalse(first.reused)
        self.assertTrue(second.reused)
        self.assertEqual(first.data, second.data)

    def test_checkpointed_stage_rematerializes_stale_or_failed_checkpoint(self):
        calls = {"count": 0}

        def materialize() -> dict[str, int]:
            calls["count"] += 1
            return {"count": calls["count"]}

        first = pipeline.run_checkpointed_stage(
            working_root=self.working_root,
            item_id="story_a",
            stage="fixture-stage",
            fingerprint={"version": 1},
            materialize=materialize,
            allow_protected_root=True,
        )
        second = pipeline.run_checkpointed_stage(
            working_root=self.working_root,
            item_id="story_a",
            stage="fixture-stage",
            fingerprint={"version": 2},
            materialize=materialize,
            allow_protected_root=True,
        )
        checkpoint.write_checkpoint(
            self.working_root,
            "story_a",
            "failed-stage",
            outcome="failure",
            fingerprint={"version": 1},
            data={"message": "old failure"},
        )
        third = pipeline.run_checkpointed_stage(
            working_root=self.working_root,
            item_id="story_a",
            stage="failed-stage",
            fingerprint={"version": 1},
            materialize=materialize,
            allow_protected_root=True,
        )

        self.assertFalse(first.reused)
        self.assertFalse(second.reused)
        self.assertFalse(third.reused)
        self.assertEqual({"count": 3}, third.data)

    def test_checkpointed_stage_records_interrupted_failure(self):
        with self.assertRaisesRegex(RuntimeError, "boom"):
            pipeline.run_checkpointed_stage(
                working_root=self.working_root,
                item_id="story_a",
                stage="fixture-stage",
                fingerprint={"version": 1},
                materialize=lambda: (_ for _ in ()).throw(RuntimeError("boom")),
                allow_protected_root=True,
            )

        result = checkpoint.read_checkpoint(
            self.working_root,
            "story_a",
            "fixture-stage",
            fingerprint={"version": 1},
        )

        self.assertFalse(result.done)
        self.assertEqual("failure", result.outcome)
        self.assertEqual("RuntimeError", result.data["kind"])

    def test_publish_sidecar_writes_valid_atomic_science_fiction_json(self):
        data = pipeline.assemble_sidecar_data(_inputs())

        path = pipeline.publish_sidecar(
            output_root=self.working_root,
            item_id="story_a",
            data=data,
            allow_protected_root=True,
        )

        self.assertEqual(path.name, sidecar.SIDECAR_FILENAME)
        loaded = json.loads(path.read_text(encoding="utf-8"))
        self.assertTrue(sidecar.validate_sidecar(loaded).valid)

    def test_publish_interruption_preserves_prior_sidecar(self):
        data = pipeline.assemble_sidecar_data(_inputs())
        path = pipeline.publish_sidecar(
            output_root=self.working_root,
            item_id="story_a",
            data=data,
            allow_protected_root=True,
        )
        original = path.read_text(encoding="utf-8")

        with patch(
            "lcats.analysis.science_fiction.sidecar.os.replace",
            side_effect=KeyboardInterrupt,
        ):
            with self.assertRaises(KeyboardInterrupt):
                pipeline.publish_sidecar(
                    output_root=self.working_root,
                    item_id="story_a",
                    data=data,
                    allow_protected_root=True,
                )

        self.assertEqual(original, path.read_text(encoding="utf-8"))
        leftovers = [item for item in path.parent.iterdir() if item.name != path.name]
        self.assertEqual([], leftovers)


if __name__ == "__main__":
    unittest.main()
