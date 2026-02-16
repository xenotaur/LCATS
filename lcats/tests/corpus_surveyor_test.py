"""Unit tests for lcats.analysis.corpus_surveyor."""

import json
import numbers
import pathlib
import unittest

import tiktoken

from lcats import test_utils
from lcats.analysis import corpus_surveyor


class TestComputeCorpusStats(test_utils.TestCaseWithData):
    """Unit tests for corpus_surveyor.compute_corpus_stats."""

    def setUp(self):
        super().setUp()

        # Corpus root in the temp dir
        self.root = pathlib.Path(self.test_temp_dir) / "data"
        (self.root / "lovecraft").mkdir(parents=True, exist_ok=True)
        (self.root / "wilde").mkdir(parents=True, exist_ok=True)
        (self.root / "cache" / "gutenberg").mkdir(
            parents=True, exist_ok=True
        )  # realism

        def write_json(relpath: str, payload: dict) -> pathlib.Path:
            p = self.root / pathlib.Path(relpath)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(payload), encoding="utf-8")
            return p

        # 1) story1: title + authors list; body plain text
        self.p1 = write_json(
            "lovecraft/story1.json",
            {
                "name": "Alpha Tale",
                "author": ["Alice", "Bob"],
                "body": "One two three four",
                "metadata": {},
            },
        )

        # 2) story2: duplicate of story1 (different case/whitespace & author order)
        self.p2 = write_json(
            "lovecraft/story2.json",
            {
                "name": "  alpha   tale ",
                "author": ["bob", "ALICE"],
                "body": "One two three four",
                "metadata": {},
            },
        )

        # 3) story3: different title; authors as a string
        self.p3 = write_json(
            "wilde/story3.json",
            {
                "name": "Beta",
                "author": "Alice",
                "body": "Hi",
                "metadata": {},
            },
        )

        # 4) story4: title from metadata.name; no authors -> excluded from author_stats
        self.p4 = write_json(
            "wilde/story4.json",
            {
                "metadata": {"name": "Gamma"},
                "body": "X Y",
            },
        )

        # 5) story5: bytes-literal body; one author overlaps with story1
        self.p5 = write_json(
            "lovecraft/story5.json",
            {
                "name": "Delta",
                "author": ["Bob"],
                "body": "b'Z z z'",
            },
        )

        self.paths = [self.p1, self.p2, self.p3, self.p4, self.p5]

    def _preferred_encoder(self):
        """Mirror survey's preference: o200k_base -> cl100k_base -> gpt-4 fallback."""
        enc = None
        for name in ("o200k_base", "cl100k_base"):
            try:
                enc = tiktoken.get_encoding(name)
                break
            except Exception:
                continue
        if enc is None:
            enc = tiktoken.encoding_for_model("gpt-4")
        return enc

    def test_basic_aggregation_with_dedupe(self):
        """Deduplicate duplicate stories; aggregate author/story stats correctly."""
        story_stats, author_stats = corpus_surveyor.compute_corpus_stats(
            self.paths, dedupe=True
        )

        # Story frame has expected columns
        expected_story_cols = {
            "path",
            "story_id",
            "title",
            "authors",
            "n_authors",
            "title_words",
            "title_chars",
            "title_tokens",
            "body_words",
            "body_chars",
            "body_tokens",
        }
        self.assertTrue(expected_story_cols.issubset(set(story_stats.columns)))

        # Duplicate p2 pruned -> 4 unique stories
        self.assertEqual(len(story_stats), 4)

        # Validate per-story metrics for p1
        s1 = story_stats[story_stats["path"] == str(self.p1)].iloc[0]
        self.assertEqual(s1["title"], "Alpha Tale")
        self.assertEqual(s1["title_words"], 2)
        self.assertEqual(s1["title_chars"], len("Alpha Tale"))
        self.assertEqual(s1["body_words"], 4)  # "One two three four"
        self.assertEqual(s1["body_chars"], len("One two three four"))
        self.assertIsInstance(s1["title_tokens"], numbers.Integral)
        self.assertIsInstance(s1["body_tokens"], numbers.Integral)
        self.assertGreater(s1["title_tokens"], 0)
        self.assertGreater(s1["body_tokens"], 0)

        # Title fallback from metadata.name (p4)
        s4 = story_stats[story_stats["path"] == str(self.p4)].iloc[0]
        self.assertEqual(s4["title"], "Gamma")

        # Author aggregation frame
        expected_author_cols = {
            "author",
            "stories",
            "body_words",
            "body_chars",
            "body_tokens",
        }
        self.assertTrue(expected_author_cols.issubset(set(author_stats.columns)))

        # Alice: story1 + story3
        row_alice = author_stats[author_stats["author"] == "Alice"].iloc[0]
        self.assertEqual(row_alice["stories"], 2)
        self.assertEqual(row_alice["body_words"], 4 + 1)  # 4 (p1) + 1 (p3)
        self.assertEqual(row_alice["body_chars"], len("One two three four") + len("Hi"))
        self.assertGreater(row_alice["body_tokens"], 0)

        # Bob: story1 + story5; p5 body "b'Z z z'" -> "Z z z"
        row_bob = author_stats[author_stats["author"] == "Bob"].iloc[0]
        self.assertEqual(row_bob["stories"], 2)
        self.assertEqual(row_bob["body_words"], 4 + 3)
        self.assertEqual(
            row_bob["body_chars"], len("One two three four") + len("Z z z")
        )
        self.assertGreater(row_bob["body_tokens"], 0)

        # No anonymous authors in author_stats
        self.assertTrue((author_stats["author"].str.len() > 0).all())

    def test_dedupe_false_keeps_duplicate_row_but_author_story_counts_stay_unique(self):
        """When dedupe=False, keep duplicates; author 'stories' remains unique by story_id."""
        story_stats, author_stats = corpus_surveyor.compute_corpus_stats(
            self.paths, dedupe=False
        )

        # Both p1 and its duplicate p2 should appear now
        self.assertEqual(len(story_stats), 5)
        self.assertIn(str(self.p1), set(story_stats["path"]))
        self.assertIn(str(self.p2), set(story_stats["path"]))

        # 'stories' uses nunique(story_id), so duplicates don't inflate counts
        row_alice = author_stats[author_stats["author"] == "Alice"].iloc[0]
        self.assertEqual(row_alice["stories"], 2)  # still 2: story1 + story3

    def test_token_counts_match_selected_encoder(self):
        """Exact token counts match the encoder preference used by the implementation."""
        enc = self._preferred_encoder()

        story_stats, _ = corpus_surveyor.compute_corpus_stats([self.p3], dedupe=True)
        row = story_stats.iloc[0]

        self.assertEqual(row["title"], "Beta")
        self.assertEqual(
            row["title_tokens"], len(enc.encode("Beta", disallowed_special=()))
        )
        self.assertEqual(
            row["body_tokens"], len(enc.encode("Hi", disallowed_special=()))
        )


if __name__ == "__main__":
    unittest.main()
