from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import evaluate_near_miss_fuzzy_matching as evaluator  # noqa: E402


class EvaluateNearMissFuzzyMatchingTest(unittest.TestCase):
    def test_fixture_evaluation_counts_only_exact_span_recovery(self):
        result = evaluator.evaluate_fixture()

        self.assertEqual(result["positive_total"], 2)
        self.assertEqual(result["positive_recovered"], 1)
        self.assertEqual(result["positive_recovery_rate"], 0.5)

        by_case = {item["case_id"]: item for item in result["positive_results"]}
        self.assertTrue(
            by_case["no_charge_end_exact_missing_p"]["recovered_expected_span"]
        )
        self.assertFalse(
            by_case["way_of_a_rebel_start_exact_verb_substitution"][
                "recovered_expected_span"
            ]
        )
        self.assertNotEqual(
            by_case["way_of_a_rebel_start_exact_verb_substitution"]["match"]["end"],
            by_case["way_of_a_rebel_start_exact_verb_substitution"][
                "expected_span_end"
            ],
        )

    def test_fixture_evaluation_rejects_negative_decoys(self):
        result = evaluator.evaluate_fixture()

        self.assertEqual(result["negative_total"], 4)
        self.assertEqual(result["negative_false_positives"], 0)
        self.assertEqual(result["negative_false_positive_rate"], 0.0)

    def test_candidate_policy_is_strict_enough_to_reject_related_wrong_window(self):
        result = evaluator.evaluate_fixture()
        by_case = {item["case_id"]: item for item in result["negative_results"]}

        self.assertFalse(
            by_case["no_charge_repeated_character_wrong_window"]["matched"]
        )
        self.assertFalse(by_case["way_radio_voice_wrong_window"]["matched"])

    def test_story_text_canonicalizes_newlines_before_offset_use(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = pathlib.Path(tmpdir) / "story.json"
            path.write_text('{"body": "alpha\\r\\nbeta\\rgamma"}', encoding="utf-8")

            self.assertEqual(evaluator._story_text(path), "alpha\nbeta\ngamma")

    def test_uniqueness_rejects_any_close_distinct_candidate(self):
        policy = evaluator.Policy(
            name="test",
            max_edit_distance=3,
            min_similarity_ratio=0.985,
            min_contiguous_run_ratio=0.7,
            uniqueness_margin=0.02,
        )
        matches = [
            evaluator.CandidateMatch(0, 10, "best", 1, 0.990, 0.9),
            evaluator.CandidateMatch(20, 30, "worse", 2, 0.940, 0.9),
            evaluator.CandidateMatch(40, 50, "close", 2, 0.980, 0.9),
        ]

        self.assertFalse(evaluator._is_unique_enough(matches, policy))


if __name__ == "__main__":
    unittest.main()
