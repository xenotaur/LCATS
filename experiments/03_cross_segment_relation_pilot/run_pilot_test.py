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


class TestPerStageModelOverrides(unittest.TestCase):
    """WI-PILOT-0060: per-stage --model overrides are opt-in plumbing only.

    These tests use fake backends and recorded complete() calls, so they
    prove wiring without spending on real LLM calls.
    """

    def test_stage_models_default_every_stage_to_global_model(self):
        args = run_pilot.argparse.Namespace(
            model_genre_detect=None,
            model_segment=None,
            model_entity=None,
            model_event=None,
            model_relation=None,
            model_discourse=None,
            model_cross_segment=None,
        )

        models = run_pilot._resolve_stage_models("global-model", args)

        self.assertEqual(
            models.to_dict(),
            {
                "genre_detect": "global-model",
                "segment": "global-model",
                "entity": "global-model",
                "event": "global-model",
                "relation": "global-model",
                "discourse": "global-model",
                "cross_segment_relation": "global-model",
            },
        )

    def test_stage_models_apply_only_explicit_overrides(self):
        args = run_pilot.argparse.Namespace(
            model_genre_detect="genre-model",
            model_segment="segment-model",
            model_entity="entity-model",
            model_event=None,
            model_relation="relation-model",
            model_discourse=None,
            model_cross_segment="cross-model",
        )

        models = run_pilot._resolve_stage_models("global-model", args)

        self.assertEqual(models.genre_detect, "genre-model")
        self.assertEqual(models.segment, "segment-model")
        self.assertEqual(models.entity, "entity-model")
        self.assertEqual(models.event, "global-model")
        self.assertEqual(models.relation, "relation-model")
        self.assertEqual(models.discourse, "global-model")
        self.assertEqual(models.cross_segment_relation, "cross-model")

    def test_segment_stage_uses_segment_model_override(self):
        from lcats.llm import fake_backend

        tool_result = {
            "segments": [
                {
                    "segment_id": 1,
                    "segment_type": "narrative_scene",
                    "start_par_id": 1,
                    "end_par_id": 1,
                    "start_exact": "Once.",
                    "end_exact": "Once.",
                    "start_prefix": "",
                    "end_suffix": "",
                    "start_char": 0,
                    "end_char": 5,
                    "summary": "Setup.",
                    "cohesion": {"time": "", "place": "", "characters": []},
                    "gacd": None,
                    "erac": None,
                    "reason": "Single scene.",
                    "confidence": 0.9,
                }
            ]
        }
        fake = fake_backend.FakeBackend(tool_result=tool_result)

        segments, error, _usage = run_pilot._segment_story(
            "Once.", fake, "segment-model"
        )

        self.assertIsNone(error)
        self.assertEqual(len(segments), 1)
        self.assertEqual(fake.calls[0]["model"], "segment-model")

    def test_erw_extractors_use_individual_model_overrides(self):
        segment_1_text = "The old machine hummed."
        segment_2_text = "It shut off forever."
        body = segment_1_text + " " + segment_2_text
        fake = _SequencedFakeBackend(
            [
                {"entities": []},
                {
                    "events": [
                        {
                            "event_id": "ev1",
                            "predicate": "hummed",
                            "event_type": "sound_emission",
                            "quote": "hummed",
                        }
                    ]
                },
                {},
                {},
                {"entities": []},
                {
                    "events": [
                        {
                            "event_id": "ev2",
                            "predicate": "shut off",
                            "event_type": "mechanical_failure",
                            "quote": "shut off",
                        }
                    ]
                },
                {},
                {},
                {
                    "relations": [
                        {
                            "relation_id": "r1",
                            "source_event_id": "1:ev1",
                            "target_event_id": "2:ev2",
                            "relation_type": "causes",
                            "certainty": "explicit",
                        }
                    ]
                },
            ]
        )
        stage_models = run_pilot.StageModels.from_global(
            "global-model",
            entity="entity-model",
            event="event-model",
            relation="relation-model",
            discourse="discourse-model",
            cross_segment_relation="cross-model",
        )
        extractors = run_pilot._build_erw_extractors(fake, "global-model", stage_models)
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

        result = run_pilot._run_erw_pipeline(
            body, segments, extractors, nlp_backend, "fake", "test_story"
        )

        self.assertEqual(len(result["story"]["cross_segment_relations"]), 1)
        self.assertEqual(
            [call["model"] for call in fake.calls],
            [
                "entity-model",
                "event-model",
                "relation-model",
                "discourse-model",
                "entity-model",
                "event-model",
                "relation-model",
                "discourse-model",
                "cross-model",
            ],
        )


class TestSegmentStoryStillReturnsBareList(unittest.TestCase):
    """WI-EVENT-0033: make_segment_extractor now uses the tool= path
    internally, but scene_analysis._segment_result_aligner unwraps the
    schema's required "segments" wrapper key before returning, so
    extracted_output stays a bare list on a successful alignment - this
    regression test proves that contract holds end-to-end through the
    real extractor, not just at the schema level. (WI-SEGMENT-0059:
    _segment_story does need to check alignment_error now, for the
    failure case - see TestSegmentStoryHandlesAlignmentFailure below.)"""

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

        segments, error, usage = run_pilot._segment_story(story_text, fb, "fake-model")

        self.assertIsNone(error)
        self.assertIsInstance(segments, list)
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0]["segment_id"], 1)
        self.assertEqual(usage, {"input_tokens": 0, "output_tokens": 0})


