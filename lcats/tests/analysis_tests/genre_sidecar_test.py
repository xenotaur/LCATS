"""Unit tests for lcats.analysis.corpus.genre_sidecar."""

import copy
import unittest

from lcats.analysis.corpus import genre_sidecar


def _metadata_assessment() -> dict:
    return {
        "assessment_id": "metadata_rules__2026-08-12T01:22:00Z",
        "label": "gutenberg_metadata_rules",
        "generated_at": "2026-08-12T01:22:00Z",
        "scope": "gutenberg_volume",
        "method": {
            "name": "lcats.utils.genre.GENRE_RULES",
            "version": "pilot-v1",
        },
        "provenance": {
            "pipeline": "experiments/05_metadata_genre_prefilter",
            "pipeline_version": "wi-genre-0002",
            "gutenberg_id": 1661,
        },
        "evidence": {
            "raw_subjects": ["Detective and mystery stories"],
            "raw_rule_matches": [{"label": "Mystery", "patterns": ["mystery"]}],
        },
        "result": {
            "target_candidates": ["mystery"],
            "primary_genre": "mystery",
            "confidence": None,
            "verdict": "candidate",
        },
    }


def _model_assessment(run_id: str = "run-001") -> dict:
    return {
        "assessment_id": f"model__gpt-oss-20b__{run_id}__2026-08-12T01:35:00Z",
        "label": "model_detect",
        "run_id": run_id,
        "generated_at": "2026-08-12T01:35:00Z",
        "scope": "story",
        "method": {
            "name": "assess_story_detect",
            "version": "genre-detect-v1",
        },
        "provenance": {
            "backend": "ollama",
            "model": "gpt-oss:20b",
            "api": "openai-compatible",
            "run_id": run_id,
        },
        "evidence": {
            "summary": "A detective investigation centered on a coded clue.",
            "issues": [],
        },
        "result": {
            "primary_genre": "mystery",
            "confidence": 0.93,
            "verdict": "include",
        },
    }


def _human_assessment() -> dict:
    return {
        "assessment_id": "human__reviewer-a__2026-08-12T02:10:00Z",
        "label": "human_review",
        "generated_at": "2026-08-12T02:10:00Z",
        "scope": "story",
        "method": {
            "name": "human_review",
            "version": "v1",
        },
        "provenance": {
            "reviewer": "reviewer-a",
            "interface": "manual",
        },
        "evidence": {
            "notes": "Primary plot mechanics are mystery, not adventure.",
        },
        "result": {
            "primary_genre": "mystery",
            "confidence": None,
            "verdict": "confirmed",
        },
    }


def _sidecar(*assessments: dict, current_adjudication=None) -> dict:
    return {
        "schema_version": genre_sidecar.SCHEMA_VERSION,
        "lcats_id": "corpora/sherlock/five_orange_pips",
        "story_path": "corpora/sherlock/five_orange_pips/story.json",
        "assessments": list(assessments),
        "current_adjudication": current_adjudication,
    }


def _finding_kinds(result: genre_sidecar.ValidationResult) -> set[str]:
    return {finding.kind for finding in result.findings}


def _findings_for_path(
    result: genre_sidecar.ValidationResult, path: str
) -> list[genre_sidecar.ValidationFinding]:
    return [finding for finding in result.findings if finding.path == path]


