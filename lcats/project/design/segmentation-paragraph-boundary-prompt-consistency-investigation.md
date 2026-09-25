# Paragraph-Boundary Prompt-Consistency Ablation

Date: 2026-08-31

Related work:

- `WI-SEGMENT-0098` root-caused 6/10 real `WI-EVENT-0096` alignment
  failures as a one-directional `end_par_id` undercount and recommended
  a code-side search-window widening, explicitly ruling out a prompt fix
  without checking the actual prompt text.
- `WI-SEGMENT-0101` (this item) re-examined that conclusion against the
  real prompt (`lcats/src/lcats/analysis/scene_analysis.py`), found
  `end_par_id`/`start_par_id` and `end_exact`/`start_exact` are two
  independently-generated, redundant fields with no consistency
  requirement, and tests whether an explicit derivation rule closes the
  gap.

## Summary

A reworded prompt variant - deriving `start_par_id`/`end_par_id` from the
located position of `start_exact`/`end_exact` rather than an independent
judgment, with an explicit rule for anchors that straddle a paragraph
break - was run against the real 17-story `WI-EVENT-0033`/`WI-EVENT-0096`
baseline cohort (`claude-haiku-4-5-20251001`, one real API call per
story, $0.57 actual cost - see Cost estimate and approval below).
Comparing against the unchanged production prompt's own already-committed
real output from the same cohort:

