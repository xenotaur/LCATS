"""Tests for lcats.gatherers.mass_quantities.parser."""

import unittest
from parameterized import parameterized

from lcats.gatherers import parser
from lcats.utils import capture


class TestIsNumber(unittest.TestCase):
    """Tests for parser.is_number."""

    @parameterized.expand(
        [
            ("integer_string", "42", True),
            ("negative_integer", "-1", True),
            ("zero", "0", True),
            ("year_like", "1920", True),
            ("float_string", "3.14", False),
            ("word", "hello", False),
            ("empty_string", "", False),
            ("whitespace", "  ", False),
        ]
    )
    def test_is_number(self, _name, s, expected):
        self.assertEqual(parser.is_number(s), expected)


class TestOnlyEnglish(unittest.TestCase):
    """Tests for parser.only_english."""

    def test_only_english_single(self):
        self.assertTrue(parser.only_english(["en"]))

    def test_only_english_set(self):
        self.assertTrue(parser.only_english({"en"}))

    def test_mixed_languages(self):
        self.assertFalse(parser.only_english(["en", "fr"]))

    def test_no_english(self):
        self.assertFalse(parser.only_english(["fr"]))

    def test_empty_list(self):
        self.assertFalse(parser.only_english([]))

    def test_custom_target(self):
        self.assertTrue(parser.only_english(["fr"], target="fr"))

    def test_custom_target_not_in_list(self):
        self.assertFalse(parser.only_english(["en"], target="fr"))


class TestFiction(unittest.TestCase):
    """Tests for parser.fiction."""

    def test_fiction_in_subject(self):
        self.assertTrue(parser.fiction(["American fiction"]))

    def test_fiction_case_insensitive(self):
        self.assertTrue(parser.fiction(["FICTION"]))

    def test_no_fiction(self):
        self.assertFalse(parser.fiction(["poetry"]))

    def test_empty_subject(self):
        self.assertFalse(parser.fiction([]))

    def test_fiction_among_multiple(self):
        self.assertTrue(parser.fiction(["PS", "Short stories", "American fiction"]))


class TestShortStory(unittest.TestCase):
    """Tests for parser.short_story."""

    def test_short_stories_in_subject(self):
        self.assertTrue(parser.short_story(["Short stories"]))

    def test_short_story_singular(self):
        self.assertTrue(parser.short_story(["Short story"]))

    def test_case_insensitive(self):
        self.assertTrue(parser.short_story(["SHORT STORIES"]))

    def test_no_short_story(self):
        self.assertFalse(parser.short_story(["American fiction"]))

    def test_empty_subject(self):
        self.assertFalse(parser.short_story([]))


class TestLocFiction(unittest.TestCase):
    """Tests for parser.loc_fiction."""

    def test_ps_present(self):
        self.assertTrue(parser.loc_fiction(["PS"]))

    def test_pr_present(self):
        self.assertTrue(parser.loc_fiction(["PR"]))

    def test_both_present(self):
        self.assertTrue(parser.loc_fiction(["PS", "PR"]))

    def test_neither_present(self):
        self.assertFalse(parser.loc_fiction(["PQ"]))

    def test_empty(self):
        self.assertFalse(parser.loc_fiction([]))

    def test_substring_does_not_match(self):
        """PS must be exact, not a substring."""
        self.assertFalse(parser.loc_fiction(["PSX"]))


class TestSubjectOk(unittest.TestCase):
    """Tests for parser.subject_ok."""

    def test_valid_subject(self):
        self.assertTrue(parser.subject_ok(["PS", "Short stories"]))

    def test_loc_plus_fiction(self):
        self.assertTrue(parser.subject_ok(["PR", "American fiction"]))

    def test_no_loc(self):
        self.assertFalse(parser.subject_ok(["Short stories"]))

    def test_no_story_or_fiction(self):
        self.assertFalse(parser.subject_ok(["PS", "poetry"]))

    def test_empty(self):
        self.assertFalse(parser.subject_ok([]))


class TestAuthorOk(unittest.TestCase):
    """Tests for parser.author_ok."""

    def test_non_empty_author(self):
        self.assertTrue(parser.author_ok(["Smith, John"]))

    def test_empty_author(self):
        self.assertFalse(parser.author_ok([]))

    def test_multiple_authors(self):
        self.assertTrue(parser.author_ok(["Smith, John", "Doe, Jane"]))


