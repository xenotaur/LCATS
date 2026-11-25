"""Regression tests for four explicit Gutenberg terminal structures."""

import unittest

from lcats.gatherers.mass_quantities import parser


ENDING = "The final words of the story remain untouched."


def _extract(*ending_lines):
    """Exercise the full Gutenberg cleaning path on a short synthetic source."""
    source = "\n".join([
        "Title: A Story", "Author: Jane Example",
        "*** START OF THE PROJECT GUTENBERG EBOOK A STORY ***",
        "", "A Story", "By Jane Example", "",
        "A character returned from the distant mountains after many years.",
        "", ENDING, "", *ending_lines, "",
        "*** END OF THE PROJECT GUTENBERG EBOOK A STORY ***",
    ])
    return parser.clean_gutenberg_story(
        source, title="A Story", authors=["Example, Jane"],
        return_diagnostics=True,
    )


class TerminalFourCasesTest(unittest.TestCase):
    """Remove only the four known editorial tail forms."""

    def test_72379_numbered_footnotes_without_heading(self):
        body, report = _extract(
            "The End", "", "[1] The message as it came in was edited.",
            "", "[2] The metropolitan papers reported the meteor.",
        )
        self.assertEqual(body.strip().splitlines()[-1], ENDING)
        self.assertIn("[1] The message", report["terminal_footnotes"])
        self.assertIn("[2] The metropolitan", report["terminal_footnotes"])

    def test_25404_illustrated_works_advertisement(self):
        body, report = _extract(
            "THE END.", "", "ILLUSTRATED WORKS BY L. FROLICH.", "",
            "LITTLE LUCY'S WONDERFUL GLOBE. Crown 4to. cloth gilt.", "",
            "MACMILLAN AND CO., LONDON.", "",
            "LONDON: R. CLAY, SONS, AND TAYLOR, PRINTERS, BREAD STREET HILL.",
        )
        self.assertEqual(body.strip().splitlines()[-1], ENDING)
        self.assertNotIn("ILLUSTRATED WORKS", body)
        self.assertIsNone(report["terminal_footnotes"])

    def test_44319_press_imprint_preserves_dateline(self):
        body, _ = _extract(
            "EVANSTON, November, 1895.", "",
            "PRESS OF W. B. CONKEY COMPANY, CHICAGO.",
        )
        self.assertIn("EVANSTON, November, 1895.", body)
        self.assertNotIn("PRESS OF W. B. CONKEY", body)

    def test_17083_city_prefix_printer_imprint(self):
        body, _ = _extract(
            "London:--Printed by G. BARCLAY, Castle St. Leicester Sq.",
        )
        self.assertEqual(body.strip().splitlines()[-1], ENDING)

    def test_narrative_after_the_end_is_preserved(self):
        body, report = _extract(
            "THE END", "", "The character looked up and started speaking again.",
        )
        self.assertIn("The character looked up", body)
        self.assertIn("THE END", body)
        self.assertIsNone(report["terminal_footnotes"])

    def test_ambiguous_footnote_without_end_marker_preserved(self):
        body, report = _extract("[1] A fictional character numbered this note.")
        self.assertIn("[1] A fictional character", body)
        self.assertIsNone(report["terminal_footnotes"])

    def test_printer_mentioned_inside_narrative_preserved(self):
        body, _ = _extract('She said "London:--Printed by" as part of her joke.')
        self.assertIn("London:--Printed by", body)


if __name__ == "__main__":
    unittest.main()
