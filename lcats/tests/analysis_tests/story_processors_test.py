"""Unit tests for lcats.analysis.story_processors."""

import json
import unittest
import unittest.mock
from unittest.mock import MagicMock, patch

from lcats.analysis import story_processors


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MINIMAL_STORY = {
    "name": "A Short Tale",
    "author": "Alice",
    "body": "Once upon a time the brave knight slew the dragon. The end.",
}

_UNTITLED_STORY = {
    "body": "Just some body text with no name or author.",
}


def _make_mock_encoder():
    """Return a mock encoder that tokenises by whitespace."""
    enc = MagicMock()
    enc.encode.side_effect = lambda text, **kw: text.split()
    return enc


# ---------------------------------------------------------------------------
# Tests: story_summarizer
# ---------------------------------------------------------------------------


class TestStorySummarizer(unittest.TestCase):
    """Tests for story_summarizer."""

    def setUp(self):
        self._enc_patcher = patch(
            "lcats.analysis.story_analysis.get_encoder",
            return_value=_make_mock_encoder(),
        )
        self._enc_patcher.start()

    def tearDown(self):
        self._enc_patcher.stop()

    def test_returns_dict(self):
        result = story_processors.story_summarizer(_MINIMAL_STORY)
        self.assertIsInstance(result, dict)

    def test_title_extracted(self):
        result = story_processors.story_summarizer(_MINIMAL_STORY)
        self.assertEqual(result["title"], "A Short Tale")

    def test_missing_name_falls_back_to_untitled(self):
        result = story_processors.story_summarizer(_UNTITLED_STORY)
        self.assertEqual(result["title"], "<Untitled>")

    def test_authors_extracted_as_list(self):
        result = story_processors.story_summarizer(_MINIMAL_STORY)
        self.assertEqual(result["authors"], ["Alice"])

    def test_missing_author_returns_empty_list(self):
        result = story_processors.story_summarizer(_UNTITLED_STORY)
        self.assertEqual(result["authors"], [])

    def test_author_from_metadata_when_no_direct_author(self):
        data = {
            "name": "T",
            "metadata": {"author": "Bob"},
            "body": "Some text here for testing.",
        }
        result = story_processors.story_summarizer(data)
        self.assertIn("Bob", result["authors"])

    def test_body_length_chars_correct(self):
        result = story_processors.story_summarizer(_MINIMAL_STORY)
        self.assertEqual(result["body_length_chars"], len(_MINIMAL_STORY["body"]))

    def test_body_length_words_positive(self):
        result = story_processors.story_summarizer(_MINIMAL_STORY)
        self.assertGreater(result["body_length_words"], 0)

    def test_body_length_tokens_is_int(self):
        result = story_processors.story_summarizer(_MINIMAL_STORY)
        self.assertIsInstance(result["body_length_tokens"], int)

    def test_body_length_paragraphs_is_int(self):
        result = story_processors.story_summarizer(_MINIMAL_STORY)
        self.assertIsInstance(result["body_length_paragraphs"], int)

    def test_top_keywords_is_list(self):
        result = story_processors.story_summarizer(_MINIMAL_STORY)
        self.assertIsInstance(result["top_keywords"], list)

    def test_top_keywords_items_have_term_and_count(self):
        result = story_processors.story_summarizer(_MINIMAL_STORY)
        for item in result["top_keywords"]:
            with self.subTest(item=item):
                self.assertIn("term", item)
                self.assertIn("count", item)

    def test_expected_keys_present(self):
        result = story_processors.story_summarizer(_MINIMAL_STORY)
        expected_keys = {
            "title",
            "authors",
            "body_length_chars",
            "body_length_words",
            "body_length_tokens",
            "body_length_paragraphs",
            "top_keywords",
        }
        self.assertEqual(set(result.keys()), expected_keys)

    def test_result_is_json_serializable(self):
        result = story_processors.story_summarizer(_MINIMAL_STORY)
        # Should not raise
        serialized = json.dumps(result)
        self.assertIsInstance(serialized, str)

    def test_empty_body(self):
        data = {"name": "Empty", "author": "Author", "body": ""}
        result = story_processors.story_summarizer(data)
        self.assertEqual(result["body_length_chars"], 0)
        self.assertEqual(result["body_length_words"], 0)
        self.assertEqual(result["top_keywords"], [])

    def test_body_bytes_decoded(self):
        data = {"name": "Bytes", "body": b"hello world text here"}
        result = story_processors.story_summarizer(data)
        self.assertGreater(result["body_length_chars"], 0)

    def test_list_of_authors(self):
        data = {"name": "T", "author": ["Alice", "Bob"], "body": "some text"}
        result = story_processors.story_summarizer(data)
        self.assertEqual(result["authors"], ["Alice", "Bob"])


