"""Unit tests for lcats.analysis.corpus.review."""

import json
import unittest

from lcats.analysis.corpus import repairs
from lcats.analysis.corpus import review
from lcats.analysis.corpus import specials
from lcats.analysis.corpus import span_ops


class ReviewTest(unittest.TestCase):
    """Tests for human review decision models and helpers."""

    def test_review_decision_store_round_trip_json(self):
        decision_store = review.ReviewDecisionStore(
            repair_decisions=(
                review.RepairReviewDecision(
                    rule_id="mojibake-right-single-quote",
                    original_text="â€™",
                    replacement_text="’",
                    decision=review.APPROVED,
                    rationale="Team-approved conversion",
                ),
            ),
            allowed_special_cases=(
                review.AllowedSpecialCase(
                    character="√",
                    codepoint="U+221A",
                    classification="review_needed",
                    evidence_contains="residual-review",
                    rationale="Expected in formula corpus",
                ),
            ),
        )

        payload = decision_store.to_dict()
        json.dumps(payload)
        loaded = review.ReviewDecisionStore.from_dict(payload)

        self.assertEqual(decision_store, loaded)

    def test_apply_review_to_repairs_partitions_by_decision(self):
        approved = repairs.RepairSuggestion(
            rule_id="mojibake-right-single-quote",
            start=0,
            end=3,
            original_text="â€™",
            replacement_text="’",
            finding_offset=0,
            evidence="rule=mojibake-pattern; fragment=â€™",
        )
        rejected = repairs.RepairSuggestion(
            rule_id="mojibake-ellipsis",
            start=4,
            end=7,
            original_text="â€¦",
            replacement_text="…",
            finding_offset=4,
            evidence="rule=mojibake-pattern; fragment=â€¦",
        )
        unresolved = repairs.RepairSuggestion(
            rule_id="mojibake-en-dash",
            start=8,
            end=11,
            original_text="â€“",
            replacement_text="–",
            finding_offset=8,
            evidence="rule=mojibake-pattern; fragment=â€“",
        )
        decision_store = review.ReviewDecisionStore(
            repair_decisions=(
                review.RepairReviewDecision(
                    rule_id=approved.rule_id,
                    original_text=approved.original_text,
                    replacement_text=approved.replacement_text,
                    decision=review.APPROVED,
                ),
                review.RepairReviewDecision(
                    rule_id=rejected.rule_id,
                    original_text=rejected.original_text,
                    replacement_text=rejected.replacement_text,
                    decision=review.REJECTED,
                ),
            )
        )

        grouped = review.apply_review_to_repairs(
            [approved, rejected, unresolved],
            decision_store,
        )

        self.assertEqual((approved,), grouped.approved)
        self.assertEqual((rejected,), grouped.rejected)
        self.assertEqual((unresolved,), grouped.unresolved)

    def test_apply_review_to_specials_suppresses_allowed_findings(self):
        findings = [
            specials.SpecialCharacter(
                character="√",
                codepoint="U+221A",
                unicode_name="SQUARE ROOT",
                occurrence_index=1,
                offset=10,
                context="Contains √ symbol",
                classification="review_needed",
                evidence="rule=residual-review; unicode_name=SQUARE ROOT",
            ),
            specials.SpecialCharacter(
                character="©",
                codepoint="U+00A9",
                unicode_name="COPYRIGHT SIGN",
                occurrence_index=1,
                offset=15,
                context="Contains © symbol",
                classification="review_needed",
                evidence="rule=residual-review; unicode_name=COPYRIGHT SIGN",
            ),
        ]
        decision_store = review.ReviewDecisionStore(
            allowed_special_cases=(
                review.AllowedSpecialCase(
                    character="√",
                    classification="review_needed",
                    evidence_contains="residual-review",
                    rationale="Allowed for math excerpts",
                ),
            )
        )

        filtered = review.apply_review_to_specials(findings, decision_store)

        self.assertEqual(1, len(filtered))
        self.assertEqual("©", filtered[0].character)


