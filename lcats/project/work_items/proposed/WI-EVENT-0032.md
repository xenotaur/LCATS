---
resolution: null
blocked_reason: null
blocked: false
id: WI-EVENT-0032
title: Harden Event-Role-World tool-schema reliability and processor error/model handling
type: deliverable
status: proposed
priority: high
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
depends_on:
  - WI-EVENT-0029
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
  - All seven tool schemas (entity_extractor.py's ENTITY_TOOL_SCHEMA, event_extractor.py's EVENT_TOOL_SCHEMA, relation_extractor.py's RELATION_TOOL_SCHEMA, discourse_extractor.py's DISCOURSE_TOOL_SCHEMA, story_relation_extractor.py's STORY_RELATION_TOOL_SCHEMA, hypothesis_extractor.py's HYPOTHESIS_TOOL_SCHEMA, and corpus/assess.py's ASSESSMENT_TOOL) set strict:true and additionalProperties:false on every object level, at the source, superseding run_pilot.py's PR #168 runtime override for the five it currently patches
  - All twelve identified array-item sites across the six event_role_world/ extractors (entity_extractor.py:142,144; event_extractor.py:185,203,219,225; relation_extractor.py:131; discourse_extractor.py:196,213,232; story_relation_extractor.py:205; hypothesis_extractor.py:146) detect a non-dict item, preserve the raw offending item for diagnosis (e.g. logged or attached to the extraction error), and surface an explicit extraction error for the affected segment/story rather than silently skipping the malformed item and treating the rest as a clean success
  - processor.py's process_segments() (plural) accepts a model parameter that overrides each extractor's factory-hardcoded default, matching the override run_pilot.py's _build_erw_extractors() already applies by building extractors itself
  - processor.py's per-pass error handling preserves the structured api_error dict (category/can_retry/should_abort_batch) from llm_extractor.py's _classify_api_error instead of discarding it into a plain f-string, via a schema change scoped explicitly by this item (see Scope) since SegmentWorldAnnotation/StoryWorldAnnotation's extraction_errors field is currently List[str] (schema.py:426,767) and cannot hold a dict as-is; run_pilot.py:673's "; ".join(extraction_errors) caller is updated to match whatever new representation is chosen, so callers no longer need to re-derive fatality via substring matching (as run_pilot.py's FatalPilotError/_check_fatal do today)
  - run_pilot.py's _strict_tool_schema()/_close_schema_objects() runtime override and its --backend anthropic gate are removed once schemas are strict at the source, since they become redundant
  - run_pilot.py's main() per-story loop catches any exception around run_story() (not just FatalPilotError), so an unexpected per-story failure still preserves and writes already-completed pilot_stories.jsonl/pilot_usage.jsonl/pilot_summary.json results instead of discarding the entire run's data, per the audit's Category B update finding
  - Existing ERW pipeline tests pass, and new tests cover both the strict-schema fix and at least one malformed-array-item scenario per extractor module
  - lrh validate reports 0 errors
required_evidence:
  - manual_review
  - lrh_validate
  - test_output
artifacts_expected:
  - lcats/src/lcats/analysis/event_role_world/entity_extractor.py
  - lcats/src/lcats/analysis/event_role_world/event_extractor.py
  - lcats/src/lcats/analysis/event_role_world/relation_extractor.py
  - lcats/src/lcats/analysis/event_role_world/discourse_extractor.py
  - lcats/src/lcats/analysis/event_role_world/story_relation_extractor.py
  - lcats/src/lcats/analysis/event_role_world/hypothesis_extractor.py
  - lcats/src/lcats/analysis/event_role_world/processor.py
  - lcats/src/lcats/analysis/event_role_world/schema.py
  - lcats/src/lcats/analysis/corpus/assess.py
  - experiments/03_cross_segment_relation_pilot/run_pilot.py
---

## Summary

Fix, at the source, the three related reliability gaps the 2026-07-27 ERW
pipeline audit found inside `lcats/src/lcats/analysis/event_role_world/` and its
`processor.py`: none of the module's tool schemas set Anthropic's
`strict: true`/`additionalProperties: false`; all six extractors share an
identical unguarded-array-item pattern that has already caused two real
pilot crashes; and `processor.py` hardcodes `gpt-4o` with no override while
discarding structured API error information into a plain string.
WI-EVENT-0030 cannot fix any of this itself — its own
`forbidden_actions: modify_event_role_world_extractor` blocks edits inside
this exact directory, which is why PR #166 and PR #168 landed as
caller-local runtime overrides in `run_pilot.py` instead of source fixes.
This item is deliberately unconstrained by that restriction so the real fix
can land where the bug actually lives.

## Problem / Context

Two real crashes during WI-EVENT-0030 dogfooding — a `ValueError` on
non-JSON segmentation output (fixed at the source in PR #167, outside this
directory) and an `AttributeError` on a malformed tool-result array item in
`relation_extractor.build_relations` (worked around only via a runtime
strict-schema override in PR #168, since WI-EVENT-0030 cannot touch
`event_role_world/` directly) — turned out to be instances of systemic
gaps affecting every extractor in this module, documented in full in
`lcats/project/audits/2026-07-27-erw-pipeline-structured-output-reliability-audit.md`
(Categories A, B, and D). A third crash occurred at a *different*
Category B site (`entity_extractor.py:144`) even with PR #168's strict-mode
override confirmed genuinely active in the request that crashed, which the
audit treats as raising — not lowering — the priority of Category B's
defensive-check fix, since strict mode alone demonstrably did not prevent
it.

### Duplication search
- In-repo: No existing work item fixes these gaps at the source. PR #166
  and PR #168 are caller-local workarounds in `run_pilot.py`, gated to
  `--backend anthropic` only, and explicitly do not reach
  `hypothesis_extractor.py` (never built by that pilot) or
  `corpus/assess.py`'s `ASSESSMENT_TOOL` (built via a separate code path).
  This item supersedes both workarounds with real source fixes.
- Sibling repos: None identified.
- External libraries: None identified.
- Recommendation: Proceed.

### Demand search
- Work items: WI-EVENT-0030's audit note ("Not yet acted on... per user
  request to scope a properly unconstrained work item... instead of
  another caller-side workaround") directly requests this item.
- Proposals: None found beyond the governing Event-Role-World extractor
  proposal, whose Implementation prerequisites already name `tool=`
  structured output as the intended reliability mechanism this item
  completes.
- Backlog: No matching entries.
- Recommendation: Proceed.

## Scope

- Harden all seven ERW-adjacent tool schemas to Anthropic's `strict` mode
  at the source (Category A).
- Add defensive array-item checks with explicit extraction-error surfacing
  at every identified malformed-tool-result site across the six
  `event_role_world/` extractors (Category B).
- Fix `processor.py`'s hardcoded model and its discarding of structured
  API error information (Category D).
- Fix the audit's Category B update finding: `run_pilot.py`'s uncaught
  per-story exception handling discards an entire run's already-paid-for
  results.
- Add test coverage for every change above.

## Required Changes

1. **Category A (strict-mode schemas):** add `strict: true` and
   `additionalProperties: false` (at every object level, including nested
   array-item objects) to all seven schemas: `entity_extractor.py`'s
   `ENTITY_TOOL_SCHEMA`, `event_extractor.py`'s `EVENT_TOOL_SCHEMA`,
   `relation_extractor.py`'s `RELATION_TOOL_SCHEMA`,
   `discourse_extractor.py`'s `DISCOURSE_TOOL_SCHEMA`,
   `story_relation_extractor.py`'s `STORY_RELATION_TOOL_SCHEMA`,
   `hypothesis_extractor.py`'s `HYPOTHESIS_TOOL_SCHEMA`, and
   `corpus/assess.py`'s `ASSESSMENT_TOOL`.
2. Once those seven schemas are strict at the source, remove
   `run_pilot.py`'s `_strict_tool_schema()`/`_close_schema_objects()`
   runtime override and its `--backend anthropic` gate — it becomes dead
   code once the schemas it patches are already strict.
3. **Category B (defensive array-item checks):** at each of the twelve
   identified sites (`entity_extractor.py:142,144`;
   `event_extractor.py:185,203,219,225`; `relation_extractor.py:131`;
   `discourse_extractor.py:196,213,232`; `story_relation_extractor.py:205`;
   `hypothesis_extractor.py:146`), detect a non-dict array item, preserve
   the raw offending item (e.g. write it to a diagnosis log or attach it
   to the returned extraction error) rather than discarding it silently,
   and surface an explicit extraction error for the affected
   segment/story. A guard that merely skips the malformed item and
   continues is **not** sufficient — per the audit's own review
   correction, that would make a segment with a dropped entity/event/
   relation look like a *successful* partial extraction instead of a
   failed one, biasing density figures exactly the way WI-EVENT-0030's
   acceptance criteria warn against.
4. **Category D (`processor.py` model override):** add a `model`
   parameter to `process_segments()` that overrides each extractor's
   factory-hardcoded default, matching the override `run_pilot.py`
   already applies by building extractors itself and calling
   `process_segment()` directly.
5. **Category D (`processor.py` structured error preservation):** change
   each pass's error handling to preserve the structured `api_error` dict
   instead of stringifying it, so a caller can read
   `category`/`can_retry`/`should_abort_batch` directly instead of
   re-deriving fatality via substring matching. This requires a schema
   change: `SegmentWorldAnnotation`/`StoryWorldAnnotation`'s
   `extraction_errors` field is currently `List[str]`
   (`schema.py:426,767`) and cannot hold a structured dict as-is. Decide
   and implement one of: (a) widen `extraction_errors`' element type to
   accept either a string or a structured-error dict, or (b) add a
   separate, additive field (e.g. `structured_extraction_errors`)
   alongside the existing string list, left untouched for backward
   compatibility. Whichever is chosen, update `run_pilot.py:673`'s
   `"; ".join(extraction_errors)` call (which assumes a list of strings)
   to match the new representation, and confirm no other caller of
   `extraction_errors` breaks.
6. **Uncaught-exception data loss (audit's Category B update):**
   `run_pilot.py`'s `main()` per-story loop only catches `FatalPilotError`
   around `run_story()` — any other exception propagates uncaught, and
   the code that writes `pilot_stories.jsonl`/`pilot_usage.jsonl`/
   `pilot_summary.json` never runs, discarding every already-completed,
   already-paid-for story in the run, not just the one that failed. Wrap
   the per-story loop to catch any exception, log/record it the same way
   a non-fatal per-story failure is handled today, and still write out
   whatever results completed before the failure.
7. Add test coverage for both the strict-schema change and at least one
   malformed-array-item scenario per extractor module (six extractors,
   one scenario each at minimum), plus a `process_segments(model=...)`
   override test, a structured-error-preserved test for `processor.py`,
   and a test confirming an unexpected per-story exception still yields
   written partial results.

## Non-Goals

- Does not implement Category C (the three extractors with no tool schema
  at all) — that is WI-EVENT-0033, a separate and more novel design
  problem given `story_processors.py`'s call-site blast radius.
- Does not implement Category E (cost/logging/checkpointing/local models)
  — independent of this item's reliability-bug scope per the audit's own
  "Next steps" section.
- Does not change the Event-Role-World pipeline's architecture or stage
  ordering — no new passes. The one explicitly scoped exception to "no
  new/changed schema fields" is `extraction_errors`' representation (see
  Category D above), needed to preserve structured `api_error` data; no
  other schema field changes are in scope.
- Does not attempt to further diagnose the unresolved "why did strict mode
  not prevent the third crash" question the audit raises — this item
  implements the defensive fix the audit concludes is needed regardless of
  that question's answer, not a root-cause investigation into Anthropic's
  grammar-constrained sampling behavior.

## Acceptance Criteria

(see frontmatter `acceptance:` above)

## Validation

- lrh validate
- scripts/test (full suite, including new tests for all six extractors and
  processor.py)
- scripts/lint
- Manual review confirming run_pilot.py's now-redundant strict-schema
  override was removed cleanly with no regression to --backend openai
  behavior

## Risk Notes

- Touching all six `event_role_world/` extractor modules plus
  `processor.py` in one item is a wide diff — consider splitting into
  smaller PRs per extractor if review load becomes unwieldy, as long as
  each PR keeps its own extractor's schema-strictness and defensive-check
  changes together (splitting Category A from Category B for the same
  extractor risks a half-fixed intermediate state).
- Removing `run_pilot.py`'s runtime strict-schema override must happen only
  after the source schemas are confirmed strict — removing it first would
  reopen the exact crash class this item exists to fix, with no override
  left to catch it.
- The audit's own postmortem could not fully resolve why the third crash
  occurred despite strict mode being confirmed active — this item's
  Category B fix is the correct response regardless, but if malformed
  array items keep recurring even after this item lands, that is evidence
  the underlying cause is not fully understood yet and may need its own
  follow-up investigation, not evidence this item's fix was wrong.

## Related Workstream and Designs

- Workstream: `project/workstreams/proposed/WS-EVENT-STRUCTURED-OUTPUT-RELIABILITY.md`
- Design/audit: `lcats/project/audits/2026-07-27-erw-pipeline-structured-output-reliability-audit.md`
- Design: `lcats/project/design/proposals/adopted/lcats-event-role-world-extractor/00_proposal.md`