class TestTitleOk(unittest.TestCase):
    """Tests for parser.title_ok."""

    def test_simple_title(self):
        self.assertTrue(parser.title_ok(["The Bell"]))

    def test_gutenberg_index_title(self):
        self.assertFalse(parser.title_ok(["Index of the Project Gutenberg Works"]))

    def test_excluded_word_volume(self):
        self.assertFalse(parser.title_ok(["Complete Works Volume 2"]))

    def test_excluded_word_part(self):
        self.assertFalse(parser.title_ok(["Stories Part 1"]))

    def test_excluded_word_poem(self):
        self.assertFalse(parser.title_ok(["The poem"]))

    def test_multiple_good_titles(self):
        self.assertTrue(parser.title_ok(["The Bell", "The Shadow"]))


class TestMakeTitle(unittest.TestCase):
    """Tests for parser.make_title."""

    def test_simple_title_unchanged(self):
        self.assertEqual(parser.make_title("The Bell"), "The Bell")

    def test_title_with_year_removed(self):
        self.assertEqual(parser.make_title("The Bell\n1920"), "The Bell")

    def test_year_too_early(self):
        """Years before 1800 are not removed."""
        self.assertEqual(parser.make_title("The Bell\n1799"), "The Bell\n1799")

    def test_year_too_late(self):
        """Years after 1960 are not removed."""
        self.assertEqual(parser.make_title("The Bell\n1970"), "The Bell\n1970")

    def test_crlf_title_split(self):
        result = parser.make_title("The Bell\r\nSubtitle")
        self.assertEqual(result, "The Bell")

    def test_no_crlf_and_no_year(self):
        result = parser.make_title("The Bell")
        self.assertEqual(result, "The Bell")


class TestChaptered(unittest.TestCase):
    """Tests for parser.chaptered."""

    def test_has_contents(self):
        text = "Some text\n\ncontents\n\nmore text"
        self.assertTrue(parser.chaptered(text))

    def test_has_contents_with_period(self):
        text = "Some text\n\ncontents.\n\nmore text"
        self.assertTrue(parser.chaptered(text))

    def test_chapter_i_and_ii(self):
        text = "Chapter I\n\nsome content\n\nChapter II\n\nmore content"
        self.assertTrue(parser.chaptered(text))

    def test_roman_numerals_i_and_ii(self):
        text = "Some text\n\ni\n\nmore text\n\nii\n\neven more"
        self.assertTrue(parser.chaptered(text))

    def test_only_one_chapter_marker(self):
        text = "Some text\n\ni\n\nno second marker"
        self.assertFalse(parser.chaptered(text))

    def test_no_chapters(self):
        text = "Just some plain text\n\nwith no chapters"
        self.assertFalse(parser.chaptered(text))

    def test_part_i_and_part_ii(self):
        text = "Part I\n\nsome content\n\nPart II\n\nmore"
        self.assertTrue(parser.chaptered(text))


class TestHowManyTitles(unittest.TestCase):
    """Tests for parser.how_many_titles."""

    def test_no_title(self):
        text = "Some paragraph.\n\nAnother paragraph."
        self.assertEqual(parser.how_many_titles(text, ["The Bell"]), 0)

    def test_one_title(self):
        text = "Some paragraph.\n\nThe Bell\n\nAnother paragraph."
        self.assertEqual(parser.how_many_titles(text, ["The Bell"]), 1)

    def test_two_titles(self):
        text = "The Bell\n\nSome text.\n\nThe Bell\n\nMore text."
        self.assertEqual(parser.how_many_titles(text, ["The Bell"]), 2)


class TestIntrusiveParagraph(unittest.TestCase):
    """Tests for parser.intrusive_paragraph."""

    def test_empty_paragraph(self):
        self.assertFalse(parser.intrusive_paragraph(""))

    def test_blank_lines_only(self):
        # Blank-only lines are skipped; result stays True
        self.assertTrue(parser.intrusive_paragraph("\n\n"))

    def test_normal_prose(self):
        self.assertFalse(parser.intrusive_paragraph("This is a normal paragraph."))

    def test_quoted_indented(self):
        """Lines with 4 spaces then a curly quote set result=False."""
        paragraph = "    \u201cQuoted text here\u201d"
        self.assertFalse(parser.intrusive_paragraph(paragraph))


class TestLineContainsTranscriberInfo(unittest.TestCase):
    """Tests for parser.line_contains_transcriber_info."""

    @parameterized.expand(
        [
            ("starts_with_transcriber", "Transcriber's note", True),
            ("bracket_transcriber", "[Transcriber's note]", True),
            ("underscore_transcriber", "_transcriber note_", True),
            ("not_transcriber", "Some normal line", False),
            ("empty", "", False),
            ("case_insensitive", "TRANSCRIBER note", True),
        ]
    )
    def test_line(self, _name, line, expected):
        self.assertEqual(parser.line_contains_transcriber_info(line), expected)


