---
resolution: "Investigated via PR #420. Built an isolated, non-production reworded prompt variant deriving end_par_id/start_par_id from end_exact/start_exact's located position; ran a real 17-story API ablation (claude-haiku-4-5-20251001, $0.57 actual cost). Result: directionally positive, not conclusive - segment-level boundary overshoot dropped 12/177->8/162, anchor-level 12/350->9/321; the specific case that motivated the fix (the_voice_in_the_fog__leverage) resolved cleanly, but 2 stories showed new overshoot and one new error shape (bidirectional narrowing) appeared. Recommendation: adopt as a complement to WI-SEGMENT-0098's window-widening recommendation, not a replacement - do not implement in production from this evidence alone; a follow-on deliverable WI combining both, sized against a larger sample, would be the next step if pursued. No production behavior changed. Full results in lcats/project/design/segmentation-paragraph-boundary-prompt-consistency-investigation.md."
blocked_reason: null
blocked: false
id: WI-SEGMENT-0101
title: Investigate prompt-side fix for paragraph-boundary end_par_id/end_exact inconsistency
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
  - lcats/project/design/segmentation-paragraph-boundary-truncation-investigation.md
  - lcats/project/work_items/resolved/WI-SEGMENT-0098.md
  - lcats/src/lcats/analysis/scene_analysis.py
depends_on:
  - WI-SEGMENT-0098
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
  - "A reworded prompt variant is drafted (as an experimental variant, not a change to SCENE_SEQUEL_SYSTEM_PROMPT/SCENE_SEQUEL_USER_PROMPT_TEMPLATE in lcats/src/lcats/analysis/scene_analysis.py) that instructs the model to derive start_par_id from the paragraph containing start_exact's first character and end_par_id from the paragraph containing end_exact's last character - not merely 'the paragraph containing' the anchor, which is undefined when an anchor spans two paragraphs (a real case in the target cohort: the_voice_in_the_fog__leverage segment 3's end_exact spans paragraphs 34 and 35)"
  - "A real-API ablation cost estimate is presented to the user and explicitly approved before any spend"
  - "The ablation is run against a real cohort (the WI-EVENT-0033 17-story baseline cohort, or a documented comparable substitute) comparing the current production prompt's paragraph-boundary overshoot rate against the reworded variant's rate on the same or a freshly-run cohort"
  - "Results are reported honestly in a written report: whether the one-directional overshoot pattern from WI-SEGMENT-0098 shrinks, disappears, or persists under the reworded prompt, and whether the reworded prompt introduces any new failure mode (e.g. a changed alignment_error rate elsewhere, or degraded segment_type/GACD/ERAC classification quality)"
  - "No production prompt or code change is made based on this evidence alone - a go/no-go implementation decision is explicitly deferred to a separate follow-up"
  - "lrh validate reports 0 errors"
required_evidence:
  - manual_review
  - lrh_validate
  - test_output
artifacts_expected:
  - lcats/project/design/segmentation-paragraph-boundary-prompt-consistency-investigation.md
---

# Work Item: WI-SEGMENT-0101

## Summary

`WI-SEGMENT-0098` found that in 6 of the 10 real `WI-EVENT-0096` alignment
failures, the model's claimed `end_par_id` undercounts by 1-2 paragraphs
relative to where its own `end_exact` anchor text actually lands - always
in the same direction (the true text is always found in the paragraph
*after* the claimed `end_par_id`, never before). That investigation
concluded the root cause is a model-side attribution error and
recommended a code-side search-window widening, explicitly rejecting a
prompt-side fix on the grounds that the underlying narrative-continuity
ambiguity (which two paragraphs "count" as one scene beat) is a real
property of the source text that no prompt instruction can resolve.

Direct inspection of the actual production prompt
(`lcats/src/lcats/analysis/scene_analysis.py:99-105`,`:132-143`,`:189-220`)
shows that conclusion conflated two different questions. The prompt
documents `end_par_id`/`start_par_id` and `end_exact`/`start_exact` as
two independently-generated, redundant "location selectors" - there is
no instruction anywhere in the system prompt, the 7-step "Procedure you
MUST follow," or the tool schema requiring the model to verify that
`end_exact` is actually located inside the paragraph numbered
`end_par_id`. The narrative-continuity ambiguity WI-SEGMENT-0098
identified is real, but it only affects *which text the model picks* as
`end_exact` - it does not require `end_par_id` to be a second,
independently-guessed opinion about the same boundary. This item
investigates whether rewording the prompt so `end_par_id`/`start_par_id`
are explicitly derived from the located paragraph containing
`end_exact`/`start_exact` - rather than judged independently - reduces
or eliminates the pattern, tested via a real-API ablation rather than
assumed.

