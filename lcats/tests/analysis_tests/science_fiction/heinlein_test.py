"""Tests for deterministic Heinlein adjudication helpers and sidecar wiring."""

from __future__ import annotations

import copy
import dataclasses
import unittest

from lcats.analysis.science_fiction import evidence
from lcats.analysis.science_fiction import heinlein
from lcats.analysis.science_fiction import models
from lcats.analysis.science_fiction import pipeline
from lcats.analysis.science_fiction import sidecar
from lcats.analysis.science_fiction.rubric import definitions

CRITERIA = models.HEINLEIN_CRITERION_IDS


def _evidence_set(story_hash: str = "story-hash") -> evidence.EvidenceSet:
    return evidence.EvidenceSet(
        evidence_set_id="evidence-set-1",
        story_hash=story_hash,
        records=tuple(
            evidence.EvidenceRecord(
                evidence_id=evidence_id,
                evidence_type="storyworld_change",
                quote=f"Quote for {evidence_id}.",
                anchor=evidence.EvidenceAnchor(
                    paragraph_ids=("p0001",), start_char=0, end_char=10
                ),
                paraphrase=f"Paraphrase for {evidence_id}.",
                confidence=0.9,
                provenance=(evidence.EvidenceProvenance(source="fixture"),),
            )
            for evidence_id in CRITERIA
        ),
        quarantined=(),
        conflicts=(),
    )


def _provenance() -> models.ProvenanceRecord:
    return models.ProvenanceRecord(
        run_id="run-heinlein",
        rubric_version=models.HEINLEIN_RUBRIC_VERSION,
        generated_at="2026-10-05T00:00:00Z",
    )


def _decisions(**statuses: str) -> tuple[heinlein.CriterionAdjudication, ...]:
    """Build five decisions; unspecified criteria default to present."""

    return tuple(
        heinlein.CriterionAdjudication(
            criterion_id=criterion_id,
            status=statuses.get(criterion_id, "present"),
            supporting_evidence_ids=(
                (criterion_id,)
                if statuses.get(criterion_id, "present") == "present"
                else ()
            ),
            rationale=f"{criterion_id} decision.",
        )
        for criterion_id in reversed(CRITERIA)
    )


def _analysis(**statuses: str) -> models.HeinleinAnalysis:
    return heinlein.build_analysis(
        analysis_id="heinlein-1",
        story_hash="story-hash",
        evidence_set=_evidence_set(),
        decisions=_decisions(**statuses),
        provenance=_provenance(),
    )


