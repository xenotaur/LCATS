"""Unit tests for run_pilot.py.

Not part of the installed lcats package (this script lives under
experiments/, not lcats/src/lcats/), so it is not discovered by lcats'
scripts/test (which only walks tests/) - run explicitly:

    python -m unittest experiments/03_cross_segment_relation_pilot/run_pilot_test.py

or:

    python -m pytest experiments/03_cross_segment_relation_pilot/run_pilot_test.py
"""

from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import unittest

from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import run_pilot  # noqa: E402 - see sys.path.insert above

from lcats.llm import backend as llm_backend  # noqa: E402


class _SequencedFakeBackend:
    """Returns a fixed sequence of tool results, one per complete() call -
    same pattern as tests/analysis_tests/event_role_world_test.py's own
    double, needed here since a single story's pipeline makes several
    distinct LLM-backed passes in order."""

    def __init__(self, tool_results):
        self._results = list(tool_results)
        self.calls = []

    def complete(self, **kwargs):
        self.calls.append(kwargs)
        return llm_backend.BackendResponse(
            text="",
            tool_result=self._results.pop(0),
            model="fake-1.0",
            input_tokens=5,
            output_tokens=2,
            raw=None,
        )


class TestRunErwPipelineStoryRelationCallSite(unittest.TestCase):
    """Regression test for a real review finding on PR #187: this script's
    own _run_erw_pipeline() has a second, separate call site for
    build_story_relations() (distinct from processor.process_segments()'s
    own call site, already covered by
    tests/analysis_tests/event_role_world_test.py) - widening
    build_story_relations()'s return signature to a 3-tuple broke this
    site's 2-value unpack with ValueError: too many values to unpack,
    which would have silently excluded every story reaching the
    cross-segment relation pass."""

    def test_cross_segment_pass_does_not_raise_on_widened_return(self):
        segment_1_text = "The old machine hummed."
        segment_2_text = "It shut off forever."
        body = segment_1_text + " " + segment_2_text

        entity_result = {"entities": []}
        event_result_1 = {
            "events": [
                {
                    "event_id": "ev1",
                    "predicate": "hummed",
                    "event_type": "sound_emission",
                    "quote": "hummed",
                }
            ]
        }
        event_result_2 = {
            "events": [
                {
                    "event_id": "ev2",
                    "predicate": "shut off",
                    "event_type": "mechanical_failure",
                    "quote": "shut off",
                }
            ]
        }
        empty_result = {}
        story_relation_result = {
            "relations": [
                {
                    "relation_id": "r1",
                    "source_event_id": "1:ev1",
                    "target_event_id": "2:ev2",
                    "relation_type": "causes",
                    "certainty": "explicit",
                }
            ]
        }

        fake = _SequencedFakeBackend(
            [
                entity_result,  # segment 1: entity
                event_result_1,  # segment 1: event
                empty_result,  # segment 1: relation
                empty_result,  # segment 1: discourse
                # No hypothesis call: _run_erw_pipeline always passes
                # include_hypotheses=False (this pilot does not use
                # hypothesis data), so process_segment skips stage 8
                # entirely for both segments.
                entity_result,  # segment 2: entity
                event_result_2,  # segment 2: event
                empty_result,  # segment 2: relation
                empty_result,  # segment 2: discourse
                story_relation_result,  # story-level cross-segment pass
            ]
        )
        extractors = run_pilot._build_erw_extractors(fake, "fake-model")
        nlp_backend = run_pilot._make_nlp_backend("fake")
        segments = [
            {
                "segment_id": 1,
                "start_char": 0,
                "end_char": len(segment_1_text),
            },
            {
                "segment_id": 2,
                "start_char": len(segment_1_text) + 1,
                "end_char": len(body),
            },
        ]

        # Must not raise ValueError: too many values to unpack.
        result = run_pilot._run_erw_pipeline(
            body, segments, extractors, nlp_backend, "fake", "test_story"
        )

        self.assertEqual(len(result["story"]["cross_segment_relations"]), 1)
        self.assertEqual(
            result["story"]["cross_segment_relations"][0]["relation_id"],
            "story:r1",
        )


