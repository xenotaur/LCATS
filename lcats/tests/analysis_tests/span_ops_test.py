"""Unit tests for canonical span operation models."""

import json
import unittest

from lcats.analysis.corpus import repairs
from lcats.analysis.corpus import span_ops


class SpanOpsTest(unittest.TestCase):
    """Tests for deterministic canonical span operations."""

    def test_serialize_deserialize_round_trip(self):
        operation = span_ops.SpanOperation(
            operation_id="spanop-000000-demo",
            operation_type=span_ops.REPLACE_SPAN,
            start=2,
            end=5,
            replacement_text="’",
            original_text="â€™",
            provenance=span_ops.SpanOperationProvenance(
                rule_id="mojibake-right-single-quote",
                source="repair_suggestion",
                finding_offset=3,
                evidence="rule=mojibake-pattern; fragment=â€™",
                rationale="Broken UTF-8 right single quote sequence.",
                confidence="high",
            ),
        )

        payload = span_ops.serialize_operations([operation])
        loaded = span_ops.deserialize_operations(payload)

        self.assertEqual([operation], loaded)
        json.loads(payload)

    def test_validate_operation_set_rejects_invalid_spans(self):
        operation = span_ops.SpanOperation(
            operation_id="invalid",
            operation_type=span_ops.REPLACE_SPAN,
            start=8,
            end=3,
            replacement_text="x",
            original_text="y",
            provenance=span_ops.SpanOperationProvenance(
                rule_id="invalid",
                source="test",
                finding_offset=0,
                evidence="e",
            ),
        )

        with self.assertRaises(ValueError):
            span_ops.validate_operation_set([operation])

    def test_validate_operation_set_rejects_overlapping_spans(self):
        operations = [
            span_ops.SpanOperation(
                operation_id="a",
                operation_type=span_ops.REPLACE_SPAN,
                start=1,
                end=4,
                replacement_text="A",
                original_text="bcd",
                provenance=span_ops.SpanOperationProvenance(
                    rule_id="a",
                    source="test",
                    finding_offset=1,
                    evidence="a",
                ),
            ),
            span_ops.SpanOperation(
                operation_id="b",
                operation_type=span_ops.REPLACE_SPAN,
                start=3,
                end=5,
                replacement_text="B",
                original_text="de",
                provenance=span_ops.SpanOperationProvenance(
                    rule_id="b",
                    source="test",
                    finding_offset=3,
                    evidence="b",
                ),
            ),
        ]

        with self.assertRaises(ValueError):
            span_ops.validate_operation_set(operations)

    def test_from_repair_suggestions_is_deterministic(self):
        first = repairs.RepairSuggestion(
            rule_id="rule-b",
            start=6,
            end=9,
            original_text="â€¦",
            replacement_text="…",
            finding_offset=7,
            evidence="rule=mojibake-pattern; fragment=â€¦",
            rationale="ellipsis",
        )
        second = repairs.RepairSuggestion(
            rule_id="rule-a",
            start=0,
            end=3,
            original_text="â€™",
            replacement_text="’",
            finding_offset=0,
            evidence="rule=mojibake-pattern; fragment=â€™",
            rationale="quote",
        )

        run_one = span_ops.from_repair_suggestions([first, second])
        run_two = span_ops.from_repair_suggestions([second, first])

        self.assertEqual(run_one, run_two)
        self.assertEqual(
            ["spanop-000000-rule-a", "spanop-000001-rule-b"],
            [operation.operation_id for operation in run_one],
        )

    def test_ordering_rules_are_stable(self):
        replace = span_ops.SpanOperation(
            operation_id="replace",
            operation_type=span_ops.REPLACE_SPAN,
            start=2,
            end=4,
            replacement_text="X",
            original_text="ab",
            provenance=span_ops.SpanOperationProvenance(
                rule_id="replace",
                source="test",
                finding_offset=2,
                evidence="replace",
            ),
        )
        remove = span_ops.SpanOperation(
            operation_id="remove",
            operation_type=span_ops.REMOVE_SPAN,
            start=2,
            end=4,
            replacement_text="",
            original_text="ab",
            provenance=span_ops.SpanOperationProvenance(
                rule_id="remove",
                source="test",
                finding_offset=2,
                evidence="remove",
            ),
        )

        ordered = span_ops.sort_operations([replace, remove])

        self.assertEqual(["remove", "replace"], [op.operation_id for op in ordered])

    def test_repairs_bridge_to_canonical_operations_preserves_provenance(self):
        suggestion = repairs.RepairSuggestion(
            rule_id="mojibake-right-single-quote",
            start=1,
            end=4,
            original_text="â€™",
            replacement_text="’",
            finding_offset=2,
            evidence="rule=mojibake-pattern; fragment=â€™",
            rationale="Broken UTF-8 right single quote sequence.",
            confidence="high",
        )

        operations = repairs.suggestions_to_canonical_span_operations([suggestion])

        self.assertEqual(1, len(operations))
        operation = operations[0]
        self.assertEqual(span_ops.REPLACE_SPAN, operation.operation_type)
        self.assertEqual("mojibake-right-single-quote", operation.provenance.rule_id)
        self.assertEqual(2, operation.provenance.finding_offset)
        self.assertIn("fragment=â€™", operation.provenance.evidence)


if __name__ == "__main__":
    unittest.main()