class TestSegmentStoryHandlesAlignmentFailure(unittest.TestCase):
    """WI-SEGMENT-0059: a genuinely unresolvable anchor now makes
    segments_result_aligner raise, which JSONPromptExtractor.extract
    catches and records as alignment_error. On that path,
    extracted_output is the raw, unaligned {"segments": [...]} dict
    (segments_result_aligner raises before ever unwrapping it), not a
    bare list - _segment_story must check alignment_error itself
    (previously it only checked api_error/extraction_error) or it would
    return that dict as "segments" with error=None, corrupting its own
    bare-list return contract."""

    def test_unresolvable_anchor_returns_empty_segments_and_error(self):
        from lcats.llm import fake_backend

        # A single short paragraph (no blank-line break) with an
        # end_exact that does not appear anywhere in the text at all.
        story_text = "Once upon a time there was a dragon."
        tool_result = {
            "segments": [
                {
                    "segment_id": 1,
                    "segment_type": "narrative_scene",
                    "start_par_id": 1,
                    "end_par_id": 1,
                    "start_exact": "Once upon a time",
                    "end_exact": "this text does not appear in the story",
                    "start_prefix": "",
                    "end_suffix": "",
                    "start_char": None,
                    "end_char": None,
                    "summary": "Intro.",
                    "cohesion": {"time": "once", "place": "", "characters": []},
                    "gacd": None,
                    "erac": None,
                    "reason": "Setup.",
                    "confidence": 0.7,
                }
            ]
        }
        fb = fake_backend.FakeBackend(tool_result=tool_result)

        segments, error, usage = run_pilot._segment_story(story_text, fb, "fake-model")

        self.assertEqual(segments, [])
        self.assertIsNotNone(error)
        self.assertIn("alignment failed", error)
        self.assertEqual(usage, {"input_tokens": 0, "output_tokens": 0})


