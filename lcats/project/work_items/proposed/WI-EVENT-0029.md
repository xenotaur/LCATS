---
resolution: null
blocked_reason: null
blocked: false
id: WI-EVENT-0029
title: Implement story-level cross-segment relation pass for Event-Role-World extractor
type: deliverable
status: proposed
priority: medium
owner: unassigned
contributors: []
assigned_agents: []
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap: []
related_workstreams:
  - WS-EVENT-STORY-RELATIONS
related_design:
  - project/design/proposals/adopted/lcats-event-role-world-extractor/00_proposal.md
  - project/design/event-role-world-cross-segment-relations-evaluation.md
depends_on:
  - WI-EVENT-0026
  - WI-EVENT-0028
blocked_by: []
expected_actions:
  - create_file
  - edit_file
  - run_tests
  - create_pr
forbidden_actions:
  - implement_option_b_event_index
  - implement_option_c_widened_window
  - force_push
  - delete_branch
acceptance:
  - A new relation-extraction pass implements option A - running once per story after schema.reconcile_story_annotations, using each event's already-resolved EvidenceSpan as one endpoint's evidence, and excluding same-segment links already covered by stage 6a
  - A new PassUsage entry (e.g. "story_relation") records the pass's cost per the existing cost/baseline reporting pattern
  - Story-level relations are held in StoryWorldAnnotation (or an equivalent story-level container), distinct from per-segment relations
  - export.build_analysis_tables includes story-level relations in its "relations" table
  - Story-level relation IDs are made globally unique (segment-qualified, e.g. "{segment_id}:{relation_id}", mirroring how reconcile_story_annotations already qualifies event IDs) before any deduplication is attempted, since raw relation_id values are not unique across segments today and reusing them for dedup would silently discard unrelated relations
  - baseline.summarize_annotations includes story-level relations in relations_per_1000_words, with deduplication keyed on the new globally-unique relation identity against per-segment relations
  - Story-level relations preserve the weakly_inferred/explicit/strongly_implied certainty partition into their reporting: weakly_inferred story-level relations are counted under weakly_inferred_relations_per_1000_words (as per-segment weakly_inferred relations already are), not mixed into the primary relations_per_1000_words density metric
  - The corpus's actual story-length distribution is checked to decide whether option A's long-story windowing caveat (hierarchical chapter-then-story pass) must be built now, with the decision and rationale documented
  - lrh validate reports 0 errors and scripts/test passes
required_evidence:
  - lrh_validate
  - test_output
  - manual_review
artifacts_expected:
  - lcats/lcats/analysis/event_role_world/relation_extractor.py (extended, not new)
  - lcats/lcats/analysis/event_role_world/schema.py (extended, not new)
  - lcats/lcats/analysis/event_role_world/processor.py (extended, not new)
  - lcats/lcats/analysis/event_role_world/export.py (extended, not new)
  - lcats/lcats/analysis/event_role_world/baseline.py (extended, not new)
  - lcats/tests/analysis_tests/event_role_world_test.py (extended, not new)
---

## Summary

Implement the architecture WI-EVENT-0028 determined is needed and
recommended: a post-reconciliation story-level relation pass (option A)
that discovers causal, enabling, preventing, temporal, motivational, and
explanatory relations whose two endpoints live in different segments —
something the current per-segment stage-6 pass
(`relation_extractor.py`, WI-EVENT-0026) structurally cannot represent,
since it only ever receives its own segment's event IDs and
`RELATION_SYSTEM_PROMPT` forbids linking outside that list.

## Problem / Context

