---
resolution: "Implemented via PR #402. Added re.IGNORECASE to _locate_anchor_span's existing whitespace/typography-tolerant fallback in text_segmenter.py (exact-match-first behavior and paragraph-window-only bounds unchanged). Both real case-only near-misses from WI-EVENT-0096 (the_haunter_of_the_dark, calling_the_empress__smith) verified to now resolve correctly. 5 new tests added (2 real regressions, 1 decoy confirming no wrong-location match, 1 exact-match-stays-case-sensitive guard, 1 combined case+whitespace case). scripts/test: 2181 tests, 1 pre-existing unrelated failure (NMF-seed flake, already noted in WI-EVENT-0096). lrh validate: 0 errors."
blocked_reason: null
blocked: false
id: WI-SEGMENT-0097
title: Add case-insensitive matching to segmentation anchor alignment fallback
type: deliverable
status: resolved
priority: medium
owner: unassigned
contributors: []
assigned_agents: []
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap: []
related_workstreams:
  - WS-PILOT-IMPROVEMENTS
related_design:
  - lcats/project/design/segmentation-alignment-failure-categories.md
  - lcats/project/work_items/resolved/WI-SEGMENT-0070.md
  - lcats/project/executions/WI-EVENT-0096/2026_08_26_05_07_53_WI_EVENT_0096_MEASUREMENT.md
depends_on: []
blocked_by: []
expected_actions:
  - edit_file
  - run_tests
  - create_pr
forbidden_actions:
  - implement_general_edit_distance_fuzzy_matching
  - widen_paragraph_search_window
  - reintroduce_full_document_fallback
  - force_push
  - delete_branch
acceptance:
  - "_locate_anchor_span's whitespace/typography-tolerant fallback (lcats/src/lcats/analysis/text_segmenter.py) matches case-insensitively (e.g. via re.IGNORECASE on the constructed pattern), while its exact-match-first behavior, paragraph-window-only search bound, and non-widening safety properties are unchanged"
  - "Both real case-only near-misses found in WI-EVENT-0096's 2026-08-26 real-API run are added as regression fixtures and now resolve correctly: the_haunter_of_the_dark segment 6 end_exact ('what had happened...' vs source 'What had happened...') and calling_the_empress__smith segment 1 end_exact ('the _Empress of Kolain_...' vs source 'The\\n_Empress of Kolain_...')"
  - "A negative/decoy test confirms case-insensitivity does not cause the fallback to accept a match at the wrong location within the claimed paragraph window (e.g. two case-variant occurrences of similar text in the same window resolve to the correct one, or the match is rejected if truly ambiguous)"
  - "scripts/test passes with no new failures"
  - "lrh validate reports 0 errors"
required_evidence:
  - test_output
  - lrh_validate
  - manual_review
artifacts_expected:
  - lcats/src/lcats/analysis/text_segmenter.py
  - lcats/tests/analysis_tests/text_segmenter_test.py
---

# Work Item: WI-SEGMENT-0097

## Summary

`_locate_anchor_span`'s existing whitespace-run and typography (curly
quote/dash) normalization fallback never case-folds. Real data from
`WI-EVENT-0096`'s 2026-08-26 measurement run shows this is a genuine,
low-risk gap: two of the ten real post-fix alignment failures differed
from the source text by exactly one letter's case and nothing else - a
deterministic, zero-ambiguity equivalence, not a similarity threshold.
Add case-insensitive matching to the existing fallback.

## Problem / Context

`WI-EVENT-0096` ran the real, exact 17-story baseline cohort through
`check_segmentation_reliability.py` and found 10 real `alignment_error`
failures ("anchor text not found in story text"). Direct forensic
analysis of each failure (reading the real story text and the real model
output side-by-side, not assumed) found:

- `lovecraft/the_haunter_of_the_dark` segment 6 `end_exact`: the model's
  anchor said `"what had happened to the skeleton..."`; the real source
  text says `"What had happened to the skeleton..."` (sentence-initial
  capital). No other difference. `_locate_anchor_span` already tries an
  exact match, then a whitespace-tolerant + typography-normalized
  fallback - confirmed directly by calling that function on this real
  case, it returns `None`; adding `re.IGNORECASE` to the same fallback
  regex recovers this case exactly.
- `mass_quantities/calling_the_empress__smith` segment 1 `end_exact`: the
  model's anchor said `"the _Empress of Kolain_ was a little world..."`;
  the real source says `"The\n_Empress of Kolain_ was a little
  world..."` - a case difference (`the`/`The`) combined with a
  newline-vs-space difference the existing whitespace-run tolerance
  already covers on its own; the case difference is what still blocks
  the match today, confirmed the same way.

