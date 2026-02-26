"""Tests for lcats.gatherers.mass_quantities.parser."""

import unittest
from unittest import mock
from parameterized import parameterized

from lcats.gatherers import parser


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
        self.assertTrue(parser.title_ok(frozenset(["The Bell"])))

    def test_gutenberg_index_title(self):
        self.assertFalse(
            parser.title_ok(frozenset(["Index of the Project Gutenberg Works"]))
        )

    def test_excluded_word_volume(self):
        self.assertFalse(parser.title_ok(frozenset(["Complete Works Volume 2"])))

    def test_excluded_word_part(self):
        self.assertFalse(parser.title_ok(frozenset(["Stories Part 1"])))

    def test_excluded_word_poem(self):
        self.assertFalse(parser.title_ok(frozenset(["The poem"])))

    def test_multiple_good_titles(self):
        self.assertTrue(parser.title_ok(frozenset(["The Bell", "The Shadow"])))


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
        text = "Some text\ncontents\nmore text"
        self.assertTrue(parser.chaptered(text))

    def test_has_contents_with_period(self):
        text = "Some text\ncontents.\nmore text"
        self.assertTrue(parser.chaptered(text))

    def test_chapter_i_and_ii(self):
        text = "Chapter I\nsome content\nChapter II\nmore content"
        self.assertTrue(parser.chaptered(text))

    def test_roman_numerals_i_and_ii(self):
        text = "Some text\ni\nmore text\nii\neven more"
        self.assertTrue(parser.chaptered(text))

    def test_only_one_chapter_marker(self):
        text = "Some text\ni\nno second marker"
        self.assertFalse(parser.chaptered(text))

    def test_no_chapters(self):
        text = "Just some plain text\nwith no chapters"
        self.assertFalse(parser.chaptered(text))

    def test_part_i_and_part_ii(self):
        text = "Part I\nsome content\nPart II\nmore"
        self.assertTrue(parser.chaptered(text))


class TestHowManyTitles(unittest.TestCase):
    """Tests for parser.how_many_titles."""

    def test_no_title(self):
        text = "Some paragraph.\n\nAnother paragraph."
        self.assertEqual(parser.how_many_titles(text, "The Bell"), 0)

    def test_one_title(self):
        text = "Some paragraph.\n\nThe Bell\n\nAnother paragraph."
        self.assertEqual(parser.how_many_titles(text, "The Bell"), 1)

    def test_two_titles(self):
        text = "The Bell\n\nSome text.\n\nThe Bell\n\nMore text."
        self.assertEqual(parser.how_many_titles(text, "The Bell"), 2)


class TestTitleInBody(unittest.TestCase):
    """Tests for parser.title_in_body."""

    def test_title_found(self):
        text = "Some text\nTHE BELL\nMore text"
        result = parser.title_in_body(text, frozenset(["The Bell"]))
        self.assertGreater(result, 0)

    def test_title_not_found(self):
        text = "Some text without the title\nMore text"
        result = parser.title_in_body(text, frozenset(["The Bell"]))
        self.assertEqual(result, -1)


