---
resolution: "Investigated via PR #403. All 6 real cases root-caused: all show the true anchor text falling in a paragraph after the claimed end_par_id, never before (5/6 off by 1 paragraph, 1/6 by 2 with a distinct empty-paragraph cause). text_segmenter's own paragraph indexing verified correct in every inspected case - root cause is model-side attribution error at narrative-continuity boundaries, not a code-side bug. Full findings and recommendation (a narrowly-scoped end-boundary-only search-window widening, sizing deferred to a broader real sample) in lcats/project/design/segmentation-paragraph-boundary-truncation-investigation.md. Investigation only - no production alignment behavior changed."
blocked_reason: null
blocked: false
id: WI-SEGMENT-0098
title: Investigate paragraph-range boundary truncation in segmentation anchor alignment
type: investigation
status: resolved
priority: medium
owner: unassigned
contributors: []
assigned_agents: []
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap: []
related_workstreams:
  - WS-PILOT-IMPROVEMENTS
related_design:
  - lcats/project/design/segmentation-alignment-failure-categories.md
  - lcats/project/executions/WI-EVENT-0096/2026_08_26_05_07_53_WI_EVENT_0096_MEASUREMENT.md
depends_on: []
blocked_by: []
expected_actions:
  - create_file
  - edit_file
  - run_tests
  - create_pr
forbidden_actions:
  - implement_production_fix
  - widen_paragraph_search_window_without_evidence
  - force_push
  - delete_branch
acceptance:
  - "All 6 real cases from WI-EVENT-0096's 2026-08-26 run where the model's claimed anchor is recoverable (exactly, or via the existing typography/whitespace-tolerant fallback) at a location that falls outside the claimed [start_par_id, end_par_id] search window are individually root-caused: easy_money__sinclair segment 3 end_exact (typography-normalized match starts 2 characters past the computed window end), the_voice_in_the_fog__leverage segment 3 end_exact (typography-normalized match starts inside the window at 7225 but extends to 7391, past the window's end at 7311), the_guardians__cox segment 9 end_exact, the_medici_boots__swet segment 10 end_exact, wintry_peacock_from_the_new_decameron_volume_iii__lawrence segment 9 end_exact, and romance_of_an_ugly_policeman segment 3 end_exact"
  - "For each case, the report states whether the true text falls under a paragraph number genuinely different from what the model claimed (a model/prompt-side misjudgment) or whether lcats.analysis.text_segmenter's own paragraph-splitting (build_paragraph_index/canonicalize_text) disagrees with what the model would perceive from the [P0001]-marked input it actually received (a code-side indexing bug)"
  - "A written report (lcats/project/design/segmentation-paragraph-boundary-truncation-investigation.md) gives a recommendation - fix the indexer, adjust the prompt, bounded search-window widening with an explicit, justified margin, or defer - grounded in the per-case evidence, not speculation"
  - "No production alignment behavior is changed by this item"
  - "lrh validate reports 0 errors"
required_evidence:
  - manual_review
  - lrh_validate
artifacts_expected:
  - lcats/project/design/segmentation-paragraph-boundary-truncation-investigation.md
---

# Work Item: WI-SEGMENT-0098

## Summary

Investigate why 6 of the 10 real post-fix segmentation alignment failures
found in `WI-EVENT-0096`'s 2026-08-26 measurement are not fundamentally
text-content mismatches: the model's claimed anchor text is recoverable
(exactly, or via the existing typography/whitespace-tolerant fallback
already in production) at a location that falls outside the character
range implied by its own claimed `start_par_id`/`end_par_id`. This is
currently the single largest category among real alignment failures
(60%) and is a distinct failure mechanism from both case-sensitivity
(`WI-SEGMENT-0097`) and genuine near-miss quoting/typos
(`WI-SEGMENT-0099`) - though two of the six cases also happen to need
typography normalization, this item's scope is the boundary problem, not
the normalization (already handled in production for those two).

## Problem / Context

