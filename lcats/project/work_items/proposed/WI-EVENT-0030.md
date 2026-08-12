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
  - WI-ASSESS-0031
  - WI-ASSESS-0051
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
  - A stratified sample of 5-10 stories per genre is run through the Event-Role-World pipeline with the story-level cross-segment relation pass (WI-EVENT-0029) enabled, using the exact four genres lcats assess --genre already classifies (science fiction, horror, western, romance) - no genre outside this set is used as a stratum
  - Per-genre cross-segment-only relation density is reported as a metric computed directly from each story's cross_segment_relations and weakly_inferred_cross_segment_relations lists (count per 1000 words), kept separate from - not folded into - the existing total relations_per_1000_words baseline.summarize_annotations already reports, since that total mixes cross-segment and same-segment counts and cannot by itself confirm or contradict a cross-segment-specific claim
  - The relation types counted toward the headline cross-segment density figure are stated explicitly (all relation_type values are counted, matching how the existing total relations_per_1000_words already counts every type without filtering)
  - Findings state plainly whether the larger sample confirms, weakens, or contradicts WI-EVENT-0028's finding that science fiction/horror shows materially more long-range cross-segment causal chains than the other strata
  - Stories whose run produced any segment- or story-level extraction_errors are excluded from the aggregated density figures (not silently counted as zero/partial) and are reported separately as excluded/failed runs, with a count and reason
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