class TestMainUnexpectedPerStoryException(unittest.TestCase):
    """WI-EVENT-0032 (audit's Category B update finding): main()'s per-story
    loop previously caught only FatalPilotError - any other exception
    propagated straight out of main(), skipping the write block entirely
    and discarding every already-completed, already-paid-for story's
    results, not just the one that failed."""

    def _write_story(self, collection_dir: pathlib.Path, name: str, body: str) -> None:
        # Bucket layout (PROP-LCATS-STORY-BUCKET-LAYOUT, retracted flat
        # support): a story is <collection>/<story>/story.json, not a flat
        # <story>.json file directly in the collection directory.
        story_dir = collection_dir / name
        story_dir.mkdir(parents=True)
        (story_dir / "story.json").write_text(
            json.dumps({"name": name, "author": "Test Author", "body": body}),
            encoding="utf-8",
        )

    def test_unexpected_exception_on_one_story_preserves_other_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = pathlib.Path(tmp) / "data"
            collection_dir = data_dir / "test_collection"
            collection_dir.mkdir(parents=True)
            output_dir = pathlib.Path(tmp) / "results"
            self._write_story(collection_dir, "story_a", "Story A body text.")
            self._write_story(collection_dir, "story_b", "Story B body text.")

            real_row = {
                "path": str(collection_dir / "story_a" / "story.json"),
                "story_id": "test_collection__story_a",
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
                if path.parent.name == "story_b":
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
            self.assertIn("test_collection__story_a", rows_by_story_id)
            self.assertFalse(rows_by_story_id["test_collection__story_a"]["excluded"])

            # story_b is recorded as excluded with the unexpected error,
            # not silently dropped and not aborting the whole run.
            self.assertIn("test_collection__story_b", rows_by_story_id)
            self.assertTrue(rows_by_story_id["test_collection__story_b"]["excluded"])
            self.assertIn(
                "unexpected error",
                rows_by_story_id["test_collection__story_b"]["exclude_reason"],
            )
            self.assertIn(
                "simulated unexpected per-story failure",
                rows_by_story_id["test_collection__story_b"]["exclude_reason"],
            )


class TestCheckpointedResumability(unittest.TestCase):
    """WI-PIPELINE-0041: run_story()'s stages (segment, erw_extract,
    cross_segment_relation) are checkpointed independently. This class
    proves, against the real pipeline stages (not mocked returns), that:
    a bounded small-scale trial makes only the expected number of LLM
    calls; a KeyboardInterrupt mid-run (not an ordinary Exception, per the
    review finding that a fake-backend test using a plain Exception does
    not exercise the real Ctrl-C escape path - run_pilot.py's own
    per-story except Exception in main() would otherwise swallow it)
    preserves every already-completed stage's checkpoint; and a second,
    resumed run does not re-issue an already-checkpointed stage's LLM
    call.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp_dir = pathlib.Path(self._tmp.name)
        self.data_dir = tmp_dir / "data" / "test_collection" / "story_a"
        self.data_dir.mkdir(parents=True)
        self.story_path = self.data_dir / "story.json"
        self.story_path.write_text(
            json.dumps(
                {
                    "name": "story_a",
                    "author": "Test Author",
                    "body": "The old machine hummed. It shut off forever.",
                }
            ),
            encoding="utf-8",
        )
        self.working_root = tmp_dir / "results"
        self.roots = run_pilot.checkpoint.resolve_roots(self.working_root)

    def tearDown(self):
        self._tmp.cleanup()

    def _segment_tool_result(self):
        return {
            "segments": [
                {
                    "segment_id": 1,
                    "segment_type": "narrative_scene",
                    "start_par_id": 1,
                    "end_par_id": 1,
                    "start_exact": "The old machine hummed.",
                    "end_exact": "It shut off forever.",
                    "start_prefix": "",
                    "end_suffix": "",
                    "start_char": 0,
                    "end_char": 45,
                    "summary": "A machine stops.",
                    "cohesion": {"time": "", "place": "", "characters": []},
                    "gacd": None,
                    "erac": None,
                    "reason": "Single scene.",
                    "confidence": 0.9,
                }
            ]
        }

    def _make_fake(self):
        return _SequencedFakeBackend(
            [
                self._segment_tool_result(),  # segment (call 1)
                {"entities": []},  # erw_extract: entity (call 2)
                {"events": []},  # erw_extract: event (call 3)
                {},  # erw_extract: relation (call 4)
                {},  # erw_extract: discourse (call 5)
                # No story_relation call: a single segment never satisfies
                # the >= 2-segments-with-events gate, so the
                # cross_segment_relation stage is a no-op here - this test
                # is about segment/erw_extract checkpointing specifically.
            ]
        )

    def _run_one_story(self, fake, roots=None):
        extractors = run_pilot._build_erw_extractors(fake, "fake-model")
        nlp_backend = run_pilot._make_nlp_backend("fake")
        return run_pilot.run_story(
            self.story_path,
            "science fiction",
            fake,
            "fake-model",
            "fake",
            roots if roots is not None else self.roots,
            extractors,
            nlp_backend,
            "fake",
            dry_run=False,
        )

    def test_bounded_small_scale_trial_makes_expected_call_count(self):
        """A single-story, single-segment trial makes exactly the 5 LLM
        calls this scenario needs (segment + entity/event/relation/
        discourse) - nowhere near "a few dozen", let alone the ~98-479
        calls this session measured for a real full-sample run."""
        fake = self._make_fake()

        row, usage_rows = self._run_one_story(fake)

        self.assertFalse(row["excluded"], row.get("exclude_reason"))
        self.assertEqual(len(fake.calls), 5)

    def test_keyboard_interrupt_mid_run_preserves_completed_stage_checkpoints(self):
        """A KeyboardInterrupt raised during the ERW-extraction stage still
        leaves the already-completed segmentation checkpoint on disk,
        untouched - not just "some file survives", but specifically the
        stage that had already succeeded before the interruption."""
        fake = self._make_fake()

        with patch.object(
            run_pilot, "_run_erw_extraction", side_effect=KeyboardInterrupt
        ):
            with self.assertRaises(KeyboardInterrupt):
                self._run_one_story(fake)

        item_id = run_pilot._story_identity(self.story_path)
        body = run_pilot.story_analysis.coerce_text(
            json.loads(self.story_path.read_text(encoding="utf-8"))["body"]
        )
        segment_result = run_pilot.checkpoint.read_checkpoint(
            self.working_root,
            item_id,
            "segment",
            run_pilot._stage_fingerprint("fake-model", "fake", upstream=body),
        )
        self.assertTrue(segment_result.done)

        erw_extract_path = run_pilot.checkpoint.checkpoint_path(
            self.working_root, item_id, "erw_extract"
        )
        self.assertFalse(erw_extract_path.exists())

        # Only the segmentation call happened before the interrupt.
        self.assertEqual(len(fake.calls), 1)

    def test_resumed_run_does_not_reissue_completed_stage_calls(self):
        """After the KeyboardInterrupt scenario above, a second, fresh
        run_story() call (same roots, same story - i.e. a real process
        restart) must not re-issue the segmentation LLM call, since a
        valid checkpoint already exists for it. The shared
        _SequencedFakeBackend proves this directly: if segmentation were
        wrongly re-issued, its result list (which has exactly one
        segmentation result left) would be exhausted by the wrong call,
        and the real entity/event/relation/discourse calls would get the
        segmentation result instead, or the sequence would run out
        entirely and raise IndexError.
        """
        fake = self._make_fake()

        with patch.object(
            run_pilot, "_run_erw_extraction", side_effect=KeyboardInterrupt
        ):
            with self.assertRaises(KeyboardInterrupt):
                self._run_one_story(fake)

        self.assertEqual(len(fake.calls), 1)

        # Resume: a fresh call, no more patching - _run_erw_extraction runs
        # for real this time, but segmentation must be skipped via its
        # checkpoint, so only the 4 ERW-extraction calls should follow.
        row, usage_rows = self._run_one_story(fake)

        self.assertFalse(row["excluded"], row.get("exclude_reason"))
        self.assertEqual(len(fake.calls), 5)

        item_id = run_pilot._story_identity(self.story_path)
        erw_extract_path = run_pilot.checkpoint.checkpoint_path(
            self.working_root, item_id, "erw_extract"
        )
        self.assertTrue(erw_extract_path.exists())


class TestErwExtractFailureIsNotCheckpointedAsDone(unittest.TestCase):
    """A story whose ERW-extraction pass surfaces extraction_errors must
    not be checkpointed as outcome="success" - a resumed run should retry
    it, not serve a transient failure forever as if it were done (review
    finding, PR #217)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp_dir = pathlib.Path(self._tmp.name)
        self.data_dir = tmp_dir / "data" / "test_collection" / "story_a"
        self.data_dir.mkdir(parents=True)
        self.story_path = self.data_dir / "story.json"
        self.story_path.write_text(
            json.dumps(
                {
                    "name": "story_a",
                    "author": "Test Author",
                    "body": "The old machine hummed.",
                }
            ),
            encoding="utf-8",
        )
        self.working_root = tmp_dir / "results"
        self.roots = run_pilot.checkpoint.resolve_roots(self.working_root)

    def tearDown(self):
        self._tmp.cleanup()

    def _fake_extraction_result(self, with_error: bool):
        return {
            "segments": [{"segment_id": 1, "extraction_errors": []}],
            "usage": [],
            "story": {
                "extraction_errors": ["boom: entity call failed"] if with_error else []
            },
            "processed_segment_count": 1,
            "segment_ids_with_events": [],
            "_story_obj": None,
        }

    def test_extraction_errors_write_failure_outcome_not_success(self):
        fake = _SequencedFakeBackend([{"segments": [{"segment_id": 1}]}])
        extractors = run_pilot._build_erw_extractors(fake, "fake-model")
        nlp_backend = run_pilot._make_nlp_backend("fake")

        with patch.object(
            run_pilot,
            "_run_erw_extraction",
            return_value=self._fake_extraction_result(with_error=True),
        ):
            row, _usage = run_pilot.run_story(
                self.story_path,
                "science fiction",
                fake,
                "fake-model",
                "fake",
                self.roots,
                extractors,
                nlp_backend,
                "fake",
                dry_run=True,
            )

        self.assertTrue(row["excluded"])

        item_id = run_pilot._story_identity(self.story_path)
        # Read back whatever was actually written - what matters is that
        # the outcome is "failure", not the exact fingerprint shape.
        checkpoint_path = run_pilot.checkpoint.checkpoint_path(
            self.working_root, item_id, "erw_extract"
        )
        self.assertTrue(checkpoint_path.exists())
        written = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        self.assertEqual(written["outcome"], "failure")


class TestSegmentationFingerprintInvalidation(unittest.TestCase):
    """A resumed run under a DIFFERENT model configuration must not honor
    an existing checkpoint written under the old one - Decision 2's
    configuration-identity requirement, applied at the "segment" stage
    specifically."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp_dir = pathlib.Path(self._tmp.name)
        self.data_dir = tmp_dir / "data" / "test_collection" / "story_a"
        self.data_dir.mkdir(parents=True)
        self.story_path = self.data_dir / "story.json"
        self.working_root = tmp_dir / "results"
        self.roots = run_pilot.checkpoint.resolve_roots(self.working_root)

    def tearDown(self):
        self._tmp.cleanup()

    def _segment_tool_result(self):
        return {
            "segments": [
                {
                    "segment_id": 1,
                    "segment_type": "narrative_scene",
                    "start_par_id": 1,
                    "end_par_id": 1,
                    "start_exact": "Once.",
                    "end_exact": "Once.",
                    "start_prefix": "",
                    "end_suffix": "",
                    "start_char": 0,
                    "end_char": 5,
                    "summary": "Intro.",
                    "cohesion": {"time": "", "place": "", "characters": []},
                    "gacd": None,
                    "erac": None,
                    "reason": "Setup.",
                    "confidence": 0.7,
                }
            ]
        }

    def test_different_model_does_not_reuse_old_checkpoint(self):
        from lcats.llm import fake_backend

        fake_1 = fake_backend.FakeBackend(tool_result=self._segment_tool_result())
        run_pilot._segment_story_cached(
            self.story_path, "Once.", fake_1, "model-a", "fake", self.roots
        )
        self.assertEqual(len(fake_1.calls), 1)

        fake_2 = fake_backend.FakeBackend(tool_result=self._segment_tool_result())
        run_pilot._segment_story_cached(
            self.story_path, "Once.", fake_2, "model-b", "fake", self.roots
        )

        # A different model must force a real re-issue, not reuse
        # model-a's checkpoint.
        self.assertEqual(len(fake_2.calls), 1)

    def test_same_model_reuses_existing_checkpoint(self):
        from lcats.llm import fake_backend

        fake_1 = fake_backend.FakeBackend(tool_result=self._segment_tool_result())
        run_pilot._segment_story_cached(
            self.story_path, "Once.", fake_1, "model-a", "fake", self.roots
        )
        self.assertEqual(len(fake_1.calls), 1)

        fake_2 = fake_backend.FakeBackend(tool_result=self._segment_tool_result())
        run_pilot._segment_story_cached(
            self.story_path, "Once.", fake_2, "model-a", "fake", self.roots
        )

        # Same model configuration - the checkpoint should be honored, so
        # fake_2 is never actually called.
        self.assertEqual(len(fake_2.calls), 0)


class TestGenreDetectCheckpointing(unittest.TestCase):
    """build_stratified_sample checkpoints each real genre-detect call
    under stage "genre_detect", so a resumed scan (same --seed) does not
    re-classify an already-scanned candidate."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp_dir = pathlib.Path(self._tmp.name)
        self.data_dir = tmp_dir / "data"
        collection_dir = self.data_dir / "test_collection"
        collection_dir.mkdir(parents=True)
        for name, body in [
            ("story_1", "A tale of science and machines."),
            ("story_2", "A tale of ghosts and dread."),
        ]:
            story_dir = collection_dir / name
            story_dir.mkdir()
            (story_dir / "story.json").write_text(
                json.dumps({"name": name, "author": "A", "body": body}),
                encoding="utf-8",
            )
        self.working_root = tmp_dir / "results"
        self.roots = run_pilot.checkpoint.resolve_roots(self.working_root)

    def tearDown(self):
        self._tmp.cleanup()

    def test_resumed_scan_does_not_reclassify_already_scanned_candidates(self):
        call_count = {"n": 0}

        def fake_assess_story(path, backend=None, model=None):
            call_count["n"] += 1
            from lcats.analysis.corpus import assess as corpus_assess

            return corpus_assess.AssessmentResult(
                file_path=str(path),
                title=path.parent.name,
                author="Test Author",
                url="",
                target_genre="",
                verdict="include",
                detected_genre="science fiction",
                error="",
            )

        with patch.object(
            run_pilot.corpus_assess, "assess_story", side_effect=fake_assess_story
        ):
            run_pilot.build_stratified_sample(
                self.data_dir,
                backend=None,
                model="model-a",
                backend_name="fake",
                roots=self.roots,
                sample_size=1,
                max_candidates=10,
                seed=1,
                dry_run=False,
            )
        first_run_calls = call_count["n"]
        self.assertGreater(first_run_calls, 0)

        # Resume: same seed (same scan order), same model - every
        # candidate scanned the first time should now be served from its
        # genre_detect checkpoint instead of calling assess_story again.
        with patch.object(
            run_pilot.corpus_assess, "assess_story", side_effect=fake_assess_story
        ):
            run_pilot.build_stratified_sample(
                self.data_dir,
                backend=None,
                model="model-a",
                backend_name="fake",
                roots=self.roots,
                sample_size=1,
                max_candidates=10,
                seed=1,
                dry_run=False,
            )

        self.assertEqual(call_count["n"], first_run_calls)


class TestFindJsonFilesDiscoverySelector(unittest.TestCase):
    """WI-PIPELINE-0041: _iter_candidate_files uses discovery.find_json_files
    (bucket-aware, multi-collection) instead of a bare recursive
    data_dir.rglob("*.json") - the latter would misread sidecar files as
    spurious stories once data/ is populated by the bucket-writing
    DataGatherer, and discovery.iter_collection_story_files (the WI's
    original, review-corrected scope draft) only examines a single
    collection's immediate children, yielding nothing on a multi-
    collection corpus root like the real --data-dir default (review
    finding, PR #210)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.data_dir = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _write_story(self, collection: str, story: str) -> None:
        story_dir = self.data_dir / collection / story
        story_dir.mkdir(parents=True)
        (story_dir / "story.json").write_text(
            json.dumps({"name": story, "author": "A", "body": "Body text."}),
            encoding="utf-8",
        )

    def test_discovers_stories_across_multiple_collections(self):
        """A corpus root with more than one collection directory must have
        every collection's stories discovered - not just the first one
        found, and not zero, per PR #210's review finding."""
        self._write_story("collection_a", "story_1")
        self._write_story("collection_b", "story_2")

        files = run_pilot._iter_candidate_files(self.data_dir, seed=1)

        self.assertEqual(len(files), 2)

    def test_ignores_sidecar_files_alongside_story_json(self):
        """A sidecar file (e.g. audit.json) inside a story's own bucket
        directory must not be misread as a second, separate story."""
        self._write_story("collection_a", "story_1")
        sidecar_path = self.data_dir / "collection_a" / "story_1" / "audit.json"
        sidecar_path.write_text(json.dumps({"findings": []}), encoding="utf-8")

        files = run_pilot._iter_candidate_files(self.data_dir, seed=1)

        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].name, "story.json")


