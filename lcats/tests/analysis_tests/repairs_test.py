"""Unit tests for lcats.analysis.corpus.repairs."""

import json
import unittest

from parameterized import parameterized

from lcats.analysis.corpus import repairs
from lcats.analysis.corpus import review
from lcats.analysis.corpus import specials


class RepairsTest(unittest.TestCase):
    """Tests for repair suggestions built from classified findings."""

    # Each context below is sampled byte-for-byte from a real story in the
    # live data/ tree (WI-RULES-0016 measurement, 2026-07-13); do not replace
    # with synthetic text — rule bytes must match real corpus bytes.
    @parameterized.expand(
        [
            ("them a resumÃ©.", "Ã©", "é", "mojibake-latin1-e-acute"),
            ("An aÃ«rial toehold", "Ã«", "ë", "mojibake-latin1-e-diaeresis"),
            ("Regardez des vÃªtements!", "Ãª", "ê", "mojibake-latin1-e-circumflex"),
            ("His uncoÃ¶rdinated hands", "Ã¶", "ö", "mojibake-latin1-o-diaeresis"),
            ("she said naÃ¯vely.", "Ã¯", "ï", "mojibake-latin1-i-diaeresis"),
            ("naturally or _Ã la lobster_", "Ã ", "à", "mojibake-latin1-a-grave"),
            ("stay off the 60Â° below", "Â°", "°", "mojibake-latin1-degree-sign"),
            ("she pay 90Â¢ for", "Â¢", "¢", "mojibake-latin1-cent-sign"),
            ('swear by it on Merop√©."', "√©", "é", "mojibake-macroman-e-acute"),
            ("Its _fin de si√®cle_ beauty", "√®", "è", "mojibake-macroman-e-grave"),
            ("The little se√±orita,", "√±", "ñ", "mojibake-macroman-n-tilde"),
            ("them, Tha√ºle?", "√º", "ü", "mojibake-macroman-u-diaeresis"),
            ("trumpets of Ragnar√∂k.", "√∂", "ö", "mojibake-macroman-o-diaeresis"),
            ("work on Niccol√≤ Tartaglia", "√≤", "ò", "mojibake-macroman-o-grave"),
        ]
    )
    def test_suggest_repairs_maps_known_fragments(
        self, text, fragment, replacement, rule_id
    ):
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

    @parameterized.expand(
        [
            ("legacy_cp1252_quote", "A broken â€™ token"),
            ("legacy_cp1252_ellipsis", "Example â€¦ token"),
            ("french_circumflex_words", "The bête noire ate the pâte."),
        ]
    )
    def test_suggest_repairs_has_no_rules_for_unmeasured_fragments(self, _name, text):
        """cp1252-form sequences occur zero times in the measured corpus and
        circumflex letters in French words are legitimate text; neither may
        produce a proposal (WI-RULES-0016 acceptance)."""
        suggestions = repairs.suggest_repairs_for_text(text)

        self.assertEqual([], suggestions)

    def test_evidence_fragment_round_trip_preserves_trailing_whitespace(self):
        """Regression: 'Ã' + NBSP ('à' mojibake) must survive the evidence
        string round trip — str.strip() would silently delete the NBSP and
        the a-grave rule would never fire on real corpus text."""
        text = "naturally or _Ã la lobster_"

        suggestions = repairs.suggest_repairs_for_text(text)

        self.assertEqual(1, len(suggestions))
        self.assertEqual("mojibake-latin1-a-grave", suggestions[0].rule_id)
        self.assertEqual("Ã ", suggestions[0].original_text)

    def test_suggest_repairs_preserves_audit_fields(self):
        text = "so he could give them a resumÃ©."
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
        self.assertEqual("Ã©", suggestion.original_text)
        self.assertEqual("é", suggestion.replacement_text)
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

    def test_suggest_repairs_ignores_review_needed_cases(self):
        finding = specials.SpecialCharacter(
            character="√",
            codepoint="U+221A",
            unicode_name="SQUARE ROOT",
            occurrence_index=1,
            offset=3,
            context="a√b",
            classification="review_needed",
            evidence="rule=residual-review; unicode_name=SQUARE ROOT",
        )

        suggestions = repairs.suggest_repairs("a√b", [finding])

        self.assertEqual([], suggestions)

    def test_apply_repair_suggestions_applies_only_matching_spans(self):
        text = "Broken Ã© and √∂"
        suggestions = [
            repairs.RepairSuggestion(
                rule_id="first",
                start=7,
                end=9,
                original_text="Ã©",
                replacement_text="é",
                finding_offset=7,
                evidence="rule=mojibake-pattern; fragment=Ã©",
            ),
            repairs.RepairSuggestion(
                rule_id="mismatch",
                start=14,
                end=16,
                original_text="BAD",
                replacement_text="X",
                finding_offset=14,
                evidence="rule=mojibake-pattern; fragment=√∂",
            ),
        ]

        updated = repairs.apply_repair_suggestions(text, suggestions)

        self.assertEqual("Broken é and √∂", updated)

    def test_suggestions_to_span_operations_exposes_explicit_fields(self):
        suggestion = repairs.RepairSuggestion(
            rule_id="mojibake-latin1-e-acute",
            start=2,
            end=4,
            original_text="Ã©",
            replacement_text="é",
            finding_offset=2,
            evidence="rule=mojibake-pattern; fragment=Ã©",
            confidence="high",
            rationale="UTF-8 'é' decoded as Latin-1.",
        )

        operations = repairs.suggestions_to_span_operations([suggestion])

        self.assertEqual(1, len(operations))
        operation = operations[0]
        self.assertEqual("replace", operation.operation)
        self.assertEqual(2, operation.start)
        self.assertEqual(4, operation.end)
        self.assertEqual("Ã©", operation.original_text)
        self.assertEqual("é", operation.replacement_text)
        self.assertEqual("mojibake-latin1-e-acute", operation.rule_id)
        self.assertIn("fragment=Ã©", operation.evidence)
        self.assertEqual("high", operation.confidence)

    def test_apply_span_operations_applies_in_deterministic_order(self):
        text = "Ã©-√∂"
        operations = [
            repairs.SpanRepairOperation(
                operation="replace",
                start=3,
                end=5,
                original_text="√∂",
                replacement_text="ö",
                rule_id="mojibake-macroman-o-diaeresis",
                evidence="rule=mojibake-pattern; fragment=√∂",
            ),
            repairs.SpanRepairOperation(
                operation="replace",
                start=0,
                end=2,
                original_text="Ã©",
                replacement_text="é",
                rule_id="mojibake-latin1-e-acute",
                evidence="rule=mojibake-pattern; fragment=Ã©",
            ),
        ]

        updated = repairs.apply_span_operations(text, operations)

        self.assertEqual("é-ö", updated)

    def test_apply_span_operations_returns_original_for_overlap(self):
        text = "abcdef"
        operations = [
            repairs.SpanRepairOperation(
                operation="replace",
                start=1,
                end=4,
                original_text="bcd",
                replacement_text="X",
                rule_id="rule-a",
                evidence="overlap-test-a",
            ),
            repairs.SpanRepairOperation(
                operation="replace",
                start=3,
                end=5,
                original_text="de",
                replacement_text="Y",
                rule_id="rule-b",
                evidence="overlap-test-b",
            ),
        ]

        updated = repairs.apply_span_operations(text, operations)

        self.assertEqual(text, updated)

    def test_apply_span_operations_ignores_non_replace_in_overlap_precheck(self):
        text = "Ã©"
        operations = [
            repairs.SpanRepairOperation(
                operation="delete",
                start=0,
                end=1,
                original_text="Ã",
                replacement_text="",
                rule_id="unsupported-delete",
                evidence="unsupported-op",
            ),
            repairs.SpanRepairOperation(
                operation="replace",
                start=0,
                end=2,
                original_text="Ã©",
                replacement_text="é",
                rule_id="mojibake-latin1-e-acute",
                evidence="rule=mojibake-pattern; fragment=Ã©",
            ),
        ]

        updated = repairs.apply_span_operations(text, operations)

        self.assertEqual("é", updated)

    def test_suggest_repairs_for_text_uses_classifier_and_rules(self):
        suggestions = repairs.suggest_repairs_for_text(
            "the screaming trumpets of Ragnar√∂k."
        )

        self.assertEqual(1, len(suggestions))
        suggestion = suggestions[0]
        self.assertEqual("√∂", suggestion.original_text)
        self.assertEqual("ö", suggestion.replacement_text)
        self.assertEqual("high", suggestion.confidence)

    def test_suggest_repairs_for_text_applies_allowed_special_review_rules(self):
        text = "the screaming trumpets of Ragnar√∂k."
        decision_store = review.ReviewDecisionStore(
            allowed_special_cases=(
                review.AllowedSpecialCase(
                    classification="likely_repairable",
                    evidence_contains="fragment=√∂",
                ),
            )
        )

        suggestions = repairs.suggest_repairs_for_text(
            text,
            decision_store=decision_store,
        )

        self.assertEqual([], suggestions)

    def test_build_dry_run_plan_entries_preserves_rationale_and_location(self):
        suggestions = [
            repairs.RepairSuggestion(
                rule_id="mojibake-macroman-o-diaeresis",
                start=12,
                end=14,
                original_text="√∂",
                replacement_text="ö",
                finding_offset=13,
                evidence="rule=mojibake-pattern; fragment=√∂",
                confidence="high",
                rationale="UTF-8 'ö' decoded as Mac-Roman.",
            )
        ]

        entries = repairs.build_dry_run_plan_entries(suggestions)

        self.assertEqual(1, len(entries))
        entry = entries[0]
        self.assertEqual(12, entry.start)
        self.assertEqual(14, entry.end)
        self.assertEqual("√∂", entry.original_text)
        self.assertEqual("ö", entry.replacement_text)
        self.assertEqual("mojibake-macroman-o-diaeresis", entry.rule_id)
        self.assertIn("fragment=√∂", entry.evidence)
        self.assertEqual("UTF-8 'ö' decoded as Mac-Roman.", entry.rationale)
        self.assertEqual(13, entry.finding_offset)

    def test_build_dry_run_jsonl_report_is_machine_parseable(self):
        suggestions = [
            repairs.RepairSuggestion(
                rule_id="mojibake-latin1-e-acute",
                start=5,
                end=7,
                original_text="Ã©",
                replacement_text="é",
                finding_offset=6,
                evidence="rule=mojibake-pattern; fragment=Ã©",
                confidence="high",
                rationale="UTF-8 'é' decoded as Latin-1.",
            )
        ]

        report = repairs.build_dry_run_jsonl_report(suggestions, path="story.txt")

        lines = report.splitlines()
        self.assertEqual(1, len(lines))
        payload = json.loads(lines[0])
        self.assertEqual("story.txt", payload["path"])
        self.assertEqual("Ã©", payload["original_text"])
        self.assertEqual("é", payload["replacement_text"])
        self.assertEqual("mojibake-latin1-e-acute", payload["rule_id"])

    def test_suggest_reviewed_repairs_for_text_groups_decision_states(self):
        text = "them a resumÃ©. stay off the 60Â° below"
        decision_store = review.ReviewDecisionStore(
            repair_decisions=(
                review.RepairReviewDecision(
                    rule_id="mojibake-latin1-e-acute",
                    original_text="Ã©",
                    replacement_text="é",
                    decision=review.APPROVED,
                ),
                review.RepairReviewDecision(
                    rule_id="mojibake-latin1-degree-sign",
                    original_text="Â°",
                    replacement_text="°",
                    decision=review.REJECTED,
                ),
            )
        )

        grouped = repairs.suggest_reviewed_repairs_for_text(
            text,
            decision_store=decision_store,
        )

        self.assertEqual(1, len(grouped.approved))
        self.assertEqual(1, len(grouped.rejected))
        self.assertEqual(0, len(grouped.unresolved))


if __name__ == "__main__":
    unittest.main()
