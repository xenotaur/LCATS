---
id: WS-EVENT-STRUCTURED-OUTPUT-RELIABILITY
kind: planning_node
title: Event-Role-World pipeline structured-output reliability
status: proposed
stage: designed
origin: design_review
summary: Fix the systemic structured-output reliability gaps in the Event-Role-World pipeline — missing strict-mode tool schemas, unguarded array-item type assumptions and unguarded array-container type assumptions, unconstrained extractors with no tool schema at all, and processor.py's model/error-handling gaps — across three work items. WI-EVENT-0032 and WI-EVENT-0033 originate from the 2026-07-27 ERW pipeline audit; WI-EVENT-0061 was added 2026-08-08 from a distinct but topically related incident (a real pilot run's container-type gap, not covered by that audit).
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap: []
related_design:
  - lcats/project/audits/2026-07-27-erw-pipeline-structured-output-reliability-audit.md
  - lcats/project/design/proposals/adopted/lcats-event-role-world-extractor/00_proposal.md
work_items:
  - WI-EVENT-0032
  - WI-EVENT-0033
  - WI-EVENT-0061
exit_criteria:
  - All seven Event-Role-World-adjacent tool schemas (the six event_role_world/ extractors plus corpus/assess.py's ASSESSMENT_TOOL) set strict:true and additionalProperties:false at every object level, at the source rather than via a caller-local runtime override
  - All twelve array-item sites across the six event_role_world/ extractors detect a malformed (non-dict) item, preserve the raw offending payload for diagnosis, and surface an explicit extraction error for the affected segment/story instead of silently skipping it
  - All twelve array-item sites across the six event_role_world/ extractors also detect a non-list container value (e.g. a string) before iterating it, surfacing one clear error instead of iterating it element-by-element (WI-EVENT-0061)
  - processor.py's process_segments() accepts a model override and process_segment()'s per-pass error handling preserves the structured api_error dict (category/can_retry/should_abort_batch) instead of discarding it into a plain string, via an explicitly scoped extraction_errors representation change in schema.py and its callers (see WI-EVENT-0032)
  - scene_analysis.py's make_segment_extractor and make_semantics_extractor, and story_analysis.py's make_doc_classification_extractor, use the tool= structured-output path instead of unconstrained json_object mode, with both real consumers of make_segment_extractor's bare-list output (story_processors.py:142 and run_pilot.py's _segment_story:277) updated to match the new extracted_output shape
  - All three work items resolved and lrh validate reports 0 errors
---

# Workstream: Event-Role-World pipeline structured-output reliability

## Purpose

This workstream coordinates the fix for every finding in the 2026-07-27 ERW
pipeline structured-output reliability audit
(`lcats/project/audits/2026-07-27-erw-pipeline-structured-output-reliability-audit.md`),
except Category E (cost visibility, checkpointing, local models), which the
audit's own "Next steps" section identifies as independent and schedulable
separately. Two real crashes during WI-EVENT-0030 dogfooding (a `ValueError`
on non-JSON segmentation output, fixed at the source in PR #167; an
`AttributeError` on a malformed tool-result array item in
`relation_extractor.build_relations`, worked around via a caller-local
runtime override in PR #168) turned out to be instances of systemic gaps
that WI-EVENT-0030's own `forbidden_actions: modify_event_role_world_extractor`
blocks it from fixing at the source. This workstream exists to give that
fix an unconstrained work item, split from a second, more novel design
problem (Category C) that needs its own scoping because of a real
call-site blast radius.

## Scope

- **WI-EVENT-0032** (Categories A, B, D): harden the six
  `event_role_world/` extractors' tool schemas to `strict: true`, add
  defensive array-item type checks with explicit extraction-error surfacing
  at all twelve identified sites, and fix `processor.py`'s hardcoded model
  and discarded structured error info. This item is deliberately
  unconstrained by `modify_event_role_world_extractor` — fixing at the
  source inside `event_role_world/` is the entire point.
- **WI-EVENT-0033** (Category C): add `tool_schema=` to the three
  extractors that currently use unconstrained `json_object` mode
  (`scene_analysis.py`'s `make_segment_extractor`/`make_semantics_extractor`,
  `story_analysis.py`'s `make_doc_classification_extractor`), explicitly
  handling the `extracted_output` shape change this implies for
  its two real consumers (`story_processors.py:142` and
  `run_pilot.py`'s `_segment_story:277`) that currently expect a bare
  list.
- Land both work items through the standard LRH execution lifecycle
  (`/lrh-implement` → `/lrh-review-response` → `/lrh-confirm-fixes` →
  `/lrh-closeout`).
- Category E (model-invocation logging/budgeting, restartable/checkpointed
  runs, local/cheaper models) is explicitly out of scope for this
  workstream — the audit's own "Next steps" section treats it as an
  independent, non-correctness concern schedulable on its own, separate
  from this workstream's reliability-bug focus.

## Prior Art Check

### Duplication search
- In-repo: No existing work item or workstream covers these findings.
  WI-EVENT-0030 identifies the same gaps but is explicitly blocked from
  fixing them by its own `forbidden_actions`. PR #166/#167/#168 already
  fixed the two crashes that triggered this audit, but only #167 fixed at
  the source (a shared parser bug outside `event_role_world/`) — #166 and
  #168 are caller-local workarounds in `run_pilot.py`, not source fixes,
  and are exactly what these two work items now supersede with real fixes.
- Sibling repos: None identified.
- External libraries: None identified.
- Recommendation: Proceed.

### Demand search
- Work items: WI-EVENT-0030's own audit note ("Not yet acted on") directly
  requests this scoping step, having deferred it pending the audit and the
  in-progress pilot run finishing.
- Proposals: None found beyond the governing Event-Role-World extractor
  proposal, which this workstream's fixes bring closer to that proposal's
  own stated reliability expectations (structured output via `tool=`, not
  `json_object` mode).
- Backlog: No matching entries.
- Recommendation: Proceed.

## Work Items

- **WI-EVENT-0032** — Harden Event-Role-World tool-schema reliability:
  strict-mode schemas, defensive array-item checks with explicit error
  surfacing, and `processor.py`'s model-override/structured-error gaps.
- **WI-EVENT-0033** — Add schema-hardened structured output to the three
  unconstrained scene/story analysis extractors, addressing the
  `story_processors.py` call-site blast radius.

## Exit Criteria

(see frontmatter `exit_criteria:` above)
