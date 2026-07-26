---
resolution: null
blocked_reason: null
blocked: false
id: WI-EVENT-0030
title: Run stratified cross-segment relation density pilot across genres
type: evaluation
status: proposed
priority: medium
owner: unassigned
contributors: []
assigned_agents: []
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap: []
related_workstreams: []
related_design:
  - project/design/proposals/adopted/lcats-event-role-world-extractor/00_proposal.md
  - project/design/event-role-world-cross-segment-relations-evaluation.md
depends_on:
  - WI-EVENT-0029
blocked_by: []
expected_actions:
  - create_file
  - edit_file
  - run_tests
  - create_pr
forbidden_actions:
  - modify_event_role_world_extractor
  - implement_new_architecture
  - force_push
  - delete_branch
acceptance:
  - A stratified sample of 5-10 stories per genre (SF, mystery, romance, adventure - the proposal's comparison genres) is run through the Event-Role-World pipeline with the story-level cross-segment relation pass (WI-EVENT-0029) enabled
  - Per-genre cross-segment relation density (relations_per_1000_words, computed via baseline.summarize_annotations with the story parameter) is reported, superseding WI-EVENT-0028's 4-story convenience sample with a larger, stratified one
  - Findings state plainly whether the larger sample confirms, weakens, or contradicts WI-EVENT-0028's finding that SF/horror shows materially more long-range cross-segment causal chains than mystery/romance/adventure
  - Results and methodology are recorded under experiments/03_cross_segment_relation_pilot/, per the experiments/README.md numbering convention
  - lrh validate reports 0 errors
required_evidence:
  - manual_review
  - lrh_validate
artifacts_expected:
  - experiments/03_cross_segment_relation_pilot/README.md
  - experiments/03_cross_segment_relation_pilot/run_pilot.py
  - experiments/03_cross_segment_relation_pilot/results/
---

## Summary

Run a larger, stratified empirical pilot (5-10 stories per genre) measuring
cross-segment relation density across genres, using the story-level
relation pass WI-EVENT-0029 implemented. This supersedes WI-EVENT-0028's
4-story convenience sample (2 Lovecraft SF/horror stories vs. 1 mystery, 1
general-fiction story) with a properly stratified measurement, sizing the
effect precisely enough to support a paper-facing density figure.

## Problem / Context

WI-EVENT-0028's investigation (`project/design/event-role-world-cross-segment-relations-evaluation.md`,
merged PR #154) established — via a small, convenience-selected 4-story
reading exercise, not a pipeline run — that SF/horror material exhibits
more long-range cross-segment causal chains than mystery/general-fiction
comparison genres, and recommended building option A (a post-reconciliation
story-level relation pass) to capture them. WI-EVENT-0029 (PR #156) shipped
that architecture. Both work items explicitly flagged that a larger,
stratified pilot should still run before the Worldcon paper publishes any
cross-segment relation density figure, since the 4-story sample was
sufficient only to answer WI-EVENT-0028's yes/no acceptance criterion, not
to size the effect precisely across genres.

### Duplication search
- In-repo: No existing stratified cross-segment relation density
  measurement exists. `experiments/01_classify_corpora/` and
  `experiments/02_llm_backend_comparison/` are unrelated prior experiments
  (genre classification and LLM backend comparison, respectively) but
  establish the `experiments/NN_name/` convention this item follows.
- Sibling repos: None identified.
- External libraries: None identified.
- Recommendation: Proceed.

### Demand search
- Work items: None found beyond WI-EVENT-0028's and WI-EVENT-0029's own
  "still needed" follow-up notes.
- Proposals: None found beyond the governing Event-Role-World extractor
  proposal, whose "Resulting scientific claim" section this pilot's
  findings would ground.
- Backlog: No matching entries.
- Recommendation: No action.

## Scope

- Select a stratified sample of 5-10 stories per genre from `lcats/data/`
  (or `corpora/` if a released equivalent exists), covering SF/horror and
  at least the mystery, romance, and adventure comparison genres already
  used elsewhere in the governing proposal.
- Run the full Event-Role-World pipeline (`processor.process_segments`,
  with `include_cross_segment_relations=True`) over each sampled story
  using a real LLM backend — this pilot requires actual pipeline output,
  not a manual reading exercise like WI-EVENT-0028's.
- Compute per-genre cross-segment relation density via
  `baseline.summarize_annotations(annotations, story)`, comparing genres on
  `relations_per_1000_words` (and `weakly_inferred_relations_per_1000_words`
  separately, per the existing certainty partition).
- Record cost/latency (`PassUsage` records, particularly the
  `"story_relation"` pass) alongside the density findings, since the
  proposal's Cost and baseline requirements apply to this pilot's own run
  as much as to the pipeline itself.
- Report findings plainly: confirm, weaken, or contradict WI-EVENT-0028's
  smaller-sample finding, with the density numbers to support whichever
  conclusion the data shows.

## Required Changes

1. Create `experiments/03_cross_segment_relation_pilot/run_pilot.py` (or
   equivalently named script) that selects the stratified sample, runs the
   pipeline over each story, and writes per-story and per-genre summary
   results.
2. Create `experiments/03_cross_segment_relation_pilot/results/` holding
   the raw run output (JSONL/CSV, per the existing `export.py` table
   conventions) needed to reproduce the reported figures.
3. Create `experiments/03_cross_segment_relation_pilot/README.md`
   documenting the sample selection methodology, the per-genre density
   findings, and the comparison against WI-EVENT-0028's smaller sample.
4. No changes to `lcats/lcats/analysis/event_role_world/` — this item
   consumes the existing pipeline, it does not modify it.

## Non-Goals

- Does not modify the Event-Role-World extractor's architecture or any of
  its existing passes.
- Does not implement option B or option C — option A is already shipped
  and is the only architecture this pilot measures.
- Does not choose the Worldcon paper's final statistical method — this
  item produces a density measurement input to that decision, not the
  decision itself.
- Does not re-litigate WI-EVENT-0028's yes/no need determination — that
  question is already answered; this item only sizes the effect more
  precisely.

## Acceptance Criteria

(see frontmatter `acceptance:` above)

## Validation

- lrh validate
- manual review of the results README against the raw results data for consistency

## Risk Notes

- Requires real LLM API calls across roughly 20-40 stories (4 genres x
  5-10 stories each) — a real cost/latency expenditure, not free; size the
  sample toward the lower end (5 per genre) if cost becomes a concern,
  and say so plainly in the results README rather than silently shrinking
  the sample.
- Genre labels must align with the corpus's existing genre-detection
  conventions (`lcats assess --genre`) rather than an ad hoc labeling
  scheme, so results are comparable to any other genre-stratified
  measurement already in the corpus.
- If the larger sample contradicts WI-EVENT-0028's smaller-sample finding,
  that is a valid, complete, and important result — report it plainly
  rather than treating it as a failed pilot.

## Related Workstream and Designs

- Design: `project/design/proposals/adopted/lcats-event-role-world-extractor/00_proposal.md`
- Design: `project/design/event-role-world-cross-segment-relations-evaluation.md`