This is a narrow, deterministic extension of a mechanism already in
production (the typography-normalization fallback added by
`WI-SEGMENT-0070`), not a reopening of `WI-SEGMENT-0072`'s deferred
question about general bounded-edit-distance fuzzy matching. A
case-insensitive comparison has no similarity threshold and no risk of
accepting a "close enough" wrong span - it accepts a match only when the
text is identical except for letter case, which cannot introduce the
class of silent wrong-location failure `WI-SEGMENT-0059`/`WI-SEGMENT-0072`
warn about.

### Duplication search

- In-repo: `_locate_anchor_span` already implements exactly this kind of
  deterministic character-class-equivalence fallback for typography
  (curly quotes/dashes -> ASCII). This item extends that same mechanism
  to also fold case; it does not introduce a new matching mechanism.
- Sibling repos: None identified.
- External libraries: Python's own `re.IGNORECASE` is sufficient; no
  third-party dependency needed.
- Recommendation: Proceed, extending the existing fallback in place.

### Demand search

- Work items: Surfaced directly by real evidence in
  `WI-EVENT-0096`'s execution record
  (`lcats/project/executions/WI-EVENT-0096/2026_08_26_05_07_53_WI_EVENT_0096_MEASUREMENT.md`)
  and `WI-EVENT-0033.md`'s Risk Notes. No existing work item covers
  case-sensitivity in anchor matching specifically.
- Proposals: None identified.
- Backlog: No matching entry found.
- Recommendation: Proceed.

## Scope

- Add case-insensitive matching to `_locate_anchor_span`'s existing
  whitespace/typography-tolerant fallback path only - never to the
  initial exact-match attempt, which stays a byte-exact check.
- Do not widen the search window, do not implement bounded edit
  distance, do not touch `align_segment`'s paragraph-range logic.
- Add the two real recovered cases as committed regression fixtures.
- Add at least one decoy/negative case verifying case-insensitivity does
  not introduce a wrong-location match.

## Required Changes

1. In `_locate_anchor_span` (`lcats/src/lcats/analysis/text_segmenter.py`),
   add `re.IGNORECASE` to the `re.search(pattern, normalized_segment)`
   call on the fallback path (after the exact-match attempt has already
   failed). Confirm the returned span's actual matched text (not just
   its length) is still used correctly downstream, consistent with the
   existing whitespace-tolerant-match handling (`WI-SEGMENT-0068`'s real
   end-offset fix).
2. Add regression tests to `text_segmenter_test.py` using the two real
   cases above (anchor text, real source text, and expected recovered
   span), citing `WI-EVENT-0096`'s execution record as the evidence
   source rather than re-deriving them from scratch.
3. Add a decoy test: two occurrences of the same text differing only in
   case within the same claimed paragraph window, confirming the match
   resolves to the correct (first, or otherwise well-defined) occurrence
   rather than silently picking an arbitrary one.
4. Run the full `text_segmenter_test.py` suite to confirm no existing
   test (e.g. ones relying on case-sensitive rejection) regresses.

## Non-Goals

- Does not implement bounded edit-distance or general fuzzy matching -
  that remains `WI-SEGMENT-0072`'s deferred, separately-gated question
  (see `WI-SEGMENT-0099`).
- Does not investigate or fix the paragraph-range-boundary truncation
  failures found in the same `WI-EVENT-0096` run - that is
  `WI-SEGMENT-0098`'s separate scope.
- Does not change `align_segment`'s paragraph-window computation.
- Does not spend any real API budget - both regression cases already
  exist as committed real data from `WI-EVENT-0096`.

## Acceptance Criteria

(see frontmatter `acceptance:` above)

## Validation

- scripts/format --check --diff
- scripts/lint
- scripts/test
- lrh validate

## Risk Notes

- **Case-folding is safe by construction, distinct from edit-distance
  fuzzy matching.** It accepts a match only when text is identical
  modulo letter case - there is no threshold to tune and no risk of
  accepting a genuinely different, merely "similar" span. This is why
  the item does not trigger `WI-SEGMENT-0072`'s stop-conditions, which
  govern similarity-threshold-based matching specifically.
- **Real-world yield is modest, not total.** Of the 10 real alignment
  failures in `WI-EVENT-0096`'s measurement, only 2 (20%) are pure
  case-only near-misses; the remainder need separate fixes
  (`WI-SEGMENT-0098`, `WI-SEGMENT-0099`). This item should not be
  reported as resolving segmentation reliability broadly.

## Related Workstream and Designs

- Workstream: `lcats/project/workstreams/proposed/WS-PILOT-IMPROVEMENTS.md`
- Design: `lcats/project/design/segmentation-alignment-failure-categories.md`
- Work item: `lcats/project/work_items/resolved/WI-SEGMENT-0070.md` -
  introduced the typography-normalization fallback this item extends
- Evidence: `lcats/project/executions/WI-EVENT-0096/2026_08_26_05_07_53_WI_EVENT_0096_MEASUREMENT.md`
  and `experiments/03_cross_segment_relation_pilot/results/segmentation_reliability/`
  - the real run that surfaced both cases
