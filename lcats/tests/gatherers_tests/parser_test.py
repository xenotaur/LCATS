"""Behavioral regression tests for Gutenberg story parsing.

These tests use deterministic, synthetic Gutenberg documents and exercise real
parser functions without network access, filesystem writes, or implementation
mocks. Integration call-order checks remain in parser_wiring_test.py.
"""

import unittest

from lcats.gatherers.mass_quantities import parser


START = "*** START OF THE PROJECT GUTENBERG EBOOK SAMPLE ***"
END = "*** END OF THE PROJECT GUTENBERG EBOOK SAMPLE ***"
OPENING = (
    "The lantern flickered as the travelers approached the station, "
    "and nobody spoke until the train arrived."
)
CONTINUATION = (
    "Across the platform the conductor waited quietly, while the "
    "last passengers searched for their tickets."
)


def _document(*body, title="The Lantern Station", author="Ada Example", wrappers=True):
    """Create a short Gutenberg-like text with predictable physical lines.

    Args:
        *body: Text lines placed after the display title and byline.
        title: Display heading in the story body.
        author: Byline name in the story body.
        wrappers: Whether to include Gutenberg START and END markers.

    Returns:
        Synthetic Gutenberg text with normalized newlines.
    """
    lines = [title, f"By {author}", "", *body]
    if wrappers:
        lines = ["Title: " + title, "Author: " + author, START, "", *lines, "", END]
    return "\n".join(lines)


class ParserBoundaryTest(unittest.TestCase):
    """Check real boundary decisions rather than source-level wiring."""

    def test_gutenberg_markers_excluded(self):
        text = _document(OPENING, "", CONTINUATION)
        lines = text.splitlines()
        start, end, report = parser.identify_story_boundaries(
            text, title="The Lantern Station", authors=["Ada Example"]
        )
        self.assertEqual(lines[start], OPENING)
        self.assertEqual(lines[end].strip(), "")
        self.assertEqual(lines[end + 1], END)
        self.assertTrue(report.start_marker_found)
        self.assertTrue(report.end_marker_found)
        self.assertTrue(report.title_found)
        self.assertEqual(report.matched_author, "Ada Example")
        self.assertEqual(report.narrative_start_line, start + 1)

    def test_diagnostics_report_missing_gutenberg_markers(self):
        text = _document(OPENING, wrappers=False)
        _, _, report = parser.identify_story_boundaries(
            text, title="The Lantern Station", authors=["Ada Example"]
        )
        self.assertFalse(report.start_marker_found)
        self.assertFalse(report.end_marker_found)
        self.assertIn("no_standard_start_marker", report.warnings)
        self.assertIn("no_standard_end_marker", report.warnings)

    def test_header_metadata_is_used_when_not_supplied(self):
        text = _document(OPENING)
        _, _, report = parser.identify_story_boundaries(text)
        self.assertTrue(report.title_found)
        self.assertEqual(report.matched_author, "Ada Example")

    def test_explicit_author_takes_precedence_over_header(self):
        text = _document(OPENING)
        _, _, report = parser.identify_story_boundaries(
            text, title="The Lantern Station", authors=["Someone Else"]
        )
        self.assertNotEqual(report.matched_author, "Ada Example")

    def test_line_ending_normalization_preserves_opening(self):
        text = _document(OPENING).replace("\n", "\r\n")
        cleaned = parser.clean_gutenberg_story(
            text, title="The Lantern Station", authors=["Ada Example"]
        )
        self.assertTrue(cleaned.startswith(OPENING))
        self.assertNotIn("\r", cleaned)

    def test_title_can_span_multiple_lines(self):
        lines = ["THE LANTERN", "STATION", "", "By Ada Example", "", OPENING]
        match = parser._title_span(lines, 0, len(lines), "The Lantern Station")
        self.assertEqual(match, 1)

    def test_title_can_span_one_internal_blank_line(self):
        lines = ["THE LANTERN", "", "STATION", "", OPENING]
        match = parser._title_span(lines, 0, len(lines), "The Lantern Station")
        self.assertEqual(match, 2)

    def test_title_match_is_not_a_random_prefix(self):
        self.assertFalse(parser._title_line("The Lantern", "The Lantern Station"))
        self.assertTrue(
            parser._title_line("THE LANTERN STATION", "The Lantern Station")
        )

    def test_author_matches_reversed_bibliographic_name(self):
        self.assertEqual(
            parser._author_line("By Ada Example", ["Example, Ada"]),
            "Example, Ada",
        )

    def test_author_matches_middle_initial(self):
        self.assertEqual(
            parser._author_line("By Ada B. Example", ["Ada Beatrice Example"]),
            "Ada Beatrice Example",
        )

    def test_author_name_in_longer_prose_is_not_signature(self):
        self.assertIsNone(
            parser._terminal_author_signature(
                "Ada Example stepped into the corridor.", ["Ada Example"]
            )
        )

    def test_known_terminal_signature_removed(self):
        lines = [OPENING, "", "-- Ada Example"]
        end, signature, warnings = parser._find_narrative_end(
            lines, 0, len(lines), ["Ada Example"]
        )
        self.assertEqual(end, 2)
        self.assertEqual(signature, "Ada Example")
        self.assertIn("removed_terminal_author_signature", warnings)

    def test_terminal_editorial_note_removed(self):
        lines = [OPENING, "", "Transcriber's Note:", "", "This ebook fixes a typo."]
        end, _, warnings = parser._find_narrative_end(lines, 0, len(lines), [])
        self.assertEqual(end, 1)
        self.assertIn("removed_terminal_editorial_note", warnings)

    def test_narrative_prose_at_end_retained(self):
        lines = [OPENING, "", CONTINUATION]
        end, signature, warnings = parser._find_narrative_end(
            lines, 0, len(lines), ["Ada Example"]
        )
        self.assertEqual(end, len(lines))
        self.assertIsNone(signature)
        self.assertNotIn("removed_terminal_editorial_note", warnings)


