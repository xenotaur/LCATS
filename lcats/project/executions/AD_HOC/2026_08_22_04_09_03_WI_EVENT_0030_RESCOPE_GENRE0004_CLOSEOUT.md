---
execution_id: 2026_08_22_04_09_03_WI_EVENT_0030_RESCOPE_GENRE0004_CLOSEOUT
prompt_id: PROMPT(AD_HOC:WI_EVENT_0030_RESCOPE_GENRE0004_CLOSEOUT)[2026-08-22T04:08:56+00:00]
work_item: AD_HOC
status: landed
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/340
commit: 0b92579d
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/340
session_transcript: claude-app:e8e46d5d-35d3-4ccc-9cba-137bd31bf3a5
created_at: 2026-08-22T04:09:03+00:00
---

# Summary

Backfill primary execution record for PR #340 ("Re-scope WI-EVENT-0030 to
8 genres using WI-GENRE-0004's real numbers"), created per `/lrh-land`
Step 7's no-primary path — Step 1 found no existing execution record
referencing this PR's `pr:` field. This record is the primary for the PR;
the `_REVIEW`, `_CONFIRM`, and `_CONFIRM_SELFREVIEW` records already on
this PR are side records of it.

# Result

Re-scoped `WI-EVENT-0030.md`'s pilot design from 4 to all 8
`VALID_GENRES`, using `WI-GENRE-0004`'s real, committed corpus counts and
validation data (`experiments/05_metadata_genre_prefilter/results/full_scan/`)
instead of the prior placeholder estimates. A review round then caught a
real methodological flaw in the first pass: the "agreement rate" numbers
and selection rule used a loose multi-label match
(`agrees_with_metadata_rules`) rather than requiring
`detected_genre == target_candidates[0]` exactly — for western this had
made a real 40%-exact-match reliability look like 75%. Fixed throughout
(Scope, Required Changes, acceptance criteria, Risk Notes), along with an
inaccurate "10x smaller" comparison for the adventure stratum. A
substitute self-review round independently re-derived every per-genre
number from the raw evidence file and confirmed the fix. Merged via merge
commit `0b92579d`.

CHAIN-NOTE: cycles=1; stops=0; gates=[merge]; friction=review-caught-methodology-flaw; self_review_rounds=1; bot_rounds=1; note="Backfill path: no primary implementation record existed for this PR. A real hosted bot review round (chatgpt-codex-connector) caught a substantive methodology error in the first re-scope pass - the agreement-rate figures conflated a loose multi-label match with exact primary-genre agreement, most severely understating western's real unreliability (75% loose vs 40% exact). Both findings independently re-verified against the committed validation_results.jsonl before fixing, not just accepted from the review text. No automatic bot response landed on the _CONFIRM commit within a bounded 5-minute wait, so one PR-mode substitute self-review ran, itself independently recomputing every per-genre number from raw data and confirming the fix clean before merge."

# Validation

- `scripts/format --check --diff`, `scripts/lint`, `lrh validate` (0
  errors) — all run before each push on this PR
- CI (lint/test/coverage) green on the final merged commit
- Both GitHub review threads resolved
- Both findings independently re-verified against the raw
  `validation_results.jsonl` data (not just accepted from the review
  text) both before fixing and again during the substitute self-review

# Follow-up

- None outstanding on this PR's own scope. WI-EVENT-0030 itself remains
  `status: proposed` — this PR only re-scoped its content; the pilot's
  own execution is still gated on `depends_on` (WI-EVENT-0029,
  WI-ASSESS-0031, WI-GENRE-0004 — all now resolved), so it is ready to
  pick up as its own future execution.
- `session_transcript` above uses the host session ID with its `local_`
  prefix stripped; update if a more durable pointer becomes available.
