"""Tests for lcats.visualize.comparison."""

import dataclasses
import json
import unittest
from unittest import mock

from lcats.visualize import analysis
from lcats.visualize import comparison


def _corpus():
    return comparison.ComparisonCorpus(
        documents=(
            comparison.ComparisonDocument(
                "a/one",
                "dragon dragon castle shared",
                candidate_genres=("fantasy",),
                primary_genre="fantasy",
                selection_genres=("sample-fantasy",),
            ),
            comparison.ComparisonDocument(
                "b/two",
                "rocket rocket shared",
                candidate_genres=("science fiction", "fantasy"),
                primary_genre="science fiction",
                selection_genres=("sample-sf",),
            ),
            comparison.ComparisonDocument(
                "c/three",
                "detective clue shared",
                candidate_genres=("mystery",),
                primary_genre="mystery",
                selection_genres=("sample-mystery",),
            ),
        ),
        source_path="fixture-corpus",
        source_revision="abc123",
    )


def _spec(**overrides):
    base = comparison.ComparisonSpec(
        universe=comparison.UniverseSpec(),
        left=comparison.Selector(
            comparison.SelectorKind.GENRE,
            genre="fantasy",
            membership_mode=comparison.MembershipMode.CANDIDATE,
        ),
        right=comparison.Selector(
            comparison.SelectorKind.COMPLEMENT,
            base=comparison.Selector(
                comparison.SelectorKind.GENRE,
                genre="fantasy",
                membership_mode=comparison.MembershipMode.CANDIDATE,
            ),
        ),
        left_metric=comparison.MetricSpec(comparison.MetricName.RAW_COUNT),
        right_metric=comparison.MetricSpec(comparison.MetricName.RAW_COUNT),
        vocabulary=comparison.VocabularySpec(
            policy=comparison.VocabularyPolicy.ALL,
            top_k=None,
        ),
        ordering=comparison.OrderingSpec(comparison.Ordering.ALPHABETICAL),
    )
    return dataclasses.replace(base, **overrides)


class TestSelectors(unittest.TestCase):
    """Selector and universe behavior."""

    def test_complement_is_universe_minus_selector(self):
        """Complement membership is computed as U - S inside the declared universe."""
        spec = _spec(
            universe=comparison.UniverseSpec(story_ids=("a/one", "b/two")),
        )
        result = comparison.compare(_corpus(), spec)

        self.assertEqual(result.manifest["universe"]["story_ids"], ["a/one", "b/two"])
        self.assertEqual(result.manifest["left"]["story_ids"], ["a/one", "b/two"])
        self.assertEqual(result.manifest["right"]["story_ids"], [])

    def test_primary_membership_differs_from_candidate_membership(self):
        """Primary and candidate genre semantics are explicit and distinct."""
        spec = _spec(
            left=comparison.Selector(
                comparison.SelectorKind.GENRE,
                genre="fantasy",
                membership_mode=comparison.MembershipMode.PRIMARY,
            ),
            right=comparison.Selector(
                comparison.SelectorKind.GENRE,
                genre="fantasy",
                membership_mode=comparison.MembershipMode.CANDIDATE,
            ),
        )
        result = comparison.compare(_corpus(), spec)

        self.assertEqual(result.manifest["left"]["story_ids"], ["a/one"])
        self.assertEqual(result.manifest["right"]["story_ids"], ["a/one", "b/two"])
        self.assertEqual(result.manifest["overlap"]["story_ids"], ["a/one"])
        self.assertTrue(result.manifest["warnings"])

    def test_unknown_story_list_member_raises(self):
        """Story-list selectors cannot silently escape U."""
        spec = _spec(
            left=comparison.Selector(
                comparison.SelectorKind.STORY_LIST, story_ids=("missing/story",)
            )
        )
        with self.assertRaises(ValueError):
            comparison.compare(_corpus(), spec)

    def test_explicit_empty_story_list_universe_stays_empty(self):
        """An explicit empty universe is not treated as the whole corpus."""
        spec = _spec(
            universe=comparison.UniverseSpec(kind="story_list", story_ids=()),
        )
        result = comparison.compare(_corpus(), spec)

        self.assertEqual(result.manifest["universe"]["story_ids"], [])
        self.assertEqual(result.manifest["left"]["story_ids"], [])
        self.assertEqual(result.manifest["right"]["story_ids"], [])


