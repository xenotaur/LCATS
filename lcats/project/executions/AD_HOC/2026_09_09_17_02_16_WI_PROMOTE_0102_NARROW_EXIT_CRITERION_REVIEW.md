---
execution_id: 2026_09_09_17_02_16_WI_PROMOTE_0102_NARROW_EXIT_CRITERION_REVIEW
prompt_id: PROMPT(AD_HOC:WI_PROMOTE_0102_NARROW_EXIT_CRITERION_REVIEW)[2026-09-09T17:01:39+00:00]
work_item: AD_HOC
status: landed
rerun_of: 2026_09_09_16_46_04_WI_PROMOTE_0102_NARROW_EXIT_CRITERION
pr: https://github.com/xenotaur/LCATS/pull/430
commit: 6095bab82854b9bb3d4944e59378c10feadc2537
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/430
session_transcript: claude-app:6a2dbae2-adca-4a2a-92fe-2e95d3b2a4e0
created_at: 2026-09-09T17:02:16+00:00
---

# Summary

Review-response round for PR #430 (exit-criterion wording change). The
PR's automatic first-push review surfaced 3 findings: 1 minor from
`copilot-pull-request-reviewer`, 2 real P2s from `chatgpt-codex-connector`.
Note: none of these landed as GraphQL `reviewThreads` at the time of the
prior empty-thread confirm-fixes gate -- both bots posted after that
gate was approved, confirming the skill's own warning that reviewers post
after a push, not simultaneously.

# Result

- **"below" should be "above" (Copilot, fixed)**: the item-4 note said
  "exit criterion 3 below," but the criteria live in the frontmatter
  above, not a later section. Fixed.
- **False "replace out of scope entirely" claim (real P2, fixed)**:
  independently verified via `grep` that `_find_orphaned_sidecars()`
  (`promote.py:401`, WI-PROMOTE-0101's orphan guard, used by `replace`)
  calls `sidecar_validators.registered_filenames()` directly --
  contradicting the applied wording's claim that replace never uses the
  registry. Narrowed the exemption to payload-validation dispatch
  specifically in both `WS-PROMOTE-MODE-REDESIGN.md`'s exit criterion 3
  and the design note's own proposed wording.
- **Overwrite guard misattributed to replace (real P2, fixed)**:
  independently verified that the destination legacy-flat-genre.json
  overwrite guard lives in `_promote_sidecar_records` (`promote.py:909-929`),
  reached only by insert/upsert -- `replace`'s own `_validate_sidecars`
  performs only shape-detection, never destination-overwrite guarding.
  Split `WI-PROMOTE-0097`'s acceptance criterion text into the two
  correctly-attributed usages; updated the design note's own proposed
  wording to match, since the same conflation originated there.

# Validation

- `lrh validate`: 0 errors.
- Both P2 findings independently re-verified via direct `grep`/source
  read against the real repo, not the reviewer's own prose.

# Follow-up

- None outstanding from this round. Proceeding to confirm-fixes next.
