---
execution_id: 2026_08_31_09_45_39_WI_SEGMENT_0101_PARAGRAPH_BOUNDARY_PROMPT_CONSISTENCY_REVIEW
prompt_id: PROMPT(AD_HOC:WI_SEGMENT_0101_PARAGRAPH_BOUNDARY_PROMPT_CONSISTENCY_REVIEW)[2026-08-31T09:45:34+00:00]
work_item: AD_HOC
status: landed
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/420
commit: 6f888a044facc293491f56b3e192d137730cafe8
agent: claude_app
instruction_source: "/lrh-land https://github.com/xenotaur/LCATS/pull/420 (inline review-response)"
session_transcript: pending
created_at: 2026-08-31T09:45:39+00:00
---

# Summary

Review-response round for PR #420 (`WI-SEGMENT-0101` implementation).
Triaged 4 review comments (2 Codex, 2 Copilot), all against the
measurement methodology and its reported numbers.

# Result

All 4 comments were valid and feasible; fixed all 4:

1. **Codex (P2): design doc's headline metric mislabeled "anchor-level"
   when it was actually segment-level.** Verified directly: the script
   incremented once per segment when either anchor was outside, so
   12/177 and 8/162 are segment counts, not individual-anchor counts.
   Computed the true anchor-level totals (12/350 baseline, 9/321
   reworded - `easy_money__sinclair` segment 4 has both anchors outside,
   contributing 2 to the anchor count but 1 to the segment count).
   **Fixed**: added the anchor-level row to the Results table, corrected
   "anchor-level" -> "segment-level" throughout, and explained why the
   two metrics differ.
2. **Codex (P2): design doc reused the baseline run's $0.593 cost for
   the reworded run instead of computing its own usage.** Verified
   directly against the reworded run's own committed result files:
   229,485 input / 67,179 output tokens, $0.5654 -> $0.57, not $0.59.
   **Fixed**: corrected every cost figure in the doc and added the
   correction as an explicit note in the Cost estimate section.
3. **Copilot (P2): `_check_segment` doesn't mirror `align_segment`'s
   par_id normalization** - accepts bools as ints (Python: `isinstance(True, int)`
   is true) and doesn't clamp `end_par_id` up to `start_par_id` when
   reported lower. Verified against `align_segment`'s real source
   (`text_segmenter.py`): confirmed both gaps. Verified against the
   actual dataset: neither case occurred in either results directory, so
   this had no effect on reported numbers. **Fixed**: added explicit bool
   exclusion and the `ep = max(ep, sp)` clamp, matching production
   exactly.
4. **Copilot (P2): `_locate_one_anchor` marks any bounded-search match as
   `inside_claimed_window=True`, but `end_exact`'s search range can be
   widened below the true window's start when `start_exact` only
   resolved via the unbounded fallback - a match in that widened gap
   would be wrongly marked inside.** Verified by finding the exact 2 real
   cases this happened on (`the_haunter_of_the_dark` segment 10 baseline;
   `the_guardians__cox` segment 6 reworded) and manually checking each
   end-anchor match's real position against the true window - both
   happened to still fall inside on direct recheck, so no reported number
   changed. **Fixed**: restructured `_locate_one_anchor` to always judge
   "inside the claimed window" against the true window, independent of
   whatever range was actually searched.

Re-ran both measurements after all fixes: **identical segment-level
results** (12/177 baseline, 8/162 reworded) - none of the 4 fixes changed
the design doc's headline finding, only its precision and the labeling/
cost accuracy around it.

# Validation

- `scripts/format --check --diff` / `scripts/lint` (LCATS conda env) - clean
- `python -m unittest experiments.03_cross_segment_relation_pilot.reworded_boundary_prompt_test` - 4/4 pass
- `lrh validate` - 0 errors, 299 warnings (pre-existing baseline)
- Both overshoot measurements re-run after all fixes - segment-level
  numbers unchanged; anchor-level numbers now correctly computed and
  reported (12/350, 9/321)

# Follow-up

None beyond what the primary record already listed.
