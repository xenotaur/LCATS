---
execution_id: 2026_08_08_00_16_13_WI_PILOT_0057_CLOSEOUT_NOTE
prompt_id: PROMPT(AD_HOC:WI_PILOT_0057_CLOSEOUT_NOTE)[2026-08-08T00:14:41+00:00]
work_item: AD_HOC
status: landed
rerun_of: 2026_08_07_23_18_58_WI_PILOT_0057_CONFIRM
pr: https://github.com/xenotaur/LCATS/pull/247
commit: ec6d0a49a164de15f754877ce29a8df156b9e708
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/247
session_transcript: claude-app:6a2dbae2-adca-4a2a-92fe-2e95d3b2a4e0
created_at: 2026-08-08T00:16:13+00:00
---

# Summary

Closeout for PR #247, which created `WI-PILOT-0057` (WI 2 of
`WS-PILOT-COST-SUSTAINABILITY`'s Implementation Plan: the prompt-caching
evaluation against `WI-PILOT-0051`'s fixture set) and registered it in
the governing workstream's `work_items:` list. Merged as
`ec6d0a49a164de15f754877ce29a8df156b9e708`, squash merge, confirmed as
`main`'s real tip via the GitHub API.

# Result

- PR #247 merged clean (`mergeStateStatus: CLEAN`) after one
  review/fix round on 3 passively-posted (not retriggered) Codex
  comments:
  1. P1: the WI's own acceptance criterion required
     `cache_read_input_tokens > 0`, contradicting its own "no real
     benefit is a complete outcome" criterion (a `tools`+`system`
     prefix below Anthropic's minimum cacheable length correctly
     produces zero) - fixed to require reporting the observed value
     (including zero) and added a new preflight-prefix-token-count
     Required Change.
  2. P1: the WI's measurement steps implied grouping same-extractor
     calls together, which could show a falsely inflated cache-hit
     rate versus the real pipeline's interleaved
     entity/event/relation/discourse call order given the 5-minute
     cache TTL - fixed to explicitly require preserving
     `processor.py:124-220`'s real call ordering and timing.
  3. P2: workstream registration claim - dismissed as stale, already
     fixed by an earlier commit on this same PR branch.
  - Both real fixes were independently re-verified by a fresh subagent
    review pass (no shared context) before the merge gate, per the
    confirm-fixes execution record, plus a direct self-check of the
    call-ordering fix.
- **CHAIN-NOTE:** cycles=1; stops=0; gates=[merge];
  friction=none; note="3 passive bot comments (repo's configured
  auto-review on PR open, not retriggered - honoring the standing
  quota-conservation policy throughout this PR and PR #244 before it),
  2 real design-level fixes to the WI's own acceptance criteria (not
  code, since this PR only creates a planning artifact), 1
  correctly-dismissed stale claim, clean single round, no billed bot
  retriggers used at any point in this PR's lifecycle."
- Confirmed `main`'s real tip via
  `gh api repos/xenotaur/LCATS/commits/main --jq '.sha'` ==
  `ec6d0a49a164de15f754877ce29a8df156b9e708`, matching the reported
  merge commit exactly.

# Validation

- `lrh validate` (from `lcats/`) - 0 errors.
- `gh pr view 247 --json state,mergedAt,mergeCommit` confirmed
  `state: MERGED`.
- GitHub API confirmed `main`'s tip matches the merge commit (see
  above) - single, non-stacked work-item-creation PR, no propagation
  gap applies.

# Follow-up

- `WI-PILOT-0057` is now `status: proposed`, ready for
  `lrh request ready-work-item` / `lrh request prompt-from-work-item`
  when implementation begins. Its real-call measurement step needs its
  own explicit human approval separate from any chain-authorization
  gate, per the WI's own Risk Notes.
- WI 3 (Batch API evaluation) and WI 4 (model-tiering evaluation) remain
  to be created, per the proposal's sequencing - both depend only on
  WI-PILOT-0051, not on WI-PILOT-0057's outcome.
- Numbering-collision backlog item (multiple concurrent sessions landing
  `WI-*-0051` under different prefixes) still outstanding - flagged to
  the user during this WI's implementation, not yet written up as a
  formal backlog entry.
