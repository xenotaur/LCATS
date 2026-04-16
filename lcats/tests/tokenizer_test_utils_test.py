"""Unit tests for shared tokenizer test helpers."""

import unittest

from lcats import chunking
from lcats.analysis import story_analysis
import tokenizer_test_utils


class TestFakeCharacterEncoding(unittest.TestCase):
    """Tests for FakeCharacterEncoding behavior."""

    def test_encode_decode_round_trip(self):
        encoder = tokenizer_test_utils.FakeCharacterEncoding()
        text = "Hello, 世界"
        self.assertEqual(encoder.decode(encoder.encode(text)), text)

    def test_encode_is_character_level(self):
        encoder = tokenizer_test_utils.FakeCharacterEncoding()
        self.assertEqual(len(encoder.encode("abc")), 3)


class TestTokenizerPatchHelpers(unittest.TestCase):
    """Tests for boundary patch helper utilities."""

    def test_patch_chunking_encoding_for_model(self):
        with tokenizer_test_utils.patch_chunking_encoding_for_model():
            self.assertEqual(chunking.count_tokens("hello"), 5)

    def test_patch_story_analysis_get_encoder(self):
        with tokenizer_test_utils.patch_story_analysis_get_encoder():
            self.assertEqual(story_analysis.token_count("hello"), 5)


if __name__ == "__main__":
    unittest.main()
