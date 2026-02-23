"""Unit tests for lcats.analysis.story_analysis."""

import unittest
import unittest.mock
from unittest.mock import MagicMock

from parameterized import parameterized

from lcats.analysis import story_analysis


# ---------------------------------------------------------------------------
# Tests: get_keywords
# ---------------------------------------------------------------------------


class TestGetKeywords(unittest.TestCase):
    """Tests for get_keywords."""

    def test_empty_string_returns_empty(self):
        self.assertEqual(story_analysis.get_keywords(""), [])

    def test_single_short_word_excluded(self):
        # "it" is 2 chars and also a stopword
        self.assertEqual(story_analysis.get_keywords("it"), [])

    def test_stopwords_excluded(self):
        result = story_analysis.get_keywords("the and are is")
        self.assertEqual(result, [])

    def test_content_word_included(self):
        result = story_analysis.get_keywords("dragon")
        self.assertIn("dragon", result)

    def test_numbers_excluded(self):
        # digits are non-alpha so split out and produce empty tokens
        result = story_analysis.get_keywords("123 456")
        self.assertEqual(result, [])

    def test_uppercase_lowercased(self):
        result = story_analysis.get_keywords("Dragon")
        self.assertIn("dragon", result)

    def test_mixed_text(self):
        result = story_analysis.get_keywords("The brave knight slew the dragon")
        self.assertIn("brave", result)
        self.assertIn("knight", result)
        self.assertIn("slew", result)
        self.assertIn("dragon", result)
        self.assertNotIn("the", result)

    def test_short_words_excluded(self):
        # words with < 3 chars (non-stopword) also excluded
        result = story_analysis.get_keywords("ab xy zz")
        self.assertEqual(result, [])

    def test_punctuation_splits(self):
        result = story_analysis.get_keywords("hello,world")
        self.assertIn("hello", result)
        self.assertIn("world", result)

    def test_three_char_minimum_inclusive(self):
        # "cat" is exactly 3 chars, not a stopword
        result = story_analysis.get_keywords("cat")
        self.assertIn("cat", result)


# ---------------------------------------------------------------------------
# Tests: top_keywords
# ---------------------------------------------------------------------------


class TestTopKeywords(unittest.TestCase):
    """Tests for top_keywords."""

    def test_empty_tokens_returns_empty(self):
        self.assertEqual(story_analysis.top_keywords([]), [])

    def test_single_token(self):
        result = story_analysis.top_keywords(["dragon"])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["term"], "dragon")
        self.assertEqual(result[0]["count"], 1)

    def test_top_k_limits_results(self):
        tokens = ["a", "b", "c", "d", "e", "f"]
        result = story_analysis.top_keywords(tokens, k=3)
        self.assertEqual(len(result), 3)

    def test_frequency_ordering(self):
        tokens = ["cat", "dog", "cat", "cat", "dog"]
        result = story_analysis.top_keywords(tokens, k=2)
        self.assertEqual(result[0]["term"], "cat")
        self.assertEqual(result[0]["count"], 3)
        self.assertEqual(result[1]["term"], "dog")
        self.assertEqual(result[1]["count"], 2)

    def test_tie_broken_alphabetically(self):
        tokens = ["zebra", "apple", "mango"]
        result = story_analysis.top_keywords(tokens, k=3)
        terms = [r["term"] for r in result]
        self.assertEqual(terms, sorted(terms))

    def test_default_k_is_five(self):
        tokens = ["a", "b", "c", "d", "e", "f", "g"]
        result = story_analysis.top_keywords(tokens)
        self.assertEqual(len(result), 5)

    def test_result_items_have_term_and_count(self):
        result = story_analysis.top_keywords(["word", "word"])
        self.assertIn("term", result[0])
        self.assertIn("count", result[0])

    def test_fewer_tokens_than_k(self):
        result = story_analysis.top_keywords(["only"], k=10)
        self.assertEqual(len(result), 1)


# ---------------------------------------------------------------------------
# Tests: coerce_text
# ---------------------------------------------------------------------------


