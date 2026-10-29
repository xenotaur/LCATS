---
execution_id: 2026_10_12_23_27_21_WI_PROMOTE_0117_PR2_CLOSEOUT_NOTE
prompt_id: PROMPT(AD_HOC:WI_PROMOTE_0117_PR2_CLOSEOUT_NOTE)[2026-10-12T23:27:03+00:00]
work_item: AD_HOC
status: landed
rerun_of: 2026_10_12_06_38_19_WI_PROMOTE_0117
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/499
session_transcript: claude-app:6a2dbae2-adca-4a2a-92fe-2e95d3b2a4e0
pr: https://github.com/xenotaur/LCATS/pull/499
commit: 0b1f17090323a3279d63859d499a6a72370f7b12
created_at: 2026-10-12T23:27:21+00:00
---

# Summary

CHAIN-NOTE for PR #499 (WI-PROMOTE-0117 implementation), merged as 0b1f1709 via /lrh-execute and /lrh-land.

# Result

CHAIN-NOTE: cycles=1; stops=1; gates=[chain, extra-stop, review-response, confirm-fixes, merge]; friction="a scratch fixture error (collection name did not match payload ids) hit the extra stop condition and was reported, corrected and rerun; a hyphen-blind filename search missed science-fiction.json until a cold review caught it; the linguistics how-to contradicted the new rule and the guard's destination-only skip contradicted the preflight claim, both caught by bot review and corrected; the installed lrh has no vcs merge subcommand so the merge ran through gh with the same SHA lock"; note="Investigation PR. Observations: enumerate every list entry and every filename before concluding a set is complete, search the whole repo for documents that contradict a new rule, and test a guard's own skip conditions before claiming it covers a case. Follow-ups: WI-PROMOTE-0118 is still open; registering linguistics.lexicon.json and science-fiction.json is in the backlog."

# Validation

CI 4/4 on the merged head 6c737df5; all three review threads resolved; the merge was SHA-locked.

# Follow-up

Execute WI-PROMOTE-0118; register the two unregistered sidecar kinds (backlog); re-link related_focus to the 1.0 focus after the WorldCon paper lands.
