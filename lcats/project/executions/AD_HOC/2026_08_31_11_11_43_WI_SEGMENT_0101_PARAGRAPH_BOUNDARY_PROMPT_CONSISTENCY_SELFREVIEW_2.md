---
execution_id: 2026_08_31_11_11_43_WI_SEGMENT_0101_PARAGRAPH_BOUNDARY_PROMPT_CONSISTENCY_SELFREVIEW_2
prompt_id: PROMPT(AD_HOC:WI_SEGMENT_0101_PARAGRAPH_BOUNDARY_PROMPT_CONSISTENCY_SELFREVIEW_2)[2026-08-31T11:11:36+00:00]
work_item: AD_HOC
status: landed
rerun_of: 2026_08_31_10_21_18_WI_SEGMENT_0101_PARAGRAPH_BOUNDARY_PROMPT_CONSISTENCY_CONFIRM_FIXES
pr: https://github.com/xenotaur/LCATS/pull/420
commit: 6f888a044facc293491f56b3e192d137730cafe8
agent: claude_app
instruction_source: "/lrh-land https://github.com/xenotaur/LCATS/pull/420 (substitute self-review, /lrh-confirm-fixes Step 8)"
session_transcript: pending
created_at: 2026-08-31T11:11:43+00:00
---

# Summary

Substitute self-review pass (PR-mode) for PR #420, dispatched from
`/lrh-confirm-fixes` Step 8 because no automatic reviewer response had
landed against the `_CONFIRM` commit (`a9651da1`) after a reasonable
wait - the existing Codex/Copilot reviews were both pinned to the
initial PR-open commit (`d13cd8ec`), consistent with this repo not
re-triggering bot review on subsequent pushes.

# Result

A first dispatch was interrupted mid-task by a host sleep/API error; a
fresh cold-context subagent was redispatched and completed cleanly. It
independently re-verified 5+ numeric/factual claims from the real
committed result files (segment-level 12/177 vs 8/162, anchor-level
12/350 vs 9/321, real reworded-run cost $0.57) and confirmed no
production files (`scene_analysis.py`/`text_segmenter.py`) were touched.

It surfaced 4 findings, all real:

1. **The PR's own description text was never re-synced after the prior
   review round's fixes** - still said "Anchor-level overshoot dropped
   from 12/177 to 8/162" (the pre-fix mislabeling the design doc has
   since corrected) and "actual cost $0.59" (the baseline run's cost,
   already corrected to $0.57 for the reworded run in the design doc).
   Independently re-verified via `gh pr view --json body`. **Fixed**:
   edited the PR description to match the design doc's corrected
   figures and terminology.
2. **Same root cause, the stale cost figure specifically** - covered by
   the same PR-body edit as finding 1.
3. **`_check_segment`'s docstring overclaimed full parity with
   `align_segment`'s par_id normalization**: it replicated the bool
   exclusion and the `end_par_id < start_par_id` clamp, but returned
   `None` (dropped the segment) for an out-of-range par_id instead of
   clamping into `[1, n]` like `align_segment` actually does. Verified
   directly against `align_segment`'s source
   (`text_segmenter.py:265-267`, `max(1, min(x, n))`). Verified the
   dataset never hit this case either. **Fixed**: clamp instead of drop,
   matching production exactly on all three normalization rules now.
4. **`measure_paragraph_boundary_overshoot.py` - the script computing
   this PR's headline numbers - had no paired unit test**, unlike every
   sibling measurement script in this directory. **Fixed**: added
   `measure_paragraph_boundary_overshoot_test.py` (8 tests) exercising
   `_check_segment`/`_locate_one_anchor` directly against a small
   synthetic story: in-window matches, genuine overshoot with correct
   sizing, bounded-search-preferred-over-duplicate (the
   `the_invaders__ferris` regression class), the `s_idx` search-floor
   handoff, bool rejection, the `end_par_id`-clamp, the
   out-of-range-clamp (finding 3 above), and the segment-vs-anchor-level
   counting distinction.

Independently re-verified the top finding (stale PR body) myself via
`gh pr view --json body` before accepting it.

Re-ran both overshoot measurements after all fixes: **identical
segment-level and anchor-level results** (12/177, 8/162, 12/350, 9/321) -
none of these 4 fixes changed the design doc's or PR's headline finding.

# Validation

- `scripts/format --check --diff` / `scripts/lint` (LCATS conda env) - clean
- `python -m unittest experiments.03_cross_segment_relation_pilot.measure_paragraph_boundary_overshoot_test` - 8/8 pass (new)
- `python -m unittest experiments.03_cross_segment_relation_pilot.reworded_boundary_prompt_test` - 4/4 pass
- `lrh validate` - 0 errors, 301 warnings (pre-existing baseline)
- Both overshoot measurements re-run after all fixes - numbers unchanged
- PR description re-synced via `gh pr edit`

# Follow-up

- `session_transcript` still `pending` - update to the durable session
  pointer before landing.
