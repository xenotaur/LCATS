---
execution_id: 2026_08_26_15_28_32_SEGMENTATION_ALIGNMENT_FOLLOWUP_SCOPING
prompt_id: PROMPT(AD_HOC:SEGMENTATION_ALIGNMENT_FOLLOWUP_SCOPING)[2026-08-26T15:24:47+00:00]
work_item: AD_HOC
status: landed
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/399
commit: 3583a8a6
agent: claude_app
instruction_source: "user request in-session (\"Let's file three work items: case-insensitivity, paragraph-range-boundary, and edit-distance tolerance...\")"
session_transcript: claude-app:e8e46d5d-35d3-4ccc-9cba-137bd31bf3a5
created_at: 2026-08-26T15:28:32+00:00
---

# Summary

Filed three follow-up work items from direct forensic analysis of
`WI-EVENT-0096`'s 10 real post-fix segmentation `alignment_error`
failures - not from the user's original hypothesis alone, but from
actually reading each real anchor against the real source text and
categorizing the true root cause per case, which turned out more varied
than "mostly case/whitespace/punctuation."

# Result

Analyzed all 10 real failures from
`experiments/03_cross_segment_relation_pilot/results/segmentation_reliability/`
directly (loading each story's real text, computing `para_spans`, and
diffing the claimed anchor against the real source at the byte level).
Found 3 distinct categories, not one:

- 2/10 pure case-only near-misses (`what`/`What`, `the`/`The`) -> filed as
  `WI-SEGMENT-0097` (deliverable): extend `_locate_anchor_span`'s existing
  deterministic typography-normalization fallback with `re.IGNORECASE`.
- 6/10 anchors recoverable (exactly, or via the existing typography
  fallback) at a location outside the claimed paragraph range -> filed as
  `WI-SEGMENT-0098` (investigation): root-cause whether this is a
  model-side paragraph miscount or a code-side indexing disagreement,
  before any fix.
- 2/10 genuine word-level near-misses in otherwise-correct anchors
  ("Martina Evers" vs real "Martha Evers" - a content substitution;
  "gratefuly" vs real "gratefully" - a spelling typo) -> filed as
  `WI-SEGMENT-0099` (evaluation): extend `WI-SEGMENT-0072`'s deferred
  fuzzy-matching evaluation corpus with these 2 real positives and report
  against its own frozen adoption thresholds, without lowering them.

**Review-round correction (PR #399, two P1 findings confirmed real
before fixing):** an earlier draft (a) wrongly described
`easy_money__sinclair`'s boundary case as a pure byte-exact match, when
it actually also needs the existing typography normalization (ASCII
`o'clock` vs source curly `o’clock`); and (b) left
`the_voice_in_the_fog__leverage` end_exact as a vague "not fully
diagnosed" 10th case instead of actually root-causing it - direct
verification (`_locate_anchor_span(canon, anchor, 0, len(canon))`) shows
it recovers via the existing typography fallback at span `(7225, 7391)`,
which starts inside the claimed window `[3598, 7311)` but extends past
its end - the same boundary-truncation mechanism as the other 5 cases,
not a separate unresolved issue. `WI-SEGMENT-0098` was corrected to cover
6 cases (not 5), with both combined-typography-and-boundary cases
explicitly flagged as such.

This finding was presented to the user before filing (the real
20%/50%/20%/10% split, not the ~100% the initial hypothesis implied,
later corrected to 20%/60%/20% after the review round) and the three-way
split was explicitly requested in response. Opened PR #399 (branch
`xenotaur/chore/segmentation-alignment-followup-scoping`, commit
`677b89e8`).

# Validation

- `lrh validate` - 0 errors, 245 warnings (pre-existing baseline)

# Follow-up

- All three new WIs are `status: proposed`, unowned, and not yet executed.
- Offering to add these three WIs to `WS-PILOT-IMPROVEMENTS.md`'s
  `work_items:` list is a candidate follow-up, not yet actioned pending
  user confirmation.
