---
resolution: null
blocked_reason: null
blocked: false
id: WI-EVENT-0033
title: Add schema-hardened structured output to scene/story analysis extractors
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
  - WS-EVENT-STRUCTURED-OUTPUT-RELIABILITY
related_design:
  - lcats/project/audits/2026-07-27-erw-pipeline-structured-output-reliability-audit.md
  - lcats/project/design/proposals/adopted/lcats-event-role-world-extractor/00_proposal.md
depends_on: []
blocked_by: []
expected_actions:
  - edit_file
  - run_tests
  - create_pr
forbidden_actions:
  - force_push
  - delete_branch
  - implement_new_architecture
acceptance:
  - scene_analysis.py's make_segment_extractor (Stage 1 segmentation) uses a tool_schema= structured-output call instead of unconstrained json_object mode
  - scene_analysis.py's make_semantics_extractor (per-segment semantics judgment) uses a tool_schema= structured-output call instead of unconstrained json_object mode
  - story_analysis.py's make_doc_classification_extractor (whole-text document classification) uses a tool_schema= structured-output call instead of unconstrained json_object mode
  - Both real consumers of make_segment_extractor's bare-list output are updated to match whatever extracted_output shape the schema-hardened segment extractor now returns: story_processors.py:142 (segments = seg_extraction.get("extracted_output") or []) and experiments/03_cross_segment_relation_pilot/run_pilot.py's _segment_story (:277, segments = seg_result.get("extracted_output") or []) — with no regression to either caller's existing behavior or tests
  - The segmentation fix measurably reduces the parsing_error exclusion rate seen live during WI-EVENT-0030 dogfooding (11 of 17 sampled stories, 65%, excluded with claude-haiku-4-5-20251001), verified by re-running the same sampled story set (or an equivalent smoke sample) through the fixed extractor and comparing exclusion counts
  - lrh validate reports 0 errors
required_evidence:
  - manual_review
  - lrh_validate
  - test_output
artifacts_expected:
  - lcats/src/lcats/analysis/scene_analysis.py
  - lcats/src/lcats/analysis/story_analysis.py
  - lcats/src/lcats/analysis/story_processors.py
  - experiments/03_cross_segment_relation_pilot/run_pilot.py
---

## Summary

Retrofit the three LCATS extractors that still use fully unconstrained
`json_object`-mode JSON-in-text output — `scene_analysis.py`'s
`make_segment_extractor` and `make_semantics_extractor`, and
`story_analysis.py`'s `make_doc_classification_extractor` — with a
`tool_schema=` structured-output call, matching the pattern the
Event-Role-World extractors already use. This is a more novel design
problem than WI-EVENT-0032's fixes, because `llm_extractor.py`'s
`extract()` behaves differently once `tool_schema` is set: `extracted_output`
becomes the whole parsed dict rather than an `output_key`-unwrapped value,
which would change `make_segment_extractor`'s output shape from a bare list
to `{"segments": [...]}` and break both of its real callers —
`story_processors.py:142` and
`experiments/03_cross_segment_relation_pilot/run_pilot.py`'s
`_segment_story` (`:277`) — which each expect a bare list today. This item
must design around that shape change for both callers, not just add a
schema to the shared factory function in isolation.

## Problem / Context

The 2026-07-27 ERW pipeline audit's Category C confirms `scene_analysis.py`'s
segmentation extractor is the actual, currently-blocking reliability
problem in the pipeline — worse than either of the two crashes WI-EVENT-0032
fixes: a real run with `claude-haiku-4-5-20251001` excluded 11 of 17 sampled
stories (65%) with `extraction_error="parsing_error"`, and the `western`
genre stratum had zero included stories as a result. The governing
Event-Role-World extractor proposal's own Implementation prerequisites
section already flagged the scene/sequel prompts' `json_object` mode as the
weaker pattern the ERW stages were specifically designed to replace via
`tool=` — this gap was a known, accepted limitation at proposal time, not
an oversight introduced later, but it was left unfixed pending this
broader audit and scoping step.

### Duplication search
- In-repo: No existing work item retrofits these three extractors. The
  governing Event-Role-World proposal names this gap explicitly as a
  Non-Goal for the ERW work itself ("scene/sequel extraction" is not being
  reimplemented) — this item does not reimplement segmentation, it only
  hardens its existing output contract.
