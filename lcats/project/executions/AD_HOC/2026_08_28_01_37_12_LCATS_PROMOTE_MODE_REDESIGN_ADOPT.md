---
execution_id: 2026_08_28_01_37_12_LCATS_PROMOTE_MODE_REDESIGN_ADOPT
prompt_id: PROMPT(AD_HOC:LCATS_PROMOTE_MODE_REDESIGN_ADOPT)[2026-08-28T01:36:47+00:00]
work_item: AD_HOC
status: landed
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/401
commit: a639fe837274380ac106d5e9c7e1dfb5865630dc
agent: claude_app
instruction_source: project/design/proposals/adopted/lcats-promote-mode-redesign/00_proposal.md
session_transcript: claude-app:6a2dbae2-adca-4a2a-92fe-2e95d3b2a4e0
created_at: 2026-08-28T01:37:12+00:00
---

# Summary

Adopted `PROP-LCATS-PROMOTE-MODE-REDESIGN`, activated
`WS-PROMOTE-MODE-REDESIGN`, and minted the workstream's Stage-1 work
item, `WI-PROMOTE-0097`, per explicit user instruction ("Adopt both and
mint the first work item").

# Result

- Moved the proposal `project/design/proposals/proposed/lcats-promote-
  mode-redesign/00_proposal.md` to `adopted/` via `git mv`; updated
  `status: proposed` → `adopted` and added `WI-PROMOTE-0097` to
  `implemented_by:`.
- Moved the workstream `project/workstreams/proposed/WS-PROMOTE-MODE-
  REDESIGN.md` to `active/` (created the `workstreams/active/` directory
  - no workstream in this repo had ever reached `active` status before)
  via `git mv`; updated `status: proposed` → `active`, `stage: designed`
  → `planned`, added `WI-PROMOTE-0097` to `work_items:`, fixed a stale
  `related_design` path to the proposal (still pointed at its old
  `proposed/` location), marked item 1 of "Proposed Work Items" as
  scoped to the new WI, and removed a now-inaccurate "does not create
  child work items in this PR" line from Non-Goals.
- Created `WI-PROMOTE-0097` (next global WI number, verified via `find
  project/work_items/ -name "WI-*.md" | sed ... | sort -n | tail`):
  Stage 1 of the workstream's own staged breakdown - mandatory `insert`/
  `upsert`/`replace` modes, the sidecar-validator registry covering all
  4 currently-produced kinds, uniform validation requirement, and the
  `--sidecar` flag. `forbidden_actions`/Non-Goals explicitly exclude
  Stage 2 (`replace`'s orphaned-sidecar guard) and Stage 3
  (live-directory-scan sourcing).
- A diff-mode `/lrh-self-review` pass before this PR's first push found
  and fixed 1 real issue: `WI-PROMOTE-0097` cited `docs/reference/*.md`
  (repo-root-relative) in 3 places (acceptance criteria,
  `artifacts_expected`, Required Change 5), but no `docs/` directory
  exists at the repo root - the real files live at
  `lcats/docs/reference/*.md`, matching the WI's own convention for
  every other path it cites. Fixed in all 3 locations, independently
  re-verified before accepting the finding.
- Grepped the whole repo for stale references to either artifact's old
  `proposed/` path after the moves: only one hit, an intentionally-
  historical execution record (`2026_08_23_05_21_06_LCATS_PROMOTE_MODE_
  REDESIGN.md`'s own `instruction_source:`, correctly left as a
  point-in-time reference per this project's established convention).

# Validation

- `scripts/version tools`: repaired shared-env drift (editable install
  pointed at an unrelated worktree; ruff/black pins drifted) before
  trusting any result.
- `scripts/format --check --diff`: clean (no code changed in this PR).
- `lrh validate`: 0 errors attributable to any of the 3 changed files;
  confirmed no bucket/status mismatch warnings for either moved file.
  Only the repo's existing baseline (owner-unassigned on the new WI,
  matching every other WI created this way; absolute-path warnings on
  unrelated pre-existing closeout notes).

# Follow-up

- Stage 2 (`replace`'s orphaned-sidecar guard) and Stage 3
  (live-directory-scan sourcing for `insert`/`upsert`) remain unminted,
  both depending on `WI-PROMOTE-0097`'s registry once it lands.
- PR #362 (`WI-GENRE-0077`) remains open, awaiting broader-team review
  per explicit prior user instruction - unaffected by this PR, but its
  own CLI-syntax description will need revisiting once `WI-PROMOTE-0097`
  changes `lcats promote`'s command shape.