- **Segment-level boundary overshoot dropped from 12/177 to 8/162**
  (measuring every segment the model returned, both `start_exact` and
  `end_exact`, not just the one segment per story that caused an
  `alignment_error` - broader than `WI-SEGMENT-0098`'s original scan). A
  segment counts once here if *either* anchor is outside the claimed
  window. **At the individual-anchor level, 12/350 anchors were outside
  in the baseline versus 9/321 in the reworded run** - one reworded
  segment (`easy_money__sinclair` segment 4) has both anchors outside,
  so the anchor-level count (9) exceeds the segment-level count (8) for
  that run; both metrics point the same direction.
- **The specific story that motivated the fix improved to zero
  overshoot.** `the_voice_in_the_fog__leverage` - whose `end_exact`
  anchor was found (during this item's own review round) to straddle
  paragraphs 34 and 35, exposing the ambiguity in "the paragraph
  containing the anchor" - had 3 overshoot instances under the baseline
  prompt and 0 under the reworded prompt.
- **Directionally positive but not conclusive**: fewer stories affected
  overall (9 -> 6) and one more story fully `included` (7 -> 8), but 2
  stories show overshoot under the reworded prompt that did not show it
  under the baseline, and one case shows a new, different error shape
  (bidirectional narrowing, not the original one-directional pattern).
  See Results and Limitations below before drawing a conclusion.

**Recommendation: the reworded instruction is a promising complement to,
not a replacement for, `WI-SEGMENT-0098`'s recommended code-side
window-widening** - see Recommendation.

## Method

### Reworded prompt variant

`experiments/03_cross_segment_relation_pilot/reworded_boundary_prompt.py`
defines an isolated variant of `SCENE_SEQUEL_SYSTEM_PROMPT` that changes
only the four location-selector bullet points
(`lcats/src/lcats/analysis/scene_analysis.py:99-105`). The original text:

```
- start_par_id: integer paragraph id where the segment begins (inclusive).
- end_par_id: integer paragraph id where the segment ends (inclusive).
- start_exact: the FIRST ≤120 characters of the segment, COPIED VERBATIM from the STORY text.
- end_exact: the LAST ≤120 characters of the segment, COPIED VERBATIM from the STORY text.
```

was replaced with:

```
- start_exact: the FIRST ≤120 characters of the segment, COPIED VERBATIM from the STORY text.
- end_exact: the LAST ≤120 characters of the segment, COPIED VERBATIM from the STORY text.
- start_par_id: the [PNNNN] paragraph marker number of the paragraph that contains
  the FIRST character of start_exact. Do NOT judge this independently of
  start_exact: first locate start_exact's exact position in the STORY text, then
  read off the paragraph marker that covers that position.
- end_par_id: the [PNNNN] paragraph marker number of the paragraph that contains
  the LAST character of end_exact. If end_exact's text spans more than one
  paragraph, use the paragraph containing its LAST character, not its first.
  Do NOT judge this independently of end_exact: first locate end_exact's exact
  position in the STORY text, then read off the paragraph marker that covers
  its final character.
```

with an added closing rule: `start_par_id`/`end_par_id` must be derived
from where the anchor text is physically located, not from which
narrative scene/beat the model judges it to belong to. This directly
targets the root cause identified during `WI-SEGMENT-0101`'s own review:
the ambiguity `WI-SEGMENT-0098` found ("two paragraphs continuing one
narrative beat") is real, but only needs to affect *which text* the model
picks as `end_exact` - it does not require `end_par_id` to be a second,
independently-guessed opinion about the same boundary.

A unit test
(`experiments/03_cross_segment_relation_pilot/reworded_boundary_prompt_test.py`,
4/4 passing) confirms the reworded prompt is byte-identical to production
outside the targeted block, so the ablation isolates exactly one
variable.

### Cost estimate and approval (WI-SEGMENT-0101 acceptance criterion 2)

Before any spend, the following estimate was presented and explicitly
approved:

- Cohort: the same 17-story `WI-EVENT-0033`/`WI-EVENT-0096` baseline
  cohort (already committed); model: `claude-haiku-4-5-20251001` (same as
  the original run, for a like-for-like comparison).
- Calls needed: 17 (one per story, reworded prompt only) - the "before"
  side reuses `WI-EVENT-0096`'s already-committed real output for the
  unchanged production prompt, no re-spend needed.
- Expected token delta: the reworded block adds 910 characters (~200-250
  tokens) to the system prompt per call; everything else (user prompt,
  output schema/shape) is unchanged. Based on `WI-EVENT-0096`'s actual
  measured usage (225,626 input / 73,483 output tokens across 17 calls,
  pulled fresh from the committed files), this implies roughly +3,900
  input tokens (~1.7%) total, output essentially unchanged.
- Estimated cost: ~$0.59-0.60 (`WI-EVENT-0096`'s actual cost was $0.593
  at Haiku 4.5 pricing of $1.00/1M input, $5.00/1M output).
- **Approved** in-session before the ablation ran.
- **Real reworded-run cost (review finding, PR #420): $0.57, not $0.59.**
  The design doc's first draft reused `WI-EVENT-0096`'s baseline cost
  ($0.593) for the reworded run instead of computing the reworded run's
  own usage. Recomputed directly from the committed reworded result
  files: 229,485 input tokens, 67,179 output tokens, $0.5654 -> $0.57 -
  close to the estimate, but the $0.593 figure belongs to the baseline
  run and should not have been reused here.

### Ablation run

`experiments/03_cross_segment_relation_pilot/run_boundary_prompt_ablation.py`
ran the reworded extractor against the same 17-story cohort
(`results/segmentation_reliability/baseline_story_list.txt`), same model
(`claude-haiku-4-5-20251001`), one real call per story: 17 calls, actual
cost $0.57 (229,485 input / 67,179 output tokens - see Cost estimate and
approval above), comparable token volume to `WI-EVENT-0096`'s original
run. Results persisted at
`results/segmentation_reliability_reworded_prompt/`.

The **"before" side reused `WI-EVENT-0096`'s already-committed real
output** (`results/segmentation_reliability/`) for the unchanged
production prompt - no fresh spend needed for that half of the
comparison, per this project's established practice of reusing
already-committed real data.

### Overshoot measurement

`experiments/03_cross_segment_relation_pilot/measure_paragraph_boundary_overshoot.py`
replays `WI-SEGMENT-0098`'s own diagnostic method, generalized to check
**every segment** in every story (not only the one segment that caused
that story's `alignment_error`) and **both** anchors (`start_exact` and
`end_exact`, not only `end_exact`):

1. For each segment, compute the claimed window
   `[para_spans[start_par_id-1][0], para_spans[end_par_id-1][1]]`
   (inclusive `end_par_id`, matching `text_segmenter.align_segment`'s own
   convention exactly).
2. Locate `start_exact` bounded to `[lo, hi)`, then locate `end_exact`
   bounded to `[s_idx, hi)` - starting from wherever `start_exact`
   resolved, not from `lo` again - the exact same two-step bounded search
   `align_segment` itself performs, in the same order.
3. Only if a bounded search genuinely fails, search the full document to
   characterize how far outside the window the true anchor lies.

This bounded-first order was corrected twice during this item's own
execution, both times caught by independent self-review, not assumed
correct on the first attempt:

- An earlier draft searched the full document unconditionally and found
  a false "overshoot" on an already-correctly-`included` story
  (`the_invaders__ferris` segment 8) - its `end_exact` anchor also
  happens, coincidentally, to match a much earlier, unrelated occurrence
  of similar text elsewhere in the same story, thousands of characters
  before the segment's real (correct) location. A real match inside the
  window is definitionally not an overshoot regardless of what else the
  anchor text happens to match elsewhere - bounding the search first
  fixes this.
- A second draft bounded both anchors to `[lo, hi)`, but
  `align_segment`'s real code bounds `end_exact` to `[s_idx, hi)` (the
  resolved *start* position), not `[lo, hi)` again - confirmed directly
  against `text_segmenter.py`'s source. This had no effect on this run's
  actual numbers (re-verified: identical 12/177 and 8/162 results before
  and after the fix), but the measurement now matches production's real
  algorithm exactly rather than only approximately.
- A third draft (review finding, PR #420) conflated "found via the
  bounded search" with "inside the claimed window": because `end_exact`'s
  search range can be widened below the true window's start (when
  `start_exact` itself only resolved via the unbounded fallback), a match
  found in that widened gap was wrongly marked inside. Two real cases hit
  this (`the_haunter_of_the_dark` segment 10, baseline;
  `the_guardians__cox` segment 6, reworded) - in both, the end anchor's
  match happened to still fall inside the true window on direct
  recheck, so this had no effect on the reported counts either, but the
  fix makes "inside the claimed window" always a check against the true
  window rather than a coincidence of the search range used. The same
  fix also matched `align_segment`'s own par_id normalization exactly
  (rejecting bool values even though `isinstance(True, int)` is true in
  Python; clamping `end_par_id` up to `start_par_id` when reported
  lower) - neither case occurred in this dataset either.

## Results

| Metric | Baseline (production prompt) | Reworded prompt |
|---|---:|---:|
| Stories `included` (fully aligned) | 7/17 | 8/17 |
| Total segments seen | 177 | 162 |
| Segments checked (had valid par_ids) | 177 | 162 |
| Segments with >=1 anchor outside its claimed window | 12 | 8 |
| Individual anchors outside their claimed window | 12/350 | 9/321 |
| Stories with at least one overshoot segment | 9 | 6 |

The segment-level and anchor-level counts differ because one reworded
segment (`easy_money__sinclair` segment 4) has *both* anchors outside -
it counts once at the segment level but twice at the anchor level. Both
metrics point the same direction; neither is more "correct" than the
other, they answer slightly different questions ("how many segments have
a problem" vs. "how many individual anchor placements have a problem").

Stories with overshoot, baseline: `the_haunter_of_the_dark`,
`calling_the_empress__smith`, `easy_money__sinclair`,
`problem_in_solid__smith`, `the_guardians__cox`, `the_medici_boots__swet`,
`the_voice_in_the_fog__leverage`,
`wintry_peacock_from_the_new_decameron_volume_iii__lawrence`,
`romance_of_an_ugly_policeman`.

Stories with overshoot, reworded: `the_haunter_of_the_dark`,
`easy_money__sinclair`, `the_guardians__cox`, `the_last_days_of_l_a__smith`,
`the_medici_boots__swet`, `girl` (ohenry-whirligigs).

**The story that directly motivated this item's design improved to
zero.** `the_voice_in_the_fog__leverage`'s `end_exact` anchor - the case
whose match span `(7225, 7391)` was found to straddle paragraphs 34 and
35 during `WI-SEGMENT-0101`'s own review round - shows 0 overshoot
segments under the reworded prompt, down from 3 under the baseline.

**A new error shape appeared in one case.**
`easy_money__sinclair` segment 4 (reworded run) shows overshoot on
*both* anchors in opposite directions - the real `start_exact` location
(14374) falls *before* the claimed window start (14500), and the real
`end_exact` location (18801) falls *after* the claimed window end
(18538). This is a bidirectional narrowing (the claimed span is
narrower than the real one on both sides), not the original
one-directional "always after, never before" pattern `WI-SEGMENT-0098`
characterized. This is a single instance, not a new confirmed pattern -
noted here rather than omitted, per this project's practice of surfacing
what a result doesn't explain rather than only what supports the
headline finding.

## Limitations

**This is not a matched, controlled before/after comparison per
segment.** The model's own choice of how many segments to produce, and
where to place their boundaries, differs between the two prompt variants
independent of the location-selector wording (temperature 0.2, not 0).
Baseline and reworded runs do not always produce the same `segment_id`
at the same location for the same story - `easy_money__sinclair` flagged
segment 3 in the baseline and segment 4 in the reworded run, for
example. The aggregate counts above are the honest comparison; a
per-segment "did this exact case improve" claim cannot be made from a
single run of each variant.

**Single-run comparison, consistent with this project's own standing
caution.** `WI-SEGMENT-0098`'s own design doc already noted "a single
pre/post-fix call pair... cannot rule out sampling variance" for a
similar comparison; the same caution applies here at a larger (17-story)
but still single-run scale.

**No classification-quality check was performed.** This item measured
only the paragraph-boundary-overshoot pattern, per its own scope. Whether
the reworded instruction affects `segment_type`/GACD/ERAC classification
quality - the concern `WI-SEGMENT-0101`'s own Risk Notes named - was not
evaluated; that would require human judgment on scene classification,
out of scope for this bounded ablation.

**2 stories show overshoot under the reworded prompt that did not show
it under the baseline** (`the_last_days_of_l_a__smith`, `girl`). Given
the matched-segment limitation above, this cannot be attributed to the
reworded wording specifically versus ordinary run-to-run variance in
which segments the model produces - named here as an open question, not
resolved by this ablation.

## Recommendation

**Adopt the reworded instruction as a complement to, not instead of,
`WI-SEGMENT-0098`'s recommended code-side end-boundary window-widening -
do not implement either from this evidence alone.** The result is
directionally positive (fewer overshoot segments, fewer affected
stories, one more story fully included, and the specific motivating case
resolved cleanly) but a single 17-story run cannot establish this
reliably clears the bar for a production prompt change on its own,
especially given the new error shape and the 2 newly-affected stories
noted above. Per this project's established pattern of separating
investigation from remediation (`WI-SEGMENT-0069` before
`WI-SEGMENT-0070`/`0071`; `WI-SEGMENT-0098` before any implementation),
a follow-on `deliverable` WI - if filed - should combine both mitigations
(reworded prompt + a defense-in-depth window-widening safety net) rather
than choosing one, sized against a larger real sample, and validated
against a control set of currently-passing alignments before any
production prompt change ships.