class GenreSidecarValidationTest(unittest.TestCase):
    def test_valid_metadata_assessment_sidecar(self):
        result = genre_sidecar.validate_sidecar(_sidecar(_metadata_assessment()))

        self.assertTrue(result.valid)
        self.assertEqual((), result.findings)

    def test_valid_future_metadata_assessment_label(self):
        assessment = _metadata_assessment()
        assessment["label"] = "metadata_library_catalog"

        result = genre_sidecar.validate_sidecar(_sidecar(assessment))

        self.assertTrue(result.valid)

    def test_valid_model_assessment_with_run_identity(self):
        result = genre_sidecar.validate_sidecar(_sidecar(_model_assessment()))

        self.assertTrue(result.valid)

    def test_valid_future_model_assessment_label_still_requires_run_identity(self):
        assessment = _model_assessment()
        assessment["label"] = "model_detect_openai_compatible"

        result = genre_sidecar.validate_sidecar(_sidecar(assessment))

        self.assertTrue(result.valid)

    def test_valid_human_assessment_and_current_adjudication(self):
        adjudication = {
            "label": "mystery",
            "selected_assessment_id": "human__reviewer-a__2026-08-12T02:10:00Z",
            "decided_at": "2026-08-12T02:20:00Z",
            "notes": "Human review is the current paper label.",
        }

        result = genre_sidecar.validate_sidecar(
            _sidecar(
                _metadata_assessment(),
                _human_assessment(),
                current_adjudication=adjudication,
            )
        )

        self.assertTrue(result.valid)

    def test_repeated_model_assessments_are_valid_with_distinct_run_identity(self):
        first = _model_assessment("run-001")
        second = _model_assessment("run-002")

        result = genre_sidecar.validate_sidecar(_sidecar(first, second))

        self.assertTrue(result.valid)

    def test_repeated_model_assessments_require_distinct_run_identity(self):
        first = _model_assessment("run-001")
        second = _model_assessment("run-001")
        second["assessment_id"] = (
            "model__gpt-oss-20b__run-001-repeat__2026-08-12T01:35:00Z"
        )

        result = genre_sidecar.validate_sidecar(_sidecar(first, second))

        self.assertFalse(result.valid)
        self.assertIn("duplicate_model_run_identity", _finding_kinds(result))

    def test_current_adjudication_may_be_null_or_absent(self):
        null_result = genre_sidecar.validate_sidecar(
            _sidecar(_metadata_assessment(), current_adjudication=None)
        )
        absent_sidecar = _sidecar(_metadata_assessment())
        absent_sidecar.pop("current_adjudication")

        absent_result = genre_sidecar.validate_sidecar(absent_sidecar)

        self.assertTrue(null_result.valid)
        self.assertTrue(absent_result.valid)

    def test_missing_schema_version_is_reported(self):
        sidecar = _sidecar(_metadata_assessment())
        sidecar.pop("schema_version")

        result = genre_sidecar.validate_sidecar(sidecar)

        self.assertFalse(result.valid)
        self.assertIn("missing_required_field", _finding_kinds(result))
        self.assertNotIn("invalid_schema_version", _finding_kinds(result))

    def test_wrong_type_schema_version_does_not_report_invalid_version(self):
        sidecar = _sidecar(_metadata_assessment())
        sidecar["schema_version"] = 1

        result = genre_sidecar.validate_sidecar(sidecar)

        self.assertFalse(result.valid)
        self.assertIn("wrong_type", _finding_kinds(result))
        self.assertNotIn("invalid_schema_version", _finding_kinds(result))

    def test_present_wrong_schema_version_is_reported_as_invalid_version(self):
        sidecar = _sidecar(_metadata_assessment())
        sidecar["schema_version"] = "genre-sidecar-v0"

        result = genre_sidecar.validate_sidecar(sidecar)

        self.assertFalse(result.valid)
        self.assertIn("invalid_schema_version", _finding_kinds(result))

    def test_wrong_assessments_type_is_reported(self):
        sidecar = _sidecar(_metadata_assessment())
        sidecar["assessments"] = {}

        result = genre_sidecar.validate_sidecar(sidecar)

        self.assertFalse(result.valid)
        self.assertIn("wrong_type", _finding_kinds(result))

    def test_missing_lcats_id_is_reported(self):
        sidecar = _sidecar(_metadata_assessment())
        sidecar.pop("lcats_id")

        result = genre_sidecar.validate_sidecar(sidecar)

        self.assertFalse(result.valid)
        self.assertIn("$.lcats_id", {finding.path for finding in result.findings})

    def test_missing_assessment_field_is_reported(self):
        assessment = _metadata_assessment()
        assessment.pop("method")

        result = genre_sidecar.validate_sidecar(_sidecar(assessment))

        self.assertFalse(result.valid)
        self.assertIn("$.assessments[0].method", {f.path for f in result.findings})
        self.assertEqual(1, len(_findings_for_path(result, "$.assessments[0].method")))

    def test_missing_scalar_assessment_field_is_reported_once(self):
        assessment = _metadata_assessment()
        assessment.pop("assessment_id")

        result = genre_sidecar.validate_sidecar(_sidecar(assessment))

        self.assertFalse(result.valid)
        self.assertEqual(
            [finding.kind for finding in result.findings],
            ["missing_required_field"],
        )

    def test_invalid_timestamp_is_reported(self):
        assessment = _metadata_assessment()
        assessment["generated_at"] = "not-a-time"

        result = genre_sidecar.validate_sidecar(_sidecar(assessment))

        self.assertFalse(result.valid)
        self.assertIn("invalid_timestamp", _finding_kinds(result))

    def test_date_only_timestamp_is_reported(self):
        assessment = _metadata_assessment()
        assessment["generated_at"] = "2026-08-12"

        result = genre_sidecar.validate_sidecar(_sidecar(assessment))

        self.assertFalse(result.valid)
        self.assertIn("invalid_timestamp", _finding_kinds(result))

    def test_invalid_scope_is_reported(self):
        assessment = _metadata_assessment()
        assessment["scope"] = "gutenberg_chapter"

        result = genre_sidecar.validate_sidecar(_sidecar(assessment))

        self.assertFalse(result.valid)
        self.assertIn("invalid_scope", _finding_kinds(result))

    def test_duplicate_assessment_id_is_reported(self):
        first = _metadata_assessment()
        second = copy.deepcopy(first)

        result = genre_sidecar.validate_sidecar(_sidecar(first, second))

        self.assertFalse(result.valid)
        self.assertIn("duplicate_assessment_id", _finding_kinds(result))

    def test_current_adjudication_must_reference_existing_assessment(self):
        result = genre_sidecar.validate_sidecar(
            _sidecar(
                _metadata_assessment(),
                current_adjudication={
                    "label": "mystery",
                    "selected_assessment_id": "missing-assessment",
                },
            )
        )

        self.assertFalse(result.valid)
        self.assertIn("unknown_assessment_id", _finding_kinds(result))

    def test_model_assessment_requires_repeated_run_identity(self):
        assessment = _model_assessment()
        assessment.pop("run_id")
        assessment["provenance"].pop("run_id")

        result = genre_sidecar.validate_sidecar(_sidecar(assessment))

        self.assertFalse(result.valid)
        self.assertIn("missing_model_run_identity", _finding_kinds(result))

    def test_future_model_assessment_run_identity_message_is_label_agnostic(self):
        assessment = _model_assessment()
        assessment["label"] = "model_detect_openai_compatible"
        assessment.pop("run_id")
        assessment["provenance"].pop("run_id")

        result = genre_sidecar.validate_sidecar(_sidecar(assessment))

        self.assertFalse(result.valid)
        messages = [finding.message for finding in result.findings]
        self.assertIn(
            "model assessments must include run_id or provenance.run_id", messages
        )
        self.assertFalse(any("model_detect assessments" in msg for msg in messages))

    def test_legacy_flat_genre_sidecar_is_detected_but_not_accepted_as_v1(self):
        legacy = {
            "detected_genre": "mystery",
            "detected_genre_confidence": 0.95,
            "genre_verdict": "detected",
            "summary": "Legacy AssessmentResult.to_dict() shape.",
        }

        result = genre_sidecar.validate_sidecar(legacy)

        self.assertTrue(genre_sidecar.is_legacy_flat_sidecar(legacy))
        self.assertFalse(result.valid)
        self.assertIn("legacy_flat_genre_sidecar", _finding_kinds(result))


if __name__ == "__main__":
    unittest.main()
