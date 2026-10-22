"""Exercise real candidate bindings, immutable inputs and failure checkpoints."""

import copy
import gzip
import json
import unittest

from lcats.gatherers import candidate_review
from lcats.gatherers import historical_review
from lcats.gatherers import readiness
from lcats.gatherers import review_rules
from tests.gatherers_tests import review_rules_test
from tests.gatherers_tests import trailing_notice_test
from tests.gettenberg_tests import qualification_evidence_test


class BoundaryGroupsEvidenceTests(unittest.TestCase):
    def setUp(self):
        fixture = review_rules_test.BoundaryReviewRulesTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.root = fixture.root
        self.module = qualification_evidence_test.load("group_boundary_cases")
        self.body = (
            review_rules_test.NOTICE
            + "\n\n"
            + review_rules_test.BODY
            + "\n\n"
            + trailing_notice_test.NOTE
        )
        self.path = fixture.candidate(self.body)
        self.record = candidate_review.load_candidate(self.path)
        self.collection = self.root / "collection"
        self.story = self.collection / "fixture" / "story.json"
        self.story.parent.mkdir(parents=True)
        self.story.write_text(json.dumps({"body": review_rules_test.BODY}))
        self.cache = self.root / "42.txt.gz"
        self.cache.write_bytes(gzip.compress(self.body.encode()))
        digest = self.module.hashlib.sha256
        self.row = {
            "id": 42,
            "path": "fixture",
            "historical_resolution": None,
            "historical_evidence": historical_review.explain_typography(
                self.body[len(review_rules_test.NOTICE) + 2 :], review_rules_test.BODY
            ),
            "candidate_record_sha256": readiness.identity(self.record),
            "corpus_sha256": digest(self.story.read_bytes()).hexdigest(),
            "compressed_sha256": digest(self.cache.read_bytes()).hexdigest(),
            "decoded_utf8_sha256": readiness.text_sha256(self.body),
            "rule_evidence": review_rules.evaluate_publication_notices(self.path),
            "prior_intent": "defer",
        }

    def evaluate(self, row=None):
        return self.module.evaluate(
            [row or self.row], self.path.parent, self.collection, self.root
        )

    def test_complete_history_is_not_approval_and_inputs_preserved(self):
        before = (
            self.story.read_bytes(),
            self.cache.read_bytes(),
            self.path.read_bytes(),
        )
        summary, rows = self.evaluate()
        self.assertEqual(summary["qualified_transformations"], 1)
        self.assertEqual(summary["complete_history_after_rule"], 1)
        self.assertEqual(summary["new_approvals"], 0)
        self.assertEqual(rows[0]["prior_intent"], "defer")
        self.assertFalse(rows[0]["publication_approved"])
        self.assertEqual(
            before,
            (self.story.read_bytes(), self.cache.read_bytes(), self.path.read_bytes()),
        )

    def test_stale_bindings_fail_closed(self):
        for field in (
            "candidate_record_sha256",
            "corpus_sha256",
            "compressed_sha256",
            "decoded_utf8_sha256",
        ):
            row = copy.deepcopy(self.row)
            row[field] = "0" * 64
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.evaluate(row)
        row = copy.deepcopy(self.row)
        row["historical_evidence"]["additional_suffix_characters"] += 1
        with self.assertRaisesRegex(ValueError, "historical comparison"):
            self.evaluate(row)

    def test_duplicate_population_and_unsafe_paths_fail(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.module.evaluate(
                [self.row, self.row], self.path.parent, self.collection, self.root
            )
        row = dict(self.row, path="../elsewhere")
        with self.assertRaisesRegex(ValueError, "unsafe"):
            self.evaluate(row)

    def test_projection_offsets_do_not_cut_candidate(self):
        # The prior qualified leading note changes selected-string coordinates.
        _, rows = self.evaluate()
        self.assertTrue(rows[0]["after_rule_history"]["complete"])
        self.assertEqual(
            rows[0]["rule_evidence"]["span"][0],
            len(review_rules_test.NOTICE) + 2 + len(review_rules_test.BODY) + 2,
        )
        row = copy.deepcopy(self.row)
        row["rule_evidence"]["selected_spans"] = [[7, len(self.body)]]
        with self.assertRaisesRegex(ValueError, "prior selection proof"):
            self.evaluate(row)

    def test_main_failure_is_incomplete_and_output_is_exclusive(self):
        ledger = self.root / "ledger.json.gz"
        ledger.write_bytes(
            gzip.compress(json.dumps([dict(self.row, corpus_sha256="0" * 64)]).encode())
        )
        output = self.root / "result"
        args = [
            str(p)
            for p in (ledger, self.path.parent, self.collection, self.root, output)
        ]
        with self.assertRaises(ValueError):
            self.module.main(args)
        self.assertFalse(json.loads((output / "summary.json").read_text())["completed"])
        with self.assertRaises(FileExistsError):
            self.module.main(args)

    def test_lexical_groups_do_not_claim_editorial_roles(self):
        self.assertEqual(
            self.module.family("_A character speaks._", "prefix"), "starts_underscore"
        )
        self.assertEqual(
            self.module.family("A transcriber entered the room.", "suffix"),
            "contains_transcriber",
        )
        self.assertEqual(self.module.family(" ", "prefix"), "empty")