class TestCoerceText(unittest.TestCase):
    """Tests for coerce_text."""

    def test_plain_string_returned_unchanged(self):
        self.assertEqual(story_analysis.coerce_text("hello"), "hello")

    def test_bytes_decoded_to_string(self):
        result = story_analysis.coerce_text(b"hello")
        self.assertEqual(result, "hello")

    def test_bytearray_decoded_to_string(self):
        result = story_analysis.coerce_text(bytearray(b"world"))
        self.assertEqual(result, "world")

    def test_bytes_literal_string_decoded(self):
        # "b'hello'" as a Python bytes literal string
        result = story_analysis.coerce_text("b'hello'")
        self.assertEqual(result, "hello")

    def test_double_quote_bytes_literal_decoded(self):
        result = story_analysis.coerce_text('b"hello"')
        self.assertEqual(result, "hello")

    def test_invalid_bytes_literal_returned_as_is(self):
        # Not a valid bytes literal - returned unchanged
        result = story_analysis.coerce_text("b'not closed")
        self.assertEqual(result, "b'not closed")

    def test_non_string_non_bytes_converted_via_str(self):
        result = story_analysis.coerce_text(42)
        self.assertEqual(result, "42")

    def test_none_converted_via_str(self):
        result = story_analysis.coerce_text(None)
        self.assertEqual(result, "None")

    def test_bytes_with_replacement_on_bad_utf8(self):
        bad = bytes([0xFF, 0xFE])
        result = story_analysis.coerce_text(bad)
        self.assertIsInstance(result, str)

    def test_empty_string_returned_unchanged(self):
        self.assertEqual(story_analysis.coerce_text(""), "")

    def test_short_b_string_not_a_literal(self):
        # "b" alone is too short to be a bytes literal (len < 3)
        result = story_analysis.coerce_text("b")
        self.assertEqual(result, "b")


# ---------------------------------------------------------------------------
# Tests: extract_authors
# ---------------------------------------------------------------------------


class TestExtractAuthors(unittest.TestCase):
    """Tests for extract_authors."""

    def test_list_of_strings(self):
        result = story_analysis.extract_authors(["Alice", "Bob"])
        self.assertEqual(result, ["Alice", "Bob"])

    def test_single_string(self):
        result = story_analysis.extract_authors("Alice")
        self.assertEqual(result, ["Alice"])

    def test_empty_string_returns_empty(self):
        result = story_analysis.extract_authors("")
        self.assertEqual(result, [])

    def test_none_returns_empty(self):
        result = story_analysis.extract_authors(None)
        self.assertEqual(result, [])

    def test_list_with_empty_strings_filtered(self):
        result = story_analysis.extract_authors(["Alice", "", "  "])
        self.assertEqual(result, ["Alice"])

    def test_list_with_whitespace_stripped(self):
        result = story_analysis.extract_authors(["  Alice  "])
        self.assertEqual(result, ["Alice"])

    def test_list_with_non_strings(self):
        result = story_analysis.extract_authors([123, "Bob"])
        self.assertIn("Bob", result)

    def test_whitespace_only_string_returns_empty(self):
        result = story_analysis.extract_authors("   ")
        self.assertEqual(result, [])

    def test_list_value_returned_as_list(self):
        result = story_analysis.extract_authors(["One Author"])
        self.assertIsInstance(result, list)


# ---------------------------------------------------------------------------
# Tests: word_count
# ---------------------------------------------------------------------------


class TestWordCount(unittest.TestCase):
    """Tests for word_count."""

    def test_empty_string_returns_zero(self):
        self.assertEqual(story_analysis.word_count(""), 0)

    def test_single_word(self):
        self.assertEqual(story_analysis.word_count("hello"), 1)

    def test_multiple_words(self):
        self.assertEqual(story_analysis.word_count("hello world"), 2)

    def test_extra_whitespace(self):
        self.assertEqual(story_analysis.word_count("  hello   world  "), 2)

    def test_newlines_as_separators(self):
        self.assertEqual(story_analysis.word_count("hello\nworld"), 2)

    def test_tabs_as_separators(self):
        self.assertEqual(story_analysis.word_count("hello\tworld"), 2)

    def test_punctuation_not_split(self):
        # punctuation attached to word counts as one token
        self.assertEqual(story_analysis.word_count("hello,world"), 1)

    def test_sentence(self):
        self.assertEqual(story_analysis.word_count("The quick brown fox"), 4)


# ---------------------------------------------------------------------------
# Tests: token_count / get_encoder
# ---------------------------------------------------------------------------


def _make_mock_encoder(words_as_tokens=True):
    """Return a mock encoder that tokenizes by splitting on whitespace."""
    enc = MagicMock()
    enc.encode.side_effect = lambda text, **kw: text.split()
    return enc


