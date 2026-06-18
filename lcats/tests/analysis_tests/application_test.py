"""Unit tests for approved span operation application."""

import json
import unittest

from lcats.analysis.corpus import application
from lcats.analysis.corpus import review
from lcats.analysis.corpus import span_ops


class ApplicationTest(unittest.TestCase):
    """Tests for non-destructive reviewed operation application."""

    def _operation(
        self,
        operation_id="spanop-000001",
        start=6,
        end=9,
        original_text="â€™",
        replacement_text="’",
        operation_type=span_ops.REPLACE_SPAN,
    ):
        return span_ops.SpanOperation(
            operation_id=operation_id,
            operation_type=operation_type,
            start=start,
            end=end,
            replacement_text=replacement_text,
            original_text=original_text,
            provenance=span_ops.SpanOperationProvenance(
                rule_id="mojibake-right-single-quote",
                source="unit_test",
                finding_offset=start,
                evidence=f"fragment={original_text}",
                rationale="Broken punctuation sequence.",
            ),
        )

    def _decision(self, operation, state=review.APPROVED, override=None):
        return review.SpanOperationReviewDecision(
            decision_id=f"decision-{operation.operation_id}-{state}",
            span_operation_id=operation.operation_id,
            state=state,
            reviewer="reviewer@example.test",
            rationale=f"Rationale for {state}",
            reviewed_operation=operation,
            audit_metadata=review.ReviewAuditMetadata(source="unit_test"),
            override=override,
        )

    def test_eligibility_states_are_applied_or_skipped(self):
        text = "Alice â€™ Bob â€¦ Carol â€“ Dana"
        approved = self._operation("approved", 6, 9, "â€™", "’")
        overridden = self._operation("overridden", 14, 17, "â€¦", "…")
        replacement = self._operation("override-replacement", 14, 17, "â€¦", "...")
        pending = self._operation("pending", 24, 27, "â€“", "–")
        rejected = self._operation("rejected", 24, 27, "â€“", "-")

        result = application.apply_reviewed_operations(
            text,
            [
                self._decision(pending, review.PENDING),
                self._decision(rejected, review.REJECTED),
                self._decision(approved, review.APPROVED),
                self._decision(
                    overridden,
                    review.OVERRIDDEN,
                    review.SpanOperationOverride(
                        replacement_operation=replacement,
                        rationale="Use source-specific ellipsis style.",
                    ),
                ),
            ],
        )

        self.assertTrue(result.success)
        self.assertEqual("Alice ’ Bob ... Carol â€“ Dana", result.transformed_text)
        self.assertEqual(text, result.original_text)
        self.assertEqual(text, "Alice â€™ Bob â€¦ Carol â€“ Dana")
        self.assertEqual(
            ["approved", "override-replacement"],
            [r.operation_id for r in result.applied],
        )
        self.assertEqual(
            ["rejected", "pending"], [r.operation_id for r in result.skipped]
        )
        self.assertTrue(result.applied[1].override_used)
        json.dumps(result.to_dict())

    def test_application_is_deterministic_for_input_order(self):
        text = "A â€™ B â€¦ C"
        quote = self._operation("quote", 2, 5, "â€™", "’")
        ellipsis = self._operation(
            "ellipsis",
            8,
            11,
            "â€¦",
            "…",
        )
        first = application.apply_reviewed_operations(
            text,
            [self._decision(ellipsis), self._decision(quote)],
        )
        second = application.apply_reviewed_operations(
            text,
            [self._decision(quote), self._decision(ellipsis)],
        )

        self.assertTrue(first.success)
        self.assertTrue(second.success)
        self.assertEqual(first.transformed_text, second.transformed_text)
        self.assertEqual(["quote", "ellipsis"], [r.operation_id for r in first.applied])
        self.assertEqual(
            ["quote", "ellipsis"], [r.operation_id for r in second.applied]
        )

    def test_overlapping_operations_fail_without_partial_output(self):
        text = "abcdef"
        first = self._operation("first", 1, 4, "bcd", "BCD")
        second = self._operation("second", 3, 5, "de", "DE")

        result = application.apply_reviewed_operations(
            text,
            [self._decision(first), self._decision(second)],
        )

        self.assertFalse(result.success)
        self.assertEqual(text, result.transformed_text)
        self.assertIn("overlapping spans", result.failures[0].message)

    def test_invalid_span_fails_without_partial_output(self):
        text = "abc"
        operation = self._operation("invalid", 1, 5, "bcde", "BCDE")

        result = application.apply_reviewed_operations(
            text, [self._decision(operation)]
        )

        self.assertFalse(result.success)
        self.assertEqual(text, result.transformed_text)
        self.assertIn("exceeds text length", result.failures[0].message)

    def test_original_text_mismatch_fails_without_partial_output(self):
        text = "abc"
        operation = self._operation("mismatch", 1, 3, "xy", "XY")

        result = application.apply_reviewed_operations(
            text, [self._decision(operation)]
        )

        self.assertFalse(result.success)
        self.assertEqual(text, result.transformed_text)
        self.assertIn("does not match", result.failures[0].message)

    def test_insert_and_remove_operations_apply_non_destructively(self):
        text = "abcd"
        insert = self._operation(
            "insert",
            2,
            2,
            "",
            "X",
            span_ops.INSERT_SPAN,
        )
        remove = self._operation(
            "remove",
            3,
            4,
            "d",
            "",
            span_ops.REMOVE_SPAN,
        )

        result = application.apply_reviewed_operations(
            text,
            [self._decision(remove), self._decision(insert)],
        )

        self.assertTrue(result.success)
        self.assertEqual("abXc", result.transformed_text)
        self.assertEqual("abcd", text)


if __name__ == "__main__":
    unittest.main()
