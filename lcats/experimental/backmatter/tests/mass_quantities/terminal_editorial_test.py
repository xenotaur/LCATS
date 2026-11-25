"""Behavioral tests for explicit editorial material after Gutenberg stories."""

import unittest

from lcats.gatherers.mass_quantities import parser


OPENING = (
    "The station clock stopped at midnight while the travelers "
    "waited for the conductor to return."
)
ENDING = "At last the conductor came back, and they boarded the train."


def _text(*tail):
    """Build a Gutenberg-like document with an optional terminal appendix."""
    lines = [
        "Title: An Evening Train",
        "Author: Jane Example",
        "*** START OF THE PROJECT GUTENBERG EBOOK AN EVENING TRAIN ***",
        "",
        "An Evening Train",
        "By Jane Example",
        "",
        OPENING,
        "",
        ENDING,
        "",
        *tail,
        "",
        "*** END OF THE PROJECT GUTENBERG EBOOK AN EVENING TRAIN ***",
    ]
    return "\n".join(lines)


def _extract(*tail):
    """Extract the document using the actual public parser interface."""
    return parser.clean_gutenberg_story(
        _text(*tail),
        title="An Evening Train",
        authors=["Jane Example"],
    )


class TerminalEditorialTest(unittest.TestCase):
    """Test full extraction rather than source-level implementation details."""

    def test_plain_transcriber_notes(self):
        result = _extract(
            "THE END", "", "Transcriber Notes:", "",
            "This ebook was produced from a magazine issue.",
            "Page 12: corrected a misprint.",
        )
        self.assertIn(ENDING, result)
        self.assertIn("THE END", result)
        self.assertNotIn("Transcriber Notes", result)
        self.assertNotIn("magazine issue", result)

    def test_inline_note_heading(self):
        result = _extract(
            "Transcribers note: This etext was produced from a magazine."
        )
        self.assertIn(ENDING, result)
        self.assertNotIn("This etext was produced", result)

    def test_apostrophe_and_period_heading(self):
        result = _extract("Transcriber's note.", "", "Printer's corrections:")
        self.assertNotIn("Transcriber's note", result)
        self.assertIn(ENDING, result)

    def test_boxed_transcriber_note(self):
        result = _extract(
            "+------------------------------------------------+",
            "|           Transcriber's Note and Errata         |",
            "+------------------------------------------------+",
            "| This etext was produced from a magazine.       |",
            "+------------------------------------------------+",
        )
        self.assertIn(ENDING, result)
        self.assertNotIn("Transcriber's Note", result)
        self.assertNotIn("+------------------------------------------------+", result)

    def test_boxed_typographical_corrections(self):
        result = _extract(
            "+------------------------------------------------+",
            "| Typographical errors corrected in text:        |",
            "| Page 12: 'teh' changed to 'the'.              |",
            "+------------------------------------------------+",
        )
        self.assertIn(ENDING, result)
        self.assertNotIn("Typographical errors corrected", result)

    def test_lengthy_correction_table(self):
        corrections = [f"Page {number}: corrected a printing error." for number in range(60)]
        result = _extract("THE END", "", "Transcribers Notes:", *corrections)
        self.assertIn(ENDING, result)
        self.assertNotIn("Page 59", result)

    def test_preserves_narrative_mention(self):
        result = _extract(
            '"The transcriber notes that our journey is nearly over," she said.',
            "The train pulled into the station with a final squeal.",
        )
        self.assertIn("transcriber notes", result)
        self.assertIn("final squeal", result)

    def test_does_not_trim_unlabelled_appendix(self):
        result = _extract("An Afterword", "", "Years later, they met again.")
        self.assertIn("Years later", result)

    def test_does_not_trim_unlabelled_box(self):
        result = _extract(
            "+------------------------------------------------+",
            "| A poem carved into the train station wall.     |",
            "+------------------------------------------------+",
        )
        self.assertIn("A poem carved", result)

    def test_preserves_terminal_author_signature(self):
        result = _extract("--JANE EXAMPLE", "", "Transcriber Notes", "Editorial details")
        self.assertIn(ENDING, result)
        self.assertNotIn("Editorial details", result)

    def test_preserves_end_marker_without_note(self):
        result = _extract("THE END")
        self.assertIn("THE END", result)


if __name__ == "__main__":
    unittest.main()