class TestTokenCount(unittest.TestCase):
    """Tests for token_count."""

    def test_empty_string_returns_zero(self):
        enc = _make_mock_encoder()
        self.assertEqual(story_analysis.token_count("", enc=enc), 0)

    def test_nonempty_string_returns_positive(self):
        enc = _make_mock_encoder()
        result = story_analysis.token_count("hello world", enc=enc)
        self.assertGreater(result, 0)

    def test_longer_text_more_tokens(self):
        enc = _make_mock_encoder()
        short = story_analysis.token_count("hello", enc=enc)
        long = story_analysis.token_count("hello world foo bar baz", enc=enc)
        self.assertGreater(long, short)

    def test_uses_provided_encoder(self):
        enc = _make_mock_encoder()
        result = story_analysis.token_count("test text", enc=enc)
        enc.encode.assert_called_once_with("test text", disallowed_special=())
        self.assertIsInstance(result, int)

    def test_uses_default_encoder_when_none(self):
        mock_enc = _make_mock_encoder()
        with unittest.mock.patch(
            "lcats.analysis.story_analysis.get_encoder", return_value=mock_enc
        ):
            result = story_analysis.token_count("some text", enc=None)
        self.assertIsInstance(result, int)
        self.assertGreater(result, 0)

    def test_returns_integer(self):
        enc = _make_mock_encoder()
        result = story_analysis.token_count("one two three", enc=enc)
        self.assertIsInstance(result, int)


class TestGetEncoder(unittest.TestCase):
    """Tests for get_encoder (mocked to avoid network calls)."""

    def test_returns_result_of_tiktoken_get_encoding(self):
        mock_enc = MagicMock()
        import tiktoken

        with unittest.mock.patch.object(
            tiktoken, "get_encoding", return_value=mock_enc
        ):
            enc = story_analysis.get_encoder()
        self.assertIs(enc, mock_enc)

    def test_fallback_to_cl100k_base_when_o200k_fails(self):
        mock_enc = MagicMock()
        import tiktoken

        call_count = [0]

        def side_effect(name):
            call_count[0] += 1
            if name == "o200k_base":
                raise ValueError("not found")
            return mock_enc

        with unittest.mock.patch.object(tiktoken, "get_encoding", side_effect=side_effect):
            enc = story_analysis.get_encoder()
        self.assertIs(enc, mock_enc)

    def test_raises_runtime_error_when_all_encodings_fail(self):
        import tiktoken

        with unittest.mock.patch.object(
            tiktoken, "get_encoding", side_effect=ValueError("not found")
        ):
            with unittest.mock.patch.object(
                tiktoken, "encoding_for_model", side_effect=ValueError("not found")
            ):
                with self.assertRaises(RuntimeError):
                    story_analysis.get_encoder()


# ---------------------------------------------------------------------------
# Tests: count_paragraph
# ---------------------------------------------------------------------------


class TestCountParagraph(unittest.TestCase):
    """Tests for count_paragraph."""

    def test_empty_string_returns_zero(self):
        self.assertEqual(story_analysis.count_paragraph(""), 0)

    def test_whitespace_only_returns_zero(self):
        self.assertEqual(story_analysis.count_paragraph("   \n  \n  "), 0)

    def test_single_paragraph(self):
        self.assertEqual(story_analysis.count_paragraph("Hello world."), 1)

    def test_single_blank_line_not_a_separator(self):
        text = "para one\n\npara two"
        # single blank line → NOT a paragraph break per the function rules
        self.assertEqual(story_analysis.count_paragraph(text), 1)

    def test_two_consecutive_blank_lines_splits_paragraphs(self):
        text = "para one\n\n\npara two"
        self.assertEqual(story_analysis.count_paragraph(text), 2)

    def test_three_consecutive_blank_lines_splits_paragraphs(self):
        text = "para one\n\n\n\npara two"
        self.assertEqual(story_analysis.count_paragraph(text), 2)

    def test_non_string_coerced(self):
        result = story_analysis.count_paragraph(42)
        self.assertIsInstance(result, int)

    def test_crlf_normalized(self):
        text = "para one\r\n\r\n\r\npara two"
        self.assertEqual(story_analysis.count_paragraph(text), 2)

    def test_cr_only_normalized(self):
        text = "para one\r\r\rpara two"
        self.assertEqual(story_analysis.count_paragraph(text), 2)

    def test_multiple_paragraphs(self):
        text = "para one\n\n\npara two\n\n\npara three"
        self.assertEqual(story_analysis.count_paragraph(text), 3)

    def test_leading_trailing_blank_lines_ignored(self):
        text = "\n\n\npara one\n\n\n"
        self.assertEqual(story_analysis.count_paragraph(text), 1)


# ---------------------------------------------------------------------------
# Tests: normalize_title
# ---------------------------------------------------------------------------