## Problem / Context

The current prompt's relevant instructions
(`lcats/src/lcats/analysis/scene_analysis.py:99-105`):

```
- start_par_id: integer paragraph id where the segment begins (inclusive).
- end_par_id: integer paragraph id where the segment ends (inclusive).
- start_exact: the FIRST <=120 characters of the segment, COPIED VERBATIM from the STORY text.
- end_exact: the LAST <=120 characters of the segment, COPIED VERBATIM from the STORY text.
```

are introduced as "Robust location selectors (PRIMARY)" - plural,
redundant-by-design. The 7-step "Procedure you MUST follow"
(`scene_analysis.py:132-143`) only asks the model to "Enforce
**Consistency Constraints** between label and checks fields" (step 7) -
referring to the `segment_type`/GACD/ERAC classification fields, not
`end_par_id` vs. `end_exact`. The tool schema
(`scene_analysis.py:189-220`) is pure JSON-Schema typing (`integer`,
`string` with no cross-field validation), which cannot express "field A
must locate inside the paragraph identified by field B" even if asked to
- that invariant can only come from a natural-language instruction or a
runtime self-check, and neither exists today.

Meanwhile `lcats.analysis.text_segmenter.align_segment` (production
code) computes its search window strictly as
`para_spans[start_par_id-1][0]` to `para_spans[end_par_id-1][1]` and
searches only inside it - it assumes `end_par_id` and `end_exact` always
agree. `WI-SEGMENT-0098`'s per-case findings are consistent with this
gap: for `easy_money__sinclair`, "paragraphs 117 and 118 are two short,
consecutive paragraphs continuing the same narrative beat... The model's
claimed `end_exact` text is drawn from paragraph 118's content, but it
labeled the segment's `end_par_id` as 117" - two separately-plausible
judgments (which paragraph does this scene "belong to," vs. what text
literally ends it) drifting apart because nothing asked the model to
reconcile them.

