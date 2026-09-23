"""Tests for lcats.visualize.comparison."""

import dataclasses
import json
import unittest
from unittest import mock

from parameterized import parameterized

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


class TestNWayComparison(unittest.TestCase):
    """Reference-to-many analysis behavior."""

    def _nway_spec(self, **overrides):
        base = comparison.NWayComparisonSpec(
            universe=comparison.UniverseSpec(),
            reference=comparison.Selector(
                comparison.SelectorKind.ALL, label="whole fixture"
            ),
            panels=(
                comparison.NWayPanelSpec(
                    "fantasy",
                    comparison.Selector(
                        comparison.SelectorKind.GENRE,
                        genre="fantasy",
                        membership_mode=comparison.MembershipMode.CANDIDATE,
                        label="Fantasy",
                    ),
                ),
                comparison.NWayPanelSpec(
                    "mystery",
                    comparison.Selector(
                        comparison.SelectorKind.GENRE,
                        genre="mystery",
                        membership_mode=comparison.MembershipMode.CANDIDATE,
                        label="Mystery",
                    ),
                ),
            ),
            metric=comparison.MetricSpec(comparison.MetricName.PER_MILLION),
            vocabulary=comparison.NWayVocabularySpec(top_k=3),
        )
        return dataclasses.replace(base, **overrides)

    def test_panel_deviation_is_panel_minus_reference(self):
        """Signed cells use the documented panel-minus-reference direction."""
        result = comparison.compare_many(_corpus(), self._nway_spec())
        shared = next(row for row in result.rows if row.term == "shared")
        fantasy = next(cell for cell in shared.panels if cell.panel_key == "fantasy")

        self.assertAlmostEqual(
            fantasy.deviation, fantasy.value - shared.reference_value
        )
        self.assertEqual(
            result.manifest["deviation_definition"], "panel_value - reference_value"
        )

    def test_all_panels_share_one_vocabulary_and_order(self):
        """Every panel cell is aligned to the same deterministic term rows."""
        result = comparison.compare_many(_corpus(), self._nway_spec())

        self.assertEqual(len(result.rows), 3)
        self.assertTrue(all(len(row.panels) == 2 for row in result.rows))
        self.assertEqual([row.display_order for row in result.rows], list(range(1, 4)))
        self.assertEqual(len(result.long_table()), 6)

    def test_duplicate_panel_keys_raise(self):
        """Panel keys are stable identifiers and cannot be ambiguous."""
        panel = self._nway_spec().panels[0]
        with self.assertRaises(ValueError):
            comparison.compare_many(_corpus(), self._nway_spec(panels=(panel, panel)))

    def test_reference_vocabulary_does_not_fill_with_panel_only_terms(self):
        """Reference ranking never pads with zero-valued panel-only terms."""
        spec = self._nway_spec(
            reference=comparison.Selector(
                comparison.SelectorKind.STORY_LIST,
                story_ids=("a/one",),
                label="one story",
            ),
            vocabulary=comparison.NWayVocabularySpec(
                policy=comparison.NWayVocabularyPolicy.REFERENCE_VALUE,
                top_k=20,
            ),
        )

        result = comparison.compare_many(_corpus(), spec)

        self.assertEqual(
            {row.term for row in result.rows}, {"castle", "dragon", "shared"}
        )

    def test_union_top_ignores_zero_valued_terms_for_empty_panel(self):
        """An empty selector cannot add alphabetical zero-valued filler terms."""
        spec = self._nway_spec(
            reference=comparison.Selector(
                comparison.SelectorKind.STORY_LIST,
                story_ids=("a/one",),
                label="one story",
            ),
            panels=(
                comparison.NWayPanelSpec(
                    "mystery",
                    comparison.Selector(
                        comparison.SelectorKind.GENRE,
                        genre="mystery",
                        label="Mystery",
                    ),
                ),
                comparison.NWayPanelSpec(
                    "empty",
                    comparison.Selector(
                        comparison.SelectorKind.STORY_LIST,
                        story_ids=(),
                        label="Empty",
                    ),
                ),
            ),
            vocabulary=comparison.NWayVocabularySpec(
                policy=comparison.NWayVocabularyPolicy.UNION_TOP,
                top_k=1,
            ),
        )

        result = comparison.compare_many(_corpus(), spec)

        self.assertEqual({row.term for row in result.rows}, {"clue", "dragon"})

    def test_manifest_is_json_serializable(self):
        """N-way provenance can be written beside figures and data."""
        result = comparison.compare_many(_corpus(), self._nway_spec())

        serialized = json.dumps(result.manifest, sort_keys=True)
        self.assertIn("lcats-nway-comparison-v2", serialized)

    def test_fewer_than_two_panels_raise(self):
        """An N-way comparison needs an ordered sequence of at least two panels."""
        spec = self._nway_spec(panels=self._nway_spec().panels[:1])

        with self.assertRaisesRegex(ValueError, "at least two"):
            comparison.compare_many(_corpus(), spec)

    def test_long_table_follows_display_then_declared_panel_order(self):
        """Long-form records are deterministic and carry per-cell references."""
        result = comparison.compare_many(_corpus(), self._nway_spec())
        records = result.long_table()

        self.assertEqual(
            [(r["display_order"], r["panel_order"]) for r in records],
            [(order, panel) for order in (1, 2, 3) for panel in (1, 2)],
        )
        self.assertEqual({r["reference_key"] for r in records}, {"reference"})
        for record in records:
            with self.subTest(term=record["term"], panel=record["panel_key"]):
                self.assertAlmostEqual(
                    record["deviation"], record["value"] - record["reference_value"]
                )

    def test_complement_panels_equal_universe_minus_selector(self):
        """Complement mode displays U - S and proves the construction."""
        spec = self._nway_spec(panel_mode=comparison.NWayPanelMode.COMPLEMENT)
        result = comparison.compare_many(_corpus(), spec)
        panels = {panel["key"]: panel for panel in result.manifest["panels"]}
        universe = set(result.manifest["universe"]["story_ids"])

        self.assertEqual(panels["fantasy"]["label"], "U - Fantasy")
        self.assertEqual(panels["fantasy"]["story_ids"], ["c/three"])
        self.assertEqual(panels["mystery"]["story_ids"], ["a/one", "b/two"])
        for key, panel in panels.items():
            with self.subTest(panel=key):
                self.assertEqual(
                    set(panel["story_ids"]),
                    universe - set(panel["base"]["story_ids"]),
                )
        records = result.manifest["complements"]
        self.assertEqual([record["role"] for record in records], ["panel", "panel"])
        self.assertTrue(
            all(record["verified_equals_universe_minus_base"] for record in records)
        )
        self.assertTrue(
            all(
                record["universe_fingerprint"]
                == result.manifest["universe"]["fingerprint"]
                for record in records
            )
        )

    def test_complement_mode_records_base_overlaps(self):
        """Complement panels also report intersections of their bases S."""
        spec = self._nway_spec(panel_mode=comparison.NWayPanelMode.COMPLEMENT)
        result = comparison.compare_many(_corpus(), spec)

        self.assertEqual(
            result.manifest["base_overlaps"],
            [
                {
                    "left_panel_key": "fantasy",
                    "right_panel_key": "mystery",
                    "story_count": 0,
                    "story_ids": [],
                }
            ],
        )
        self.assertEqual(
            comparison.compare_many(_corpus(), self._nway_spec()).manifest[
                "base_overlaps"
            ],
            [],
        )

    def test_empty_per_panel_reference_warns(self):
        """A panel equal to U has an empty complement, which is disclosed."""
        panels = (
            comparison.NWayPanelSpec(
                "everything", comparison.Selector(comparison.SelectorKind.ALL)
            ),
            self._nway_spec().panels[1],
        )
        spec = self._nway_spec(
            panels=panels,
            reference=None,
            reference_policy=comparison.NWayReferencePolicy.PER_PANEL_COMPLEMENT,
            vocabulary=comparison.NWayVocabularySpec(
                policy=comparison.NWayVocabularyPolicy.MAX_PANEL_VALUE
            ),
            ordering=comparison.NWayOrderingSpec(
                by=comparison.NWayOrdering.MAX_PANEL_VALUE
            ),
        )

        result = comparison.compare_many(_corpus(), spec)

        self.assertTrue(
            any(
                "everything:complement" in warning
                for warning in result.manifest["warnings"]
            )
        )

    def test_complement_mode_rejects_complement_bases(self):
        """Complement mode takes S, so a pre-complemented base is ambiguous."""
        complement_panel = comparison.NWayPanelSpec(
            "not_fantasy",
            comparison.Selector(
                comparison.SelectorKind.COMPLEMENT,
                base=comparison.Selector(
                    comparison.SelectorKind.GENRE, genre="fantasy"
                ),
            ),
        )
        spec = self._nway_spec(
            panels=(complement_panel, self._nway_spec().panels[1]),
            panel_mode=comparison.NWayPanelMode.COMPLEMENT,
        )

        with self.assertRaisesRegex(ValueError, "base selectors"):
            comparison.compare_many(_corpus(), spec)

    def test_per_panel_complement_reference_uses_each_panels_complement(self):
        """Each cell is compared with U minus its own panel."""
        spec = self._nway_spec(
            reference=None,
            reference_policy=comparison.NWayReferencePolicy.PER_PANEL_COMPLEMENT,
            vocabulary=comparison.NWayVocabularySpec(
                policy=comparison.NWayVocabularyPolicy.MAX_ABSOLUTE_DEVIATION,
                top_k=None,
            ),
            ordering=comparison.NWayOrderingSpec(
                by=comparison.NWayOrdering.MAX_ABSOLUTE_DEVIATION
            ),
        )
        result = comparison.compare_many(_corpus(), spec)
        references = {ref["panel_key"]: ref for ref in result.manifest["references"]}
        dragon = next(row for row in result.rows if row.term == "dragon")
        fantasy = next(cell for cell in dragon.panels if cell.panel_key == "fantasy")

        self.assertIsNone(result.manifest["reference"])
        self.assertIsNone(dragon.reference_value)
        self.assertEqual(references["fantasy"]["story_ids"], ["c/three"])
        self.assertEqual(references["mystery"]["story_ids"], ["a/one", "b/two"])
        self.assertEqual(fantasy.reference_key, "fantasy:complement")
        self.assertEqual(fantasy.reference_label, "U - Fantasy")
        self.assertEqual(fantasy.reference_value, 0.0)
        self.assertAlmostEqual(fantasy.deviation, fantasy.value)
        self.assertEqual(
            [record["role"] for record in result.manifest["complements"]],
            ["reference", "reference"],
        )
        self.assertTrue(
            all(
                record["verified_equals_universe_minus_base"]
                for record in result.manifest["complements"]
            )
        )

    def test_no_reference_reports_values_without_deviation(self):
        """The no-reference policy never fabricates a zero reference."""
        spec = self._nway_spec(
            reference=None,
            reference_policy=comparison.NWayReferencePolicy.NONE,
            vocabulary=comparison.NWayVocabularySpec(
                policy=comparison.NWayVocabularyPolicy.MAX_PANEL_VALUE, top_k=2
            ),
            ordering=comparison.NWayOrderingSpec(
                by=comparison.NWayOrdering.MAX_PANEL_VALUE
            ),
        )
        result = comparison.compare_many(_corpus(), spec)

        self.assertEqual(result.manifest["references"], [])
        self.assertIsNone(result.manifest["deviation_definition"])
        self.assertTrue(
            all(
                cell.deviation is None and cell.reference_value is None
                for row in result.rows
                for cell in row.panels
            )
        )
        maxima = [max(cell.value for cell in row.panels) for row in result.rows]
        self.assertEqual(maxima, sorted(maxima, reverse=True))

    @parameterized.expand(
        [
            ("common_without_reference", {"reference": None}, "requires a reference"),
            (
                "none_with_reference",
                {"reference_policy": comparison.NWayReferencePolicy.NONE},
                "set reference=None",
            ),
            (
                "per_panel_reference_value_vocabulary",
                {
                    "reference": None,
                    "reference_policy": (
                        comparison.NWayReferencePolicy.PER_PANEL_COMPLEMENT
                    ),
                },
                "reference_value",
            ),
            (
                "none_absolute_deviation_order",
                {
                    "reference": None,
                    "reference_policy": comparison.NWayReferencePolicy.NONE,
                    "vocabulary": comparison.NWayVocabularySpec(
                        policy=comparison.NWayVocabularyPolicy.MAX_PANEL_VALUE
                    ),
                    "ordering": comparison.NWayOrderingSpec(
                        by=comparison.NWayOrdering.MAX_ABSOLUTE_DEVIATION
                    ),
                },
                "max_absolute_deviation",
            ),
        ]
    )
    def test_reference_policy_conflicts_raise(self, _name, overrides, message):
        """Reference policy, reference selector, and rankings must agree."""
        with self.assertRaisesRegex(ValueError, message):
            comparison.compare_many(_corpus(), self._nway_spec(**overrides))

    def test_overlapping_selectors_record_every_pair_without_partition_claim(self):
        """Overlap is reported pairwise; panels are never claimed to partition U."""
        panels = (
            *self._nway_spec().panels,
            comparison.NWayPanelSpec(
                "sf",
                comparison.Selector(
                    comparison.SelectorKind.GENRE,
                    genre="science fiction",
                    label="SF",
                ),
            ),
        )
        result = comparison.compare_many(_corpus(), self._nway_spec(panels=panels))
        overlaps = {
            (record["left_panel_key"], record["right_panel_key"]): record
            for record in result.manifest["panel_overlaps"]
        }
        membership = result.manifest["membership"]

        self.assertEqual(
            list(overlaps),
            [("fantasy", "mystery"), ("fantasy", "sf"), ("mystery", "sf")],
        )
        self.assertEqual(overlaps[("fantasy", "sf")]["story_ids"], ["b/two"])
        self.assertEqual(overlaps[("fantasy", "mystery")]["story_count"], 0)
        self.assertEqual(overlaps[("mystery", "sf")]["story_count"], 0)
        self.assertFalse(membership["partition_claim"])
        self.assertFalse(membership["pairwise_disjoint"])
        self.assertTrue(membership["covers_universe"])
        self.assertIn("overlap in 1 pair", result.manifest["warnings"][0])

    def test_universe_fingerprint_is_stable_and_order_sensitive(self):
        """All panels are bound to one fingerprinted universe."""
        result = comparison.compare_many(_corpus(), self._nway_spec())

        self.assertEqual(
            result.manifest["universe"]["fingerprint"],
            comparison.story_id_fingerprint(("a/one", "b/two", "c/three")),
        )
        self.assertNotEqual(
            comparison.story_id_fingerprint(("a/one", "b/two")),
            comparison.story_id_fingerprint(("b/two", "a/one")),
        )

    def test_every_panel_and_reference_records_the_shared_metric(self):
        """Commensurability evidence is explicit for panels and references."""
        result = comparison.compare_many(_corpus(), self._nway_spec())
        entries = result.manifest["panels"] + result.manifest["references"]

        self.assertTrue(
            all(entry["metric"] == result.manifest["metric"] for entry in entries)
        )
        self.assertTrue(result.manifest["commensurability"]["shared_vocabulary"])

    def test_custom_tokenizer_provenance_names_real_function(self):
        """Non-default preprocessing identifies the function that implements it."""
        spec = self._nway_spec(
            token_filter=comparison.TokenFilter(include_stopwords=True, min_length=1)
        )

        result = comparison.compare_many(_corpus(), spec)

        self.assertEqual(
            result.manifest["preprocessing"]["tokenizer"],
            "lcats.visualize.comparison._tokenize",
        )


if __name__ == "__main__":
    unittest.main()
