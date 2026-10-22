"""Deterministic boundary/adversarial checks for the experiment-only rule.

From lcats/, project environment, PYTHONPATH=src:
python -m unittest discover -s ../experiments/10_gettenberg_qualification/scripts -p test_terminal_notice_candidate.py -v
No network, caches, publication or changes to the imported production cleaner.
"""

import unittest

from lcats.gettenberg import cleanup
import terminal_notice_candidate


class TerminalNoticeTests(unittest.TestCase):
    """Protect exact narrative slices and refusal behavior, not implementation calls."""

    def setUp(self):
        self.candidate = terminal_notice_candidate.load_candidate()
        self.notice = "End of the Project Gutenberg EBook of A Story, by An Author"

    def envelope(self, body, title="A Story"):
        """A minimal independently authored, corroborated Gutenberg envelope."""
        return (
            f"*** START OF THE PROJECT GUTENBERG EBOOK {title} ***\n"
            + body
            + f"*** END OF THE PROJECT GUTENBERG EBOOK {title} ***\n"
        )

    def test_only_terminal_notice_removed_with_original_offsets(self):
        for newline in ("\n", "\r\n", "\r"):
            with self.subTest(newline=newline):
                raw = self.envelope("Narrative.\n\n" + self.notice + "\n\n").replace(
                    "\n", newline
                )
                result = self.candidate.strip_boilerplate(raw)
                self.assertEqual(result.text, "Narrative." + newline * 2)
                self.assertEqual(result.original, raw)
                self.assertEqual(result.content_end, raw.index(self.notice))
                self.assertEqual(
                    result.text, raw[result.content_start : result.content_end]
                )
                self.assertIn(self.notice, cleanup.strip_boilerplate(raw).text)
                self.assertIn(
                    "end_notice_removed", [d.code for d in result.diagnostics]
                )

    def test_existing_notice_stays_identical(self):
        raw = self.envelope(
            "Narrative.\nEnd of Project Gutenberg's A Story, by Author\n"
        )
        before = cleanup.strip_boilerplate(raw)
        after = self.candidate.strip_boilerplate(raw)
        self.assertEqual(before.text, after.text)
        self.assertEqual(before.content_end, after.content_end)

    def test_unqualified_notices_are_preserved(self):
        for notice in (
            self.notice.replace("A Story", "Other Story"),
            self.notice.replace("An Author", "   "),
            self.notice.replace(", by An Author", "\nby An Author"),
            '"' + self.notice + '"',
            "A character said: " + self.notice,
            self.notice + "\nMore narrative.",
            "End of A Story, by An Author",
        ):
            with self.subTest(notice=notice):
                raw = self.envelope("Narrative.\n" + notice + "\n")
                self.assertEqual(
                    self.candidate.strip_boilerplate(raw).text,
                    cleanup.strip_boilerplate(raw).text,
                )

    def test_numeric_marker_does_not_corroborate_a_title(self):
        raw = self.envelope("Narrative.\n" + self.notice + "\n", title="50103")
        self.assertEqual(
            self.candidate.strip_boilerplate(raw).text,
            cleanup.strip_boilerplate(raw).text,
        )

    def test_repeated_notice_does_not_expand_cut(self):
        raw = self.envelope("Narrative.\n" + self.notice + "\n\n" + self.notice + "\n")
        self.assertEqual(
            self.candidate.strip_boilerplate(raw).text,
            "Narrative.\n" + self.notice + "\n\n",
        )

    def test_missing_ambiguous_or_uncorroborated_envelopes_unchanged(self):
        good = self.envelope("Narrative.\n" + self.notice + "\n")
        inputs = [
            "Narrative.\n" + self.notice,
            good.replace("*** START", "*** BEGIN"),
            good.replace("END OF THE", "END OF THIS"),
            good + good,
            good + "Unverified footer.\n",
            "Unverified header.\n" + good,
        ]
        for raw in inputs:
            with self.subTest(raw=raw):
                before = cleanup.strip_boilerplate(raw)
                after = self.candidate.strip_boilerplate(raw)
                self.assertFalse(after.changed)
                self.assertEqual(after.text, before.text)
                self.assertEqual(
                    [d.code for d in after.diagnostics],
                    [d.code for d in before.diagnostics],
                )

    def test_empty_remainder_refused(self):
        raw = self.envelope(self.notice + "\n")
        result = self.candidate.strip_boilerplate(raw)
        self.assertEqual(result.text, raw)
        self.assertIn("empty_content", [d.code for d in result.diagnostics])

    def test_title_space_and_case_follow_existing_contract(self):
        raw = self.envelope(
            "Narrative.\n" + self.notice.replace("A Story", "a\tSTORY") + "\n"
        )
        self.assertEqual(self.candidate.strip_boilerplate(raw).text, "Narrative.\n")


if __name__ == "__main__":
    unittest.main()
