import unittest
from lcats.gatherers.mass_quantities import frontmatter_precision
from lcats.gatherers.mass_quantities import boundary_features


class FrontmatterTest(unittest.TestCase):

    def test_blank_lines_not_sufficient(self):
        lines = [
            "TITLE",
            "",
            "",
            "An opening paragraph that should not be removed.",
            "",
            "* * * * *",
            "",
            "The story continues.",
        ]
        self.assertEqual(
            frontmatter_precision.refine_promotional_blurb_boundary(
                lines, 3, len(lines)
            ),
            3,
        )

    def test_real_italic_prologue_not_removed(self):
        lines = [
            "BY SOME WRITER",
            "",
            "_We watched the ship land at dawn._",
            "",
            "_The crowds were silent._",
            "",
            "* * * * *",
            "",
            "The sequel.",
        ]
        self.assertEqual(
            frontmatter_precision.refine_promotional_blurb_boundary(
                lines, 2, len(lines)
            ),
            2,
        )

    def test_no_backward_move_without_evidence(self):
        lines = [
            "An opening paragraph.",
            "",
            "",
            "Another paragraph.",
            "",
            "",
            "Yet another paragraph.",
        ]
        self.assertEqual(
            boundary_features.preserve_structural_opening(
                lines,
                6,
                len(lines),
                [],
                [],
                title_match=lambda *a: None,
                author_match=lambda *a: None,
                warnings=[],
            ),
            6,
        )


if __name__ == "__main__":
    unittest.main()
