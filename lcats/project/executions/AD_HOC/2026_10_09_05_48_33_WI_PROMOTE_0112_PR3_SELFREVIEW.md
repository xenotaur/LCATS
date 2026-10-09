---
execution_id: 2026_10_09_05_48_33_WI_PROMOTE_0112_PR3_SELFREVIEW
prompt_id: PROMPT(AD_HOC:WI_PROMOTE_0112_PR3_SELFREVIEW)[2026-10-09T05:48:26+00:00]
work_item: AD_HOC
status: landed
rerun_of: 2026_10_08_06_39_54_WI_PROMOTE_0112
pr: https://github.com/xenotaur/LCATS/pull/486
commit: f7ba7fb612bfd84b2a18e22fb7c9c46174457a59
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/486
session_transcript: claude-app:6a2dbae2-adca-4a2a-92fe-2e95d3b2a4e0
created_at: 2026-10-09T05:48:33+00:00
---

# Summary

PR-mode substitute review signal #3 for PR #486, at the final head 9c67524e (the
head that merged). Neither hosted bot reviewed the fix commits, so a cold
subagent reviewed the live PR; it was told to hunt for any remaining gap of the
case-insensitive-comparison class.

# Result

- Findings: 0 real or material issues; judged safe to merge as-is. It verified
  both guard fixes independently and probed: miscased and nested paths, hard
  links, a symlink to the evidence file as the final component, a symlinked
  directory leading to the evidence, `..` traversal, an --evidence that is
  itself a symlink, an existing directory as --manifest-out, and a dangling
  symlink; all refused or harmless. The atomic write (mkstemp in the output's
  directory plus os.replace) cannot corrupt a hard-link or symlink target.
  Mutation checks on both guards failed the expected tests.
- Re-verified by the invoking session: a symlink to the evidence file as the
  output exits 2 with the evidence hash unchanged (scratch copy).
- The subagent's extracted-archive run showed 8 failures and 1 error in
  worldcon_spike_test; unrelated to this PR and an artifact of a git-archive
  extract lacking untracked/ignored files. In the real worktree scripts/test
  passes (2504 OK) and CI passes.
- No commits were pushed after this review, so the reviewed head is the merged
  head.

# Validation

- Seed flow reproduced by the subagent on scratch copies: insert dry-run 146,
  insert exit 0, second insert exit 1 with 146 rejected, bare replace exit 0 with
  0 blocked and 146 byte-identical genre.json; unseeded control exit 1.
- lrh validate: 0 errors.

# Follow-up

- None.
