---
execution_id: 2026_10_22_15_05_19_WI_SF_0123_HEINLEIN_TEMPORAL_REFERENCE_DESIGN_REVIEW
prompt_id: PROMPT(AD_HOC:WI_SF_0123_HEINLEIN_TEMPORAL_REFERENCE_DESIGN_REVIEW)[2026-10-22T15:05:16+00:00]
work_item: AD_HOC
status: in_progress
rerun_of: 2026_10_22_08_04_28_WI_SF_0123_HEINLEIN_TEMPORAL_REFERENCE_DESIGN
pr: https://github.com/xenotaur/LCATS/pull/527
commit: 0dbba51f6e75440ed26a230a08eebf9a6245fca0
created_at: 2026-10-22T15:05:19+00:00
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/527
session_transcript: pending
---

# Summary

Review-response round for PR 527 (WI-SF-0123): one Codex P2 thread on the relation-to-now vocabulary, triaged against the work item and approved by the user before any edit.

# Result

Codex noted that listing calendar-expired as a value in the relation enum while also requiring it as a separate flag loses or duplicates state, since a dated prediction can be both expired and falsified or realized, and that the enum lacked not_assessable although Required Change 5 mandates it. The finding was valid and was my design error. Decision 6 now defines an outcome relation (stable, still open, realized, falsified, not assessable) and decision 7 defines calendar-expired as a separate true-or-false flag independent of the outcome relation, not counted toward plausible now.

# Validation

- lrh validate reported 0 errors; lrh work-items readiness reported the item ready; git diff --check clean.

# Follow-up

- Run confirm-fixes, resolve the thread, then the merge-and-closeout ask.
