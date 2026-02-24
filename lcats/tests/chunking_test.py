import contextlib
import io
import unittest
import unittest.mock

from lcats import chunking


class FakeEncoding:
    """Character-level tokenizer for testing without network access.

    Each character maps to its Unicode code point, enabling lossless
    round-trip: decode(encode(text)) == text.
    """

    def encode(self, text):
        return [ord(ch) for ch in text]

    def decode(self, tokens):
        return "".join(chr(t) for t in tokens)


def _fake_encoding_for_model(model):
    return FakeEncoding()


class TestChunking(unittest.TestCase):

    def setUp(self):
        self.model = "gpt-3.5-turbo"
        self.text = (
            "Once upon a time, in a land far away, there was a kingdom ruled by a kind and wise "
            "queen. She had three children who were brave and clever, and they loved to explore "
            "the forests and mountains surrounding the castle. One day, they found a secret cave "
            "that glowed with mysterious light. Inside, they discovered an ancient map that led "
            "to a forgotten treasure..."
        )
        self.patcher = unittest.mock.patch(
            "lcats.chunking.tiktoken.encoding_for_model",
            side_effect=_fake_encoding_for_model,
        )
        self.patcher.start()
        self.token_count = chunking.count_tokens(self.text, model=self.model)

    def tearDown(self):
        self.patcher.stop()

    def test_token_count_matches(self):
        """Test token count of the unit test's story text is a positive integer."""
        self.assertTrue(isinstance(self.token_count, int))
        self.assertGreater(self.token_count, 0)

    def test_count_tokens_equals_char_length(self):
        """With character-level encoding, token count equals text length."""
        text = "Hello, world!"
        count = chunking.count_tokens(text, model=self.model)
        self.assertEqual(count, len(text))

    def test_chunk_story_no_overlap(self):
        """Test chunk_story without overlap returns at least one full chunk."""
        chunks = chunking.chunk_story(self.text, max_tokens=20, model_name=self.model)
        self.assertGreaterEqual(len(chunks), 1)
        for i, chunk in enumerate(chunks):
            self.assertIsInstance(chunk, chunking.Chunk)
            self.assertEqual(chunk.index, i)
            self.assertIsInstance(chunk.text, str)

    def test_chunk_story_with_overlap(self):
        """Test chunk_story with overlap includes shared tokens."""
        chunks = chunking.chunk_story(
            self.text, max_tokens=30, overlap_tokens=10, model_name=self.model
        )
        self.assertGreaterEqual(len(chunks), 2)
        self.assertTrue(chunks[1].start_token < chunks[1].start_token + 30)
        # Ensure overlap exists
        overlap = chunks[0].text[-50:] in chunks[1].text
        self.assertTrue(overlap or len(chunks[0].text) < 50)

    def test_chunk_story_with_end_token_limit(self):
        """Test end_token_limit truncates token input."""
        limit = 30
        chunks = chunking.chunk_story(
            self.text, max_tokens=20, end_token_limit=limit, model_name=self.model
        )
        total_tokens = sum(
            chunking.count_tokens(c.text, model=self.model) for c in chunks
        )
        self.assertLessEqual(total_tokens, limit)

    def test_chunk_story_with_max_chunks(self):
        """Test limiting total number of chunks."""
        chunks = chunking.chunk_story(
            self.text, max_tokens=20, max_chunks=2, model_name=self.model
        )
        self.assertEqual(len(chunks), 2)

    def test_chunk_story_empty_text(self):
        """Test chunk_story with empty text returns empty list."""
        chunks = chunking.chunk_story("", max_tokens=20, model_name=self.model)
        self.assertEqual(chunks, [])

    def test_chunk_story_max_chunks_zero(self):
        """Test chunk_story with max_chunks=0 returns empty list."""
        chunks = chunking.chunk_story(
            self.text, max_tokens=20, max_chunks=0, model_name=self.model
        )
        self.assertEqual(chunks, [])

    def test_chunk_story_indices_are_sequential(self):
        """Test that chunk indices are sequential starting from 0."""
        chunks = chunking.chunk_story(self.text, max_tokens=50, model_name=self.model)
        for i, chunk in enumerate(chunks):
            self.assertEqual(chunk.index, i)

    def test_chunk_story_start_char_nondecreasing(self):
        """Test that start_char values are non-decreasing across chunks."""
        chunks = chunking.chunk_story(self.text, max_tokens=50, model_name=self.model)
        for i in range(1, len(chunks)):
            self.assertGreaterEqual(chunks[i].start_char, chunks[i - 1].start_char)

    def test_summarize_chunks_format(self):
        """Test summarize_chunks returns a string with chunk headers."""
        chunks = chunking.chunk_story(self.text, max_tokens=30, model_name=self.model)
        summary = chunking.summarize_chunks(chunks)
        self.assertIsInstance(summary, str)
        self.assertIn("Chunk 0", summary)
        self.assertIn("starts at char", summary)

    def test_summarize_chunks_empty_list(self):
        """Test summarize_chunks with empty list returns empty string."""
        summary = chunking.summarize_chunks([])
        self.assertEqual(summary, "")

    def test_summarize_chunks_short_text_shown_in_full(self):
        """Test summarize_chunks with text <= 200 chars shows it without ellipsis."""
        short_text = "Short story."
        chunks = chunking.chunk_story(short_text, max_tokens=100, model_name=self.model)
        summary = chunking.summarize_chunks(chunks)
        self.assertIn(short_text, summary)
        self.assertNotIn(" ... ", summary)

    def test_summarize_chunks_long_text_truncated(self):
        """Test summarize_chunks with text > 200 chars shows ellipsis."""
        chunks = chunking.chunk_story(self.text, max_tokens=500, model_name=self.model)
        summary = chunking.summarize_chunks(chunks)
        self.assertIn(" ... ", summary)

    def test_display_chunks_prints_output(self):
        """Test display_chunks prints totals to stdout."""
        chunks = chunking.chunk_story(self.text, max_tokens=50, model_name=self.model)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            chunking.display_chunks(chunks)
        output = buf.getvalue()
        self.assertIn("Total chunks:", output)
        self.assertIn("Total characters:", output)
        self.assertIn("Total tokens:", output)

    def test_chunk_dataclass_fields(self):
        """Test Chunk dataclass stores all four fields correctly."""
        chunk = chunking.Chunk(index=3, text="sample", start_token=10, start_char=42)
        self.assertEqual(chunk.index, 3)
        self.assertEqual(chunk.text, "sample")
        self.assertEqual(chunk.start_token, 10)
        self.assertEqual(chunk.start_char, 42)


if __name__ == "__main__":
    unittest.main()
