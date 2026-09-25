---
resolution: null
blocked_reason: null
blocked: false
id: WI-SEGMENT-0106
title: Investigate combining paragraph-boundary prompt fix with window-widening
type: investigation
status: proposed
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
  - lcats/project/design/segmentation-paragraph-boundary-truncation-investigation.md
  - lcats/project/design/segmentation-paragraph-boundary-prompt-consistency-investigation.md
  - lcats/project/work_items/resolved/WI-SEGMENT-0098.md
  - lcats/project/work_items/resolved/WI-SEGMENT-0101.md
  - lcats/project/work_items/resolved/WI-SEGMENT-0059.md
depends_on:
  - WI-SEGMENT-0098
  - WI-SEGMENT-0101
blocked_by: []
expected_actions:
  - create_file
  - edit_file
  - run_tests
  - create_pr
forbidden_actions:
  - implement_production_prompt_change
  - implement_window_widening
  - spend_api_budget_without_approval
  - force_push
  - delete_branch
acceptance:
  - "Both stories that regressed under WI-SEGMENT-0101's reworded prompt (mass_quantities/the_last_days_of_l_a__smith, ohenry-whirligigs/girl) are examined against their actual committed reworded-prompt output and story text, and a verdict is stated for each: genuine new confusion introduced by the reworded instruction, ordinary run-to-run stochastic variance, OR explicitly inconclusive if a single baseline/reworded run pair cannot support a causal verdict either way (review finding, PR #422: with only one generation per prompt variant per story, examining committed anchors can explain WHAT happened but not establish WHY - inconclusive is a valid, expected answer here, not a fallback for insufficient effort)"
  - "A margin-sizing analysis reports the full distribution of overshoot sizes (in characters) separately for start-side and end-side anchor failures across both WI-SEGMENT-0098's baseline data and WI-SEGMENT-0101's reworded-prompt data (21 real instances as of this item's filing: 4 start-side - 1533, 319, 126, 48 chars - and 17 end-side, 4-5,345 chars) - not merged into one distribution (review finding, PR #422: WI-SEGMENT-0098 explicitly recommends widening only the end boundary, never the start; mixing start-side failures into an end-margin-sizing distribution both misrepresents what an end-only widening could ever recover and skews the reported spread) and not just a single min/max/typical number, since the end-side distribution alone has a long tail a fixed small margin would not cover"
  - "A simulated combined-fix pass applies a hypothetical widened end-boundary window (sized per the end-side margin distribution) to WI-SEGMENT-0101's already-committed real reworded-prompt output and reports, for every newly-recovered match (an anchor that had no match at all in the original same-window search): an explicit correctness check against the real story text/context confirming it is the actually-correct occurrence, not merely that a match was found (review finding, PR #422: comparing against what the original search found is vacuous for a newly-recovered anchor, since the original result was `None` - the widened window could expose an unrelated duplicate before the correct occurrence, exactly the ambiguity this dataset has already demonstrated on other cases, and that must be checked directly, not inferred from the absence of a prior result to differ from) - using the exact same strict exact/typography/whitespace/case-tolerant match criteria text_segmenter._locate_anchor_span already uses, never a looser fuzzy search"
  - "A plain recommendation is stated: implement a combined-fix deliverable WI now, defer pending a larger real sample, or reject the combined approach - grounded in the findings above, not asserted"
  - "No production code (scene_analysis.py, text_segmenter.py) or prompt text is changed by this item - investigation and simulation only"
  - "No new real API spend - this item's entire analysis is performed against already-committed real data from WI-SEGMENT-0098 and WI-SEGMENT-0101"
  - "lrh validate reports 0 errors"
required_evidence:
  - manual_review
  - lrh_validate
  - test_output
artifacts_expected:
  - lcats/project/design/segmentation-combined-boundary-fix-feasibility.md
---

# Work Item: WI-SEGMENT-0106

## Summary

`WI-SEGMENT-0098` recommended a code-side end-boundary search-window
widening for paragraph-boundary overshoot failures, but never
implemented it or sized the margin. `WI-SEGMENT-0101` separately tested
a prompt-side fix (deriving `end_par_id`/`start_par_id` from anchor
location instead of independent judgment) and found it directionally
positive but incomplete: anchor-level overshoot dropped from 12/350 to
9/321, with 2 stories showing new overshoot that hadn't appeared under
the unmodified prompt. Neither investigation resolved whether combining
both mitigations is worth implementing. This item answers that -
entirely by analyzing data both prior items already collected and
committed, with no new real API spend.

## Problem / Context

Three open questions block a combined-implementation decision, all
answerable from already-committed real data:

