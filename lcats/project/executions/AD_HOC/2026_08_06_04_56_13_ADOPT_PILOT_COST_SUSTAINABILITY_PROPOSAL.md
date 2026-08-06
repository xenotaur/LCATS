---
execution_id: 2026_08_06_04_56_13_ADOPT_PILOT_COST_SUSTAINABILITY_PROPOSAL
prompt_id: PROMPT(AD_HOC:ADOPT_PILOT_COST_SUSTAINABILITY_PROPOSAL)[2026-08-06T04:54:46+00:00]
work_item: AD_HOC
status: in_progress
rerun_of:
pr: https://github.com/xenotaur/LCATS/pull/231
commit:
agent: claude_app
instruction_source: user request in-session ("Adopt the proposal, then /lrh-workstream")
session_transcript: claude-app:6a2dbae2-adca-4a2a-92fe-2e95d3b2a4e0
created_at: 2026-08-06T04:56:13+00:00
---

# Summary

Adopted `PROP-LCATS-PILOT-COST-SUSTAINABILITY` (merged as `proposed` in
PR #221) - moved it to `adopted/`, updated its own status and its
proposal-set README, and updated the top-level catalog.

# Result

- `git mv`'d `project/design/proposals/proposed/lcats-pilot-cost-sustainability/`
  to `adopted/`; set `status: adopted` in `00_proposal.md` and its
  `README.md`.
- Updated the top-level `project/design/proposals/README.md` catalog
  entry to point at the `adopted/` path.
- Following this project's own established precedent for adoption PRs
  (`59a0b49a`, adopting `PROP-LCATS-PIPELINE-CHECKPOINTING`, which
  fixed adjacent staleness noticed in the same file while adopting):
  found and fixed two stale entries for `PROP-LCATS-PIPELINE-CHECKPOINTING`
  itself - its `implementation_status: not_started`/`implemented_by: []`
  hadn't been updated since `WI-PIPELINE-0040`/`0041` resolved and
  `WS-PIPELINE-CHECKPOINTING` closed (2026-08-03), and its README's
  "Governed by" link pointed at `workstreams/proposed/` when the
  workstream is actually under `workstreams/resolved/`. Fixed both,
  verified the real file location via `find` before editing the link.

# Validation

- `lrh validate` (from `lcats/`) - 0 errors, 73 warnings (unchanged
  baseline); confirmed no new warnings tied to either proposal's files.
- `gh pr diff 231 --name-only` confirmed only the intended files were
  in the PR diff at the time of this validation (the PR has since grown
  through review-response commits).

# Follow-up

- Next: `/lrh-workstream` to create the governing workstream for
  `PROP-LCATS-PILOT-COST-SUSTAINABILITY`'s Implementation Plan (test
  harness, prompt-caching evaluation, Batch API evaluation,
  model-tiering evaluation), per the user's own stated next step.
