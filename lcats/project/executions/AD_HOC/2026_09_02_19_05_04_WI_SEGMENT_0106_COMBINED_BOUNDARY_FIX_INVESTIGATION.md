---
execution_id: 2026_09_02_19_05_04_WI_SEGMENT_0106_COMBINED_BOUNDARY_FIX_INVESTIGATION
prompt_id: PROMPT(AD_HOC:WI_SEGMENT_0106_COMBINED_BOUNDARY_FIX_INVESTIGATION)[2026-09-02T19:04:50+00:00]
work_item: AD_HOC
status: landed
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/422
agent: claude_app
instruction_source: "user request in-session (follow-on to WI-SEGMENT-0101 closeout's open follow-up item)"
session_transcript: pending
commit: 68e9a8225f91fafa61c979e62dc60da8a32f198e
created_at: 2026-09-02T19:05:04+00:00
---

# Summary

Created work item `WI-SEGMENT-0106`: investigate whether combining
`WI-SEGMENT-0098`'s recommended code-side window-widening with
`WI-SEGMENT-0101`'s reworded prompt is worth implementing - by
root-causing `WI-SEGMENT-0101`'s 2 regressed stories, sizing the
window-widening margin against the real 21-instance combined dataset,
and simulating the combined fix against already-committed data, with no
new API spend.

# Result

Spot-checked the real data before scoping: pulled the two regressed
stories' (`the_last_days_of_l_a__smith`, `girl`) exact overshoot detail
directly from `paragraph_boundary_overshoot_reworded.json`, and
aggregated all 21 real anchor-level overshoot instances across both
`WI-SEGMENT-0098`'s baseline data and `WI-SEGMENT-0101`'s reworded-prompt
data - confirmed a real, wide spread (4-5,345 characters), directly
motivating the item's margin-distribution requirement rather than a
single fixed-margin guess. Wrote
`lcats/project/work_items/proposed/WI-SEGMENT-0106.md`, scoped entirely
around already-committed data with `forbidden_actions:
spend_api_budget_without_approval` and explicit Non-Goals against
implementing either mitigation directly.

# Validation

- `lrh validate` - 0 errors (281 warnings, pre-existing baseline plus the
  standard `unassigned`-owner warnings)

# Follow-up

- PR opened: https://github.com/xenotaur/LCATS/pull/422
- `session_transcript` still `pending` - update to the durable session
  pointer before landing.