class TestLineContainsIllustration(unittest.TestCase):
    """Tests for parser.line_contains_illustration."""

    @parameterized.expand(
        [
            ("starts_with_illustrat", "Illustrated by John", True),
            ("bracket_illustrat", "[Illustration: A tree]", True),
            ("underscore_illustrat", "_Illustrated by_", True),
            ("not_illustration", "Some normal line", False),
            ("empty", "", False),
            ("case_insensitive", "ILLUSTRATION: fig 1", True),
        ]
    )
    def test_line(self, _name, line, expected):
        self.assertEqual(parser.line_contains_illustration(line), expected)


class TestLineContainsTitle(unittest.TestCase):
    """Tests for parser.line_contains_title."""

    def test_exact_match(self):
        self.assertTrue(parser.line_contains_title("The Bell", ["The Bell"]))

    def test_with_underscore_wrapping(self):
        self.assertTrue(parser.line_contains_title("_the bell_", ["The Bell"]))

    def test_with_trailing_period(self):
        self.assertTrue(parser.line_contains_title("The Bell.", ["The Bell"]))

    def test_too_different_length(self):
        self.assertFalse(
            parser.line_contains_title("The Bell is ringing loudly", ["The Bell"])
        )

    def test_no_match(self):
        self.assertFalse(parser.line_contains_title("Some other line", ["The Bell"]))

    def test_fuzzy_match(self):
        self.assertTrue(parser.line_contains_title("The Bell!", ["The Bell"]))

    def test_title_starts_with_the(self):
        """Lines without 'the' can match titles that start with 'the '."""
        self.assertTrue(parser.line_contains_title("Bell", ["the Bell"]))

    def test_multiline_rn(self):
        """Lines with rn\\n in the middle are joined before matching."""
        line = "The Bellrn\nsome text"
        self.assertTrue(parser.line_contains_title(line, ["the bell some text"]))

    def test_multiline_newline(self):
        """Lines with \\n (not rn\\n) are joined."""
        line = "The\nBell"
        self.assertTrue(parser.line_contains_title(line, ["The Bell"]))


class TestLineContainsAuthor(unittest.TestCase):
    """Tests for parser.line_contains_author."""

    def test_single_author_full_name(self):
        self.assertTrue(parser.line_contains_author("John Smith", ["Smith, John"], []))

    def test_single_author_not_found(self):
        self.assertFalse(parser.line_contains_author("Jane Doe", ["Smith, John"], []))

    def test_by_line_short(self):
        self.assertTrue(
            parser.line_contains_author("by John Smith", ["Smith, John"], [])
        )

    def test_by_alone(self):
        self.assertTrue(parser.line_contains_author("by", ["Smith, John"], []))

    def test_by_underscore(self):
        self.assertTrue(
            parser.line_contains_author("_by John Smith_", ["Smith, John"], [])
        )

    def test_two_authors(self):
        self.assertTrue(
            parser.line_contains_author(
                "John Smith and Jane Doe",
                ["Smith, John", "Doe, Jane"],
                [],
                limit=10,
            )
        )

    def test_two_authors_only_one_present(self):
        self.assertFalse(
            parser.line_contains_author(
                "John Smith",
                ["Smith, John", "Doe, Jane"],
                [],
                limit=10,
            )
        )

    def test_more_than_two_authors(self):
        """Three or more authors always returns False."""
        self.assertFalse(
            parser.line_contains_author(
                "John Smith, Jane Doe, Bob Brown",
                ["Smith, John", "Doe, Jane", "Brown, Bob"],
                [],
            )
        )

    def test_pen_name_match(self):
        """Author with known pen name matches the pen name."""
        # "Garrett, Randall" has pen name "Gordon, David"
        self.assertTrue(
            parser.line_contains_author("David Gordon", ["Garrett, Randall"], [])
        )


class TestIsBlankLine(unittest.TestCase):
    """Tests for parser.is_blank_line."""

    @parameterized.expand(
        [
            ("empty_string", "", True),
            ("single_space", " hello", True),
            ("newline_space", "\n hello", True),
            ("normal_line", "Hello world", False),
            ("tab_start", "\tHello", False),
        ]
    )
    def test_blank(self, _name, line, expected):
        self.assertEqual(parser.is_blank_line(line), expected)


