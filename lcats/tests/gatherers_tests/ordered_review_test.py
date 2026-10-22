"""Exact noncontiguous selections must preserve narrative and every provenance link."""

import copy
import dataclasses
import json
import os
import pathlib
import socket
import tempfile
import unittest
from unittest import mock

from lcats import cli
from lcats.gatherers import candidate_review
from lcats.gatherers import downloaders
from lcats.gatherers import parser
from lcats.gatherers import readiness
from lcats.gatherers import review_rules
from lcats.gatherers import review_store
from lcats.gatherers.mass_quantities import gatherer
from lcats.utils import capture
from tests.gatherers_tests import mass_quantities_test
from tests.gatherers_tests import review_rules_test


class OrderedReviewTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = pathlib.Path(temporary.name)
        self.queue = self.root / "queue"
        self.dispositions = self.root / "dispositions"
        patch = mock.patch.dict(
            os.environ,
            LCATS_DATA_DIR=str(self.root / "data"),
            LCATS_CORPORA_DIR=str(self.root / "corpora"),
        )
        patch.start()
        self.addCleanup(patch.stop)
        network = mock.patch.object(
            socket, "socket", side_effect=AssertionError("network forbidden")
        )
        network.start()
        self.addCleanup(network.stop)
        self.opening = "She read the café sign 🦉 and remembered her childhood."
        self.notice = review_rules_test.NOTICE
        self.ending = review_rules_test.BODY + "\n\nShe finally returned home."
        self.text = self.opening + "\n\n" + self.notice + "\n\n" + self.ending
        self.source = mass_quantities_test.MemorySource({1: self.text})
        self.report = parser.inspect_story(1, source=self.source)
        self.assertEqual(self.report["body"], self.text)
        self.path = pathlib.Path(
            review_store.save(
                self.report, directory=self.queue, data_root=self.root / "data"
            )
        )
        self.omissions = [
            {
                "start": len(self.opening) + 2,
                "end": len(self.opening) + 2 + len(self.notice) + 2,
                "kind": "publication_notice",
                "reason": "Complete authored notice.",
                "evidence": "Fixture deliberately separates narrative from publication notice.",
            }
        ]

    def decision(self, omissions=None):
        return readiness.OrderedReviewDecision.for_report(
            self.report,
            omissions=self.omissions if omissions is None else omissions,
            reviewer="fixture reviewer",
            rationale="All authored narrative retained in source order.",
        )

    def test_exact_unicode_selection_preserves_opening_ending_and_separators(self):
        decision = self.decision()
        inspected = parser.inspect_story(
            1, source=self.source, review_decision=decision
        )
        self.assertEqual(inspected["status"], "ready")
        self.assertIsNone(inspected["selected_span"])
        self.assertEqual(
            readiness.selected_text(decision, self.text),
            self.opening + "\n\n" + self.ending,
        )
        self.assertEqual(
            decision,
            readiness.decision_from_dict(
                json.loads(json.dumps(dataclasses.asdict(decision)))
            ),
        )
        self.assertEqual(
            decision.omitted_spans[0].sha256,
            readiness.text_sha256(self.notice + "\n\n"),
        )

    def test_cli_record_export_and_actual_gather_use_all_retained_spans(self):
        omissions_path = self.root / "omissions.json"
        omissions_path.write_text(json.dumps(self.omissions), encoding="utf-8")
        message, status = cli.dispatch(
            "gather-review",
            [
                "record",
                str(self.path),
                "--outcome",
                "approve",
                "--reviewer",
                "fixture reviewer",
                "--rationale",
                "Read complete authored story.",
                "--omissions",
                str(omissions_path),
                "--directory",
                str(self.dispositions),
            ],
        )
        self.assertEqual(status, 0, message)
        disposition = json.loads(message)["disposition"]
        output = self.root / "approvals.json"
        candidate_review.export_approvals(
            [disposition], candidates=self.queue, output=output
        )
        decision = readiness.load_decisions(output)[1]
        with capture.capture_output():
            result = parser.gather_story(
                downloaders.DataGatherer("test", root=self.root / "data"),
                1,
                source=self.source,
                review_decision=decision,
            )
        self.assertEqual(result.status, "published")
        published = json.loads(pathlib.Path(result.path).read_text())
        self.assertEqual(published["body"], self.opening + "\n\n" + self.ending)
        self.assertEqual(
            published["metadata"]["gettenberg"]["publication_readiness"][
                "review_decision"
            ]["schema_version"],
            2,
        )
        self.assertEqual(
            candidate_review.inventory(self.queue, dispositions=self.dispositions)[
                "counts"
            ],
            {"approve": 1},
        )

    def test_confirmed_blurb_is_preserved_separately_with_exact_source_and_evidence(
        self,
    ):
        # Explicit fixture classification only; the notice rule never makes it.
        blurb = {
            "start": 0,
            "end": len(self.opening) + 2,
            "kind": "publisher_blurb",
            "reason": "Authored publisher teaser fixture.",
            "evidence": "Explicit source review establishes this role for this fixture only.",
        }
        decision = self.decision([blurb, *self.omissions])
        with capture.capture_output():
            result = parser.gather_story(
                downloaders.DataGatherer("test", root=self.root / "data"),
                1,
                source=self.source,
                review_decision=decision,
            )
        published = json.loads(pathlib.Path(result.path).read_text())
        self.assertEqual(published["body"], self.ending)
        editorial = published["metadata"]["editorial"]
        self.assertEqual(len(editorial), 1)
        self.assertEqual(editorial[0]["text"], self.opening + "\n\n")
        self.assertEqual(
            editorial[0]["sha256"], readiness.text_sha256(editorial[0]["text"])
        )
        self.assertEqual(
            editorial[0]["candidate_sha256"], readiness.text_sha256(self.text)
        )
        self.assertEqual(editorial[0]["evidence"], blurb["evidence"])
        self.assertEqual(editorial[0]["reviewer"], "fixture reviewer")

    def test_stale_source_assessment_selection_and_omission_hashes_fail(self):
        values = dataclasses.asdict(self.decision())
        for field in (
            "source_identity_sha256",
            "candidate_sha256",
            "assessment_sha256",
            "selected_sha256",
        ):
            with self.subTest(field=field):
                altered = readiness.decision_from_dict({**values, field: "0" * 64})
                with self.assertRaises(ValueError):
                    parser.inspect_story(1, source=self.source, review_decision=altered)
        altered = copy.deepcopy(values)
        altered["omitted_spans"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "omitted text identity"):
            parser.inspect_story(
                1,
                source=self.source,
                review_decision=readiness.decision_from_dict(altered),
            )
        self.source.inputs[1] += "Changed source."
        with self.assertRaisesRegex(ValueError, "stale"):
            parser.inspect_story(1, source=self.source, review_decision=self.decision())

    def test_strict_partition_rejects_overlap_reordering_gaps_and_invalid_types(self):
        values = dataclasses.asdict(self.decision())
        for spans in (
            [],
            [[0, len(self.text)]],
            list(reversed(values["selected_spans"])),
            [[0, 1], [0, 2]],
            [[True, 2]],
            [[0.0, 2]],
            [[-1, 3]],
            [[0, len(self.text) + 1]],
            [[0, 0]],
            [[0, 1, 2]],
        ):
            with self.subTest(spans=spans), self.assertRaises(ValueError):
                readiness.decision_from_dict({**values, "selected_spans": spans})
        for changes in (
            {"candidate_characters": True},
            {"schema_version": True},
            {"schema_version": 3},
            {"unknown": 1},
            {"omitted_spans": []},
            {"selected_spans": "wrong"},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                readiness.decision_from_dict({**values, **changes})

    def test_omissions_require_evidence_and_cannot_remove_every_character(self):
        for changes in (
            {"start": True},
            {"end": len(self.text) + 1},
            {"reason": ""},
            {"kind": "narrative"},
            {"evidence": " "},
            {"evidence": "x" * 4001},
            {"unknown": "x"},
            {"start": 0, "end": len(self.text)},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.decision([{**self.omissions[0], **changes}])
        with self.assertRaises(ValueError):
            self.decision(self.omissions * 257)
        with self.assertRaises(ValueError):
            self.decision(self.omissions * 2)

    def test_explicit_approval_does_not_override_short_selection_exclusion(self):
        omissions = [
            {**self.omissions[0], "start": len(self.opening), "end": len(self.text)}
        ]
        with self.assertRaisesRegex(ValueError, "collection exclusion"):
            parser.inspect_story(
                1, source=self.source, review_decision=self.decision(omissions)
            )

    def test_conflict_compares_all_spans_and_editorial_role(self):
        for omissions in (
            self.omissions,
            [{**self.omissions[0], "kind": "publisher_blurb"}],
        ):
            candidate_review.record_disposition(
                self.path,
                outcome="approve",
                reviewer="reviewer",
                rationale="Explicit fixture intent.",
                omissions=omissions,
                directory=self.dispositions,
            )
        self.assertEqual(
            candidate_review.inventory(self.queue, dispositions=self.dispositions)[
                "counts"
            ],
            {"conflict": 1},
        )

    def test_nonapprovals_and_mixed_selection_arguments_are_rejected(self):
        for outcome, extra in (
            ("exclude", {}),
            ("defer", {}),
            ("approve", {"start": 0}),
            ("approve", {"end": 2}),
        ):
            with (
                self.subTest(outcome=outcome, extra=extra),
                self.assertRaises(ValueError),
            ):
                candidate_review.record_disposition(
                    self.path,
                    outcome=outcome,
                    reviewer="reviewer",
                    rationale="Fixture intent.",
                    omissions=self.omissions,
                    directory=self.dispositions,
                    **extra,
                )
        self.assertFalse(self.dispositions.exists())

    def test_tampered_omission_fails_export_even_with_recomputed_record_identity(self):
        path = pathlib.Path(
            candidate_review.record_disposition(
                self.path,
                outcome="approve",
                reviewer="reviewer",
                rationale="Fixture intent.",
                omissions=self.omissions,
                directory=self.dispositions,
            )
        )
        record = json.loads(path.read_text())
        record["approval"]["omitted_spans"][0]["sha256"] = "0" * 64
        bad = self.dispositions / f"1-{readiness.identity(record)}.disposition.json"
        bad.write_text(json.dumps(record), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "stale"):
            candidate_review.export_approvals(
                [bad], candidates=self.queue, output=self.root / "bad.json"
            )

    def test_rule_preserves_ambiguous_opening_and_does_not_approve_publication(self):
        result = review_rules.evaluate_publication_notices(self.path)
        self.assertTrue(result["transformation_qualified"])
        self.assertTrue(result["selected_readiness_eligible"])
        self.assertFalse(result["publication_approved"])
        selected = "".join(self.text[a:b] for a, b in result["selected_spans"])
        self.assertEqual(selected, self.opening + "\n\n" + self.ending)
        self.assertEqual(result["omissions"][0]["kind"], "publication_notice")
        self.assertFalse(self.dispositions.exists())
        self.assertEqual(list(self.root.rglob("story.json")), [])

    def test_unknown_or_extended_notice_never_becomes_an_omission(self):
        for notice in (
            self.notice.replace("Galaxy Science Fiction", "Unknown Journal"),
            self.notice + " She opened the door.",
            self.notice.replace("]", " And she vanished.]"),
        ):
            self.source.inputs[1] = self.text.replace(self.notice, notice)
            report = parser.inspect_story(1, source=self.source)
            path = review_store.save(
                report, directory=self.queue, data_root=self.root / "data"
            )
            result = review_rules.evaluate_publication_notices(path)
            self.assertFalse(result["transformation_qualified"])
            self.assertEqual(result["omissions"], [])

    def test_remaining_sidenote_blocks_readiness_but_not_notice_transformation(self):
        self.source.inputs[1] = (
            self.text + "\n\n[Sidenote: The traveler is lost.]\n\n" + self.ending
        )
        report = parser.inspect_story(1, source=self.source)
        path = review_store.save(
            report, directory=self.queue, data_root=self.root / "data"
        )
        result = review_rules.evaluate_publication_notices(path)
        self.assertTrue(result["transformation_qualified"])
        self.assertFalse(result["selected_readiness_eligible"])
        self.assertIn("retained_editorial_label", result["blockers"])

    def test_v1_loader_preserves_its_original_serialized_shape(self):
        decision = readiness.ReviewDecision.for_report(
            self.report,
            start=0,
            end=len(self.text),
            reviewer="reviewer",
            rationale="Historical fixture.",
        )
        original = dataclasses.asdict(decision)
        loaded = readiness.decision_from_dict(original)
        self.assertEqual(dataclasses.asdict(loaded), original)
        self.assertNotIn("selected_spans", original)

    def test_selection_preserves_candidate_exterior_whitespace(self):
        report = copy.deepcopy(self.report)
        report["body"] += "\n \t"
        body = report["body"]
        report["provenance"]["publication_readiness"]["candidate_sha256"] = (
            readiness.text_sha256(body)
        )
        decision = readiness.OrderedReviewDecision.for_report(
            report,
            omissions=self.omissions,
            reviewer="reviewer",
            rationale="Exact candidate fixture.",
        )
        self.assertEqual(
            decision.reconstruct(body), self.opening + "\n\n" + self.ending + "\n \t"
        )

    def test_multiple_boundary_and_interior_notices_preserve_every_narrative_paragraph(
        self,
    ):
        text = self.notice + "\n\n" + self.text + "\n\n" + self.notice
        self.source.inputs[1] = text
        report = parser.inspect_story(1, source=self.source)
        path = review_store.save(
            report, directory=self.queue, data_root=self.root / "data"
        )
        result = review_rules.evaluate_publication_notices(path)
        self.assertTrue(result["transformation_qualified"])
        self.assertEqual(len(result["omissions"]), 3)
        body = report["body"]
        selected = "".join(body[a:b] for a, b in result["selected_spans"])
        self.assertEqual(selected, self.opening + "\n\n" + self.ending + "\n\n")
        for removed in result["removed"]:
            self.assertTrue(review_rules.publication_notice(removed["text"].strip()))

    def test_batch_gather_accepts_v2_and_publishes_exact_reconstruction(self):
        with capture.capture_output():
            result = gatherer.gather_stories(
                [1],
                source=self.source,
                review_decisions={1: self.decision()},
                log_dir=self.root / "logs",
            )
        self.assertEqual(result.counts, {"published": 1})
        published = json.loads(pathlib.Path(result.gathered[1]).read_text())
        self.assertEqual(published["body"], self.opening + "\n\n" + self.ending)
