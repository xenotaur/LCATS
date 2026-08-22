"""Unit tests for lcats.analysis.corpus.annotate."""

import json
import pathlib
import tempfile
import unittest
import unittest.mock

from lcats.analysis.corpus import annotate, genre_sidecar
from lcats.utils import checkpoint

_GENRE_TOOL_RESULT = {
    "verdict": "include",
    "wellformed": True,
    "detected_genre": "science fiction",
    "detected_genre_confidence": 0.9,
    "genre_verdict": "detected",
    "specials_verdict": "none",
    "summary": "A story about a dragon.",
    "issues": [],
    "exclude_reason": "",
    "genre_suggestion": "",
    "secondary_genre": "",
}

_SEGMENT_TOOL_RESULT = {
    "segments": [
        {
            "segment_id": 1,
            "segment_type": "narrative_scene",
            "start_par_id": 1,
            "end_par_id": 1,
            # Deliberately empty: this fixture is reused across tests with
            # different story bodies ("Once upon a time there was a
            # dragon.", "A dragon story.", etc.). Empty anchors fall back
            # to paragraph bounds unconditionally (align_segment's
            # existing, unaffected contract) -- a hardcoded non-empty
            # anchor matching only one body used to silently "work" for
            # all of them under the old lenient fallback (a genuinely
            # unresolvable anchor fell back to paragraph bounds too, not
            # just an empty one); WI-SEGMENT-0059 correctly rejects that
            # case now, so this fixture must not rely on it.
            "start_exact": "",
            "end_exact": "",
            "start_prefix": "",
            "end_suffix": "",
            "start_char": None,
            "end_char": None,
            "summary": "A dragon appears.",
            "cohesion": {
                "time": "once upon a time",
                "place": "unspecified",
                "characters": ["dragon"],
            },
            "gacd": None,
            "erac": None,
            "reason": "Establishes setting.",
            "confidence": 0.8,
        }
    ]
}


class _DualToolFakeBackend:
    """Test double dispatching on tool["name"] -- annotate_story calls
    both assess_story (record_story_assessment) and make_segment_extractor
    (record_segments) through the same backend, so a single fixed
    tool_result (what FakeBackend provides) can't serve both.

    fail_genre_calls_after, if set, makes the Nth-and-later genre call
    return tool_result=None (assess_story's own "no tool result" failure
    path), for testing stale-sidecar-removal on a failed recompute.
    """

    def __init__(self, fail_genre_calls_after=None):
        self.calls = []
        self.fail_genre_calls_after = fail_genre_calls_after
        self._genre_call_count = 0

    def complete(
        self, *, system, messages, model, temperature=0.2, max_tokens=4096, tool=None
    ):
        from lcats.llm import backend as backend_module

        self.calls.append({"tool_name": tool["name"] if tool else None, "model": model})
        if tool and tool["name"] == "record_story_assessment":
            self._genre_call_count += 1
            if (
                self.fail_genre_calls_after is not None
                and self._genre_call_count > self.fail_genre_calls_after
            ):
                result = None
            else:
                result = _GENRE_TOOL_RESULT
        elif tool and tool["name"] == "record_segments":
            result = _SEGMENT_TOOL_RESULT
        else:
            result = None
        return backend_module.BackendResponse(
            text="",
            tool_result=result,
            model=model,
            input_tokens=0,
            output_tokens=0,
            raw=None,
        )


def _write_story(collection_dir: pathlib.Path, name: str, body: str) -> pathlib.Path:
    bucket_dir = collection_dir / name
    bucket_dir.mkdir(parents=True, exist_ok=True)
    story_path = bucket_dir / "story.json"
    story_path.write_text(
        json.dumps({"name": name, "body": body, "metadata": {}}),
        encoding="utf-8",
    )
    return story_path


class StoryItemIdTest(unittest.TestCase):
    def test_combines_collection_and_story(self):
        self.assertEqual(
            "sherlock__blue_carbuncle",
            annotate.story_item_id("sherlock", "blue_carbuncle"),
        )


