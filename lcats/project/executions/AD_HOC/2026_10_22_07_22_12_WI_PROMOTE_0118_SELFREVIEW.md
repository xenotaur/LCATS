---
execution_id: 2026_10_22_07_22_12_WI_PROMOTE_0118_SELFREVIEW
prompt_id: PROMPT(AD_HOC:WI_PROMOTE_0118_SELFREVIEW)[2026-10-22T07:14:13+00:00]
work_item: AD_HOC
status: in_progress
rerun_of:
pr:
commit:
created_at: 2026-10-22T07:22:12+00:00
---

# Summary

Diff-mode self-review (cold subagent, report-only) of the uncommitted WI-PROMOTE-0118 working-tree changes before the first push. The reviewer rebuilt every number from raw files, including the 146 checkpoint hashes in the sibling worktree.

# Result

All quantitative claims held (146 of 146 on every comparison). Three claims were wrong and are fixed: (1) the note said science fiction checks its story hash against the source; it only checks internal consistency against the sidecar's own top-level story_hash (models.py:705,722) and hashes normalized text; (2) the note and backlog called the checkpoints untracked; they are gitignored (.gitignore:137), so git status does not show them and git clean -fdx, a fresh clone or removing the worktree loses them; (3) the note cited full_scan/summary.json as the run's summary, but it is the selection dry-run's. I verified each by reading the code, git check-ignore and the summary files before editing. Four low items were applied: the local-model checkpoint set and the only-copy question were measurable and are now stated (gpt-oss:20b, hashes equal for 146 of 146; one worktree only); a reproduction row for checkpoint-to-assessment equality (generated_at and input_tokens, 146 of 146, which I re-ran); the prototype is stated as restricted to the wodehouse entries; the run id is given in full.

# Validation

lrh validate: 0 errors after the fixes. The fixes were doc edits I checked myself; the cold reviewer did not re-read them.

# Follow-up

None for this record.