class TestNormalizeTitle(unittest.TestCase):
    """Tests for normalize_title."""

    def test_already_normalized(self):
        self.assertEqual(story_analysis.normalize_title("hello world"), "hello world")

    def test_uppercase_lowercased(self):
        self.assertEqual(story_analysis.normalize_title("Hello World"), "hello world")

    def test_multiple_spaces_collapsed(self):
        self.assertEqual(story_analysis.normalize_title("hello   world"), "hello world")

    def test_leading_trailing_whitespace_stripped(self):
        self.assertEqual(story_analysis.normalize_title("  hello  "), "hello")

    def test_newline_collapsed(self):
        self.assertEqual(story_analysis.normalize_title("hello\nworld"), "hello world")

    def test_tab_collapsed(self):
        self.assertEqual(story_analysis.normalize_title("hello\tworld"), "hello world")

    def test_empty_string(self):
        self.assertEqual(story_analysis.normalize_title(""), "")


# ---------------------------------------------------------------------------
# Tests: decode_possible_bytes_literal
# ---------------------------------------------------------------------------


class TestDecodePossibleBytesLiteral(unittest.TestCase):
    """Tests for decode_possible_bytes_literal."""

    def test_plain_string_returned_unchanged(self):
        self.assertEqual(story_analysis.decode_possible_bytes_literal("hello"), "hello")

    def test_bytes_literal_single_quote_decoded(self):
        result = story_analysis.decode_possible_bytes_literal("b'hello'")
        self.assertEqual(result, "hello")

    def test_bytes_literal_double_quote_decoded(self):
        result = story_analysis.decode_possible_bytes_literal('b"world"')
        self.assertEqual(result, "world")

    def test_non_string_coerced_to_string(self):
        result = story_analysis.decode_possible_bytes_literal(99)
        self.assertEqual(result, "99")

    def test_short_string_returned_unchanged(self):
        result = story_analysis.decode_possible_bytes_literal("b")
        self.assertEqual(result, "b")

    def test_invalid_bytes_literal_returned_as_is(self):
        # Looks like a bytes literal but is invalid
        result = story_analysis.decode_possible_bytes_literal("b'unclosed")
        self.assertEqual(result, "b'unclosed")

    def test_empty_string_returned_unchanged(self):
        result = story_analysis.decode_possible_bytes_literal("")
        self.assertEqual(result, "")

    def test_bytes_literal_with_escape_sequence(self):
        # b'\n' should decode to a newline character
        result = story_analysis.decode_possible_bytes_literal(r"b'\n'")
        self.assertEqual(result, "\n")

    def test_whitespace_stripped_before_check(self):
        # Leading/trailing whitespace stripped before literal check
        result = story_analysis.decode_possible_bytes_literal("  b'hi'  ")
        self.assertEqual(result, "hi")


# ---------------------------------------------------------------------------
# Tests: extract_title_authors_body
# ---------------------------------------------------------------------------


class TestExtractTitleAuthorsBody(unittest.TestCase):
    """Tests for extract_title_authors_body."""

    def test_basic_extraction(self):
        data = {"name": "My Story", "author": "Alice", "body": "Once upon a time."}
        title, authors, body = story_analysis.extract_title_authors_body(data)
        self.assertEqual(title, "My Story")
        self.assertEqual(authors, ["Alice"])
        self.assertEqual(body, "Once upon a time.")

    def test_missing_name_falls_back_to_untitled(self):
        data = {"body": "text"}
        title, _, _ = story_analysis.extract_title_authors_body(data)
        self.assertEqual(title, "<Untitled>")

    def test_name_from_metadata(self):
        data = {"metadata": {"name": "Meta Title"}, "body": "text"}
        title, _, _ = story_analysis.extract_title_authors_body(data)
        self.assertEqual(title, "Meta Title")

    def test_author_list(self):
        data = {"name": "T", "author": ["Alice", "Bob"], "body": ""}
        _, authors, _ = story_analysis.extract_title_authors_body(data)
        self.assertEqual(authors, ["Alice", "Bob"])

    def test_author_from_metadata(self):
        data = {"name": "T", "metadata": {"author": ["Carol"]}, "body": ""}
        _, authors, _ = story_analysis.extract_title_authors_body(data)
        self.assertEqual(authors, ["Carol"])

    def test_no_author_returns_empty_list(self):
        data = {"name": "T", "body": ""}
        _, authors, _ = story_analysis.extract_title_authors_body(data)
        self.assertEqual(authors, [])

    def test_body_bytes_decoded(self):
        data = {"name": "T", "body": b"hello bytes"}
        _, _, body = story_analysis.extract_title_authors_body(data)
        self.assertEqual(body, "hello bytes")

    def test_body_bytearray_decoded(self):
        data = {"name": "T", "body": bytearray(b"bytearray body")}
        _, _, body = story_analysis.extract_title_authors_body(data)
        self.assertEqual(body, "bytearray body")

    def test_body_bytes_literal_string_decoded(self):
        data = {"name": "T", "body": "b'literal'"}
        _, _, body = story_analysis.extract_title_authors_body(data)
        self.assertEqual(body, "literal")

    def test_missing_body_defaults_to_empty(self):
        data = {"name": "T"}
        _, _, body = story_analysis.extract_title_authors_body(data)
        self.assertEqual(body, "")

    def test_title_whitespace_stripped(self):
        data = {"name": "  Spaced  ", "body": ""}
        title, _, _ = story_analysis.extract_title_authors_body(data)
        self.assertEqual(title, "Spaced")

    def test_author_whitespace_stripped(self):
        data = {"name": "T", "author": ["  Alice  "], "body": ""}
        _, authors, _ = story_analysis.extract_title_authors_body(data)
        self.assertEqual(authors, ["Alice"])

    def test_empty_author_strings_filtered(self):
        data = {"name": "T", "author": ["", "  ", "Bob"], "body": ""}
        _, authors, _ = story_analysis.extract_title_authors_body(data)
        self.assertEqual(authors, ["Bob"])

    def test_returns_tuple_of_three(self):
        data = {"name": "T", "body": ""}
        result = story_analysis.extract_title_authors_body(data)
        self.assertEqual(len(result), 3)