class TestSegmentationUsageRecording(unittest.TestCase):
    """WI-PILOT-0051: run_story()'s usage_rows must include a
    pass_name="segment" PassUsage-style entry with the real (fake-backend)
    token counts - closing backlog P2 (pilot_usage.jsonl previously had no
    record of segmentation cost at all) - and a cache-hit replay must NOT
    add a second entry (would double-count the original call's cost, per
    this item's own Risk Notes)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp_dir = pathlib.Path(self._tmp.name)
        self.data_dir = tmp_dir / "data" / "test_collection" / "story_a"
        self.data_dir.mkdir(parents=True)
        self.story_path = self.data_dir / "story.json"
        self.story_path.write_text(
            json.dumps(
                {
                    "name": "story_a",
                    "author": "Test Author",
                    "body": "The old machine hummed. It shut off forever.",
                }
            ),
            encoding="utf-8",
        )
        self.working_root = tmp_dir / "results"
        self.roots = run_pilot.checkpoint.resolve_roots(self.working_root)

    def tearDown(self):
        self._tmp.cleanup()

    def _segment_tool_result(self):
        return {
            "segments": [
                {
                    "segment_id": 1,
                    "segment_type": "narrative_scene",
                    "start_par_id": 1,
                    "end_par_id": 1,
                    "start_exact": "The old machine hummed.",
                    "end_exact": "It shut off forever.",
                    "start_prefix": "",
                    "end_suffix": "",
                    "start_char": 0,
                    "end_char": 45,
                    "summary": "A machine stops.",
                    "cohesion": {"time": "", "place": "", "characters": []},
                    "gacd": None,
                    "erac": None,
                    "reason": "Single scene.",
                    "confidence": 0.9,
                }
            ]
        }

    def _make_fake(self):
        return _SequencedFakeBackend(
            [
                self._segment_tool_result(),  # segment (call 1)
                {"entities": []},  # erw_extract: entity (call 2)
                {"events": []},  # erw_extract: event (call 3)
                {},  # erw_extract: relation (call 4)
                {},  # erw_extract: discourse (call 5)
            ]
        )

    def _run_one_story(self, fake, roots=None):
        extractors = run_pilot._build_erw_extractors(fake, "fake-model")
        nlp_backend = run_pilot._make_nlp_backend("fake")
        return run_pilot.run_story(
            self.story_path,
            "science fiction",
            fake,
            "fake-model",
            "fake",
            roots if roots is not None else self.roots,
            extractors,
            nlp_backend,
            "fake",
            dry_run=False,
        )

    def test_fresh_call_records_segment_pass_usage(self):
        fake = self._make_fake()

        row, usage_rows = self._run_one_story(fake)

        self.assertFalse(row["excluded"], row.get("exclude_reason"))
        segment_usages = [u for u in usage_rows if u["pass_name"] == "segment"]
        self.assertEqual(len(segment_usages), 1)
        usage = segment_usages[0]
        self.assertTrue(usage["is_llm_backed"])
        self.assertEqual(usage["model"], "fake-model")
        self.assertEqual(usage["input_tokens"], 5)  # _SequencedFakeBackend default
        self.assertEqual(usage["output_tokens"], 2)
        self.assertEqual(usage["story_id"], run_pilot._story_identity(self.story_path))
        self.assertEqual(usage["genre"], "science fiction")

    def test_cache_hit_does_not_duplicate_segment_usage(self):
        fake_1 = self._make_fake()
        self._run_one_story(fake_1)

        # A fresh backend with only the 4 ERW-extraction results left -
        # if segmentation were wrongly re-issued (cache miss), this would
        # raise IndexError; if the cache is honored but a usage row is
        # wrongly still emitted, the test below catches that instead.
        fake_2 = _SequencedFakeBackend(
            [
                {"entities": []},
                {"events": []},
                {},
                {},
            ]
        )
        row, usage_rows = self._run_one_story(fake_2)

        self.assertFalse(row["excluded"], row.get("exclude_reason"))
        segment_usages = [u for u in usage_rows if u["pass_name"] == "segment"]
        self.assertEqual(
            len(segment_usages),
            0,
            "a cache-hit replay must not add a new segment usage row",
        )


class TestTargetedStoryResolution(unittest.TestCase):
    """WI-PILOT-0051: _resolve_target_story and _parse_story_list, the
    path-resolution and manifest-parsing helpers behind --story and
    --story-list."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp_dir = pathlib.Path(self._tmp.name)
        self.data_dir = tmp_dir / "data"
        self.fixtures_dir = tmp_dir / "fixtures"
        (self.data_dir / "test_collection" / "story_a").mkdir(parents=True)
        (self.fixtures_dir / "fixture_story").mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def test_resolves_against_data_dir_by_default(self):
        path = run_pilot._resolve_target_story(
            "test_collection/story_a", self.data_dir, self.fixtures_dir
        )
        self.assertEqual(
            path, self.data_dir / "test_collection" / "story_a" / "story.json"
        )

    def test_fixtures_prefix_resolves_against_fixtures_dir(self):
        path = run_pilot._resolve_target_story(
            "fixtures/fixture_story", self.data_dir, self.fixtures_dir
        )
        self.assertEqual(path, self.fixtures_dir / "fixture_story" / "story.json")

    def test_parse_story_list_resolves_entries_in_order(self):
        list_path = self.data_dir / "manifest.txt"
        list_path.write_text(
            "# comment\n"
            "\n"
            "fixtures/fixture_story:science fiction\n"
            "test_collection/story_a:horror\n",
            encoding="utf-8",
        )

        pairs = run_pilot._parse_story_list(list_path, self.data_dir, self.fixtures_dir)

        self.assertEqual(
            pairs,
            [
                (
                    "science fiction",
                    self.fixtures_dir / "fixture_story" / "story.json",
                ),
                (
                    "horror",
                    self.data_dir / "test_collection" / "story_a" / "story.json",
                ),
            ],
        )

    def test_parse_story_list_rejects_malformed_line(self):
        list_path = self.data_dir / "manifest.txt"
        list_path.write_text("no_colon_here\n", encoding="utf-8")

        with self.assertRaises(ValueError):
            run_pilot._parse_story_list(list_path, self.data_dir, self.fixtures_dir)

    def test_parse_story_list_rejects_unknown_genre(self):
        list_path = self.data_dir / "manifest.txt"
        list_path.write_text("test_collection/story_a:mystery\n", encoding="utf-8")

        with self.assertRaises(ValueError):
            run_pilot._parse_story_list(list_path, self.data_dir, self.fixtures_dir)


