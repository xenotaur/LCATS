---
execution_id: 2026_10_10_00_06_49_WI_PROMOTE_0115_PR1_SELFREVIEW
prompt_id: PROMPT(AD_HOC:WI_PROMOTE_0115_PR1_SELFREVIEW)[2026-10-10T00:06:44+00:00]
work_item: AD_HOC
status: landed
rerun_of: 2026_10_09_17_33_04_WI_PROMOTE_0115
pr: https://github.com/xenotaur/LCATS/pull/491
commit: fa7f167ad3a2bcc1fb73d7616319cb82af390622
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/491
session_transcript: claude-app:6a2dbae2-adca-4a2a-92fe-2e95d3b2a4e0
created_at: 2026-10-10T00:06:49+00:00
---

# Summary

PR-mode substitute review signal for PR #491 (planning PR for
WI-PROMOTE-0115) at the final head 6d8ec516, the head that merged. Hosted bots
had reviewed only earlier commits (Codex 0bf4362f, Copilot 3077014d), so a cold
subagent reviewed the live PR instead of any bot retrigger. This record was
created at closeout, so the reviewed head stayed the merged head.

# Result

- Findings: 0 blocking, 6 minor notes; it judged the PR safe to merge as-is.
  The subagent reproduced the work item's factual claims on its own scratch
  copies: the 7 blocked collections (orphan counts summing to 146), the seed
  manifest covering exactly those 7 collections (hemingway and sherlock have 0),
  the full-manifest insert on empty data/ (146 would promote, exit 0; a second
  insert exit 1 with 146 rejected), a seeded `replace --dry-run` (12 would
  promote, 0 blocked), `survey --mode specials` exit 0 on seeded and unseeded
  copies, the single-collection claim (after a scoped wodehouse clean, a
  full-manifest dry-run gave 12 would promote and 134 rejected, exit 1; the
  `grep -F` filter gave 12 lines and a clean dry-run, real insert and scoped
  replace), and the non-transactional claim (a bad record still leaves all 146
  good sidecars written; a retry collides on all 146). It also confirmed the
  placement default "3b" needs no renumbering and the only incoming step
  reference (cli-commands.md "step 2") stays valid.
- Two notes deferred as optional spec hardening (deliberately not applied, to
  keep the reviewed head the merged head): (1) the filtered-manifest "0 lines
  means nothing to seed" check depends on the tool's exact JSON spacing; a
  cross-check that the per-collection counts sum to 146 would harden it, and a
  format change would currently fail loudly later because the scoped replace
  stays blocked; (2) the spec does not state that the manifest output must be
  outside corpora/, the repo's lcats/data and the configured roots (re-verified:
  `--manifest-out data/seed.jsonl` exits 2); the executor should write the doc
  example to a temp directory. Both will surface when the executor runs and
  records every command on scratch copies, as the work item requires.
- Also noted: the design note's drafted step 6b ordering (after the preview) is
  wrong and the work item corrects it; the executor may add a one-line pointer.
  The PR body was re-synced after the review fixes via a body edit that did not
  move the head.
- Substitute review signal, not a follow-up for a non-thread finding; no finding
  routed to confirm-fixes.

# Validation

- Subagent report cross-checked by the invoking session (re-verified the
  output-path guard note); lrh validate: 0 errors.

# Follow-up

- Executor of WI-PROMOTE-0115: write doc examples' manifest path outside the
  protected trees, and consider the sum-to-146 cross-check for the scoped path.