class HeinleinAdjudicationTest(unittest.TestCase):
    def test_builds_five_ordered_criteria_without_threshold(self):
        analysis = _analysis()
        data = analysis.to_dict()

        self.assertEqual(CRITERIA, tuple(c.criterion_id for c in analysis.criteria))
        self.assertEqual(5, analysis.interval.total_count)
        self.assertNotIn("threshold", data)
        self.assertNotIn("probability", data)

    def test_verdict_is_a_conjunction_not_a_count(self):
        self.assertEqual("qualifies", _analysis().verdict)
        # Four of five present is still not a qualifying story.
        self.assertEqual("does_not_qualify", _analysis(plausible="absent").verdict)
        self.assertEqual("indeterminate", _analysis(plausible="ambiguous").verdict)
        self.assertEqual("indeterminate", _analysis(human="not_assessable").verdict)
        # Any absent criterion decides the verdict even alongside ambiguity.
        self.assertEqual(
            "does_not_qualify",
            _analysis(plausible="absent", human="ambiguous").verdict,
        )

    def test_interval_counts_present_and_possible(self):
        interval = _analysis(human="ambiguous", plausible="absent").interval

        self.assertEqual(3, interval.definite_count)
        self.assertEqual(4, interval.possible_count)

    def test_rejects_present_dependent_with_absent_prerequisite(self):
        for statuses in (
            {"different": "absent"},  # essential/causal present, nothing new
            {"human": "absent"},  # causal present, but no human problem
        ):
            with self.subTest(statuses=statuses):
                with self.assertRaisesRegex(ValueError, "cannot be present"):
                    _analysis(**statuses)

    def test_absent_prerequisite_is_valid_when_dependents_not_present(self):
        analysis = _analysis(different="absent", essential="absent", causal="absent")

        self.assertEqual("does_not_qualify", analysis.verdict)

    def test_requires_supporting_evidence_for_present(self):
        with self.assertRaisesRegex(ValueError, "supporting evidence"):
            models.HeinleinCriterion(criterion_id="different", status="present")

    def test_requires_five_unique_criteria(self):
        with self.assertRaisesRegex(ValueError, "five unique criteria"):
            heinlein.build_analysis(
                analysis_id="heinlein-1",
                story_hash="story-hash",
                evidence_set=_evidence_set(),
                decisions=_decisions()[:4],
                provenance=_provenance(),
            )

    def test_rejects_wrong_rubric_version(self):
        with self.assertRaisesRegex(ValueError, "heinlein-five-v1"):
            heinlein.build_analysis(
                analysis_id="heinlein-1",
                story_hash="story-hash",
                evidence_set=_evidence_set(),
                decisions=_decisions(),
                provenance=models.ProvenanceRecord(
                    run_id="r", rubric_version=models.KNIGHT_RUBRIC_VERSION
                ),
            )

    def test_rejects_missing_evidence_ids_and_story_hash_mismatch(self):
        bad = tuple(
            heinlein.CriterionAdjudication(
                criterion_id=c,
                status="present" if c == "different" else "absent",
                supporting_evidence_ids=(("missing",) if c == "different" else ()),
            )
            for c in CRITERIA
        )
        with self.assertRaisesRegex(ValueError, "evidence ids do not exist"):
            heinlein.build_analysis(
                analysis_id="h",
                story_hash="story-hash",
                evidence_set=_evidence_set(),
                decisions=bad,
                provenance=_provenance(),
            )
        with self.assertRaisesRegex(ValueError, "story_hash"):
            heinlein.build_analysis(
                analysis_id="h",
                story_hash="other",
                evidence_set=_evidence_set(),
                decisions=_decisions(),
                provenance=_provenance(),
            )

    def test_plans_bounded_follow_up_in_criterion_order(self):
        decisions = _decisions(human="ambiguous", plausible="not_assessable")

        requests = heinlein.plan_follow_up(decisions, max_requests=1)
        self.assertEqual(("human",), tuple(r.criterion_id for r in requests))
        requests = heinlein.plan_follow_up(decisions)
        self.assertEqual(
            ("human", "plausible"), tuple(r.criterion_id for r in requests)
        )

    def test_failed_analysis_is_not_assessable_and_indeterminate(self):
        analysis = heinlein.failed_analysis(
            analysis_id="heinlein-failed",
            story_hash="story-hash",
            evidence_set_id="evidence-set-1",
            provenance=_provenance(),
            failure=models.FailureRecord(
                stage="heinlein", kind="Timeout", message="timed out"
            ),
        )

        self.assertEqual("failed", analysis.status)
        self.assertEqual("indeterminate", analysis.verdict)
        self.assertEqual(0, analysis.interval.possible_count)

    def test_rubric_slots_are_resolved_with_citations(self):
        rubric = definitions.HEINLEIN_FIVE

        self.assertEqual(models.HEINLEIN_RUBRIC_VERSION, rubric.rubric_id)
        self.assertEqual(CRITERIA, tuple(slot.slot_id for slot in rubric.text_slots))
        self.assertTrue(rubric.source_ready)
        for slot in rubric.text_slots:
            self.assertIn("Of Worlds", slot.citation)
        causal = next(s for s in rubric.text_slots if s.slot_id == "causal")
        self.assertIn("indispensably affected", causal.governing_text)


def _inputs(*, with_heinlein: bool, **statuses: str) -> pipeline.SidecarAssemblyInputs:
    return pipeline.SidecarAssemblyInputs(
        lcats_id="bucket/story",
        story_path="bucket/story/story.json",
        story_hash="story-hash",
        evidence_sets=(_evidence_set(),),
        heinlein_analyses=((_analysis(**statuses),) if with_heinlein else ()),
    )


