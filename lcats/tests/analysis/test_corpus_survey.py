"""Unit tests for lcats.analysis.corpus_survey architecture."""

import unittest

from lcats.analysis import corpus_survey


class CorpusSurveyArchitectureTest(unittest.TestCase):
    """Tests for detector orchestration and placeholder special-char detector."""

    def setUp(self):
        self.clean_text = "This is plain ASCII text."
        self.bad_start_text = "© starts with a bad char"
        self.bad_end_text = "ends with a bad char ©"
        self.encoding_issue_text = "contains replacement char: �"

    def test_clean_text_has_no_findings(self):
        findings = corpus_survey.run_detectors(self.clean_text, config={})
        self.assertEqual([], findings)

    def test_bad_start_and_bad_end_report_precise_spans(self):
        cases = [
            (self.bad_start_text, 0),
            (self.bad_end_text, len(self.bad_end_text) - 1),
        ]

        for text, expected_index in cases:
            with self.subTest(text=text):
                findings = corpus_survey.run_detectors(text, config={})
                self.assertEqual(1, len(findings))
                finding = findings[0]
                self.assertEqual("special-character", finding.kind)
                self.assertEqual("warning", finding.severity)
                self.assertEqual((expected_index, expected_index + 1), finding.span)
                self.assertIn("codepoint", finding.evidence)

    def test_encoding_issues_are_detected(self):
        findings = corpus_survey.run_detectors(self.encoding_issue_text, config={})

        self.assertEqual(1, len(findings))
        finding = findings[0]
        self.assertEqual("U+FFFD", finding.evidence["codepoint"])
        self.assertEqual("�", finding.evidence["character"])

    def test_custom_detector_configuration_is_used(self):
        detector = corpus_survey.SpecialCharactersDetector(excluded_chars=["©", "�"])
        findings = corpus_survey.run_detectors(
            self.bad_start_text + self.encoding_issue_text,
            config={"detectors": [detector]},
        )

        self.assertEqual([], findings)


if __name__ == "__main__":
    unittest.main()
