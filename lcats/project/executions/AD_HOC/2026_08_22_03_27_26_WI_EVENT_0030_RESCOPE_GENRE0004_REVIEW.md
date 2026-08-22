---
execution_id: 2026_08_22_03_27_26_WI_EVENT_0030_RESCOPE_GENRE0004_REVIEW
prompt_id: PROMPT(AD_HOC:WI_EVENT_0030_RESCOPE_GENRE0004_REVIEW)[2026-08-22T00:00:28+00:00]
work_item: AD_HOC
status: landed
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/340
commit: 0b92579d
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/340
session_transcript: claude-app:e8e46d5d-35d3-4ccc-9cba-137bd31bf3a5
created_at: 2026-08-22T03:27:26+00:00
---

# Summary

Address two open review comments on PR #340 (re-scoping WI-EVENT-0030 to
8 genres using WI-GENRE-0004's real numbers). No primary implementation
execution record exists for this PR (Step 1 of `/lrh-land` found none) —
this is the first execution record authored against it.

# Result

Both comments from `chatgpt-codex-connector` exposed a real defect in the
re-scope's own methodology, not just wording:

**P1 (confirmed by direct re-verification against the committed data):**
the re-scope's "prefer stories where the two labels agree" selection rule
and its quoted per-genre agreement rates used `WI-GENRE-0004`'s
`agrees_with_metadata_rules` flag, which is `detected_genre` appearing
*anywhere* in `target_candidates` (a loose multi-label match), not
confirmation of the primary/selection genre. Independently queried
`experiments/05_metadata_genre_prefilter/results/full_scan/validation_results.jsonl`:
of western's 15 "agreeing" stories, 7 are actually model-detected as a
different genre (6 as `adventure`, 1 as `romance` — mostly Jack London
stories the metadata rules tag both `western` and `adventure`) — only
8/20 truly match the western stratum by exact primary-genre match, not
15/20. Recomputed exact-match rates (`detected_genre ==
target_candidates[0]`) for all 8 genres: western drops sharply from 75%
(loose) to **40%** (exact); science fiction drops slightly from 95% to
90%; the other 6 genres are unchanged (fantasy/horror 100%, mystery 90%,
adventure 83%, humor 80%, romance 70%) — for those, whenever the model
agreed at all, it agreed with the primary genre specifically.

**P2 (confirmed):** the Risk Notes claimed adventure's 6-story stratum
was "10x smaller" than the other genres' strata, but those target only
5-10 stories each — nowhere near a 10x gap.

Fixed in `lcats/project/work_items/proposed/WI-EVENT-0030.md`: changed
the selection rule (Scope, Required Changes, acceptance criteria) to
require the exact match `detected_genre == target_candidates[0]`
throughout, replaced every quoted agreement-rate figure with the
recomputed exact-match numbers, and rewrote the Risk Notes' genre-label-
reliability paragraph to correctly identify western — not romance — as
the real outlier, plus fixed the "10x" comparison to describe the actual
relative stratum sizes.

# Validation

- `scripts/format --check --diff` — 194 files unchanged
- `scripts/lint` — ruff and black both pass
- `lrh validate` — 0 errors, 166 warnings (pre-existing baseline, unrelated)
- Independently recomputed both findings' underlying numbers directly
  from the committed `validation_results.jsonl` via a Python script
  grouping by each story's primary metadata-rule genre and comparing
  against `model_detect.detected_genre` — did not simply accept the
  reviewer's stated counts

# Follow-up

- Suggest running `/lrh-confirm-fixes` (inlined as `/lrh-land` Step 5)
  against the current HEAD to verify these fixes and resolve the review
  threads before merge.
- `session_transcript` above uses the host session ID with its `local_`
  prefix stripped; update if a more durable pointer becomes available.