class TestIntrusiveParagraph(unittest.TestCase):
    """Tests for parser.intrusive_paragraph."""

    def test_empty_paragraph(self):
        self.assertFalse(parser.intrusive_paragraph(""))

    def test_blank_lines_only(self):
        # Blank-only lines are skipped; result stays True
        self.assertTrue(parser.intrusive_paragraph("\n\n"))

    def test_normal_prose(self):
        self.assertFalse(parser.intrusive_paragraph("This is a normal paragraph."))

    def test_indented_non_space(self):
        """Lines with 4 spaces then non-space trigger continue, result stays True."""
        paragraph = "    regular indented text"
        self.assertTrue(parser.intrusive_paragraph(paragraph))

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
        self.assertTrue(parser.line_contains_title("The Bell", "The Bell"))

    def test_with_underscore_wrapping(self):
        self.assertTrue(parser.line_contains_title("_the bell_", "The Bell"))

    def test_with_trailing_period(self):
        self.assertTrue(parser.line_contains_title("The Bell.", "The Bell"))

    def test_too_different_length(self):
        self.assertFalse(
            parser.line_contains_title("The Bell is ringing loudly", "The Bell")
        )

    def test_no_match(self):
        self.assertFalse(parser.line_contains_title("Some other line", "The Bell"))

    def test_fuzzy_match(self):
        self.assertTrue(parser.line_contains_title("The Bell!", "The Bell"))

    def test_title_starts_with_the(self):
        """Lines without 'the' can match titles that start with 'the '."""
        self.assertTrue(parser.line_contains_title("Bell", "the Bell"))

    def test_multiline_rn(self):
        """Lines with rn\\n in the middle are joined before matching."""
        line = "The Bellrn\nsome text"
        self.assertTrue(parser.line_contains_title(line, "the bell some text"))

    def test_multiline_newline(self):
        """Lines with \\n (not rn\\n) are joined."""
        line = "The\nBell"
        self.assertTrue(parser.line_contains_title(line, "The Bell"))


class TestNamesMatch(unittest.TestCase):
    """Tests for parser.names_match."""

    def test_exact_match(self):
        self.assertTrue(parser.names_match("smith john", "smith john"))

    def test_reverse_order(self):
        self.assertTrue(parser.names_match("John Smith", "Smith, John"))

    def test_no_match(self):
        self.assertFalse(parser.names_match("John Smith", "Jane Doe"))

    def test_partial_match_single_word(self):
        """Single-word name2 matches if that word is found in name1."""
        self.assertTrue(parser.names_match("John Smith", "John"))

    def test_three_word_name_two_match(self):
        """With 3+ word name2, >=2 matches returns True."""
        self.assertTrue(parser.names_match("John Edward Smith", "John Edward Smith"))


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


