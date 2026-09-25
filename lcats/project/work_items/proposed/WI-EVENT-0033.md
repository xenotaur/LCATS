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
  - "Both real consumers of make_segment_extractor's bare-list output are updated to match whatever extracted_output shape the schema-hardened segment extractor now returns: story_processors.py:142 (segments = seg_extraction.get(\"extracted_output\") or []) and experiments/03_cross_segment_relation_pilot/run_pilot.py's _segment_story (:277, segments = seg_result.get(\"extracted_output\") or []) — with no regression to either caller's existing behavior or tests"
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

- Design and wire a `tool_schema` through `extract()`'s `tool=` path for
  all three extractors: `make_segment_extractor`, `make_semantics_extractor`,
  `make_doc_classification_extractor`.
- Preserve each extractor's existing `extracted_output` contract for its
  real callers, verified directly against `llm_extractor.py`'s two code
  paths (see Required Changes for the concrete design this implies).
- Update both real consumers of segmentation's output
  (`story_processors.py:142`, `run_pilot.py`'s `_segment_story:277`).
- Verify the segmentation fix's real-world effect against the live 65%
  exclusion rate.
- Add or update test coverage for all three retrofitted extractors and
  the two adapted call sites.

## Required Changes

1. **`make_segment_extractor` (Stage 1 segmentation):** add a
   `SEGMENT_TOOL_SCHEMA` whose **top-level property is still named
   `"segments"`** (an array of segment objects with all the fields the
   existing prompt already requests: `segment_id`, `segment_type`,
   `start_par_id`, `end_par_id`, `start_exact`, `end_exact`,
   `start_prefix`, `end_suffix`, `start_char`, `end_char`, `summary`,
   `cohesion` (nested object), `gacd`/`erac` (nested objects, nullable via
   a `["object", "null"]` type union — see `lcats.llm.tool_schema`'s
   `close_schema_objects`, which already supports this), `reason`,
   `confidence`), hardened via
   `lcats.llm.tool_schema.strict_tool_schema()` (WI-EVENT-0032's shared
   helper). **Keeping the `"segments"` wrapper key is required, not
   incidental**: confirmed directly against `llm_extractor.py`'s
   tool_schema code path — `result_aligner`/`result_validator` receive
   `parsed` (the tool_result) *before* any unwrapping, so
   `text_segmenter.segments_result_aligner`/`segments_auditor` (which
   both read `parsed_output.get("segments")` internally) work completely
   unchanged only if the schema's top level still nests the array under
   `"segments"`. The tradeoff this creates: `extracted_output` becomes
   `{"segments": [...]}` (the whole dict) instead of today's bare list,
   since the tool_schema path never applies the `output_key` unwrap the
   `json_object` path does — this is the one real, unavoidable shape
   change, addressed by item 4 below.
2. **`make_semantics_extractor` (per-segment semantics):** add a
   `SEMANTICS_TOOL_SCHEMA` whose top level is the judgment's own fields
   directly (`label`, `reason`, `confidence`, `checks` (nested), `evidence`
   (nested)) — **no wrapping `"judgment"` key**. This extractor has no
   `result_aligner`/`result_validator` (`text_indexer=None,
   result_aligner=None, result_validator=None`), so there is no reason to
   preserve a wrapper key, and omitting it keeps `extracted_output`'s
   shape byte-for-byte identical to today's `output_key="judgment"`
   unwrap — zero consumer changes needed. Confirmed against
   `annotate_segments_with_semantics`'s `seg_copy["segment_eval"] =
   result.get("extracted_output")` and its consumers reading
   `.get("label")` directly on that value.
3. **`make_doc_classification_extractor` (whole-text classification):**
   same treatment as item 2 — a `DOC_CLASSIFICATION_TOOL_SCHEMA` with the
   classification's own fields at the top level (`integrity`,
   `integrity_evidence`, `completeness`, `completeness_evidence`, `type`,
   `type_evidence`, `series`, `series_title`, `series_evidence`,
   `genre_primary`, `genre_secondary`, `genre_evidence`, `confidence`
   (nested)), no wrapper key. This extractor has no production caller
   today (only direct test usage), so risk here is minimal either way,
   but the same no-wrapper design keeps it consistent with item 2 and
   with a future caller's expectations.
4. **Update segmentation's two real consumers** for the now-wrapped
   `extracted_output`: `story_processors.py:142`
   (`segments = seg_extraction.get("extracted_output") or []` →
   `segments = (seg_extraction.get("extracted_output") or {}).get("segments") or []`)
   and `run_pilot.py`'s `_segment_story` (`:277`, same change). No other
   behavior in either function changes.
5. Add/update tests: `scene_analysis_test.py`'s
   `TestMakeSegmentExtractor`/`TestMakeSemanticsExtractor` gain a
   `tool_schema` assertion each; `story_analysis_test.py`'s
   `TestMakeDocClassificationExtractor` likewise. Add a real
   `extract()`-level test per extractor exercising a stubbed tool-call
   response through the full path (aligner/validator included for
   segmentation) to prove the wrapper-key design actually works, not
   just that the constructor stores the schema. Update
   `story_processors_test.py`'s existing segmentation-consuming tests'
   fixtures to return `{"segments": [...]}` instead of a bare list where
   they stub `seg_extractor.extract()`'s return value directly. Add or
   update a `run_pilot_test.py` case covering `_segment_story`'s adapted
   unwrap.
6. Re-run or smoke-test the same sampled story set from the live
   dogfooding run that saw the 65% `parsing_error` exclusion rate, and
   report the new rate for comparison — per the acceptance criteria.

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

- **REAL MEASUREMENT (2026-08-26, `WI-EVENT-0096`, PR pending):** ran
  `experiments/03_cross_segment_relation_pilot/check_segmentation_reliability.py`
  against the exact original 17-story baseline cohort (resolved from
  `experiments/03_cross_segment_relation_pilot/results/pilot_stories.jsonl`),
  `claude-haiku-4-5-20251001`, 17 real API calls, actual cost $0.59. Full
  data and write-up:
  `experiments/03_cross_segment_relation_pilot/results/segmentation_reliability/SUMMARY.md`.

  **The named `parsing_error` failure mode is structurally eliminated**:
  `parsing_error` dropped from 11/17 (65%) to **0/17 (0%)** by switching
  to the `tool_schema=` path, which removes the free-text JSON-parse step
  that mode used to fail at. Note this 0/17 is not itself measured
  evidence of improved reliability - `JSONPromptExtractor.extract()` sets
  `parsing_error = None` unconditionally on the `tool_schema` path
  (confirmed above, and by `check_segmentation_reliability.py`'s own
  documented caveat), so a 0/17 `parsing_error` count is guaranteed by the
  code path regardless of whether segmentation actually became more
  reliable (review finding, PR #398, confirmed real before fixing this
  paragraph's earlier, overclaiming wording). The only real, measured
  evidence is the any-cause exclusion-rate comparison below.

  **But the overall any-cause segmentation exclusion rate barely moved**
  (65% → 59%, 11/17 → 10/17), because a different, pre-existing failure
  mode was already present underneath and is now fully exposed:
  10/10 new exclusions are `alignment_error: "anchor text not found in
  story text"` — the exact near-miss-anchor category `WI-SEGMENT-0069`
  investigated and `WI-SEGMENT-0072` evaluated (fuzzy-matching) and
  declined to fix, due to false-positive risk. The model now
  successfully returns a full, well-formed segment list, but one
  segment's anchor text fails to align against the real story text, and
  the whole story is still excluded as a result.

  **One observed inclusion flip, not yet established as a regression**:
  `romance`'s `wintry_peacock_from_the_new_decameron_volume_iii__lawrence`
  was *included* in the original baseline and is *excluded* now
  (`alignment_error`). `make_segment_extractor` samples at
  `temperature=0.2`, and this compares one pre-fix call against one
  post-fix call with no repeated trials or same-version control - the
  flip could reflect ordinary model-output variance rather than a real
  effect of the code change (review finding, PR #398). Reported as an
  observed flip, not asserted as a regression, pending further evidence.
  Per-genre: science fiction unchanged (1/5→1/5), horror improved
  (1/5→2/5), western improved (0/2→1/2, no longer zero), romance's
  observed count dropped (4/5→3/5).

  **Per this item's own Risk Notes above, this measurement does not
  resolve `WI-EVENT-0033`.** The improvement (6 points) is smaller than
  the acceptance criterion's implicit expectation, and the honest
  conclusion is that this item's fix was necessary but not sufficient:
  segmentation reliability is now bottlenecked by the alignment-anchor
  issue, not the parsing issue this item targeted. `WI-EVENT-0033`
  remains `status: proposed`. Whether to reopen the near-miss-anchor
  fuzzy-matching question (`WI-SEGMENT-0072`, previously declined) given
  this new evidence that it is now the dominant real-world blocker is a
  live open question for whoever picks this up next — not decided by
  this measurement alone.

## Related Workstream and Designs

- Workstream: `project/workstreams/proposed/WS-EVENT-STRUCTURED-OUTPUT-RELIABILITY.md`
- Design/audit: `lcats/project/audits/2026-07-27-erw-pipeline-structured-output-reliability-audit.md`
- Design: `lcats/project/design/proposals/adopted/lcats-event-role-world-extractor/00_proposal.md`