class TestSegmentStoryStillReturnsBareList(unittest.TestCase):
    """WI-EVENT-0033: make_segment_extractor now uses the tool= path
    internally, but scene_analysis._segment_result_aligner unwraps the
    schema's required "segments" wrapper key before returning, so
    extracted_output stays a bare list and _segment_story needs no
    changes of its own - this regression test proves that contract holds
    end-to-end through the real extractor, not just at the schema level."""

    def test_segment_story_returns_bare_list(self):
        from lcats.llm import fake_backend

        story_text = "Once upon a time.\n\nThe end."
        tool_result = {
            "segments": [
                {
                    "segment_id": 1,
                    "segment_type": "narrative_scene",
                    "start_par_id": 1,
                    "end_par_id": 1,
                    "start_exact": "Once upon a time.",
                    "end_exact": "Once upon a time.",
                    "start_prefix": "",
                    "end_suffix": "",
                    "start_char": None,
                    "end_char": None,
                    "summary": "Intro.",
                    "cohesion": {
                        "time": "once",
                        "place": "",
                        "characters": [],
                    },
                    "gacd": None,
                    "erac": None,
                    "reason": "Setup.",
                    "confidence": 0.7,
                }
            ]
        }
        fb = fake_backend.FakeBackend(tool_result=tool_result)

        segments, error = run_pilot._segment_story(story_text, fb, "fake-model")

        self.assertIsNone(error)
        self.assertIsInstance(segments, list)
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0]["segment_id"], 1)


class TestMainUnexpectedPerStoryException(unittest.TestCase):
    """WI-EVENT-0032 (audit's Category B update finding): main()'s per-story
    loop previously caught only FatalPilotError - any other exception
    propagated straight out of main(), skipping the write block entirely
    and discarding every already-completed, already-paid-for story's
    results, not just the one that failed."""

    def _write_story(self, data_dir: pathlib.Path, name: str, body: str) -> None:
        (data_dir / f"{name}.json").write_text(
            json.dumps({"name": name, "author": "Test Author", "body": body}),
            encoding="utf-8",
        )

    def test_unexpected_exception_on_one_story_preserves_other_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = pathlib.Path(tmp) / "data"
            data_dir.mkdir()
            output_dir = pathlib.Path(tmp) / "results"
            self._write_story(data_dir, "story_a", "Story A body text.")
            self._write_story(data_dir, "story_b", "Story B body text.")

            real_row = {
                "path": str(data_dir / "story_a.json"),
                "story_id": "story_a",
                "genre": "science fiction",
                "excluded": False,
                "exclude_reason": "",
                "word_count": 3,
                "segment_count": 1,
                "cross_segment_density_per_1000_words": 0.0,
                "weakly_inferred_cross_segment_density_per_1000_words": 0.0,
                "folded_relations_per_1000_words": 0.0,
                "folded_weakly_inferred_relations_per_1000_words": 0.0,
            }

            def fake_run_story(path, genre, *args, **kwargs):
                if path.stem == "story_b":
                    raise RuntimeError("simulated unexpected per-story failure")
                return dict(real_row), []

            argv = [
                "run_pilot.py",
                "--dry-run",
                "--data-dir",
                str(data_dir),
                "--sample-size",
                "1",
                "--output",
                str(output_dir),
            ]
            with patch.object(sys, "argv", argv), patch.object(
                run_pilot, "run_story", side_effect=fake_run_story
            ):
                exit_code = run_pilot.main()

            self.assertEqual(exit_code, 0)

            stories_path = output_dir / "pilot_stories.jsonl"
            self.assertTrue(stories_path.exists())
            rows = [
                json.loads(line)
                for line in stories_path.read_text(encoding="utf-8").splitlines()
            ]
            rows_by_story_id = {row["story_id"]: row for row in rows}

            # story_a's real, already-completed result must still be
            # written - not discarded because story_b crashed later.
            self.assertIn("story_a", rows_by_story_id)
            self.assertFalse(rows_by_story_id["story_a"]["excluded"])

            # story_b is recorded as excluded with the unexpected error,
            # not silently dropped and not aborting the whole run.
            self.assertIn("story_b", rows_by_story_id)
            self.assertTrue(rows_by_story_id["story_b"]["excluded"])
            self.assertIn(
                "unexpected error", rows_by_story_id["story_b"]["exclude_reason"]
            )
            self.assertIn(
                "simulated unexpected per-story failure",
                rows_by_story_id["story_b"]["exclude_reason"],
            )


if __name__ == "__main__":
    unittest.main()
