"""Unit tests for check_segmentation_reliability.py.

Not part of the installed lcats package (this script lives under
experiments/, not lcats/src/lcats/), so it is not discovered by lcats'
scripts/test (which only walks tests/) - run explicitly:

    python -m unittest experiments/03_cross_segment_relation_pilot/check_segmentation_reliability_test.py

or:

    python -m pytest experiments/03_cross_segment_relation_pilot/check_segmentation_reliability_test.py
"""

from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import unittest

from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import check_segmentation_reliability  # noqa: E402 - see sys.path.insert above


def _write_bucket_story(collection_dir: pathlib.Path, slug: str, body: str) -> None:
    # Bucket layout (PROP-LCATS-STORY-BUCKET-LAYOUT, retracted flat
    # support): a story is <collection>/<story>/story.json, not a flat
    # <story>.json file directly in the collection directory.
    story_dir = collection_dir / slug
    story_dir.mkdir(parents=True)
    (story_dir / "story.json").write_text(
        json.dumps({"name": slug, "author": "Test Author", "body": body}),
        encoding="utf-8",
    )


class TestSelectFilesCanonicalOnly(unittest.TestCase):
    """select_files() must use the canonical bucket-only selector, not a
    raw rglob("*.json") -- a bucket directory can hold non-story sidecar
    JSON (analysis.json, scenes.json, etc.) that must never be sampled as
    if it were an independent story."""

    def test_ignores_sidecar_json_in_bucket_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = pathlib.Path(tmp) / "corpora"
            collection_dir = data_dir / "collection_a"
            _write_bucket_story(collection_dir, "real_story", "Some story text.")
            (collection_dir / "real_story" / "analysis.json").write_text(
                json.dumps({"unrelated": "sidecar data"}), encoding="utf-8"
            )

            args = _namespace(data_dir=str(data_dir), sample_size=10)
            found = check_segmentation_reliability.select_files(args)

            self.assertEqual(len(found), 1)
            self.assertEqual(found[0].name, "story.json")
            self.assertEqual(found[0].parent.name, "real_story")

    def test_finds_bucket_story_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = pathlib.Path(tmp) / "corpora"
            collection_dir = data_dir / "collection_a"
            _write_bucket_story(collection_dir, "story_one", "Body one.")
            _write_bucket_story(collection_dir, "story_two", "Body two.")

            args = _namespace(data_dir=str(data_dir), sample_size=10)
            found = check_segmentation_reliability.select_files(args)

            self.assertEqual(len(found), 2)

    def test_story_list_also_ignores_sidecar_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = pathlib.Path(tmp) / "corpora"
            collection_dir = data_dir / "collection_a"
            _write_bucket_story(collection_dir, "real_story", "Some story text.")
            sidecar = collection_dir / "real_story" / "analysis.json"
            sidecar.write_text(
                json.dumps({"unrelated": "sidecar data"}), encoding="utf-8"
            )
            story_list = pathlib.Path(tmp) / "story_list.txt"
            story_list.write_text(
                f"{collection_dir / 'real_story' / 'story.json'}\n{sidecar}\n",
                encoding="utf-8",
            )

            args = _namespace(story_list=str(story_list))
            found = check_segmentation_reliability.select_files(args)

            self.assertEqual(len(found), 1)
            self.assertEqual(found[0].name, "story.json")


