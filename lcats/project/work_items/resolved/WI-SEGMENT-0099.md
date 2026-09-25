---
resolution: "Added 2 real positives from WI-EVENT-0096 to WI-SEGMENT-0072's near-miss fuzzy-matching evaluation corpus (now 4 positives, 4 decoys unchanged); reran the unmodified strict_local_fuzzy evaluator: 75% exact recovery (up from 50%), 0/4 false positives. Explicitly distinguished the Martina/Martha case as a content/name substitution, a different risk class from the pure spelling-omission cases (uroariously/uproariously, gratefuly/gratefully); reclassified sits/sat as content-substitution too during PR review, correcting the original grouping. Compared against WI-SEGMENT-0072's frozen thresholds (>=10 positives, >=20 decoys, >=90% recovery, 0 false positives) without renegotiating them - still short on corpus size, recommendation remains defer. No production alignment behavior changed. PR #409."
blocked_reason: null
blocked: false
id: WI-SEGMENT-0099
title: Extend near-miss fuzzy-matching evaluation with real spelling and content near-misses
type: evaluation
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
  - lcats/project/design/segmentation-near-miss-fuzzy-matching-evaluation.md
  - lcats/project/work_items/resolved/WI-SEGMENT-0072.md
  - lcats/project/executions/WI-EVENT-0096/2026_08_26_05_07_53_WI_EVENT_0096_MEASUREMENT.md
depends_on:
  - WI-SEGMENT-0072
blocked_by: []
expected_actions:
  - edit_file
  - run_tests
  - create_pr
forbidden_actions:
  - implement_production_fuzzy_matcher
  - weaken_exact_grounding
  - reintroduce_full_document_fallback
  - lower_wi_segment_0072_thresholds
  - force_push
  - delete_branch
acceptance:
  - "Two new real positive cases from WI-EVENT-0096's 2026-08-26 run are added to the tracked evaluation fixture (experiments/03_cross_segment_relation_pilot/fixtures/wi_segment_0072_near_miss_fuzzy_cases.json): problem_in_solid__smith segment 6 end_exact ('Martina Evers' in the model's anchor vs 'Martha Evers' in the real source - a name substitution) and the_last_days_of_l_a__smith segment 13 start_exact ('gratefuly' vs real 'gratefully' - a one-letter deletion)"
  - "experiments/03_cross_segment_relation_pilot/evaluate_near_miss_fuzzy_matching.py is rerun against the enlarged corpus (now 4 positive cases) and reports, per case: edit distance, similarity ratio, contiguous-run-ratio, and whether the recovered span is an exact-boundary match or overextended"
  - "Results are compared explicitly against WI-SEGMENT-0072's own frozen thresholds (at least 10 real positives, at least 20 decoys, at least 90% exact recovery, exactly 0 false positives) and a plain go/still-defer recommendation is stated - the thresholds themselves are not renegotiated or loosened"
  - "The 'Martina'/'Martha' case is explicitly analyzed as a name/content substitution distinct from a pure spelling or whitespace near-miss, with the report stating whether a future production policy's intended scope should include content-substitution recovery at all, or exclude it as a different risk class from spelling typos"
  - "No production alignment behavior is changed by this item"
  - "lrh validate reports 0 errors"
required_evidence:
  - manual_review
  - lrh_validate
  - test_output
artifacts_expected:
  - experiments/03_cross_segment_relation_pilot/fixtures/wi_segment_0072_near_miss_fuzzy_cases.json
  - lcats/project/design/segmentation-near-miss-fuzzy-matching-evaluation.md
---

# Work Item: WI-SEGMENT-0099

## Summary

`WI-SEGMENT-0072` evaluated a strict local fuzzy-matching policy against
2 real near-miss positive cases and deferred production adoption pending
a broader corpus (its own frozen thresholds: at least 10 real positives,
at least 20 decoys, at least 90% exact recovery, exactly 0 false
positives). `WI-EVENT-0096`'s 2026-08-26 real measurement run surfaced 2
more real near-miss positives. This item adds them to the tracked
evaluation corpus, reruns the existing evaluator, and reports the result
against `WI-SEGMENT-0072`'s own thresholds - honestly stating whether
this is progress toward the bar or evidence the bar is still far off, per
the user's own framing: "if the rest of the text is correct this might
be a useful win; if more of it is malformed it may be a lose."

