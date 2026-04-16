"""Unit tests for lcats.analysis.corpus_survey architecture."""

import json
import pathlib
import tempfile
import unittest
import unittest.mock

from lcats.analysis import corpus_survey


class CorpusSurveyArchitectureTest(unittest.TestCase):
    """Tests for detector orchestration and placeholder special-char detector."""

    def setUp(self):
        self.fixture_dir = pathlib.Path(__file__).parent / "fixtures"
        self.clean_text = "This is plain ASCII text."
        self.bad_start_text = "© starts with a bad char"
        self.bad_end_text = "ends with a bad char ©"
        self.encoding_issue_text = "contains replacement char: \ufffd"

    def _fixture_text(self, filename):
        return (self.fixture_dir / filename).read_text(encoding="utf-8")

    def test_clean_text_has_no_findings(self):
        findings = corpus_survey.run_detectors(self.clean_text, config={})
        self.assertEqual([], findings)

    def test_start_detector_finds_title_author_and_editor_note(self):
        text = self._fixture_text("bad_start_title_author_note.txt")
        findings = corpus_survey.StartDetector().run(text)

        types = [finding.evidence["type"] for finding in findings]
        self.assertIn("title-line", types)
        self.assertIn("author-line", types)
        self.assertIn("editor-note", types)

    def test_end_detector_finds_the_end_and_gutenberg_footer(self):
        text = self._fixture_text("bad_end_markers.txt")
        findings = corpus_survey.EndDetector().run(text)

        types = [finding.evidence["type"] for finding in findings]
        self.assertIn("the-end", types)
        self.assertIn("gutenberg-footer", types)

    def test_structural_detectors_find_expected_artifacts(self):
        text = self._fixture_text("structural_artifacts.txt")
        detectors = [
            corpus_survey.ChapterHeadingDetector(),
            corpus_survey.TocRemnantsDetector(),
            corpus_survey.SectionBreakDetector(),
            corpus_survey.IllustrationCaptionDetector(),
        ]

        findings = []
        for detector in detectors:
            findings.extend(detector.run(text))

        types = [finding.evidence["type"] for finding in findings]
        self.assertIn("chapter-heading", types)
        self.assertIn("toc-heading", types)
        self.assertIn("toc-entry", types)
        self.assertIn("section-break", types)
        self.assertIn("illustration-caption", types)

    def test_structural_detectors_avoid_false_positives_on_clean_excerpt(self):
        text = self._fixture_text("clean_story_excerpt.txt")
        detectors = [
            corpus_survey.StartDetector(),
            corpus_survey.EndDetector(),
            corpus_survey.ChapterHeadingDetector(),
            corpus_survey.TocRemnantsDetector(),
            corpus_survey.SectionBreakDetector(),
            corpus_survey.IllustrationCaptionDetector(),
        ]

        findings = []
        for detector in detectors:
            findings.extend(detector.run(text))

        self.assertEqual([], findings)

    def test_start_detector_fixtures(self):
        cases = [
            ("boundary_contamination/start_contaminated.txt", 3),
            ("boundary_contamination/clean_story.txt", 0),
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
            ("boundary_contamination/end_the_end.txt", "the-end"),
            ("boundary_contamination/end_gutenberg.txt", "gutenberg-footer"),
        ]

        for fixture_name, expected_type in cases:
            with self.subTest(fixture_name=fixture_name):
                findings = corpus_survey.EndDetector().run(
                    self._fixture_text(fixture_name)
                )
                self.assertGreaterEqual(len(findings), 1)
                types = [finding.evidence["type"] for finding in findings]
                self.assertIn(expected_type, types)
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

    def test_run_lcats_display_uses_internal_formatter_api(self):
        sample_story = {
            "name": "Sample",
            "author": ["Author"],
            "metadata": {"source": "unit-test"},
            "body": "Hello world",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            story_path = pathlib.Path(temp_dir) / "story.json"
            with story_path.open("w", encoding="utf-8") as story_file:
                json.dump(sample_story, story_file)

            with unittest.mock.patch.object(
                corpus_survey.lcats.inspect,
                "format_story_json",
                return_value="rendered",
            ) as mock_formatter:
                output = corpus_survey.run_lcats_display(story_path)

        mock_formatter.assert_called_once_with(
            sample_story, max_body_chars=None, width=80
        )
        self.assertEqual("rendered\n", output)

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
