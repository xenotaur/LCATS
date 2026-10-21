"""Batch evidence must account for all inputs and never accept an exception."""

import copy
import gzip
import json
import pathlib
import unittest

from lcats.gatherers import candidate_review
from lcats.gatherers import readiness
from lcats.gatherers import review_store
from tests.gatherers_tests import review_rules_test
from tests.gettenberg_tests import qualification_evidence_test
from tests.gettenberg_tests import review_workflow_evidence_test


class ReviewBatchEvidenceTests(unittest.TestCase):
    def setUp(self):
        fixture = review_workflow_evidence_test.ReviewWorkflowEvidenceTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.module = qualification_evidence_test.load("qualify_review_batch")
        fixture.raw = (
            review_rules_test.NOTICE + "\n\n" + review_rules_test.BODY
        ).encode()
        fixture.cached.write_bytes(gzip.compress(fixture.raw))
        stored = json.loads(fixture.story.read_text())
        stored["body"] = review_rules_test.BODY
        fixture.story.write_text(json.dumps(stored))
        census = qualification_evidence_test.load("assess_cached_readiness")
        self.before = census.assess_path(fixture.story, fixture.root, fixture.source)
        self.report = fixture.report()
        self.candidate = pathlib.Path(
            review_store.save(
                self.report,
                directory=fixture.root / "queue",
                data_root=fixture.collection,
            )
        )
        self.dispositions = fixture.root / "dispositions"
        self.dispositions.mkdir()
        self.census = {"completed": True, "rows": [self.before]}
        self.old = {
            "id": self.before["id"],
            "status": "compared",
            "body_equal": False,
            "corpus_sha256": self.before["corpus_sha256"],
            "cache_sha256": self.before["compressed_sha256"],
            "decoded_utf8_sha256": self.before["decoded_utf8_sha256"],
            "new_extracted_sha256": readiness.text_sha256(self.report["body"]),
            "normalized_after_sha256": self.module.normalized(
                self.report["body"], "fixture"
            )["sha256"],
            "normalized_before_sha256": self.module.normalized(
                review_rules_test.BODY, "fixture"
            )["sha256"],
        }
        self.comparison = {"completed": True, "rows": [self.old]}

    def evaluate(self, **options):
        return self.module.evaluate(
            self.census,
            self.comparison,
            self.candidate.parent,
            self.dispositions,
            self.fixture.root,
            self.fixture.collection,
            [],
            self.dispositions,
            **options,
        )

    def test_exact_rule_and_historical_delta_have_individual_evidence(self):
        rows, decisions, inventory = self.evaluate()
        self.assertEqual(inventory, {"unreviewed": 1})
        self.assertEqual(len(decisions), 1)
        self.assertEqual(rows[0]["historical_resolution"], "qualified_boundary_rule")
        evidence = rows[0]["rule_evidence"]
        self.assertEqual(
            evidence["selected_sha256"], readiness.text_sha256(review_rules_test.BODY)
        )
        summary = self.module.summarize(rows, record_qualified=True)
        self.assertEqual(summary["historical_unresolved_ids"], [])
        self.assertFalse(summary["corpus_accepted"])
        self.assertEqual(list(self.dispositions.iterdir()), [])
        self.assertEqual(
            self.module.summarize(rows)["historical_unresolved_ids"],
            [self.before["id"]],
        )

    def test_unexplained_historical_difference_is_not_normalized_away(self):
        self.old["normalized_before_sha256"] = "0" * 64
        rows, decisions, _ = self.evaluate()
        self.assertTrue(rows[0]["rule_evidence"]["approval_eligible"])
        self.assertFalse(rows[0]["rule_explains_entire_historical_difference"])
        self.assertEqual(decisions, [])
        self.assertEqual(
            self.module.summarize(rows)["historical_unresolved_ids"],
            [self.before["id"]],
        )

    def record(self, outcome):
        return candidate_review.record_disposition(
            self.candidate,
            outcome=outcome,
            reviewer="authored reviewer",
            rationale="Explicit test intent",
            directory=self.dispositions,
        )

    def test_defer_exclude_and_conflicts_never_get_overridden(self):
        self.record("defer")
        rows, decisions, _ = self.evaluate()
        self.assertEqual(rows[0]["prior_intent"], "defer")
        self.assertEqual(decisions, [])
        self.record("exclude")
        rows, decisions, _ = self.evaluate()
        self.assertEqual(rows[0]["prior_intent"], "conflict")
        self.assertEqual(decisions, [])
        self.assertIsNone(rows[0]["historical_resolution"])

    def test_incomplete_cumulative_inventory_cannot_override_known_prior_intent(self):
        for outcome in ("exclude", "defer"):
            with self.subTest(outcome=outcome):
                prior = self.fixture.root / ("prior-" + outcome)
                disposition = pathlib.Path(
                    candidate_review.record_disposition(
                        self.candidate,
                        outcome=outcome,
                        reviewer="prior reviewer",
                        rationale="Explicit source review",
                        directory=prior,
                    )
                )
                self.old.update(
                    legacy_matches_retained=True,
                    old_body_characters=len(review_rules_test.BODY),
                )
                review = {
                    "id": self.before["id"],
                    "candidate": self.candidate.name,
                    "disposition": disposition.name,
                    "review_scope": "Authored source review",
                    "historical_rationale": "Explicit prior intent",
                    "source_anchors": [
                        {"start": 0, "end": 8, "text": self.fixture.raw.decode()[:8]}
                    ],
                }
                with self.assertRaisesRegex(ValueError, "omits a known prior"):
                    self.module.evaluate(
                        self.census,
                        self.comparison,
                        self.candidate.parent,
                        self.dispositions,
                        self.fixture.root,
                        self.fixture.collection,
                        [review],
                        prior,
                    )

    def test_all_population_rows_are_checked_before_coverage(self):
        for field, value in (
            ("body_equal", None),
            ("status", "missing"),
            ("decoded_utf8_sha256", "0" * 64),
        ):
            with self.subTest(field=field):
                original = copy.deepcopy(self.old)
                self.old[field] = value
                with self.assertRaises(ValueError):
                    self.evaluate()
                self.old.clear()
                self.old.update(original)
        del self.old["body_equal"]
        with self.assertRaises(ValueError):
            self.evaluate()

    def test_equality_flag_must_agree_with_valid_before_after_hashes(self):
        self.old["body_equal"] = True
        with self.assertRaisesRegex(ValueError, "equality flag"):
            self.evaluate()
        self.old["body_equal"] = False
        self.old["normalized_before_sha256"] = "invalid digest"
        with self.assertRaisesRegex(ValueError, "comparison digest"):
            self.evaluate()
        self.old["normalized_before_sha256"] = self.old["normalized_after_sha256"]
        with self.assertRaisesRegex(ValueError, "equality flag"):
            self.evaluate()

    def test_missing_candidate_or_modified_source_is_fatal(self):
        self.fixture.cached.write_bytes(gzip.compress(b"changed"))
        with self.assertRaisesRegex(ValueError, "identity changed"):
            self.evaluate()
        self.fixture.cached.write_bytes(gzip.compress(self.fixture.raw))
        self.candidate.unlink()
        with self.assertRaisesRegex(ValueError, "candidate population"):
            self.evaluate()

    def test_sidecars_do_not_become_population_members_but_missing_stories_fail(self):
        (self.fixture.story.parent / "genre.json").write_text('{"genre":"fiction"}')
        self.assertEqual(len(self.evaluate()[0]), 1)
        self.fixture.story.unlink()
        with self.assertRaisesRegex(ValueError, "collection population"):
            self.evaluate()

    def test_normalization_context_change_is_fatal(self):
        self.old["normalized_after_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "normalization differs"):
            self.evaluate()

    def test_main_records_only_qualified_decisions_and_refuses_overwrite(self):
        root = self.fixture.root
        for filename, value in (
            ("census.json", self.census),
            ("comparison.json", self.comparison),
            ("reviews.json", []),
        ):
            (root / filename).write_text(json.dumps(value))
        output = root / "batch"
        args = [
            str(p)
            for p in (
                root / "census.json",
                root / "comparison.json",
                self.candidate.parent,
                self.dispositions,
                root,
                self.fixture.collection,
                output,
            )
        ]
        args += [
            "--prior-reviews",
            str(root / "reviews.json"),
            "--prior-dispositions",
            str(self.dispositions),
            "--record-qualified",
        ]
        before = self.fixture.story.read_bytes(), self.fixture.cached.read_bytes()
        self.module.main(args)
        self.assertTrue(json.loads((output / "summary.json").read_text())["completed"])
        self.assertEqual(len(readiness.load_decisions(output / "approvals.json")), 1)
        self.assertEqual(
            before, (self.fixture.story.read_bytes(), self.fixture.cached.read_bytes())
        )
        self.assertEqual(
            len(json.loads(gzip.decompress((output / "ledger.json.gz").read_bytes()))),
            1,
        )
        # Do not call argparse's error path here: the CLI guard is also obvious
        # at entry; verify exclusive writer semantics without noisy stderr.
        with self.assertRaises(FileExistsError):
            self.module._write(output / "summary.json", {})

    def test_ordered_rule_keeps_transformation_and_unrecorded_resolution_separate(self):
        rows, decisions, _ = self.evaluate(rule="ordered")
        self.assertTrue(rows[0]["rule_evidence"]["transformation_qualified"])
        self.assertFalse(rows[0]["rule_evidence"]["publication_approved"])
        self.assertEqual(decisions[0]["schema_version"], 2)
        self.assertEqual(
            self.module.summarize(rows)["historical_unresolved_ids"],
            [self.before["id"]],
        )
        self.assertEqual(
            self.module.summarize(rows, record_qualified=True)[
                "historical_unresolved_ids"
            ],
            [],
        )
        decision = readiness.decision_from_dict(decisions[0])
        self.assertEqual(
            readiness.selected_text(decision, self.report["body"]),
            review_rules_test.BODY,
        )

    def test_ordered_transformation_does_not_override_prior_deferral_or_unexplained_delta(
        self,
    ):
        self.record("defer")
        rows, decisions, _ = self.evaluate(rule="ordered")
        self.assertTrue(rows[0]["rule_evidence"]["transformation_qualified"])
        self.assertEqual(decisions, [])
        self.assertIsNone(rows[0]["historical_resolution"])
        self.old["normalized_before_sha256"] = "0" * 64
        rows, decisions, _ = self.evaluate(rule="ordered")
        self.assertFalse(rows[0]["rule_explains_entire_historical_difference"])
        self.assertEqual(decisions, [])

    def test_equivalent_v1_v2_approvals_do_not_create_a_false_inventory_conflict(self):
        rows, decisions, _ = self.evaluate(rule="ordered")
        v2 = readiness.decision_from_dict(decisions[0])
        start, end = v2.selected_spans[0]
        for selection in (
            {"start": start, "end": end},
            {"omissions": rows[0]["rule_evidence"]["omissions"]},
        ):
            candidate_review.record_disposition(
                self.candidate,
                outcome="approve",
                reviewer="fixture reviewer",
                rationale="Equivalent exact narrative, no separately retained blurbs.",
                directory=self.dispositions,
                **selection,
            )
        inventory = candidate_review.inventory(
            self.candidate.parent, dispositions=self.dispositions
        )
        self.assertEqual(inventory["counts"], {"approve": 1})
        self.assertEqual(len(inventory["candidates"][0]["dispositions"]), 2)
        rows, decisions, _ = self.evaluate(rule="ordered")
        self.assertEqual(
            rows[0]["historical_resolution"], "prior_review_baseline_reconciled"
        )
        self.assertEqual(decisions, [])

    def test_ordered_recording_mode_exports_a_replayable_v2_decision(self):
        # Exercise the runner's mutation branch on an authored one-story corpus;
        # real-corpus measurement can legitimately produce no new approvals.
        root = self.fixture.root
        for name, value in (
            ("census", self.census),
            ("comparison", self.comparison),
            ("reviews", []),
        ):
            (root / (name + ".json")).write_text(json.dumps(value), encoding="utf-8")
        output = root / "batch-recorded"
        self.module.main(
            [
                str(root / "census.json"),
                str(root / "comparison.json"),
                str(self.candidate.parent),
                str(self.dispositions),
                str(root),
                str(self.fixture.collection),
                str(output),
                "--prior-reviews",
                str(root / "reviews.json"),
                "--prior-dispositions",
                str(self.dispositions),
                "--rule",
                "ordered",
                "--record-qualified",
            ]
        )
        summary = json.loads((output / "summary.json").read_text())
        self.assertTrue(summary["completed"])
        self.assertEqual(summary["historical_unresolved_ids"], [])
        self.assertFalse(summary["corpus_accepted"])
        decision = readiness.load_decisions(output / "approvals.json")[
            self.before["id"]
        ]
        self.assertEqual(decision.schema_version, 2)
        self.assertEqual(
            readiness.selected_text(decision, self.report["body"]),
            review_rules_test.BODY,
        )
