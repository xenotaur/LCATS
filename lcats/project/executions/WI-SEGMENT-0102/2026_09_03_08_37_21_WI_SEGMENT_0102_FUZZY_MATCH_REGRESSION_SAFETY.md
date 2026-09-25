---
execution_id: 2026_09_03_08_37_21_WI_SEGMENT_0102_FUZZY_MATCH_REGRESSION_SAFETY
prompt_id: PROMPT(WI-SEGMENT-0102:WI_SEGMENT_0102_FUZZY_MATCH_REGRESSION_SAFETY)[2026-09-03T08:37:02+00:00]
work_item: WI-SEGMENT-0102
status: landed
agent: claude_app
instruction_source: "/lrh-execute WI-SEGMENT-0102 (inlined /lrh-implement)"
session_transcript: claude-app:e8e46d5d-35d3-4ccc-9cba-137bd31bf3a5
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/425
commit: 9ab824e25a3e71e94060ed587668771deba2f375
created_at: 2026-09-03T08:37:21+00:00
---

# Summary

Implements `WI-SEGMENT-0102`: regression-test `WI-SEGMENT-0072`'s frozen
`strict_local_fuzzy` policy against every real, already-correctly-aligned
segment discoverable in the repo, to check whether it ever disagrees with
the current production result on a segment the exact matcher already gets
right. Non-production, non-op-invariance check only - no production
alignment code or `WI-SEGMENT-0072`'s thresholds are touched.

# Result

Wrote `experiments/03_cross_segment_relation_pilot/
regression_test_fuzzy_matcher_against_real_segments.py`. A repo-wide
discovery pass (not limited to the WI's originally-named two locations)
found real segment-schema data in 4 locations; two other `"start_char"`
grep hits were inspected and excluded as non-segment schemas. Discovered
280 real segments across 35 stories; validated 257 as genuine ground truth
after 3 checks (overlap, reused anchor, and a third check added during
execution - paragraph-window-must-contain-char-offsets, needed because
`annotation_feasibility_trial`'s `love_of_life`/`story_of_keesh`/
`brown_wolf` still carry pre-`WI-SEGMENT-0059` paragraph-collapse-bug
metadata that overlap detection alone would not catch); 23 excluded.

Of 257 validated segments: 145 agree exactly on both anchors; 112
disagree. Decomposed the disagreements (a prior in-session miscount was
caught and corrected before this run): 105 are safe false negatives (no
candidate found - traced to two previously-undocumented structural limits
in `candidate_matches`: a punctuation-blind `\s+`-only token-join regex,
and a hard 3-word-token minimum before any n-gram is built at all); 7 are
a genuine, narrow disagreement (candidate found, off by exactly 1
character, always requiring real fuzzy tolerance, always a
typography-normalization boundary case - the same two-independent-matchers
risk `WI-SEGMENT-0059` treats as a stop condition).

Wrote `lcats/project/design/segmentation-fuzzy-match-regression-safety-check.md`
with the full inventory, methodology, results, and an explicit non-blanket
verdict (not "safe": the 7 wrong-offset cases and the two structural
false-negative causes are both reported, not absorbed).

Added `regression_test_fuzzy_matcher_against_real_segments_test.py` (11
unit tests). Two real bugs were caught and fixed during this item's own
execution: (1) `check_segment` initially crashed with `IndexError` on an
out-of-range `par_id` because it didn't clamp like `validate_controls`
does - fixed by applying the identical clamp; (2) 3 of the 11 first-drafted
tests failed because their hand-picked synthetic `start_char`/`end_char`
offsets didn't match the real computed paragraph spans for the test
fixture text (paragraph boundaries exclude the trailing blank-line
separator) - fixed by computing the real spans directly rather than
guessing, which also incidentally surfaced the 3-token-minimum finding
above (a 2-word test anchor produced zero fuzzy candidates for a reason
that turned out to be a real, generalizable limitation, not a test bug).

# Validation

- `python -m unittest experiments.03_cross_segment_relation_pilot.regression_test_fuzzy_matcher_against_real_segments_test -v` - 11/11 pass
- `black --check --diff` - both new files unchanged
- `ruff check` - both new files pass
- `lrh validate` - 0 errors, 284 warnings (pre-existing baseline)
- Real run of `regression_test_fuzzy_matcher_against_real_segments.py --output ...` producing `experiments/03_cross_segment_relation_pilot/results/fuzzy_matcher_regression_safety_check.json`

# Follow-up

- Proceed to `/lrh-implement` Step 8 (commit, PR) and `/lrh-land`.
- The design doc's verdict (7 real wrong-offset cases; a large, newly-found
  false-negative robustness gap in `candidate_matches`) should be
  highlighted in the final report to the user, not just left in the
  committed doc - it materially affects confidence in
  `WI-SEGMENT-0072`'s prior "directionally interesting" framing.
