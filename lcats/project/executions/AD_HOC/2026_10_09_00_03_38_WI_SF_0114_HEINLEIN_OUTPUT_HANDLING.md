---
execution_id: 2026_10_09_00_03_38_WI_SF_0114_HEINLEIN_OUTPUT_HANDLING
prompt_id: PROMPT(AD_HOC:WI_SF_0114_HEINLEIN_OUTPUT_HANDLING)[2026-10-09T00:02:45+00:00]
work_item: AD_HOC
status: in_progress
pr: https://github.com/xenotaur/LCATS/pull/488
created_at: 2026-10-09T00:03:38+00:00
agent: claude_app
instruction_source: project/work_items/proposed/WI-SF-0114.md
session_transcript: pending
---

# Summary

Created work item WI-SF-0114, which plans making the structured-output stages fail loudly: the sf_heinlein stage on mismatched criterion keys and fenced JSON, and the shared evidence stage on an all-quarantined (empty) evidence set, with the evidence and Heinlein prompts aligned to the schema key names and no-cost tests built from the WI-SF-0113 canary's raw responses. Planning only; no code was changed.

# Result

Wrote project/work_items/proposed/WI-SF-0114.md (type deliverable, depends on WI-SF-0110, WI-SF-0111, WI-SF-0113), registered it in WS-KNIGHT-NOVUM-ANALYSIS, and opened PR 488. The owner approved the proposal and chose the recommended defaults: fail loudly on mismatched keys, and accept fenced JSON as a recorded coercion.

# Validation

- lrh validate reported 0 errors.
- lrh work-items readiness reported prompt_ready: yes.

# Follow-up

- The scope was widened after the PR opened: while checking Vonnegut's evidence, the canary files showed the evidence stage returned zero usable records in trials 1 to 3 (all six candidates quarantined as evidence_type is required), so the item now covers the evidence stage and prompts as well. The owner approved this as one work item.
- A docs-only follow-up PR corrects the merged canary report's two statements about the evidence stage and the Vonnegut result.

- Land the PR with /lrh-land, then run /lrh-execute WI-SF-0114.
- A canary rerun is a separate step after the fix.
- Update session_transcript from pending at closeout.
