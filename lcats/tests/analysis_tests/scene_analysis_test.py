"""Unit tests for lcats.analysis.scene_analysis."""

import unittest
from unittest.mock import MagicMock, patch

from parameterized import parameterized

from lcats.analysis import scene_analysis


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_extractor(return_value=None):
    """Return a mock JSONPromptExtractor that returns `return_value` when called."""
    mock = MagicMock()
    mock.return_value = return_value or {}
    return mock


# ---------------------------------------------------------------------------
# Tests: normalize_preview
# ---------------------------------------------------------------------------


class TestNormalizePreview(unittest.TestCase):
    """Tests for normalize_preview."""

    def test_empty_string_returns_empty(self):
        self.assertEqual(scene_analysis.normalize_preview(""), "")

    def test_single_newline_becomes_space(self):
        result = scene_analysis.normalize_preview("hello\nworld")
        self.assertEqual(result, "hello world")

    def test_crlf_normalized_to_space(self):
        result = scene_analysis.normalize_preview("hello\r\nworld")
        self.assertEqual(result, "hello world")

    def test_cr_normalized_to_space(self):
        result = scene_analysis.normalize_preview("hello\rworld")
        self.assertEqual(result, "hello world")

    def test_double_newline_becomes_newline(self):
        result = scene_analysis.normalize_preview("para1\n\npara2")
        self.assertIn("\n", result)
        self.assertNotIn("\n\n", result)

    def test_multiple_spaces_collapsed(self):
        result = scene_analysis.normalize_preview("hello   world")
        self.assertEqual(result, "hello world")

    def test_tabs_collapsed(self):
        result = scene_analysis.normalize_preview("hello\t\tworld")
        self.assertEqual(result, "hello world")

    def test_leading_trailing_whitespace_stripped(self):
        result = scene_analysis.normalize_preview("  hello world  ")
        self.assertEqual(result, "hello world")

    def test_plain_text_unchanged(self):
        result = scene_analysis.normalize_preview("Hello world.")
        self.assertEqual(result, "Hello world.")


# ---------------------------------------------------------------------------
# Tests: normalize_label
# ---------------------------------------------------------------------------


class TestNormalizeLabel(unittest.TestCase):
    """Tests for normalize_label."""

    @parameterized.expand(
        [
            ("dramatic_scene", "dramatic_scene"),
            ("dramatic_sequel", "dramatic_sequel"),
            ("narrative_scene", "narrative_scene"),
            ("other", "other"),
        ]
    )
    def test_allowed_labels_pass_through(self, name, label):
        self.assertEqual(scene_analysis.normalize_label(label), label)

    @parameterized.expand(
        [
            ("capitalized", "Dramatic Scene"),
            ("typo", "dramatic-scene"),
            ("empty", ""),
            ("random", "unknown_type"),
            ("none_string", "None"),
        ]
    )
    def test_disallowed_labels_become_unknown(self, name, label):
        self.assertEqual(scene_analysis.normalize_label(label), "unknown")


# ---------------------------------------------------------------------------
# Tests: summarize_type_agreement
# ---------------------------------------------------------------------------