# ---------------------------------------------------------------------------
# Tests: make_annotated_segment_extractor – factory behaviour
# ---------------------------------------------------------------------------


class TestMakeAnnotatedSegmentExtractorFactory(unittest.TestCase):
    """Tests for make_annotated_segment_extractor factory (not the inner callable)."""

    def test_returns_callable(self):
        client = MagicMock()
        processor = story_processors.make_annotated_segment_extractor(client)
        self.assertTrue(callable(processor))

    def test_default_models_stored(self):
        """Returned processor captures default model names from factory."""
        client = MagicMock()
        with patch("lcats.analysis.scene_analysis.make_segment_extractor") as ms, patch(
            "lcats.analysis.scene_analysis.make_semantics_extractor"
        ) as mm:
            ms.return_value = MagicMock()
            mm.return_value = MagicMock()
            processor = story_processors.make_annotated_segment_extractor(client)
        # Factory creates extractors at call time
        ms.assert_called_once_with(client)
        mm.assert_called_once_with(client)
        self.assertTrue(callable(processor))

    def test_custom_model_names_accepted(self):
        client = MagicMock()
        processor = story_processors.make_annotated_segment_extractor(
            client, segment_model="gpt-3.5", semantic_model="gpt-3.5"
        )
        self.assertTrue(callable(processor))

    def test_include_validation_false_accepted(self):
        client = MagicMock()
        processor = story_processors.make_annotated_segment_extractor(
            client, include_validation=False
        )
        self.assertTrue(callable(processor))


# ---------------------------------------------------------------------------
# Tests: processor_function (inner callable)
# ---------------------------------------------------------------------------


