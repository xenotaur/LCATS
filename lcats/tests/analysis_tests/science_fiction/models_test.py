"""Tests for science-fiction sidecar contract records."""

import unittest
from types import MappingProxyType

from lcats.analysis.science_fiction import evidence
from lcats.analysis.science_fiction import models
from lcats.analysis.science_fiction.rubric import definitions


def _reference(evidence_id: str = "ev-1") -> models.EvidenceReference:
    return models.EvidenceReference(
        evidence_set_id="evidence-set-1",
        evidence_id=evidence_id,
    )


def _evidence_record(evidence_id: str = "ev-1") -> evidence.EvidenceRecord:
    return evidence.EvidenceRecord(
        evidence_id=evidence_id,
        evidence_type="storyworld_change",
        quote="A changed condition.",
        anchor=evidence.EvidenceAnchor(
            paragraph_ids=("p0001",),
            start_char=0,
            end_char=20,
        ),
        paraphrase="A changed condition is introduced.",
        confidence=0.9,
        provenance=(evidence.EvidenceProvenance(source="fixture"),),
    )


def _evidence_set(
    evidence_set_id: str = "evidence-set-1",
    story_hash: str = "story-hash",
    evidence_ids: tuple[str, ...] = ("ev-1",),
) -> evidence.EvidenceSet:
    return evidence.EvidenceSet(
        evidence_set_id=evidence_set_id,
        story_hash=story_hash,
        records=tuple(_evidence_record(evidence_id) for evidence_id in evidence_ids),
        quarantined=(),
        conflicts=(),
    )


def _provenance(rubric_version: str) -> models.ProvenanceRecord:
    return models.ProvenanceRecord(
        run_id=f"run-{rubric_version}",
        rubric_version=rubric_version,
        code_commit="abc1234",
    )


def _criterion(criterion_id: str, status: str) -> models.KnightCriterion:
    support = (_reference(criterion_id),) if status == "present" else ()
    materiality = "central" if status in {"present", "ambiguous"} else None
    return models.KnightCriterion(
        criterion_id=criterion_id,
        status=status,
        materiality=materiality,
        supporting_evidence=support,
        rationale=f"{criterion_id} is {status}",
    )


def _dimension(status: str, evidence_id: str) -> models.NovumDimensionDecision:
    support = (_reference(evidence_id),) if status == "present" else ()
    return models.NovumDimensionDecision(
        status=status,
        supporting_evidence=support,
        rationale=f"{evidence_id} is {status}",
    )


def _qualified_candidate(candidate_id: str = "novum-1") -> models.NovumCandidate:
    return models.NovumCandidate(
        candidate_id=candidate_id,
        description="A new storyworld condition governs the plot.",
        novelty=_dimension("present", f"{candidate_id}-n"),
        cognitive_validation=_dimension("present", f"{candidate_id}-c"),
        narrative_hegemony=_dimension("present", f"{candidate_id}-h"),
        estrangement=models.EstrangementProfile(
            reader_facing_evidence=(_reference(f"{candidate_id}-reader"),)
        ),
    )


