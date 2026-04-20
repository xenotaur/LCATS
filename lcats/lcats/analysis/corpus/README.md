# Corpus Analysis Documentation

## Unicode / special-character human review decisions (library usage)

The corpus analysis package now includes a library-first decision model for
human-reviewed Unicode/special-character findings and conservative repair
proposals.

### What this supports

- Mark a repair proposal as:
  - `approved`
  - `rejected`
  - `unresolved`
- Mark repeated special-character findings as allowed/expected so they are
  suppressed in later reporting/proposal generation.
- Keep decisions serializable (`to_dict` / `from_dict`) for future config or
  persistence workflows.

### Modules

- `lcats.analysis.corpus.review`: decision model + application helpers
- `lcats.analysis.corpus.specials`: optional decision-aware suppression in
  reporting helpers
- `lcats.analysis.corpus.repairs`: optional decision-aware suppression and
  reviewed suggestion grouping

### Minimal example

```python
from lcats.analysis.corpus import repairs
from lcats.analysis.corpus import review

text = "Broken token â€™ and accepted symbol √"

decision_store = review.ReviewDecisionStore(
    repair_decisions=(
        review.RepairReviewDecision(
            rule_id="mojibake-right-single-quote",
            original_text="â€™",
            replacement_text="’",
            decision=review.APPROVED,
            rationale="Known encoding fix in this corpus.",
        ),
    ),
    allowed_special_cases=(
        review.AllowedSpecialCase(
            character="√",
            classification="review_needed",
            evidence_contains="residual-review",
            rationale="Expected in mathematical excerpts.",
        ),
    ),
)

# Conservative: suggestions are still non-destructive proposals only.
grouped = repairs.suggest_reviewed_repairs_for_text(
    text,
    decision_store=decision_store,
)

print(len(grouped.approved), len(grouped.rejected), len(grouped.unresolved))
```

### Notes

- Review decisions do **not** rewrite corpora by default.
- Decisions are applied in-memory to findings/reports/proposals.
- Interactive UI/editor workflows are intentionally deferred.
