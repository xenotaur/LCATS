"""A terminal grammar must not authorize deletion of nearby narrative."""

import unittest

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