`WS-EVENT-STORY-RELATIONS` coordinates this implementation.
`WI-EVENT-0028`'s investigation (`project/design/event-role-world-cross-segment-relations-evaluation.md`,
merged PR #154) ran a direct reading-based pilot over four corpus stories
and found a clear, genre-differentiated result: both SF/horror stories
sampled (Lovecraft's "The Colour Out of Space" — 4 long-range causal
links; "Cool Air" — 2) exhibited multiple long-range causal chains, while
the mystery ("The Engineer's Thumb") and general-fiction ("After Twenty
Years") comparison stories exhibited none. This confirmed that
per-segment-only relation counting would undercount SF's causal density
specifically, threatening the validity of the paper's central genre
comparison, and recommended option A as the architecture to fix it.

### Duplication search
- In-repo: No existing story-level relation extraction exists in `lcats/`.
  `schema.reconcile_story_annotations` (WI-EVENT-0026) performs story-level
  entity alias reconciliation and same-segment relation ID qualification
  only — its own docstring explicitly disclaims discovering cross-segment
  relations.
- Sibling repos: None identified.
- External libraries: None identified.
- Recommendation: Proceed.

### Demand search
- Work items: None found beyond WI-EVENT-0028's recommendation and
  WS-EVENT-STORY-RELATIONS's exit criteria requiring this item.
- Proposals: None found beyond the governing Event-Role-World extractor
  proposal, which this item extends per its "cross-segment relations"
  schema-sketch expectation.
- Backlog: No matching entries.
- Recommendation: No action.

## Scope

- New relation-extraction pass (a new `relation_extractor.py` function, or
  a second tool schema in the same module) that runs once per story, after
  `schema.reconcile_story_annotations` has produced global entity IDs and
  the full list of segment-qualified events.
- Build a compact representation of every story-level event (predicate,
  event type, segment ID, and its already-resolved `EvidenceSpan`) to pass
  as context to this pass, reusing each event's evidence span as one
  endpoint's evidence rather than requiring a fresh quote search across a
  multi-segment text blob.
- Scope this pass to same-segment-excluded, cross-segment links only, to
  avoid double-counting relations already discovered by the existing
  stage-6a per-segment pass.
- Reuse `EventRelation.certainty` (`explicit`/`strongly_implied`/
  `weakly_inferred`) unchanged for these new relations — no new schema
  field is needed to keep speculative cross-segment links identifiable.
  Downstream reporting must still route `weakly_inferred` story-level
  relations into the same separate density bucket
  (`weakly_inferred_relations_per_1000_words`) that per-segment
  weakly-inferred relations already use, rather than aggregating both
  certainty layers into the primary metric.
- New `PassUsage` entry (e.g. `"story_relation"`) for cost/token visibility,
  consistent with the existing cost/baseline reporting pattern.
- Extend `export.py`'s `build_analysis_tables()` to include story-level
  relations in the `"relations"` table.
- Qualify story-level relation IDs to be globally unique before any
  deduplication is attempted — `schema.reconcile_story_annotations()`
  today qualifies each relation's event endpoints but leaves `relation_id`
  itself unchanged, and separate segment-level LLM calls can both emit a
  common ID such as `r1`; deduplicating on the raw ID would discard
  unrelated relations and silently undercount density. Extend the ID
  qualification to relations themselves (e.g. `"{segment_id}:{relation_id}"`
  for the story-level pass's own new relations), or use an equivalent
  composite identity.
- Extend `baseline.py`'s `summarize_annotations()` to include story-level
  relations in `relations_per_1000_words`, de-duplicating by the new
  globally-unique relation identity against relations already present in
  a segment's own `relations` list (do not assume the same-segment-
  exclusion rule alone prevents double-counting).
- Preserve the `weakly_inferred`/`explicit`/`strongly_implied` certainty
  partition for story-level relations in `baseline.py`'s output: today
  `summarize_annotations()` reports `weakly_inferred_relations_per_1000_words`
  separately from the primary `relations_per_1000_words` for per-segment
  relations, and story-level relations must follow the same split rather
  than aggregating both certainty layers into one bucket.
- Check the corpus's actual story-length distribution before deciding
  whether option A's long-story windowing caveat (a hierarchical,
  chapter-level then story-level pass) needs to be built in this item, or
  whether story lengths in this corpus stay well within one call's context
  window and the caveat can remain a documented future concern.

## Required Changes

1. Add a story-level relation extraction function/tool schema to
   `lcats/lcats/analysis/event_role_world/relation_extractor.py` (or a
   sibling module, if that reads cleaner), following the existing
   entity/event/relation/discourse/hypothesis extractor pattern (LLM
   extraction via `JSONPromptExtractor` with a `tool_schema`).
