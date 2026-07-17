---
execution_id: 2026_07_17_03_05_31_WI_RELEASE_0021_RUNBOOK_REVIEW
prompt_id: PROMPT(AD_HOC:WI_RELEASE_0021_RUNBOOK_REVIEW)[2026-07-17T02:58:05-04:00]
work_item: AD_HOC
status: in_progress
rerun_of: 2026_07_17_02_47_54_WI_RELEASE_0021
pr: https://github.com/xenotaur/LCATS/pull/127
commit: 
created_at: 2026-07-17T03:05:31-04:00
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/127
session_transcript: pending
---

# Summary

Address five review comments on PR #127 (WI-RELEASE-0021's runbook
implementation) via `lrh request review_response`: two P2 from
chatgpt-codex-connector, three from copilot-pull-request-reviewer.

# Result

All five fixed in commit eb40979, each confirmed against source before
fixing:

- Fragile `cd` in step 7b (P2) -- confirmed the bug live: if step 7a
  (one-time `corpora/ohenry`/`corpora/wilde` cleanup) is skipped because
  it was already done, the reader never leaves `lcats/`, so 7b's
  `cd lcats` would descend into `lcats/lcats` instead. Replaced both
  7a's and 7b's `cd` with a `git rev-parse --show-toplevel`-based
  absolute path, which is correct regardless of the reader's current
  directory or
  whether 7a ran.
- Unscoped verify/promote after a single-collection recheck (P2) --
  confirmed: `lcats promote` with no collection arguments considers
  every collection under `data/` (`promote_cli.py:22-26`), so following
  step 2's single-collection shortcut with the unscoped commands in
  steps 4/6/7 would survey/promote collections that were never
  regenerated in this run. Labeled the shortcut as diagnostic-only and
  added matching scoped survey/promote examples.
- Inaccurate "skips existing files" claim (copilot) -- confirmed this is
  only true for 11 of 12 gatherers. `mass_quantities` uses
  `parser.gather_story()` (`lcats/gatherers/parser.py:1474-1477`), which
  unconditionally overwrites via `open(file_path, "w")` with no
  existence check -- unlike the other gatherers, which route through
  `DataGatherer.download()` (`downloaders.py:226-230`, via
  `gatherlib.gather()`) and do skip existing files. Rewrote the
  rationale to lead with the risk that's true for every gatherer either
  way -- `lcats gather` never deletes stale outputs it no longer
  produces -- rather than a blanket "skips existing files" claim.
- Inaccurate "re-downloads... network-dependent" wording (copilot) --
  confirmed `DataGatherer.download()` routes through
  `ResourceCache.get()`/`.cache()` (`downloaders.py:93-101`), which skips
  the network entirely when `cache/resources` already holds the page.
  Reworded to state the cache-first behavior and point to the existing
  optional `cache/resources`-clearing note for a genuinely fresh run.
- Non-portable `rm -rf data/*` (copilot) -- confirmed the glob-failure
  risk (bash errors, zsh has `nomatch` on for an empty/missing `data/`).
  Replaced with `rm -rf data && mkdir -p data` (and the equivalent
  single-collection form), which has no glob to fail.

No comments skipped.

Self-caught during this same review pass (not from a reviewer comment):
`lrh prompt record-execution` was run one directory too deep -- cwd had
persisted at `lcats/` from a prior command, so `cd lcats` landed in
`lcats/lcats` (the Python package dir) and wrote this very file to a
stray `lcats/lcats/project/executions/AD_HOC/` tree. Caught immediately
via `pwd`, moved the file to the correct `lcats/project/executions/AD_HOC/`
path, and removed the stray directories before they could be staged.

# Validation

- `scripts/format --check --diff` -- clean, 149 files unchanged
- `scripts/lint` -- ruff + black pass
- `scripts/test` -- 1314 tests OK
- `lrh validate` -- 0 errors, 25 pre-existing owner-role/orphan warnings

# Follow-up

- On merge: set this record and the primary WI-RELEASE-0021 record to
  `landed` via `/lrh-closeout`.
- Unchanged from the primary record: the user will manually run the
  merged runbook end-to-end as independent verification of the repair
  pipeline; clean run resolves the three legacy WIs, issues found get
  fixed and re-verified first.
