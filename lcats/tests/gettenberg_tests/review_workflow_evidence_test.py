"""Qualify the real cached-source review runner with authored offline inputs."""

import dataclasses
import gzip
import json
import pathlib
import signal
import socket
import tempfile
import unittest
from unittest import mock

from lcats.gatherers import parser
from lcats.gatherers import readiness
from tests.gatherers_tests import live_gather_test
from tests.gettenberg_tests import qualification_evidence_test


class ReviewWorkflowEvidenceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = pathlib.Path(temporary.name)
        self.module = qualification_evidence_test.load("qualify_review_workflow")
        fixture = live_gather_test.LiveGatherTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.source = fixture.source()
        network = mock.patch.object(
            socket, "socket", side_effect=AssertionError("network forbidden")
        )
        network.start()
        self.addCleanup(network.stop)
        self.raw = (
            "The Bell\n\nJohn Smith\n\nTranscriber's Note\n\n" + live_gather_test.BODY
        ).encode()
        self.cached = self.root / f"{live_gather_test.BOOK_ID}.txt.gz"
        self.cached.write_bytes(gzip.compress(self.raw))
        self.collection = self.root / "collection"
        self.story = self.collection / "fixture" / "story.json"
        self.story.parent.mkdir(parents=True)
        self.story.write_text(
            json.dumps(
                {"metadata": {"url": live_gather_test.SOURCE_URI}, "body": "old body"}
            )
        )
        census = qualification_evidence_test.load("assess_cached_readiness")
        self.row = census.assess_path(self.story, self.root, self.source)
        self.baseline = self.root / "baseline.json"
        self.baseline.write_text(json.dumps({"completed": True, "rows": [self.row]}))
        self.approvals = self.root / "approvals.json"
        self.approvals.write_text("[]")
        self.annotations = self.root / "annotations.json"
        self.annotations.write_text("[]")
        self.output = self.root / "result.json"
        self.work = self.root / "work"
        self.args = [
            str(v)
            for v in (
                fixture.cache,
                self.root,
                self.collection,
                self.baseline,
                self.work,
                self.output,
            )
        ]
        self.args += [
            "--approvals",
            str(self.approvals),
            "--annotations",
            str(self.annotations),
        ]

    def report(self):
        """Reconstruct the same explicitly historical source as the runner."""
        helpers = self.module.helpers
        text, compressed, decoded = helpers.corpus.cached_text(
            self.root, live_gather_test.BOOK_ID
        )
        replay = helpers.HistoricalSource(
            self.source,
            helpers.HistoricalText(
                live_gather_test.BOOK_ID,
                helpers.cleanup.strip_boilerplate(text),
                compressed,
                decoded,
            ),
        )
        return parser.inspect_story(live_gather_test.BOOK_ID, source=replay)

    def annotation(self, outcome="defer"):
        evidence = self.row["provenance"]["publication_readiness"]
        return {
            "gutenberg_id": live_gather_test.BOOK_ID,
            "outcome": outcome,
            "reviewer": "fixture reviewer",
            "rationale": "Explicit authored fixture intent.",
            **{
                key: evidence[key]
                for key in (
                    "source_identity_sha256",
                    "candidate_sha256",
                    "assessment_sha256",
                )
            },
        }

    def assert_partial_failure(self, pattern):
        with self.assertRaisesRegex(ValueError, pattern):
            self.module.main(self.args)
        result = json.loads(self.output.read_text())
        self.assertFalse(result["completed"])
        self.assertIn("error", result)
        self.assertEqual(result["network_bytes"], 0)
        return result

    def test_main_replays_exact_prior_approval_and_does_not_publish(self):
        report = self.report()
        decision = readiness.ReviewDecision.for_report(
            report,
            start=report["body"].index(live_gather_test.BODY),
            end=len(report["body"]),
            reviewer="fixture reviewer",
            rationale="Full authored narrative.",
        )
        self.approvals.write_text(json.dumps([dataclasses.asdict(decision)]))
        before = self.story.read_bytes(), self.cached.read_bytes()
        handler = signal.getsignal(signal.SIGALRM)
        self.module.main(self.args)
        result = json.loads(self.output.read_text())
        self.assertTrue(result["completed"])
        self.assertTrue(result["exported_decisions_equal_explicit_inputs"])
        self.assertEqual(result["inventory"]["counts"], {"approve": 1})
        self.assertEqual(result["source_counts"], {"needs_review": 1})
        self.assertEqual(result["stories_published"], 0)
        self.assertEqual(
            readiness.load_decisions(result["export"]),
            {decision.gutenberg_id: decision},
        )
        self.assertTrue(result["preview_checks"][0]["text_and_omissions_equal"])
        self.assertEqual(list(self.work.rglob("story.json")), [])
        self.assertEqual((self.story.read_bytes(), self.cached.read_bytes()), before)
        self.assertEqual(signal.getsignal(signal.SIGALRM), handler)

    def test_main_records_explicit_deferral_without_export(self):
        self.annotations.write_text(json.dumps([self.annotation()]))
        self.module.main(self.args)
        result = json.loads(self.output.read_text())
        self.assertTrue(result["completed"])
        self.assertEqual(result["inventory"]["counts"], {"defer": 1})
        self.assertIsNone(result["export"])
        self.assertFalse((self.work / "approvals.json").exists())

    def test_source_and_annotation_drift_fail_with_partial_evidence(self):
        annotation = self.annotation()
        annotation["source_identity_sha256"] = "0" * 64
        self.annotations.write_text(json.dumps([annotation]))
        self.assert_partial_failure("annotation source/candidate/assessment changed")
        self.assertFalse((self.work / "approvals.json").exists())

    def test_changed_cached_text_cannot_reuse_baseline(self):
        self.cached.write_bytes(gzip.compress(self.raw + b"Changed source."))
        result = self.assert_partial_failure("immutable source/corpus identity changed")
        self.assertEqual(result["rows"], [])

    def test_missing_cached_text_is_explicit_failure(self):
        self.cached.unlink()
        self.assert_partial_failure("missing cached source")

    def test_duplicate_baseline_and_corpus_ids_are_not_complete_census(self):
        self.baseline.write_text(
            json.dumps({"completed": True, "rows": [self.row, self.row]})
        )
        self.assert_partial_failure("unique positive integer IDs")
        self.assertFalse(self.work.exists())

    def test_cleanup_refusal_stays_refusal_and_never_becomes_candidate(self):
        raw = live_gather_test.ENVELOPE.replace("*** END OF", "*** START OF").encode()
        self.cached.write_bytes(gzip.compress(raw))
        census = qualification_evidence_test.load("assess_cached_readiness")
        row = census.assess_path(self.story, self.root, self.source)
        self.baseline.write_text(json.dumps({"completed": True, "rows": [row]}))
        self.module.main(self.args)
        result = json.loads(self.output.read_text())
        self.assertTrue(result["completed"])
        self.assertEqual(result["source_counts"], {"cleanup_refused": 1})
        self.assertEqual(result["inventory"]["candidate_count"], 0)
        self.assertIsNone(result["export"])

    def test_annotations_are_bounded_strict_unique_nonapproval_inputs(self):
        for bad in (
            [self.annotation("approve")],
            [self.annotation(), self.annotation()],
            [{**self.annotation(), "gutenberg_id": True}],
            [{**self.annotation(), "rationale": " "}],
            [{**self.annotation(), "outcome": []}],
            [{**self.annotation(), "unexpected": 1}],
        ):
            self.annotations.write_text(json.dumps(bad))
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.module._read_annotations(self.annotations)
        self.annotations.write_text('[{"x":1,"x":2}]')
        with self.assertRaisesRegex(ValueError, "duplicate evidence field"):
            self.module._read_annotations(self.annotations)
        self.annotations.write_text(" " * (1024**2 + 1))
        with self.assertRaisesRegex(ValueError, "exceeds"):
            self.module._read_annotations(self.annotations)

    def test_baseline_bound_applies_after_gzip_decompression(self):
        path = self.root / "evidence.json.gz"
        path.write_bytes(gzip.compress(b" " * 1000))
        with self.assertRaisesRegex(ValueError, "exceeds"):
            self.module._read_json(path, 100)
