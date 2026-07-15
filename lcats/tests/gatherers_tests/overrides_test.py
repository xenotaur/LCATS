"""Unit tests for lcats.gatherers.overrides and its normalization integration."""

import json
import unittest
import warnings

from lcats.gatherers import normalization
from lcats.gatherers import overrides


class ApplyOverridesTest(unittest.TestCase):
    """Tests for the override application helper."""

    def test_applies_entry_and_reports_provenance(self):
        entries = [
            {
                "find": "Ângstrom",
                "replace": "Ångstrom",
                "rationale": "judgment call",
                "reviewer": "tester",
            }
        ]

        updated, applied = overrides.apply_overrides("1/100,000 Ângstrom unit", entries)

        self.assertEqual("1/100,000 Ångstrom unit", updated)
        self.assertEqual(1, len(applied))
        self.assertEqual("Ângstrom", applied[0]["find"])
        self.assertEqual("Ångstrom", applied[0]["replace"])
        self.assertEqual("judgment call", applied[0]["rationale"])
        self.assertEqual("tester", applied[0]["reviewer"])
        self.assertEqual(1, applied[0]["count"])

    def test_non_matching_entry_warns_and_is_skipped(self):
        entries = [{"find": "not present", "replace": "X"}]

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            updated, applied = overrides.apply_overrides("clean body", entries)

        self.assertEqual("clean body", updated)
        self.assertEqual([], applied)
        self.assertEqual(1, len(caught))
        self.assertIn("not present", str(caught[0].message))

    def test_no_entries_returns_body_unchanged(self):
        body = "unchanged body"

        updated, applied = overrides.apply_overrides(body, [])

        self.assertIs(body, updated)
        self.assertEqual([], applied)

    def test_multiple_occurrences_are_counted(self):
        entries = [{"find": "foo", "replace": "bar"}]

        updated, applied = overrides.apply_overrides("foo and foo again", entries)

        self.assertEqual("bar and bar again", updated)
        self.assertEqual(2, applied[0]["count"])


class LoadOverridesTest(unittest.TestCase):
    """Tests for loading the versioned per-collection override files."""

    def test_missing_collection_returns_empty(self):
        self.assertEqual({}, overrides.load_overrides("no_such_collection"))

    def test_seed_angstrom_override_is_present(self):
        loaded = overrides.load_overrides("mass_quantities")

        self.assertIn("f_o_b_venus__bond", loaded)
        entry = loaded["f_o_b_venus__bond"][0]
        self.assertEqual("Ângstrom", entry["find"])
        self.assertEqual("Ångstrom", entry["replace"])
        self.assertTrue(entry["rationale"])

    def test_override_files_are_valid_json_keyed_by_story(self):
        for path in overrides.OVERRIDES_DIR.glob("*.json"):
            with self.subTest(path=path.name):
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertIsInstance(data, dict)
                for entries in data.values():
                    self.assertIsInstance(entries, list)
                    for entry in entries:
                        self.assertIn("find", entry)
                        self.assertIn("replace", entry)


class NormalizeStoryDictOverridesTest(unittest.TestCase):
    """Tests for override integration in the normalization hook."""

    def test_seed_override_applied_during_normalization(self):
        data = {
            "name": "F.O.B. Venus",
            "body": "rays go down to 1/100,000\nÂngstrom units",
            "metadata": {"author": "Bond"},
        }

        result = normalization.normalize_story_dict(
            data, collection="mass_quantities", story_id="f_o_b_venus__bond"
        )

        self.assertIn("Ångstrom", result["body"])
        self.assertNotIn("Ângstrom", result["body"])
        provenance = result["metadata"]["normalization"]
        self.assertEqual(overrides.OVERRIDE_SOURCE, provenance["override_source"])
        self.assertEqual("Ângstrom", provenance["overrides_applied"][0]["find"])

    def test_rules_and_overrides_compose_with_separate_provenance(self):
        data = {
            "name": "Mixed",
            "body": "blas√© eyes near 1/100,000\nÂngstrom",
            "metadata": {"author": "X"},
        }

        result = normalization.normalize_story_dict(
            data, collection="mass_quantities", story_id="f_o_b_venus__bond"
        )

        self.assertEqual("blasé eyes near 1/100,000\nÅngstrom", result["body"])
        provenance = result["metadata"]["normalization"]
        self.assertIn("rules_applied", provenance)
        self.assertIn("overrides_applied", provenance)

    def test_without_collection_and_story_id_overrides_are_skipped(self):
        data = {
            "name": "F.O.B. Venus",
            "body": "1/100,000\nÂngstrom units",
            "metadata": {"author": "Bond"},
        }

        result = normalization.normalize_story_dict(data)

        # No rule matches bare "Ân", and overrides are not consulted, so the
        # body and metadata pass through untouched.
        self.assertEqual("1/100,000\nÂngstrom units", result["body"])
        self.assertNotIn("normalization", result["metadata"])

    def test_override_normalization_is_deterministic(self):
        def fresh():
            return {
                "name": "F.O.B. Venus",
                "body": "1/100,000\nÂngstrom units",
                "metadata": {"author": "Bond"},
            }

        first = normalization.normalize_story_dict(
            fresh(), collection="mass_quantities", story_id="f_o_b_venus__bond"
        )
        second = normalization.normalize_story_dict(
            fresh(), collection="mass_quantities", story_id="f_o_b_venus__bond"
        )

        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
