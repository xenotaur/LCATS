"""Unit tests for lcats.analysis.corpus.review."""

import json
import unittest

from lcats.analysis.corpus import repairs
from lcats.analysis.corpus import review
from lcats.analysis.corpus import specials


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


if __name__ == "__main__":
    unittest.main()