- Sibling repos: None identified.
- External libraries: None identified.
- Recommendation: Proceed.

### Demand search
- Work items: WI-EVENT-0030's audit note requests this scoping step
  directly, describing Category C as "a separate, more novel design
  problem per extractor" needing to address the `story_processors.py`
  blast radius, not just bolt on a schema.
- Proposals: The governing Event-Role-World extractor proposal's
  Implementation prerequisites section already recommends this direction.
- Backlog: No matching entries.
- Recommendation: Proceed.

## Scope

- Design a `tool_schema` for `make_segment_extractor`'s segment output
  (list of segments, each with the fields the existing prompt already
  requests) and wire it through `extract()`'s `tool=` path.
- Decide and implement how to preserve a bare-list `extracted_output` for
  `make_segment_extractor`'s two real consumers —
  `story_processors.py:142` and
  `experiments/03_cross_segment_relation_pilot/run_pilot.py`'s
  `_segment_story` (`:277`) — despite `tool_schema` mode's
  whole-dict-return behavior. (`story_processors.py:76` only constructs
  the extractor; it is not itself a consumption site.) Options include
  (a) unwrapping the single top-level key at each call site, (b) a
  second, schema-hardened extractor variant specific to these callers, or
  (c) another design; the chosen approach and its rationale must be
  recorded in this item's implementation, and both callers' existing
  tests must still pass unmodified in behavior (only in internal
  implementation, if needed).
- Apply the same `tool_schema=` treatment to `make_semantics_extractor`
  (`output_key="judgment"`) and `make_doc_classification_extractor`
  (`output_key="classification"`), auditing each for its own callers
  before assuming the same unwrapping approach applies identically.
- Verify the segmentation fix's real-world effect: re-run (or smoke-test)
  the same sampled story set from the live dogfooding run that saw a 65%
  exclusion rate, and report the new exclusion rate for comparison.
- Add or update test coverage for all three retrofitted extractors and for
  `story_processors.py`'s adapted call sites.

## Non-Goals

- Does not reimplement scene/sequel segmentation logic itself — the
  governing proposal already treats that as a Non-Goal; this item only
  hardens the existing extractors' output contract.
- Does not implement WI-EVENT-0032's Category A/B/D fixes — those are a
  separate item, unconstrained by comparison, since this item's scope is
  specifically the three extractors outside `event_role_world/`.
- Does not implement Category E (cost/logging/checkpointing/local models).
- Does not change `story_processors.py`'s public behavior or existing
  callers' expectations — only its internal handling of the segmentation
  extractor's new output shape, verified by its existing tests continuing
  to pass.

## Acceptance Criteria

(see frontmatter `acceptance:` above)

## Validation

- lrh validate
- scripts/test (full suite, including `story_processors.py`'s existing
  tests unmodified in behavior, plus new tests for all three retrofitted
  extractors)
- scripts/lint
- Re-run or smoke-test against the same sampled story set that saw the
  live 65% exclusion rate, reporting the new rate

## Risk Notes

- The `extracted_output` shape change between `tool_schema` and
  non-`tool_schema` modes is the central design risk this item must solve
  correctly — an incomplete fix that changes `make_segment_extractor`'s
  return shape without updating both `story_processors.py` call sites
  would silently break Stage 1 segmentation for every downstream caller,
  a strictly worse outcome than the current parsing-error exclusion rate.
- `make_semantics_extractor` and `make_doc_classification_extractor` are
  not exercised by the current pilot, so their failure rates are
  unmeasured (not absent, per the audit) — treat their fixes with the same
  care as segmentation's even without a live failure rate to compare
  against.
- If the segmentation fix's measured exclusion-rate improvement is smaller
  than expected, report that plainly rather than treating it as a failed
  fix — the audit's own finding is that `json_object` mode is *a* cause of
  the exclusion rate, not necessarily the only one.

## Related Workstream and Designs

- Workstream: `project/workstreams/proposed/WS-EVENT-STRUCTURED-OUTPUT-RELIABILITY.md`
- Design/audit: `lcats/project/audits/2026-07-27-erw-pipeline-structured-output-reliability-audit.md`
- Design: `lcats/project/design/proposals/adopted/lcats-event-role-world-extractor/00_proposal.md`
