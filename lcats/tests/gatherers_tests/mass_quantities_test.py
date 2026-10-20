"""Exercise real batch outcomes, publication and crash-visible logs offline.

The in-memory source is the acquisition boundary; the parser, readiness,
normalization, output store and RunLog all execute normally.
"""

import json
import os
import pathlib
import tempfile
import types
import unittest
from unittest import mock

from lcats.gatherers import readiness
from lcats.gatherers.mass_quantities import gatherer
from lcats.gatherers.mass_quantities import storymap
from lcats.gettenberg import cleanup
from lcats.gettenberg import resources
from lcats.utils import capture

BODY = "\n\n".join(f"On day {i} the traveler waited by the river." for i in range(15))


class MemorySource:
    """Authored decoded inputs with explicit provenance, not simulated HTTP bytes."""

    def __init__(self, inputs):
        self.inputs = inputs
        self.read_ids = []

    def metadata(self, story):
        if story not in self.inputs:
            return None
        return types.SimpleNamespace(
            ebook=types.SimpleNamespace(gutenberg_id=story),
            titles=(f"Fixture {story}",),
            authors=("Smith, John",),
            aliases=(),
            subjects=("Short stories", "PS"),
            languages=("en",),
        )

    def read(self, metadata):
        story = metadata.ebook.gutenberg_id
        self.read_ids.append(story)
        text = self.inputs[story]
        if isinstance(text, BaseException):
            raise text
        return types.SimpleNamespace(
            cleaned=cleanup.strip_boilerplate(text),
            provenance=lambda: {
                "source_uri": f"https://fixture.invalid/{story}",
                "input_kind": "authored_decoded_text",
                "decoded_utf8_sha256": readiness.text_sha256(text),
            },
        )


class BatchTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = pathlib.Path(temporary.name)
        self.data = self.root / "data"
        self.logs = self.root / "logs"
        patch = mock.patch.dict(
            os.environ,
            LCATS_DATA_DIR=str(self.data),
            LCATS_CORPORA_DIR=str(self.root / "corpora"),
        )
        patch.start()
        self.addCleanup(patch.stop)

    def run_batch(self, inputs, ids=None, **kwargs):
        source = MemorySource(inputs)
        with capture.capture_output():
            result = gatherer.gather_stories(
                list(inputs) if ids is None else ids,
                log_dir=self.logs,
                source=source,
                **kwargs,
            )
        return result, source

    def events(self):
        return [
            json.loads(line)
            for line in (self.logs / gatherer.GATHER_LOG_FILENAME)
            .read_text()
            .splitlines()
        ]

    def test_mixed_results_keep_all_categories_and_preserve_candidate(self):
        note = "Transcriber's Note\n\n" + BODY
        refused = resources.ResourceDecodeError("cleanup_refused", "ambiguous envelope")
        result, source = self.run_batch(
            {1: BODY, 2: note, 3: refused, 4: "Too short."}, ids=[1, 2, 3, 4, 5]
        )
        self.assertEqual(
            result.counts,
            {"published": 1, "needs_review": 1, "cleanup_refused": 1, "ineligible": 2},
        )
        self.assertTrue(result.requires_attention)
        self.assertEqual(set(result.gathered), {1})
        self.assertEqual(len(list(self.data.rglob("story.json"))), 1)
        review = result.outcomes[1]
        self.assertIsNone(review.path)
        self.assertEqual(
            json.loads(pathlib.Path(review.review_path).read_text())["report"]["body"],
            note,
        )
        self.assertEqual(source.read_ids, [1, 2, 3, 4])
        self.assertEqual(
            [e["event"] for e in self.events()],
            [
                "run_start",
                "story_published",
                "story_needs_review",
                "story_cleanup_refused",
                "story_ineligible",
                "story_ineligible",
                "run_end",
            ],
        )
        json.dumps(result.to_dict())

    def test_existing_outputs_reused_without_source_read_or_requalification(self):
        initial, _ = self.run_batch({1: BODY})
        path = pathlib.Path(initial.gathered[1])
        original = path.read_bytes()
        result, source = self.run_batch({1: RuntimeError("must not read existing")})
        self.assertEqual(result.counts, {"reused": 1})
        self.assertEqual(source.read_ids, [])
        self.assertFalse(result.requires_attention)
        self.assertEqual(path.read_bytes(), original)

    def test_operational_failure_keeps_prior_output_and_abort_log(self):
        with self.assertRaisesRegex(OSError, "unavailable"):
            self.run_batch({1: BODY, 2: OSError("source unavailable"), 3: BODY})
        self.assertEqual(len(list(self.data.rglob("story.json"))), 1)
        self.assertEqual(
            [e["event"] for e in self.events()],
            ["run_start", "story_published", "run_aborted_unexpected"],
        )

    def test_decode_failure_is_not_a_cleanup_refusal(self):
        with self.assertRaises(resources.ResourceDecodeError):
            self.run_batch(
                {1: resources.ResourceDecodeError("invalid_utf8", "bad bytes")}
            )
        self.assertEqual(self.events()[-1]["event"], "run_aborted_unexpected")

    def test_empty_and_generator_selections(self):
        empty, _ = self.run_batch({})
        self.assertEqual(empty.outcomes, ())
        result, _ = self.run_batch({1: BODY}, ids=(value for value in (1,)))
        self.assertEqual(result.counts, {"published": 1})
        self.assertEqual(self.events()[-3]["story_count"], 1)

    def test_review_ids_outside_selection_fail_before_io(self):
        with self.assertRaisesRegex(ValueError, "outside"):
            self.run_batch({1: BODY}, review_decisions={2: object()})
        self.assertFalse(self.logs.exists())
        self.assertFalse(self.data.exists())

    def test_logs_refuse_protected_runtime_root_and_symlink(self):
        self.data.mkdir()
        alias = self.root / "alias"
        alias.symlink_to(self.data, target_is_directory=True)
        for path in (
            self.data / "logs",
            alias / "logs",
            self.root / "corpora" / "logs",
        ):
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, "outside"):
                gatherer.gather_stories(
                    [1], log_dir=path, source=MemorySource({1: BODY})
                )
        self.assertEqual(list(self.data.iterdir()), [])

    def test_configured_collection_retains_all_outcomes(self):
        with (
            mock.patch.object(storymap, "SINGLE_STORIES", [1, 2]),
            mock.patch.object(gatherer, "DEFAULT_GATHER_LOG_DIR", self.logs),
            tempfile.TemporaryDirectory() as cwd,
        ):
            # The public wrapper uses its function default; isolate that relative path.
            import contextlib

            with contextlib.chdir(cwd), capture.capture_output():
                result = gatherer.gather(
                    source=MemorySource({1: BODY, 2: "Too short."})
                )
        self.assertEqual(result.counts, {"published": 1, "ineligible": 1})
        self.assertFalse(result.requires_attention)

    def test_missing_source_fails_before_io(self):
        with self.assertRaisesRegex(ValueError, "explicit"):
            gatherer.gather_stories([], log_dir=self.logs, source=None)
        self.assertFalse(self.logs.exists())
