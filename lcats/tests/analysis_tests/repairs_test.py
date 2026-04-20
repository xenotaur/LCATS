"""Unit tests for lcats.analysis.corpus.repairs."""

import unittest

from parameterized import parameterized

from lcats.analysis.corpus import repairs
from lcats.analysis.corpus import specials


class RepairsTest(unittest.TestCase):
    """Tests for repair suggestions built from classified findings."""

    @parameterized.expand(
        [
            ("â€™", "’", "mojibake-right-single-quote"),
            ("â€œ", "“", "mojibake-left-double-quote"),
            ("â€\u009d", "”", "mojibake-right-double-quote"),
            ("â€“", "–", "mojibake-en-dash"),
            ("â€”", "—", "mojibake-em-dash"),
            ("â€¦", "…", "mojibake-ellipsis"),
        ]
    )
    def test_suggest_repairs_maps_known_fragments(self, fragment, replacement, rule_id):
        text = f"A {fragment} B"
        findings = list(
            specials.iter_special_characters(
                text=text,
                allow_smart=False,
                excluded=set(),
                allowlist=specials.AllowlistConfig(),
                context=3,
                name_width=0,
            )
        )

        suggestions = repairs.suggest_repairs(text, findings)

        self.assertEqual(1, len(suggestions))
        suggestion = suggestions[0]
        self.assertEqual(rule_id, suggestion.rule_id)
        self.assertEqual(fragment, suggestion.original_text)
        self.assertEqual(replacement, suggestion.replacement_text)

    def test_suggest_repairs_preserves_audit_fields(self):
        text = "Broken â€™ punctuation"
        findings = list(
            specials.iter_special_characters(
                text=text,
                allow_smart=False,
                excluded=set(),
                allowlist=specials.AllowlistConfig(),
                context=4,
                name_width=0,
            )
        )

        suggestions = repairs.suggest_repairs(text, findings)

        self.assertEqual(1, len(suggestions))
        suggestion = suggestions[0]
        self.assertEqual("â€™", suggestion.original_text)
        self.assertEqual("’", suggestion.replacement_text)
        self.assertEqual(
            text[suggestion.start : suggestion.end], suggestion.original_text
        )
        self.assertIn("rule=mojibake-pattern", suggestion.evidence)

    def test_suggest_repairs_ignores_likely_good_cases(self):
        text = "A naïve sentence"
        findings = list(
            specials.iter_special_characters(
                text=text,
                allow_smart=False,
                excluded=set(),
                allowlist=specials.AllowlistConfig(),
                context=4,
                name_width=0,
            )
        )

        suggestions = repairs.suggest_repairs(text, findings)

        self.assertEqual([], suggestions)

    def test_suggest_repairs_ignores_unsupported_fragments(self):
        finding = specials.SpecialCharacter(
            character="â",
            codepoint="U+00E2",
            unicode_name="LATIN SMALL LETTER A WITH CIRCUMFLEX",
            occurrence_index=1,
            offset=4,
            context="aaâbb",
            classification="likely_repairable",
            evidence="rule=mojibake-pattern; fragment=â‚¬",
        )

        suggestions = repairs.suggest_repairs("aaâ‚¬bb", [finding])

        self.assertEqual([], suggestions)

    def test_apply_repair_suggestions_applies_only_matching_spans(self):
        text = "Broken â€™ and â€¦"
        suggestions = [
            repairs.RepairSuggestion(
                rule_id="first",
                start=7,
                end=10,
                original_text="â€™",
                replacement_text="’",
                finding_offset=7,
                evidence="rule=mojibake-pattern; fragment=â€™",
            ),
            repairs.RepairSuggestion(
                rule_id="mismatch",
                start=15,
                end=18,
                original_text="BAD",
                replacement_text="X",
                finding_offset=15,
                evidence="rule=mojibake-pattern; fragment=â€¦",
            ),
        ]

        updated = repairs.apply_repair_suggestions(text, suggestions)

        self.assertEqual("Broken ’ and â€¦", updated)


if __name__ == "__main__":
    unittest.main()