class TestSummarizeTypeAgreement(unittest.TestCase):
    """Tests for summarize_type_agreement."""

    def test_empty_segments_returns_zero_counts(self):
        result = scene_analysis.summarize_type_agreement({"segments": []})
        self.assertEqual(result["segments_total"], 0)
        self.assertEqual(result["agreements"], 0)
        self.assertEqual(result["disagreements"], 0)
        self.assertAlmostEqual(result["agreement_rate"], 0.0)

    def test_missing_segments_key_treated_as_empty(self):
        result = scene_analysis.summarize_type_agreement({})
        self.assertEqual(result["segments_total"], 0)

    def test_non_list_segments_treated_as_empty(self):
        result = scene_analysis.summarize_type_agreement({"segments": "bad"})
        self.assertEqual(result["segments_total"], 0)

    def test_agreement_when_types_match(self):
        story_data = {
            "segments": [
                {
                    "segment_type": "dramatic_scene",
                    "whole_story_type": "dramatic_scene",
                    "per_scene_type": "dramatic_scene",
                }
            ]
        }
        result = scene_analysis.summarize_type_agreement(story_data)
        self.assertEqual(result["agreements"], 1)
        self.assertEqual(result["disagreements"], 0)
        self.assertAlmostEqual(result["agreement_rate"], 1.0)

    def test_disagreement_when_types_differ(self):
        story_data = {
            "segments": [
                {
                    "whole_story_type": "dramatic_scene",
                    "per_scene_type": "narrative_scene",
                }
            ]
        }
        result = scene_analysis.summarize_type_agreement(story_data)
        self.assertEqual(result["agreements"], 0)
        self.assertEqual(result["disagreements"], 1)

    def test_by_extractor_and_auditor_counts(self):
        story_data = {
            "segments": [
                {
                    "whole_story_type": "dramatic_scene",
                    "per_scene_type": "dramatic_scene",
                },
                {
                    "whole_story_type": "narrative_scene",
                    "per_scene_type": "dramatic_scene",
                },
            ]
        }
        result = scene_analysis.summarize_type_agreement(story_data)
        self.assertEqual(result["by_extractor"]["dramatic_scene"], 1)
        self.assertEqual(result["by_extractor"]["narrative_scene"], 1)
        self.assertEqual(result["by_auditor"]["dramatic_scene"], 2)

    def test_fallback_to_segment_type_and_segment_eval_label(self):
        story_data = {
            "segments": [
                {
                    "segment_type": "dramatic_sequel",
                    "segment_eval": {"label": "dramatic_sequel"},
                }
            ]
        }
        result = scene_analysis.summarize_type_agreement(story_data)
        self.assertEqual(result["agreements"], 1)

    def test_unknown_labels_bucketed_as_unknown(self):
        story_data = {
            "segments": [
                {"whole_story_type": "BAD_TYPE", "per_scene_type": "dramatic_scene"}
            ]
        }
        result = scene_analysis.summarize_type_agreement(story_data)
        self.assertEqual(result["by_extractor"]["unknown"], 1)

    def test_agreement_rate_calculation(self):
        story_data = {
            "segments": [
                {
                    "whole_story_type": "dramatic_scene",
                    "per_scene_type": "dramatic_scene",
                },
                {"whole_story_type": "narrative_scene", "per_scene_type": "other"},
                {"whole_story_type": "other", "per_scene_type": "other"},
            ]
        }
        result = scene_analysis.summarize_type_agreement(story_data)
        self.assertEqual(result["segments_total"], 3)
        self.assertEqual(result["agreements"], 2)
        self.assertAlmostEqual(result["agreement_rate"], 2 / 3)


# ---------------------------------------------------------------------------
# Tests: make_segment_extractor
# ---------------------------------------------------------------------------


class TestMakeSegmentExtractor(unittest.TestCase):
    """Tests for make_segment_extractor."""

    def test_returns_json_prompt_extractor(self):
        from lcats.analysis import llm_extractor

        client = MagicMock()
        extractor = scene_analysis.make_segment_extractor(client)
        self.assertIsInstance(extractor, llm_extractor.JSONPromptExtractor)

    def test_output_key_is_segments(self):
        extractor = scene_analysis.make_segment_extractor(MagicMock())
        self.assertEqual(extractor.output_key, "segments")

    def test_default_model_is_gpt4o(self):
        extractor = scene_analysis.make_segment_extractor(MagicMock())
        self.assertEqual(extractor.default_model, "gpt-4o")

    def test_text_indexer_is_set(self):
        from lcats.analysis import text_segmenter

        extractor = scene_analysis.make_segment_extractor(MagicMock())
        self.assertIs(extractor.text_indexer, text_segmenter.paragraph_text_indexer)

    def test_result_aligner_is_set(self):
        from lcats.analysis import text_segmenter

        extractor = scene_analysis.make_segment_extractor(MagicMock())
        self.assertIs(extractor.result_aligner, text_segmenter.segments_result_aligner)

    def test_result_validator_is_set(self):
        from lcats.analysis import text_segmenter

        extractor = scene_analysis.make_segment_extractor(MagicMock())
        self.assertIs(extractor.result_validator, text_segmenter.segments_auditor)


# ---------------------------------------------------------------------------
# Tests: make_semantics_extractor
# ---------------------------------------------------------------------------


