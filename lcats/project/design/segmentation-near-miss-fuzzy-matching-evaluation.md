# Segmentation Near-Miss Fuzzy Matching Evaluation

Date: 2026-08-21

Related work:

- `WI-SEGMENT-0069` classified the original segmentation alignment failures and
  identified near-miss quoting as 10 of 21 alignment errors.
- `WI-SEGMENT-0070` fixed only paragraph-marker leakage and quote/dash
  typography mismatches.
- `WI-SEGMENT-0071` produced a post-`WI-SEGMENT-0070` replay fixture that
  preserves real `parsed_output` for two fresh `anchor_absent_from_document`
  cases.
- `WI-SEGMENT-0059` documents why broad fallback matching is unsafe.

## Summary

A strict local fuzzy policy can recover the two committed near-miss positives
available in the repository, with zero false positives on four hand-built decoy
cases. That is a useful signal, but it is not enough evidence to adopt fuzzy
matching in production.

Recommendation: defer production fuzzy matching. Keep exact/normalized anchor
grounding as the production behavior. Reconsider only after a broader,
predeclared near-miss corpus exists with realistic decoys and a zero
false-positive result.

## Evidence Source

`WI-SEGMENT-0072` first required checking whether existing tracked artifacts
already contained real near-miss `parsed_output` from `WI-SEGMENT-0069` or
`WI-SEGMENT-0070`. The committed
`experiments/03_cross_segment_relation_pilot/fixtures/wi_segment_0069_alignment_cases.json`
does not satisfy that requirement by itself: as documented in its own comment,
it contains marker-leakage and quote/dash typography cases used by
`WI-SEGMENT-0070`, not near-miss positives.

No committed raw WI-SEGMENT-0069 near-miss smoke output was found. However,
`WI-SEGMENT-0071` committed a later, real, post-`WI-SEGMENT-0070` replay
fixture under
`experiments/03_cross_segment_relation_pilot/results/segmentation_paragraph_misnumbering_diagnostics/replay_fixture/`.
That fixture preserves `parsed_output` for two `anchor_absent_from_document`
cases that are genuine near misses:

| Case | Real LLM anchor | Source text | Difference |
|---|---|---|---|
| `no_charge_for_alterations__gold`, segment 17 `end_exact` | `uroariously` | `uproariously` | missing `p` |
| `way_of_a_rebel__miller`, segment 2 `start_exact` | `sits on the` | `sat on the` | verb substitution |

The evaluation corpus is committed at
`experiments/03_cross_segment_relation_pilot/fixtures/wi_segment_0072_near_miss_fuzzy_cases.json`.
It includes those two positive cases plus four negative/decoy cases intended
to expose wrong-window, repeated-character, and nearby-anchor risks.

No Anthropic calls were made for this evaluation.

## Candidate Policy

The evaluated policy is `strict_local_fuzzy`:

- Search only inside the model's claimed paragraph range.
- Generate candidates from short exact token sequences in the anchor.
- Accept only if edit distance is at most 3.
- Require similarity ratio at least 0.985.
- Require the longest contiguous matching run to cover at least 70% of the
  normalized anchor.
- Require a uniqueness margin of at least 0.02 against genuinely different
  candidate spans.

This is intentionally stricter than a general fuzzy search. It does not widen
the paragraph window, search the full document, or alter production alignment
behavior.

The evaluator is
`experiments/03_cross_segment_relation_pilot/evaluate_near_miss_fuzzy_matching.py`.
The result artifact is
`experiments/03_cross_segment_relation_pilot/results/segmentation_near_miss_fuzzy_matching_evaluation.json`.

## Results

| Metric | Result |
|---|---:|
| Positive near-miss cases | 2 |
| Positives recovered | 2 |
| Positive recovery rate | 100% |
| Negative/decoy cases | 4 |
| False positives | 0 |
| False-positive rate | 0% |

Recovered positive spans:

- `no_charge_end_exact_missing_p`: recovered source span `[44115, 44310)`,
  edit distance 1, similarity 0.9974, contiguous-run ratio 0.8402.
- `way_of_a_rebel_start_exact_verb_substitution`: recovered source span
  `[1575, 1714)`, edit distance 2, similarity 0.9892, contiguous-run ratio
  0.9281.

Rejected decoys:

- The `no_charge` near-miss anchor in an unrelated early window of the same
  story.
- The `way_of_a_rebel` near-miss anchor in a later window of the same story.
- A repeated Dr. Kalmar character/action anchor placed against a later window.
- A nearby radio-command anchor placed against the previous segment window.

## Safety Assessment

The strict local policy is directionally promising because it recovered both
available positives without accepting the decoys. The important limitation is
sample size: two positives and four decoys do not estimate false-positive risk
well enough for a production matcher. A single silent wrong span can corrupt
segment boundaries while still producing syntactically valid output, which is
the exact class of failure `WI-SEGMENT-0059` warns against.

The policy's strongest safety properties are:

- It stays inside the model's claimed paragraph range.
- It requires high lexical similarity and low edit distance.
- It rejects non-unique competing spans.
- It keeps broad full-document fallback out of scope.

The unresolved risks are:

- The positive set is too small and comes from only two stories.
- The decoys are useful but hand-built, not a broad repeated-text control set.
- The evaluation does not yet include cases with multiple near-identical
  phrases in the same claimed paragraph range.
- The policy has not been tested against currently-correct included stories,
  so it does not yet prove that adding fuzzy matching would leave existing
  successful alignments untouched.

## Thresholds And Stop Conditions

Any future production implementation WI should predeclare a broader corpus and
meet all of these conditions before changing production alignment:

- At least 10 real near-miss positive anchors with persisted `parsed_output`.
- At least 20 negative/decoy cases, including repeated-text ambiguity,
  wrong-window same-story decoys, nearby-anchor decoys, and currently-correct
  included-story controls.
- At least 90% positive recovery.
- Exactly 0 false positives. A single false positive is a stop condition, not a
  tuning invitation.
- Exactly 0 accepted matches outside the model's claimed paragraph window.
- Every accepted match must be unique under the predeclared uniqueness rule.

Stop immediately if any evaluation result requires widening to a full-document
search, loosening the false-positive threshold above zero, or redefining the
thresholds after seeing the results.

## Recommendation

Defer production fuzzy matching.

This evaluation shows that a strict local fuzzy matcher may be viable, but it
does not yet clear the safety bar for production adoption. Do not implement a
production matcher from this evidence alone. The right next step is to let
future approved segmentation runs accumulate more real near-miss
`parsed_output`, or to file a separate bounded evidence-gathering WI if fuzzy
matching becomes important enough to justify fresh spend.

Do not file a production implementation WI yet. If follow-on work is filed, it
should be an evidence-expansion WI first, with the thresholds above frozen
before any real API calls.
