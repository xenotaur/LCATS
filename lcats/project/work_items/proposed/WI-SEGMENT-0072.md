---
resolution: null
blocked_reason: null
blocked: false
id: WI-SEGMENT-0072
title: Evaluate safe fuzzy matching for near-miss segmentation anchors
type: evaluation
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
  - lcats/project/design/segmentation-alignment-failure-categories.md
  - lcats/project/work_items/resolved/WI-SEGMENT-0059.md
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
  - implement_production_fuzzy_matcher
  - weaken_exact_grounding
  - reintroduce_full_document_fallback
  - fix_paragraph_misnumbering
acceptance:
  - "A near-miss anchor evaluation corpus is built from a tracked fixture/output artifact containing real near-miss parsed_output, or from an explicitly approved replacement sample when no reusable artifact exists; it includes positive near-miss cases and negative decoy cases"
  - "At least one candidate fuzzy-matching policy is evaluated for recovery rate and false-positive risk before any production behavior change"
  - "The recommendation states adopt, defer, or reject fuzzy matching, with explicit false-positive thresholds and stop conditions"
  - "No production fuzzy matching or weakened quote grounding is implemented"
  - "lrh validate reports 0 errors"
required_evidence:
  - manual_review
  - lrh_validate
  - test_output
artifacts_expected:
  - lcats/project/design/segmentation-near-miss-fuzzy-matching-evaluation.md
  - experiments/03_cross_segment_relation_pilot/
  - experiments/03_cross_segment_relation_pilot/fixtures/
---

## Summary

Evaluate whether fuzzy matching can safely recover near-miss segmentation
anchors without reintroducing silent wrong matches. The output is an
evaluation and recommendation, not a production matcher.

## Problem / Context

`WI-SEGMENT-0069` found 10 of 21 remaining alignment failures were near-miss
quotes with small edit distances. The design doc explicitly warns that a
character-edit-distance-tolerant fuzzy match has false-positive risk and needs
dedicated design and evaluation before implementation. `WI-SEGMENT-0070`
fixes only marker leakage and quote/dash typography, and explicitly excludes
this near-miss bucket.

### Duplication search

- In-repo: No existing proposed work item evaluates fuzzy matching for
  near-miss segmentation anchors. Related but not duplicate:
  `WI-SEGMENT-0059` documents why unsafe fallback matching is dangerous;
  `WI-SEGMENT-0069` identifies the near-miss bucket; `WI-SEGMENT-0070`
  excludes it.
- Sibling repos: None identified.
- External libraries: String-similarity libraries exist, but they do not
  decide LCATS's safety policy for quote grounding or false-positive
  tolerance.
- Recommendation: Proceed with evaluation before any implementation.

### Demand search

- Work items: Found `WI-SEGMENT-0069`, which says fuzzy matching needs its own
  dedicated design and evaluation; found `WI-SEGMENT-0070`, which forbids
  fixing the near-miss bucket.
- Proposals: No matching proposed design proposal found.
- Backlog: The demand is currently captured in
  `lcats/project/design/segmentation-alignment-failure-categories.md`, not a
  separate backlog item.
- Recommendation: Proceed; no existing item should be closed by filing this
  one.

## Scope

- Build or derive an evaluation set for near-miss anchors, including real
  positive cases and realistic negative/decoy cases.
- Require a tracked fixture/output artifact containing the real near-miss
  `parsed_output`, or explicitly approve a replacement sample if no reusable
  artifact exists.
- Evaluate candidate fuzzy-matching policies for both recovery rate and
  false-positive risk.
- Define explicit thresholds and stop conditions for any future adoption.
- Record a design/evaluation report with a go/defer/reject recommendation.

## Required Changes

1. Confirm whether a tracked artifact already contains real near-miss
   `parsed_output` from `WI-SEGMENT-0069`/`WI-SEGMENT-0070`. Do not treat
   `experiments/03_cross_segment_relation_pilot/fixtures/wi_segment_0069_alignment_cases.json`
   as satisfying this requirement by itself; that fixture captures the
   marker-leakage and quote/dash cases used by `WI-SEGMENT-0070`, not the
   near-miss positives.
2. If no reusable tracked artifact exists, get explicit approval for a
   bounded replacement sample before running real Anthropic calls, and persist
   the resulting near-miss positives as a tracked fixture/output artifact.
3. Derive near-miss examples from the tracked `parsed_output` and source text.
4. Add negative/decoy cases that could expose wrong-span matches,
   repeated-text ambiguity, or overlap regressions like the failure mode
   documented by `WI-SEGMENT-0059`.
5. Evaluate candidate policies such as bounded edit distance, contiguous-run
   ratio, paragraph-window constraints, and uniqueness checks.
6. Write
   `lcats/project/design/segmentation-near-miss-fuzzy-matching-evaluation.md`
   with methodology, metrics, thresholds, results, and recommendation.
7. If fuzzy matching is recommended, file a separate deliverable WI for
   implementation.

## Non-Goals

- Do not implement production fuzzy matching.
- Do not weaken exact quote grounding or silently accept guessed spans.
- Do not reintroduce full-document fallback.
- Do not cover paragraph misnumbering; that is `WI-SEGMENT-0071`.

## Acceptance Criteria

- A near-miss evaluation corpus is built from a tracked fixture/output
  artifact containing real near-miss `parsed_output`, or from an explicitly
  approved replacement sample when no reusable artifact exists; it includes
  both positive near-miss cases and negative/decoy cases.
- At least one candidate fuzzy-matching policy is evaluated for recovery rate
  and false-positive risk.
- The report gives an adopt/defer/reject recommendation with explicit
  thresholds and stop conditions.
- Production alignment behavior is unchanged.
- `lrh validate` reports 0 errors.

## Validation

- `scripts/version tools`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`

## Risk Notes

- A high recovery rate is not enough if false positives can silently move
  segment boundaries to the wrong text.
- If realistic decoy coverage cannot be built from existing artifacts, the
  correct outcome is defer with a named evidence gap.
- If no tracked near-miss positive fixture exists, the executor must not invent
  positives from prose summaries; use an explicitly approved replacement sample
  and persist the result.
- Any implementation must be a separate WI after this evaluation lands.