class TestMakeSemanticsExtractor(unittest.TestCase):
    """Tests for make_semantics_extractor."""

    def test_returns_json_prompt_extractor(self):
        from lcats.analysis import llm_extractor

        client = MagicMock()
        extractor = scene_analysis.make_semantics_extractor(client)
        self.assertIsInstance(extractor, llm_extractor.JSONPromptExtractor)

    def test_output_key_is_judgment(self):
        extractor = scene_analysis.make_semantics_extractor(MagicMock())
        self.assertEqual(extractor.output_key, "judgment")

    def test_text_indexer_is_none(self):
        extractor = scene_analysis.make_semantics_extractor(MagicMock())
        self.assertIsNone(extractor.text_indexer)

    def test_result_aligner_is_none(self):
        extractor = scene_analysis.make_semantics_extractor(MagicMock())
        self.assertIsNone(extractor.result_aligner)

    def test_default_model_is_gpt4o(self):
        extractor = scene_analysis.make_semantics_extractor(MagicMock())
        self.assertEqual(extractor.default_model, "gpt-4o")


# ---------------------------------------------------------------------------
# Tests: evaluate_segment_semantics
# ---------------------------------------------------------------------------


class TestEvaluateSegmentSemantics(unittest.TestCase):
    """Tests for evaluate_segment_semantics."""

    def test_calls_extractor_with_segment_text(self):
        mock_extractor = MagicMock(
            return_value={"extracted_output": {"label": "dramatic_scene"}}
        )
        result = scene_analysis.evaluate_segment_semantics(mock_extractor, "some text")
        mock_extractor.assert_called_once_with("some text", model_name=None)
        self.assertEqual(result, {"extracted_output": {"label": "dramatic_scene"}})

    def test_passes_model_name_override(self):
        mock_extractor = MagicMock(return_value={})
        scene_analysis.evaluate_segment_semantics(
            mock_extractor, "text", model_name="gpt-3.5"
        )
        mock_extractor.assert_called_once_with("text", model_name="gpt-3.5")

    def test_returns_extractor_result(self):
        expected = {"extracted_output": {"label": "narrative_scene", "confidence": 0.9}}
        mock_extractor = MagicMock(return_value=expected)
        result = scene_analysis.evaluate_segment_semantics(mock_extractor, "text")
        self.assertEqual(result, expected)


# ---------------------------------------------------------------------------
# Tests: annotate_segments_with_semantics
# ---------------------------------------------------------------------------


class TestAnnotateSegmentsWithSemantics(unittest.TestCase):
    """Tests for annotate_segments_with_semantics."""

    def setUp(self):
        self.story_text = "Hello world. This is a test story."

    def test_annotates_valid_segment(self):
        segments = [{"segment_id": 1, "start_char": 0, "end_char": 12}]
        mock_extractor = MagicMock(
            return_value={"extracted_output": {"label": "narrative_scene"}}
        )
        result = scene_analysis.annotate_segments_with_semantics(
            self.story_text, segments, mock_extractor
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["segment_eval"], {"label": "narrative_scene"})
        self.assertEqual(result[0]["segment_text"], "Hello world.")

    def test_preserves_original_segment_fields(self):
        segments = [{"segment_id": 42, "start_char": 0, "end_char": 5, "summary": "hi"}]
        mock_extractor = MagicMock(return_value={"extracted_output": None})
        result = scene_analysis.annotate_segments_with_semantics(
            self.story_text, segments, mock_extractor
        )
        self.assertEqual(result[0]["segment_id"], 42)
        self.assertEqual(result[0]["summary"], "hi")

    def test_does_not_mutate_original_segment(self):
        seg = {"segment_id": 1, "start_char": 0, "end_char": 5}
        mock_extractor = MagicMock(return_value={"extracted_output": None})
        scene_analysis.annotate_segments_with_semantics(
            self.story_text, [seg], mock_extractor
        )
        self.assertNotIn("segment_text", seg)
        self.assertNotIn("segment_eval", seg)

    def test_invalid_offsets_raises_value_error(self):
        segments = [{"segment_id": 1, "start_char": 10, "end_char": 5}]
        mock_extractor = MagicMock()
        with self.assertRaises(ValueError):
            scene_analysis.annotate_segments_with_semantics(
                self.story_text, segments, mock_extractor
            )

    def test_missing_offsets_raises_value_error(self):
        segments = [{"segment_id": 1}]
        mock_extractor = MagicMock()
        with self.assertRaises(ValueError):
            scene_analysis.annotate_segments_with_semantics(
                self.story_text, segments, mock_extractor
            )

    def test_out_of_bounds_end_char_raises_value_error(self):
        segments = [{"segment_id": 1, "start_char": 0, "end_char": 9999}]
        mock_extractor = MagicMock()
        with self.assertRaises(ValueError):
            scene_analysis.annotate_segments_with_semantics(
                self.story_text, segments, mock_extractor
            )

    def test_multiple_segments_all_annotated(self):
        story = "ABCDEFGHIJ"
        segments = [
            {"segment_id": 1, "start_char": 0, "end_char": 5},
            {"segment_id": 2, "start_char": 5, "end_char": 10},
        ]
        mock_extractor = MagicMock(
            return_value={"extracted_output": {"label": "other"}}
        )
        result = scene_analysis.annotate_segments_with_semantics(
            story, segments, mock_extractor
        )
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["segment_text"], "ABCDE")
        self.assertEqual(result[1]["segment_text"], "FGHIJ")

    def test_passes_model_name_to_extractor(self):
        segments = [{"segment_id": 1, "start_char": 0, "end_char": 5}]
        mock_extractor = MagicMock(return_value={"extracted_output": None})
        scene_analysis.annotate_segments_with_semantics(
            self.story_text, segments, mock_extractor, model_name="gpt-3.5"
        )
        mock_extractor.assert_called_once_with("Hello", model_name="gpt-3.5")

    def test_segment_eval_none_when_extracted_output_missing(self):
        segments = [{"segment_id": 1, "start_char": 0, "end_char": 5}]
        mock_extractor = MagicMock(return_value={})
        result = scene_analysis.annotate_segments_with_semantics(
            self.story_text, segments, mock_extractor
        )
        self.assertIsNone(result[0]["segment_eval"])