class TestMetrics(unittest.TestCase):
    """Metric and support-count behavior."""

    def test_raw_counts_and_denominators_are_reported(self):
        """Rows carry raw support counts and left/right denominators."""
        result = comparison.compare(_corpus(), _spec())
        rows = {row.term: row for row in result.rows}

        self.assertEqual(rows["dragon"].left_raw_count, 2)
        self.assertEqual(rows["dragon"].right_raw_count, 0)
        self.assertEqual(rows["shared"].left_token_denominator, 7)
        self.assertEqual(rows["shared"].right_token_denominator, 3)
        self.assertEqual(rows["shared"].left_document_denominator, 2)

    def test_per_million_normalizes_by_selected_tokens(self):
        """Per-million values disclose unequal denominators."""
        spec = _spec(
            left_metric=comparison.MetricSpec(comparison.MetricName.PER_MILLION),
            right_metric=comparison.MetricSpec(comparison.MetricName.PER_MILLION),
        )
        result = comparison.compare(_corpus(), spec)
        rows = {row.term: row for row in result.rows}

        self.assertAlmostEqual(rows["dragon"].left_value, 2 / 7 * 1_000_000)
        self.assertEqual(rows["dragon"].right_value, 0.0)

    def test_document_percentage_uses_document_denominator(self):
        """Document percentage is based on selected story count."""
        spec = _spec(
            left_metric=comparison.MetricSpec(
                comparison.MetricName.DOCUMENT_PERCENTAGE
            ),
            right_metric=comparison.MetricSpec(
                comparison.MetricName.DOCUMENT_PERCENTAGE
            ),
        )
        result = comparison.compare(_corpus(), spec)
        rows = {row.term: row for row in result.rows}

        self.assertEqual(rows["shared"].left_value, 100.0)
        self.assertEqual(rows["shared"].right_value, 100.0)
        self.assertEqual(
            result.manifest["metrics"]["left"]["effective_denominator"], "documents"
        )

    def test_metric_rejects_unsupported_denominator(self):
        """Metric provenance cannot claim a denominator the calculation ignores."""
        spec = _spec(
            left_metric=comparison.MetricSpec(
                comparison.MetricName.PER_MILLION,
                denominator="documents",
            )
        )

        with self.assertRaises(ValueError):
            comparison.compare(_corpus(), spec)

    def test_tfidf_contrast_fits_once_over_universe(self):
        """TF-IDF contrast uses the shared universe and records that provenance."""
        spec = _spec(
            left=comparison.Selector(
                comparison.SelectorKind.GENRE,
                genre="fantasy",
                membership_mode=comparison.MembershipMode.PRIMARY,
            ),
            right=comparison.Selector(
                comparison.SelectorKind.COMPLEMENT,
                base=comparison.Selector(
                    comparison.SelectorKind.GENRE,
                    genre="fantasy",
                    membership_mode=comparison.MembershipMode.PRIMARY,
                ),
            ),
            left_metric=comparison.MetricSpec(comparison.MetricName.TFIDF_CONTRAST),
            right_metric=comparison.MetricSpec(comparison.MetricName.TFIDF_CONTRAST),
            vocabulary=comparison.VocabularySpec(
                policy=comparison.VocabularyPolicy.TOP_LEFT,
                top_k=3,
            ),
        )
        result = comparison.compare(_corpus(), spec)

        self.assertEqual(result.manifest["metrics"]["tfidf_fit_scope"], "universe")
        self.assertIn("dragon", [row.term for row in result.rows])

    def test_tfidf_metrics_honor_declared_token_filter(self):
        """TF-IDF uses the same token filter disclosed in the manifest."""
        corpus = comparison.ComparisonCorpus(
            documents=(
                comparison.ComparisonDocument("a/one", "the cat"),
                comparison.ComparisonDocument("b/two", "dog"),
            )
        )
        spec = comparison.ComparisonSpec(
            universe=comparison.UniverseSpec(),
            left=comparison.Selector(comparison.SelectorKind.ALL),
            right=comparison.Selector(
                comparison.SelectorKind.STORY_LIST, story_ids=("b/two",)
            ),
            left_metric=comparison.MetricSpec(comparison.MetricName.MEAN_TFIDF),
            right_metric=comparison.MetricSpec(comparison.MetricName.MEAN_TFIDF),
            token_filter=comparison.TokenFilter(include_stopwords=True, min_length=1),
            vocabulary=comparison.VocabularySpec(
                policy=comparison.VocabularyPolicy.ALL,
                top_k=None,
            ),
            ordering=comparison.OrderingSpec(comparison.Ordering.ALPHABETICAL),
        )
        result = comparison.compare(corpus, spec)

        self.assertIn("the", [row.term for row in result.rows])

    def test_tfidf_fit_is_shared_between_sides(self):
        """Both TF-IDF series are derived from one universe fit."""
        spec = _spec(
            left_metric=comparison.MetricSpec(comparison.MetricName.MEAN_TFIDF),
            right_metric=comparison.MetricSpec(comparison.MetricName.TFIDF_CONTRAST),
        )

        with mock.patch(
            "lcats.visualize.comparison._fit_tfidf",
            wraps=comparison._fit_tfidf,
        ) as fit_tfidf:
            comparison.compare(_corpus(), spec)

        self.assertEqual(fit_tfidf.call_count, 1)

    def test_stopword_filter_can_preserve_case(self):
        """Stopword removal does not force lowercase when lowercase=False."""
        corpus = comparison.ComparisonCorpus(
            documents=(
                comparison.ComparisonDocument("a/one", "Apple apple the"),
                comparison.ComparisonDocument("b/two", "pear"),
            )
        )
        spec = comparison.ComparisonSpec(
            universe=comparison.UniverseSpec(),
            left=comparison.Selector(comparison.SelectorKind.ALL),
            right=comparison.Selector(
                comparison.SelectorKind.STORY_LIST, story_ids=("b/two",)
            ),
            left_metric=comparison.MetricSpec(comparison.MetricName.RAW_COUNT),
            right_metric=comparison.MetricSpec(comparison.MetricName.RAW_COUNT),
            token_filter=comparison.TokenFilter(
                include_stopwords=False,
                min_length=1,
                lowercase=False,
            ),
            vocabulary=comparison.VocabularySpec(
                policy=comparison.VocabularyPolicy.ALL,
                top_k=None,
            ),
            ordering=comparison.OrderingSpec(comparison.Ordering.ALPHABETICAL),
        )
        result = comparison.compare(corpus, spec)
        rows = {row.term: row for row in result.rows}

        self.assertEqual(rows["Apple"].left_raw_count, 1)
        self.assertEqual(rows["apple"].left_raw_count, 1)
        self.assertNotIn("the", rows)

    def test_analysis_module_adapter_returns_comparison_result(self):
        """Existing analysis module exposes the comparison entry point."""
        result = analysis.compare_lexical(_corpus(), _spec())

        self.assertIsInstance(result, comparison.ComparisonResult)
        self.assertTrue(result.rows)