class SpanOperationReviewTest(unittest.TestCase):
    """Tests for span-operation review decision semantics."""

    def _operation(self, operation_id="spanop-demo", replacement_text="’"):
        return span_ops.SpanOperation(
            operation_id=operation_id,
            operation_type=span_ops.REPLACE_SPAN,
            start=1,
            end=4,
            replacement_text=replacement_text,
            original_text="â€™",
            provenance=span_ops.SpanOperationProvenance(
                rule_id="mojibake-right-single-quote",
                source="repair_suggestion",
                finding_offset=1,
                evidence="rule=mojibake-pattern; fragment=â€™",
                rationale="Broken UTF-8 right single quote sequence.",
            ),
        )

    def _decision(self, state, override=None):
        operation = self._operation()
        return review.SpanOperationReviewDecision(
            decision_id=f"review-{state}",
            span_operation_id=operation.operation_id,
            state=state,
            reviewer="reviewer@example.test",
            rationale=f"Decision rationale for {state}",
            reviewed_operation=operation,
            audit_metadata=review.ReviewAuditMetadata(
                created_at="2026-06-16T00:00:00Z",
                updated_at="2026-06-16T00:00:00Z",
                source="unit_test",
                notes="deterministic audit metadata",
            ),
            override=override,
        )

    def test_decision_state_application_eligibility(self):
        replacement = self._operation("spanop-demo-override", "'")
        override = review.SpanOperationOverride(
            replacement_operation=replacement,
            rationale="Prefer ASCII apostrophe for this source.",
        )
        cases = [
            (review.PENDING, None, False),
            (review.APPROVED, None, True),
            (review.REJECTED, None, False),
            (review.OVERRIDDEN, override, True),
        ]

        for state, override_details, expected in cases:
            with self.subTest(state=state):
                decision = self._decision(state, override_details)

                actual = review.is_span_operation_review_eligible_for_application(
                    decision
                )

                self.assertEqual(expected, actual)

    def test_operation_for_application_uses_override_replacement(self):
        replacement = self._operation("spanop-demo-override", "'")
        decision = self._decision(
            review.OVERRIDDEN,
            review.SpanOperationOverride(
                replacement_operation=replacement,
                rationale="Reviewer supplied replacement operation.",
            ),
        )

        application_operation = review.operation_for_application(decision)

        self.assertEqual(self._operation(), decision.reviewed_operation)
        self.assertEqual(replacement, decision.override.replacement_operation)
        self.assertEqual(replacement, application_operation)

    def test_pending_and_rejected_operations_cannot_be_selected_for_application(self):
        for state in (review.PENDING, review.REJECTED):
            with self.subTest(state=state):
                decision = self._decision(state)

                with self.assertRaises(ValueError):
                    review.operation_for_application(decision)

    def test_review_decision_requires_rationale(self):
        for state in review.SPAN_OPERATION_REVIEW_STATES:
            with self.subTest(state=state):
                override = None
                if state == review.OVERRIDDEN:
                    override = review.SpanOperationOverride(
                        replacement_operation=self._operation(
                            "spanop-demo-override", "'"
                        ),
                        rationale="Override rationale.",
                    )
                decision = review.SpanOperationReviewDecision(
                    decision_id=f"review-{state}",
                    span_operation_id="spanop-demo",
                    state=state,
                    reviewer="reviewer@example.test",
                    rationale="",
                    reviewed_operation=self._operation(),
                    override=override,
                )

                with self.assertRaises(ValueError):
                    review.validate_span_operation_review_decision(decision)

    def test_overridden_decision_requires_override_rationale(self):
        decision = self._decision(
            review.OVERRIDDEN,
            review.SpanOperationOverride(
                replacement_operation=self._operation("spanop-demo-override", "'"),
                rationale="",
            ),
        )

        with self.assertRaises(ValueError):
            review.validate_span_operation_review_decision(decision)

    def test_deserialize_rejects_missing_rationale(self):
        decision = self._decision(review.APPROVED)
        payload = decision.to_dict()
        del payload["rationale"]

        with self.assertRaises(ValueError):
            review.SpanOperationReviewDecision.from_dict(payload)

    def test_span_operation_review_serialization_is_deterministically_ordered(self):
        first_operation = self._operation("spanop-a", "’")
        second_operation = span_ops.SpanOperation(
            operation_id="spanop-b",
            operation_type=span_ops.REPLACE_SPAN,
            start=8,
            end=11,
            replacement_text="…",
            original_text="â€¦",
            provenance=span_ops.SpanOperationProvenance(
                rule_id="mojibake-ellipsis",
                source="repair_suggestion",
                finding_offset=8,
                evidence="rule=mojibake-pattern; fragment=â€¦",
                rationale="Broken UTF-8 ellipsis sequence.",
            ),
        )
        first_decision = review.SpanOperationReviewDecision(
            decision_id="review-a",
            span_operation_id=first_operation.operation_id,
            state=review.APPROVED,
            reviewer="reviewer@example.test",
            rationale="Approve first operation.",
            reviewed_operation=first_operation,
        )
        second_decision = review.SpanOperationReviewDecision(
            decision_id="review-b",
            span_operation_id=second_operation.operation_id,
            state=review.APPROVED,
            reviewer="reviewer@example.test",
            rationale="Approve second operation.",
            reviewed_operation=second_operation,
        )

        run_one = review.serialize_span_operation_review_decisions(
            [second_decision, first_decision]
        )
        run_two = review.serialize_span_operation_review_decisions(
            [first_decision, second_decision]
        )

        self.assertEqual(run_one, run_two)
        loaded = review.deserialize_span_operation_review_decisions(run_one)
        self.assertEqual(
            ["review-a", "review-b"], [item.decision_id for item in loaded]
        )

    def test_span_operation_review_round_trip_preserves_auditability(self):
        replacement = self._operation("spanop-demo-override", "'")
        decision = self._decision(
            review.OVERRIDDEN,
            review.SpanOperationOverride(
                replacement_operation=replacement,
                rationale="Reviewer supplied replacement operation.",
            ),
        )

        payload = review.serialize_span_operation_review_decisions([decision])
        loaded = review.deserialize_span_operation_review_decisions(payload)

        json.loads(payload)
        self.assertEqual([decision], loaded)
        self.assertEqual("reviewer@example.test", loaded[0].reviewer)
        self.assertEqual(
            "Decision rationale for overridden",
            loaded[0].rationale,
        )
        self.assertEqual(self._operation(), loaded[0].reviewed_operation)
        self.assertEqual(replacement, loaded[0].override.replacement_operation)


if __name__ == "__main__":
    unittest.main()