**The reworded rule must handle anchors that themselves cross a
paragraph boundary (review finding, PR #415).** "The paragraph containing
`end_exact`" is not always well-defined: in the same target cohort,
`the_voice_in_the_fog__leverage` segment 3's `end_exact` matches source
span `(7225, 7391)`, which straddles two real paragraphs -
paragraph 34 is `[7021, 7311)` and paragraph 35 is `[7313, 7391]`
(verified directly against the real story text via
`text_segmenter.paragraph_text_indexer`). A rule that just says "the
paragraph containing the anchor" could still emit 34 here and reproduce
exactly the failure this item is trying to fix. The reworded instruction
must specify a precise rule for this case - e.g., `start_par_id` comes
from `start_exact`'s first character, `end_par_id` from `end_exact`'s
last character - not left implicit.

### Duplication search

- In-repo: `WI-SEGMENT-0098` is the direct predecessor and already
  root-caused the failure pattern at the data level; it explicitly
  considered and rejected a prompt-side fix, but without inspecting the
  actual prompt text - this item re-examines that specific conclusion
  against the real prompt, not the underlying phenomenon `WI-SEGMENT-0098`
  already characterized. No other work item addresses prompt-level
  cross-field consistency for this pipeline's anchor fields.
- Sibling repos: None identified.
- External libraries: Not applicable - this is LCATS's own prompt design.
- Recommendation: Proceed; this is a genuinely distinct question
  (prompt design) from what `WI-SEGMENT-0098` already answered (data
  root-cause).

### Demand search

- Work items: Surfaced directly by user-driven review of `WI-SEGMENT-0098`'s
  conclusions in this session. No existing work item investigates a
  prompt-side fix for this pattern.
- Proposals: None identified.
- Backlog: No matching entry found.
- Recommendation: Proceed.

## Scope

- Draft a reworded instruction for `end_par_id`/`start_par_id` that asks
  the model to report `start_par_id` as the paragraph containing
  `start_exact`'s first character and `end_par_id` as the paragraph
  containing `end_exact`'s last character - a precise rule that resolves
  even when an anchor spans two paragraphs - rather than an
  independently-judged paragraph number. Keep this as an experimental
  prompt variant for the ablation; do not modify the production prompt as
  part of this item.
- Present a real-API cost estimate (model, expected token volume, cohort
  size) for the ablation and obtain explicit approval before spending.
- Run the ablation: the same (or a documented comparable) real cohort
  through both the current production prompt and the reworded variant,
  and measure the paragraph-boundary overshoot rate for each using the
  same methodology `WI-SEGMENT-0098` used (`_locate_anchor_span` against
  the full document, compared to the claimed window).
- Report results honestly, including any new failure modes the reworded
  prompt introduces elsewhere (e.g. classification quality, other
  alignment failures).
- State a plain recommendation - adopt, reject, or inconclusive/needs a
  larger sample - without implementing any production change.

## Required Changes

1. Draft the reworded `end_par_id`/`start_par_id` instruction text as an
   isolated prompt variant (e.g. a separate constant or parameter, not an
   in-place edit to `SCENE_SEQUEL_SYSTEM_PROMPT`), preserving every other
   instruction unchanged so the ablation isolates this one variable.
   Explicitly specify the cross-paragraph case: `start_par_id` from
   `start_exact`'s first character, `end_par_id` from `end_exact`'s last
   character - not an ambiguous "the paragraph containing the anchor."
2. Compute and present a cost estimate for running both the current and
   reworded prompts against the chosen real cohort; wait for explicit
   approval before any API spend.
3. Run both prompt variants against the same real cohort; for each
   resulting segment, replay `WI-SEGMENT-0098`'s own methodology
   (`text_segmenter.paragraph_text_indexer`, `_locate_anchor_span` against
   the full document) to measure whether `end_exact`/`start_exact` lands
   inside the claimed `[start_par_id, end_par_id]` range.
4. Write
   `lcats/project/design/segmentation-paragraph-boundary-prompt-consistency-investigation.md`
   with: the reworded instruction text, the cost estimate and approval
   record, per-story/per-segment results for both variants, the
   before/after overshoot-rate comparison, any new failure modes
   observed, and a plain recommendation.
5. Do not implement any production prompt or code change as part of this
   item, regardless of the ablation's outcome.

## Non-Goals

- Does not implement the reworded prompt in production
  (`scene_analysis.py`) - recommendation only, pending its own follow-up
  decision.
- Does not implement `WI-SEGMENT-0098`'s separately-recommended
  code-side search-window widening - that remains a distinct,
  still-unimplemented mitigation, complementary to (not replaced by) this
  item's prompt-side investigation.
- Does not re-litigate `WI-SEGMENT-0098`'s own root-cause finding (model
  misattribution, not a `text_segmenter` bug) - that stands; this item
  investigates only whether the model can be prompted into producing a
  self-consistent `end_par_id` given the anchor text it already commits to.
- Does not spend API budget without a presented estimate and explicit
  approval first.

## Acceptance Criteria

(see frontmatter `acceptance:` above)

## Validation

- lrh validate
- test_output (any new analysis script's own tests, if applicable)

## Risk Notes

- **A real-API ablation is required here, unlike `WI-SEGMENT-0098` and
  `WI-SEGMENT-0099`, which reused only already-committed data.** Cost
  estimate and explicit approval are non-negotiable gates before any
  spend, per this project's established practice.
- **The reworded instruction could introduce a new failure mode**: asking
  the model to perform a "reverse lookup" (find which paragraph number
  contains this text) is itself a precise-counting task over long
  documents, a known general LLM weak point. The ablation must measure
  overall failure rate, not just whether this specific pattern shrinks -
  a fix that reduces boundary-overshoot but increases some other
  alignment failure would not be a net win.
- **This item does not decide adoption.** Even a clean ablation result
  (pattern eliminated, no new failures) is evidence toward a production
  change, not authorization for one - a separate follow-up WI should
  implement it, per this project's established pattern of separating
  investigation from remediation.

## Related Workstream and Designs

- Workstream: `lcats/project/workstreams/proposed/WS-PILOT-IMPROVEMENTS.md`
- Design: `lcats/project/design/segmentation-paragraph-boundary-truncation-investigation.md`
  (the predecessor investigation this item re-examines and extends)
- Work item: `lcats/project/work_items/resolved/WI-SEGMENT-0098.md`
- Prompt under investigation: `lcats/src/lcats/analysis/scene_analysis.py`