class TestLineContainsAuthor2(unittest.TestCase):
    """Tests for parser.line_contains_author2."""

    def test_name_match(self):
        self.assertTrue(parser.line_contains_author2("John Smith", ["Smith, John"]))

    def test_by_line(self):
        self.assertTrue(parser.line_contains_author2("by John", ["Smith, John"]))

    def test_by_alone(self):
        self.assertTrue(parser.line_contains_author2("by", ["Smith, John"]))

    def test_no_match(self):
        self.assertFalse(parser.line_contains_author2("Jane Doe", ["Smith, John"]))

    def test_by_too_long(self):
        """A 'by' line that is too long returns False."""
        long_line = "by " + " ".join(["word"] * 10)
        self.assertFalse(parser.line_contains_author2(long_line, ["Smith, John"]))


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
        self.assertFalse(parser.in_body("The Bell", "The Bell", ["Smith, John"], []))

    def test_author_line_not_in_body(self):
        self.assertFalse(parser.in_body("John Smith", "The Bell", ["Smith, John"], []))

    def test_blank_line_not_in_body(self):
        self.assertFalse(parser.in_body("", "The Bell", ["Smith, John"], []))

    def test_illustration_line_not_in_body(self):
        self.assertFalse(
            parser.in_body("Illustration: A drawing", "The Bell", ["Smith, John"], [])
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
        result = parser.fix_body(text, ["Smith, John"], [])
        self.assertNotIn("Transcriber", result)
        self.assertIn("Actual story begins here.", result)

    def test_removes_illustration_from_start(self):
        text = "Illustration: A drawing\n\nActual story begins here."
        result = parser.fix_body(text, ["Smith, John"], [])
        self.assertNotIn("Illustration", result)
        self.assertIn("Actual story begins here.", result)

    def test_removes_etext_produced_from_start(self):
        text = "This etext was produced by volunteers\n\nActual story begins here."
        result = parser.fix_body(text, ["Smith, John"], [])
        self.assertNotIn("This etext was produced", result)
        self.assertIn("Actual story begins here.", result)

    def test_removes_author_from_start(self):
        text = "John Smith\n\nActual story begins here."
        result = parser.fix_body(text, ["Smith, John"], [])
        self.assertNotIn("John Smith", result)
        self.assertIn("Actual story begins here.", result)

    def test_preserves_normal_body(self):
        text = "First paragraph.\n\nSecond paragraph."
        result = parser.fix_body(text, ["Smith, John"], [])
        self.assertIn("First paragraph.", result)
        self.assertIn("Second paragraph.", result)

    def test_does_not_remove_transcriber_after_first_paragraph(self):
        text = "First paragraph.\n\nTranscriber's note: late note"
        result = parser.fix_body(text, ["Smith, John"], [])
        self.assertIn("Transcriber", result)


class TestBodyOfText(unittest.TestCase):
    """Tests for parser.body_of_text."""

    def _make_story(self, title, author_line, body):
        return f"{title}\n\n{author_line}\n\n{body}"

    def test_extracts_body_after_title_and_author(self):
        text = self._make_story("The Bell", "John Smith", "Once upon a time.")
        result = parser.body_of_text(text, ["Smith, John"], [], "The Bell")
        self.assertIn("Once upon a time.", result)

    def test_body_excludes_title(self):
        text = self._make_story("The Bell", "John Smith", "Once upon a time.")
        result = parser.body_of_text(text, ["Smith, John"], [], "The Bell")
        self.assertNotIn("The Bell\n\nJohn Smith", result)

    def test_debug_flag_does_not_raise(self):
        """debug=True should not raise errors."""
        text = self._make_story("The Bell", "John Smith", "Once upon a time.")
        try:
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
        """A line with high similarity to the title triggers the fuzzy-match branch when no exact match exists."""
        # "The Bel" vs "The Bell": no exact match variant fires,
        # but SequenceMatcher ratio ~0.93 > 0.90 so the fuzzy branch returns True.
        self.assertTrue(parser.line_contains_title("The Bel", "The Bell"))

    def test_no_match_returns_false_for_non_the_title(self):
        """A line with no similarity and title not starting with 'the ' returns False."""
        # len diff = 3 (<=5), no exact match, low fuzzy ratio, title[:4] != "the "
        self.assertFalse(parser.line_contains_title("abcde", "my story"))


class TestLineContainsAuthorAdditional(unittest.TestCase):
    """Additional tests for line_contains_author covering single-name and long-by-line cases."""

    def test_single_name_no_comma(self):
        """Author with a single name (no comma) sets first_name to empty string."""
        self.assertTrue(parser.line_contains_author("Mark", ["Mark"], []))

    def test_by_line_over_limit_containing_names_returns_true(self):
        """A 'by' line with >=limit words that still contains author names returns True."""
        # 9 words: the length check fails (len >= 8), but names are present, exercising lines 422-424.
        line = "by john smith the author of this story today"
        self.assertTrue(parser.line_contains_author(line, ["Smith, John"], []))


class TestNamesMatchAdditional(unittest.TestCase):
    """Additional tests for names_match covering partial three-word name matching."""

    def test_three_word_name_two_match_returns_true(self):
        """A 3+ word name2 with exactly 2 matching words still returns True."""
        # name2 split = ["john", "edward", "smith"]; "edward" not in name1
        self.assertTrue(parser.names_match("John Smith", "John Edward Smith"))


class TestFixBodyAdditional(unittest.TestCase):
    """Additional tests for fix_body covering the intrusive-paragraph branch."""

    def test_removes_intrusive_paragraph_at_start(self):
        """An intrusive paragraph (4-space-indented non-quoted lines) at the start is skipped."""
        text = "    X\n\nActual story begins here."
        result = parser.fix_body(text, ["Smith, John"], [])
        self.assertNotIn("    X", result)
        self.assertIn("Actual story begins here.", result)


class TestBodyOfTextAdditional(unittest.TestCase):
    """Additional tests for body_of_text covering the remaining break/continue branches."""

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
        """Body content after title but with no author present triggers the elif break (line 626)."""
        text = "The Bell\n\nThis is the body."
        result = parser.body_of_text(text, [], [], "The Bell")
        self.assertIn("This is the body.", result)

    def test_preface_before_title_is_skipped_via_else_continue(self):
        """Text before the title (not blank, not title/author) is skipped via else:continue (line 628)."""
        text = "Preface text\n\nThe Bell\n\nJohn Smith\n\nThis is the body."
        result = parser.body_of_text(text, ["Smith, John"], [], "The Bell")
        self.assertIn("This is the body.", result)
        self.assertNotIn("Preface text", result)


def _make_metadata_side_effect(subject, language, title, author, alias):
    """Return a side_effect function for api.get_metadata that returns metadata by key."""

    def side_effect(key, story_id):
        return {
            "subject": subject,
            "language": language,
            "title": title,
            "author": author,
            "alias": alias,
        }[key]

    return side_effect


class TestGatherStory(unittest.TestCase):
    """Tests for parser.gather_story using a mocked API and gatherer."""

    def test_empty_subject_returns_early(self):
        """An empty subject causes gather_story to return early with an error."""
        gatherer = mock.MagicMock()
        with mock.patch(
            "lcats.gatherers.parser.api.get_metadata", return_value=[]
        ):
            result = parser.gather_story(gatherer, 42)
        self.assertEqual(result[0], 42)
        self.assertIsNone(result[1])
        self.assertIn("No data", result[2])

    def test_bad_metadata_returns_early(self):
        """Non-OK metadata causes gather_story to return early."""
        gatherer = mock.MagicMock()
        side_effect = _make_metadata_side_effect(
            subject=["PQ", "poetry"],
            language=["en"],
            title=frozenset(["The Bell"]),
            author=frozenset(["Smith, John"]),
            alias=frozenset([]),
        )
        with mock.patch(
            "lcats.gatherers.parser.api.get_metadata", side_effect=side_effect
        ):
            result = parser.gather_story(gatherer, 42)
        self.assertEqual(result[0], 42)
        self.assertIsNone(result[1])
        self.assertIn("Metadata not suitable", result[2])

    def test_failed_etext_load_returns_early(self):
        """A failure to load the etext causes gather_story to return early."""
        gatherer = mock.MagicMock()
        side_effect = _make_metadata_side_effect(
            subject=["PS", "Short stories"],
            language=["en"],
            title=frozenset(["The Bell"]),
            author=frozenset(["Smith, John"]),
            alias=frozenset([]),
        )
        with mock.patch(
            "lcats.gatherers.parser.api.get_metadata", side_effect=side_effect
        ):
            with mock.patch(
                "lcats.gatherers.parser.api.load_etext",
                side_effect=Exception("network error"),
            ):
                result = parser.gather_story(gatherer, 42)
        self.assertIn("Failed to retrieve", result[2])

    def test_chaptered_text_returns_early(self):
        """A text with chapters causes gather_story to return early."""
        gatherer = mock.MagicMock()
        side_effect = _make_metadata_side_effect(
            subject=["PS", "Short stories"],
            language=["en"],
            title=frozenset(["The Bell"]),
            author=frozenset(["Smith, John"]),
            alias=frozenset([]),
        )
        chaptered_bytes = b"Chapter I\nsome content\nChapter II\nmore content"
        with mock.patch(
            "lcats.gatherers.parser.api.get_metadata", side_effect=side_effect
        ):
            with mock.patch(
                "lcats.gatherers.parser.api.load_etext", return_value=chaptered_bytes
            ):
                with mock.patch(
                    "lcats.gatherers.parser.headers.strip_headers",
                    side_effect=lambda x: x,
                ):
                    result = parser.gather_story(gatherer, 42)
        self.assertIn("chapters", result[2])

    def test_short_story_returns_early(self):
        """A story whose body is too short causes gather_story to return early."""
        gatherer = mock.MagicMock()
        side_effect = _make_metadata_side_effect(
            subject=["PS", "Short stories"],
            language=["en"],
            title=frozenset(["The Bell"]),
            author=frozenset(["Smith, John"]),
            alias=frozenset([]),
        )
        short_text = b"The Bell\n\nJohn Smith\n\nA short story."
        with mock.patch(
            "lcats.gatherers.parser.api.get_metadata", side_effect=side_effect
        ):
            with mock.patch(
                "lcats.gatherers.parser.api.load_etext", return_value=short_text
            ):
                with mock.patch(
                    "lcats.gatherers.parser.headers.strip_headers",
                    side_effect=lambda x: x,
                ):
                    result = parser.gather_story(gatherer, 42)
        self.assertIn("too short", result[2])

    def test_happy_path_saves_story(self):
        """A valid story is saved and the function returns the story ID and path."""
        gatherer = mock.MagicMock()
        side_effect = _make_metadata_side_effect(
            subject=["PS", "Short stories"],
            language=["en"],
            title=frozenset(["The Bell"]),
            author=frozenset(["Smith, John"]),
            alias=frozenset([]),
        )
        body_paragraphs = "\n\n".join(
            ["Paragraph {}.".format(i) for i in range(15)]
        )
        story_text = "The Bell\n\nJohn Smith\n\n{}".format(body_paragraphs)
        etext = story_text.encode("utf-8")
        with mock.patch(
            "lcats.gatherers.parser.api.get_metadata", side_effect=side_effect
        ):
            with mock.patch(
                "lcats.gatherers.parser.api.load_etext", return_value=etext
            ):
                with mock.patch(
                    "lcats.gatherers.parser.headers.strip_headers",
                    side_effect=lambda x: x,
                ):
                    with mock.patch("builtins.open", mock.mock_open()):
                        result = parser.gather_story(gatherer, 42)
        self.assertEqual(result[0], 42)
        self.assertIsNone(result[2])
        self.assertIsNotNone(result[1])


class TestTestStories(unittest.TestCase):
    """Tests for parser.test_stories."""

    def test_calls_test_story_get_for_each_story(self):
        """test_stories calls test_story_get for each story ID."""
        with mock.patch(
            "lcats.gatherers.parser.test_story_get"
        ) as mock_get:
            parser.test_stories([1, 2, 3])
        self.assertEqual(mock_get.call_count, 3)


class TestShowDataFunctions(unittest.TestCase):
    """Tests for parser.show_data_not_corpora and parser.show_corpora_not_data."""

    def test_show_data_not_corpora_handles_missing_file(self):
        """show_data_not_corpora handles a missing CSV file without raising."""
        try:
            parser.show_data_not_corpora()
        except Exception as e:
            self.fail(
                "show_data_not_corpora raised an unexpected exception: {}".format(e)
            )

    def test_show_corpora_not_data_handles_missing_file(self):
        """show_corpora_not_data handles a missing CSV file without raising."""
        try:
            parser.show_corpora_not_data()
        except Exception as e:
            self.fail(
                "show_corpora_not_data raised an unexpected exception: {}".format(e)
            )

    def test_show_data_not_corpora_reads_matching_rows(self):
        """show_data_not_corpora processes rows with data=False and corpora=False."""
        rows = [["a/b/c/d/e/42", "x", "y", "False", "a", "b", "c", "False"]]
        with mock.patch("builtins.open", mock.mock_open()):
            with mock.patch(
                "lcats.gatherers.parser.csv.reader", return_value=iter(rows)
            ):
                with mock.patch(
                    "lcats.gatherers.parser.api.get_metadata",
                    return_value=frozenset(["something"]),
                ):
                    parser.show_data_not_corpora()

    def test_show_data_not_corpora_handles_generic_exception(self):
        """show_data_not_corpora handles a generic exception without raising."""
        with mock.patch("builtins.open", side_effect=PermissionError("denied")):
            try:
                parser.show_data_not_corpora()
            except Exception as e:
                self.fail(
                    "show_data_not_corpora raised an unexpected exception: {}".format(e)
                )

    def test_show_corpora_not_data_reads_matching_rows(self):
        """show_corpora_not_data processes rows with data=False and corpora=True."""
        rows = [["a/b/c/d/e/42", "x", "y", "False", "a", "b", "c", "True"]]
        with mock.patch("builtins.open", mock.mock_open()):
            with mock.patch(
                "lcats.gatherers.parser.csv.reader", return_value=iter(rows)
            ):
                with mock.patch(
                    "lcats.gatherers.parser.api.get_metadata",
                    return_value=frozenset(["something"]),
                ):
                    parser.show_corpora_not_data()

    def test_show_corpora_not_data_handles_generic_exception(self):
        """show_corpora_not_data handles a generic exception without raising."""
        with mock.patch("builtins.open", side_effect=PermissionError("denied")):
            try:
                parser.show_corpora_not_data()
            except Exception as e:
                self.fail(
                    "show_corpora_not_data raised an unexpected exception: {}".format(e)
                )


class TestTestStoryGet(unittest.TestCase):
    """Tests for parser.test_story_get using a mocked API."""

    def test_chaptered_text_returns_early(self):
        """test_story_get returns early when text has chapters."""
        side_effect = _make_metadata_side_effect(
            subject=["PS", "Short stories"],
            language=["en"],
            title=frozenset(["The Bell"]),
            author=frozenset(["Smith, John"]),
            alias=frozenset([]),
        )
        chaptered_bytes = b"Chapter I\nsome content\nChapter II\nmore content"
        with mock.patch(
            "lcats.gatherers.parser.api.get_metadata", side_effect=side_effect
        ):
            with mock.patch(
                "lcats.gatherers.parser.api.load_etext", return_value=chaptered_bytes
            ):
                with mock.patch(
                    "lcats.gatherers.parser.headers.strip_headers",
                    side_effect=lambda x: x,
                ):
                    result = parser.test_story_get(42)
        self.assertIn("chapters", result[2])

    def test_short_body_returns_early(self):
        """test_story_get returns early when body is too short."""
        side_effect = _make_metadata_side_effect(
            subject=["PS", "Short stories"],
            language=["en"],
            title=frozenset(["The Bell"]),
            author=frozenset(["Smith, John"]),
            alias=frozenset([]),
        )
        short_bytes = b"The Bell\n\nJohn Smith\n\nA"
        with mock.patch(
            "lcats.gatherers.parser.api.get_metadata", side_effect=side_effect
        ):
            with mock.patch(
                "lcats.gatherers.parser.api.load_etext", return_value=short_bytes
            ):
                with mock.patch(
                    "lcats.gatherers.parser.headers.strip_headers",
                    side_effect=lambda x: x,
                ):
                    result = parser.test_story_get(42)
        self.assertIn("too short", result[2])

    def test_returns_body_for_valid_story(self):
        """test_story_get returns the body text for a valid non-chaptered story."""
        side_effect = _make_metadata_side_effect(
            subject=["PS", "Short stories"],
            language=["en"],
            title=frozenset(["The Bell"]),
            author=frozenset(["Smith, John"]),
            alias=frozenset([]),
        )
        story_text = b"The Bell\n\nJohn Smith\n\nOnce upon a time there was a story."
        with mock.patch(
            "lcats.gatherers.parser.api.get_metadata", side_effect=side_effect
        ):
            with mock.patch(
                "lcats.gatherers.parser.api.load_etext", return_value=story_text
            ):
                with mock.patch(
                    "lcats.gatherers.parser.headers.strip_headers",
                    side_effect=lambda x: x,
                ):
                    with mock.patch(
                        "lcats.gatherers.parser.names.title_and_author_to_filename",
                        return_value="the_bell__smith.json",
                    ):
                        result = parser.test_story_get(42)
        self.assertIn("Once upon a time", result)


class TestGrabStory(unittest.TestCase):
    """Tests for parser.grab_story."""

    def test_returns_decoded_text(self):
        """grab_story returns the decoded text of the story."""
        etext = b"Some story text"
        with mock.patch(
            "lcats.gatherers.parser.api.load_etext", return_value=etext
        ):
            with mock.patch(
                "lcats.gatherers.parser.headers.strip_headers",
                side_effect=lambda x: x,
            ):
                result = parser.grab_story(42)
        self.assertIn("Some story text", result)


if __name__ == "__main__":
    unittest.main()