class TestMainTargetedMode(unittest.TestCase):
    """WI-PILOT-0051: end-to-end --story/--story-list runs through the
    real main() CLI path (argv patched, --dry-run for zero real API
    cost) - not just calling internal functions directly, per this item's
    own Risk Notes on tests needing to exercise the real targeted-story
    code path."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp_dir = pathlib.Path(self._tmp.name)
        self.data_dir = tmp_dir / "data"
        self.output_dir = tmp_dir / "results"
        story_dir = self.data_dir / "test_collection" / "story_a"
        story_dir.mkdir(parents=True)
        (story_dir / "story.json").write_text(
            json.dumps({"name": "story_a", "author": "A", "body": "Body text."}),
            encoding="utf-8",
        )

    def tearDown(self):
        self._tmp.cleanup()

    def test_story_list_default_runs_committed_fixture_set(self):
        """--story-list with no FILE argument must run this repo's own
        committed fixtures/manifest.txt end to end, at zero real API
        cost, and must never call build_stratified_sample (the 200-
        candidate genre-detect scan --story/--story-list exists to
        bypass)."""
        argv = [
            "run_pilot.py",
            "--dry-run",
            "--story-list",
            "--output",
            str(self.output_dir),
        ]
        with patch.object(sys, "argv", argv), patch.object(
            run_pilot,
            "build_stratified_sample",
            side_effect=AssertionError(
                "build_stratified_sample must not be called in targeted mode"
            ),
        ):
            exit_code = run_pilot.main()

        self.assertEqual(exit_code, 0)
        stories_path = self.output_dir / "pilot_stories.jsonl"
        rows = [
            json.loads(line)
            for line in stories_path.read_text(encoding="utf-8").splitlines()
        ]
        story_ids = {row["story_id"] for row in rows}
        # Both fixtures/manifest.txt entries (WI-PILOT-0051).
        self.assertEqual(
            story_ids,
            {"fixtures__king_of_the_hill", "fixtures__five_o_clock_tea_farce"},
        )

    def test_story_targets_exactly_one_story(self):
        argv = [
            "run_pilot.py",
            "--dry-run",
            "--story",
            "test_collection/story_a",
            "--genre",
            "science fiction",
            "--data-dir",
            str(self.data_dir),
            "--output",
            str(self.output_dir),
        ]
        with patch.object(sys, "argv", argv), patch.object(
            run_pilot,
            "build_stratified_sample",
            side_effect=AssertionError(
                "build_stratified_sample must not be called in targeted mode"
            ),
        ):
            exit_code = run_pilot.main()

        self.assertEqual(exit_code, 0)
        stories_path = self.output_dir / "pilot_stories.jsonl"
        rows = [
            json.loads(line)
            for line in stories_path.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["story_id"], "test_collection__story_a")
        self.assertEqual(rows[0]["genre"], "science fiction")

    def test_story_without_genre_errors_before_any_work(self):
        argv = [
            "run_pilot.py",
            "--dry-run",
            "--story",
            "test_collection/story_a",
            "--data-dir",
            str(self.data_dir),
            "--output",
            str(self.output_dir),
        ]
        with patch.object(sys, "argv", argv):
            exit_code = run_pilot.main()

        self.assertEqual(exit_code, 1)
        self.assertFalse((self.output_dir / "pilot_stories.jsonl").exists())

    def test_story_and_story_list_are_mutually_exclusive(self):
        argv = [
            "run_pilot.py",
            "--dry-run",
            "--story",
            "test_collection/story_a",
            "--genre",
            "science fiction",
            "--story-list",
            "--data-dir",
            str(self.data_dir),
            "--output",
            str(self.output_dir),
        ]
        with patch.object(sys, "argv", argv):
            exit_code = run_pilot.main()

        self.assertEqual(exit_code, 1)

    def test_story_list_pointing_at_a_directory_errors_cleanly(self):
        """A --story-list path that exists but is a directory must fail
        with a clean error message and exit code 1, not an unhandled
        OSError/IsADirectoryError stack trace (review finding, PR #244)."""
        list_dir = self.data_dir / "not_a_file"
        list_dir.mkdir()
        argv = [
            "run_pilot.py",
            "--dry-run",
            "--story-list",
            str(list_dir),
            "--data-dir",
            str(self.data_dir),
            "--output",
            str(self.output_dir),
        ]
        with patch.object(sys, "argv", argv):
            exit_code = run_pilot.main()

        self.assertEqual(exit_code, 1)
        self.assertFalse((self.output_dir / "pilot_stories.jsonl").exists())

    def test_story_list_file_named_like_the_internal_sentinel_is_not_misread(self):
        """A real manifest file whose name happens to collide with the
        internal argparse sentinel string must still be read as that real
        file, not silently redirected to the fixture set (review finding,
        PR #244 - the sentinel is now a distinct object(), not a string,
        specifically so this can't happen)."""
        list_path = self.data_dir / "__FIXTURES_DEFAULT__"
        list_path.write_text("test_collection/story_a:horror\n", encoding="utf-8")
        argv = [
            "run_pilot.py",
            "--dry-run",
            "--story-list",
            str(list_path),
            "--data-dir",
            str(self.data_dir),
            "--output",
            str(self.output_dir),
        ]
        with patch.object(sys, "argv", argv):
            exit_code = run_pilot.main()

        self.assertEqual(exit_code, 0)
        stories_path = self.output_dir / "pilot_stories.jsonl"
        rows = [
            json.loads(line)
            for line in stories_path.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["story_id"], "test_collection__story_a")
        self.assertEqual(rows[0]["genre"], "horror")


class TestSegmentationUsagePreservedOnUnexpectedException(unittest.TestCase):
    """WI-PILOT-0051 review finding (PR #244): an unexpected (non-
    FatalPilotError) exception raised after a real segmentation call
    succeeded must not silently drop that already-paid-for cost from the
    usage_rows _run_stories returns."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp_dir = pathlib.Path(self._tmp.name)
        self.story_dir = tmp_dir / "data" / "test_collection" / "story_a"
        self.story_dir.mkdir(parents=True)
        self.story_path = self.story_dir / "story.json"
        self.story_path.write_text(
            json.dumps(
                {
                    "name": "story_a",
                    "author": "Test Author",
                    "body": "The old machine hummed. It shut off forever.",
                }
            ),
            encoding="utf-8",
        )
        self.working_root = tmp_dir / "results"
        self.roots = run_pilot.checkpoint.resolve_roots(self.working_root)

    def tearDown(self):
        self._tmp.cleanup()

    def _segment_tool_result(self):
        return {
            "segments": [
                {
                    "segment_id": 1,
                    "segment_type": "narrative_scene",
                    "start_par_id": 1,
                    "end_par_id": 1,
                    "start_exact": "The old machine hummed.",
                    "end_exact": "It shut off forever.",
                    "start_prefix": "",
                    "end_suffix": "",
                    "start_char": 0,
                    "end_char": 45,
                    "summary": "A machine stops.",
                    "cohesion": {"time": "", "place": "", "characters": []},
                    "gacd": None,
                    "erac": None,
                    "reason": "Single scene.",
                    "confidence": 0.9,
                }
            ]
        }

    def test_unexpected_exception_after_segmentation_preserves_its_usage(self):
        fake = _SequencedFakeBackend([self._segment_tool_result()])
        extractors = run_pilot._build_erw_extractors(fake, "fake-model")
        nlp_backend = run_pilot._make_nlp_backend("fake")

        with patch.object(
            run_pilot,
            "_run_erw_extraction",
            side_effect=RuntimeError("simulated unexpected mid-pipeline failure"),
        ), run_pilot.run_log.RunLog(self.roots, "pilot_run_log.jsonl") as log:
            rows, usage_rows, aborted = run_pilot._run_stories(
                [("science fiction", self.story_path)],
                fake,
                "fake-model",
                "fake",
                self.roots,
                extractors,
                nlp_backend,
                "fake",
                None,
                dry_run=False,
                log=log,
            )

        self.assertFalse(aborted)
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["excluded"])
        self.assertIn("unexpected error", rows[0]["exclude_reason"])

        # The segmentation call that already succeeded (and was paid for)
        # before the simulated failure must still be recorded, not lost.
        segment_usages = [u for u in usage_rows if u["pass_name"] == "segment"]
        self.assertEqual(len(segment_usages), 1)
        self.assertEqual(segment_usages[0]["input_tokens"], 5)
        self.assertEqual(segment_usages[0]["output_tokens"], 2)


class TestCappedExcludeReason(unittest.TestCase):
    """WI-EVENT-0061: a container-type extraction error (schema.
    coerce_list_field) can produce many joined item_errors for one story;
    the console print must be capped so it can't flood the terminal, while
    the stored row value stays uncapped for later analysis."""

    def test_short_reason_is_unchanged(self):
        reason = "empty story body"
        self.assertEqual(run_pilot._capped_exclude_reason(reason), reason)

    def test_long_reason_is_truncated_with_more_count_suffix(self):
        errors = [
            f"speech_acts[{i}] is not an object (got str): 'x'" for i in range(50)
        ]
        reason = "; ".join(errors)
        self.assertGreater(len(reason), run_pilot._EXCLUDE_REASON_PRINT_MAX_CHARS)

        capped = run_pilot._capped_exclude_reason(reason)

        self.assertLess(len(capped), len(reason))
        self.assertRegex(capped, r"\.\.\.\d+ more errors?$")

    def test_reason_at_exactly_the_limit_is_unchanged(self):
        reason = "x" * run_pilot._EXCLUDE_REASON_PRINT_MAX_CHARS
        self.assertEqual(run_pilot._capped_exclude_reason(reason), reason)

    def test_single_long_message_does_not_claim_nonexistent_more_errors(self):
        """Regression test (self-review finding, WI-EVENT-0061): a single
        message longer than the cap, with no "; "-joined sibling errors,
        must not be suffixed "...1 more error" -- there is no second
        error, just one long message that got truncated."""
        reason = "a" * (run_pilot._EXCLUDE_REASON_PRINT_MAX_CHARS + 50)
        capped = run_pilot._capped_exclude_reason(reason)
        self.assertNotRegex(capped, r"more errors?")
        self.assertTrue(capped.endswith("...(truncated)"))

    def test_cutoff_within_final_segment_does_not_claim_nonexistent_more_errors(
        self,
    ):
        """Regression test (Copilot review, PR #274): if the char-count cap
        falls inside the LAST "; "-joined segment (all separators are
        already included in the truncated text), no segment was actually
        omitted -- only the last one's text was cut short. This must not
        be reported as "...N more errors" for any N >= 1; a naive
        `max(total - shown, 1)` floor previously fabricated "...1 more
        error" here even though there is no additional error."""
        head = "; ".join(f"error{i}" for i in range(3))
        long_last_segment = "x" * (run_pilot._EXCLUDE_REASON_PRINT_MAX_CHARS + 100)
        reason = f"{head}; {long_last_segment}"

        capped = run_pilot._capped_exclude_reason(reason)

        self.assertNotRegex(capped, r"more errors?")
        self.assertTrue(capped.endswith("...(truncated)"))


class TestRunLogging(unittest.TestCase):
    """WI-RUNLOG-0080: run_pilot.py gets a crash-safe, incremental run-event
    log (via lcats.utils.run_log.RunLog) closing the gap that
    WI-EVENT-0032's exception-handling fix alone does not - a hard kill
    mid-run still discarded everything in memory, even though per-item
    checkpointing already existed."""

    def _write_story(self, collection_dir: pathlib.Path, name: str, body: str) -> None:
        story_dir = collection_dir / name
        story_dir.mkdir(parents=True)
        (story_dir / "story.json").write_text(
            json.dumps({"name": name, "author": "Test Author", "body": body}),
            encoding="utf-8",
        )

    def test_run_log_records_start_and_per_story_and_end_in_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = pathlib.Path(tmp) / "data"
            collection_dir = data_dir / "test_collection"
            collection_dir.mkdir(parents=True)
            output_dir = pathlib.Path(tmp) / "results"
            self._write_story(collection_dir, "story_a", "Story A body text.")

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
            with patch.object(sys, "argv", argv):
                exit_code = run_pilot.main()

            self.assertEqual(exit_code, 0)
            log_path = output_dir / "pilot_run_log.jsonl"
            self.assertTrue(log_path.exists())
            events = [
                json.loads(line)
                for line in log_path.read_text(encoding="utf-8").splitlines()
            ]
            event_names = [e["event"] for e in events]
            self.assertEqual(event_names[0], "run_start")
            self.assertEqual(event_names[-1], "run_end")
            self.assertFalse(events[-1]["aborted"])
            self.assertEqual(events[-1]["processed_count"], 1)
            self.assertIn("story_completed", event_names)
            story_events = [e for e in events if e["event"] == "story_completed"]
            self.assertEqual(story_events[0]["story_id"], "test_collection__story_a")

    def test_crash_mid_run_leaves_a_readable_partial_log(self):
        """A FatalPilotError partway through the run must not corrupt or
        truncate the already-written log entries - every line up to the
        abort remains valid, readable JSON, and a run_aborted_fatal event
        is recorded for the story that triggered it."""
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = pathlib.Path(tmp) / "data"
            collection_dir = data_dir / "test_collection"
            collection_dir.mkdir(parents=True)
            output_dir = pathlib.Path(tmp) / "results"
            self._write_story(collection_dir, "story_a", "Story A body text.")
            self._write_story(collection_dir, "story_b", "Story B body text.")

            # --story-list processes entries in file order (unlike the
            # full stratified-sample path, whose genre-detect scan order
            # isn't deterministic by filename) - needed here so story_a
            # reliably runs before story_b crashes the run.
            list_path = pathlib.Path(tmp) / "manifest.txt"
            list_path.write_text(
                "test_collection/story_a:science fiction\n"
                "test_collection/story_b:science fiction\n",
                encoding="utf-8",
            )

            real_row = {
                "path": "",
                "story_id": "test_collection__story_a",
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
                if path.parent.name == "story_b":
                    raise run_pilot.FatalPilotError("simulated fatal API failure")
                return dict(real_row), []

            argv = [
                "run_pilot.py",
                "--dry-run",
                "--story-list",
                str(list_path),
                "--data-dir",
                str(data_dir),
                "--output",
                str(output_dir),
            ]
            with patch.object(sys, "argv", argv), patch.object(
                run_pilot, "run_story", side_effect=fake_run_story
            ):
                exit_code = run_pilot.main()

            self.assertEqual(exit_code, 3)
            log_path = output_dir / "pilot_run_log.jsonl"
            lines = log_path.read_text(encoding="utf-8").splitlines()
            events = [json.loads(line) for line in lines]
            event_names = [e["event"] for e in events]
            self.assertEqual(event_names[0], "run_start")
            self.assertIn("story_completed", event_names)
            self.assertIn("run_aborted_fatal", event_names)
            fatal_event = next(e for e in events if e["event"] == "run_aborted_fatal")
            self.assertEqual(fatal_event["story_id"], "test_collection__story_b")
            # The manually-logged trailing run_end (not RunLog's bare
            # automatic one) still fires here since FatalPilotError is
            # caught inside _run_stories() rather than propagating out of
            # the `with` block - but it must carry aborted=True so the
            # log is distinguishable from a fully successful run without
            # scanning every earlier event (review finding, PR #371).
            self.assertEqual(event_names[-1], "run_end")
            self.assertTrue(events[-1]["aborted"])

    def test_output_write_failure_produces_run_aborted_unexpected_not_run_end(self):
        """WI-RUNLOG-0080's own scope (mirroring the review finding fixed
        for WI-RUNLOG-0079): the RunLog scope wraps the pilot_stories.jsonl/
        pilot_usage.jsonl write block, not just _run_stories() - a failure
        writing those files must produce run_aborted_unexpected, never a
        false run_end implying success."""
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = pathlib.Path(tmp) / "data"
            collection_dir = data_dir / "test_collection"
            collection_dir.mkdir(parents=True)
            output_dir = pathlib.Path(tmp) / "results"
            self._write_story(collection_dir, "story_a", "Story A body text.")

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
            # Only the pilot_stories.jsonl write itself fails - a blanket
            # Path.open patch would also break story reads inside
            # _run_stories() (Path.read_text() calls self.open()
            # internally), producing the failure at the wrong site.
            real_open = pathlib.Path.open

            def selective_open(self, *args, **kwargs):
                if self.name == "pilot_stories.jsonl":
                    raise OSError("simulated disk-full failure")
                return real_open(self, *args, **kwargs)

            with patch.object(sys, "argv", argv), patch.object(
                pathlib.Path, "open", selective_open
            ):
                with self.assertRaises(OSError):
                    run_pilot.main()

            log_path = output_dir / "pilot_run_log.jsonl"
            self.assertTrue(log_path.exists())
            events = [
                json.loads(line)
                for line in log_path.read_text(encoding="utf-8").splitlines()
            ]
            event_names = [e["event"] for e in events]
            self.assertNotIn("run_end", event_names)
            self.assertIn("run_aborted_unexpected", event_names)


if __name__ == "__main__":
    unittest.main()
