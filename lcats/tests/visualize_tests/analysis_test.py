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


if __name__ == "__main__":
    unittest.main()