class ParserCleaningTest(unittest.TestCase):
    """Verify narrative transformations and their configurable switches."""

    def test_line_unwrapping_and_paragraph_boundaries(self):
        cleaned = parser.clean_story_text(
            "First physical line\nsecond physical line\n\nNext paragraph."
        )
        self.assertEqual(
            cleaned, "First physical line second physical line\n\nNext paragraph.\n"
        )

    def test_preserve_physical_lines_when_unwrap_disabled(self):
        cleaned = parser.clean_story_text(
            "First physical line\nsecond physical line", unwrap_lines=False
        )
        self.assertEqual(cleaned, "First physical line\nsecond physical line\n")

    def test_scene_breaks_removed_by_default(self):
        cleaned = parser.clean_story_text("First scene.\n\n* * *\n\nSecond scene.")
        self.assertNotIn("***", cleaned)
        self.assertIn("First scene.", cleaned)
        self.assertIn("Second scene.", cleaned)

    def test_scene_breaks_can_be_preserved(self):
        cleaned = parser.clean_story_text(
            "First scene.\n\n* * *\n\nSecond scene.", remove_scene_breaks=False
        )
        self.assertIn("***", cleaned)

    def test_italics_markers_are_optional(self):
        self.assertEqual(parser.clean_story_text("_A quiet room._"), "A quiet room.\n")
        self.assertEqual(
            parser.clean_story_text("_A quiet room._", strip_italics=False),
            "_A quiet room._\n",
        )

    def test_remove_the_end_is_optional(self):
        text = "The door closed.\n\nTHE END"
        self.assertIn("THE END", parser.clean_story_text(text))
        self.assertNotIn("THE END", parser.clean_story_text(text, remove_the_end=True))

    def test_the_end_inside_narrative_not_removed(self):
        text = "She wrote THE END on the page and closed the book."
        self.assertIn("THE END", parser.clean_story_text(text, remove_the_end=True))

    def test_bracketed_editorial_note_removed_and_counted(self):
        text = "A first sentence.\n\n[Illustration: portrait]\n\nA last sentence."
        cleaned, removed = parser.clean_story_text(text, return_removed_count=True)
        self.assertNotIn("portrait", cleaned)
        self.assertIn("A last sentence.", cleaned)
        self.assertEqual(removed, 1)

    def test_empty_input_returns_empty_string(self):
        self.assertEqual(parser.clean_story_text(""), "")


class ParserExtractionTest(unittest.TestCase):
    """Exercise the end-to-end extraction API with synthetic stories."""

    def test_full_extraction_excludes_gutenberg_wrapper_and_byline(self):
        text = _document(OPENING, "", CONTINUATION)
        story = parser.clean_gutenberg_story(
            text, title="The Lantern Station", authors=["Ada Example"]
        )
        self.assertTrue(story.startswith(OPENING))
        self.assertIn(CONTINUATION, story)
        self.assertNotIn("PROJECT GUTENBERG", story)
        self.assertNotIn("By Ada Example", story)
        self.assertNotIn("The Lantern Station", story)

    def test_extraction_with_diagnostics_returns_dictionary(self):
        text = _document(OPENING)
        story, report = parser.clean_gutenberg_story(
            text,
            title="The Lantern Station",
            authors=["Ada Example"],
            return_diagnostics=True,
        )
        self.assertTrue(story.startswith(OPENING))
        self.assertIsInstance(report, dict)
        self.assertTrue(report["start_marker_found"])
        self.assertTrue(report["end_marker_found"])
        self.assertIn(report["boundary_confidence"], {"low", "medium", "high"})
        self.assertGreater(report["narrative_start_line"], 0)

    def test_extraction_strips_terminal_the_end_when_requested(self):
        text = _document(OPENING, "", "THE END")
        story = parser.clean_gutenberg_story(
            text,
            title="The Lantern Station",
            authors=["Ada Example"],
            remove_the_end=True,
        )
        self.assertTrue(story.startswith(OPENING))
        self.assertNotIn("THE END", story)

    def test_extraction_keeps_scene_divider_when_requested(self):
        text = _document(OPENING, "", "* * *", "", CONTINUATION)
        story = parser.clean_gutenberg_story(
            text,
            title="The Lantern Station",
            authors=["Ada Example"],
            remove_scene_breaks=False,
        )
        self.assertIn("***", story)
        self.assertIn(CONTINUATION, story)

    def test_extraction_returns_trailing_newline(self):
        text = _document(OPENING)
        story = parser.clean_gutenberg_story(
            text, title="The Lantern Station", authors=["Ada Example"]
        )
        self.assertTrue(story.endswith("\n"))


if __name__ == "__main__":
    unittest.main()
