"""Tests for deterministic science-fiction story preparation."""

import copy
import hashlib
import json
import pathlib
import tempfile
import unittest

from lcats.analysis.science_fiction import preparation


def _write_story(path: pathlib.Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


class PreparationTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.root = pathlib.Path(self.tmpdir.name)
        self.story_path = self.root / "collection" / "story-a" / "story.json"

    def test_loads_canonical_story_without_mutating_source(self):
        data = {
            "name": "Example",
            "body": " First paragraph.  \r\n\r\nSecond paragraph.\n",
            "metadata": {"author": "A. Writer"},
        }
        _write_story(self.story_path, data)
        before = self.story_path.read_bytes()

        result = preparation.prepare_story_file(self.story_path)

        self.assertEqual(before, self.story_path.read_bytes())
        self.assertEqual(
            "First paragraph.\n\nSecond paragraph.", result.normalized_text
        )
        self.assertEqual("Example", result.story_name)
        self.assertEqual(str(self.story_path), result.story_path)

    def test_story_hash_and_paragraph_ids_are_stable(self):
        data = {"name": "Hash Story", "body": "Alpha.\n\nBeta.\n\nGamma."}
        original = copy.deepcopy(data)

        first = preparation.prepare_story_data(data, story_path=self.story_path)
        second = preparation.prepare_story_data(data, story_path=self.story_path)

        expected_hash = hashlib.sha256(b"Alpha.\n\nBeta.\n\nGamma.").hexdigest()
        self.assertEqual(expected_hash, first.story_hash)
        self.assertEqual(first.to_manifest(), second.to_manifest())
        self.assertEqual(
            ["p00001", "p00002", "p00003"],
            [paragraph.paragraph_id for paragraph in first.paragraphs],
        )
        self.assertEqual(original, data)

    def test_indented_paragraphs_keep_stable_separate_anchors(self):
        data = {"name": "Indented", "body": "Alpha.\n\n  Beta.\n\n\tGamma."}

        result = preparation.prepare_story_data(data, story_path=self.story_path)

        self.assertEqual(
            ["Alpha.", "Beta.", "Gamma."],
            [paragraph.text for paragraph in result.paragraphs],
        )
        self.assertEqual(
            ["p00001", "p00002", "p00003"],
            [paragraph.paragraph_id for paragraph in result.paragraphs],
        )

    def test_whole_story_eligible_uses_single_full_story_chunk(self):
        data = {"name": "Short", "body": "Alpha.\n\nBeta."}
        config = preparation.PreparationConfig(whole_story_max_chars=100)

        result = preparation.prepare_story_data(
            data, story_path=self.story_path, config=config
        )

        self.assertTrue(result.whole_story_eligible)
        self.assertEqual(1, len(result.chunks))
        self.assertEqual(("p00001", "p00002"), result.chunks[0].core_paragraph_ids)
        self.assertEqual((), result.chunks[0].overlap_before_ids)
        self.assertEqual((), result.chunks[0].overlap_after_ids)
        preparation.assert_gap_free_core_coverage(result)

    def test_adaptive_chunks_have_gap_free_coverage_and_overlap_accounting(self):
        body = "\n\n".join(
            [
                "One alpha words.",
                "Two beta words.",
                "Three gamma words.",
                "Four delta words.",
                "Five epsilon words.",
            ]
        )
        config = preparation.PreparationConfig(
            whole_story_max_chars=10,
            chunk_target_chars=25,
            chunk_max_chars=40,
            chunk_overlap_paragraphs=1,
        )

        result = preparation.prepare_story_data(
            {"name": "Chunked", "body": body},
            story_path=self.story_path,
            config=config,
        )

        self.assertFalse(result.whole_story_eligible)
        preparation.assert_gap_free_core_coverage(result)
        core_ids = [
            paragraph_id
            for chunk in result.chunks
            for paragraph_id in chunk.core_paragraph_ids
        ]
        self.assertEqual(
            [paragraph.paragraph_id for paragraph in result.paragraphs], core_ids
        )
        self.assertTrue(any(chunk.overlap_after_ids for chunk in result.chunks))
        self.assertTrue(any(chunk.overlap_before_ids for chunk in result.chunks))
        self.assertTrue(
            all(
                len(chunk.text) <= result.config.chunk_max_chars
                for chunk in result.chunks
            )
        )

    def test_chunk_overlap_stays_within_configured_max_when_possible(self):
        body = "\n\n".join(f"{index} " + ("x" * 29_998) for index in range(6))

        result = preparation.prepare_story_data(
            {"name": "Large paragraphs", "body": body},
            story_path=self.story_path,
            config=preparation.PreparationConfig(
                whole_story_max_chars=10,
                chunk_target_chars=60_000,
                chunk_max_chars=75_000,
                chunk_overlap_paragraphs=1,
            ),
        )

        self.assertGreater(len(result.chunks), 1)
        self.assertTrue(
            all(
                len(chunk.text) <= result.config.chunk_max_chars
                for chunk in result.chunks
            )
        )
        preparation.assert_gap_free_core_coverage(result)

    def test_chunk_planning_prefers_section_boundaries(self):
        body = "\n\n".join(
            [
                "First paragraph has enough text.",
                "Second paragraph has enough text.",
                "CHAPTER II",
                "Third paragraph begins the next section.",
            ]
        )
        config = preparation.PreparationConfig(
            whole_story_max_chars=10,
            chunk_target_chars=55,
            chunk_max_chars=120,
            chunk_overlap_paragraphs=0,
        )

        result = preparation.prepare_story_data(
            {"name": "Sections", "body": body},
            story_path=self.story_path,
            config=config,
        )

        self.assertTrue(result.paragraphs[2].is_section_boundary)
        self.assertEqual(("p00001", "p00002"), result.chunks[0].core_paragraph_ids)
        self.assertEqual(("p00003", "p00004"), result.chunks[1].core_paragraph_ids)
        preparation.assert_gap_free_core_coverage(result)

    def test_chunk_planning_prefers_boundary_before_target(self):
        body = "\n\n".join(
            [
                "alpha text before the heading",
                "CHAPTER II",
                "beta text after the heading",
            ]
        )
        config = preparation.PreparationConfig(
            whole_story_max_chars=10,
            chunk_target_chars=55,
            chunk_max_chars=120,
            chunk_overlap_paragraphs=0,
        )

        result = preparation.prepare_story_data(
            {"name": "Boundary Before Target", "body": body},
            story_path=self.story_path,
            config=config,
        )

        self.assertEqual(("p00001",), result.chunks[0].core_paragraph_ids)
        self.assertEqual(("p00002", "p00003"), result.chunks[1].core_paragraph_ids)
        preparation.assert_gap_free_core_coverage(result)

    def test_manifest_records_versioned_configuration_and_chunk_hashes(self):
        config = preparation.PreparationConfig(
            whole_story_max_chars=10,
            chunk_target_chars=8,
            chunk_max_chars=30,
            chunk_overlap_paragraphs=0,
        )

        result = preparation.prepare_story_data(
            {"name": "Manifest", "body": "Alpha.\n\nBeta."},
            story_path=self.story_path,
            config=config,
        )
        manifest = result.to_manifest()

        self.assertEqual("sf-preparation-manifest-v1", manifest["manifest_version"])
        self.assertEqual("sf-preparation-config-v1", manifest["config"]["version"])
        self.assertEqual("sha256", manifest["story_hash_algorithm"])
        self.assertNotIn("normalized_text", manifest)
        self.assertEqual(
            preparation.hash_text(result.chunks[0].text),
            manifest["chunks"][0]["text_hash"],
        )

    def test_rejects_non_canonical_story_filename(self):
        path = self.root / "collection" / "story-a" / "draft.json"
        _write_story(path, {"name": "Draft", "body": "Text."})

        with self.assertRaises(ValueError):
            preparation.prepare_story_file(path)

    def test_rejects_non_object_story_json(self):
        path = self.root / "collection" / "story-a" / "story.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")

        with self.assertRaisesRegex(TypeError, "JSON object"):
            preparation.prepare_story_file(path)


if __name__ == "__main__":
    unittest.main()
