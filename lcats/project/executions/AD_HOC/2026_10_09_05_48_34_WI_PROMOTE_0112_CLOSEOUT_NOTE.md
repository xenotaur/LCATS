---
execution_id: 2026_10_09_05_48_34_WI_PROMOTE_0112_CLOSEOUT_NOTE
prompt_id: PROMPT(AD_HOC:WI_PROMOTE_0112_CLOSEOUT_NOTE)[2026-10-09T05:48:26+00:00]
work_item: AD_HOC
status: landed
rerun_of: 2026_10_08_06_39_54_WI_PROMOTE_0112
pr: https://github.com/xenotaur/LCATS/pull/486
commit: f7ba7fb612bfd84b2a18e22fb7c9c46174457a59
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/486
session_transcript: claude-app:6a2dbae2-adca-4a2a-92fe-2e95d3b2a4e0
created_at: 2026-10-09T05:48:34+00:00
---

# Summary

CHAIN-NOTE: closeout of PR #486 (WI-PROMOTE-0112), squash-merged as
`f7ba7fb612bfd84b2a18e22fb7c9c46174457a59`.

CHAIN-NOTE: cycles=4; stops=1; gates=[chain, review, confirm_fixes, merge];
self_review_rounds=4; friction=same-bug-class-fixed-over-three-rounds;
note="Five review threads fixed and resolved (payload validation,
unreadable-evidence handling, protected output paths). Two further real
findings from substitute self-reviews, both case-insensitive path comparisons
(first the protected-tree guard, then the evidence-overwrite guard), were fixed
in separate rounds; a final self-review hunting for the same class found
nothing. One deliberate stop: a stray 'merge it' at a review-response gate was
not treated as authorization. The bug class should have been fixed in one pass:
after fixing the protected-roots comparison I did not audit the other path
comparison in the same file."

# Result

- Landed the execution records for PR #486 to `status: landed` with the real
  merge commit.
- Resolved WI-PROMOTE-0112.

# Validation

- lrh validate: to be re-run on this closeout branch before push.

# Follow-up

- Runbook step 6b (design-note follow-up 2) is not yet drafted, so the seed step
  is not part of the documented release procedure yet.
- Remaining design-note follow-ups: other-sidecar-kind rule and preflight;
  optional story-text fingerprint.
- The orphan-guard Copilot thread on PR #362 can now be answered: the seed
  tool exists and is verified on scratch copies.
