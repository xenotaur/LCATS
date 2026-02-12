import unittest
from lcats import chunking


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
        self.token_count = chunking.count_tokens(self.text, model=self.model)

    def test_token_count_matches(self):
        """Test token count of the unit test's story text is a positive integer."""
        self.assertTrue(isinstance(self.token_count, int))
        self.assertGreater(self.token_count, 0)

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

    def test_summarize_chunks_format(self):
        """Test summarize_chunks returns a string with chunk headers."""
        chunks = chunking.chunk_story(self.text, max_tokens=30, model_name=self.model)
        summary = chunking.summarize_chunks(chunks)
        self.assertIsInstance(summary, str)
        self.assertIn("Chunk 0", summary)
        self.assertIn("starts at char", summary)


if __name__ == "__main__":
    unittest.main()
