"""Tests for experimental model-comparison diagnostic helpers."""

from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest

_MODEL_COMPARISON = (
    pathlib.Path(__file__).resolve().parents[2] / "experimental" / "model_comparison"
)
sys.path.insert(0, str(_MODEL_COMPARISON))

from common import harness  # noqa: E402
import entity_diff  # noqa: E402
from lcats.llm import backend as llm_backend  # noqa: E402
from lcats.llm import fake_backend  # noqa: E402
from ollama_gpt_oss_20b import entity_shape_adapter  # noqa: E402


class _NoToolCallBackend:
    def complete(self, **kwargs):
        raise llm_backend.NoToolCallError(
            "no tool call",
            input_tokens=10,
            output_tokens=20,
            raw_content='{"entities": ["old machine"]}',
        )


class TestModelComparisonDiagnostics(unittest.TestCase):
    def test_entity_extraction_result_captures_minimal_entity_list(self):
        backend = fake_backend.FakeBackend(
            tool_result={
                "entities": [
                    {
                        "entity_id": "e1",
                        "canonical_name": "The Machine",
                        "entity_type": "machine_or_artifact",
                    },
                    {
                        "name": "The Ghost",
                        "type": "abstract_force",
                    },
                    "loose string entity",
                ]
            },
            input_tokens=10,
            output_tokens=20,
        )
        segment_path = pathlib.Path(self.id()).with_suffix(".json")
        segment_path.write_text(
            (
                "{\n"
                '  "source_story": "fixture",\n'
                '  "segment_id": 1,\n'
                '  "segment_type": "dramatic_scene",\n'
                '  "body": "The old machine hummed."\n'
                "}\n"
            ),
            encoding="utf-8",
        )
        self.addCleanup(segment_path.unlink)

        result = harness.run_entity_extraction(
            candidate="test",
            backend_kind="fake",
            backend=backend,
            model="fake-1.0",
            segment_path=segment_path,
        )

        self.assertTrue(result.success)
        self.assertEqual(result.entity_count, 3)
        self.assertEqual(
            result.entities,
            [
                {
                    "canonical_name": "The Machine",
                    "entity_type": "machine_or_artifact",
                    "entity_id": "e1",
                },
                {
                    "canonical_name": "The Ghost",
                    "entity_type": "abstract_force",
                },
                {
                    "canonical_name": "loose string entity",
                    "entity_type": None,
                },
            ],
        )

    def test_entity_diff_reports_shared_unique_and_missing_entities(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            opus_path = root / "opus.json"
            qwen_path = root / "qwen.json"
            opus_path.write_text(
                (
                    "{\n"
                    '  "candidate": "anthropic_opus",\n'
                    '  "entities": [\n'
                    '    {"canonical_name": "The Machine", "entity_type": "artifact"},\n'
                    '    {"canonical_name": "Professor X", "entity_type": "person"}\n'
                    "  ]\n"
                    "}\n"
                ),
                encoding="utf-8",
            )
            qwen_path.write_text(
                (
                    "{\n"
                    '  "candidate": "ollama_qwen3_8b",\n'
                    '  "entities": [\n'
                    '    {"canonical_name": "the   machine", "entity_type": "device"},\n'
                    '    {"canonical_name": "THE MACHINE", "entity_type": ""},\n'
                    '    {"canonical_name": "Laboratory", "entity_type": "place"}\n'
                    "  ]\n"
                    "}\n"
                ),
                encoding="utf-8",
            )

            candidates = [
                entity_diff.load_candidate_entities(opus_path),
                entity_diff.load_candidate_entities(qwen_path),
            ]
            report = entity_diff.build_report(candidates)

        self.assertRegex(report, r"(?i:the machine) \[(artifact|device)\]")
        self.assertIn("Professor X [person]", report)
        self.assertIn("Laboratory [place]", report)
        self.assertIn("### anthropic_opus", report)
        self.assertIn("### ollama_qwen3_8b", report)

    def test_entity_diff_excludes_failed_and_stale_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            opus_path = root / "opus.json"
            qwen_path = root / "qwen.json"
            failed_path = root / "failed.json"
            stale_path = root / "stale.json"
            opus_path.write_text(
                (
                    "{\n"
                    '  "candidate": "anthropic_opus",\n'
                    '  "entities": [\n'
                    '    {"canonical_name": "The Machine", "entity_type": "artifact"},\n'
                    '    {"canonical_name": "Professor X", "entity_type": "person"}\n'
                    "  ]\n"
                    "}\n"
                ),
                encoding="utf-8",
            )
            qwen_path.write_text(
                (
                    "{\n"
                    '  "candidate": "ollama_qwen3_8b",\n'
                    '  "entities": [\n'
                    '    {"canonical_name": "the machine", "entity_type": "artifact"}\n'
                    "  ]\n"
                    "}\n"
                ),
                encoding="utf-8",
            )
            failed_path.write_text(
                (
                    "{\n"
                    '  "candidate": "ollama_qwen3_30b_a3b",\n'
                    '  "success": false,\n'
                    '  "error_type": "truncated_output",\n'
                    '  "entities": [\n'
                    '    {"canonical_name": "Should Not Compare", "entity_type": "artifact"}\n'
                    "  ]\n"
                    "}\n"
                ),
                encoding="utf-8",
            )
            stale_path.write_text(
                (
                    "{\n"
                    '  "candidate": "anthropic_haiku",\n'
                    '  "success": true,\n'
                    '  "entity_count": 22\n'
                    "}\n"
                ),
                encoding="utf-8",
            )

            candidates = [
                entity_diff.load_candidate_entities(opus_path),
                entity_diff.load_candidate_entities(qwen_path),
                entity_diff.load_candidate_entities(failed_path),
                entity_diff.load_candidate_entities(stale_path),
            ]
            report = entity_diff.build_report(candidates)

        self.assertIn("## Not Comparable", report)
        self.assertIn("ollama_qwen3_30b_a3b: not comparable: truncated_output", report)
        self.assertIn(
            "anthropic_haiku: stale result: rerun benchmark to populate `entities`",
            report,
        )
        self.assertNotIn("### ollama_qwen3_30b_a3b", report)
        self.assertNotIn("### anthropic_haiku", report)
        self.assertIn("Professor X [person]", report)
        self.assertNotIn("Should Not Compare", report)

    def test_segment_anchor_diagnostics_reads_pre_alignment_wrapper(self):
        parsed_output = {
            "segments": [
                {
                    "segment_id": 1,
                    "segment_type": "dramatic_scene",
                    "start_par_id": 1,
                    "end_par_id": 1,
                    "start_exact": "The old machine",
                    "end_exact": "not in story",
                    "summary": "A machine appears.",
                }
            ]
        }

        diagnostics = harness.summarize_segment_anchor_diagnostics(
            parsed_output, "The old machine hummed."
        )

        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(diagnostics[0]["segment_id"], 1)
        self.assertEqual(diagnostics[0]["start_exact"], "The old machine")
        self.assertTrue(diagnostics[0]["start_exact_found"])
        self.assertEqual(diagnostics[0]["end_exact"], "not in story")
        self.assertFalse(diagnostics[0]["end_exact_found"])

    def test_entity_grounding_reports_raw_and_grounded_counts(self):
        backend = fake_backend.FakeBackend(
            tool_result={
                "entities": [
                    {
                        "entity_id": "e1",
                        "canonical_name": "the machine",
                        "entity_type": "machine_or_artifact",
                        "mentions": [
                            {
                                "mention_id": "m1",
                                "text": "the machine",
                                "quote": "old machine",
                            }
                        ],
                    },
                    {
                        "entity_id": "e2",
                        "canonical_name": "the ghost",
                        "entity_type": "abstract_force",
                        "mentions": [
                            {
                                "mention_id": "m2",
                                "text": "ghost",
                                "quote": "not in the segment",
                            }
                        ],
                    },
                ]
            },
            input_tokens=10,
            output_tokens=20,
        )
        segment_path = pathlib.Path(self.id()).with_suffix(".json")
        segment_path.write_text(
            (
                "{\n"
                '  "source_story": "fixture",\n'
                '  "segment_id": 1,\n'
                '  "segment_type": "dramatic_scene",\n'
                '  "body": "The old machine hummed."\n'
                "}\n"
            ),
            encoding="utf-8",
        )
        self.addCleanup(segment_path.unlink)

        result = harness.run_entity_extraction_with_grounding(
            candidate="test",
            backend_kind="fake",
            backend=backend,
            model="fake-1.0",
            segment_path=segment_path,
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["raw_entity_count"], 2)
        self.assertEqual(result["grounded_entity_count"], 1)
        self.assertEqual(result["grounded_mention_count"], 1)
        self.assertEqual(result["input_tokens"], 10)
        self.assertEqual(result["output_tokens"], 20)

    def test_entity_grounding_applies_prompt_suffix_and_adapter(self):
        backend = fake_backend.FakeBackend(
            tool_result={
                "entities": [
                    {
                        "name": "the machine",
                        "mentions": ["old machine", "not in the segment"],
                    }
                ]
            },
            input_tokens=10,
            output_tokens=20,
        )
        segment_path = pathlib.Path(self.id()).with_suffix(".json")
        segment_path.write_text(
            (
                "{\n"
                '  "source_story": "fixture",\n'
                '  "segment_id": 1,\n'
                '  "segment_type": "dramatic_scene",\n'
                '  "body": "The old machine hummed."\n'
                "}\n"
            ),
            encoding="utf-8",
        )
        self.addCleanup(segment_path.unlink)

        result = harness.run_entity_extraction_with_grounding(
            candidate="test",
            backend_kind="fake",
            backend=backend,
            model="fake-1.0",
            segment_path=segment_path,
            system_prompt_suffix="\nSUFFIX",
            tool_result_adapter=(
                entity_shape_adapter.normalize_gpt_oss_entity_tool_result
            ),
        )

        self.assertTrue(backend.calls[0]["system"].endswith("\nSUFFIX"))
        self.assertTrue(result["success"])
        self.assertTrue(result["production_grounded_success"])
        self.assertEqual(result["raw_entity_count"], 1)
        self.assertEqual(result["grounded_entity_count"], 1)
        self.assertEqual(result["grounded_mention_count"], 1)
        self.assertEqual(result["adapter_diagnostics"]["converted_string_mentions"], 1)
        self.assertEqual(
            result["adapter_diagnostics"]["dropped_string_mentions"][0]["reason"],
            "ungrounded_string_mention:not in the segment",
        )

    def test_gpt_oss_entity_adapter_preserves_already_shaped_mentions(self):
        tool_result = {
            "entities": [
                {
                    "entity_id": "e1",
                    "canonical_name": "the machine",
                    "entity_type": "machine_or_artifact",
                    "mentions": [
                        {
                            "mention_id": "m1",
                            "text": "the machine",
                            "quote": "old machine",
                        }
                    ],
                }
            ]
        }

        normalized, diagnostics = (
            entity_shape_adapter.normalize_gpt_oss_entity_tool_result(
                tool_result, "The old machine hummed."
            )
        )

        self.assertEqual(normalized, tool_result)
        self.assertFalse(diagnostics["adapter_applied"])

    def test_gpt_oss_entity_adapter_repairs_grounded_dict_mentions(self):
        tool_result = {
            "entities": [
                {
                    "entity": "the machine",
                    "mentions": [
                        {"surface": "old machine"},
                        {"text": "not in the segment"},
                    ],
                }
            ]
        }

        normalized, diagnostics = (
            entity_shape_adapter.normalize_gpt_oss_entity_tool_result(
                tool_result, "The old machine hummed."
            )
        )

        mentions = normalized["entities"][0]["mentions"]
        self.assertEqual(normalized["entities"][0]["canonical_name"], "the machine")
        self.assertEqual(mentions[0]["quote"], "old machine")
        self.assertEqual(mentions[0]["text"], "old machine")
        self.assertIn("mention_id", mentions[0])
        self.assertNotIn("quote", mentions[1])
        self.assertEqual(diagnostics["changed_dict_mentions"], 2)
        self.assertEqual(diagnostics["repaired_dict_mentions"], 1)
        self.assertEqual(
            diagnostics["unrepaired_dict_mentions"][0]["reason"],
            "dict_mention_missing_grounded_quote",
        )

    def test_gpt_oss_entity_adapter_repairs_grounded_string_entities(self):
        tool_result = {"entities": ["old machine", "missing ghost"]}

        normalized, diagnostics = (
            entity_shape_adapter.normalize_gpt_oss_entity_tool_result(
                tool_result, "The old machine hummed."
            )
        )

        self.assertEqual(len(normalized["entities"]), 1)
        self.assertEqual(normalized["entities"][0]["canonical_name"], "old machine")
        self.assertEqual(
            normalized["entities"][0]["mentions"][0]["quote"], "old machine"
        )
        self.assertEqual(diagnostics["converted_string_entities"], 1)
        self.assertEqual(
            diagnostics["dropped_string_entities"][0]["reason"],
            "ungrounded_string_mention:missing ghost",
        )

    def test_entity_grounding_can_fallback_to_no_tool_call_json_content(self):
        segment_path = pathlib.Path(self.id()).with_suffix(".json")
        segment_path.write_text(
            (
                "{\n"
                '  "source_story": "fixture",\n'
                '  "segment_id": 1,\n'
                '  "segment_type": "dramatic_scene",\n'
                '  "body": "The old machine hummed."\n'
                "}\n"
            ),
            encoding="utf-8",
        )
        self.addCleanup(segment_path.unlink)

        result = harness.run_entity_extraction_with_grounding(
            candidate="test",
            backend_kind="fake",
            backend=_NoToolCallBackend(),
            model="fake-1.0",
            segment_path=segment_path,
            tool_result_adapter=(
                entity_shape_adapter.normalize_gpt_oss_entity_tool_result
            ),
            allow_no_tool_call_json_fallback=True,
        )

        self.assertFalse(result["tool_call_success"])
        self.assertTrue(result["json_content_fallback_applied"])
        self.assertTrue(result["production_grounded_success"])
        self.assertEqual(result["grounded_entity_count"], 1)


if __name__ == "__main__":
    unittest.main()