# ---------------------------------------------------------------------------
# Tests: display_segments
# ---------------------------------------------------------------------------


class TestDisplaySegments(unittest.TestCase):
    """Tests for display_segments (smoke tests; validates no crash and output)."""

    STORY = "Once upon a time in a land far away. The hero went on a quest."

    def _capture_output(self, func, *args, **kwargs):
        """Capture stdout from a function call."""
        with patch("builtins.print") as mock_print:
            func(*args, **kwargs)
            return mock_print

    def test_empty_scenes_no_crash(self):
        """display_segments with empty list should not crash."""
        scene_analysis.display_segments(self.STORY, [])

    def test_minimal_segment_no_crash(self):
        """display_segments with a minimal segment dict should not crash."""
        seg = {
            "segment_id": 1,
            "segment_type": "narrative_scene",
            "confidence": 0.8,
            "reason": "test reason",
            "summary": "test summary",
        }
        scene_analysis.display_segments(self.STORY, [seg])

    def test_segment_with_valid_char_offsets(self):
        """Segment with valid start_char/end_char shows preview."""
        seg = {
            "segment_id": 1,
            "segment_type": "narrative_scene",
            "confidence": 0.9,
            "reason": "time/place unified",
            "summary": "Opening scene",
            "start_char": 0,
            "end_char": 36,
            "start_exact": "Once upon a time",
            "end_exact": "far away.",
            "start_prefix": "",
            "end_suffix": " The",
            "start_par_id": 1,
            "end_par_id": 1,
            "cohesion": {"time": "past", "place": "far away", "characters": ["hero"]},
            "gacd": None,
            "erac": None,
        }
        mock_print = self._capture_output(
            scene_analysis.display_segments, self.STORY, [seg]
        )
        # Should have printed something
        self.assertTrue(mock_print.called)

    def test_segment_with_gacd(self):
        """Segment with gacd dict should print GACD line."""
        seg = {
            "segment_id": 1,
            "segment_type": "dramatic_scene",
            "confidence": 0.9,
            "reason": "GACD present",
            "summary": "Hero fights dragon",
            "gacd": {
                "goal": "slay dragon",
                "action": "attacks",
                "conflict": "dragon fights back",
                "outcome": "Disaster",
            },
            "erac": None,
        }
        with patch("builtins.print") as mock_print:
            scene_analysis.display_segments(self.STORY, [seg])
            calls = [str(c) for c in mock_print.call_args_list]
            self.assertTrue(any("GACD" in c for c in calls))

    def test_segment_with_erac(self):
        """Segment with erac dict should print ERAC line."""
        seg = {
            "segment_id": 2,
            "segment_type": "dramatic_sequel",
            "confidence": 0.7,
            "reason": "ERAC present",
            "summary": "Hero reflects",
            "gacd": None,
            "erac": {
                "emotion": "devastated",
                "reason": "considers options",
                "anticipation": "expects failure",
                "choice": "try again",
            },
        }
        with patch("builtins.print") as mock_print:
            scene_analysis.display_segments(self.STORY, [seg])
            calls = [str(c) for c in mock_print.call_args_list]
            self.assertTrue(any("ERAC" in c for c in calls))

    def test_segment_derives_span_from_anchors(self):
        """When start_char/end_char are invalid, derives from start_exact/end_exact."""
        story = "The quick brown fox jumps over the lazy dog."
        seg = {
            "segment_id": 1,
            "segment_type": "narrative_scene",
            "confidence": 0.5,
            "reason": "test",
            "summary": "fox story",
            "start_char": None,
            "end_char": None,
            "start_exact": "The quick brown fox",
            "end_exact": "lazy dog.",
        }
        # Should not raise
        scene_analysis.display_segments(story, [seg])

    def test_segment_with_invalid_anchors_fallback(self):
        """When anchors are not found in story, partial span fallback used."""
        story = "Something completely different."
        seg = {
            "segment_id": 1,
            "segment_type": "other",
            "confidence": 0.1,
            "reason": "test",
            "summary": "test",
            "start_char": -1,
            "end_char": -1,
            "start_exact": "NOT IN STORY AT ALL XYZ",
            "end_exact": "ALSO NOT IN STORY",
        }
        scene_analysis.display_segments(story, [seg])