2. Extend `lcats/lcats/analysis/event_role_world/schema.py` to hold the
   new story-level relations (on `StoryWorldAnnotation` or an equivalent
   container) and validate them (ID resolution against the global entity/
   event index, evidence-span alignment, same-segment-link exclusion,
   globally-unique/segment-qualified relation IDs). Keep `weakly_inferred`
   story-level relations distinguishable from `explicit`/`strongly_inferred`
   ones (e.g. via separate buckets or certainty-based filtering) so
   downstream reporting can preserve the existing certainty partition.
3. Extend `processor.py` (or the story-level orchestration point that
   calls `reconcile_story_annotations`) to run this pass once per story,
   after reconciliation, with its own `PassUsage`/token-tracking entry and
   the same routed-through-`extract()` error-handling pattern as the
   existing passes.
4. Extend `export.py`'s `build_analysis_tables()` and `validate_artifacts()`
   to cover story-level relations.
5. Extend `baseline.py`'s `summarize_annotations()` to include story-level
   relations in `relations_per_1000_words`, with de-duplication by the new
   globally-unique relation identity, and route `weakly_inferred`
   story-level relations into `weakly_inferred_relations_per_1000_words`
   rather than the primary density metric, matching how per-segment
   relations are already reported.
6. Check story-length distribution across the corpus (`lcats/data/`) and
   document the finding and windowing decision in the PR description or a
   short note in this work item's execution record.
7. Extend `lcats/tests/analysis_tests/event_role_world_test.py` covering
   the new schema, the extraction pass, its export/validation coverage,
   the baseline extension, same-segment exclusion, and de-duplication.

## Non-Goals

- Does not implement option B (growing per-story event index) or option C
  (widened per-segment window) — option A was the recommended
  architecture; the others are out of scope unless option A proves
  infeasible during implementation, in which case stop and report rather
  than switching architectures unilaterally.
- Does not run the larger stratified pilot (5-10 stories per genre) that
  WI-EVENT-0028 flagged as still needed before the paper publishes a
  cross-segment relation density figure — that is a corpus/methodology
  task for the paper, not an implementation task for this item.
- Does not modify or reopen WS-EVENT-CROSS-SEGMENT-RELATIONS,
  WS-EVENT-ROLE-WORLD, or any of their resolved work items.
- Does not choose the Worldcon paper's final statistical method.

## Acceptance Criteria

(see frontmatter `acceptance:` above)

## Validation

- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`

## Risk Notes

- Accuracy risk: the model reasons over compact event summaries rather
  than full original text for events outside the immediate story-level
  prompt for cross-segment endpoints — a real limitation, mitigated by
  keeping `EventRelation.certainty` populated so speculative links stay
  identifiable and separately partitioned, exactly as same-segment
  relations already are.
- Long-story context risk: if story-length distribution shows some stories
  exceed a practical single-call context window, this item must decide
  whether to cap the pass to salient/high-confidence events, or build the
  hierarchical windowing mitigation now rather than deferring it further.
- Double-counting risk: export and baseline changes must not assume the
  same-segment-exclusion rule alone prevents a relation from being counted
  twice; raw `relation_id` values are not globally unique across segments
  today, so dedup must key on a qualified, globally-unique relation
  identity, not the raw ID.
- Certainty-partition risk: `weakly_inferred` story-level relations must
  not be silently merged into the primary `relations_per_1000_words`
  metric — they need the same separate-bucket treatment
  `weakly_inferred_relations_per_1000_words` already gives per-segment
  weakly-inferred relations, or the paper's primary density figure would
  be contaminated with speculative links.

## Related Workstream and Designs

- Workstream: `project/workstreams/proposed/WS-EVENT-STORY-RELATIONS.md`
- Design: `project/design/proposals/adopted/lcats-event-role-world-extractor/00_proposal.md`
- Design: `project/design/event-role-world-cross-segment-relations-evaluation.md`
