"""Partial editorial reviews bind exact source spans and never approve stories."""

import copy
import pathlib
import tempfile
import unittest

from lcats.gatherers import candidate_review
from lcats.gatherers import editorial_evidence
from lcats.gatherers import parser
from lcats.gatherers import readiness
from lcats.gatherers import review_store
from tests.gatherers_tests import review_rules_test

NOTE = "[Publisher’s note: We chose this story for its quiet humour—enjoy it!]"
EDITOR = "(_Editor's note: We enjoyed the author's story. What do you think?_)"


def packet(path, source, note):
    """Supply a separate, explicitly attributed authored role judgment."""
    record = candidate_review.load_candidate(path)
    body = record["report"]["body"]
    raw = note.replace("\n", "\r\n")
    a, b = body.index(note), source.index(raw)
    return {
        "schema_version": 1,
        "kind": "gettenberg_preface_role_review",
        "gutenberg_id": record["report"]["gutenberg_id"],
        "candidate_record_sha256": readiness.identity(record),
        "candidate_span": [a, a + len(note)],
        "candidate_text_sha256": readiness.text_sha256(note),
        "source_span": [b, b + len(raw)],
        "source_text_sha256": readiness.text_sha256(raw),
        "decoded_utf8_sha256": readiness.text_sha256(source),
        "reviewer": "Authored fixture reviewer",
        "rationale": "Authored fixture explicitly assigns the publisher a promotional voice.",
    }


class EditorialEvidenceTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = pathlib.Path(temp.name)

    def candidate(self, note=NOTE, *, source_prefix="Source header\n\n"):
        body = (
            note + "\n\n" + review_rules_test.NOTICE + "\n\n" + review_rules_test.BODY
        )
        source = (source_prefix + body + "\n\nSource footer").replace("\n", "\r\n")
        metadata = {
            "titles": ["The Traveler"],
            "authors": ["Smith, Joan"],
            "aliases": [],
        }
        chapters = parser.assess_chapters(body, **metadata)
        assessment = readiness.assess(body, chapters, **metadata)
        provenance = {
            "input_kind": "historical_decoded_utf8_cache",
            "decoded_utf8_sha256": readiness.text_sha256(source),
            "chapter_assessment": chapters,
        }
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
        path = pathlib.Path(
            review_store.save(
                report, directory=self.root / "queue", data_root=self.root / "data"
            )
        )
        return path, source, report

    def test_exact_unicode_crlf_mapping_and_separate_preservation(self):
        for note in (NOTE, EDITOR, NOTE.replace("this story", "this\n story")):
            with self.subTest(note=note):
                path, source, report = self.candidate(note)
                before = path.read_bytes()
                proof = editorial_evidence.reviewed_preface(
                    path, source, packet(path, source, note)
                )
                self.assertFalse(proof["publication_approved"])
                self.assertTrue(proof["review_binding_validated"])
                decision = readiness.OrderedReviewDecision.for_report(
                    report,
                    omissions=[proof["omission"]],
                    reviewer="Explicit fixture selection",
                    rationale="Authored test only.",
                )
                self.assertEqual(
                    decision.reconstruct(report["body"]), report["body"][len(note) :]
                )
                self.assertEqual(decision.selected_sha256, proof["selected_sha256"])
                self.assertEqual(decision.editorial(report["body"])[0]["text"], note)
                self.assertEqual(path.read_bytes(), before)
                self.assertFalse((self.root / "dispositions").exists())

    def test_labels_are_discovery_only_and_lookalikes_do_not_match(self):
        # Even fictional editor speech with identical syntax needs an independent
        # role judgment. The locator returns ranges, never a role or an omission.
        found = editorial_evidence.labeled_prefaces(NOTE + "\n\nThe story begins.")
        self.assertEqual(set(found[0]), {"span", "sha256"})
        for text in (
            "Publisher's Note: _Mixed publication history._",
            "An editor said: " + NOTE,
            NOTE[:-1],
            NOTE + " Narrative continues.",
            NOTE.replace("We chose", "[We chose"),
            "_An italic epigraph._",
            "The editor looked at his desk.",
        ):
            with self.subTest(text=text):
                self.assertEqual(editorial_evidence.labeled_prefaces(text), [])
        path, source, _ = self.candidate()
        with self.assertRaises(ValueError):
            editorial_evidence.reviewed_preface(path, source, {})

    def test_stale_identity_attribution_and_span_packets_fail(self):
        path, source, _ = self.candidate()
        original = packet(path, source, NOTE)
        for key, bad in (
            ("candidate_record_sha256", "0" * 64),
            ("decoded_utf8_sha256", "0" * 64),
            ("candidate_text_sha256", "0" * 64),
            ("source_text_sha256", "0" * 64),
            ("reviewer", " "),
            ("rationale", ""),
            ("gutenberg_id", True),
            ("schema_version", True),
            ("candidate_span", [True, len(NOTE)]),
            ("source_span", [-1, 8]),
        ):
            with self.subTest(key=key):
                changed = copy.deepcopy(original)
                changed[key] = bad
                with self.assertRaises(ValueError):
                    editorial_evidence.reviewed_preface(path, source, changed)
        with self.assertRaises(ValueError):
            editorial_evidence.reviewed_preface(path, source + "changed", original)
        with self.assertRaises(ValueError):
            editorial_evidence.reviewed_preface(
                path, source, {**original, "approval": True}
            )

    def test_wrong_occurrence_cannot_cite_identical_text_elsewhere(self):
        path, source, _ = self.candidate(source_prefix=NOTE + "\n\nSource header\n\n")
        review = packet(path, source, NOTE)  # Deliberately chooses header occurrence.
        with self.assertRaisesRegex(ValueError, "source mapping"):
            editorial_evidence.reviewed_preface(path, source, review)
        a = source.index(NOTE, source.index(NOTE) + 1)
        review["source_span"] = [a, a + len(NOTE)]
        self.assertTrue(
            editorial_evidence.reviewed_preface(path, source, review)[
                "review_binding_validated"
            ]
        )

    def test_window_and_size_limits_do_not_truncate_notes_into_matches(self):
        self.assertEqual(
            editorial_evidence.labeled_prefaces(
                "x" * editorial_evidence.OPENING_LIMIT + "\n\n" + NOTE
            ),
            [],
        )
        self.assertEqual(
            editorial_evidence.labeled_prefaces(
                "[Publisher's note: " + "x" * editorial_evidence.MAX_NOTE + "]"
            ),
            [],
        )
        for text in (None, "x" * (editorial_evidence.MAX_TEXT + 1)):
            with self.assertRaises(ValueError):
                editorial_evidence.labeled_prefaces(text)
        # An incomplete paragraph at the search edge is never a complete note.
        prefix = "x" * (editorial_evidence.OPENING_LIMIT - len(NOTE) - 2) + "\n\n"
        self.assertEqual(
            editorial_evidence.labeled_prefaces(prefix + NOTE + " more prose"), []
        )
