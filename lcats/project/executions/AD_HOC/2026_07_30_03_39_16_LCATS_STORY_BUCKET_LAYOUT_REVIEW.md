---
execution_id: 2026_07_30_03_39_16_LCATS_STORY_BUCKET_LAYOUT_REVIEW
prompt_id: PROMPT(AD_HOC:LCATS_STORY_BUCKET_LAYOUT_REVIEW)[2026-07-30T03:26:13-04:00]
work_item: AD_HOC
status: in_progress
rerun_of: 2026_07_30_03_20_24_LCATS_STORY_BUCKET_LAYOUT
pr: https://github.com/xenotaur/LCATS/pull/196
commit: 6546259b
created_at: 2026-07-30T03:39:16-04:00
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/196
session_transcript: claude-app:ca0e8b20-2e3a-44f3-90b6-c506f3b98336
---

# Summary

Addressed 3 open P1 review comments from `chatgpt-codex-connector` on
`PROP-LCATS-STORY-BUCKET-LAYOUT`'s proposal PR, all substantive design gaps
rather than style nitpicks, each verified against the actual code before
being applied.

# Result

- **Migrate the mass-quantities writer too** — confirmed
  `parser.gather_story()` (`lcats/src/lcats/gatherers/parser.py:1468-1476`)
  independently constructs and writes to a flat path, unaffected by a
  `DataGatherer.ensure`-only fix, and is the write path
  `mass_quantities/gatherer.py:40-54` uses for LCATS's single-stories
  collection. Added Decision 8 to the proposal and folded this site into
  Stage 2's Implementation Plan scope, alongside its own parser tests.
- **Keep flat reads until the tracked corpus is migrated** — confirmed via
  `git ls-files corpora/`: 1,868 tracked flat `.json` files, 0 nested
  `story.json`. Revised Decision 4 and the Stage 3 Implementation Plan: dual-
  layout retraction is now a distinct follow-up step gated on the tracked
  corpus migration actually completing, not bundled into the same merge as
  Stage 3's other convergence work.
- **Enforce layout correctness on every promotion** — confirmed
  `CollectionSurveyResult.clean` (`promote.py:56-59`) returns `not
  self.findings`, so a `story_count == 0` collection is reported clean and
  `_copy_collection` (`promote.py:156-160`) copies it wholesale regardless.
  Revised Decision 6: validation moves from a one-time pre-promotion step to
  a standing part of `lcats promote` itself, rejecting zero-story or
  noncanonical collections on every run.
- Updated Cross-References with the newly-cited sites.

# Validation

- `./scripts/version tools` -> lcats 0.1.1.dev17+ge31c50a80.d20260729,
  ruff 0.15.0, black 25.11.0, Python 3.11.8
- `./scripts/format --check --diff` -> all 172 files unchanged, clean
- `./scripts/lint` -> all checks passed
- `./scripts/test` -> 1505 tests, 2 pre-existing failures
  (`test_utils_test.TestTestCaseWithTestData.test_get_test_path_default`,
  `test_get_test_path_filename`), confirmed unrelated to this change: this
  worktree's editable `lcats` install resolves to a *different* worktree
  (`lcats-docs-audit-7cff4e`, confirmed via `pip show lcats` ->
  `Editable project location`), an environment staleness issue independent
  of branch content. This PR touches zero Python files.
- `lrh validate` -> 0 errors, 49 pre-existing warnings, unchanged from the
  primary record's own validation run.

# Follow-up

- The stale editable-install path (pointing at `lcats-docs-audit-7cff4e`
  instead of this worktree) should be re-pointed via `pip install -e
  --force-reinstall` in this worktree — unrelated to this PR, flagged for
  separate attention.