class HeinleinSidecarTest(unittest.TestCase):
    def test_new_field_is_appended_last_to_preserve_positional_order(self):
        for cls, previous_last in (
            (models.ScienceFictionSidecarEnvelope, "schema_version"),
            (pipeline.SidecarAssemblyInputs, "configuration"),
        ):
            with self.subTest(cls=cls.__name__):
                names = [field.name for field in dataclasses.fields(cls)]
                self.assertEqual(
                    ["heinlein_analyses"], names[names.index(previous_last) + 1 :]
                )

    def test_sidecar_round_trips_with_current_pointer(self):
        data = pipeline.assemble_sidecar_data(_inputs(with_heinlein=True))

        self.assertEqual("heinlein-1", data["current"]["heinlein_analysis_id"])
        self.assertEqual("qualifies", data["analyses"]["heinlein"][0]["verdict"])
        self.assertTrue(sidecar.validate_sidecar(data).valid)

    def test_pre_heinlein_sidecar_shape_and_fingerprint_are_unchanged(self):
        inputs = _inputs(with_heinlein=False)
        data = pipeline.assemble_sidecar_data(inputs)
        fingerprint = pipeline.effective_fingerprint(inputs)

        self.assertNotIn("heinlein", data["analyses"])
        self.assertNotIn("heinlein_analysis_id", data["current"])
        self.assertNotIn("heinlein_analyses", fingerprint["inputs"])
        self.assertTrue(sidecar.validate_sidecar(data).valid)

    def test_adding_heinlein_changes_the_fingerprint(self):
        without = pipeline.effective_fingerprint(_inputs(with_heinlein=False))
        with_it = pipeline.effective_fingerprint(_inputs(with_heinlein=True))

        self.assertNotEqual(without["sha256"], with_it["sha256"])

    def _kinds(self, data) -> set[str]:
        return {f.kind for f in sidecar.validate_sidecar(data).findings}

    def test_validator_rejects_verdict_and_interval_mismatch(self):
        data = pipeline.assemble_sidecar_data(_inputs(with_heinlein=True))
        broken = copy.deepcopy(data)
        broken["analyses"]["heinlein"][0]["verdict"] = "does_not_qualify"
        broken["analyses"]["heinlein"][0]["interval"]["definite_count"] = 4

        self.assertEqual(
            {"heinlein_verdict_mismatch", "heinlein_interval_mismatch"},
            self._kinds(broken),
        )

    def test_validator_rejects_dependency_violation_in_loaded_json(self):
        data = pipeline.assemble_sidecar_data(_inputs(with_heinlein=True))
        broken = copy.deepcopy(data)
        for criterion in broken["analyses"]["heinlein"][0]["criteria"]:
            if criterion["criterion_id"] == "different":
                criterion["status"] = "absent"

        self.assertIn("heinlein_dependency_violation", self._kinds(broken))

    def test_validator_rejects_dangling_evidence_and_wrong_rubric(self):
        data = pipeline.assemble_sidecar_data(_inputs(with_heinlein=True))
        broken = copy.deepcopy(data)
        analysis = broken["analyses"]["heinlein"][0]
        analysis["criteria"][0]["supporting_evidence"][0]["evidence_id"] = "nope"
        analysis["provenance"]["rubric_version"] = models.KNIGHT_RUBRIC_VERSION

        self.assertTrue(
            {"missing_reference", "invalid_rubric_version"} <= self._kinds(broken)
        )

    def test_validator_rejects_dangling_current_pointer(self):
        data = pipeline.assemble_sidecar_data(_inputs(with_heinlein=True))
        broken = copy.deepcopy(data)
        broken["current"]["heinlein_analysis_id"] = "missing"

        self.assertIn("missing_reference", self._kinds(broken))

    def test_failed_heinlein_never_becomes_current(self):
        failed = heinlein.failed_analysis(
            analysis_id="heinlein-failed",
            story_hash="story-hash",
            evidence_set_id="evidence-set-1",
            provenance=_provenance(),
            failure=models.FailureRecord(
                stage="heinlein", kind="Timeout", message="timed out"
            ),
        )
        inputs = pipeline.SidecarAssemblyInputs(
            lcats_id="bucket/story",
            story_path="bucket/story/story.json",
            story_hash="story-hash",
            evidence_sets=(_evidence_set(),),
            heinlein_analyses=(failed,),
        )

        data = pipeline.assemble_sidecar_data(inputs)

        self.assertNotIn("heinlein_analysis_id", data["current"])

    def test_heinlein_is_accepted_as_partial_success_stage(self):
        record = models.PartialSuccessRecord(
            completed_stages=("evidence", "knight"),
            failed_stages=(
                models.FailureRecord(
                    stage="heinlein", kind="Timeout", message="timed out"
                ),
            ),
        )
        inputs = _inputs(with_heinlein=False)
        data = pipeline.assemble_sidecar_data(
            pipeline.SidecarAssemblyInputs(
                lcats_id=inputs.lcats_id,
                story_path=inputs.story_path,
                story_hash=inputs.story_hash,
                evidence_sets=inputs.evidence_sets,
                partial_success=record,
            )
        )

        self.assertTrue(sidecar.validate_sidecar(data).valid)


if __name__ == "__main__":
    unittest.main()
