---
resolution: "Implemented and merged via PR #324 (commit ad7717e2, merged 1db7a49e). _locate_anchor_span now strips a leaked \\[P\\d{4,}\\]\\s* paragraph-index marker (add_paragraph_markers' f\"[P{idx+1:04d}]\" format, widened from 4 to 4-or-more digits after a review finding that :04d is a minimum width, not exact) and normalizes Unicode curly quotes/dashes to ASCII via a length-preserving str.translate, before the whitespace-tolerant regex fallback. Regression tests replay all 16 real anchors from WI-SEGMENT-0069's committed fixture end-to-end via align_segment. A live 5-story smoke-test re-run confirmed 0 marker-leakage/typography-mismatch alignment_error outcomes (2 of 5 stories, the marker-leakage cases, now align successfully; the other 3 hit different, explicitly out-of-scope failure modes). backlog.md updated per WI-SEGMENT-0068's convention. Paragraph mis-numbering and the near-miss-quoting bucket remain explicitly out of scope, per this WI's own Non-Goals."
blocked_reason: null
blocked: false
id: WI-SEGMENT-0070
title: "Fix segmentation alignment anchor-matching gaps: paragraph-marker leakage and quote/dash typography"
type: deliverable
status: resolved
priority: high
owner: unassigned
contributors: []
assigned_agents: []
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap: []
related_workstreams: []
related_design:
  - lcats/project/design/segmentation-alignment-failure-categories.md
  - lcats/project/work_items/resolved/WI-SEGMENT-0068.md
  - lcats/project/work_items/resolved/WI-SEGMENT-0069.md
depends_on:
  - WI-SEGMENT-0069
blocked_by: []
expected_actions:
  - edit_file
  - create_file
  - run_tests
  - create_pr
forbidden_actions:
  - force_push
  - delete_branch
  - widen_search_range_without_distribution_data
  - reintroduce_full_document_fallback
  - fix_near_miss_quoting_bucket
  - fix_paragraph_misnumbering
acceptance:
  - "text_segmenter._locate_anchor_span strips a leading or embedded \\[P\\d{4}\\]\\s* paragraph-index marker from the anchor before the whitespace-tolerant regex fallback runs (four digits, matching add_paragraph_markers' actual f\"[P{idx+1:04d}]\" format exactly -- not \\d+, which would also strip real story content like a citation \"[P045]\")"
  - "_locate_anchor_span normalizes Unicode curly quotes (“”‘’) and em/en dashes to their ASCII equivalents when attempting the whitespace-tolerant match, on both the anchor and the searched text"
  - "Regression tests replay the exact real cases captured in experiments/03_cross_segment_relation_pilot/fixtures/wi_segment_0069_alignment_cases.json (new_apples_in_the_garden__neville, perchance_to_dream__stockham, weak_on_square_roots__burton for marker leakage; the_hollow_lens__leverage, the_voice_in_the_fog__leverage for quote/dash mismatch), against the real committed corpus text"
  - "A live smoke-test re-run (real API, same method as WI-SEGMENT-0069) confirms these two specific failure categories no longer reproduce for the cited example stories"
  - "lcats/project/design/backlog.md is updated to mark this fix resolved, mirroring WI-SEGMENT-0068's own convention"
  - "lrh validate reports 0 errors"
required_evidence:
  - manual_review
  - lrh_validate
  - test_output
artifacts_expected:
  - lcats/src/lcats/analysis/text_segmenter.py
  - lcats/tests/analysis_tests/text_segmenter_test.py
  - lcats/project/design/backlog.md
  - experiments/03_cross_segment_relation_pilot/fixtures/wi_segment_0069_alignment_cases.json
---

## Summary

`WI-SEGMENT-0069`'s investigation classified the segmentation alignment
failures remaining after `WI-SEGMENT-0068`'s whitespace-mismatch fix. Its
dominant category, `anchor_absent_from_document` (15 of 21 failures in a
30-story live smoke test), turned out not to be one thing: manual
inspection found two concrete, narrowly-fixable sub-patterns within it,
together accounting for 5 of 21 (~24%) of *all* alignment failures
observed in that sample:

