"""Authored narrative fixtures; the legacy parser is deliberately not an oracle."""

import unittest

from lcats.gatherers import parser
from lcats.gatherers import story_body


class BodyExtractionTests(unittest.TestCase):
    def extract(self, text):
        return story_body.extract(text, ("The Bell",), ("Smith, John",))

    def test_late_named_byline_and_long_editorial_tail_do_not_move_start(self):
        narrative = "\n\n".join(
            f"The visitor told story number {i}." for i in range(15)
        )
        note = "Transcriber's Note\n\n" + "\n\n".join(
            f"Editorial correction number {i}." for i in range(15)
        )
        text = f"The Bell\n\nBy John Smith\n\n{narrative}\n\nJohn Smith\n\n{note}"
        result = self.extract(text)
        self.assertTrue(result.text.startswith(narrative))
        self.assertTrue(result.text.endswith(note))
        self.assertIn("possible_editorial_note_retained", result.diagnostics)
        self.assertEqual(
            parser.body_of_text(text, ["Smith, John"], [], ["The Bell"]), result.text
        )

    def test_wrapped_by_line_and_title_mentions_preserve_all_narrative(self):
        body = 'The visitor arrived.\n\n"You should have known her\nby her behavior!"\n\nThey rang\nThe Bell.\n\nThen they left.'
        result = self.extract("The Bell\n\nBy John Smith\n\n" + body)
        self.assertEqual(result.text, body)

    def test_standalone_metadata_after_opening_is_narrative(self):
        body = "She read the inscription.\n\nJohn Smith\n\nThe Bell\n\nThen she understood."
        self.assertEqual(self.extract("The Bell\n\nJohn Smith\n\n" + body).text, body)

    def test_unknown_opening_is_never_discarded_to_reach_later_heading(self):
        text = "A prologue with a vital clue.\n\nThe Bell\n\nJohn Smith\n\nThe visitor arrived."
        result = self.extract(text)
        self.assertEqual(result.text, text)
        self.assertIn("unclassified_opening_retained", result.diagnostics)

    def test_wrapped_heading_and_byline(self):
        self.assertEqual(
            self.extract("The\n\nBell\n\nBy\n\nJohn Smith\n\nA visitor arrived.").text,
            "A visitor arrived.",
        )

    def test_known_opening_credits_and_illustration(self):
        text = "Produced by Pat and the Distributed Proofreading Team\n\nThe Bell\n\nBy John Smith\n\n[Illustration: a bell]\n\nA visitor arrived."
        self.assertEqual(self.extract(text).text, "A visitor arrived.")

    def test_editorial_label_mixed_with_narrative_is_preserved(self):
        for opening in (
            "[Illustration: the bell]\nA visitor arrived with the only key.",
            "Illustrated by the blood on his hands, his account was impossible to deny.",
            "Produced by the Distributed Proofreading Team\nA visitor arrived.",
        ):
            with self.subTest(opening=opening):
                body = opening + "\n\nHe unlocked the door."
                self.assertEqual(
                    self.extract("The Bell\n\nJohn Smith\n\n" + body).text, body
                )

    def test_wrapped_terminal_notice_is_removed_with_corroboration(self):
        body = "A visitor arrived.\n\nA visitor departed."
        for notice in (
            "End of the Project Gutenberg EBook of The Bell,\nby John Smith",
            "End of Project Gutenberg's The Bell, by John Smith",
        ):
            with self.subTest(notice=notice):
                result = self.extract(body + "\n\n" + notice)
                self.assertEqual(result.text, body)
                self.assertIn("corroborated_end_notice_removed", result.diagnostics)

    def test_mismatched_or_nonterminal_notice_is_retained(self):
        for tail in (
            "End of the Project Gutenberg EBook of Other Book, by John Smith",
            "End of the Project Gutenberg EBook of The Bell, by Jane Doe",
            "End of the Project Gutenberg EBook of The Bell, by John Smith\n\nAnother narrative paragraph.",
        ):
            with self.subTest(tail=tail):
                text = "A visitor arrived.\n\n" + tail
                self.assertEqual(self.extract(text).text, text)

    def test_footnotes_notes_scene_breaks_and_end_are_not_blanket_deleted(self):
        body = "A visitor arrived.\n\n* * *\n\nThe end\n\n[Footnote: a vital reference]\n\nTranscriber's Note: typography\n\nItalics indicate a voice."
        self.assertEqual(self.extract(body).text, body)

    def test_offsets_identify_exact_normalized_input_slice(self):
        text = "\r\nThe Bell\r\n\r\nJohn Smith\r\n\r\n  A visitor arrived.  \r\n"
        result = self.extract(text)
        normalized = text.replace("\r\n", "\n")
        self.assertEqual(
            result.text, normalized[result.content_start : result.content_end]
        )
        self.assertEqual(result.text, "A visitor arrived.")
        self.assertEqual(result.provenance()["policy"], story_body.POLICY_VERSION)

    def test_empty_and_editorial_only_inputs_do_not_create_body(self):
        for text in (
            "",
            " \n\n ",
            "The Bell\n\nJohn Smith",
            "End of the Project Gutenberg EBook of The Bell, by John Smith",
        ):
            with self.subTest(text=text):
                self.assertEqual(self.extract(text).text, "")

    def test_mononym_alias_and_non_ascii_heading(self):
        self.assertEqual(
            story_body.extract(
                "L’écho\n\nBy Émile\n\nA voice answered.",
                ["L’écho"],
                ["Other, Name"],
                ["Émile"],
            ).text,
            "A voice answered.",
        )