`WI-EVENT-0096` ran the real, exact 17-story baseline cohort through
`check_segmentation_reliability.py`. Direct forensic analysis of each of
the 10 real `alignment_error` failures (reading the real story text and
model output side-by-side, and calling `text_segmenter._locate_anchor_span`
directly against the real data - not just eyeballing diffs) found 6 cases
where the claimed anchor is recoverable at a location that falls outside
`align_segment`'s computed `[lo, hi)` search bound (derived from
`para_spans[start_par_id-1][0]` to `para_spans[end_par_id-1][1]`):

- `mass_quantities/easy_money__sinclair` segment 3 `end_exact`: **not** a
  pure byte-exact match (an earlier draft of this item wrongly claimed
  it was, corrected in review) - the anchor uses an ASCII apostrophe
  (`o'clock`) where the source has a curly one (`o’clock`), already
  handled by the existing typography-normalization fallback. Once that
  normalization is applied, the match starts at character index 30808 in
  the canonicalized source; the claimed paragraph range's computed end is
  30806 - the true match falls only **2 characters** past the window
  boundary, combining a boundary miss with an already-solved typography
  difference.
- `mass_quantities/the_voice_in_the_fog__leverage` segment 3 `end_exact`:
  also a combined case, not previously classified in this item's first
  draft (added per review finding). `_locate_anchor_span(canon, anchor,
  0, len(canon))` (searched over the whole document) recovers it via the
  typography-normalized fallback at span `(7225, 7391)`. The claimed
  window is `[3598, 7311)` - the match **starts inside** the window
  (7225 < 7311) but its real end (7391) extends past the window's end,
  so the truncated `text[lo:hi]` search never contains the full anchor.
- `mass_quantities/the_guardians__cox` segment 9 `end_exact`,
  `mass_quantities/the_medici_boots__swet` segment 10 `end_exact`,
  `mass_quantities/wintry_peacock_from_the_new_decameron_volume_iii__lawrence`
  segment 9 `end_exact`, and `wodehouse/romance_of_an_ugly_policeman`
  segment 3 `end_exact`: each anchor matches exactly (no normalization
  needed) at a character index confirmed to fall outside the claimed
  paragraph range, by amounts not yet individually measured (this item's
  own Required Changes cover measuring each precisely).

Whether the root cause is the model itself misjudging which
`[P0001]`-numbered paragraph its own claimed anchor falls in (a
prompting/model-behavior issue) or `lcats.analysis.text_segmenter`'s own
paragraph splitting producing boundaries that do not match what the
model perceives from the marked-up input it was given (a code-level
indexing bug) has not been determined - this item's job is to find out,
not to guess or to widen the search window speculatively (the
`WI-SEGMENT-0059`-documented danger of an unjustified fallback widening
applies here just as much as to full-document fallback).

### Duplication search

- In-repo: `WI-SEGMENT-0069` classified alignment failures into
  `anchor_absent_from_document` and `paragraph_misnumbering` categories
  in an earlier, smaller sample; `WI-SEGMENT-0070` fixed marker leakage
  and quote/dash typography; `WI-SEGMENT-0071` produced a paragraph-
  misnumbering diagnostics replay fixture. None of these characterize
  the specific "anchor matches exactly, just outside the computed
  window" pattern this item investigates - `WI-SEGMENT-0071`'s own scope
  was explicitly the near-miss-quoting bucket, not this boundary pattern.
- Sibling repos: None identified.
- External libraries: Not applicable - this is LCATS's own paragraph-
  indexing logic.
- Recommendation: Proceed; this is a genuinely uncharacterized failure
  mode in the existing classification.

### Demand search

- Work items: Surfaced directly by real evidence in `WI-EVENT-0096`'s
  execution record. No existing work item investigates this specific
  boundary-truncation pattern.
- Proposals: None identified.
- Backlog: No matching entry found.
- Recommendation: Proceed.

## Scope

- For each of the 6 real cases, measure precisely how far outside the
  claimed paragraph range the true anchor text falls (in characters and,
  if relevant, in paragraph count).