# ---------------------------------------------------------------------------
# Tests: display_annotated_segment / display_annotated_segments
# ---------------------------------------------------------------------------


class TestDisplayAnnotatedSegment(unittest.TestCase):
    """Tests for display_annotated_segment and display_annotated_segments."""

    def _base_segment(self, **overrides):
        seg = {
            "segment_id": 1,
            "segment_type": "narrative_scene",
            "confidence": 0.8,
            "reason": "unified time/place",
            "summary": "Hero walks",
            "segment_text": "The hero walked slowly.",
            "segment_eval": None,
        }
        seg.update(overrides)
        return seg

    def test_no_crash_minimal_segment(self):
        scene_analysis.display_annotated_segment(self._base_segment())

    def test_matching_types_print_segment_id(self):
        seg = self._base_segment(
            segment_eval={
                "label": "narrative_scene",
                "confidence": 0.8,
                "reason": "ok",
                "checks": {},
                "evidence": {},
            }
        )
        with patch("builtins.print") as mock_print:
            scene_analysis.display_annotated_segment(seg)
            calls = " ".join(str(c) for c in mock_print.call_args_list)
            self.assertIn("Segment ID", calls)

    def test_mismatched_types_print_mismatch(self):
        seg = self._base_segment(
            segment_eval={
                "label": "dramatic_scene",
                "confidence": 0.9,
                "reason": "ok",
                "checks": {},
                "evidence": {},
            }
        )
        with patch("builtins.print") as mock_print:
            scene_analysis.display_annotated_segment(seg)
            calls = " ".join(str(c) for c in mock_print.call_args_list)
            self.assertIn("MISMATCH", calls)

    def test_with_cohesion(self):
        seg = self._base_segment(
            cohesion={"time": "morning", "place": "forest", "characters": ["hero"]}
        )
        # should not crash
        scene_analysis.display_annotated_segment(seg)

    def test_with_gacd(self):
        seg = self._base_segment(
            gacd={
                "goal": "escape",
                "action": "runs",
                "conflict": "pursuer",
                "outcome": "Success",
            }
        )
        with patch("builtins.print") as mock_print:
            scene_analysis.display_annotated_segment(seg)
            calls = " ".join(str(c) for c in mock_print.call_args_list)
            self.assertIn("GACD", calls)

    def test_with_erac(self):
        seg = self._base_segment(
            erac={
                "emotion": "relief",
                "reason": "thinks",
                "anticipation": "hopes",
                "choice": "stays",
            }
        )
        with patch("builtins.print") as mock_print:
            scene_analysis.display_annotated_segment(seg)
            calls = " ".join(str(c) for c in mock_print.call_args_list)
            self.assertIn("ERAC", calls)

    def test_matching_types_with_populated_checks_and_evidence(self):
        """segment_eval with real checks and evidence data should not crash."""
        seg = self._base_segment(
            segment_eval={
                "label": "narrative_scene",
                "confidence": 0.75,
                "reason": "unified by time and place",
                "checks": {
                    "time_place_unity": True,
                    "gacd": {
                        "has_goal": False,
                        "has_action": False,
                        "has_conflict": False,
                        "outcome": "None",
                    },
                    "erac": {
                        "has_emotion": False,
                        "has_reason": False,
                        "has_anticipation": False,
                        "has_choice": False,
                    },
                },
                "evidence": {
                    "time": "morning",
                    "place": "forest path",
                    "characters": ["hero"],
                    "quotes": {
                        "goal": "",
                        "action": "",
                        "conflict": "",
                        "outcome": "",
                        "emotion": "",
                        "reason": "",
                        "anticipation": "",
                        "choice": "",
                    },
                },
            }
        )
        with patch("builtins.print") as mock_print:
            scene_analysis.display_annotated_segment(seg)
            calls = " ".join(str(c) for c in mock_print.call_args_list)
            self.assertIn("Checks", calls)
            self.assertIn("Evidence", calls)

    def test_display_annotated_segments_calls_each(self):
        segs = [self._base_segment(segment_id=i) for i in range(3)]
        with patch.object(scene_analysis, "display_annotated_segment") as mock_fn:
            scene_analysis.display_annotated_segments(segs)
            self.assertEqual(mock_fn.call_count, 3)

    def test_display_annotated_segments_empty_list(self):
        # Should not crash
        scene_analysis.display_annotated_segments([])


