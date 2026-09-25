---
execution_id: 2026_08_28_07_10_23_WI_PROMOTE_0097_CLOSEOUT_NOTE
prompt_id: PROMPT(AD_HOC:WI_PROMOTE_0097_CLOSEOUT_NOTE)[2026-08-28T07:10:18+00:00]
work_item: AD_HOC
status: landed
rerun_of: 2026_08_28_06_56_20_WI_PROMOTE_0097_CONFIRM
pr: https://github.com/xenotaur/LCATS/pull/405
commit: 9665a2d44544941b476e47015bf7f178a3ed7289
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/405
session_transcript: pending
created_at: 2026-08-28T07:10:23+00:00
---

# Summary

Closeout note for PR #405 — implemented and merged `WI-PROMOTE-0097`
(Stage 1 of `WS-PROMOTE-MODE-REDESIGN`): mandatory insert/upsert/replace
modes and a shared sidecar-validator registry for `lcats promote`.

# Result

CHAIN-NOTE: PR #405 merged to `main` at `9665a2d4`
(`https://github.com/xenotaur/LCATS/pull/405`). `lcats promote` now
requires an explicit `insert`/`upsert`/`replace` mode; `promote_sidecar_
tranche()` generalized into `promote_sidecar_insert()`/
`promote_sidecar_upsert()` sharing one manifest-envelope-driven engine;
a new `sidecar_validators.py` registry covers all 4 produced sidecar
kinds. One review round (7 findings — 4 `copilot-pull-request-reviewer`,
3 P1 `chatgpt-codex-connector`, including a real regression against
`WI-GENRE-0077`'s only existing manifest) was fixed and all threads
resolved. Confirm-fixes verdict was Green at commit `15e8096b`; CI green
throughout. Merged via `gh pr merge --match-head-commit
15e8096b2445f4d13f9755ca3ff2c188d6689660`.

Execution record chain for this PR:
- Primary: `2026_08_28_06_43_07_WI_PROMOTE_0097` (status: landed)
- Review-response: `2026_08_28_06_53_24_WI_PROMOTE_0097_REVIEW` (status: landed)
- Confirm-fixes: `2026_08_28_06_56_20_WI_PROMOTE_0097_CONFIRM` (status: landed)
- This closeout note (status: landed)

`WI-PROMOTE-0097` moved to `project/work_items/resolved/` with a
populated `resolution:` field. `WS-PROMOTE-MODE-REDESIGN` updated: item 1
of its Proposed Work Items marked Resolved, and both of its Open
Questions (registry module location, `--allow-unvalidated` scope) marked
resolved by this item. The workstream itself remains `status: active`,
`stage: planned` — Stage 2 (`replace`'s orphaned-sidecar guard) and
Stage 3 (live-directory-scan sourcing) are still unminted, both
depending on this item's registry.

# Validation

- `gh pr view https://github.com/xenotaur/LCATS/pull/405 --json
  state,mergedAt,mergeCommit`: confirmed `MERGED` at `9665a2d4`.
- `lrh validate`: 0 new errors introduced by this closeout's files.

# Follow-up

- Stage 2 and Stage 3 work items remain to be minted when the team is
  ready — both depend on `WI-PROMOTE-0097`'s registry, now landed.
- `WI-GENRE-0077`/PR #362 remains intentionally open awaiting
  broader-team review — unaffected by this closeout, and its existing
  manifest stays consumable via the bare-record compatibility path
  added in this PR's review round.