- Determine whether the true text's real paragraph index (per
  `text_segmenter`'s own `para_spans`) differs from what the model
  claimed, or whether the model's claimed paragraph number is internally
  consistent with the marked-up input but `text_segmenter`'s own
  splitting disagrees with it.
- Inspect the actual `[P0001]`-marked text sent to the model for each
  case around the relevant boundary, to see whether the paragraph
  numbering the model saw is itself ambiguous or miscounted (e.g. blank
  lines, quoted dialogue, or other structural cues that could confuse
  paragraph counting).
- Report findings and a recommendation; do not implement a production
  fix as part of this item.

## Required Changes

1. Write a small analysis script or notebook cell (not a permanent
   pipeline component) that, for each of the 6 real cases, loads the
   real story text, computes `para_spans` via
   `text_segmenter.paragraph_text_indexer`, locates the true anchor
   position via exact search, and reports: the true character offset,
   which paragraph index actually contains it, the model's claimed
   `start_par_id`/`end_par_id`, and the exact character gap between the
   claimed window's boundary and the true match.
2. For at least 2 of the 6 cases, manually inspect the `[P0001]`-marked
   text actually sent to the model (reconstructible via
   `paragraph_text_indexer` on the real story text) around the relevant
   paragraph boundary, to check for a plausible reason the model could
   have miscounted (e.g. a paragraph broken across dialogue, an unusual
   blank-line pattern) versus no plausible reason (suggesting a
   code-side indexing disagreement instead).
3. Write `lcats/project/design/segmentation-paragraph-boundary-truncation-investigation.md`
   with per-case findings, a categorization (model-side miscount vs.
   code-side indexing disagreement vs. inconclusive), and a
   recommendation: fix `text_segmenter`'s indexing, adjust the prompt's
   paragraph-numbering instructions, a narrowly-justified bounded window
   margin (e.g. a small fixed character/paragraph slack with its own
   safety argument against `WI-SEGMENT-0059`'s concerns), or defer
   pending more evidence.
4. If a production fix is recommended, file it as a separate WI - this
   item is investigation-only.

## Non-Goals

- Does not implement any production fix - recommendation only.
- Does not widen the search window in production code as part of this
  item, even if that turns out to be the eventual recommendation.
- Does not investigate case-sensitivity (`WI-SEGMENT-0097`) or genuine
  near-miss quoting/typos (`WI-SEGMENT-0099`) - those are separately
  scoped.
- Does not spend any real API budget - all 6 cases already exist as
  committed real data from `WI-EVENT-0096`.

## Acceptance Criteria

(see frontmatter `acceptance:` above)

## Validation

- lrh validate

## Risk Notes

- **This is the largest real-world category (60% of current failures) -
  likely the highest-value of the three follow-up items**, but its fix
  (if any) is not yet known; this item deliberately separates diagnosis
  from remediation, per this project's established pattern
  (`WI-SEGMENT-0069` before `WI-SEGMENT-0070`/`0071`).
- **A bounded window-widening fix, if recommended, must carry its own
  explicit safety argument** against `WI-SEGMENT-0059`'s documented
  danger of silently accepting a wrong-location match when the search
  scope is loosened without justification.
- **Sample size is small (6 real cases, all from one story cohort).** The
  report should say plainly if the evidence is too thin to distinguish
  model-side from code-side causes conclusively, rather than forcing a
  confident-sounding conclusion.

## Related Workstream and Designs

- Workstream: `lcats/project/workstreams/proposed/WS-PILOT-IMPROVEMENTS.md`
- Design: `lcats/project/design/segmentation-alignment-failure-categories.md`
- Evidence: `lcats/project/executions/WI-EVENT-0096/2026_08_26_05_07_53_WI_EVENT_0096_MEASUREMENT.md`
  and `experiments/03_cross_segment_relation_pilot/results/segmentation_reliability/`
  - the real run that surfaced all 6 cases