1. **Paragraph-index marker leakage.** `paragraph_text_indexer` prefixes
   each paragraph shown to the model with a `[PNNNN]` marker (e.g.
   `[P0047]`), but `align_segment` searches `canonical_text`, which never
   contains these markers. In at least 3 stories
   (`new_apples_in_the_garden__neville`, `perchance_to_dream__stockham`,
   `weak_on_square_roots__burton`), the model's own anchor text included
   the literal marker -- and, per `parsed_output`'s full segment list in
   each story, this was not a one-off: it recurred on 3-6 segments within
   each of those stories once they ran long enough for the pattern to
   take hold.
2. **Typographic quote/dash mismatch.** The source corpus uses Unicode
   curly quotes (`“”‘’`) and em/en dashes; the model's anchor text uses
   plain ASCII equivalents. Confirmed in 2 stories
   (`the_hollow_lens__leverage`, `the_voice_in_the_fog__leverage`) where
   the anchor resolves to an exact match once typography is normalized.

This item (currently `status: proposed`, no code written yet) will
implement both fixes in `text_segmenter._locate_anchor_span`, scoped the
same narrow way `WI-SEGMENT-0068` was: a targeted transform applied
before matching, not a widened search range or a fallback that guesses.

## Problem / Context

**Prior art check:**
- *Duplication search:* No existing work item addresses either
  sub-pattern -- confirmed via `grep -rl "paragraph.index.marker\|curly.quote\|typography" project/work_items/ project/design/` (only `WI-SEGMENT-0069`'s own design doc, the source of this finding, matches).
- *Demand search:* `lcats/project/design/segmentation-alignment-failure-categories.md`'s own "Recommendations" section explicitly names both fixes as "well-scoped enough to be its own narrow follow-up deliverable WI, structured the same way as `WI-SEGMENT-0068`" -- this item is that direct request, not a new independent decision.

Full evidence (real story IDs, exact anchor text, real character positions)
is in `lcats/project/design/segmentation-alignment-failure-categories.md`'s
"`anchor_absent_from_document`, subdivided" section; this item does not
repeat it in full, only cites it. The design doc's own prose quotes only
truncated anchor excerpts, though -- the *complete* real anchors needed to
write exact-replay regression tests are committed separately, in
`experiments/03_cross_segment_relation_pilot/fixtures/wi_segment_0069_alignment_cases.json`
(added by this WI's own creation PR, #321, in response to a review
finding that the design doc alone wasn't enough to reproduce the exact
cases without inventing anchors or paying for a fresh live LLM call).

## Scope

- Modify `_locate_anchor_span` in `lcats/src/lcats/analysis/text_segmenter.py`
  to strip a paragraph-index marker from the anchor, and to normalize
  quote/dash typography, before attempting the whitespace-tolerant match.
- Add regression tests replaying the real cited cases against the real
  committed corpus text (matching `WI-SEGMENT-0068`'s own
  `TestWiSegment0068RealCaseReplay` pattern).
- Re-run a live smoke test to confirm the two fixed categories no longer
  reproduce.
- Update `lcats/project/design/backlog.md`.

## Non-Goals

- Does not fix paragraph mis-numbering (`paragraph_misnumbering_large_margin`/
  `paragraph_misnumbering_narrow_margin`, 6/21 of the original sample) --
  `WI-SEGMENT-0069`'s own investigation found no correlation with paragraph
  count in its small sample and explicitly deferred this category pending
  more evidence. This item does not gather that evidence or attempt a fix.
- Does not fix the residual near-miss-quoting bucket (10/21) --
  `WI-SEGMENT-0069` reported this as a likely inherent LLM-reliability
  floor with no safe targeted fix identified; a character-edit-distance-
  tolerant fuzzy match was explicitly named as needing its own dedicated
  design and evaluation, not a quick addition here.
- Does not widen `find_anchor_in_range`/`_locate_anchor_span`'s search
  range, or reintroduce any form of full-document fallback search --
  `WI-SEGMENT-0059`'s prior documented mistake (a naive full-document
  fallback silently produced spurious overlapping segments) is exactly
  what these two fixes must avoid repeating; both are narrow,
  before-match transforms, not search-range changes.

## Required Changes

