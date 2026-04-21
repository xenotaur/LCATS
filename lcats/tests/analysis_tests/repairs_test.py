"""Unit tests for lcats.analysis.corpus.repairs."""

import json
import unittest

from parameterized import parameterized

from lcats.analysis.corpus import repairs
from lcats.analysis.corpus import review
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

    def test_suggestions_to_span_operations_exposes_explicit_fields(self):
        suggestion = repairs.RepairSuggestion(
            rule_id="mojibake-right-single-quote",
            start=2,
            end=5,
            original_text="â€™",
            replacement_text="’",
            finding_offset=2,
            evidence="rule=mojibake-pattern; fragment=â€™",
            confidence="high",
            rationale="Broken UTF-8 right single quote sequence.",
        )

        operations = repairs.suggestions_to_span_operations([suggestion])

        self.assertEqual(1, len(operations))
        operation = operations[0]
        self.assertEqual("replace", operation.operation)
        self.assertEqual(2, operation.start)
        self.assertEqual(5, operation.end)
        self.assertEqual("â€™", operation.original_text)
        self.assertEqual("’", operation.replacement_text)
        self.assertEqual("mojibake-right-single-quote", operation.rule_id)
        self.assertIn("fragment=â€™", operation.evidence)
        self.assertEqual("high", operation.confidence)

    def test_apply_span_operations_applies_in_deterministic_order(self):
        text = "â€™-â€¦"
        operations = [
            repairs.SpanRepairOperation(
                operation="replace",
                start=4,
                end=7,
                original_text="â€¦",
                replacement_text="…",
                rule_id="mojibake-ellipsis",
                evidence="rule=mojibake-pattern; fragment=â€¦",
            ),
            repairs.SpanRepairOperation(
                operation="replace",
                start=0,
                end=3,
                original_text="â€™",
                replacement_text="’",
                rule_id="mojibake-right-single-quote",
                evidence="rule=mojibake-pattern; fragment=â€™",
            ),
        ]

        updated = repairs.apply_span_operations(text, operations)

        self.assertEqual("’-…", updated)

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
        text = "â€™"
        operations = [
            repairs.SpanRepairOperation(
                operation="delete",
                start=0,
                end=2,
                original_text="â€",
                replacement_text="",
                rule_id="unsupported-delete",
                evidence="unsupported-op",
            ),
            repairs.SpanRepairOperation(
                operation="replace",
                start=0,
                end=3,
                original_text="â€™",
                replacement_text="’",
                rule_id="mojibake-right-single-quote",
                evidence="rule=mojibake-pattern; fragment=â€™",
            ),
        ]

        updated = repairs.apply_span_operations(text, operations)

        self.assertEqual("’", updated)

    def test_suggest_repairs_for_text_uses_classifier_and_rules(self):
        suggestions = repairs.suggest_repairs_for_text("Text â€” sample")

        self.assertEqual(1, len(suggestions))
        suggestion = suggestions[0]
        self.assertEqual("â€”", suggestion.original_text)
        self.assertEqual("—", suggestion.replacement_text)
        self.assertEqual("high", suggestion.confidence)

    def test_suggest_repairs_for_text_applies_allowed_special_review_rules(self):
        text = "Text â€” sample"
        decision_store = review.ReviewDecisionStore(
            allowed_special_cases=(
                review.AllowedSpecialCase(
                    classification="likely_repairable",
                    evidence_contains="fragment=â€”",
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
                rule_id="mojibake-ellipsis",
                start=12,
                end=15,
                original_text="â€¦",
                replacement_text="…",
                finding_offset=13,
                evidence="rule=mojibake-pattern; fragment=â€¦",
                confidence="high",
                rationale="Broken UTF-8 ellipsis sequence.",
            )
        ]

        entries = repairs.build_dry_run_plan_entries(suggestions)

        self.assertEqual(1, len(entries))
        entry = entries[0]
        self.assertEqual(12, entry.start)
        self.assertEqual(15, entry.end)
        self.assertEqual("â€¦", entry.original_text)
        self.assertEqual("…", entry.replacement_text)
        self.assertEqual("mojibake-ellipsis", entry.rule_id)
        self.assertIn("fragment=â€¦", entry.evidence)
        self.assertEqual("Broken UTF-8 ellipsis sequence.", entry.rationale)
        self.assertEqual(13, entry.finding_offset)

    def test_build_dry_run_jsonl_report_is_machine_parseable(self):
        suggestions = [
            repairs.RepairSuggestion(
                rule_id="mojibake-em-dash",
                start=5,
                end=8,
                original_text="â€”",
                replacement_text="—",
                finding_offset=6,
                evidence="rule=mojibake-pattern; fragment=â€”",
                confidence="high",
                rationale="Broken UTF-8 em dash sequence.",
            )
        ]

        report = repairs.build_dry_run_jsonl_report(suggestions, path="story.txt")

        lines = report.splitlines()
        self.assertEqual(1, len(lines))
        payload = json.loads(lines[0])
        self.assertEqual("story.txt", payload["path"])
        self.assertEqual("â€”", payload["original_text"])
        self.assertEqual("—", payload["replacement_text"])
        self.assertEqual("mojibake-em-dash", payload["rule_id"])

    def test_suggest_reviewed_repairs_for_text_groups_decision_states(self):
        text = "Text â€” and â€¦ sample"
        decision_store = review.ReviewDecisionStore(
            repair_decisions=(
                review.RepairReviewDecision(
                    rule_id="mojibake-em-dash",
                    original_text="â€”",
                    replacement_text="—",
                    decision=review.APPROVED,
                ),
                review.RepairReviewDecision(
                    rule_id="mojibake-ellipsis",
                    original_text="â€¦",
                    replacement_text="…",
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
