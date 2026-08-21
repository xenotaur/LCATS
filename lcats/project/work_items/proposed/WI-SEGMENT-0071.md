---
resolution: null
blocked_reason: null
blocked: false
id: WI-SEGMENT-0071
title: Diagnose paragraph misnumbering segmentation alignment failures
type: investigation
status: proposed
priority: high
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
  - lcats/project/work_items/resolved/WI-SEGMENT-0069.md
  - lcats/project/work_items/proposed/WI-SEGMENT-0070.md
depends_on:
  - WI-SEGMENT-0069
  - WI-SEGMENT-0070
blocked_by: []
expected_actions:
  - create_file
  - edit_file
  - run_tests
  - create_pr
forbidden_actions:
  - force_push
  - delete_branch
  - implement_alignment_fix
  - widen_search_range_without_distribution_data
  - reintroduce_full_document_fallback
  - fix_near_miss_quoting_bucket
acceptance:
  - "A diagnostic sample after WI-SEGMENT-0070 classifies paragraph_misnumbering_large_margin and paragraph_misnumbering_narrow_margin cases with real counts and cited examples"
  - "The report tests at least offset drift, paragraph-density, boundary off-by-one, and prompt/marker interpretation hypotheses against captured parsed_output and source text"
  - "The report recommends fix now, defer, or reject for paragraph misnumbering, with a concrete safe-fix sketch only if supported by evidence"
  - "No production alignment behavior is changed"
  - "lrh validate reports 0 errors"
required_evidence:
  - manual_review
  - lrh_validate
  - test_output
artifacts_expected:
  - lcats/project/design/segmentation-paragraph-misnumbering-diagnostics.md
  - experiments/03_cross_segment_relation_pilot/classify_alignment_failures.py
  - experiments/03_cross_segment_relation_pilot/classify_alignment_failures_test.py
---

## Summary

Investigate the paragraph-misnumbering segmentation alignment failures that
`WI-SEGMENT-0069` explicitly deferred. The output is a diagnostic report with
real evidence and a fix/defer/reject recommendation, not an implementation.

## Problem / Context

`WI-SEGMENT-0069` classified 6 of 21 remaining alignment failures as
`paragraph_misnumbering_large_margin` or
`paragraph_misnumbering_narrow_margin`. The design doc found no visible
correlation with paragraph count in the small sample and recommended
diagnostic sampling before any fix design. `WI-SEGMENT-0070` intentionally
forbids fixing paragraph misnumbering, so this item covers that unhandled
category after the narrow marker/typography fix lands.

### Duplication search

- In-repo: No existing proposed work item covers paragraph-misnumbering
  diagnostics. Related but not duplicate: `WI-SEGMENT-0069` identified the
  category, and `WI-SEGMENT-0070` explicitly excludes it.
- Sibling repos: None identified.
- External libraries: None identified. This is an LCATS-specific diagnostic
  problem involving model-provided paragraph IDs, corpus paragraph indexing,
  and alignment search bounds.
- Recommendation: Proceed.

### Demand search

- Work items: Found `WI-SEGMENT-0069`, which recommends follow-up diagnostic
  sampling; found `WI-SEGMENT-0070`, which names paragraph misnumbering as a
  non-goal.
- Proposals: No matching proposed design proposal found.
- Backlog: The segmentation alignment backlog/design trail points to the same
  failure category through
  `lcats/project/design/segmentation-alignment-failure-categories.md`.
- Recommendation: Proceed; no existing item should be closed by filing this
  one.

## Scope

- Analyze paragraph-misnumbering failures after `WI-SEGMENT-0070` removes the
  known marker/typography cases.
- Use captured `parsed_output` and source text wherever possible so
  diagnostics do not require unnecessary fresh LLM calls.
- Test concrete hypotheses about offset drift, paragraph-density effects,
  paragraph-boundary off-by-one behavior, and model interpretation of
  paragraph markers.
- Record a design/diagnostic report with examples, counts, and a
  recommendation.

## Required Changes

1. Run or reuse a bounded segmentation reliability sample after
   `WI-SEGMENT-0070` lands, with explicit real-spend approval if new Anthropic
   calls are needed.
2. Extend or reuse
   `experiments/03_cross_segment_relation_pilot/classify_alignment_failures.py`
   to extract diagnostics needed for paragraph-misnumbering hypotheses.
3. Write
   `lcats/project/design/segmentation-paragraph-misnumbering-diagnostics.md`
   with methodology, real examples, category counts, hypothesis results, and
   recommendation.
4. If a fix is recommended, sketch the narrow safe design and file a separate
   deliverable WI rather than implementing it here.
5. If no safe fix is supported, state that clearly and define the stop
   condition for this category.

## Non-Goals

- Do not implement an alignment fix.
- Do not widen the search range or restore full-document fallback.
- Do not treat near-miss quoting or fuzzy matching as part of this item.
- Do not retry or tune prompts until a preferred result appears.

## Acceptance Criteria

- A diagnostic sample after `WI-SEGMENT-0070` classifies
  paragraph-misnumbering cases with real counts and cited examples.
- The report tests offset drift, paragraph-density, boundary off-by-one, and
  prompt/marker interpretation hypotheses.
- The report makes a clear fix/defer/reject recommendation.
- Production alignment behavior is unchanged.
- `lrh validate` reports 0 errors.

## Validation

- `scripts/version tools`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`

## Risk Notes

- New live sampling may cost real Anthropic spend; get explicit approval
  before any real API call.
- The category may remain inconclusive; that is a valid outcome if the report
  states what evidence is still missing.
- A passing diagnostic should not silently authorize a code fix.
  Implementation must be a separate WI.
