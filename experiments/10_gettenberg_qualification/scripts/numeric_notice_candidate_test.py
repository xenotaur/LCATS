"""Authored boundaries for the experiment-only numeric notice rule.

From lcats/: PYTHONPATH=src:../experiments/10_gettenberg_qualification/scripts
scripts/test numeric_notice_candidate_test. No network, corpus or cache access.
"""

import unittest

import numeric_notice_candidate
import terminal_notice_candidate


class NumericNoticeTest(unittest.TestCase):
    """Require independent source/catalog/title binding and preserve ambiguity."""

    def setUp(self):
        self.cleaner = terminal_notice_candidate.load_candidate()
        self.notice = "End of the Project Gutenberg EBook of A Story, by An Author"

    def raw(self, body=None, marker="50103", newline="\n"):
        """Author a minimal envelope without relying on the candidate's regex."""
        if body is None:
            body = "Narrative.\n\n" + self.notice + "\n\n"
        return (
            f"*** START OF THE PROJECT GUTENBERG EBOOK {marker} ***\n"
            + body
            + f"*** END OF THE PROJECT GUTENBERG EBOOK {marker} ***\n"
        ).replace("\n", newline)

    def apply(self, raw, **overrides):
        """Supply an explicit source/catalog association for each authored case."""
        args = dict(source_id=50103, metadata_id=50103, titles=("A Story",))
        args.update(overrides)
        before = self.cleaner.strip_boilerplate(raw)
        return before, numeric_notice_candidate.extend(before, **args)

    def test_exact_binding_preserves_original_offsets_and_newlines(self):
        for newline in ("\n", "\r\n", "\r"):
            with self.subTest(newline=newline):
                raw = self.raw(newline=newline)
                before, after = self.apply(raw)
                self.assertEqual(after.text, "Narrative." + newline * 2)
                self.assertEqual(after.original, raw)
                self.assertEqual(after.content_start, before.content_start)
                self.assertEqual(after.content_end, raw.index(self.notice))
                self.assertEqual(after.markers[1].line, 4)
                self.assertEqual(after.diagnostics[-1].code, "numeric_notice_removed")

    def test_wrong_missing_or_noncanonical_identity_preserved(self):
        for args in (
            {"source_id": 1},
            {"metadata_id": 1},
            {"metadata_id": None},
            {"source_id": True},
            {"source_id": "50103"},
            {"titles": ()},
            {"titles": ("Another Story",)},
            {"titles": ("A—Story",)},
        ):
            with self.subTest(args=args):
                before, after = self.apply(self.raw(), **args)
                self.assertIs(after, before)
        before, after = self.apply(self.raw(marker="050103"))
        self.assertIs(after, before)

    def test_no_fuzzy_matching_but_existing_case_space_semantics(self):
        before, after = self.apply(self.raw(), titles=("a\tSTORY",))
        self.assertNotEqual(before.content_end, after.content_end)
        before, after = self.apply(self.raw(), titles=("A Story!",))
        self.assertIs(before, after)

    def test_nonterminal_quoted_wrapped_and_empty_author_notices_preserved(self):
        for notice in (
            self.notice + "\nMore narrative.",
            '"' + self.notice + '"',
            self.notice.replace(", by", ",\nby"),
            self.notice.replace("An Author", "  "),
            "A narrator says: " + self.notice,
        ):
            with self.subTest(notice=notice):
                before, after = self.apply(self.raw("Narrative.\n" + notice + "\n"))
                self.assertIs(after, before)

    def test_missing_ambiguous_uncorroborated_envelope_preserved(self):
        good = self.raw()
        for raw in (
            good + good,
            good + "Unverified footer.\n",
            "Unverified header.\n" + good,
            good.replace("*** START", "*** BEGIN"),
            self.notice,
        ):
            with self.subTest(raw=raw):
                before, after = self.apply(raw)
                self.assertIs(after, before)

    def test_empty_remainder_preserved(self):
        before, after = self.apply(self.raw(self.notice + "\n"))
        self.assertIs(after, before)

    def test_already_removed_title_notice_is_not_processed_twice(self):
        before, after = self.apply(self.raw(marker="A Story"))
        self.assertIs(after, before)
        self.assertNotIn(self.notice, after.text)

    def test_internal_notice_not_removed_with_terminal_one(self):
        body = "Narrative.\n" + self.notice + "\nMore narrative.\n" + self.notice + "\n"
        _, after = self.apply(self.raw(body))
        self.assertEqual(
            after.text, "Narrative.\n" + self.notice + "\nMore narrative.\n"
        )


if __name__ == "__main__":
    unittest.main()
