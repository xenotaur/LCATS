"""Readiness decisions preserve text and fail closed on stale approvals."""

import dataclasses
import json
import pathlib
import tempfile
import unittest

from lcats.gatherers import parser
from lcats.gatherers import readiness

BODY = "\n\n".join(f"The traveler crossed the river on day {i}." for i in range(15))


def assess(body):
    return readiness.assess(body, parser.assess_chapters(body))


def decision(body, assessment=None, **changes):
    """Authored explicit approval, never an inference from setup consent."""
    assessment = assessment or assess(body)
    values = dict(
        gutenberg_id=1,
        source_identity_sha256="a" * 64,
        candidate_sha256=readiness.text_sha256(body),
        assessment_sha256=readiness.identity(assessment.to_dict()),
        selected_start=0,
        selected_end=len(body),
        selected_sha256=readiness.text_sha256(body),
        reviewer="fixture reviewer",
        rationale="Reviewed every retained paragraph.",
    )
    return readiness.ReviewDecision(**{**values, **changes})


class AssessmentTests(unittest.TestCase):
    def test_clean_narrative_ready_and_unchanged(self):
        self.assertEqual(assess(BODY).status, "ready")
        self.assertEqual(assess(BODY).findings, ())

    def test_long_editorial_only_body_is_review_not_story(self):
        body = "Transcriber’s Note\n\n" + "\n\n".join(
            f"Correction {i}: punctuation was changed." for i in range(15)
        )
        result = assess(body)
        self.assertEqual(result.status, "needs_review")
        self.assertEqual(result.to_dict(), json.loads(json.dumps(result.to_dict())))
        finding = result.findings[0]
        self.assertEqual(finding.kind, "editorial_note")
        self.assertEqual(body[slice(*finding.span)], "Transcriber’s Note")

    def test_note_formats_and_unbracketed_inline_notes(self):
        for label in (
            "[Transcriber's Note: Corrections follow.]",
            "EDITOR'S NOTE",
            "Note to the reader:",
        ):
            with self.subTest(label=label):
                self.assertEqual(assess(BODY + "\n\n" + label).status, "needs_review")

    def test_mentions_and_wrapped_contents_prose_are_not_editorial_labels(self):
        for paragraph in (
            "The transcriber returned home.",
            "By the millions and tens of millions, they arrived.",
            "Contents\nspilled over the deck.\nThe crew watched in silence.",
        ):
            with self.subTest(paragraph=paragraph):
                self.assertEqual(assess(paragraph + "\n\n" + BODY).status, "ready")

    def test_editorial_front_and_back_matter_need_review(self):
        for label in (
            "Copyright, 1912",
            "Published by Example Press",
            "BOOKS BY JANE DOE",
            "[Illustration: The house]",
            "Project Gutenberg license",
            "A POWERFUL NOVELET",
        ):
            with self.subTest(label=label):
                self.assertEqual(assess(label + "\n\n" + BODY).status, "needs_review")

    def test_boxed_notes_transcription_credits_and_author_bibliography(self):
        for label in (
            "+------------------+\n| Transcriber's Note and Errata |\n| Corrections follow. |\n+------------------+",
            "Transcribed from the 1864 edition by Example Person.",
            "Author of ‘Another Book,’ ‘A Third Book,’ etc.",
        ):
            with self.subTest(label=label):
                result = assess(BODY + "\n\n" + label)
                self.assertEqual(result.status, "needs_review")

    def test_weak_display_headings_are_uncertain_not_confident_exclusion(self):
        body = "SIGN ONE\n\n" + BODY + "\n\nSIGN TWO\n\nA person read it.\n\nSIGN THREE"
        result = assess(body)
        self.assertEqual(result.status, "needs_review")
        self.assertIn("ambiguous_structure", [f.kind for f in result.findings])
        for finding in result.findings:
            self.assertEqual(body[slice(*finding.span)][:240], finding.evidence["text"])

    def test_correlated_contents_and_separated_numbered_sections_are_excluded(self):
        for body in (
            "CONTENTS\nFirst Tale\nSecond Tale\n\nFIRST TALE\n\n"
            + BODY
            + "\n\nSECOND TALE\n\n"
            + BODY,
            "Chapter I\n\n" + BODY + "\n\nChapter II\n\n" + BODY,
        ):
            with self.subTest(body=body[:25]):
                result = assess(body)
                self.assertEqual(result.status, "ineligible")
                self.assertEqual(result.exclusion, "divided_work")

    def test_numbered_commercial_prefixes_are_not_section_proof(self):
        body = "I. A BOOK\n\nII. ANOTHER BOOK\n\nIII. LAST BOOK\n\n" + BODY
        self.assertEqual(assess(body).status, "needs_review")

    def test_short_stays_ineligible(self):
        result = assess("Transcriber's Note\n\nOne correction.")
        self.assertEqual(result.exclusion, "too_short")


class ReviewDecisionTests(unittest.TestCase):
    def test_valid_selection_is_an_exact_contiguous_span(self):
        body = "A LABEL\n\n" + BODY
        approval = decision(
            body, selected_start=9, selected_sha256=readiness.text_sha256(BODY)
        )
        selected = approval.select(
            gutenberg_id=1,
            source_identity_sha256="a" * 64,
            candidate=body,
            assessment=assess(body),
        )
        self.assertEqual(selected, BODY)

    def test_source_candidate_policy_and_ebook_drift_fail(self):
        approval = decision(BODY)
        base = dict(
            gutenberg_id=1,
            source_identity_sha256="a" * 64,
            candidate=BODY,
            assessment=assess(BODY),
        )
        for change in (
            {"gutenberg_id": 2},
            {"source_identity_sha256": "b" * 64},
            {"candidate": BODY + "changed"},
            {"assessment": dataclasses.replace(assess(BODY), policy="new-policy")},
        ):
            with (
                self.subTest(change=change),
                self.assertRaisesRegex(ValueError, "stale"),
            ):
                approval.select(**{**base, **change})

    def test_span_and_selected_hash_cannot_drift(self):
        for changes in ({"selected_end": len(BODY) + 1}, {"selected_sha256": "b" * 64}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                decision(BODY, **changes).select(
                    gutenberg_id=1,
                    source_identity_sha256="a" * 64,
                    candidate=BODY,
                    assessment=assess(BODY),
                )

    def test_invalid_fields_fail_at_construction(self):
        for changes in (
            {"gutenberg_id": True},
            {"schema_version": True},
            {"candidate_sha256": "no"},
            {"selected_start": -1},
            {"selected_end": 0},
            {"selected_start": 0.0},
            {"reviewer": " "},
            {"rationale": None},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                decision(BODY, **changes)

    def test_strict_loader_validates_shape_duplicates_and_types(self):
        record = dataclasses.asdict(decision(BODY))
        invalid = [
            json.dumps({}),
            json.dumps([record, record]),
            json.dumps([{"extra": 1, **record}]),
            '[{"gutenberg_id":1,"gutenberg_id":2}]',
            json.dumps([None]),
        ]
        with tempfile.TemporaryDirectory() as root:
            path = pathlib.Path(root) / "reviews.json"
            for text in invalid:
                path.write_text(text, encoding="utf-8")
                with self.subTest(text=text[:35]), self.assertRaises(ValueError):
                    readiness.load_decisions(path)
            path.write_text(json.dumps([record]), encoding="utf-8")
            self.assertEqual(readiness.load_decisions(path), {1: decision(BODY)})
