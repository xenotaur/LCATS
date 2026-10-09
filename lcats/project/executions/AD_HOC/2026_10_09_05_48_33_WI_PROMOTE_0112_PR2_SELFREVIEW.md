---
execution_id: 2026_10_09_05_48_33_WI_PROMOTE_0112_PR2_SELFREVIEW
prompt_id: PROMPT(AD_HOC:WI_PROMOTE_0112_PR2_SELFREVIEW)[2026-10-09T05:48:26+00:00]
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

PR-mode substitute review signal #2 for PR #486, at head 03c17856 (after the
case-insensitive protected-tree fix). Neither hosted bot had reviewed the fix
commits, so a cold subagent reviewed the live PR.

# Result

- Findings: 0 regressions; the previous fix was confirmed independently (miscased
  paths, nested paths, symlinked parents and relative roots into a protected
  tree all exit 2 and write nothing; mutation check failed exactly the
  miscased-path test). One new real finding, verified by the invoking session:
  - The evidence-overwrite guard in main() still compared resolved paths as
    strings, so a miscased --manifest-out equal to the evidence file bypassed it,
    exited 0 and overwrote the evidence (reproduced on a scratch copy only: its
    sha256 changed). Same bug class as the previous round, missed there. Fixed in
    9c67524e with a shared same_file() helper (os.path.samefile when both paths
    exist, resolved-path fallback otherwise); 3 tests added.
  - PR body staleness (33 tests / 2498): re-synced via a body edit.
- Substitute review signal; the finding was routed to the human, who chose
  "fix it".

# Validation

- Subagent report cross-checked against my own reproduction; lrh validate:
  0 errors.

# Follow-up

- Superseded by the next PR-mode self-review (record PR3) on the fixed head.
