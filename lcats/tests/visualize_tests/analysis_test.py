"""Unit tests for lcats.visualize.analysis."""

import unittest

from lcats.visualize import analysis


class TestSortedCounts(unittest.TestCase):
    """Tests for sorted_counts."""

    def test_sorts_by_count_descending(self):
        """Highest count comes first."""
        result = analysis.sorted_counts({"a": 1, "b": 3, "c": 2})
        self.assertEqual(result, [("b", 3), ("c", 2), ("a", 1)])

    def test_ties_broken_by_label(self):
        """Equal counts are ordered alphabetically by label."""
        result = analysis.sorted_counts({"b": 1, "a": 1})
        self.assertEqual(result, [("a", 1), ("b", 1)])

    def test_empty_mapping(self):
        """Empty input returns an empty list."""
        self.assertEqual(analysis.sorted_counts({}), [])


class TestCountsWithNoSignal(unittest.TestCase):
    """Tests for counts_with_no_signal."""

    def test_adds_no_signal_category(self):
        """A non-zero no_usable_signal_count is added as its own category."""
        result = analysis.counts_with_no_signal({"fantasy": 3}, 5)
        self.assertEqual(result, {"fantasy": 3, "no usable signal": 5})

    def test_zero_no_signal_omitted(self):
        """A zero no_usable_signal_count adds no category."""
        result = analysis.counts_with_no_signal({"fantasy": 3}, 0)
        self.assertEqual(result, {"fantasy": 3})

    def test_does_not_mutate_input(self):
        """Input mapping is not modified."""
        counts = {"fantasy": 3}
        analysis.counts_with_no_signal(counts, 5)
        self.assertEqual(counts, {"fantasy": 3})


class TestTotalCount(unittest.TestCase):
    """Tests for total_count."""

    def test_sums_all_values(self):
        """Sum of all counts is returned."""
        self.assertEqual(analysis.total_count({"a": 1, "b": 2, "c": 3}), 6)

    def test_empty_mapping_is_zero(self):
        """Empty mapping sums to zero."""
        self.assertEqual(analysis.total_count({}), 0)


class TestWordFrequencies(unittest.TestCase):
    """Tests for word_frequencies."""

    def test_counts_words_across_texts(self):
        """Word counts aggregate across every text in the list."""
        result = analysis.word_frequencies(["castle castle dragon", "castle knight"])
        self.assertEqual(result["castle"], 3)
        self.assertEqual(result["dragon"], 1)
        self.assertEqual(result["knight"], 1)

    def test_excludes_stopwords_and_short_tokens(self):
        """Stopwords and short tokens are excluded (via story_analysis.get_keywords)."""
        result = analysis.word_frequencies(["the a of dragon"])
        self.assertNotIn("the", result)
        self.assertNotIn("a", result)
        self.assertNotIn("of", result)
        self.assertIn("dragon", result)

    def test_top_k_limits_result_size(self):
        """At most top_k terms are returned."""
        text = " ".join(f"word{i}" for i in range(10))
        result = analysis.word_frequencies([text], top_k=3)
        self.assertLessEqual(len(result), 3)

    def test_empty_texts_returns_empty(self):
        """An empty text list returns an empty mapping."""
        self.assertEqual(analysis.word_frequencies([]), {})


class TestTfidfTopTerms(unittest.TestCase):
    """Tests for tfidf_top_terms."""

    def test_group_terms_ranked_above_common_terms(self):
        """A term unique to the group outranks a term common to every document."""
        corpus_texts = [
            "dragon castle dragon knight",
            "forest shadow forest path",
            "castle knight castle path",
        ]
        result = analysis.tfidf_top_terms(corpus_texts, group_indices=[0], top_k=10)
        self.assertIn("dragon", result)
        top_term = max(result, key=result.get)
        self.assertEqual(top_term, "dragon")

    def test_whole_corpus_group_is_valid_degenerate_case(self):
        """Passing every index (whole corpus) still returns a ranked mapping."""
        corpus_texts = ["dragon castle knight", "forest shadow path"]
        result = analysis.tfidf_top_terms(corpus_texts, group_indices=[0, 1], top_k=10)
        self.assertTrue(result)
        for term in ("dragon", "castle", "knight", "forest", "shadow", "path"):
            self.assertIn(term, result)

    def test_top_k_limits_result_size(self):
        """At most top_k terms are returned."""
        corpus_texts = [
            "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda"
        ]
        result = analysis.tfidf_top_terms(corpus_texts, group_indices=[0], top_k=3)
        self.assertLessEqual(len(result), 3)

    def test_empty_corpus_returns_empty(self):
        """An empty corpus returns an empty mapping."""
        self.assertEqual(analysis.tfidf_top_terms([], group_indices=[], top_k=10), {})

    def test_empty_group_indices_returns_empty(self):
        """An empty group selection returns an empty mapping."""
        result = analysis.tfidf_top_terms(["dragon castle"], group_indices=[], top_k=10)
        self.assertEqual(result, {})

    def test_excludes_stopwords_and_short_tokens(self):
        """Preprocessing matches word_frequencies (stopwords/short tokens excluded)."""
        result = analysis.tfidf_top_terms(
            ["the a of dragon castle"], group_indices=[0], top_k=10
        )
        self.assertNotIn("the", result)
        self.assertNotIn("a", result)
        self.assertNotIn("of", result)
        self.assertIn("dragon", result)

    def test_empty_vocabulary_returns_empty_not_raises(self):
        """Documents with only stopwords/short tokens return {} instead of
        propagating TfidfVectorizer's raw empty-vocabulary ValueError."""
        result = analysis.tfidf_top_terms(
            ["the a of it is", "an at to on in"], group_indices=[0, 1], top_k=10
        )
        self.assertEqual(result, {})


if __name__ == "__main__":
    unittest.main()
