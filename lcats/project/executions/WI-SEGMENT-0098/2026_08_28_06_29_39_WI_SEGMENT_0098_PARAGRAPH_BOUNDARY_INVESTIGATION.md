---
execution_id: 2026_08_28_06_29_39_WI_SEGMENT_0098_PARAGRAPH_BOUNDARY_INVESTIGATION
prompt_id: PROMPT(WI-SEGMENT-0098:WI_SEGMENT_0098_PARAGRAPH_BOUNDARY_INVESTIGATION)[2026-08-28T06:21:34+00:00]
work_item: WI-SEGMENT-0098
status: landed
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/403
commit: eaaee2db
agent: claude_app
instruction_source: lcats/project/work_items/proposed/WI-SEGMENT-0098.md
session_transcript: claude-app:e8e46d5d-35d3-4ccc-9cba-137bd31bf3a5
created_at: 2026-08-28T06:29:39+00:00
---

# Summary

Executed `WI-SEGMENT-0098`: root-caused all 6 real cases from
`WI-EVENT-0096`'s measurement where the model's claimed segmentation
anchor is recoverable but lands outside its claimed paragraph-range
search window.

# Result

For each of the 6 cases, called `_locate_anchor_span` (the real
production function, unmodified) against the whole canonicalized
document to find the true anchor location, then checked it against
`para_spans` to determine the real paragraph number.

**Finding: all 6 cases show the same direction of error** - the real
text always falls in a paragraph after the claimed `end_par_id`, never
before. 5/6 off by exactly 1 paragraph; 1/6 (`the_medici_boots__swet`)
off by 2, with a distinct identifiable cause (an empty/zero-length
paragraph in the source between the claimed and real paragraph).

Directly inspected the `[P####]`-marked boundary text for 3 of the 6
cases (`easy_money__sinclair`, `the_guardians__cox`,
`the_medici_boots__swet`) - confirmed `text_segmenter`'s own paragraph
numbering is correct and internally consistent in every case (using the
exact function that built the model's own input). The pattern is a
model-side attribution error at natural narrative-continuity boundaries,
not a code-side indexing disagreement.

Wrote `lcats/project/design/segmentation-paragraph-boundary-truncation-investigation.md`
with the full per-case table, 3 detailed boundary inspections, the
model-side/code-side categorization with supporting evidence, and a
recommendation: a narrowly-scoped end-boundary-only search-window
widening is the most promising direction, but sizing needs a broader
real sample than these 6 cases - not implemented here, per this item's
own `forbidden_actions`. Opened PR #403 (branch
`xenotaur/spike/wi-segment-0098-paragraph-boundary-investigation`,
commit `ed1b122e`).

**Review-round correction (PR #403, three findings confirmed real
before fixing):** a markdown formatting issue (a parenthetical split
across two lines, the second starting with `-`, rendering as a list
item); the per-case table's "overshoot" column reported match-*start*-
minus-window-end for 5 of 6 rows instead of match-*end*-minus-window-end,
understating the real character margin (corrected values are tens to
hundreds of characters, not single digits - materially different for
sizing any future widening fix); and the `the_guardians__cox` boundary
excerpt was truncated by this investigation's own 250-character debug
print, which I then wrongly described as the real text ending
mid-sentence - the full paragraph 142 is in fact complete and
self-contained. All three fixed by re-verifying directly against the
real data, not by trusting the review comments alone.

# Validation

- `lrh validate` - 0 errors, 247 warnings (pre-existing baseline)
- All 3 review findings independently re-verified against real data
  before fixing (re-ran `_locate_anchor_span`'s actual computation for
  the overshoot correction; re-read the full, untruncated paragraph 142
  directly from the source for the second correction)

# Follow-up

- If a follow-on implementation WI is filed for the recommended
  end-boundary widening, it should be a `deliverable` depending on this
  investigation, sized against a predeclared broader real sample, and
  validated against both these 6 failing cases and a control set of
  currently-passing alignments.
- The empty-paragraph secondary finding (whether
  `build_paragraph_index` should skip assigning markers to zero-length
  paragraphs) is a separate, smaller question worth evaluating
  independently of the main end-boundary-widening question.
- `WI-SEGMENT-0099` remains separately scoped and unexecuted.
