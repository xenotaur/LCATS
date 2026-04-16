"""Unit tests for lcats.analysis.corpus_survey architecture."""

import pathlib
import unittest
import unittest.mock

from lcats.analysis import corpus_survey


class CorpusSurveyArchitectureTest(unittest.TestCase):
    """Tests for detector orchestration and placeholder special-char detector."""

    def setUp(self):
        self.fixture_dir = (
            pathlib.Path(__file__).resolve().parent / "fixtures" / "boundary_contamination"
        )
        self.clean_text = "This is plain ASCII text."
        self.bad_start_text = "© starts with a bad char"
        self.bad_end_text = "ends with a bad char ©"
        self.encoding_issue_text = "contains replacement char: �"

    def _fixture_text(self, filename: str) -> str:
        return (self.fixture_dir / filename).read_text(encoding="utf-8")

    def test_clean_text_has_no_findings(self):
        findings = corpus_survey.run_detectors(self.clean_text, config={})
        self.assertEqual([], findings)

    def test_start_detector_fixtures(self):
        cases = [
            ("start_contaminated.txt", 3),
            ("clean_story.txt", 0),
        ]

        for fixture_name, expected_count in cases:
            with self.subTest(fixture_name=fixture_name):
                findings = corpus_survey.StartDetector().run(
                    self._fixture_text(fixture_name)
                )
                self.assertEqual(expected_count, len(findings))
                for finding in findings:
                    self.assertEqual("start-contamination", finding.kind)

    def test_end_detector_fixtures(self):
        cases = [
            ("end_the_end.txt", "the-end"),
            ("end_gutenberg.txt", "gutenberg-footer"),
        ]

        for fixture_name, expected_pattern in cases:
            with self.subTest(fixture_name=fixture_name):
                findings = corpus_survey.EndDetector().run(
                    self._fixture_text(fixture_name)
                )
                self.assertGreaterEqual(len(findings), 1)
                patterns = [finding.evidence["pattern"] for finding in findings]
                self.assertIn(expected_pattern, patterns)
                for finding in findings:
                    self.assertEqual("end-contamination", finding.kind)


class CorpusSurveyCliHelpersTest(unittest.TestCase):
    """Tests for corpus_survey CLI helper functions moved from script."""

    def setUp(self):
        self.bad_start_text = "© starts with a bad char"
        self.bad_end_text = "ends with a bad char ©"
        self.encoding_issue_text = "contains replacement char: �"

    def test_run_special_characters_check_forwards_context(self):
        completed = unittest.mock.Mock()
        completed.returncode = 0
        completed.stdout = "U+00A9\t©\tCOPYRIGHT SIGN\t1\t2\tctx"
        completed.stderr = ""

        with unittest.mock.patch.object(
            corpus_survey.subprocess, "run", return_value=completed
        ) as mock_run:
            output = corpus_survey.run_special_characters_check(
                displayed_text="pi√©ce",
                extract_script="scripts/utils/extract_special_chars.py",
                allow_smart=True,
                excluded_codepoints=["00A0"],
                excluded_chars=["é"],
                context=10,
                nocontext=False,
                name_width=0,
                header=False,
            )

        self.assertIn("COPYRIGHT SIGN", output)
        cmd = mock_run.call_args.args[0]
        self.assertIn("--context=10", cmd)
        self.assertNotIn("--nocontext", cmd)

    def test_run_special_characters_check_uses_nocontext_flag(self):
        completed = unittest.mock.Mock()
        completed.returncode = 0
        completed.stdout = ""
        completed.stderr = ""

        with unittest.mock.patch.object(
            corpus_survey.subprocess, "run", return_value=completed
        ) as mock_run:
            corpus_survey.run_special_characters_check(
                displayed_text="pi√©ce",
                extract_script="scripts/utils/extract_special_chars.py",
                allow_smart=True,
                excluded_codepoints=[],
                excluded_chars=[],
                context=10,
                nocontext=True,
                name_width=12,
                header=True,
            )

        cmd = mock_run.call_args.args[0]
        self.assertIn("--nocontext", cmd)
        self.assertNotIn("--context=10", cmd)
        self.assertIn("--name-width=12", cmd)
        self.assertIn("--header", cmd)

    def test_parser_defaults_include_context(self):
        parser = corpus_survey.build_parser()
        args = parser.parse_args([])
        self.assertEqual(10, args.context)
        self.assertFalse(args.nocontext)

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
