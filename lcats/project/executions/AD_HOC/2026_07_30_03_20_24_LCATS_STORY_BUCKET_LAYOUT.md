---
execution_id: 2026_07_30_03_20_24_LCATS_STORY_BUCKET_LAYOUT
prompt_id: PROMPT(AD_HOC:LCATS_STORY_BUCKET_LAYOUT)[2026-07-30T03:09:03-04:00]
work_item: AD_HOC
status: in_progress
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/196
commit: 2aa4ab09
created_at: 2026-07-30T03:20:24-04:00
agent: claude_app
instruction_source: lcats/project/design/proposals/proposed/lcats-story-bucket-layout/00_proposal.md
session_transcript: claude-app:ca0e8b20-2e3a-44f3-90b6-c506f3b98336
---

# Summary

Created `PROP-LCATS-STORY-BUCKET-LAYOUT`, a design proposal for migrating
LCATS story storage from flat per-collection files
(`data/<collection>/<story>.json`) to per-story bucket directories
(`data/<collection>/<story>/story.json`), following a session-long
grounded analysis of `flat_story_layout_migration_impact_report.md`
(scope assessment, `/lrh-design` walkthrough, and follow-up complicating-
factors review) that preceded this skill run.

# Result

- Wrote `lcats/project/design/proposals/proposed/lcats-story-bucket-layout/00_proposal.md`
  and its set `README.md`, and registered the set in
  `lcats/project/design/proposals/README.md`'s "Current proposal sets" index.
- The proposal adopts a staged expand-contract migration (Fowler's Parallel
  Change pattern) matching the impact report's own 3-stage recommendation,
  and resolves the report's four deferred design questions (canonical
  identity = directory slug; discovery predicate = canonical `story.json`
  filename only; dual-layout window bounded to this migration, not
  permanent; output schema gets a new `story_dir`/`story_slug` column
  rather than repurposing `story_file`).
- Two acceptance criteria beyond the original 16-site inventory were added
  during this session's follow-up analysis and folded into the existing
  stages (not new stages): a 4th identity-collapse site in gather-time
  overrides keying (`lcats/src/lcats/gatherers/downloaders.py:249`), and an
  explicit end-to-end gather-then-promote validation step required before
  the first real post-migration promotion, since `lcats promote`'s
  existing survey gate (`lcats/src/lcats/analysis/corpus/promote.py:27`)
  checks encoding damage only, not layout correctness.
- Four related-but-excluded follow-ons were made explicit in the proposal's
  Non-Goals with cross-references to where each belongs: `lcats gather`
  incremental/restartable checkpointing (`PROP-LCATS-PIPELINE-CHECKPOINTING`'s
  own deferred scope), two notebooks with hardcoded flat-layout paths, two
  `experiments/` scripts with silent-failure (non-recursive glob) bugs plus
  a stem-collision output-naming bug, and a larger librarize-and-test
  architecture question for `notebooks/`/`experiments/` code living outside
  the installable package.
- Branch `xenotaur/feat/lcats-story-bucket-layout` created from `origin/main`
  (this worktree's own branch tip had fallen behind `origin/main`, and
  worktrees cannot `git checkout main` directly since another worktree has
  it checked out).

# Validation

- `lrh validate` -> 0 errors, 49 pre-existing warnings (all
  `OWNER_ROLE_INSUFFICIENT`/`OWNER_NOT_IN_CONTRIBUTORS` on unrelated
  work items; none touch the new files).

# Follow-up

- After adoption: create a `/lrh-workstream` for the 3-stage implementation
  (work items matching Stage 1 read-path, Stage 2 write-path, Stage 3
  convergence-and-validation).
- The four Non-Goals follow-ons (gather incrementality, notebook fixes,
  experiment fixes, librarize-and-test investigation) each need their own
  future scoping — not part of this proposal or its eventual workstream.
