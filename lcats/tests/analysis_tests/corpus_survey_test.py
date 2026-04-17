"""Unit tests for lcats.analysis.corpus_survey architecture."""

import json
import pathlib
import tempfile
import unittest
import unittest.mock
from unittest import mock

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
        output = corpus_survey.run_special_characters_check(
            displayed_text="pi√©ce",
            extract_script="scripts/utils/extract_special_chars.py",
            allow_smart=True,
            allowlist_config="",
            excluded_codepoints=["00A0"],
            excluded_chars=["é"],
            context=10,
            nocontext=False,
            name_width=0,
            header=False,
        )
        self.assertIn("COPYRIGHT SIGN", output)
        first_row = output.splitlines()[0].split("\t")
        self.assertEqual("U+221A", first_row[0])
        self.assertEqual("2", first_row[4])

    def test_run_special_characters_check_uses_nocontext_flag(self):
        output = corpus_survey.run_special_characters_check(
            displayed_text="pi√©ce",
            extract_script="scripts/utils/extract_special_chars.py",
            allow_smart=True,
            allowlist_config="",
            excluded_codepoints=[],
            excluded_chars=[],
            context=10,
            nocontext=True,
            name_width=12,
            header=True,
        )

        lines = output.splitlines()
        self.assertEqual("\t".join(corpus_survey.specials.TSV_COLUMNS), lines[0])
        self.assertEqual("", lines[1].split("\t")[5])

    def test_parser_defaults_include_context(self):
        parser = corpus_survey.build_parser()
        args = parser.parse_args([])
        self.assertEqual(10, args.context)
        self.assertFalse(args.nocontext)
        self.assertEqual("path", args.identifier)
        self.assertEqual(48, args.unicode_name_width)

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

    def test_safe_accented_characters_and_horizontal_bar_are_not_flagged(self):
        detector = corpus_survey.SpecialCharactersDetector(
            safe_excluded_chars=corpus_survey.SAFE_EXCLUDED_CHARS,
            rare_review_chars=corpus_survey.RARE_REVIEW_CHARS,
            mojibake_trigger_chars=corpus_survey.MOJIBAKE_TRIGGER_CHARS,
        )
        text = "A naïve café uses æ and œ with ― punctuation."

        findings = detector.run(text)

        self.assertEqual([], findings)

    def test_rare_review_characters_emit_low_severity_findings(self):
        detector = corpus_survey.SpecialCharactersDetector(
            safe_excluded_chars=corpus_survey.SAFE_EXCLUDED_CHARS,
            rare_review_chars=corpus_survey.RARE_REVIEW_CHARS,
            mojibake_trigger_chars=corpus_survey.MOJIBAKE_TRIGGER_CHARS,
        )

        findings = detector.run("Transliteration: Ō ā ×")

        self.assertEqual(3, len(findings))
        for finding in findings:
            self.assertEqual("rare-review-character", finding.kind)
            self.assertEqual("info", finding.severity)

    def test_mojibake_sequences_emit_high_severity_findings(self):
        detector = corpus_survey.SpecialCharactersDetector(
            safe_excluded_chars=corpus_survey.SAFE_EXCLUDED_CHARS,
            rare_review_chars=corpus_survey.RARE_REVIEW_CHARS,
            mojibake_trigger_chars=corpus_survey.MOJIBAKE_TRIGGER_CHARS,
        )
        text = "Broken tokens: Â£ and Ã© and â€™."

        findings = detector.run(text)

        self.assertGreaterEqual(len(findings), 3)
        self.assertTrue(
            all(finding.kind == "mojibake-sequence" for finding in findings)
        )
        self.assertTrue(all(finding.severity == "error" for finding in findings))

    def test_valid_accented_text_does_not_flood_findings(self):
        detector = corpus_survey.SpecialCharactersDetector(
            safe_excluded_chars=corpus_survey.SAFE_EXCLUDED_CHARS,
            rare_review_chars=corpus_survey.RARE_REVIEW_CHARS,
            mojibake_trigger_chars=corpus_survey.MOJIBAKE_TRIGGER_CHARS,
        )
        text = (
            "Émile wrote about naïve readers in café salons while "
            "François and Zoë discussed œuvre and æsthetics."
        )

        findings = detector.run(text)

        self.assertEqual([], findings)

    def test_parse_special_character_rows_uses_stable_schema(self):
        output = "U+00A9\t©\tCOPYRIGHT SIGN\t1\t2\tctx\tspecial\tliteral"

        rows = corpus_survey.parse_special_character_rows(
            output, pathlib.Path("story.json"), "Story Title"
        )

        self.assertEqual(1, len(rows))
        row = rows[0]
        self.assertEqual(corpus_survey.TSV_COLUMNS, list(row.keys())[:15])
        self.assertEqual("Story Title", row["story_title"])
        self.assertEqual("story.json", row["story_file"])
        self.assertEqual("story.json", row["path"])
        self.assertEqual("spchar", row["check"])
        self.assertEqual("spchar", row["kind"])
        self.assertEqual("U+00A9", row["codepoint"])
        self.assertEqual("", row["story_identifier"])

    def test_parse_special_character_rows_skips_header_line(self):
        output = (
            "codepoint\tchar\tunicode_name\toccurrence_index\t"
            "offset\tcontext\tclassification\tevidence\n"
            "U+00A9\t©\tCOPYRIGHT SIGN\t1\t2\tctx\tmojibake-pattern\tliteral"
        )

        rows = corpus_survey.parse_special_character_rows(
            output, pathlib.Path("story.json"), "Story Title"
        )

        self.assertEqual(1, len(rows))
        self.assertEqual("U+00A9", rows[0]["codepoint"])
        self.assertEqual("mojibake", rows[0]["classification"])

    def test_main_tsv_output_has_stable_columns_for_multiple_checks(self):
        rows = [
            {
                "check": "spchar",
                "kind": "spchar",
                "severity": "warning",
                "codepoint": "U+00A9",
                "char": "©",
                "unicode_name": "COPYRIGHT SIGN",
                "occurrence_index": "1",
                "offset": "2",
                "span_start": "",
                "span_end": "",
                "context": "ctx",
                "classification": "special",
                "evidence": "literal",
                "message": "Special character finding.",
                "story_title": "The Story",
                "story_file": "story.json",
                "path": "story.json",
                "identifier": "",
            },
            {
                "check": "boundary",
                "kind": "start-contam",
                "severity": "warning",
                "codepoint": "",
                "char": "",
                "unicode_name": "",
                "occurrence_index": "",
                "offset": "",
                "span_start": "0",
                "span_end": "10",
                "context": "",
                "classification": "",
                "evidence": '{"line":"By Author"}',
                "message": "Likely author line at start of story.",
                "story_title": "The Story",
                "story_file": "story.json",
                "path": "story.json",
                "identifier": "",
            },
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            story_path = pathlib.Path(temp_dir) / "story.json"
            story_path.write_text("{}", encoding="utf-8")

            with mock.patch.object(
                corpus_survey, "find_json_files", return_value=[story_path]
            ), mock.patch.object(
                corpus_survey, "survey_file", return_value=rows
            ), mock.patch.object(
                corpus_survey.sys.stderr, "isatty", return_value=False
            ), mock.patch(
                "sys.stdout"
            ) as fake_stdout:
                exit_code = corpus_survey.main(
                    [
                        "--format",
                        "tsv",
                        "--check-for",
                        "special-characters,boundary-contamination",
                        "--no-progress",
                        temp_dir,
                    ]
                )

        self.assertEqual(1, exit_code)
        output = "".join(call.args[0] for call in fake_stdout.write.call_args_list)
        lines = [line for line in output.splitlines() if line]
        self.assertGreaterEqual(len(lines), 3)
        self.assertEqual("\t".join(corpus_survey.TSV_COLUMNS), lines[0])
        self.assertTrue(all(not line.startswith("#check=") for line in lines[1:]))
        first_data = lines[1].split("\t")
        self.assertEqual("spchar", first_data[0])
        self.assertEqual("story.json", first_data[-1])

    def test_main_tsv_output_file_writes_and_skips_stdout(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            story_path = pathlib.Path(temp_dir) / "story.json"
            story_path.write_text("{}", encoding="utf-8")
            output_path = pathlib.Path(temp_dir) / "report.tsv"
            row = corpus_survey._clean_row(story_path)

            with mock.patch.object(
                corpus_survey, "find_json_files", return_value=[story_path]
            ), mock.patch.object(
                corpus_survey, "survey_file", return_value=[]
            ), mock.patch.object(
                corpus_survey.sys.stderr, "isatty", return_value=False
            ), mock.patch(
                "sys.stdout"
            ) as fake_stdout:
                exit_code = corpus_survey.main(
                    [
                        "--format",
                        "tsv",
                        "--output",
                        str(output_path),
                        "--print-clean-filenames",
                        "--no-progress",
                        temp_dir,
                    ]
                )

            self.assertEqual(0, exit_code)
            self.assertEqual([], fake_stdout.write.call_args_list)
            written = output_path.read_text(encoding="utf-8")
            self.assertIn("\t".join(corpus_survey.TSV_COLUMNS), written)
            self.assertIn("summary\tclean\tinfo", written)
            self.assertIn("story.json", written)
            self.assertEqual("summary", row["check"])

    def test_main_tsv_identifier_switches_to_filename(self):
        rows = [
            {
                "check": "spchar",
                "kind": "spchar",
                "severity": "warning",
                "codepoint": "U+00A9",
                "char": "©",
                "unicode_name": "COPYRIGHT SIGN",
                "occurrence_index": "1",
                "offset": "2",
                "span_start": "",
                "span_end": "",
                "context": "ctx",
                "classification": "special",
                "evidence": "literal",
                "message": "Special character finding.",
                "story_title": "The Story",
                "story_file": "story.json",
                "path": "corpora/story.json",
                "identifier": "",
            }
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            story_path = pathlib.Path(temp_dir) / "story.json"
            story_path.write_text("{}", encoding="utf-8")

            with mock.patch.object(
                corpus_survey, "find_json_files", return_value=[story_path]
            ), mock.patch.object(
                corpus_survey, "survey_file", return_value=rows
            ), mock.patch.object(
                corpus_survey.sys.stderr, "isatty", return_value=False
            ), mock.patch(
                "sys.stdout"
            ) as fake_stdout:
                corpus_survey.main(
                    [
                        "--format",
                        "tsv",
                        "--identifier",
                        "filename",
                        "--no-progress",
                        temp_dir,
                    ]
                )

        output = "".join(call.args[0] for call in fake_stdout.write.call_args_list)
        lines = [line for line in output.splitlines() if line]
        self.assertEqual("story.json", lines[1].split("\t")[-1])

    def test_compact_human_tsv_row_truncates_unicode_name(self):
        row = corpus_survey.compact_human_tsv_row(
            {
                "unicode_name": "MATHEMATICAL DOUBLE-STRUCK SMALL C",
                "story_title": "Story",
                "story_file": "story.json",
                "path": "corpora/story.json",
            },
            identifier="title",
            unicode_name_width=8,
        )

        self.assertEqual("MATHEMA…", row["unicode_name"])
        self.assertEqual("Story", row["story_identifier"])

    def test_parser_help_includes_compact_value_legend(self):
        parser = corpus_survey.build_parser()

        help_text = parser.format_help()

        self.assertIn("Compact TSV values:", help_text)
        self.assertIn("spchar=special-characters", help_text)

    def test_main_tsv_no_header_is_deterministic(self):
        rows = [corpus_survey._clean_row(pathlib.Path("story.json"))]
        with tempfile.TemporaryDirectory() as temp_dir:
            story_path = pathlib.Path(temp_dir) / "story.json"
            story_path.write_text("{}", encoding="utf-8")

            with mock.patch.object(
                corpus_survey, "find_json_files", return_value=[story_path]
            ), mock.patch.object(
                corpus_survey, "survey_file", return_value=rows
            ), mock.patch.object(
                corpus_survey.sys.stderr, "isatty", return_value=False
            ), mock.patch(
                "sys.stdout"
            ) as fake_stdout:
                corpus_survey.main(
                    ["--format", "tsv", "--no-header", "--no-progress", temp_dir]
                )

        output = "".join(call.args[0] for call in fake_stdout.write.call_args_list)
        lines = [line for line in output.splitlines() if line]
        self.assertEqual(1, len(lines))
        self.assertNotEqual("\t".join(corpus_survey.TSV_COLUMNS), lines[0])

    def test_main_progress_default_follows_tty(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            story_path = pathlib.Path(temp_dir) / "story.json"
            story_path.write_text("{}", encoding="utf-8")

            with mock.patch.object(
                corpus_survey, "find_json_files", return_value=[story_path]
            ), mock.patch.object(
                corpus_survey, "survey_file", return_value=[]
            ), mock.patch.object(
                corpus_survey.sys.stderr, "isatty", return_value=False
            ), mock.patch.object(
                corpus_survey.tqdm, "tqdm"
            ) as mock_tqdm:
                mock_tqdm.side_effect = lambda items, disable: items
                corpus_survey.main([temp_dir])

        self.assertTrue(mock_tqdm.call_args.kwargs["disable"])

    def test_main_no_progress_disables_tqdm(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            story_path = pathlib.Path(temp_dir) / "story.json"
            story_path.write_text("{}", encoding="utf-8")

            with mock.patch.object(
                corpus_survey, "find_json_files", return_value=[story_path]
            ), mock.patch.object(
                corpus_survey, "survey_file", return_value=[]
            ), mock.patch.object(
                corpus_survey.tqdm, "tqdm"
            ) as mock_tqdm:
                mock_tqdm.side_effect = lambda items, disable: items
                corpus_survey.main(["--no-progress", temp_dir])

        self.assertTrue(mock_tqdm.call_args.kwargs["disable"])


if __name__ == "__main__":
    unittest.main()
