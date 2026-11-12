import json
import tempfile
import unittest
from pathlib import Path

from compare_validation import (
    InputValidationError,
    classify,
    normalize_genre,
    validate_inputs,
)


class ClassificationTests(unittest.TestCase):
    def test_all_categories(self):
        cases = [
            ((["fantasy"], "fantasy", "fantasy"), "all_three_agree"),
            ((["fantasy"], "fantasy", "horror"), "metadata_opus_only"),
            ((["fantasy"], "horror", "fantasy"), "metadata_local_only"),
            ((["fantasy"], "horror", "horror"), "models_agree_metadata_differs"),
            ((["fantasy"], "horror", "mystery"), "all_three_differ"),
            (
                (["western", "adventure"], "western", "adventure"),
                "metadata_multi_label_models_split",
            ),
        ]
        for (metadata, opus, local), expected in cases:
            with self.subTest(expected=expected):
                category, multi_label = classify(metadata, opus, local)
                self.assertEqual(category, expected)
                self.assertEqual(multi_label, len(metadata) > 1)

    def test_aliases_are_canonicalized(self):
        self.assertEqual(normalize_genre(" SF "), "science fiction")
        self.assertEqual(normalize_genre("Humor / satire"), "humor")
        self.assertEqual(
            classify(["SF"], "science-fiction", "SF")[0], "all_three_agree"
        )


def _metadata_record(story_id: str, candidates: list[str]) -> dict:
    return {
        "story_id": story_id,
        "story_path": f"{story_id}/story.json",
        "title": story_id,
        "gutenberg_id": 1,
        "metadata_assessment": {"result": {"target_candidates": candidates}},
    }


def _model_record(story_id: str, model: str, genre: str) -> dict:
    return {
        "lcats_id": story_id,
        "schema_version": "genre-sidecar-v1",
        "assessments": [
            {
                "label": "gutenberg_metadata_rules",
                "result": {"target_candidates": ["fantasy"]},
            },
            {
                "label": "model_detect",
                "generated_at": "2026-01-01T00:00:00Z",
                "provenance": {"backend_model": model},
                "result": {"detected_genre": genre, "detected_genre_confidence": 0.5},
            },
        ],
    }


class InputValidationTests(unittest.TestCase):
    def write_inputs(
        self,
        directory: Path,
        *,
        opus_model="claude-opus-4-8",
        local_model="gpt-oss:20b",
    ):
        metadata = directory / "metadata.jsonl"
        opus = directory / "opus.jsonl"
        local = directory / "local.jsonl"
        metadata.write_text(
            json.dumps(_metadata_record("story/one", ["fantasy"])) + "\n",
            encoding="utf-8",
        )
        opus.write_text(
            json.dumps(_model_record("story/one", opus_model, "fantasy")) + "\n",
            encoding="utf-8",
        )
        local.write_text(
            json.dumps(_model_record("story/one", local_model, "horror")) + "\n",
            encoding="utf-8",
        )
        return metadata, opus, local

    def test_malformed_and_mismatched_inputs_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            metadata, opus, local = self.write_inputs(directory)
            metadata.write_text("{not-json}\n", encoding="utf-8")
            with self.assertRaises(InputValidationError) as context:
                validate_inputs(metadata, opus, local)
            self.assertTrue(
                any("malformed JSON" in item for item in context.exception.diagnostics)
            )

    def test_duplicate_and_wrong_model_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            metadata, opus, local = self.write_inputs(
                directory, opus_model="wrong-model"
            )
            metadata.write_text(
                json.dumps(_metadata_record("story/one", ["fantasy"]))
                + "\n"
                + json.dumps(_metadata_record("story/one", ["fantasy"]))
                + "\n",
                encoding="utf-8",
            )
            with self.assertRaises(InputValidationError) as context:
                validate_inputs(metadata, opus, local)
            diagnostics = "\n".join(context.exception.diagnostics)
            self.assertIn("duplicate story ID", diagnostics)
            self.assertIn("backend_model", diagnostics)

    def test_missing_ids_and_same_source_hash_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            metadata, opus, local = self.write_inputs(directory)
            local.write_bytes(opus.read_bytes())
            with self.assertRaises(InputValidationError) as context:
                validate_inputs(metadata, opus, local)
            diagnostics = "\n".join(context.exception.diagnostics)
            self.assertIn("identical", diagnostics)
            self.assertIn("backend_model", diagnostics)

    def test_missing_story_id_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            metadata, opus, local = self.write_inputs(directory)
            record = _metadata_record("story/one", ["fantasy"])
            del record["story_id"]
            metadata.write_text(json.dumps(record) + "\n", encoding="utf-8")
            with self.assertRaises(InputValidationError) as context:
                validate_inputs(metadata, opus, local)
            self.assertIn(
                "no non-empty story_id/lcats_id",
                "\n".join(context.exception.diagnostics),
            )

    def test_mismatched_story_sets_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            metadata, opus, local = self.write_inputs(directory)
            local.write_text(
                json.dumps(_model_record("story/two", "gpt-oss:20b", "horror")) + "\n",
                encoding="utf-8",
            )
            with self.assertRaises(InputValidationError) as context:
                validate_inputs(metadata, opus, local)
            diagnostics = "\n".join(context.exception.diagnostics)
            self.assertIn("missing story IDs", diagnostics)
            self.assertIn("unexpected story IDs", diagnostics)


if __name__ == "__main__":
    unittest.main()