def _namespace(**kwargs):
    import argparse

    defaults = {
        "story_list": None,
        "data_dir": "corpora",
        "sample_size": 20,
        "seed": 42,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


class _FakeExtractor:
    """Stub segment extractor: returns one segment per call, deterministic,
    no LLM/API involvement."""

    def extract(self, body, model_name=None):
        return {
            "extracted_output": [{"text": body[:20]}],
            "raw_output": "",
            "api_error": None,
            "extraction_error": None,
            "usage": None,
        }


class TestMainStoryIdCollisionAvoidance(unittest.TestCase):
    """main()'s per-story result cache key must be collection-qualified,
    not derived from path.stem alone (always the literal "story" under the
    bucket layout) or from the directory slug alone (only guaranteed
    unique per collection, not globally)."""

    def _run_main(self, data_dir, output_dir, sample_size=10):
        argv = [
            "check_segmentation_reliability.py",
            "--data-dir",
            str(data_dir),
            "--sample-size",
            str(sample_size),
            "--output",
            str(output_dir),
        ]
        with (
            patch.object(sys, "argv", argv),
            patch.object(check_segmentation_reliability, "load_secrets"),
            patch(
                "lcats.llm.anthropic_backend.AnthropicBackend",
                return_value=object(),
            ),
            patch.object(
                check_segmentation_reliability.scene_analysis,
                "make_segment_extractor",
                return_value=_FakeExtractor(),
            ),
        ):
            return check_segmentation_reliability.main()

    def test_two_collections_sharing_story_slug_do_not_collide(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = pathlib.Path(tmp) / "corpora"
            output_dir = pathlib.Path(tmp) / "results"
            _write_bucket_story(
                data_dir / "collection_a", "common_slug", "Collection A's story body."
            )
            _write_bucket_story(
                data_dir / "collection_b", "common_slug", "Collection B's story body."
            )

            exit_code = self._run_main(data_dir, output_dir, sample_size=10)

            self.assertEqual(exit_code, 0)
            result_a = output_dir / "collection_a" / "common_slug.json"
            result_b = output_dir / "collection_b" / "common_slug.json"
            self.assertTrue(result_a.exists())
            self.assertTrue(result_b.exists())

            record_a = json.loads(result_a.read_text("utf-8"))
            record_b = json.loads(result_b.read_text("utf-8"))
            self.assertEqual(record_a["story_id"], "collection_a/common_slug")
            self.assertEqual(record_b["story_id"], "collection_b/common_slug")
            # Each story's own extraction result was preserved -- neither
            # was silently overwritten by the other's cached record.
            self.assertNotEqual(
                record_a["extracted_output"], record_b["extracted_output"]
            )

    def test_single_story_run_behavior_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = pathlib.Path(tmp) / "corpora"
            output_dir = pathlib.Path(tmp) / "results"
            _write_bucket_story(data_dir / "sherlock", "the_only_story", "Body text.")

            exit_code = self._run_main(data_dir, output_dir, sample_size=1)

            self.assertEqual(exit_code, 0)
            result_path = output_dir / "sherlock" / "the_only_story.json"
            self.assertTrue(result_path.exists())
            record = json.loads(result_path.read_text("utf-8"))
            self.assertEqual(record["story_id"], "sherlock/the_only_story")
            self.assertEqual(record["outcome"], "included")
            self.assertTrue(record["llm_call_made"])

    def test_rerun_reuses_cached_result_without_recomputing(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = pathlib.Path(tmp) / "corpora"
            output_dir = pathlib.Path(tmp) / "results"
            _write_bucket_story(data_dir / "sherlock", "cached_story", "Body text.")

            first_exit = self._run_main(data_dir, output_dir, sample_size=1)
            self.assertEqual(first_exit, 0)
            result_path = output_dir / "sherlock" / "cached_story.json"
            first_record = json.loads(result_path.read_text("utf-8"))

            # Second run: extract() would raise if actually called again --
            # proves the cache hit path is taken, not a real re-extraction.
            # (make_segment_extractor() itself is still called unconditionally
            # once per main() invocation, before the per-story loop -- only
            # the per-story .extract() call is expected to be skipped.)
            failing_extractor = _FakeExtractor()
            failing_extractor.extract = lambda *a, **k: (_ for _ in ()).throw(
                AssertionError("extract() should not run again on a cache hit")
            )
            argv = [
                "check_segmentation_reliability.py",
                "--data-dir",
                str(data_dir),
                "--sample-size",
                "1",
                "--output",
                str(output_dir),
            ]
            with (
                patch.object(sys, "argv", argv),
                patch.object(check_segmentation_reliability, "load_secrets"),
                patch(
                    "lcats.llm.anthropic_backend.AnthropicBackend",
                    return_value=object(),
                ),
                patch.object(
                    check_segmentation_reliability.scene_analysis,
                    "make_segment_extractor",
                    return_value=failing_extractor,
                ),
            ):
                second_exit = check_segmentation_reliability.main()

            self.assertEqual(second_exit, 0)
            second_record = json.loads(result_path.read_text("utf-8"))
            self.assertEqual(first_record, second_record)


class _FakeAlignmentFailureExtractor:
    """Stub extractor simulating JSONPromptExtractor's real alignment_error
    contract: extracted_output cleared to None, but parsed_output still
    holding the raw pre-alignment segments (see the comment above
    check_segmentation_reliability.py's `record = {...}` for why this is
    real behavior, not a test-only assumption)."""

    def extract(self, body, model_name=None):
        return {
            "raw_output": "",
            "parsed_output": {
                "segments": [
                    {
                        "segment_id": 1,
                        "start_par_id": 3,
                        "end_par_id": 5,
                        "start_exact": "It was",
                        "end_exact": "the end.",
                    }
                ]
            },
            "extracted_output": None,
            "api_error": None,
            "extraction_error": None,
            "alignment_error": "alignment failed for segment_id=1: ...",
            "usage": None,
        }


class TestParsedOutputPersistedOnAlignmentFailure(unittest.TestCase):
    """WI-SEGMENT-0069, Required Change 1: a captured alignment_error must
    retain enough detail (the pre-alignment parsed_output) to be analyzed
    later without a fresh live LLM call."""

    def test_parsed_output_present_when_extracted_output_is_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = pathlib.Path(tmp) / "corpora"
            output_dir = pathlib.Path(tmp) / "results"
            _write_bucket_story(data_dir / "sherlock", "failing_story", "Body text.")

            argv = [
                "check_segmentation_reliability.py",
                "--data-dir",
                str(data_dir),
                "--sample-size",
                "1",
                "--output",
                str(output_dir),
            ]
            with (
                patch.object(sys, "argv", argv),
                patch.object(check_segmentation_reliability, "load_secrets"),
                patch(
                    "lcats.llm.anthropic_backend.AnthropicBackend",
                    return_value=object(),
                ),
                patch.object(
                    check_segmentation_reliability.scene_analysis,
                    "make_segment_extractor",
                    return_value=_FakeAlignmentFailureExtractor(),
                ),
            ):
                exit_code = check_segmentation_reliability.main()

            self.assertEqual(exit_code, 0)
            record = json.loads(
                (output_dir / "sherlock" / "failing_story.json").read_text("utf-8")
            )
            self.assertTrue(record["outcome"].startswith("alignment_error:"))
            self.assertIsNone(record["extracted_output"])
            self.assertIsNotNone(record["parsed_output"])
            self.assertEqual(
                record["parsed_output"]["segments"][0]["start_exact"], "It was"
            )


class TestClassifyAlignmentError(unittest.TestCase):
    """WI-SEGMENT-0059: on an alignment failure, extracted_output is the
    raw, unaligned {"segments": [...]} dict (segments_result_aligner
    raises before ever unwrapping it), not a bare list. classify() must
    check alignment_error explicitly -- without that check, a truthy,
    non-empty dict would fall through every other check and misreport
    "included", exactly the class of silent misreporting this script
    exists to measure and prevent."""

    def test_alignment_error_reported_not_included(self):
        result = {
            "api_error": None,
            "extraction_error": None,
            "alignment_error": "alignment failed for segment_id=1: ...",
            "extracted_output": {"segments": [{"segment_id": 1}]},
        }
        segments = result.get("extracted_output") or []
        outcome = check_segmentation_reliability.classify(result, segments)
        self.assertTrue(outcome.startswith("alignment_error:"))

    def test_alignment_error_takes_priority_over_no_segments_check(self):
        """A truthy dict is not "no segments" either -- confirm
        alignment_error is checked before the segments truthiness check
        would (wrongly) let it through as "included"."""
        result = {
            "api_error": None,
            "extraction_error": None,
            "alignment_error": "alignment failed",
            "extracted_output": {"segments": []},
        }
        segments = result.get("extracted_output") or []
        self.assertTrue(segments)  # a non-empty dict is truthy
        outcome = check_segmentation_reliability.classify(result, segments)
        self.assertNotEqual(outcome, "included")

    def test_no_alignment_error_still_included(self):
        result = {
            "api_error": None,
            "extraction_error": None,
            "alignment_error": None,
            "extracted_output": [{"segment_id": 1}],
        }
        segments = result.get("extracted_output") or []
        outcome = check_segmentation_reliability.classify(result, segments)
        self.assertEqual(outcome, "included")


if __name__ == "__main__":
    unittest.main()
