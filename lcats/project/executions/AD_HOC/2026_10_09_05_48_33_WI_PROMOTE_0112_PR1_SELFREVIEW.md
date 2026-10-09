---
execution_id: 2026_10_09_05_48_33_WI_PROMOTE_0112_PR1_SELFREVIEW
prompt_id: PROMPT(AD_HOC:WI_PROMOTE_0112_PR1_SELFREVIEW)[2026-10-09T05:48:26+00:00]
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

PR-mode substitute review signal #1 for PR #486, at head 9bcd789b (after review
rounds 1 and 2). Hosted bots had reviewed only earlier commits (Codex 42d24037,
Copilot 2c1a3c2b), so a cold subagent reviewed the live PR instead of any bot
retrigger. Created at closeout so the reviewed head stayed the merged head only
for the final round; this earlier head was superseded by fixes below.

# Result

- Findings: 0 blocking; 3 minor, all verified by the invoking session.
  - Stale PR body (33 tests / 2498 suite; guard additions missing): fixed by a PR
    body edit that did not move the head.
  - Case-insensitive bypass of the protected-output-tree guard: reproduced on a
    scratch directory (a miscased --manifest-out into a protected tree exited 0
    and wrote there). Fixed in 03c17856 by comparing file identity
    (os.path.samefile) alongside the path comparison; 3 tests added.
  - Cwd-relative default roots (../corpora, data): the repo's own corpora/ and
    lcats/data are always protected; a populated data/ outside the repo is
    protected only via LCATS_DATA_DIR. Documented in the tool docstring.
- Substitute review signal; findings were routed to the human, who chose
  "fix it"; fixed in a follow-up commit, not by the review itself.

# Validation

- Subagent report cross-checked against my own reproduction; lrh validate:
  0 errors.

# Follow-up

- Superseded by the next PR-mode self-review (record PR2) on the fixed head.
