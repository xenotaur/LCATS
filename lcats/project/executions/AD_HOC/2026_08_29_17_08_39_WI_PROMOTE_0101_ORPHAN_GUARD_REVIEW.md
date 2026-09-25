---
execution_id: 2026_08_29_17_08_39_WI_PROMOTE_0101_ORPHAN_GUARD_REVIEW
prompt_id: PROMPT(AD_HOC:WI_PROMOTE_0101_ORPHAN_GUARD_REVIEW)[2026-08-29T17:08:34+00:00]
work_item: AD_HOC
status: landed
rerun_of: 2026_08_29_17_01_30_WI_PROMOTE_0101
pr: https://github.com/xenotaur/LCATS/pull/416
commit: a19322d28fb09fa3cd70000a3cc5ed9cd523fbff
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/416
session_transcript: claude-app:6a2dbae2-adca-4a2a-92fe-2e95d3b2a4e0
created_at: 2026-08-29T17:08:39+00:00
---

# Summary

Review-response round for PR #416 (`WI-PROMOTE-0101` implementation).
The PR's automatic first-push review surfaced 2 real findings from
`copilot-pull-request-reviewer`, one a genuine P1-class bug.

# Result

- **Destination-only story wrongly flagged as orphaned (real bug,
  fixed)**: `_find_orphaned_sidecars()` iterated every destination
  story bucket and flagged any registered sidecar missing from the
  corresponding source path — including a story that doesn't exist in
  source *at all*. A wholesale `replace` legitimately removes such a
  retired story entirely, sidecars included; that's not the "sidecar
  quietly lost while the story survives" scenario the guard exists to
  catch. Independently confirmed present via a real end-to-end repro
  before fixing. Fixed by skipping any story whose source bucket lacks
  `story.json` entirely, before checking its sidecars — only a story
  present in *both* trees can have an orphaned sidecar. Added
  `test_destination_only_story_with_sidecar_does_not_block_replace` as
  a regression test.
- **Missing encoding on a new test's `read_text()` call (fixed)**:
  inconsistent with the rest of the file's UTF-8 convention. Added
  `encoding="utf-8"`.

# Validation

- `scripts/version tools`: ruff/black drifted mid-session again (black
  26.3.1 vs. pinned 25.11.0); re-pinned via `pip install -q
  "ruff==0.15.0" "black==25.11.0"`, re-verified.
- `scripts/format --check --diff`: clean (1 file needed reformatting
  after the fix, applied via `scripts/format`).
- `scripts/lint`: clean.
- `scripts/test` (targeted): `tests/analysis_tests/promote_test.py` —
  101 tests, all pass.
- Manual repro of the destination-only-story false positive before and
  after the fix, confirming the fix resolves it.

# Follow-up

- None outstanding from this round. Proceeding to confirm-fixes next to
  verify the fix against the current diff and resolve the review
  threads.