class ScienceFictionModelsTest(unittest.TestCase):
    def test_knight_interval_counts_present_and_ambiguous_deterministically(self):
        statuses = (
            "present",
            "present",
            "present",
            "present",
            "ambiguous",
            "absent",
            "not_assessable",
        )
        criteria = tuple(
            _criterion(criterion_id, status)
            for criterion_id, status in zip(models.KNIGHT_CRITERION_IDS, statuses)
        )

        analysis = models.KnightAnalysis(
            analysis_id="knight-1",
            story_hash="story-hash",
            evidence_set_id="evidence-set-1",
            criteria=criteria,
            provenance=_provenance(models.KNIGHT_RUBRIC_VERSION),
        )

        self.assertEqual(4, analysis.interval.definite_count)
        self.assertEqual(5, analysis.interval.possible_count)
        self.assertNotIn("probability", analysis.to_dict())
        self.assertNotIn("threshold", analysis.to_dict())

    def test_knight_requires_seven_unique_criteria(self):
        criteria = tuple(
            _criterion(criterion_id, "absent")
            for criterion_id in models.KNIGHT_CRITERION_IDS[:-1]
        )

        with self.assertRaisesRegex(ValueError, "seven unique criteria"):
            models.KnightAnalysis(
                analysis_id="knight-1",
                story_hash="story-hash",
                evidence_set_id="evidence-set-1",
                criteria=criteria,
                provenance=_provenance(models.KNIGHT_RUBRIC_VERSION),
            )

    def test_present_knight_criterion_requires_supporting_evidence(self):
        with self.assertRaisesRegex(ValueError, "supporting evidence"):
            models.KnightCriterion(
                criterion_id=models.KNIGHT_CRITERION_IDS[0],
                status="present",
            )

    def test_suvin_qualification_is_conjunctive(self):
        qualified = _qualified_candidate()
        missing_hegemony = models.NovumCandidate(
            candidate_id="novum-2",
            description="Technology appears but does not govern the plot.",
            novelty=_dimension("present", "novum-2-n"),
            cognitive_validation=_dimension("present", "novum-2-c"),
            narrative_hegemony=_dimension("absent", "novum-2-h"),
        )

        self.assertTrue(qualified.qualified_novum)
        self.assertFalse(missing_hegemony.qualified_novum)
        self.assertFalse(missing_hegemony.to_dict()["qualified_novum"])

    def test_estrangement_is_separate_from_novum_qualification(self):
        candidate = models.NovumCandidate(
            candidate_id="novum-no-reaction",
            description="A validated novum without character surprise.",
            novelty=_dimension("present", "novum-n"),
            cognitive_validation=_dimension("present", "novum-c"),
            narrative_hegemony=_dimension("present", "novum-h"),
            estrangement=models.EstrangementProfile(
                reader_facing_evidence=(_reference("reader-facing"),)
            ),
        )

        self.assertTrue(candidate.qualified_novum)
        self.assertEqual((), candidate.estrangement.character_reaction_evidence)
        self.assertIn("estrangement", candidate.to_dict())

    def test_suvin_analysis_requires_dominant_novum_to_be_qualified(self):
        unqualified = models.NovumCandidate(
            candidate_id="incidental-tech",
            description="Incidental technology.",
            novelty=_dimension("present", "incidental-n"),
            cognitive_validation=_dimension("present", "incidental-c"),
            narrative_hegemony=_dimension("absent", "incidental-h"),
        )

        with self.assertRaisesRegex(ValueError, "qualified candidate"):
            models.SuvinNovumAnalysis(
                analysis_id="suvin-1",
                story_hash="story-hash",
                evidence_set_id="evidence-set-1",
                candidates=(unqualified,),
                provenance=_provenance(models.SUVIN_RUBRIC_VERSION),
                dominant_novum_id="incidental-tech",
            )

    def test_suvin_analysis_allows_multiple_qualified_novum_system(self):
        candidate_a = _qualified_candidate("novum-a")
        candidate_b = _qualified_candidate("novum-b")

        analysis = models.SuvinNovumAnalysis(
            analysis_id="suvin-1",
            story_hash="story-hash",
            evidence_set_id="evidence-set-1",
            candidates=(candidate_a, candidate_b),
            provenance=_provenance(models.SUVIN_RUBRIC_VERSION),
            dominant_novum_id="novum-a",
            novum_systems=(models.NovumSystem("system-1", ("novum-a", "novum-b")),),
        )

        self.assertEqual("novum-a", analysis.to_dict()["dominant_novum_id"])
        self.assertEqual(1, len(analysis.to_dict()["novum_systems"]))

    def test_current_pointer_validation_reports_missing_references(self):
        envelope = models.ScienceFictionSidecarEnvelope(
            lcats_id="collection/story",
            story_path="collection/story/story.json",
            story_hash="story-hash",
            evidence_sets=(_evidence_set(),),
            current=models.CurrentPointers(
                evidence_set_id="missing",
                knight_analysis_id="also-missing",
            ),
        )

        result = envelope.validate_current_pointers()

        self.assertFalse(result.valid)
        self.assertEqual(2, len(result.findings))
        self.assertEqual("missing_reference", result.findings[0].kind)

    def test_current_pointer_validation_rejects_invalid_active_analysis(self):
        criteria = tuple(
            _criterion(criterion_id, "absent")
            for criterion_id in models.KNIGHT_CRITERION_IDS
        )
        failure = models.FailureRecord(
            stage="knight",
            kind="pipeline_failure",
            message="Review needed.",
        )
        knight_analysis = models.KnightAnalysis(
            analysis_id="knight-current",
            story_hash="different-story-hash",
            evidence_set_id="old-evidence-set",
            criteria=criteria,
            provenance=_provenance(models.KNIGHT_RUBRIC_VERSION),
            status="partial",
            failures=(failure,),
        )
        envelope = models.ScienceFictionSidecarEnvelope(
            lcats_id="collection/story",
            story_path="collection/story/story.json",
            story_hash="story-hash",
            evidence_sets=(_evidence_set(),),
            knight_analyses=(knight_analysis,),
            current=models.CurrentPointers(
                evidence_set_id="evidence-set-1",
                knight_analysis_id="knight-current",
            ),
        )

        result = envelope.validate_current_pointers()
        finding_kinds = {finding.kind for finding in result.findings}

        self.assertFalse(result.valid)
        self.assertIn("incomplete_current_record", finding_kinds)
        self.assertIn("failed_current_record", finding_kinds)
        self.assertIn("story_hash_mismatch", finding_kinds)
        self.assertIn("evidence_set_mismatch", finding_kinds)

    def test_sidecar_serializes_evidence_sets_and_story_hash(self):
        envelope = models.ScienceFictionSidecarEnvelope(
            lcats_id="collection/story",
            story_path="collection/story/story.json",
            story_hash="story-hash",
            evidence_sets=(_evidence_set(evidence_ids=("ev-1", "ev-2")),),
        )

        data = envelope.to_dict()

        self.assertEqual("story-hash", data["story_hash"])
        self.assertNotIn("story_sha256", data)
        self.assertNotIn("evidence_set_ids", data)
        self.assertEqual("evidence-set-1", data["evidence_sets"][0]["evidence_set_id"])
        self.assertEqual(2, len(data["evidence_sets"][0]["records"]))

    def test_sidecar_serialization_recomputes_stale_validation(self):
        envelope = models.ScienceFictionSidecarEnvelope(
            lcats_id="collection/story",
            story_path="collection/story/story.json",
            story_hash="story-hash",
            current=models.CurrentPointers(evidence_set_id="missing"),
        )

        validation = envelope.to_dict()["validation"]

        self.assertFalse(validation["valid"])
        self.assertEqual("missing_reference", validation["findings"][0]["kind"])

    def test_sidecar_validation_rejects_dangling_evidence_reference(self):
        criteria = tuple(
            _criterion(criterion_id, "absent")
            for criterion_id in models.KNIGHT_CRITERION_IDS
        )
        criteria = (
            models.KnightCriterion(
                criterion_id=models.KNIGHT_CRITERION_IDS[0],
                status="present",
                materiality="central",
                supporting_evidence=(_reference("missing-evidence"),),
            ),
        ) + criteria[1:]
        analysis = models.KnightAnalysis(
            analysis_id="knight-1",
            story_hash="story-hash",
            evidence_set_id="evidence-set-1",
            criteria=criteria,
            provenance=_provenance(models.KNIGHT_RUBRIC_VERSION),
        )
        envelope = models.ScienceFictionSidecarEnvelope(
            lcats_id="collection/story",
            story_path="collection/story/story.json",
            story_hash="story-hash",
            evidence_sets=(_evidence_set(evidence_ids=("ev-1",)),),
            knight_analyses=(analysis,),
        )

        result = envelope.validate()

        self.assertFalse(result.valid)
        self.assertIn(
            "missing_reference", {finding.kind for finding in result.findings}
        )

    def test_sidecar_validation_checks_non_current_analysis_integrity(self):
        criteria = tuple(
            _criterion(criterion_id, "absent")
            for criterion_id in models.KNIGHT_CRITERION_IDS
        )
        stale_story_analysis = models.KnightAnalysis(
            analysis_id="stale-story",
            story_hash="different-story-hash",
            evidence_set_id="evidence-set-1",
            criteria=criteria,
            provenance=_provenance(models.KNIGHT_RUBRIC_VERSION),
        )
        missing_evidence_set_analysis = models.KnightAnalysis(
            analysis_id="missing-evidence-set",
            story_hash="story-hash",
            evidence_set_id="missing-evidence-set",
            criteria=criteria,
            provenance=_provenance(models.KNIGHT_RUBRIC_VERSION),
        )
        envelope = models.ScienceFictionSidecarEnvelope(
            lcats_id="collection/story",
            story_path="collection/story/story.json",
            story_hash="story-hash",
            evidence_sets=(_evidence_set(),),
            knight_analyses=(stale_story_analysis, missing_evidence_set_analysis),
        )

        validation = envelope.to_dict()["validation"]
        finding_kinds = {finding["kind"] for finding in validation["findings"]}

        self.assertFalse(validation["valid"])
        self.assertIn("story_hash_mismatch", finding_kinds)
        self.assertIn("missing_reference", finding_kinds)

    def test_sidecar_validation_rejects_cross_set_evidence_references(self):
        criteria = (
            models.KnightCriterion(
                criterion_id=models.KNIGHT_CRITERION_IDS[0],
                status="present",
                materiality="central",
                supporting_evidence=(
                    models.EvidenceReference(
                        evidence_set_id="evidence-set-2",
                        evidence_id="ev-2",
                    ),
                ),
            ),
        ) + tuple(
            _criterion(criterion_id, "absent")
            for criterion_id in models.KNIGHT_CRITERION_IDS[1:]
        )
        analysis = models.KnightAnalysis(
            analysis_id="knight-1",
            story_hash="story-hash",
            evidence_set_id="evidence-set-1",
            criteria=criteria,
            provenance=_provenance(models.KNIGHT_RUBRIC_VERSION),
        )
        envelope = models.ScienceFictionSidecarEnvelope(
            lcats_id="collection/story",
            story_path="collection/story/story.json",
            story_hash="story-hash",
            evidence_sets=(
                _evidence_set(evidence_set_id="evidence-set-1"),
                _evidence_set(evidence_set_id="evidence-set-2", evidence_ids=("ev-2",)),
            ),
            knight_analyses=(analysis,),
        )

        validation = envelope.to_dict()["validation"]
        finding_kinds = {finding["kind"] for finding in validation["findings"]}

        self.assertFalse(validation["valid"])
        self.assertIn("evidence_set_mismatch", finding_kinds)

    def test_current_pointer_validation_rejects_duplicate_analysis_ids(self):
        criteria = tuple(
            _criterion(criterion_id, "absent")
            for criterion_id in models.KNIGHT_CRITERION_IDS
        )
        analysis_a = models.KnightAnalysis(
            analysis_id="knight-current",
            story_hash="story-hash",
            evidence_set_id="evidence-set-1",
            criteria=criteria,
            provenance=_provenance(models.KNIGHT_RUBRIC_VERSION),
        )
        analysis_b = models.KnightAnalysis(
            analysis_id="knight-current",
            story_hash="story-hash",
            evidence_set_id="evidence-set-1",
            criteria=criteria,
            provenance=_provenance(models.KNIGHT_RUBRIC_VERSION),
        )
        envelope = models.ScienceFictionSidecarEnvelope(
            lcats_id="collection/story",
            story_path="collection/story/story.json",
            story_hash="story-hash",
            evidence_sets=(_evidence_set(),),
            knight_analyses=(analysis_a, analysis_b),
            current=models.CurrentPointers(
                evidence_set_id="evidence-set-1",
                knight_analysis_id="knight-current",
            ),
        )

        result = envelope.validate_current_pointers()

        self.assertFalse(result.valid)
        self.assertIn(
            "duplicate_reference", {finding.kind for finding in result.findings}
        )

    def test_provenance_mappings_are_immutable_after_construction(self):
        parameters = {
            "temperature": 0,
            "nested": {"top_p": 0.9},
            "stop_sequences": ["END"],
        }
        token_usage = {"prompt": 10}
        provenance = models.ProvenanceRecord(
            run_id="run",
            rubric_version=models.KNIGHT_RUBRIC_VERSION,
            generation_parameters=parameters,
            token_usage=token_usage,
        )
        parameters["temperature"] = 1
        parameters["nested"]["top_p"] = 0.1
        parameters["stop_sequences"].append("MORE")
        token_usage["prompt"] = 20

        self.assertIsInstance(provenance.generation_parameters, MappingProxyType)
        self.assertEqual(0, provenance.generation_parameters["temperature"])
        self.assertEqual(0.9, provenance.generation_parameters["nested"]["top_p"])
        self.assertEqual(("END",), provenance.generation_parameters["stop_sequences"])
        self.assertEqual(10, provenance.token_usage["prompt"])
        with self.assertRaises(TypeError):
            provenance.generation_parameters["nested"]["top_p"] = 0.2
        with self.assertRaises(TypeError):
            provenance.token_usage["prompt"] = 30
        self.assertEqual(
            {
                "temperature": 0,
                "nested": {"top_p": 0.9},
                "stop_sequences": ["END"],
            },
            provenance.to_dict()["generation_parameters"],
        )

    def test_partial_success_keeps_stage_failure_separate(self):
        failure = models.FailureRecord(
            stage="suvin_novum",
            kind="pipeline_failure",
            message="Structured output was malformed.",
            recoverable=True,
        )
        partial = models.PartialSuccessRecord(
            completed_stages=("evidence", "knight"),
            failed_stages=(failure,),
        )

        self.assertEqual(("evidence", "knight"), partial.completed_stages)
        self.assertEqual("suvin_novum", partial.failed_stages[0].stage)

    def test_rubric_definitions_keep_primary_source_text_pending(self):
        self.assertFalse(definitions.KNIGHT_SEVEN.source_ready)
        self.assertFalse(definitions.SUVIN_NOVUM.source_ready)
        self.assertEqual(7, len(definitions.KNIGHT_SEVEN.text_slots))
        self.assertEqual(3, len(definitions.SUVIN_NOVUM.text_slots))
        self.assertTrue(
            all(
                slot.governing_text is None
                for slot in definitions.KNIGHT_SEVEN.text_slots
            )
        )

    def test_pending_rubric_slot_rejects_uncited_governing_text(self):
        with self.assertRaisesRegex(ValueError, "pending rubric slots"):
            definitions.RubricTextSlot(
                slot_id="criterion_1",
                label="Criterion 1",
                governing_text="Unapproved wording",
            )

    def test_source_ready_requires_rubric_source_status_to_be_resolved(self):
        rubric = definitions.RubricDefinition(
            rubric_id="rubric",
            source_status=definitions.SOURCE_STATUS_PENDING,
            text_slots=(
                definitions.RubricTextSlot(
                    slot_id="slot",
                    label="Slot",
                    source_status="resolved",
                    governing_text="Approved text.",
                    citation="Approved source, p. 1.",
                ),
            ),
            source_note="Source note.",
        )

        self.assertFalse(rubric.source_ready)


if __name__ == "__main__":
    unittest.main()