# ---------------------------------------------------------------------------
# Tests: ALLOWED_SCENE_TYPES constant
# ---------------------------------------------------------------------------


class TestAllowedSceneTypes(unittest.TestCase):
    """Tests for the ALLOWED_SCENE_TYPES module-level constant."""

    def test_contains_expected_types(self):
        expected = {"dramatic_scene", "dramatic_sequel", "narrative_scene", "other"}
        self.assertEqual(set(scene_analysis.ALLOWED_SCENE_TYPES), expected)

    def test_is_list(self):
        self.assertIsInstance(scene_analysis.ALLOWED_SCENE_TYPES, list)


# ---------------------------------------------------------------------------
# Tests: prompt constants present
# ---------------------------------------------------------------------------


class TestPromptConstants(unittest.TestCase):
    """Smoke tests to ensure prompt constants are non-empty strings."""

    def test_scene_sequel_system_prompt_nonempty(self):
        self.assertIsInstance(scene_analysis.SCENE_SEQUEL_SYSTEM_PROMPT, str)
        self.assertGreater(len(scene_analysis.SCENE_SEQUEL_SYSTEM_PROMPT), 0)

    def test_scene_sequel_user_prompt_template_nonempty(self):
        self.assertIsInstance(scene_analysis.SCENE_SEQUEL_USER_PROMPT_TEMPLATE, str)
        self.assertGreater(len(scene_analysis.SCENE_SEQUEL_USER_PROMPT_TEMPLATE), 0)

    def test_scene_semantics_system_prompt_nonempty(self):
        self.assertIsInstance(scene_analysis.SCENE_SEMANTICS_SYSTEM_PROMPT, str)
        self.assertGreater(len(scene_analysis.SCENE_SEMANTICS_SYSTEM_PROMPT), 0)

    def test_scene_semantics_user_prompt_template_nonempty(self):
        self.assertIsInstance(scene_analysis.SCENE_SEMANTICS_USER_PROMPT_TEMPLATE, str)
        self.assertGreater(len(scene_analysis.SCENE_SEMANTICS_USER_PROMPT_TEMPLATE), 0)

    def test_user_prompt_template_contains_placeholder(self):
        self.assertIn(
            "{indexed_story_text}", scene_analysis.SCENE_SEQUEL_USER_PROMPT_TEMPLATE
        )

    def test_semantics_user_prompt_template_contains_placeholder(self):
        self.assertIn(
            "{story_text}", scene_analysis.SCENE_SEMANTICS_USER_PROMPT_TEMPLATE
        )


if __name__ == "__main__":
    unittest.main()