1. **Two stories regressed under the reworded prompt with no
   explanation on record.**
   `mass_quantities/the_last_days_of_l_a__smith` (segment 7: end
   overshoot 93 chars at window `[21030, 22624]`, real match
   `[22626, 22717]`; segment 11: end overshoot 209 chars at window
   `[32451, 34775]`, real match `[34777, 34984]`) and
   `ohenry-whirligigs/girl` (segment 2: end overshoot 170 chars at
   window `[943, 2373]`, real match `[2376, 2543]`) both show overshoot
   under `WI-SEGMENT-0101`'s reworded prompt that did not appear under
   the unmodified production prompt on the same cohort. `WI-SEGMENT-0101`
   explicitly left this unresolved, citing the single-run/model-
   stochasticity limitation, and did not investigate further.
2. **The window-widening margin was never sized against real data - and
   the two overshoot directions must not be conflated.**
   `WI-SEGMENT-0098`'s original 6 cases all needed only 1-2 paragraphs of
   margin, but that investigation explicitly flagged the sample as too
   thin to trust as representative, and its recommendation is explicitly
   **end-boundary-only** - it names no evidence for widening the start.
   The combined real dataset now available (`WI-SEGMENT-0098`'s baseline +
   `WI-SEGMENT-0101`'s reworded-prompt residuals) has 21 real anchor-level
   overshoot instances, but they are not all the same failure mode: 4 are
   `start_exact` failures (1533, 319, 126, 48 chars - the anchor's real
   position is *before* the claimed window's lower bound) and 17 are
   `end_exact` failures (4-5,345 chars - *after* the upper bound),
   spot-checked directly from the committed
   `paragraph_boundary_overshoot_baseline.json`/`_reworded.json`
   artifacts. An end-only widening can never recover a start-side
   failure, so the two must be sized and reported as separate
   distributions, not merged.
3. **No one has checked whether the two fixes interact safely together -
   and a "recovered" count alone is not the safety-relevant signal.**
   Applying a widened window on top of the already-reworded prompt's
   output has never been simulated, so it's unknown whether a combined
   fix would recover the residual 9/321 anchor-level failures. Recovery
   count by itself is insufficient: a newly-recovered anchor's original
   search returned no match at all, so there is nothing to compare it
   against for a false-accept check - it must instead be independently
   verified as the actually-correct occurrence, since a widened window
   could just as easily expose an unrelated duplicate before the correct
   text (an ambiguity this dataset has already demonstrated - see
   `WI-SEGMENT-0101`'s own bounded-search-vs-duplicate fix).

### Duplication search

- In-repo: `WI-SEGMENT-0098` and `WI-SEGMENT-0101` are the direct
  predecessors; neither combines the two mitigations or sizes the
  margin. `WI-SEGMENT-0059` documents the standing safety principle
  (never silently accept a wrong-but-plausible match) this item's
  simulation must respect. No existing item performs this specific
  combined-feasibility analysis.
- Sibling repos: None identified.
- External libraries: Not applicable - reuses
  `text_segmenter._locate_anchor_span` and the existing overshoot
  measurement tooling from `WI-SEGMENT-0101` unmodified.
- Recommendation: Proceed.

### Demand search

- Work items: Surfaced directly from `WI-SEGMENT-0101`'s own closeout
  follow-up note and a user-driven design discussion in this session. No
  existing work item covers this combined-feasibility question.
- Proposals: None identified.
- Backlog: No matching entry found.
- Recommendation: Proceed.

## Scope

- Root-cause the 2 regressed stories by reading their real committed
  `parsed_output` (both baseline and reworded) directly, alongside the
  real story text; state a verdict of genuine new confusion, sampling
  variance, or explicitly inconclusive - do not force a causal choice
  a single run pair per story cannot support.
- Gather every real anchor-level overshoot instance currently available
  (both `WI-SEGMENT-0098`'s baseline data and `WI-SEGMENT-0101`'s
  reworded-prompt data), split by direction (`start_exact` vs.
  `end_exact` failures), and report each direction's own distribution of
  `overshoot_chars` separately.
- Simulate a widened end-boundary window (sized from the end-side
  distribution only) against `WI-SEGMENT-0101`'s already-committed
  reworded-prompt output: for each currently-failing end anchor, does a
  widened window recover it using the same strict match criteria, and -
  for every newly-recovered match specifically - independently verify it
  against the real story text as the actually-correct occurrence, not
  merely "a match was found." For each currently-*passing* segment, does
  the widened window ever produce a different, wrong match.
- State a plain go/defer/reject recommendation, including whether
  start-side failures need their own separate follow-on investigation
  (widening the start boundary is out of scope for this item, per
  `WI-SEGMENT-0098`'s own recommendation).
- Do not implement the prompt change, the window-widening code, or spend
  any new real API budget.

## Required Changes

1. Write a small analysis script (not a permanent pipeline component)
   that loads `mass_quantities/the_last_days_of_l_a__smith` and
   `ohenry-whirligigs/girl`'s real committed reworded-prompt
   `parsed_output`, locates the relevant segments' anchors in the real
   story text, and reports a verdict for each with supporting evidence
   (not just the offsets already known - inspect the actual anchor text
   and surrounding context) - explicitly allowing "inconclusive" as the
   reported verdict when the evidence does not support a causal claim.
2. Aggregate all real `overshoot_chars` values from
   `experiments/03_cross_segment_relation_pilot/results/paragraph_boundary_overshoot_baseline.json`
   and `..._reworded.json` (or freshly regenerate them from the
   underlying committed result directories if either has drifted),
   **split into two separate distributions by direction** (`start`
   anchor failures vs. `end` anchor failures - do not merge); report
   percentiles or a full sorted list for each, not just min/max.
3. Write a simulation function that, given an end-margin size, re-checks
   every segment in `WI-SEGMENT-0101`'s reworded-prompt results with the
   end boundary widened by that margin only (still using
   `text_segmenter._locate_anchor_span`'s existing strict matching, never
   a fuzzy/looser search). For every anchor that becomes newly-recovered
   (had no match at all in the original same-window search), read the
   real story text at the widened match's location and record an
   explicit correctness verdict against the actual expected content -
   not merely whether a match was returned. For every already-passing
   segment, report whether the widened window ever produces a *different*
   match than the original same-window search found (a genuine
   regression signal for those cases, where a prior result does exist to
   compare against).
4. Write
   `lcats/project/design/segmentation-combined-boundary-fix-feasibility.md`
   with the root-cause findings (including any inconclusive verdicts,
   reported as such), the two separate margin distributions, the
   simulation results (with per-newly-recovered-match correctness
   verdicts), and a plain recommendation.
5. If a combined-implementation WI is recommended, note that as a
   follow-up - do not file or implement it as part of this item.

## Non-Goals

- Does not implement the prompt-side fix in production
  (`scene_analysis.py`) or the code-side window-widening
  (`text_segmenter.py`) - simulation and analysis only.
- Does not spend any real API budget - all analysis reuses already-
  committed real data from `WI-SEGMENT-0098` and `WI-SEGMENT-0101`.
- Does not loosen the match criteria used anywhere in this analysis -
  the simulation must use the same strict exact/typography/whitespace/
  case-tolerant matching production already uses, never a fuzzy
  similarity threshold.
- Does not decide the combined-implementation question by itself if the
  evidence remains inconclusive - "defer, need a larger sample" is an
  acceptable and expected outcome, not a failure of this item.

## Acceptance Criteria

(see frontmatter `acceptance:` above)

## Validation

- lrh validate
- test_output

## Risk Notes

- **This item's own honesty bar matters more than a clean-sounding
  conclusion.** Both parent investigations already flagged their
  evidence as thin; this item's job is to state plainly whether combining
  them clears a higher bar or merely restates the same thinness with
  extra steps - not to manufacture confidence the data doesn't support.
- **The false-accept check in the simulation is the safety-critical
  part.** Per `WI-SEGMENT-0059`, a widened window that ever silently
  prefers a wrong match over the correct one is a stop condition for
  recommending implementation, not a tuning parameter to adjust past.
- **Root-causing the 2 regressions might turn up nothing conclusive**
  given only one real trace per story - "inconclusive" is now an
  explicit acceptance-criteria outcome (review finding, PR #422), not
  just a caveat here; say so plainly rather than forcing a
  confident-sounding explanation.
- **Start-side and end-side overshoot failures are different failure
  modes and must not be conflated** (review finding, PR #422) - only
  end-boundary widening is in scope, per `WI-SEGMENT-0098`'s own
  recommendation; the 4 real start-side failures in this dataset
  characterize a distinct, out-of-scope pattern worth flagging as a
  possible future follow-on, not folded into the end-margin sizing.

## Related Workstream and Designs

- Workstream: `lcats/project/workstreams/proposed/WS-PILOT-IMPROVEMENTS.md`
- Design: `lcats/project/design/segmentation-paragraph-boundary-truncation-investigation.md`
  (`WI-SEGMENT-0098`'s original window-widening recommendation)
- Design: `lcats/project/design/segmentation-paragraph-boundary-prompt-consistency-investigation.md`
  (`WI-SEGMENT-0101`'s reworded-prompt ablation and its unresolved
  regressions)
- Work item: `lcats/project/work_items/resolved/WI-SEGMENT-0059.md`
  (the standing safety principle this item's simulation must respect)