class TestProcessorFunction(unittest.TestCase):
    """Tests for the inner processor_function returned by make_annotated_segment_extractor."""

    def _run_processor(
        self,
        data=None,
        seg_output=None,
        seg_errors=None,
        annotated=None,
        include_validation=True,
        raise_in_annotate=None,
    ):
        """Execute the processor with mocked dependencies and return the result."""
        if data is None:
            data = dict(_MINIMAL_STORY)

        seg_errors = seg_errors or {}
        seg_extraction = {
            "extracted_output": seg_output or [],
            "parsing_error": seg_errors.get("parsing_error"),
            "extraction_error": seg_errors.get("extraction_error"),
            "alignment_error": seg_errors.get("alignment_error"),
            "validation_report": seg_errors.get("validation_report"),
        }

        mock_seg_extractor = MagicMock()
        mock_seg_extractor.extract.return_value = seg_extraction

        mock_sem_extractor = MagicMock()
        mock_encoder = _make_mock_encoder()

        client = MagicMock()

        if raise_in_annotate is not None:
            annotate_kwargs = {"side_effect": raise_in_annotate}
        else:
            annotate_kwargs = {"return_value": annotated or []}

        with patch(
            "lcats.analysis.scene_analysis.make_segment_extractor",
            return_value=mock_seg_extractor,
        ), patch(
            "lcats.analysis.scene_analysis.make_semantics_extractor",
            return_value=mock_sem_extractor,
        ), patch(
            "lcats.analysis.story_analysis.get_encoder",
            return_value=mock_encoder,
        ), patch(
            "lcats.analysis.scene_analysis.annotate_segments_with_semantics",
            **annotate_kwargs,
        ):
            processor = story_processors.make_annotated_segment_extractor(
                client, include_validation=include_validation
            )
            result = processor(data)

        return result

    # -- Basic structure --

    def test_returns_dict(self):
        result = self._run_processor()
        self.assertIsInstance(result, dict)

    def test_result_is_json_serializable(self):
        result = self._run_processor()
        serialized = json.dumps(result)
        self.assertIsInstance(serialized, str)

    def test_expected_top_level_keys(self):
        result = self._run_processor()
        for key in (
            "title",
            "authors",
            "body_length_chars",
            "body_length_words",
            "body_length_tokens",
            "body_length_paragraphs",
            "top_keywords",
            "models",
            "segmentation",
            "segments",
        ):
            with self.subTest(key=key):
                self.assertIn(key, result)

    def test_models_dict_keys(self):
        result = self._run_processor()
        self.assertIn("segment_model", result["models"])
        self.assertIn("semantic_model", result["models"])

    def test_default_model_names_are_gpt4o(self):
        result = self._run_processor()
        self.assertEqual(result["models"]["segment_model"], "gpt-4o")
        self.assertEqual(result["models"]["semantic_model"], "gpt-4o")

    def test_custom_model_names_reflected(self):
        mock_seg = MagicMock()
        mock_seg.extract.return_value = {"extracted_output": []}
        mock_sem = MagicMock()
        mock_enc = _make_mock_encoder()

        client = MagicMock()
        with patch(
            "lcats.analysis.scene_analysis.make_segment_extractor",
            return_value=mock_seg,
        ), patch(
            "lcats.analysis.scene_analysis.make_semantics_extractor",
            return_value=mock_sem,
        ), patch(
            "lcats.analysis.story_analysis.get_encoder",
            return_value=mock_enc,
        ), patch(
            "lcats.analysis.scene_analysis.annotate_segments_with_semantics",
            return_value=[],
        ):
            processor = story_processors.make_annotated_segment_extractor(
                client,
                segment_model="model-seg",
                semantic_model="model-sem",
            )
            result = processor(dict(_MINIMAL_STORY))

        self.assertEqual(result["models"]["segment_model"], "model-seg")
        self.assertEqual(result["models"]["semantic_model"], "model-sem")

    def test_segmentation_keys_present(self):
        result = self._run_processor()
        segmentation = result["segmentation"]
        for key in ("parsing_error", "extraction_error", "alignment_error"):
            with self.subTest(key=key):
                self.assertIn(key, segmentation)

    # -- Title / authors --

    def test_title_from_name(self):
        result = self._run_processor()
        self.assertEqual(result["title"], "A Short Tale")

    def test_missing_name_gives_untitled(self):
        result = self._run_processor(data=dict(_UNTITLED_STORY))
        self.assertEqual(result["title"], "<Untitled>")

    def test_authors_extracted(self):
        result = self._run_processor()
        self.assertEqual(result["authors"], ["Alice"])

    # -- Body metrics --

    def test_body_length_chars_matches(self):
        result = self._run_processor()
        self.assertEqual(result["body_length_chars"], len(_MINIMAL_STORY["body"]))

    def test_body_length_words_positive(self):
        result = self._run_processor()
        self.assertGreater(result["body_length_words"], 0)

    def test_body_length_tokens_is_int(self):
        result = self._run_processor()
        self.assertIsInstance(result["body_length_tokens"], int)

    def test_body_length_paragraphs_is_int(self):
        result = self._run_processor()
        self.assertIsInstance(result["body_length_paragraphs"], int)

    def test_top_keywords_is_list(self):
        result = self._run_processor()
        self.assertIsInstance(result["top_keywords"], list)

    # -- Segments --

    def test_segments_defaults_to_empty_list(self):
        result = self._run_processor()
        self.assertEqual(result["segments"], [])

    def test_annotated_segments_stored(self):
        annotated = [{"segment_id": 1, "segment_eval": {"label": "narrative_scene"}}]
        result = self._run_processor(annotated=annotated)
        self.assertEqual(result["segments"], annotated)

    # -- Segmentation errors propagated --

    def test_parsing_error_propagated(self):
        result = self._run_processor(seg_errors={"parsing_error": "bad JSON"})
        self.assertEqual(result["segmentation"]["parsing_error"], "bad JSON")

    def test_extraction_error_propagated(self):
        result = self._run_processor(seg_errors={"extraction_error": "LLM timeout"})
        self.assertEqual(result["segmentation"]["extraction_error"], "LLM timeout")

    def test_alignment_error_propagated(self):
        result = self._run_processor(seg_errors={"alignment_error": "offset mismatch"})
        self.assertEqual(result["segmentation"]["alignment_error"], "offset mismatch")

    def test_validation_report_included_when_flag_true(self):
        report = {"score": 0.9}
        result = self._run_processor(
            seg_errors={"validation_report": report}, include_validation=True
        )
        self.assertEqual(result["segmentation"]["validation_report"], report)

    def test_validation_report_absent_when_flag_false(self):
        """When include_validation=False, validation_report stays None."""
        report = {"score": 0.9}
        result = self._run_processor(
            seg_errors={"validation_report": report}, include_validation=False
        )
        self.assertIsNone(result["segmentation"]["validation_report"])

    # -- Exception handling --

    def test_exception_captured_in_error_key(self):
        result = self._run_processor(raise_in_annotate=RuntimeError("boom"))
        self.assertIn("error", result)
        self.assertIn("RuntimeError", result["error"])
        self.assertIn("boom", result["error"])

    def test_partial_results_preserved_on_exception(self):
        """When annotate raises, the other fields should still be populated."""
        result = self._run_processor(raise_in_annotate=ValueError("oops"))
        self.assertEqual(result["title"], "A Short Tale")
        self.assertIn("error", result)

    def test_no_error_key_when_successful(self):
        result = self._run_processor()
        self.assertNotIn("error", result)


if __name__ == "__main__":
    unittest.main()