Run a larger, stratified empirical pilot (5-10 stories per genre, across
the four genres `lcats assess --genre` classifies: science fiction,
horror, western, romance) measuring cross-segment-only relation density
across genres, using the story-level relation pass WI-EVENT-0029
implemented. This supersedes WI-EVENT-0028's 4-story convenience sample (2
Lovecraft science-fiction/horror stories vs. 1 mystery, 1 general-fiction
story — neither a validated genre stratum) with a properly stratified
measurement using the corpus's actual genre-classification tooling, sizing
the effect precisely enough to support a paper-facing density figure.

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
  (or `corpora/` if a released equivalent exists), covering the four
  genres `lcats assess --genre` supports (`science fiction`, `horror`,
  `western`, `romance` — see `assess.py`'s `VALID_GENRES`). Mystery and
  adventure are not classifiable genres in this tooling today (detect mode
  falls back to `"other"` for both) and are explicitly not used as strata;
  if a finer split within a genre (e.g. isolating mystery-adjacent stories)
  is wanted later, that requires extending genre classification first, out
  of scope for this item.
- Run the full Event-Role-World pipeline (`processor.process_segments`,
  with `include_cross_segment_relations=True`) over each sampled story
  using a real LLM backend — this pilot requires actual pipeline output,
  not a manual reading exercise like WI-EVENT-0028's.
- Compute the headline metric — cross-segment-only relation density — by
  counting each story's `cross_segment_relations` and
  `weakly_inferred_cross_segment_relations` entries directly (all
  `relation_type` values counted, no filtering) and normalizing per 1000
  words, **not** via `baseline.summarize_annotations(annotations, story)`
  alone, since that function's `relations_per_1000_words` folds
  cross-segment relations into the same total as same-segment ones and
  cannot isolate the cross-segment-specific effect this pilot measures.
  Report the existing folded total alongside the cross-segment-only figure
  for context, clearly labeled as two different metrics.
- Detect and exclude stories whose run produced any segment- or
  story-level `extraction_errors` from the aggregated per-genre figures —
  `processor.process_segments` deliberately catches and records API/
  extraction failures rather than raising, so a transient failure must not
  silently become an undercounted zero in the genre mean. Report excluded/
  failed runs (count and reason) alongside the results.
- Record cost/latency (`PassUsage` records, particularly the
  `"story_relation"` pass) alongside the density findings, since the
  proposal's Cost and baseline requirements apply to this pilot's own run
  as much as to the pipeline itself.
- Report findings plainly: confirm, weaken, or contradict WI-EVENT-0028's
  smaller-sample finding, with the density numbers to support whichever
  conclusion the data shows.

## Dependencies / Order

**Added 2026-07-26 (via `depends_on`):** this item depends on
`WI-ASSESS-0031`, which extends `VALID_GENRES` from 4 to 8 genres per
`project/design/event-role-world-genre-target-reconciliation.md` ("Gap 1").
**Resolved 2026-08-07:** `WI-ASSESS-0031` landed (PR #224) — `VALID_GENRES`
now has all 8 genres.

**Added 2026-08-08 (via `depends_on`):** this item also depends on
`WI-ASSESS-0051` ("Gap 2" — run the current-classifier full-corpus genre
survey). The design doc doesn't name either work item directly, but its
own Gap 3 sequencing (`event-role-world-genre-target-reconciliation.md:274-277`)
says both follow-up items ("A", the corpus survey, and "B", this item's
re-scope) depend on Gap 1 landing first, and that A should run before B
"so B's per-genre sampling draws from an actual current genre census
rather than the stale 2025-10 numbers" - i.e. B (this item) depends on A's
(`WI-ASSESS-0051`'s) output, even though the doc predates either work
item's ID. As of this note, `WI-ASSESS-0051` is `status: proposed`, not
yet implemented - its survey has not run.

**Why the content re-scope below is still deferred, not done in this
edit:** this item's Scope/Summary/Required Changes sections still commit
to "5-10 stories per genre" against the original 4 genres (SF, horror,
western, romance) — a number chosen when those 4 genres' corpus
representation was already roughly known. The 4 new genres (humor,
mystery, fantasy, adventure) have no verified current-classifier counts —
`WI-ASSESS-0051`'s survey is what will produce them. Rewriting this item's
strata list and sample-size language *now*, before that survey exists,
would mean guessing at exactly the numbers the reconciliation effort has
been deliberately avoiding guessing at (see the design doc's own
open-flag note on the original genre thresholds not holding up under the
one existing, older corpus count). **Do not execute this item's pilot, and
do not finalize its 8-genre content, until `WI-ASSESS-0051` has produced
real per-genre counts** — at that point, re-scope the Scope/Summary/
Required Changes/Risk Notes sections below using those real numbers, not
before.

## Required Changes

1. Create `experiments/03_cross_segment_relation_pilot/run_pilot.py` (or
   equivalently named script) that selects the stratified sample (using
   `lcats assess --genre`'s four supported genres as strata), runs the
   pipeline over each story, detects and excludes any story with
   segment- or story-level `extraction_errors` from the aggregate, and
   writes per-story and per-genre summary results — computing the
   cross-segment-only density directly from each story's
   `cross_segment_relations`/`weakly_inferred_cross_segment_relations`
   fields, not from `baseline.summarize_annotations`'s folded total alone.
2. Create `experiments/03_cross_segment_relation_pilot/results/` holding
   the raw run output (JSONL/CSV, per the existing `export.py` table
   conventions) needed to reproduce the reported figures, including which
   stories were excluded and why.
3. Create `experiments/03_cross_segment_relation_pilot/README.md`
   documenting the sample selection methodology (genre strata, why
   mystery/adventure are not used), the metric definitions (cross-segment-
   only density vs. the existing folded total, reported side by side), the
   per-genre density findings, and the comparison against WI-EVENT-0028's
   smaller sample.
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
- Genre strata are fixed to what `lcats assess --genre` actually supports
  (science fiction, horror, western, romance) — WI-EVENT-0028's original
  mystery/general-fiction comparison stories are not representable in this
  stratification and are not part of this pilot's sample; the results
  README should note this explicitly so a reader does not assume identical
  comparison genres across the two work items.
- Conflating the cross-segment-only density metric with the existing
  folded `relations_per_1000_words` total would make the pilot's headline
  finding unable to confirm or contradict WI-EVENT-0028's cross-segment-
  specific claim — the two metrics must be computed and reported
  separately, as this item's acceptance criteria require.
- If the larger sample contradicts WI-EVENT-0028's smaller-sample finding,
  that is a valid, complete, and important result — report it plainly
  rather than treating it as a failed pilot.

## Related Workstream and Designs

- Design: `project/design/proposals/adopted/lcats-event-role-world-extractor/00_proposal.md`
- Design: `project/design/event-role-world-cross-segment-relations-evaluation.md`