1. In `_locate_anchor_span`, before the whitespace-tolerant regex
   fallback, strip a leading or embedded `\[P\d{4}\]\s*` marker from the
   anchor -- four digits, exactly matching `add_paragraph_markers`'
   actual `f"[P{idx+1:04d}]"` format (`text_segmenter.py:77`), not a
   looser `\d+` that would also strip real story content that merely
   resembles a marker (e.g. a citation like `[P045]`, 3 digits). The
   `perchance_to_dream__stockham` example in the committed fixture (see
   Required Change 3) shows a marker can appear mid-anchor at a paragraph
   boundary within the segment, not only at the very start -- the strip
   must handle any occurrence, not just a leading one.
2. In `_locate_anchor_span`, normalize Unicode curly quotes (`“”‘’`)
   and em/en dashes to their ASCII equivalents on both the anchor and the
   text being searched (or match against normalized copies of both),
   matching the existing whitespace-tolerant fallback's structure rather
   than replacing it.
3. Add regression tests in `lcats/tests/analysis_tests/text_segmenter_test.py`
   replaying the exact real cases captured in
   `experiments/03_cross_segment_relation_pilot/fixtures/wi_segment_0069_alignment_cases.json`
   (committed by this WI's own creation PR, #321 -- real LLM-produced
   `start_par_id`/`end_par_id`/`start_exact`/`end_exact` per failing
   segment, captured during `WI-SEGMENT-0069`'s smoke test; the design
   doc's own prose only quotes truncated excerpts, not enough to replay
   the exact cases without inventing anchors or paying for a fresh live
   call -- review finding, PR #321), against the real committed corpus
   story files (`corpora/mass_quantities/new_apples_in_the_garden__neville/story.json`,
   `.../perchance_to_dream__stockham/story.json`,
   `.../weak_on_square_roots__burton/story.json`,
   `.../the_hollow_lens__leverage/story.json`,
   `.../the_voice_in_the_fog__leverage/story.json`) and asserting each
   previously-failing anchor now resolves.
4. Re-run `experiments/03_cross_segment_relation_pilot/check_segmentation_reliability.py`
   (real API cost -- get explicit sample-size authorization before
   running, same as prior smoke tests) and confirm via
   `classify_alignment_failures.py` (or direct inspection of any
   remaining `alignment_error` for the cited stories) that these two
   specific categories no longer reproduce.
5. Update `lcats/project/design/backlog.md` to record this fix as
   resolved, following `WI-SEGMENT-0068`'s own convention of documenting
   both the root cause and the final fix there.

## Acceptance Criteria

(see `acceptance` frontmatter above)

## Validation

- `lrh validate`
- `python -m pytest lcats/tests/analysis_tests/text_segmenter_test.py`
- `./scripts/test` (full suite, confirm no regression)
- A live smoke-test re-run against `claude-haiku-4-5-20251001`, as
  described in Required Change 4

## Risk Notes

- This is real-money API spend for the Required Change 4 smoke-test
  re-run -- get explicit authorization for the sample size before
  running, matching this session's established pattern.
- The marker-stripping regex must not be so permissive that it strips
  real story content that merely resembles a marker (e.g. a story whose
  actual text contains bracketed content like `[P045]`, 3 digits, as
  dialogue or a citation) -- scope the strip to exactly `\[P\d{4}\]`,
  matching `add_paragraph_markers`' real 4-digit zero-padded format
  (`text_segmenter.py:77`), not a looser `\d+` (review finding, PR #321:
  an earlier draft of this WI's own acceptance criterion contradicted
  this exact caution by specifying `\d+`).
- Do not let a passing regression test on the 5 cited stories substitute
  for the live smoke-test re-run in Required Change 4 -- the regression
  tests prove the code change is correct against known cases; the smoke
  test is the only way to confirm it doesn't have an unexpected
  interaction with real, uncited data.

## Related Workstream and Designs

- Work item: `project/work_items/resolved/WI-SEGMENT-0069.md` (source of
  this fix's evidence and its own explicit recommendation)
- Work item: `project/work_items/resolved/WI-SEGMENT-0068.md` (prior art
  for a narrowly-scoped `_locate_anchor_span` fix, same function)
- Design doc: `project/design/segmentation-alignment-failure-categories.md`
- Work item: `project/work_items/resolved/WI-SEGMENT-0059.md` (prior art
  on why a naive full-document fallback is unsafe)