class TestInBody(unittest.TestCase):
    """Tests for parser.in_body."""

    def test_normal_line_in_body(self):
        self.assertTrue(
            parser.in_body("This is story text.", "The Bell", ["Smith, John"], [])
        )

    def test_title_line_not_in_body(self):
        self.assertFalse(parser.in_body("The Bell", ["The Bell"], ["Smith, John"], []))

    def test_author_line_not_in_body(self):
        self.assertFalse(
            parser.in_body("John Smith", ["The Bell"], ["Smith, John"], [])
        )

    def test_blank_line_not_in_body(self):
        self.assertFalse(parser.in_body("", ["The Bell"], ["Smith, John"], []))

    def test_illustration_line_not_in_body(self):
        self.assertFalse(
            parser.in_body("Illustration: A drawing", ["The Bell"], ["Smith, John"], [])
        )


class TestPenNames(unittest.TestCase):
    """Tests for parser.pen_names."""

    def test_no_pen_name(self):
        result = parser.pen_names("Doe, John")
        self.assertEqual(result, ["Doe, John"])

    def test_with_pen_name(self):
        # "Garrett, Randall" has pen name "Gordon, David"
        result = parser.pen_names("Garrett, Randall")
        self.assertIn("Garrett, Randall", result)
        self.assertIn("Gordon, David", result)


class TestFixBody(unittest.TestCase):
    """Tests for parser.fix_body."""

    def test_removes_transcriber_info_from_start(self):
        text = "Transcriber's note: some note\n\nActual story begins here."
        result = parser.fix_body(text, ["A Story"], ["Smith, John"], [])
        self.assertNotIn("Transcriber", result)
        self.assertIn("Actual story begins here.", result)

    def test_removes_illustration_from_start(self):
        text = "Illustration: A drawing\n\nActual story begins here."
        result = parser.fix_body(text, ["A Story"], ["Smith, John"], [])
        self.assertNotIn("Illustration", result)
        self.assertIn("Actual story begins here.", result)

    def test_removes_etext_produced_from_start(self):
        text = "This etext was produced by volunteers\n\nActual story begins here."
        result = parser.fix_body(text, ["A Story"], ["Smith, John"], [])
        self.assertNotIn("This etext was produced", result)
        self.assertIn("Actual story begins here.", result)

    def test_removes_author_from_start(self):
        text = "John Smith\n\nActual story begins here."
        result = parser.fix_body(text, ["A Story"], ["Smith, John"], [])
        self.assertNotIn("John Smith", result)
        self.assertIn("Actual story begins here.", result)

    def test_preserves_normal_body(self):
        text = "First paragraph.\n\nSecond paragraph."
        result = parser.fix_body(text, ["A Story"], ["Smith, John"], [])
        self.assertIn("First paragraph.", result)
        self.assertIn("Second paragraph.", result)

    def test_does_remove_transcriber_in_last_paragraph(self):
        text = "First paragraph.\n\nSecond paragraph.\n\nTranscriber's note: late note"
        result = parser.fix_body(text, ["A Story"], ["Smith, John"], [])
        self.assertNotIn("Transcriber", result)


class TestBodyOfText(unittest.TestCase):
    """Tests for parser.body_of_text."""

    def setUp(self):
        self._output_suppression = capture.suppress_output()
        self._output_suppression.__enter__()
        self.addCleanup(self._output_suppression.__exit__, None, None, None)

    def _make_story(self, title, author_line, body):
        """Helper to create a story text with title, author, and body."""
        return f"{title}\n\n{author_line}\n\n{body}"

    def test_extracts_body_after_title_and_author(self):
        """The body should be extracted after the title and author lines."""
        text = self._make_story("The Bell", "John Smith", "Once upon a time.")
        result = parser.body_of_text(text, ["Smith, John"], [], "The Bell")
        self.assertIn("Once upon a time.", result)

    def test_body_excludes_title(self):
        """The title line should not be included in the body, even if it appears at the start."""
        text = self._make_story("The Bell", "John Smith", "Once upon a time.")
        result = parser.body_of_text(text, ["Smith, John"], [], "The Bell")
        self.assertNotIn("The Bell\n\nJohn Smith", result)

    def test_debug_flag_does_not_raise(self):
        """debug=True should not raise errors."""
        text = self._make_story("The Bell", "John Smith", "Once upon a time.")

        try:
            with capture.suppress_output():
                parser.body_of_text(text, ["Smith, John"], [], "The Bell", debug=True)
        except Exception as e:
            self.fail(f"body_of_text raised an exception with debug=True: {e}")

    def test_story_with_year_title(self):
        """Titles with year suffix are stripped correctly."""
        text = "The Bell\n\nJohn Smith\n\nOnce upon a time."
        result = parser.body_of_text(text, ["Smith, John"], [], "The Bell\n1920")
        self.assertIn("Once upon a time.", result)