class TestVocabularyAndOrdering(unittest.TestCase):
    """Aligned vocabulary and deterministic order behavior."""

    def test_top_absolute_difference_and_tie_order_are_deterministic(self):
        """Top-N selection and row ordering use stable value/name tie-breaks."""
        spec = _spec(
            vocabulary=comparison.VocabularySpec(
                policy=comparison.VocabularyPolicy.TOP_ABSOLUTE_DIFFERENCE,
                top_k=2,
            ),
            ordering=comparison.OrderingSpec(comparison.Ordering.ABSOLUTE_DIFFERENCE),
        )
        result = comparison.compare(_corpus(), spec)

        self.assertEqual([row.term for row in result.rows], ["dragon", "rocket"])
        self.assertEqual([row.display_order for row in result.rows], [1, 2])

    def test_include_and_exclude_terms_override_policy(self):
        """Explicit include/exclude lists are applied after the policy."""
        spec = _spec(
            vocabulary=comparison.VocabularySpec(
                policy=comparison.VocabularyPolicy.TOP_LEFT,
                top_k=1,
                include_terms=("clue",),
                exclude_terms=("dragon",),
            )
        )
        result = comparison.compare(_corpus(), spec)

        terms = [row.term for row in result.rows]
        self.assertIn("clue", terms)
        self.assertNotIn("dragon", terms)

    def test_explicit_ordering_places_unknown_terms_after_declared_terms(self):
        """Explicit term order is honored without dropping extra aligned rows."""
        spec = _spec(
            ordering=comparison.OrderingSpec(
                comparison.Ordering.EXPLICIT, explicit_terms=("rocket", "dragon")
            )
        )
        result = comparison.compare(_corpus(), spec)

        self.assertEqual([row.term for row in result.rows[:2]], ["rocket", "dragon"])


class TestCompatibility(unittest.TestCase):
    """Compatibility checks for renderer-facing styles."""

    def test_reference_overlay_rejects_mismatched_metrics(self):
        """Overlay specs cannot compare incommensurate metrics."""
        spec = _spec(
            style=comparison.ComparisonStyle.REFERENCE_OVERLAY,
            left_metric=comparison.MetricSpec(comparison.MetricName.RAW_COUNT),
            right_metric=comparison.MetricSpec(comparison.MetricName.PER_MILLION),
        )

        with self.assertRaises(ValueError):
            comparison.compare(_corpus(), spec)

    def test_mirrored_allows_different_metrics(self):
        """Mirrored tables may expose differently labelled left/right metrics."""
        spec = _spec(
            style=comparison.ComparisonStyle.MIRRORED,
            left_metric=comparison.MetricSpec(comparison.MetricName.RAW_COUNT),
            right_metric=comparison.MetricSpec(comparison.MetricName.PER_MILLION),
        )
        result = comparison.compare(_corpus(), spec)

        self.assertTrue(result.rows)
        self.assertEqual(result.manifest["metrics"]["left"]["name"], "raw_count")
        self.assertEqual(result.manifest["metrics"]["right"]["name"], "per_million")

    def test_manifest_is_json_serializable(self):
        """Manifest payload can be written beside later figure outputs."""
        result = comparison.compare(_corpus(), _spec())

        serialized = json.dumps(result.manifest, sort_keys=True)
        self.assertIn("lcats-comparison-v1", serialized)


if __name__ == "__main__":
    unittest.main()