## Problem / Context

Forensic analysis of `WI-EVENT-0096`'s 10 real alignment failures found 2
cases that are neither pure formatting near-misses
(`WI-SEGMENT-0097`'s scope) nor paragraph-boundary truncation
(`WI-SEGMENT-0098`'s scope), but genuine word-level near-misses in
otherwise-correct anchor text:

- `mass_quantities/problem_in_solid__smith` segment 6 `end_exact`: the
  model's anchor reads `"...ordered the Manhattan that was to become
  Gargantuan in\nsize--"` and everything else in the ~284-character
  anchor matches the source exactly **except** the character name -
  the model wrote `"Martina Evers"` where the real source says
  `"Martha Evers"`. This is a genuine content substitution (a
  wrong-but-plausible name), not a spelling slip or formatting
  difference.
- `mass_quantities/the_last_days_of_l_a__smith` segment 13 `start_exact`:
  the model's anchor reads `"...you head for The Bar and dive\ngratefuly
  through the door."` where the real source says `"...gratefully through
  the door."` - a one-letter deletion (`gratefuly` vs `gratefully`), a
  pure spelling typo with everything else exact.

Both are real, already-committed data (no new API spend needed) and
directly extend `WI-SEGMENT-0072`'s own evaluation corpus, which
currently has only 2 positive cases - well short of its own 10-positive
threshold. `WI-SEGMENT-0072`'s own Recommendation section explicitly
invites exactly this: "file a separate bounded evidence-gathering WI if
fuzzy matching becomes important enough to justify fresh spend" - this
item is that evidence-gathering step, using data that already exists
rather than fresh spend.

### Duplication search

- In-repo: `WI-SEGMENT-0072` already built the evaluation corpus format
  (`experiments/03_cross_segment_relation_pilot/fixtures/wi_segment_0072_near_miss_fuzzy_cases.json`)
  and evaluator
  (`experiments/03_cross_segment_relation_pilot/evaluate_near_miss_fuzzy_matching.py`).
  This item extends that corpus and reruns that evaluator; it does not
  build new tooling.
- Sibling repos: None identified.
- External libraries: None identified; the existing evaluator's
  dependencies are sufficient.
- Recommendation: Proceed, using the existing tool and fixture format
  as-is.

### Demand search

- Work items: `WI-SEGMENT-0072`'s own Recommendation section names this
  exact next step. Surfaced further by real evidence in `WI-EVENT-0096`.
- Proposals: None identified.
- Backlog: No matching entry found.
- Recommendation: Proceed.

## Scope

- Add the two new real positive cases to the tracked fixture, following
  its existing schema (`case_id`, `story_id`, `story_path`,
  `parsed_output_path` pointing at `WI-EVENT-0096`'s committed real
  output, `segment_id`, `anchor_field`, `expected_source_text`,
  `expected_span_start`, `near_miss_reason`).
- Rerun `evaluate_near_miss_fuzzy_matching.py` against the enlarged
  corpus (4 positives, existing 4 decoys unless additional decoys are
  warranted - see Required Changes).
- Report results per-case and in aggregate, compared explicitly against
  `WI-SEGMENT-0072`'s frozen thresholds.
- Explicitly separate the "Martina"/"Martha" content-substitution case
  from the "gratefuly"/"gratefully" spelling-typo case in the analysis -
  they are different risk classes even though both are "near-miss."
- State a plain go/still-defer recommendation; do not implement
  production fuzzy matching regardless of the result (still short of the
  10-positive threshold either way).

## Required Changes

1. Add both new cases to
   `experiments/03_cross_segment_relation_pilot/fixtures/wi_segment_0072_near_miss_fuzzy_cases.json`,
   with `parsed_output_path` pointing at the real committed output under
   `experiments/03_cross_segment_relation_pilot/results/segmentation_reliability/`
   (`WI-EVENT-0096`'s real run), not a freshly-invented fixture.
2. Rerun `evaluate_near_miss_fuzzy_matching.py` against the updated
   corpus; capture per-case edit distance, similarity ratio,
   contiguous-run-ratio, and exact-vs-overextended span recovery, plus
   aggregate recovery/false-positive rates against the existing 4
   decoys.
3. Update `lcats/project/design/segmentation-near-miss-fuzzy-matching-evaluation.md`
   with the new results section, explicitly restating
   `WI-SEGMENT-0072`'s frozen thresholds and comparing the updated
   corpus size (4 of the required 10+ positives) and results against
   them.
4. Add analysis distinguishing the "Martina"/"Martha" content
   substitution from the "gratefuly"/"gratefully" spelling typo:
   consider whether a future production policy's safety argument should
   even attempt to recover content substitutions (a wrong name is a
   different failure mode from a misspelled but otherwise-correct word,
   and forgiving it via fuzzy matching could mask a downstream
   data-quality issue distinct from segmentation boundary correctness).
5. State the resulting recommendation (still defer, given the corpus
   remains below the 10-positive threshold either way; or any other
   finding the actual evaluation surfaces) without lowering or
   reinterpreting `WI-SEGMENT-0072`'s own thresholds.

## Non-Goals

- Does not implement production fuzzy matching - the corpus will remain
  below `WI-SEGMENT-0072`'s own 10-positive threshold even after this
  item, so a "still defer" outcome is expected, not a failure of this
  item.
- Does not lower, redefine, or reinterpret `WI-SEGMENT-0072`'s frozen
  thresholds - this item reports against them as-is.
- Does not investigate case-sensitivity (`WI-SEGMENT-0097`) or
  paragraph-boundary truncation (`WI-SEGMENT-0098`) - those are
  separately scoped.
- Does not spend any real API budget - both new cases already exist as
  committed real data from `WI-EVENT-0096`.

## Acceptance Criteria

(see frontmatter `acceptance:` above)

## Validation

- lrh validate

## Risk Notes

- **This item is explicitly evidence-gathering, not adoption.** Even a
  clean result (high recovery, zero false positives on 4 positives) does
  not clear `WI-SEGMENT-0072`'s own bar (10+ positives, 20+ decoys) - the
  honest expected outcome is "more evidence, still short of the
  threshold," and this item's acceptance criteria are written to accept
  that outcome rather than pressure toward a false "adopt" conclusion.
- **Content substitution vs. spelling typo is a real distinction worth
  preserving**, per the user's own framing: a correctly-identified
  segment reported with a sloppy but recoverable quote (spelling typo,
  formatting) is a different risk than a segment reported with a
  factually wrong detail (character name) that happens to also fail
  alignment. Collapsing them into one "near-miss" bucket could hide that
  a future fuzzy matcher recovering the first class says nothing about
  the safety of recovering the second.
- **Do not invent additional decoys casually.** `WI-SEGMENT-0072`'s own
  Risk Notes caution that hand-built decoys are a real limitation; if
  this item adds decoys, they should be justified real or realistic
  cases, not filler to inflate the count.

## Related Workstream and Designs

- Workstream: `lcats/project/workstreams/proposed/WS-PILOT-IMPROVEMENTS.md`
- Design: `lcats/project/design/segmentation-near-miss-fuzzy-matching-evaluation.md`
- Work item: `lcats/project/work_items/resolved/WI-SEGMENT-0072.md` - the
  evaluation this item extends, including its frozen thresholds
- Evidence: `lcats/project/executions/WI-EVENT-0096/2026_08_26_05_07_53_WI_EVENT_0096_MEASUREMENT.md`
  and `experiments/03_cross_segment_relation_pilot/results/segmentation_reliability/`
  - the real run that surfaced both new cases
