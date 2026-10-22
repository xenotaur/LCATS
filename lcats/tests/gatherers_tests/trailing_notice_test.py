"""A terminal grammar must not authorize deletion of nearby narrative."""

import unittest
import dataclasses

from tests.gatherers_tests import review_rules_test

from lcats.gatherers import readiness
from lcats.gatherers import review_rules

NOTE = (
    "Transcriber's Note:\n\nThis etext was produced from _Galaxy_ February 1958. "
    "Extensive research did not uncover any evidence that the U.S. copyright "
    "on this publication was renewed."
)


class TrailingNoticeTests(unittest.TestCase):
    def test_exact_retention_and_evidence(self):
        for note in (
            NOTE,
            NOTE.replace("_Galaxy_", "Galaxy"),
            NOTE + " Minor spelling and typographical errors have been "
            "corrected without note.",
            NOTE.replace("'", "’"),
        ):
            body = "A traveler spoke.\n\n--AN AUTHOR\n\n" + note + "\n"
            proof = review_rules.propose_trailing_publication_notice(body)
            self.assertIsNotNone(proof)
            a, b = proof["span"]
            self.assertEqual(body[a:b], note + "\n")
            self.assertEqual(body[:a], "A traveler spoke.\n\n--AN AUTHOR\n\n")
            self.assertEqual(proof["retained_sha256"], readiness.text_sha256(body[:a]))
            self.assertFalse(proof["publication_approved"])

    def test_ambiguous_or_nonterminal_material_is_untouched(self):
        for body in (
            NOTE,
            "\n\n" + NOTE,
            "Story\n" + NOTE,
            "Story " + NOTE,
            "Story\n\n" + NOTE + "\n\nMore narrative.",
            "Story\n\n" + NOTE + " A new editorial claim.",
            "Story\n\n" + NOTE.replace("Galaxy", "Unknown Review"),
            "Story\n\n" + NOTE.replace("_Galaxy_", "_Galaxy"),
            "Story\n\n" + NOTE.replace("1958", "2058"),
            "Story\n\n" + NOTE.replace("February", "February-March"),
        ):
            with self.subTest(body=body):
                self.assertIsNone(
                    review_rules.propose_trailing_publication_notice(body)
                )

    def test_bounds(self):
        for body in (None, "x" * 4_000_001):
            with self.assertRaises(ValueError):
                review_rules.propose_trailing_publication_notice(body)
        self.assertIsNone(
            review_rules.propose_trailing_publication_notice(
                "Story\n\n" + NOTE + " " * 1001
            )
        )


class TerminalCompositionTests(unittest.TestCase):
    """Composition preserves original coordinates and the old default packet."""

    def setUp(self):
        self.fixture = review_rules_test.BoundaryReviewRulesTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_compose_leading_interior_and_terminal_notes_exactly(self):
        opening = "She read the café sign 🦉 and returned home.\n\n"
        middle = review_rules_test.BODY + "\n\n"
        body = (
            review_rules_test.NOTICE
            + "\n\n"
            + opening
            + review_rules_test.NOTICE
            + "\n\n"
            + middle
            + NOTE
        )
        path = self.fixture.candidate(body)
        old = review_rules.evaluate_publication_notices(path)
        proposal = review_rules.evaluate_publication_notices(
            path, include_terminal=True
        )
        self.assertEqual(len(old["omissions"]), 2)
        self.assertNotIn("terminal_notice", old)
        self.assertEqual(
            old, review_rules.evaluate_publication_notices(path, include_terminal=False)
        )
        self.assertEqual(len(proposal["omissions"]), 3)
        self.assertTrue(proposal["selected_readiness_eligible"])
        self.assertFalse(proposal["publication_approved"])
        record = review_rules.candidate_review.load_candidate(path)
        decision = readiness.OrderedReviewDecision.for_report(
            record["report"],
            omissions=proposal["omissions"],
            reviewer="Authored source reviewer",
            rationale="All authored narrative preserved.",
        )
        self.assertEqual(decision.reconstruct(body), opening + middle)
        self.assertEqual(
            decision, readiness.decision_from_dict(dataclasses.asdict(decision))
        )
        for omitted in decision.omitted_spans:
            self.assertEqual(
                omitted.sha256, readiness.text_sha256(body[omitted.start : omitted.end])
            )

    def test_terminal_only_and_ambiguous_retained_opening(self):
        for prefix in ("", "[Illustration: A scene.]\n\n"):
            body = prefix + review_rules_test.BODY + "\n\n" + NOTE
            proof = review_rules.evaluate_publication_notices(
                self.fixture.candidate(body), include_terminal=True
            )
            self.assertTrue(proof["transformation_qualified"])
            self.assertEqual(proof["selected_readiness_eligible"], not bool(prefix))
            self.assertEqual(proof["selected_spans"], [[0, len(body) - len(NOTE)]])

    def test_postnote_prose_and_overlap_fail_closed(self):
        body = review_rules_test.BODY + "\n\n" + NOTE + "\n\nThe narrative continues."
        proof = review_rules.evaluate_publication_notices(
            self.fixture.candidate(body), include_terminal=True
        )
        self.assertFalse(proof["transformation_qualified"])
        # The old paragraph omission includes following indentation, which would
        # overlap the terminal proof's whitespace-inclusive original start.
        body = (
            review_rules_test.BODY
            + "\n\n"
            + review_rules_test.NOTICE
            + "\n\n   "
            + NOTE
        )
        proof = review_rules.evaluate_publication_notices(
            self.fixture.candidate(body), include_terminal=True
        )
        self.assertEqual(proof["blockers"], ["overlapping_notice_proposals"])
        self.assertFalse(proof["transformation_qualified"])

    def test_terminal_composition_respects_omission_limit(self):
        body = (
            (review_rules_test.NOTICE + "\n\n") * 256
            + review_rules_test.BODY
            + "\n\n"
            + NOTE
        )
        proof = review_rules.evaluate_publication_notices(
            self.fixture.candidate(body), include_terminal=True
        )
        self.assertEqual(proof["blockers"], ["too_many_notices"])
        self.assertFalse(proof["transformation_qualified"])
