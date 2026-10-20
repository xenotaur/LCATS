"""Guard evidence coverage against stale sources, reviews and population drift."""

import contextlib
import io
import copy
import json
import pathlib
import unittest

from lcats.gatherers import candidate_review
from lcats.gatherers import readiness
from lcats.gatherers import review_store
from tests.gettenberg_tests import qualification_evidence_test
from tests.gettenberg_tests import review_workflow_evidence_test


class DispositionTrancheEvidenceTests(unittest.TestCase):
    def setUp(self):
        # Reuse an authored historical source/catalog fixture, not a real corpus
        # or network mock of product logic. All product artifact loaders run.
        fixture = review_workflow_evidence_test.ReviewWorkflowEvidenceTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.module = qualification_evidence_test.load("reconcile_review_tranche")
        self.report = fixture.report()
        self.candidate = pathlib.Path(
            review_store.save(
                self.report,
                directory=fixture.root / "queue",
                data_root=fixture.collection,
            )
        )
        self.identifier = self.report["gutenberg_id"]
        self.census = {"completed": True, "rows": [fixture.row]}
        self.old = {
            "id": self.identifier,
            "new_extracted_sha256": readiness.text_sha256(self.report["body"]),
            "cache_sha256": fixture.row["compressed_sha256"],
            "decoded_utf8_sha256": fixture.row["decoded_utf8_sha256"],
            "corpus_sha256": fixture.row["corpus_sha256"],
            "body_equal": False,
            "normalized_before_sha256": "0" * 64,
            "normalized_after_sha256": "1" * 64,
            "status": "compared",
            "legacy_matches_retained": True,
            "old_body_characters": 8,
        }
        self.comparison = {"completed": True, "rows": [self.old]}

    def review(self, outcome):
        selected = {}
        if outcome == "approve":
            selected = {
                "start": self.report["body"].index("Paragraph 0:"),
                "end": len(self.report["body"]),
            }
        disposition = candidate_review.record_disposition(
            self.candidate,
            outcome=outcome,
            reviewer="authored test reviewer",
            rationale="Explicit fixture disposition.",
            directory=self.fixture.root / "dispositions",
            **selected,
        )
        return {
            "id": self.identifier,
            "candidate": self.candidate.name,
            "disposition": pathlib.Path(disposition).name,
            "review_scope": "Authored fixture.",
            "historical_rationale": "Known old fixture body.",
            "source_anchors": [
                {"start": 0, "end": 8, "text": self.fixture.raw.decode()[:8]}
            ],
        }

    def run_review(self, review):
        return self.module.reconcile(
            self.census,
            self.comparison,
            [review],
            self.candidate.parent,
            self.fixture.root / "dispositions",
            self.fixture.root,
            self.fixture.collection,
        )

    def test_deferral_never_becomes_disposition_coverage(self):
        for outcome in ("approve", "exclude", "defer"):
            with self.subTest(outcome=outcome):
                result = self.run_review(self.review(outcome))
                self.assertEqual(result["tranche_reviewed_ids"], [self.identifier])
                self.assertFalse(result["corpus_accepted"])
                self.assertEqual(
                    result["tranche_disposition_covered_changed_ids"],
                    [] if outcome == "defer" else [self.identifier],
                )
                self.assertEqual(
                    result["historical_changed_ids_not_covered_by_tranche"],
                    [self.identifier] if outcome == "defer" else [],
                )
                json.dumps(result)

    def test_source_anchor_and_source_drift_refuse_coverage(self):
        review = self.review("exclude")
        changed = copy.deepcopy(review)
        changed["source_anchors"][0]["text"] = "wrong"
        with self.assertRaisesRegex(ValueError, "source anchor"):
            self.run_review(changed)
        self.old["decoded_utf8_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "source/corpus identity"):
            self.run_review(review)

    def test_modified_corpus_and_duplicate_population_refuse_coverage(self):
        review = self.review("exclude")
        self.comparison["rows"].append(self.old)
        with self.assertRaisesRegex(ValueError, "unique positive"):
            self.run_review(review)
        self.comparison["rows"].pop()
        self.fixture.story.write_text('{"body":"changed"}')
        with self.assertRaisesRegex(ValueError, "corpus identity"):
            self.run_review(review)

    def test_rebinding_an_approval_to_another_span_is_detected(self):
        review = self.review("approve")
        root = self.fixture.root / "dispositions"
        record = candidate_review.load_disposition(root / review["disposition"])
        # Keep the candidate binding and recompute outer artifact identity, but
        # leave the selected-text digest stale. Structural JSON alone must fail.
        record["approval"]["selected_start"] += 1
        name = f"{self.identifier}-{readiness.identity(record)}.disposition.json"
        (root / name).write_text(json.dumps(record))
        review["disposition"] = name
        with self.assertRaisesRegex(ValueError, "approval differs"):
            self.run_review(review)

    def test_unselected_population_is_retained_as_uncovered(self):
        row = copy.deepcopy(self.fixture.row)
        row["id"] += 1
        self.census["rows"].append(row)
        historical = copy.deepcopy(self.old)
        historical["id"] += 1
        self.comparison["rows"].append(historical)
        result = self.run_review(self.review("exclude"))
        self.assertEqual(
            result["historical_changed_ids_not_covered_by_tranche"], [historical["id"]]
        )

    def test_malformed_unreviewed_rows_cannot_reduce_remaining_count(self):
        row = copy.deepcopy(self.fixture.row)
        row["id"] += 1
        self.census["rows"].append(row)
        old = copy.deepcopy(self.old)
        old["id"] += 1
        self.comparison["rows"].append(old)
        review = self.review("exclude")
        for invalid in (None, 0, 1, "false"):
            with self.subTest(invalid=invalid):
                old["body_equal"] = invalid
                with self.assertRaisesRegex(ValueError, "body_equal"):
                    self.run_review(review)
        del old["body_equal"]
        with self.assertRaisesRegex(ValueError, "body_equal"):
            self.run_review(review)
        old["body_equal"] = False
        old["status"] = "missing_cached_text"
        with self.assertRaisesRegex(ValueError, "status/body_equal"):
            self.run_review(review)
        old["status"] = "cleanup_refused"
        with self.assertRaisesRegex(ValueError, "body_equal type"):
            self.run_review(review)
        old["status"] = "compared"
        self.comparison["body_differences"] = 1
        with self.assertRaisesRegex(ValueError, "total differs"):
            self.run_review(review)
        self.comparison["body_differences"] = 2
        old["cache_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "population source/corpus"):
            self.run_review(review)

    def test_main_preserves_failure_and_refuses_existing_output(self):
        files = []
        review = self.review("exclude")
        review["source_anchors"][0]["start"] = -1
        for name, data in (
            ("census", self.census),
            ("comparison", self.comparison),
            ("reviews", [review]),
        ):
            path = self.fixture.root / f"{name}.json"
            path.write_text(json.dumps(data))
            files.append(path)
        output = self.fixture.root / "result.json"
        args = [
            str(p)
            for p in (
                *files,
                self.candidate.parent,
                self.fixture.root / "dispositions",
                self.fixture.root,
                self.fixture.collection,
                output,
            )
        ]
        with self.assertRaisesRegex(ValueError, "source anchor"):
            self.module.main(args)
        saved = output.read_bytes()
        self.assertFalse(json.loads(saved)["completed"])
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.module.main(args)
        self.assertEqual(output.read_bytes(), saved)
