"""Historical explanations preserve source text and refuse unrelated differences."""

import unittest

from lcats.gatherers import historical_review
from lcats.gatherers import readiness

SEPARATOR = "       *       *       *       *       *"
BEFORE = "The ship arrived.\n\n"
AFTER = "\n\nThey went home."


class HistoricalReviewTests(unittest.TestCase):
    def test_exact_source_separator_and_exterior_indent_are_explained(self):
        selected = BEFORE + SEPARATOR + AFTER
        old = "    " + BEFORE + AFTER + "\n"
        evidence = historical_review.explain_typography(selected, old)
        self.assertTrue(evidence["complete"])
        self.assertFalse(evidence["publication_approved"])
        self.assertEqual(evidence["residual_shape"], "explained_typography")
        self.assertEqual(
            evidence["comparison_selected_sha256"],
            evidence["comparison_historical_sha256"],
        )
        self.assertEqual(evidence["selected_sha256"], readiness.text_sha256(selected))
        self.assertEqual(evidence["historical_sha256"], readiness.text_sha256(old))
        for text, key in (
            (selected, "selected_comparison_ranges"),
            (old, "historical_comparison_ranges"),
        ):
            for item in evidence[key]:
                a, b = item["span"]
                self.assertEqual(text[a:b], item["text"])
                self.assertEqual(readiness.text_sha256(text[a:b]), item["sha256"])
        self.assertEqual(selected, BEFORE + SEPARATOR + AFTER)

    def test_exact_equality_is_separate_from_typography(self):
        evidence = historical_review.explain_typography("Story.", "Story.")
        self.assertTrue(evidence["complete"])
        self.assertEqual(evidence["residual_shape"], "exact_equality")

    def test_prose_deletion_reordering_and_added_blurb_are_not_explained(self):
        for selected, old in (
            ("First.\n\nLast.", "First.\n\nMissing sentence.\n\nLast."),
            ("Last.\n\nFirst.", "First.\n\nLast."),
            ("A thrilling tale!\n\n" + BEFORE + SEPARATOR + AFTER, BEFORE + AFTER),
            (
                BEFORE + SEPARATOR + AFTER,
                "An omitted introduction.\n\n" + BEFORE + AFTER,
            ),
        ):
            with self.subTest(selected=selected, old=old):
                self.assertFalse(
                    historical_review.explain_typography(selected, old)["complete"]
                )

    def test_boundary_shape_is_diagnostic_not_a_blurb_classification(self):
        result = historical_review.explain_typography(
            "Ambiguous opening.\n\nStory.", "Story."
        )
        self.assertEqual(result["residual_shape"], "additional_boundary_text")
        self.assertGreater(result["additional_prefix_characters"], 0)
        self.assertFalse(result["complete"])
        self.assertFalse(result["publication_approved"])

    def test_separator_embedded_in_narrative_or_nonparagraph_is_never_ignored(self):
        for new in (
            BEFORE + SEPARATOR + " some narrative" + AFTER,
            "Text.\n" + SEPARATOR + "\nMore.",
            SEPARATOR + AFTER,
            BEFORE + SEPARATOR,
            BEFORE + "* * *" + AFTER,
        ):
            with self.subTest(new=new):
                result = historical_review.explain_typography(new, BEFORE + AFTER)
                self.assertFalse(result["complete"])
                self.assertFalse(
                    any(
                        p["kind"] == "preserved_scene_separator"
                        for p in result["selected_comparison_ranges"]
                    )
                )

    def test_missing_source_separator_cannot_be_excused(self):
        self.assertFalse(
            historical_review.explain_typography(
                BEFORE + AFTER, BEFORE + SEPARATOR + AFTER
            )["complete"]
        )

    def test_interior_indentation_and_unicode_whitespace_are_material(self):
        for old in ("First.\n\n    Last.", "First.  Last.", "\u00a0First.\n\nLast."):
            with self.subTest(old=old):
                self.assertFalse(
                    historical_review.explain_typography("First.\n\nLast.", old)[
                        "complete"
                    ]
                )

    def test_multiple_separators_remain_in_exact_source_order(self):
        new = BEFORE + SEPARATOR + AFTER + "\n\n" + SEPARATOR + "\n\nFin."
        old = new.replace(SEPARATOR, "")
        result = historical_review.explain_typography(new, old)
        self.assertTrue(result["complete"])
        self.assertEqual(len(result["selected_comparison_ranges"]), 2)
        self.assertEqual(result["selected_sha256"], readiness.text_sha256(new))

    def test_empty_whitespace_and_invalid_inputs_do_not_qualify(self):
        for new, old in (("", ""), (" \n", "\t"), ("Story.", "")):
            self.assertFalse(historical_review.explain_typography(new, old)["complete"])
        for value in (None, 2, "x" * (historical_review.MAX_CHARACTERS + 1)):
            with self.assertRaises(ValueError):
                historical_review.explain_typography(value, "Story.")