class TestLineContainsTitleAdditional(unittest.TestCase):
    """Additional tests for line_contains_title covering fuzzy and no-match branches."""

    def test_fuzzy_match_fires_for_near_miss(self):
        """Line w/high similarity to title triggers fuzzy-match when no exact match exists."""
        # "The Bel" vs "The Bell": no exact match variant fires,
        # but SequenceMatcher ratio ~0.93 > 0.90 so the fuzzy branch returns True.
        self.assertTrue(parser.line_contains_title("The Bel", ["The Bell"]))

    def test_no_match_returns_false_for_non_the_title(self):
        """A line with no similarity and title not starting with 'the ' returns False."""
        # len diff = 3 (<=5), no exact match, low fuzzy ratio, title[:4] != "the "
        self.assertFalse(parser.line_contains_title("abcde", ["my story"]))


class TestLineContainsAuthorAdditional(unittest.TestCase):
    """Additional tests for line_contains_author covering single-name and long-by-line cases."""

    def test_single_name_no_comma(self):
        """Author with a single name (no comma) sets first_name to empty string."""
        self.assertTrue(parser.line_contains_author("Mark", ["Mark"], []))

    def test_by_line_over_limit_containing_names_returns_true(self):
        """A 'by' line with >=limit words that still contains author names returns True."""
        # 9 words: length check fails (len >= 8), but names are present, exercising lines 422-424.
        line = "by john smith the author of this story today"
        self.assertTrue(parser.line_contains_author(line, ["Smith, John"], []))


class TestFixBodyAdditional(unittest.TestCase):
    """Additional tests for fix_body covering the intrusive-paragraph branch."""

    def test_removes_intrusive_paragraph_at_start(self):
        """An intrusive paragraph (Classic reprint) at the start is skipped."""
        text = "classic reprint from SuperScienceStories\n\nActual story begins here."
        result = parser.fix_body(text, ["A Story"], ["Smith, John"], [])
        self.assertNotIn("Classic reprint", result)
        self.assertIn("Actual story begins here.", result)


class TestBodyOfTextAdditional(unittest.TestCase):
    """Additional tests for body_of_text covering the remaining break/continue branches."""

    def setUp(self):
        self._output_suppression = capture.suppress_output()
        self._output_suppression.__enter__()
        self.addCleanup(self._output_suppression.__exit__, None, None, None)

    def test_double_title_breaks_after_second_occurrence(self):
        """When the title appears twice, the loop breaks after both are found (line 612)."""
        text = "The Bell\n\nThe Bell\n\nThis is the body."
        result = parser.body_of_text(text, [], [], "The Bell")
        self.assertIn("This is the body.", result)

    def test_no_title_breaks_on_author(self):
        """When title is absent but the author is seen, the loop breaks (line 614)."""
        text = "John Smith\n\nThis is the body."
        result = parser.body_of_text(text, ["Smith, John"], [], "Absent Title")
        self.assertIn("This is the body.", result)

    def test_blank_paragraph_before_title_is_skipped(self):
        """A blank paragraph before the title is skipped via the is_blank_line branch (line 622)."""
        text = "\n\nThe Bell\n\nJohn Smith\n\nThis is the body."
        result = parser.body_of_text(text, ["Smith, John"], [], "The Bell")
        self.assertIn("This is the body.", result)

    def test_text_between_multiple_title_occurrences_is_skipped(self):
        """Paragraphs between multiple title occurrences are skipped (line 624)."""
        text = "The Bell\n\nMiddle text\n\nThe Bell\n\nThis is the body."
        result = parser.body_of_text(text, [], [], "The Bell")
        self.assertIn("This is the body.", result)

    def test_body_content_after_title_without_author_triggers_break(self):
        """Body content after title but w/o author present triggers the elif break (line 626)."""
        text = "The Bell\n\nThis is the body."
        result = parser.body_of_text(text, [], [], "The Bell")
        self.assertIn("This is the body.", result)

    def test_unknown_preface_before_title_is_preserved(self):
        """Unknown opening prose is evidence, not permission to skip to a later title."""
        text = "Preface text\n\nThe Bell\n\nJohn Smith\n\nThis is the body."
        result = parser.body_of_text(text, ["Smith, John"], [], "The Bell")
        self.assertIn("This is the body.", result)
        self.assertIn("Preface text", result)


if __name__ == "__main__":
    unittest.main()