# ---------------------------------------------------------------------------
# Tests: make_doc_classification_extractor
# ---------------------------------------------------------------------------


class TestMakeDocClassificationExtractor(unittest.TestCase):
    """Tests for make_doc_classification_extractor."""

    def test_returns_json_prompt_extractor(self):
        from lcats.analysis import llm_extractor

        client = MagicMock()
        extractor = story_analysis.make_doc_classification_extractor(client)
        self.assertIsInstance(extractor, llm_extractor.JSONPromptExtractor)

    def test_output_key_is_classification(self):
        client = MagicMock()
        extractor = story_analysis.make_doc_classification_extractor(client)
        self.assertEqual(extractor.output_key, "classification")

    def test_default_model_is_gpt4o(self):
        client = MagicMock()
        extractor = story_analysis.make_doc_classification_extractor(client)
        self.assertEqual(extractor.default_model, "gpt-4o")

    def test_text_indexer_is_none(self):
        client = MagicMock()
        extractor = story_analysis.make_doc_classification_extractor(client)
        self.assertIsNone(extractor.text_indexer)

    def test_result_aligner_is_none(self):
        client = MagicMock()
        extractor = story_analysis.make_doc_classification_extractor(client)
        self.assertIsNone(extractor.result_aligner)


# ---------------------------------------------------------------------------
# Tests: Prompt constants
# ---------------------------------------------------------------------------


class TestPromptConstants(unittest.TestCase):
    """Smoke tests for module-level prompt constants."""

    def test_doc_classify_system_prompt_nonempty(self):
        self.assertIsInstance(story_analysis.DOC_CLASSIFY_SYSTEM_PROMPT, str)
        self.assertGreater(len(story_analysis.DOC_CLASSIFY_SYSTEM_PROMPT), 0)

    def test_doc_classify_user_prompt_template_nonempty(self):
        self.assertIsInstance(story_analysis.DOC_CLASSIFY_USER_PROMPT_TEMPLATE, str)
        self.assertGreater(len(story_analysis.DOC_CLASSIFY_USER_PROMPT_TEMPLATE), 0)

    def test_user_prompt_template_contains_story_text_placeholder(self):
        self.assertIn("{story_text}", story_analysis.DOC_CLASSIFY_USER_PROMPT_TEMPLATE)


# ---------------------------------------------------------------------------
# Tests: _STOPWORDS constant
# ---------------------------------------------------------------------------


class TestStopwords(unittest.TestCase):
    """Tests for the _STOPWORDS module-level constant."""

    def test_is_frozenset(self):
        self.assertIsInstance(story_analysis._STOPWORDS, frozenset)

    def test_contains_common_words(self):
        for word in ("the", "and", "is", "a"):
            with self.subTest(word=word):
                self.assertIn(word, story_analysis._STOPWORDS)

    def test_does_not_contain_content_words(self):
        for word in ("dragon", "castle", "hero", "knight"):
            with self.subTest(word=word):
                self.assertNotIn(word, story_analysis._STOPWORDS)


if __name__ == "__main__":
    unittest.main()
