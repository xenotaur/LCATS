---
execution_id: 2026_09_04_05_59_24_WI_PROMOTE_0102_GENRE_SIDECAR_REGISTRY_ASSESSMENT_CLOSEOUT_NOTE
prompt_id: PROMPT(AD_HOC:WI_PROMOTE_0102_GENRE_SIDECAR_REGISTRY_ASSESSMENT_CLOSEOUT_NOTE)[2026-09-04T05:59:18+00:00]
work_item: AD_HOC
status: landed
rerun_of: 2026_09_04_05_27_55_WI_PROMOTE_0102
pr: https://github.com/xenotaur/LCATS/pull/427
commit: 4a41604487ee4fea2a8cc1d79a059174b52472f1
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/427
session_transcript: claude-app:6a2dbae2-adca-4a2a-92fe-2e95d3b2a4e0
created_at: 2026-09-04T05:59:24+00:00
---

# Summary

CHAIN-NOTE: closeout of PR #427 (`WI-PROMOTE-0102` implementation),
merged as `4a41604487ee4fea2a8cc1d79a059174b52472f1`.

CHAIN-NOTE: cycles=1; stops=0; gates=[chain_auth, confirm_fixes, merge];
friction=lrh-cli-drift; note="Straightforward implementation round: one
real Codex P2 finding (a self-contradiction in the design note's own
Recommendation section) was found, fixed, and independently
re-verified via a second substitute self-review round. One tooling
friction point: `lrh confirm-fixes check-batch-routine` no longer
exists as a CLI subcommand in the installed lrh version
(0.2.5.dev2333) -- fell back to the skill's own always_confirm
fail-safe and a live confirm gate, which the human approved."

# Result

- Landed all 4 execution records for PR #427 to `status: landed` with
  the real merge commit SHA: primary
  (`2026_09_04_05_27_55_WI_PROMOTE_0102`), review-response, confirm-fixes,
  substitute self-review.
- `WI-PROMOTE-0102` moved from `project/work_items/proposed/` to
  `project/work_items/resolved/`, `status: resolved`, `resolution:`
  populated with the full investigation summary.
- `WS-PROMOTE-MODE-REDESIGN.md`'s "Proposed Work Items" item 4 updated
  from "In progress (PR #417)" to "Resolved (PR #427)".

# Validation

- `lrh validate`: to be re-run on this closeout branch before push.

# Follow-up

- **Open decision, not yet applied**: `WI-PROMOTE-0102`'s own
  recommendation (narrow `WS-PROMOTE-MODE-REDESIGN`'s exit criterion 3
  and `WI-PROMOTE-0097`'s acceptance criterion, rather than a partial
  code swap) has NOT been applied to either file. `WS-PROMOTE-MODE-
  REDESIGN.md`'s exit criterion 3 still reads "no direct promote.py
  import of any producer subpackage" -- literally still unmet, by the
  investigation's own finding. The exact replacement text is in
  `project/design/promote-genre-sidecar-import-assessment.md`. This is
  flagged explicitly in the workstream file's item 4 entry and in this
  note; applying it (or deciding not to) is a human decision, not made
  here.
- Flag (recorded, not yet actioned): `lrh confirm-fixes` CLI subcommand
  missing in installed `lrh` 0.2.5.dev2333 -- worth investigating
  whether this is an intentional upstream rename/removal or local
  install drift, since this skill's own instructions still reference it.
- With `WI-PROMOTE-0102` now resolved, `WS-PROMOTE-MODE-REDESIGN`'s own
  `work_items:` list is again fully resolved -- but its exit criteria
  are not yet fully satisfied (criterion 3's wording gap above), so the
  workstream is not yet ready for closure despite that.
