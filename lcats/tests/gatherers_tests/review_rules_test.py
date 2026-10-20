"""Boundary rules must preserve narrative and refuse similar but uncertain notes."""

import copy
import json
import pathlib
import tempfile
import unittest

from lcats.gatherers import parser
from lcats.gatherers import readiness
from lcats.gatherers import review_rules
from lcats.gatherers import review_store

NOTICE = (
    "[Transcriber's Note: This etext was produced from Galaxy Science Fiction "
    "October 1954. Extensive research did not uncover any evidence that the "
    "U.S. copyright on this publication was renewed.]"
)
BODY = "\n\n".join(
    f"The traveler walked past house {i}, remembering the people who lived there."
    for i in range(14)
)


class BoundaryReviewRulesTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = pathlib.Path(temp.name)

    def candidate(self, body):
        """Use real saved candidate validation with authored source provenance."""
        metadata = {
            "titles": ["The Traveler"],
            "authors": ["Smith, Joan"],
            "aliases": [],
        }
        chapters = parser.assess_chapters(body, **metadata)
        assessment = readiness.assess(body, chapters, **metadata)
        self.assertEqual(assessment.status, "needs_review")
        provenance = {"chapter_assessment": chapters, "source": "authored fixture"}
        evidence = {
            **assessment.to_dict(),
            "candidate_sha256": readiness.text_sha256(body),
            "assessment_sha256": readiness.identity(assessment.to_dict()),
            "source_identity_sha256": readiness.identity(
                {"gutenberg_id": 42, "metadata": metadata, "source": provenance}
            ),
        }
        report = {
            "gutenberg_id": 42,
            "body": body,
            "metadata": metadata,
            "status": "needs_review",
            "rejection": None,
            "selected_span": [0, len(body)],
            "provenance": {**provenance, "publication_readiness": evidence},
        }
        return pathlib.Path(
            review_store.save(
                report, directory=self.root / "queue", data_root=self.root / "data"
            )
        )

    def evaluate(self, text):
        return review_rules.evaluate_boundary_notice(self.candidate(text))

    def test_leading_trailing_and_both_preserve_every_retained_character(self):
        for text in (
            NOTICE + "\n\n" + BODY,
            BODY + "\n\n" + NOTICE,
            NOTICE + "\n\n" + BODY + "\n\n" + NOTICE,
        ):
            with self.subTest(text=text[:25]):
                result = self.evaluate(text)
                self.assertTrue(result["approval_eligible"])
                start, end = result["selected_span"]
                self.assertEqual(text[start:end], BODY)
                self.assertEqual(result["selected_sha256"], readiness.text_sha256(BODY))
                for removed in result["removed"]:
                    a, b = removed["span"]
                    self.assertEqual(text[a:b], removed["text"])
                    self.assertEqual(
                        readiness.text_sha256(text[a:b]), removed["sha256"]
                    )
                self.assertFalse((self.root / "dispositions").exists())

    def test_exterior_whitespace_never_discards_a_narrative_paragraph(self):
        for ending in ("\n", "\n\n", "   ", "\n ", "\t"):
            with self.subTest(ending=repr(ending)):
                text = NOTICE + "\n\n" + BODY + ending
                result = self.evaluate(text)
                self.assertTrue(result["approval_eligible"])
                a, b = result["selected_span"]
                self.assertEqual(text[a:b], BODY + ending)
                self.assertEqual(b, len(text))
                self.assertEqual(len(result["removed"]), 1)
                # A trailing notice may remove its own exterior whitespace;
                # the narrative between both notices remains character-exact.
                text = NOTICE + "\n\n" + BODY + "\n\n" + NOTICE + ending
                result = self.evaluate(text)
                a, b = result["selected_span"]
                self.assertEqual(text[a:b], BODY)
                self.assertTrue(
                    all(
                        review_rules.publication_notice(r["text"].strip())
                        for r in result["removed"]
                    )
                )

    def test_whitespace_and_curly_apostrophe_only_change_recognition(self):
        note = NOTICE.replace("'", "’").replace("Science Fiction", "Science\n Fiction")
        result = self.evaluate(note + "\n\n" + BODY)
        self.assertTrue(result["approval_eligible"])
        self.assertEqual(result["removed"][0]["text"], note + "\n\n")

    def test_unknown_publication_date_and_extra_prose_do_not_match(self):
        for note in (
            NOTICE.replace("Galaxy Science Fiction", "Invented Journal"),
            NOTICE.replace("October 1954", "Issue 18"),
            NOTICE[:-1],
            NOTICE.replace("]", " She opened the door.]"),
            NOTICE + " She opened the door.",
            NOTICE.replace("[", "", 1),
        ):
            with self.subTest(note=note):
                self.assertFalse(review_rules.publication_notice(note))
                result = self.evaluate(note + "\n\n" + BODY)
                self.assertFalse(result["matched"])

    def test_interior_notice_and_narrative_prefix_are_never_discarded(self):
        for prefix in (
            "She woke to a strange new world.",
            "By Joan Smith",
            "The Traveler",
        ):
            result = self.evaluate(prefix + "\n\n" + NOTICE + "\n\n" + BODY)
            self.assertFalse(result["matched"])
            self.assertIsNone(result["selected_span"])

    def test_remaining_interior_caption_or_sidenote_blocks_approval(self):
        for label in ("[Illustration: The traveler falls.]", "[Sidenote: A warning]"):
            body = BODY + "\n\n" + label + "\n\n" + BODY
            result = self.evaluate(NOTICE + "\n\n" + body)
            self.assertTrue(result["matched"])
            self.assertFalse(result["approval_eligible"])
            self.assertIn("retained_editorial_label", result["blockers"])

    def test_multiple_notes_and_short_or_divided_selections_stay_unresolved(self):
        for body in (NOTICE + "\n\n" + BODY, "I\n\n" + BODY + "\n\nII\n\n" + BODY):
            result = self.evaluate(NOTICE + "\n\n" + body)
            self.assertFalse(result["approval_eligible"])
        short = "\n\n".join(BODY.split("\n\n")[:9])
        self.assertFalse(
            self.evaluate(NOTICE + "\n\n" + short + "\n\n" + NOTICE)[
                "approval_eligible"
            ]
        )

    def test_self_consistent_but_forged_assessment_is_not_a_rule_proof(self):
        path = self.candidate(NOTICE + "\n\n" + BODY)
        record = json.loads(path.read_text())
        report = copy.deepcopy(record["report"])
        assessment = report["provenance"]["publication_readiness"]
        assessment["findings"][0]["message"] = "unverified assessment"
        fields = {
            k: assessment[k]
            for k in ("policy", "status", "exclusion", "offset_basis", "findings")
        }
        assessment["assessment_sha256"] = readiness.identity(fields)
        changed = review_store.save(
            report, directory=self.root / "queue", data_root=self.root / "data"
        )
        with self.assertRaisesRegex(ValueError, "assessment differs"):
            review_rules.evaluate_boundary_notice(changed)

    def test_source_body_tampering_is_rejected(self):
        path = self.candidate(NOTICE + "\n\n" + BODY)
        data = json.loads(path.read_text())
        data["report"]["body"] += "Tampered."
        path.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            review_rules.evaluate_boundary_notice(path)