class ErrorMessageTest(unittest.TestCase):
    """Regression coverage: str()-ing a structured api_error dict produces
    noisy Python-repr output and discards the clean message field (review
    finding, PR #241)."""

    def test_extracts_message_from_dict_error(self):
        error = {"status": 429, "code": "quota_exceeded", "message": "No credits."}
        self.assertEqual("No credits.", annotate._error_message(error))

    def test_falls_back_to_str_for_plain_string_error(self):
        self.assertEqual(
            "alignment failed: x", annotate._error_message("alignment failed: x")
        )


class AnnotateStoryTest(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.tmp_path = pathlib.Path(self._tmpdir.name)
        self.source_root = self.tmp_path / "data"
        self.checkpoint_dir = self.tmp_path / "checkpoints"
        self.source_root.mkdir()
        self.roots = checkpoint.resolve_roots(
            working_root=self.checkpoint_dir, source_root=self.source_root
        )

    def test_writes_genre_and_scenes_sidecars(self):
        story_path = _write_story(
            self.source_root / "collection_a",
            "story_one",
            "Once upon a time there was a dragon.",
        )
        backend = _DualToolFakeBackend()

        result = annotate.annotate_story(
            story_path,
            collection_name="collection_a",
            backend=backend,
            model="fake-model",
            roots=self.roots,
        )

        self.assertTrue(result.clean)
        bucket_dir = story_path.parent
        genre_data = json.loads((bucket_dir / "genre.json").read_text(encoding="utf-8"))
        # A fresh write is genre-sidecar-v1-shaped (WI-GENRE-0076), not
        # the legacy flat AssessmentResult.to_dict() shape -- the
        # detected genre lives nested under the one assessment's result.
        self.assertEqual("genre-sidecar-v1", genre_data["schema_version"])
        self.assertEqual(1, len(genre_data["assessments"]))
        self.assertEqual(
            "science fiction", genre_data["assessments"][0]["result"]["detected_genre"]
        )
        scenes_data = json.loads(
            (bucket_dir / "scenes.json").read_text(encoding="utf-8")
        )
        self.assertEqual(1, scenes_data["segment_count"])
        # scenes.json carries the same cost-visibility fields genre.json
        # already does, sourced from JSONPromptExtractor.extract()'s own
        # "usage" dict rather than left unrecorded (review finding, PR
        # #253).
        self.assertIn("input_tokens", scenes_data)
        self.assertIn("output_tokens", scenes_data)

    def test_writes_readme_summarizing_sidecars(self):
        story_path = _write_story(
            self.source_root / "collection_a", "story_one", "A dragon story."
        )
        backend = _DualToolFakeBackend()

        annotate.annotate_story(
            story_path,
            collection_name="collection_a",
            backend=backend,
            model="fake-model",
            roots=self.roots,
        )

        readme = (story_path.parent / "README.md").read_text(encoding="utf-8")
        self.assertIn("science fiction", readme)
        self.assertIn("segment_count", readme)

    def test_second_call_with_same_config_skips_api_calls(self):
        """Checkpoint hit: a resumed run under an unchanged config must not
        repeat the paid LLM calls."""
        story_path = _write_story(
            self.source_root / "collection_a", "story_one", "A dragon story."
        )
        backend = _DualToolFakeBackend()

        annotate.annotate_story(
            story_path,
            collection_name="collection_a",
            backend=backend,
            model="fake-model",
            roots=self.roots,
        )
        first_call_count = len(backend.calls)
        self.assertEqual(2, first_call_count)  # one genre call, one scenes call

        annotate.annotate_story(
            story_path,
            collection_name="collection_a",
            backend=backend,
            model="fake-model",
            roots=self.roots,
        )

        self.assertEqual(first_call_count, len(backend.calls))

    def test_changed_body_invalidates_checkpoint(self):
        """A corrected story must not silently serve a stale cache -- the
        fingerprint must hash the actual input, not just model config."""
        story_path = _write_story(
            self.source_root / "collection_a", "story_one", "First version."
        )
        backend = _DualToolFakeBackend()
        annotate.annotate_story(
            story_path,
            collection_name="collection_a",
            backend=backend,
            model="fake-model",
            roots=self.roots,
        )
        first_call_count = len(backend.calls)

        story_path.write_text(
            json.dumps(
                {
                    "name": "story_one",
                    "body": "A completely different revised story.",
                    "metadata": {},
                }
            ),
            encoding="utf-8",
        )
        annotate.annotate_story(
            story_path,
            collection_name="collection_a",
            backend=backend,
            model="fake-model",
            roots=self.roots,
        )

        self.assertGreater(len(backend.calls), first_call_count)

    def test_resumed_sidecar_rewritten_from_checkpoint_data(self):
        """Deleting the sidecar file (simulating an interrupted
        materialization step) must not force a re-paid API call -- the
        checkpoint's own stored data is the source of truth for re-writing
        it."""
        story_path = _write_story(
            self.source_root / "collection_a", "story_one", "A dragon story."
        )
        backend = _DualToolFakeBackend()
        annotate.annotate_story(
            story_path,
            collection_name="collection_a",
            backend=backend,
            model="fake-model",
            roots=self.roots,
        )
        call_count = len(backend.calls)
        (story_path.parent / "genre.json").unlink()

        annotate.annotate_story(
            story_path,
            collection_name="collection_a",
            backend=backend,
            model="fake-model",
            roots=self.roots,
        )

        self.assertEqual(call_count, len(backend.calls))
        self.assertTrue((story_path.parent / "genre.json").is_file())

    def test_valid_v1_sidecar_survives_a_failed_recompute(self):
        """A failed recompute must not delete an existing valid v1 ledger
        -- its prior assessments remain independently valid regardless of
        this later, unrelated attempt failing (review finding, PR #357;
        supersedes this test's own prior "always delete on failure"
        assertion, which predated append-mode semantics)."""
        story_path = _write_story(
            self.source_root / "collection_a", "story_one", "A dragon story."
        )
        backend = _DualToolFakeBackend(fail_genre_calls_after=1)
        annotate.annotate_story(
            story_path,
            collection_name="collection_a",
            backend=backend,
            model="fake-model",
            roots=self.roots,
        )
        genre_path = story_path.parent / "genre.json"
        first_write = json.loads(genre_path.read_text(encoding="utf-8"))
        self.assertEqual("genre-sidecar-v1", first_write["schema_version"])

        # A body change invalidates the checkpoint, forcing a real
        # recompute -- which this backend is configured to fail.
        story_path.write_text(
            json.dumps(
                {"name": "story_one", "body": "A different story now.", "metadata": {}}
            ),
            encoding="utf-8",
        )
        result = annotate.annotate_story(
            story_path,
            collection_name="collection_a",
            backend=backend,
            model="fake-model",
            roots=self.roots,
        )

        self.assertFalse(result.clean)
        self.assertIsNotNone(result.genre_error)
        # The prior valid ledger survives completely untouched -- not
        # deleted, not partially modified.
        self.assertTrue(genre_path.is_file())
        self.assertEqual(
            first_write, json.loads(genre_path.read_text(encoding="utf-8"))
        )

    def test_stale_legacy_sidecar_removed_when_recompute_fails(self):
        """A failed recompute over a pre-append-mode legacy sidecar (not
        yet migrated to v1) must still remove the stale file from a
        prior, differently-configured run -- the bucket would otherwise
        silently mix a new-config scenes.json with an old-config
        genre.json (review finding, PR #241); this narrower case is
        unaffected by the v1-ledger-survives fix above, since a legacy
        sidecar was never independently valid evidence the append
        mechanism itself vouches for."""
        story_path = _write_story(
            self.source_root / "collection_a", "story_one", "A dragon story."
        )
        genre_path = story_path.parent / "genre.json"
        genre_path.write_text(json.dumps(_REAL_LEGACY_FLAT_SIDECAR), encoding="utf-8")
        backend = _DualToolFakeBackend(fail_genre_calls_after=0)

        result = annotate.annotate_story(
            story_path,
            collection_name="collection_a",
            backend=backend,
            model="fake-model",
            roots=self.roots,
        )

        self.assertFalse(result.clean)
        self.assertIsNotNone(result.genre_error)
        self.assertFalse(genre_path.exists())


# A real genre-sidecar-v1 record actually produced by WI-GENRE-0004's
# gated validation run (experiments/05_metadata_genre_prefilter/results/
# full_scan/validation_results.jsonl, first line) -- used as a fixture
# per this item's own Required Change 3 ("replay real records ... rather
# than only synthetic examples") instead of a hand-built stand-in.
_REAL_V1_SIDECAR = {
    "schema_version": "genre-sidecar-v1",
    "lcats_id": "anderson/bell",
    "story_path": "anderson/bell/story.json",
    "assessments": [
        {
            "assessment_id": "gutenberg_metadata_rules:anderson__bell:2026-08-21T06:19:16.729706Z",
            "label": "gutenberg_metadata_rules",
            "generated_at": "2026-08-21T06:19:16.729706Z",
            "scope": "gutenberg_volume",
            "method": {"name": "gutenberg_subject_rules", "version": "v1"},
            "provenance": {"story_id": "anderson/bell"},
            "evidence": {"raw_subjects": ["Fairy tales"]},
            "result": {"target_candidates": ["fantasy"]},
        }
    ],
    "current_adjudication": None,
}

_REAL_LEGACY_FLAT_SIDECAR = {
    "verdict": "include",
    "wellformed": True,
    "detected_genre": "fantasy",
    "detected_genre_confidence": 0.85,
    "genre_verdict": "detected",
    "specials_verdict": "none",
    "summary": "A fairy tale.",
    "issues": [],
    "exclude_reason": "",
    "genre_suggestion": "",
    "secondary_genre": "",
}


class GenreSidecarAppendModeTest(unittest.TestCase):
    """Tests for WI-GENRE-0076: append-mode genre-sidecar writes."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.tmp_path = pathlib.Path(self._tmpdir.name)
        self.source_root = self.tmp_path / "data"
        self.checkpoint_dir = self.tmp_path / "checkpoints"
        self.source_root.mkdir()
        self.roots = checkpoint.resolve_roots(
            working_root=self.checkpoint_dir, source_root=self.source_root
        )

    def test_appends_to_existing_valid_v1_sidecar(self):
        story_path = _write_story(
            self.source_root / "anderson", "bell", "Once upon a time."
        )
        (story_path.parent / "genre.json").write_text(
            json.dumps(_REAL_V1_SIDECAR), encoding="utf-8"
        )
        backend = _DualToolFakeBackend()

        result = annotate.annotate_story(
            story_path,
            collection_name="anderson",
            backend=backend,
            model="fake-model",
            roots=self.roots,
        )

        self.assertTrue(result.clean)
        genre_data = json.loads(
            (story_path.parent / "genre.json").read_text(encoding="utf-8")
        )
        self.assertEqual("genre-sidecar-v1", genre_data["schema_version"])
        # The pre-existing metadata-rules assessment survives untouched...
        self.assertEqual(2, len(genre_data["assessments"]))
        self.assertEqual(
            "gutenberg_metadata_rules", genre_data["assessments"][0]["label"]
        )
        self.assertEqual(
            ["fantasy"], genre_data["assessments"][0]["result"]["target_candidates"]
        )
        # ...and the new model assessment is appended after it, not
        # replacing it.
        self.assertEqual("model_detect", genre_data["assessments"][1]["label"])
        self.assertEqual(
            "science fiction", genre_data["assessments"][1]["result"]["detected_genre"]
        )

    def test_converts_legacy_flat_sidecar_then_appends(self):
        story_path = _write_story(
            self.source_root / "anderson", "bell", "Once upon a time."
        )
        (story_path.parent / "genre.json").write_text(
            json.dumps(_REAL_LEGACY_FLAT_SIDECAR), encoding="utf-8"
        )
        backend = _DualToolFakeBackend()

        result = annotate.annotate_story(
            story_path,
            collection_name="anderson",
            backend=backend,
            model="fake-model",
            roots=self.roots,
        )

        self.assertTrue(result.clean)
        genre_data = json.loads(
            (story_path.parent / "genre.json").read_text(encoding="utf-8")
        )
        self.assertEqual("genre-sidecar-v1", genre_data["schema_version"])
        self.assertEqual(2, len(genre_data["assessments"]))
        # The legacy sidecar's evidence is preserved as the first
        # assessment, not discarded.
        self.assertEqual(
            "fantasy", genre_data["assessments"][0]["result"]["detected_genre"]
        )
        self.assertEqual(
            0.85, genre_data["assessments"][0]["result"]["detected_genre_confidence"]
        )
        self.assertEqual(
            "science fiction", genre_data["assessments"][1]["result"]["detected_genre"]
        )

    def test_fresh_write_produces_valid_v1_record_not_legacy_shape(self):
        story_path = _write_story(
            self.source_root / "anderson", "bell", "Once upon a time."
        )
        backend = _DualToolFakeBackend()

        result = annotate.annotate_story(
            story_path,
            collection_name="anderson",
            backend=backend,
            model="fake-model",
            roots=self.roots,
        )

        self.assertTrue(result.clean)
        genre_data = json.loads(
            (story_path.parent / "genre.json").read_text(encoding="utf-8")
        )
        self.assertFalse(genre_sidecar.is_legacy_flat_sidecar(genre_data))
        self.assertTrue(genre_sidecar.validate_sidecar(genre_data).valid)
        self.assertEqual("anderson/bell", genre_data["lcats_id"])
        self.assertEqual("anderson/bell/story.json", genre_data["story_path"])

    def test_refuses_write_when_existing_sidecar_fails_validation(self):
        story_path = _write_story(
            self.source_root / "anderson", "bell", "Once upon a time."
        )
        # A dict that is neither a valid v1 record (no assessments/
        # lcats_id/story_path) nor the legacy flat shape (no
        # detected_genre) -- annotate.py must not guess how to merge into
        # this or silently overwrite it.
        unrecognized = {"schema_version": "genre-sidecar-v1", "something_else": True}
        genre_path = story_path.parent / "genre.json"
        genre_path.write_text(json.dumps(unrecognized), encoding="utf-8")
        backend = _DualToolFakeBackend()

        result = annotate.annotate_story(
            story_path,
            collection_name="anderson",
            backend=backend,
            model="fake-model",
            roots=self.roots,
        )

        self.assertFalse(result.clean)
        self.assertIsNotNone(result.genre_error)
        # The unrecognized file survives untouched -- refused, not
        # overwritten or deleted.
        self.assertEqual(
            unrecognized, json.loads(genre_path.read_text(encoding="utf-8"))
        )

    def test_append_is_atomic_no_partial_file_on_interrupted_write(self):
        # Targets the append path's own write directly (merge_genre_sidecar
        # + _write_json), not the full annotate_story flow -- annotate.py
        # also calls checkpoint.write_checkpoint before ever reaching this
        # write, and that call goes through its own, separately-tested
        # os.replace inside checkpoint.py; patching annotate.py's `os`
        # module globally would intercept that earlier call instead of
        # this one (caught in this item's own self-review), since both
        # share the same underlying os.replace attribute.
        story_path = _write_story(
            self.source_root / "anderson", "bell", "Once upon a time."
        )
        genre_path = story_path.parent / "genre.json"
        genre_path.write_text(json.dumps(_REAL_V1_SIDECAR), encoding="utf-8")

        new_assessment = annotate.build_model_genre_assessment(
            _GENRE_TOOL_RESULT,
            lcats_id="anderson/bell",
            story_path_str="anderson/bell/story.json",
        )
        sidecar_data, error = annotate.merge_genre_sidecar(
            story_path.parent,
            lcats_id="anderson/bell",
            story_path_str="anderson/bell/story.json",
            new_assessment=new_assessment,
        )
        self.assertIsNone(error)

        with unittest.mock.patch(
            "lcats.analysis.corpus.annotate.os.replace",
            side_effect=OSError("simulated interruption"),
        ):
            with self.assertRaises(OSError):
                annotate._write_json(genre_path, sidecar_data)

        # The pre-existing valid sidecar must survive completely intact --
        # not truncated, not partially merged.
        self.assertEqual(
            _REAL_V1_SIDECAR, json.loads(genre_path.read_text(encoding="utf-8"))
        )
        # No stray temp file left behind either.
        leftover_tmp = list(story_path.parent.glob(".genre.json.*.tmp"))
        self.assertEqual([], leftover_tmp)

    def test_write_readme_renders_v1_sidecar_result(self):
        story_path = _write_story(
            self.source_root / "anderson", "bell", "Once upon a time."
        )
        (story_path.parent / "genre.json").write_text(
            json.dumps(_REAL_V1_SIDECAR), encoding="utf-8"
        )
        story_data = json.loads(story_path.read_text(encoding="utf-8"))

        annotate._write_readme(story_path.parent, story_data, story_path)

        readme = (story_path.parent / "README.md").read_text(encoding="utf-8")
        # Only one assessment exists (the metadata-rules one, which has
        # no detected_genre field) -- the README must not blank out, it
        # falls back to the empty-string/0 defaults for that assessment's
        # own result shape rather than crashing.
        self.assertIn("## genre.json", readme)

    def test_write_readme_renders_legacy_sidecar_for_backward_compatibility(self):
        story_path = _write_story(
            self.source_root / "anderson", "bell", "Once upon a time."
        )
        (story_path.parent / "genre.json").write_text(
            json.dumps(_REAL_LEGACY_FLAT_SIDECAR), encoding="utf-8"
        )
        story_data = json.loads(story_path.read_text(encoding="utf-8"))

        annotate._write_readme(story_path.parent, story_data, story_path)

        readme = (story_path.parent / "README.md").read_text(encoding="utf-8")
        self.assertIn("fantasy", readme)

    def test_scenes_json_write_is_unaffected_by_append_mode(self):
        story_path = _write_story(
            self.source_root / "anderson", "bell", "Once upon a time."
        )
        (story_path.parent / "genre.json").write_text(
            json.dumps(_REAL_V1_SIDECAR), encoding="utf-8"
        )
        backend = _DualToolFakeBackend()

        annotate.annotate_story(
            story_path,
            collection_name="anderson",
            backend=backend,
            model="fake-model",
            roots=self.roots,
        )

        scenes_data = json.loads(
            (story_path.parent / "scenes.json").read_text(encoding="utf-8")
        )
        self.assertEqual(1, scenes_data["segment_count"])

    def test_build_human_genre_assessment_is_constructible_and_appendable(self):
        story_path = _write_story(
            self.source_root / "anderson", "bell", "Once upon a time."
        )
        (story_path.parent / "genre.json").write_text(
            json.dumps(_REAL_V1_SIDECAR), encoding="utf-8"
        )

        human_assessment = annotate.build_human_genre_assessment(
            {"detected_genre": "fantasy", "detected_genre_confidence": 1.0},
            lcats_id="anderson/bell",
            story_path_str="anderson/bell/story.json",
            reviewer="a.reviewer@example.com",
        )
        sidecar_data, error = annotate.merge_genre_sidecar(
            story_path.parent,
            lcats_id="anderson/bell",
            story_path_str="anderson/bell/story.json",
            new_assessment=human_assessment,
        )

        self.assertIsNone(error)
        self.assertIsNotNone(sidecar_data)
        self.assertTrue(genre_sidecar.validate_sidecar(sidecar_data).valid)
        self.assertEqual("human_review", sidecar_data["assessments"][-1]["label"])

    def test_checkpoint_hit_is_a_no_op_not_a_duplicate_append(self):
        """A resumed run under an unchanged config must not pile up a
        content-identical assessment on every re-run -- that would
        contradict this module's own checkpoint idempotency guarantee
        (review finding, this item's own self-review)."""
        story_path = _write_story(
            self.source_root / "anderson", "bell", "Once upon a time."
        )
        backend = _DualToolFakeBackend()

        annotate.annotate_story(
            story_path,
            collection_name="anderson",
            backend=backend,
            model="fake-model",
            roots=self.roots,
        )
        first_call_count = len(backend.calls)
        genre_data = json.loads(
            (story_path.parent / "genre.json").read_text(encoding="utf-8")
        )
        self.assertEqual(1, len(genre_data["assessments"]))

        annotate.annotate_story(
            story_path,
            collection_name="anderson",
            backend=backend,
            model="fake-model",
            roots=self.roots,
        )

        self.assertEqual(first_call_count, len(backend.calls))
        genre_data = json.loads(
            (story_path.parent / "genre.json").read_text(encoding="utf-8")
        )
        self.assertEqual(1, len(genre_data["assessments"]))

    def test_checkpoint_hit_against_legacy_sidecar_still_migrates(self):
        """The checkpoint-hit no-op only applies once the existing file is
        already a valid v1 ledger -- a pre-WI-GENRE-0076 legacy sidecar
        re-annotated under an unchanged config (a checkpoint hit) must
        still be converted-and-appended, not skipped (review finding,
        PR #357: the original no-op check only tested `is_file()`)."""
        story_path = _write_story(
            self.source_root / "anderson", "bell", "Once upon a time."
        )
        backend = _DualToolFakeBackend()

        annotate.annotate_story(
            story_path,
            collection_name="anderson",
            backend=backend,
            model="fake-model",
            roots=self.roots,
        )
        first_call_count = len(backend.calls)
        # Simulate a story annotated by the pre-append-mode implementation:
        # a valid checkpoint exists (from the call above), but the on-disk
        # file is overwritten with a legacy flat sidecar.
        genre_path = story_path.parent / "genre.json"
        genre_path.write_text(json.dumps(_REAL_LEGACY_FLAT_SIDECAR), encoding="utf-8")

        result = annotate.annotate_story(
            story_path,
            collection_name="anderson",
            backend=backend,
            model="fake-model",
            roots=self.roots,
        )

        self.assertTrue(result.clean)
        # No new API calls -- this was a genuine checkpoint hit.
        self.assertEqual(first_call_count, len(backend.calls))
        # But the legacy file was still migrated, not left in place.
        genre_data = json.loads(genre_path.read_text(encoding="utf-8"))
        self.assertEqual("genre-sidecar-v1", genre_data["schema_version"])
        self.assertEqual(2, len(genre_data["assessments"]))
        self.assertEqual(
            "fantasy", genre_data["assessments"][0]["result"]["detected_genre"]
        )

    def test_merge_preserves_existing_current_adjudication(self):
        """merge_genre_sidecar rebuilds the top-level record on every call
        -- it must not silently drop an existing human adjudication
        pointer while doing so (review finding, this item's own
        self-review)."""
        seeded = dict(_REAL_V1_SIDECAR)
        seeded["current_adjudication"] = {
            "label": "fantasy",
            "selected_assessment_id": _REAL_V1_SIDECAR["assessments"][0][
                "assessment_id"
            ],
            "decided_at": "2026-08-22T00:00:00+00:00",
        }
        story_path = _write_story(
            self.source_root / "anderson", "bell", "Once upon a time."
        )
        (story_path.parent / "genre.json").write_text(
            json.dumps(seeded), encoding="utf-8"
        )

        new_assessment = annotate.build_model_genre_assessment(
            _GENRE_TOOL_RESULT,
            lcats_id="anderson/bell",
            story_path_str="anderson/bell/story.json",
        )
        sidecar_data, error = annotate.merge_genre_sidecar(
            story_path.parent,
            lcats_id="anderson/bell",
            story_path_str="anderson/bell/story.json",
            new_assessment=new_assessment,
        )

        self.assertIsNone(error)
        self.assertEqual(
            seeded["current_adjudication"], sidecar_data["current_adjudication"]
        )
        self.assertTrue(genre_sidecar.validate_sidecar(sidecar_data).valid)


class AnnotateCollectionTest(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.tmp_path = pathlib.Path(self._tmpdir.name)
        self.source_root = self.tmp_path / "data"
        self.checkpoint_dir = self.tmp_path / "checkpoints"
        self.source_root.mkdir()
        self.roots = checkpoint.resolve_roots(
            working_root=self.checkpoint_dir, source_root=self.source_root
        )

    def test_annotates_every_story_in_collection(self):
        collection_dir = self.source_root / "collection_a"
        _write_story(collection_dir, "story_one", "First story.")
        _write_story(collection_dir, "story_two", "Second story.")
        backend = _DualToolFakeBackend()

        results = annotate.annotate_collection(
            collection_dir, backend=backend, model="fake-model", roots=self.roots
        )

        self.assertEqual(2, len(results))
        self.assertTrue(all(r.clean for r in results))

    def test_missing_collection_raises_instead_of_silently_succeeding(self):
        """A missing/empty collection must not let `lcats annotate
        <collection>` appear to succeed while doing nothing (review
        finding, PR #241)."""
        missing_dir = self.source_root / "does_not_exist"
        backend = _DualToolFakeBackend()

        with self.assertRaises(annotate.EmptyCollectionError):
            annotate.annotate_collection(
                missing_dir, backend=backend, model="fake-model", roots=self.roots
            )

    def test_empty_collection_directory_raises(self):
        empty_dir = self.source_root / "empty_collection"
        empty_dir.mkdir()
        backend = _DualToolFakeBackend()

        with self.assertRaises(annotate.EmptyCollectionError):
            annotate.annotate_collection(
                empty_dir, backend=backend, model="fake-model", roots=self.roots
            )


class AnnotateCollectionsTest(unittest.TestCase):
    """Regression coverage for the corpus-root vs. per-collection selector
    bug (review finding, PR #226): iterating a multi-collection root must
    process every collection, not silently yield nothing."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.tmp_path = pathlib.Path(self._tmpdir.name)
        self.source_root = self.tmp_path / "data"
        self.checkpoint_dir = self.tmp_path / "checkpoints"
        self.source_root.mkdir()
        _write_story(self.source_root / "collection_a", "story_one", "Story A1.")
        _write_story(self.source_root / "collection_b", "story_one", "Story B1.")
        self.roots = checkpoint.resolve_roots(
            working_root=self.checkpoint_dir, source_root=self.source_root
        )

    def test_annotates_every_collection_under_root_by_default(self):
        backend = _DualToolFakeBackend()

        results = annotate.annotate_collections(
            self.source_root, backend=backend, model="fake-model", roots=self.roots
        )

        self.assertEqual({"collection_a", "collection_b"}, set(results.keys()))
        self.assertEqual(1, len(results["collection_a"]))
        self.assertEqual(1, len(results["collection_b"]))

    def test_collection_names_filters_to_requested_subset(self):
        backend = _DualToolFakeBackend()

        results = annotate.annotate_collections(
            self.source_root,
            backend=backend,
            model="fake-model",
            roots=self.roots,
            collection_names=["collection_a"],
        )

        self.assertEqual({"collection_a"}, set(results.keys()))
