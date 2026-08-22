from __future__ import annotations

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import evaluate_near_miss_fuzzy_matching as evaluator  # noqa: E402


class EvaluateNearMissFuzzyMatchingTest(unittest.TestCase):
    def test_fixture_evaluation_recovers_positive_near_misses(self):
        result = evaluator.evaluate_fixture()

        self.assertEqual(result["positive_total"], 2)
        self.assertEqual(result["positive_recovered"], 2)
        self.assertEqual(result["positive_recovery_rate"], 1.0)

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


if __name__ == "__main__":
    unittest.main()
