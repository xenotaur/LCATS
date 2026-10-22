"""Terminal recording must require source review even for exact old equality."""

import dataclasses
import gzip
import json
import pathlib
import unittest

from lcats.gatherers import readiness
from lcats.gatherers import review_store
from tests.gatherers_tests import review_rules_test
from tests.gatherers_tests import trailing_notice_test
from tests.gettenberg_tests import qualification_evidence_test
from tests.gettenberg_tests import review_batch_evidence_test


class TerminalBatchEvidenceTests(unittest.TestCase):
    def setUp(self):
        review_batch_evidence_test.ReviewBatchEvidenceTests.setUp(self)
        self.retained = review_rules_test.BODY + "\n\n"
        self.fixture.raw = (
            review_rules_test.NOTICE
            + "\n\n"
            + self.retained
            + trailing_notice_test.NOTE
        ).encode()
        self.fixture.cached.write_bytes(gzip.compress(self.fixture.raw))
        stored = json.loads(self.fixture.story.read_text())
        stored["body"] = self.retained
        self.fixture.story.write_text(json.dumps(stored))
        self.candidate.unlink()
        self.report = self.fixture.report()
        self.candidate = pathlib.Path(
            review_store.save(
                self.report,
                directory=self.candidate.parent,
                data_root=self.fixture.collection,
            )
        )
        census = qualification_evidence_test.load("assess_cached_readiness")
        self.before = census.assess_path(
            self.fixture.story, self.fixture.root, self.fixture.source
        )
        self.census = {"completed": True, "rows": [self.before]}
        self.old.update(
            corpus_sha256=self.before["corpus_sha256"],
            cache_sha256=self.before["compressed_sha256"],
            decoded_utf8_sha256=self.before["decoded_utf8_sha256"],
            new_extracted_sha256=readiness.text_sha256(self.report["body"]),
            normalized_after_sha256=self.module.normalized(
                self.report["body"], "fixture"
            )["sha256"],
            normalized_before_sha256=readiness.text_sha256(self.retained),
        )
        self.comparison = {"completed": True, "rows": [self.old]}

    def evaluate(self, **options):
        options.setdefault("rule", "terminal")
        return review_batch_evidence_test.ReviewBatchEvidenceTests.evaluate(
            self, **options
        )

    record = review_batch_evidence_test.ReviewBatchEvidenceTests.record
    cohort = review_batch_evidence_test.SourceGroundedBatchTests.cohort

    def args(self, name, review=None):
        root = self.fixture.root
        values = {"census": self.census, "comparison": self.comparison, "reviews": []}
        if review is not None:
            values["cohort"] = review
        for key, value in values.items():
            (root / (key + ".json")).write_text(json.dumps(value))
        args = [
            str(p)
            for p in (
                root / "census.json",
                root / "comparison.json",
                self.candidate.parent,
                self.dispositions,
                root,
                self.fixture.collection,
                root / name,
            )
        ]
        args += [
            "--prior-reviews",
            str(root / "reviews.json"),
            "--prior-dispositions",
            str(self.dispositions),
            "--rule",
            "terminal",
            "--record-qualified",
        ]
        if review is not None:
            args += ["--cohort-review", str(root / "cohort.json")]
        return args

    def test_exact_baseline_cannot_bypass_source_cohort_gate(self):
        rows, decisions, _ = self.evaluate()
        self.assertEqual(rows[0]["historical_acceptance_basis"], "exact_baseline")
        self.assertEqual(len(decisions), 1)
        with self.assertRaisesRegex(ValueError, "exact reviewed cohort"):
            self.module.main(self.args("missing-review"))
        output = self.fixture.root / "missing-review"
        self.assertFalse(json.loads((output / "summary.json").read_text())["completed"])
        self.assertFalse((output / "dispositions").exists())
        review = self.cohort(rows[0], decisions[0])
        for bad in ([dict(review, selected_sha256="0" * 64)], [review, review]):
            with self.assertRaises(ValueError):
                self.module.verify_cohort(
                    bad, rows, decisions, self.candidate.parent, require_all=True
                )

    def test_explicit_review_records_publishes_exact_text_and_replays(self):
        rows, decisions, _ = self.evaluate()
        review = self.cohort(rows[0], decisions[0])
        self.module.main(self.args("recorded", [review]))
        output = self.fixture.root / "recorded"
        decision = readiness.load_decisions(output / "approvals.json")[
            self.before["id"]
        ]
        self.assertEqual(decision.schema_version, 2)
        self.assertEqual(decision.reconstruct(self.report["body"]), self.retained)
        cases = qualification_evidence_test.load("qualify_readiness_cases")
        publication = self.fixture.root / "publication"
        cases.check_case(
            {
                "id": self.before["id"],
                "decoded_utf8_sha256": self.before["decoded_utf8_sha256"],
                "expected_status": "needs_review",
            },
            self.fixture.root,
            self.fixture.source,
            publication,
            decision=readiness.decision_from_dict(
                json.loads(json.dumps(dataclasses.asdict(decision)))
            ),
        )
        published = json.loads(next(publication.rglob("story.json")).read_text())
        self.assertEqual(published["body"], self.retained)
        self.dispositions = output / "dispositions"
        rows, decisions, _ = self.evaluate()
        self.assertEqual(decisions, [])
        self.assertEqual(
            rows[0]["historical_resolution"], "prior_review_baseline_reconciled"
        )

    def test_terminal_mode_preserves_defer_exclude_and_conflict(self):
        for outcome in ("defer", "exclude"):
            self.record(outcome)
            rows, decisions, _ = self.evaluate()
            self.assertEqual(decisions, [])
            self.assertIsNone(rows[0]["historical_resolution"])

    def test_default_and_ordered_modes_do_not_remove_terminal_note(self):
        for rule in ("boundary", "ordered"):
            _, decisions, _ = self.evaluate(rule=rule)
            self.assertEqual(decisions, [])
