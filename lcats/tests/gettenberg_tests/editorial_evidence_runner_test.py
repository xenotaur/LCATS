"""The evidence runner preserves intent and never turns a partial role into approval."""

import copy
import gzip
import json
import pathlib
import shutil
import unittest

from lcats.gatherers import candidate_review
from lcats.gatherers import readiness
from lcats.gatherers import review_store
from lcats.utils import capture
from tests.gatherers_tests import editorial_evidence_test
from tests.gatherers_tests import review_rules_test
from tests.gettenberg_tests import qualification_evidence_test
from tests.gettenberg_tests import review_batch_evidence_test


class EditorialEvidenceRunnerTests(unittest.TestCase):
    def setUp(self):
        review_batch_evidence_test.ReviewBatchEvidenceTests.setUp(self)
        self.fixture.raw = (
            editorial_evidence_test.NOTE
            + "\n\n"
            + review_rules_test.NOTICE
            + "\n\n"
            + review_rules_test.BODY
        ).encode()
        self.fixture.cached.write_bytes(gzip.compress(self.fixture.raw))
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
        )
        self.comparison = {"completed": True, "rows": [self.old]}
        self.runner = qualification_evidence_test.load("qualify_editorial_evidence")
        self.review = editorial_evidence_test.packet(
            self.candidate, self.fixture.raw.decode(), editorial_evidence_test.NOTE
        )

    def evaluate(self, reviews=None):
        return self.runner.evaluate(
            self.census,
            self.comparison,
            self.candidate.parent,
            self.dispositions,
            self.fixture.root,
            self.fixture.collection,
            [],
            [self.review] if reviews is None else reviews,
        )

    def test_discovery_does_not_supply_a_role_or_approval(self):
        summary, rows = self.evaluate([])
        self.assertEqual(summary["discovery_candidates"], 1)
        self.assertEqual(summary["reviewed_spans"], 0)
        self.assertNotIn("preface_selection", rows[0])
        self.assertEqual(list(self.dispositions.iterdir()), [])

    def test_verified_partial_role_preserves_text_metadata_and_prior_intent(self):
        for outcome in (None, "defer", "exclude"):
            if outcome:
                candidate_review.record_disposition(
                    self.candidate,
                    outcome=outcome,
                    reviewer="Prior reviewer",
                    rationale="Authored intent",
                    directory=self.dispositions,
                )
            before = {p.name: p.read_bytes() for p in self.dispositions.iterdir()}
            summary, rows = self.evaluate()
            proposal = rows[0]["preface_selection"]
            self.assertEqual(summary["new_approvals"], 0)
            self.assertEqual(summary["new_dispositions"], 0)
            self.assertFalse(proposal["publication_approved"])
            self.assertIn("whole_story_review_required", proposal["blockers"])
            self.assertEqual(
                proposal["editorial"][0]["text"], editorial_evidence_test.NOTE
            )
            body = self.report["body"]
            selected = "".join(body[a:b] for a, b in proposal["selected_spans"])
            self.assertIn(review_rules_test.BODY, selected)
            self.assertNotIn(editorial_evidence_test.NOTE, selected)
            self.assertEqual(
                before, {p.name: p.read_bytes() for p in self.dispositions.iterdir()}
            )
            if outcome:
                self.assertIn("prior_intent_preserved", proposal["blockers"])
        self.assertEqual(rows[0]["prior_intent"], "conflict")

    def test_separate_explicit_fixture_approval_publishes_exact_editorial_text(self):
        # Partial evidence does not call publication. This authored test supplies
        # a separate complete-story approval to exercise the existing v2 path.
        _, rows = self.evaluate()
        proposal = rows[0]["preface_selection"]
        decision = readiness.OrderedReviewDecision.for_report(
            self.report,
            omissions=proposal["omissions"],
            reviewer="Authored complete-story reviewer",
            rationale="The complete authored fixture is known narrative.",
        )
        cases = qualification_evidence_test.load("qualify_readiness_cases")
        output = self.fixture.root / "explicit-publication"
        cases.check_case(
            {
                "id": self.before["id"],
                "decoded_utf8_sha256": self.before["decoded_utf8_sha256"],
                "expected_status": "needs_review",
            },
            self.fixture.root,
            self.fixture.source,
            output,
            decision=decision,
        )
        story = json.loads(next(output.rglob("story.json")).read_text())
        self.assertEqual(
            story["metadata"]["editorial"][0]["text"], editorial_evidence_test.NOTE
        )
        self.assertEqual(story["body"].strip(), review_rules_test.BODY)
        self.assertIn(
            self.runner.batch.readiness.identity(self.review),
            story["metadata"]["editorial"][0]["evidence"],
        )

    def test_catalogue_mismatch_duplicates_and_stale_sources_fail(self):
        for reviews in (
            [self.review, self.review],
            [{**self.review, "gutenberg_id": 999}],
            [{**self.review, "candidate_record_sha256": "0" * 64}],
        ):
            with self.assertRaises(ValueError):
                self.evaluate(reviews)
        changed = copy.deepcopy(self.comparison)
        self.comparison["rows"][0]["decoded_utf8_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            self.evaluate()
        self.comparison = changed

    def test_cli_exclusive_output_failure_checkpoint_and_no_publication(self):
        root = self.fixture.root
        for name, value in (
            ("census", self.census),
            ("comparison", self.comparison),
            ("prior", []),
            ("reviews", [self.review]),
        ):
            (root / (name + ".json")).write_text(json.dumps(value))
        output = root.parent / (root.name + "-editorial")
        self.addCleanup(lambda: shutil.rmtree(output, ignore_errors=True))
        args = [
            str(p)
            for p in (
                root / "census.json",
                root / "comparison.json",
                self.candidate.parent,
                self.dispositions,
                root,
                self.fixture.collection,
                root / "prior.json",
                root / "reviews.json",
                output,
            )
        ]

        with capture.suppress_output():
            self.runner.main(args)
        self.assertTrue(json.loads((output / "summary.json").read_text())["completed"])
        self.assertFalse(list(output.rglob("story.json")))
        self.assertFalse((output / "approvals.json").exists())
        failed = output.with_name(output.name + "-failed")
        self.addCleanup(lambda: shutil.rmtree(failed, ignore_errors=True))
        (root / "reviews.json").write_text(
            json.dumps([dict(self.review, candidate_record_sha256="0" * 64)])
        )
        with self.assertRaises(ValueError):
            self.runner.main([*args[:-1], str(failed)])
        self.assertFalse(json.loads((failed / "summary.json").read_text())["completed"])
        self.assertFalse((failed / "ledger.json.gz").exists())
        with self.assertRaises(FileExistsError):
            self.runner.main(args)
        with self.assertRaisesRegex(ValueError, "inside an input"):
            self.runner.main([*args[:-1], str(root / "bad-output")])
