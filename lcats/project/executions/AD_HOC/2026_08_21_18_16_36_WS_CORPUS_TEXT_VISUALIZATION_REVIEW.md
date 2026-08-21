---
execution_id: 2026_08_21_18_16_36_WS_CORPUS_TEXT_VISUALIZATION_REVIEW
prompt_id: PROMPT(AD_HOC:WS_CORPUS_TEXT_VISUALIZATION_REVIEW)[2026-08-21T18:13:20+00:00]
work_item: AD_HOC
status: in_progress
rerun_of: 2026_08_21_17_55_30_WS_CORPUS_TEXT_VISUALIZATION
pr: https://github.com/xenotaur/LCATS/pull/335
commit: a7ece0b9
created_at: 2026-08-21T18:16:36+00:00
agent: claude-sonnet-5
instruction_source: https://github.com/xenotaur/LCATS/pull/335
session_transcript: pending
---

# Summary

Review-response round on PR #335 (WS-CORPUS-TEXT-VISUALIZATION /
WI-VISUALIZE-0073 creation). One open comment addressed.

# Result

**Fixed:** chatgpt-codex-connector (P1) — "Require sample scope on
census-derived figures." Verified the concern was valid: the WI's
acceptance criteria permitted `experiments/04_genre_census` as a genre
source for `lcats visualize genres` without qualifying that its checked-in
`census_sample_summary.json` currently covers only 20 of 1,868 stories
(`mode: "sample"`), which could let a paper-critical figure misrepresent
a small sample as the full corpus. Added an explicit acceptance criterion
to `WI-VISUALIZE-0073` and a matching exit criterion to
`WS-CORPUS-TEXT-VISUALIZATION` requiring the command/output to disclose
source population, sample size/mode, and denominator whenever a
non-full-corpus source is used, and requiring a full-corpus artifact for
corpus-wide figures. Also added a corresponding Risk Note to the WI.

**Skipped:** none.

# Validation

- Environment: editable `lcats` install had drifted to a different
  worktree (concurrent session); re-ran `scripts/develop`, confirmed
  `python3 -c "import lcats; print(lcats.__file__)"` now resolves to this
  worktree.
- `scripts/version tools`: ruff 0.15.0, black 25.11.0 (match pinned
  versions).
- `scripts/format --check --diff`: 194 files unchanged, 0 diff.
- `scripts/lint`: ruff and black checks both pass.
- `scripts/test`: 1813 tests, OK.
- `lrh validate`: 0 errors, 166 pre-existing warnings unrelated to this
  change.
- Pushed directly to `xenotaur/feat/ws-corpus-text-visualization` at
  commit `a7ece0b9`.

# Follow-up

- `session_transcript` is `pending` — update to the durable session
  pointer when available.
- Recommend `/lrh-confirm-fixes https://github.com/xenotaur/LCATS/pull/335`
  next to verify the fix against the live diff and resolve the review
  thread before merge.
