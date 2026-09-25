---
execution_id: 2026_08_28_16_52_43_WI_SEGMENT_0099_NEAR_MISS_FUZZY_MATCHING_EVALUATION
prompt_id: PROMPT(WI-SEGMENT-0099:WI_SEGMENT_0099_NEAR_MISS_FUZZY_MATCHING_EVALUATION)[2026-08-28T07:18:13+00:00]
work_item: WI-SEGMENT-0099
status: landed
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/409
commit: e45223df312ee6642394a568c755c182f035f14c
agent: claude_app
instruction_source: lcats/project/work_items/proposed/WI-SEGMENT-0099.md
session_transcript: claude-app:e8e46d5d-35d3-4ccc-9cba-137bd31bf3a5
created_at: 2026-08-28T16:52:43+00:00
---

# Summary

Executed `WI-SEGMENT-0099`: extended `WI-SEGMENT-0072`'s deferred
near-miss fuzzy-matching evaluation with 2 real positives from
`WI-EVENT-0096`'s 2026-08-26 measurement, without lowering that
evaluation's own frozen adoption thresholds.

# Result

Computed the exact real-source-text correction and its true span-start
for both new cases directly (not assumed): `problem_in_solid__smith`
segment 6 `end_exact` (model said `"Martina Evers"`, real source says
`"Martha Evers"` at char 23981) and `the_last_days_of_l_a__smith` segment
13 `start_exact` (model said `"gratefuly"`, real source says
`"gratefully"` at char 19105) - both verified by exact string search
against the real canonicalized story text, not derived from the fuzzy
matcher itself.

Added both to
`experiments/03_cross_segment_relation_pilot/fixtures/wi_segment_0072_near_miss_fuzzy_cases.json`,
keeping the existing 4 decoys unchanged (per that evaluation's own Risk
Notes against inventing decoys casually). Reran
`evaluate_near_miss_fuzzy_matching.py` unmodified: 3/4 exact recovery
(75%, up from 50% on the original 2-case corpus), 0/4 false positives.
Both new cases recovered exactly on the first try.

Updated `lcats/project/design/segmentation-near-miss-fuzzy-matching-evaluation.md`
with a full 2026-08-28 section: per-case results, an explicit
content-substitution-vs-spelling-typo risk-class distinction (per the
user's own framing), and a comparison table against `WI-SEGMENT-0072`'s
frozen thresholds (10+ positives, 20+ decoys, 90%+ recovery, 0 false
positives) - still short on corpus size despite the encouraging numbers,
so the recommendation remains **defer**, unchanged and not renegotiated.

Refreshed the committed result artifact
(`experiments/03_cross_segment_relation_pilot/results/segmentation_near_miss_fuzzy_matching_evaluation.json`)
and fixed one existing unit test
(`evaluate_near_miss_fuzzy_matching_test.py`) that hardcoded the old
2-positive/1-recovered counts, adding assertions for both new cases'
exact recovery.

Opened PR #409 (branch
`xenotaur/audit/wi-segment-0099-near-miss-fuzzy-matching-evaluation`,
commit `14222658`).

# Validation

- `black`/`ruff` - clean
- `python -m unittest experiments.03_cross_segment_relation_pilot.evaluate_near_miss_fuzzy_matching_test` - 5/5 pass
- `lrh validate` - 0 errors, 248 warnings (pre-existing baseline)

# Follow-up

- Whether a future production policy should even attempt to recover
  content substitutions (vs. treating them as a distinct, always-loud
  failure mode) remains an explicitly open question, not resolved by
  this evaluation.
- All three segmentation-alignment follow-up WIs from `WI-EVENT-0096`'s
  forensic analysis (`WI-SEGMENT-0097`, `WI-SEGMENT-0098`,
  `WI-SEGMENT-0099`) are now executed.
