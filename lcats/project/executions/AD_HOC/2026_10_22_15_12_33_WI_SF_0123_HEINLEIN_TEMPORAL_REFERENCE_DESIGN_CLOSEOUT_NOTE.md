---
execution_id: 2026_10_22_15_12_33_WI_SF_0123_HEINLEIN_TEMPORAL_REFERENCE_DESIGN_CLOSEOUT_NOTE
prompt_id: PROMPT(AD_HOC:WI_SF_0123_HEINLEIN_TEMPORAL_REFERENCE_DESIGN_CLOSEOUT_NOTE)[2026-10-22T15:12:16+00:00]
work_item: AD_HOC
status: landed
rerun_of: 2026_10_22_08_04_28_WI_SF_0123_HEINLEIN_TEMPORAL_REFERENCE_DESIGN
pr: https://github.com/xenotaur/LCATS/pull/527
commit: d69f440b55f4fab4289682c3f6a74a2278407809
created_at: 2026-10-22T15:12:33+00:00
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/527
session_transcript: claude-app:dff6f127-44db-417c-9b1e-0f962af4c00a
---

# Summary

Closeout note for PR 527 (the planning PR for WI-SF-0123), landed through /lrh-work-item and /lrh-land. The primary execution record is immutable, so the CHAIN-NOTE lives in this record.

# Result

PR 527 was squash-merged as d69f440b55f4fab4289682c3f6a74a2278407809 at head 41bced033195aab5abde0e82f8088800c81f8d9f. It adds proposed work item WI-SF-0123, a design proposal (no code) for judging the five Heinlein conditions against the author's world at the time of writing, and registers it in WS-KNIGHT-NOVUM-ANALYSIS. The work item records the owner's decisions from the session as fixed inputs: the author's-here-and-now reference frame, a premise-first and date-second design, change windows, a composition-date interval with a source order, interval-to-status and combination rules, a speculative-premises flag, and a separate opt-in stage that leaves heinlein-five-v1 untouched. One Codex P2 thread found that the relation vocabulary I had proposed overlapped the separate calendar-expired flag and lacked a not-assessable value; the finding was valid, the user approved the fix, and decision 6 is now an outcome relation (stable, still open, realized, falsified, not assessable) with calendar-expired as an independent true-or-false flag in decision 7. Copilot recommended approval with no open issues. All four CI checks passed on the final head. The primary, review and confirm records were landed with this closeout. No work item was resolved: WI-SF-0123 stays proposed, and WS-KNIGHT-NOVUM-ANALYSIS stays open.

CHAIN-NOTE: cycles=2; stops=3; gates=[chain-authorization, review, merge]; friction=design-overlap-caught-by-review; note="planning PR for the temporal-reference design; the relation vocabulary the author proposed and the owner approved had an overlap with the calendar-expired flag and a missing not-assessable value, caught by Codex and fixed with approval; confirm check was the author's own reading, not a cold review; no WI resolved"

# Validation

- lrh validate reported 0 errors before and after closeout.
- CI: coverage, lint and both test checks passed on the final head.

# Follow-up

- Execute WI-SF-0123 with /lrh-execute: it commits the six-story premise trial as an evidence file and writes the design proposal for owner review.
- The open questions it must record include whether backward differences such as historical fiction count for the different condition.
