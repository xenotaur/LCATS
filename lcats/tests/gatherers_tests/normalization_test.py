"""Unit tests for lcats.gatherers.normalization."""

import unittest

from lcats.gatherers import normalization


class NormalizeBodyTest(unittest.TestCase):
    """Tests for the body-level normalization helper."""

    def test_repairs_measured_mojibake_and_reports_provenance(self):
        # Real sampled contexts (WI-RULES-0016): Mac-Roman é and Latin-1 °.
        body = "unnerving even to the blas√© eyes; 60Â° below"

        normalized, applied = normalization.normalize_body(body)

        self.assertEqual("unnerving even to the blasé eyes; 60° below", normalized)
        rule_ids = [entry["rule_id"] for entry in applied]
        self.assertEqual(
            ["mojibake-latin1-degree-sign", "mojibake-macroman-e-acute"], rule_ids
        )
        for entry in applied:
            self.assertEqual(1, entry["count"])
            self.assertIn("replacement", entry)

    def test_counts_multiple_occurrences_of_one_rule(self):
        body = "resumÃ© and clichÃ© and exptosÃ©"

        _, applied = normalization.normalize_body(body)

        self.assertEqual(1, len(applied))
        self.assertEqual("mojibake-latin1-e-acute", applied[0]["rule_id"])
        self.assertEqual(3, applied[0]["count"])

    def test_clean_body_returned_unchanged(self):
        body = "A perfectly clean sentence with é and ñ already correct."

        normalized, applied = normalization.normalize_body(body)

        self.assertIs(body, normalized)
        self.assertEqual([], applied)

    def test_non_string_body_is_passed_through(self):
        normalized, applied = normalization.normalize_body(None)

        self.assertIsNone(normalized)
        self.assertEqual([], applied)

    def test_normalization_is_idempotent(self):
        body = "trumpets of Ragnar√∂k and se√±orita"

        once, first_applied = normalization.normalize_body(body)
        twice, second_applied = normalization.normalize_body(once)

        self.assertEqual(once, twice)
        self.assertNotEqual([], first_applied)
        self.assertEqual([], second_applied)


class NormalizeStoryDictTest(unittest.TestCase):
    """Tests for the story-dict normalization helper."""

    def test_repairs_body_and_stamps_metadata(self):
        data = {
            "name": "The Marrying Man",
            "body": "even to the blas√© eyes of Marilyn",
            "metadata": {"author": "Test", "year": 1950},
        }

        result = normalization.normalize_story_dict(data)

        self.assertIs(data, result)
        self.assertEqual("even to the blasé eyes of Marilyn", result["body"])
        provenance = result["metadata"]["normalization"]
        self.assertEqual(normalization.RULE_SOURCE, provenance["rule_source"])
        self.assertEqual(
            "mojibake-macroman-e-acute",
            provenance["rules_applied"][0]["rule_id"],
        )
        # Pre-existing metadata is preserved alongside the provenance block.
        self.assertEqual("Test", result["metadata"]["author"])

    def test_clean_story_left_byte_identical(self):
        data = {
            "name": "Clean",
            "body": "No defects here at all.",
            "metadata": {"author": "Z"},
        }
        original_metadata = dict(data["metadata"])

        result = normalization.normalize_story_dict(data)

        self.assertEqual("No defects here at all.", result["body"])
        self.assertEqual(original_metadata, result["metadata"])
        self.assertNotIn("normalization", result["metadata"])

    def test_two_regenerations_produce_identical_output(self):
        def fresh():
            return {
                "name": "S",
                "body": "adapting a hypnop√¶dic language on Ragnar√∂k",
                "metadata": {"author": "A"},
            }

        first = normalization.normalize_story_dict(fresh())
        second = normalization.normalize_story_dict(fresh())

        self.assertEqual(first, second)
        self.assertEqual("adapting a hypnopædic language on Ragnarök", first["body"])

    def test_missing_metadata_still_repairs_body(self):
        data = {"name": "S", "body": "se√±orita"}

        result = normalization.normalize_story_dict(data)

        self.assertEqual("señorita", result["body"])
        self.assertNotIn("metadata", result)


if __name__ == "__main__":
    unittest.main()
