"""Offline tests of exact causal-ledger measurements and conservative grouping.

From lcats/, PYTHONPATH="$PWD/src" python -m unittest discover -s
../experiments/10_gettenberg_qualification/scripts -p qualify_narrow_causality_test.py
No catalog, historical dependency, network or corpus writes are required. These
checks validate measurement semantics; the pinned real-source replay separately
validates the complete experiment and its historical cleaner provenance.
"""

import unittest

from lcats.gettenberg import cleanup
import qualify_narrow_causality


class DeltaTest(unittest.TestCase):
    """Exact change intervals must reconstruct both inputs without fuzzy claims."""

    def check_delta(self, before, after, shape):
        result = qualify_narrow_causality.delta(before, after)
        self.assertEqual(result["shape"], shape)
        left, right = result["before_span"]
        new_left, new_right = result["after_span"]
        self.assertEqual(left, new_left)
        self.assertEqual(
            before[:left] + after[new_left:new_right] + before[right:], after
        )
        self.assertEqual(
            result["removed"]["sha256"],
            qualify_narrow_causality.sha(before[left:right]),
        )
        self.assertEqual(
            result["added"]["sha256"],
            qualify_narrow_causality.sha(after[new_left:new_right]),
        )
        return result

    def test_suffix(self):
        result = self.check_delta("story", "story\nnotice", "suffix_extension")
        self.assertTrue(result["whole_before_preserved"])
        self.assertFalse(result["equal_after_strip"])

    def test_prefix(self):
        result = self.check_delta("ending", "opening\nending", "prefix_extension")
        self.assertTrue(result["whole_before_preserved"])

    def test_mixed(self):
        result = self.check_delta("prefix old suffix", "prefix new suffix", "mixed")
        self.assertFalse(result["whole_before_preserved"])
        self.assertEqual(result["removed"]["excerpt"], "old")
        self.assertEqual(result["added"]["excerpt"], "new")

    def test_equal_and_empty(self):
        self.check_delta("story", "story", "equal")
        result = self.check_delta("", "story", "mixed")
        self.assertFalse(result["whole_before_preserved"])
        self.check_delta("story", "", "mixed")

    def test_whitespace_is_not_content_equivalence_for_empty_bodies(self):
        result = self.check_delta("story", "\nstory", "prefix_extension")
        self.assertTrue(result["equal_after_strip"])


class GroupTest(unittest.TestCase):
    """Mechanism names describe observed differences, never literary approval."""

    def test_terminal_notice(self):
        self.assertEqual(
            qualify_narrow_causality.body_group(
                "story", "story\n\nEnd of the Project Gutenberg EBook of A, by B"
            ),
            "terminal_notice_only",
        )

    def test_preceding_content_is_not_notice_only(self):
        self.assertEqual(
            qualify_narrow_causality.body_group(
                "story", "story\nfinal paragraph\nEnd of Project Gutenberg's A, by B"
            ),
            "terminal_notice_and_preceding_content",
        )

    def test_mention_inside_sentence_is_not_terminal_notice(self):
        self.assertEqual(
            qualify_narrow_causality.body_group(
                "story", "story tells of the End of the Project Gutenberg"
            ),
            "mixed_front_and_tail_effect",
        )

    def test_newline_only(self):
        self.assertEqual(
            qualify_narrow_causality.body_group("story", "\nstory"),
            "boundary_whitespace_only",
        )

    def test_wrapped_marker_and_interior_end(self):
        wrapped = "*** START OF THE PROJECT GUTENBERG EBOOK A\nTITLE ***\nbody\n*** END OF THE PROJECT GUTENBERG EBOOK A\nTITLE ***\n"
        result = cleanup.strip_boilerplate(wrapped)
        self.assertEqual(
            qualify_narrow_causality.refusal_group(result, wrapped),
            "wrapped_envelope_marker",
        )
        interior = "*** START OF THE PROJECT GUTENBERG EBOOK A ***\nbody\n*END*\n*** END OF THE PROJECT GUTENBERG EBOOK A ***\n"
        result = cleanup.strip_boilerplate(interior)
        self.assertEqual(
            qualify_narrow_causality.refusal_group(result, interior),
            "interior_star_end_is_competing_marker",
        )

    def test_unclosed_marker_is_not_claimed_to_be_wrapped(self):
        text = "*** START OF THE PROJECT GUTENBERG EBOOK A\nordinary next line\n"
        result = cleanup.strip_boilerplate(text)
        self.assertEqual(
            qualify_narrow_causality.refusal_group(result, text), "other_refusal"
        )

    def test_mixed_hunks_retain_exact_coordinates(self):
        before = "old heading\nshared narrative\nend"
        after = "shared narrative\nend\nnotice"
        hunks = qualify_narrow_causality.mixed_hunks(before, after)
        self.assertEqual(len(hunks), 2)
        for hunk in hunks:
            self.assertEqual(
                hunk["removed"]["excerpt"], before[slice(*hunk["before_span"])]
            )
            self.assertEqual(
                hunk["added"]["excerpt"], after[slice(*hunk["after_span"])]
            )

    def test_title_mismatch_is_refusal(self):
        text = "*** START OF THE PROJECT GUTENBERG EBOOK ABC ***\nbody\n*** END OF THE PROJECT GUTENBERG EBOOK AB ***\n"
        result = cleanup.strip_boilerplate(text)
        self.assertEqual(
            qualify_narrow_causality.refusal_group(result, text),
            "different_envelope_identifiers",
        )

    def test_source_excerpt_binds_exact_span(self):
        result = qualify_narrow_causality.source_excerpt("0123456789", 3, 6)
        self.assertEqual(result["span"], [3, 6])
        self.assertEqual(result["excerpt"], "345")
        self.assertEqual(result["preceding"], "012")
        self.assertEqual(result["following"], "6789")


if __name__ == "__main__":
    unittest.main()
