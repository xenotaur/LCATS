"""Tests for unified lcats.analysis.corpus package."""

import json
import pathlib
import unittest
from unittest import mock

from lcats import test_utils
from lcats.analysis.corpus import cli
from lcats.analysis.corpus import discovery
from lcats.analysis.corpus import processing
from lcats.analysis.corpus import qa
from lcats.analysis.corpus import stats
from lcats.analysis.corpus.detectors import boundary
from lcats.analysis.corpus.detectors import unicode
from lcats.utils import capture


class TestDiscovery(test_utils.TestCaseWithData):
    """Tests for corpus discovery helpers."""

    def test_find_corpus_stories(self):
        root = pathlib.Path(self.test_temp_dir) / "corpus"
        (root / "a").mkdir(parents=True)
        (root / "a" / "story.json").write_text("{}", encoding="utf-8")

        found = discovery.find_corpus_stories(root)

        self.assertEqual([root / "a" / "story.json"], found)


class TestQa(test_utils.TestCaseWithData):
    """Tests for QA detector orchestration."""

    def test_boundary_detectors_via_qa(self):
        text = "A Tale\nBy Someone\n\nBody\nTHE END"
        findings = qa.run_detectors(
            text,
            config={"detectors": [boundary.StartDetector(), boundary.EndDetector()]},
        )

        finding_kinds = [finding.kind for finding in findings]
        self.assertIn("start-contamination", finding_kinds)
        self.assertIn("end-contamination", finding_kinds)


class TestStatsAndProcessing(test_utils.TestCaseWithData):
    """Tests for stats and processing modules."""

    def test_stats_returns_story_and_author_frames(self):
        root = pathlib.Path(self.test_temp_dir) / "corpus"
        root.mkdir()
        file_path = root / "story.json"
        file_path.write_text(
            json.dumps({"name": "Title", "author": ["A"], "body": "hello world"}),
            encoding="utf-8",
        )

        mock_encoder = mock.Mock()
        mock_encoder.encode.side_effect = (
            lambda text, disallowed_special=(): text.split()
        )

        with mock.patch.object(
            stats.story_analysis, "get_encoder", return_value=mock_encoder
        ):
            with capture.suppress_output():
                story_stats, author_stats = stats.compute_corpus_stats([file_path])

        self.assertFalse(story_stats.empty)
        self.assertFalse(author_stats.empty)

    def test_process_files(self):
        root = pathlib.Path(self.test_temp_dir) / "corpus"
        output_root = pathlib.Path(self.test_temp_dir) / "output"
        root.mkdir()
        output_root.mkdir()
        input_path = root / "story.json"
        input_path.write_text("{}", encoding="utf-8")

        with capture.suppress_output():
            summary = processing.process_files(
                [input_path],
                corpora_root=root,
                output_root=output_root,
                processor_function=lambda data: data,
                job_label="job",
            )

        self.assertEqual(1, summary["processed"])


class TestCli(test_utils.TestCaseWithData):
    """Tests for corpus cli subcommands."""

    @mock.patch("lcats.analysis.corpus.cli.survey_file")
    @mock.patch("lcats.analysis.corpus.cli.discovery.find_json_files")
    def test_run_survey(self, mock_find_json_files, mock_survey_file):
        path = pathlib.Path(self.test_temp_dir) / "story.json"
        path.write_text("{}", encoding="utf-8")
        mock_find_json_files.return_value = [path]
        mock_survey_file.return_value = []

        with capture.suppress_output():
            status = cli.run_survey(
                [str(path), "--check-for", "boundary-contamination"]
            )

        self.assertEqual(0, status)
        mock_survey_file.assert_called_once()

    @mock.patch("lcats.analysis.corpus.cli.stats.compute_corpus_stats")
    def test_run_stats(self, mock_compute):
        import pandas as pd

        mock_compute.return_value = (pd.DataFrame([{"a": 1}]), pd.DataFrame([{"b": 2}]))

        with capture.suppress_output():
            status = cli.run_stats([])

        self.assertEqual(0, status)
        mock_compute.assert_called_once()


class TestCompatibilityWrappers(unittest.TestCase):
    """Tests for legacy wrapper modules."""

    def test_legacy_modules_forward(self):
        from lcats.analysis import corpus_survey
        from lcats.analysis import corpus_surveyor

        self.assertIs(corpus_survey.StartDetector, boundary.StartDetector)
        self.assertIs(
            corpus_survey.SpecialCharactersDetector, unicode.SpecialCharactersDetector
        )
        self.assertIs(
            corpus_surveyor.find_corpus_stories, discovery.find_corpus_stories
        )


if __name__ == "__main__":
    unittest.main()
