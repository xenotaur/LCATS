---
execution_id: 2026_07_27_19_45_15_ERW_RELIABILITY_SCOPING
prompt_id: PROMPT(AD_HOC:ERW_RELIABILITY_SCOPING)[2026-07-27T19:27:06-04:00]
work_item: AD_HOC
status: in_progress
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/172
commit: 2ac5a5e3
agent: claude_app
instruction_source: user request, per the audit's own "Next steps" recommendation in lcats/project/audits/2026-07-27-erw-pipeline-structured-output-reliability-audit.md
session_transcript: pending
created_at: 2026-07-27T19:45:15-04:00
---

# Summary

Create the actual work item(s)/workstream the 2026-07-27 ERW pipeline
structured-output reliability audit recommends as its own next step:
Categories A/B/D (blocked by WI-EVENT-0030's `forbidden_actions:
modify_event_role_world_extractor`, need an unconstrained work item) and
Category C (the three unconstrained extractors, a separate, more novel
design problem). Category E is explicitly out of scope, per the audit's
own note that it's independent and schedulable separately.

# Result

Authored three new control-plane planning artifacts (no source code
changed):

- `project/workstreams/proposed/WS-EVENT-STRUCTURED-OUTPUT-RELIABILITY.md`
  — coordinates the two work items below; scope explicitly excludes
  Category E.
- `project/work_items/proposed/WI-EVENT-0032.md` — Categories A/B/D:
  strict-mode tool schemas across all seven ERW-adjacent schemas
  (previously only five were patched at runtime by PR #168, and only for
  `--backend anthropic`), defensive array-item checks with explicit
  extraction-error surfacing at all eleven identified sites (a guard that
  merely skips a malformed item is explicitly called out as insufficient,
  per the audit's own review correction), and `processor.py`'s
  model-override parameter plus preserving the structured `api_error` dict
  instead of discarding it into a plain string. Deliberately unconstrained
  by `forbidden_actions: modify_event_role_world_extractor` — this is the
  entire reason this item exists as a separate item from WI-EVENT-0030.
  Also scopes removal of `run_pilot.py`'s now-redundant runtime
  strict-schema override once the schemas are strict at the source.
- `project/work_items/proposed/WI-EVENT-0033.md` — Category C: adds
  `tool_schema=` to `scene_analysis.py`'s `make_segment_extractor`/
  `make_semantics_extractor` and `story_analysis.py`'s
  `make_doc_classification_extractor`. Scoped explicitly to address the
  `story_processors.py` blast radius the audit flagged — `tool_schema`
  mode changes `extracted_output`'s shape from a bare list to a
  single-key dict, which would silently break `story_processors.py`'s two
  existing call sites if not designed around. Acceptance criteria include
  measuring the fix's real effect against the live 65% segmentation
  exclusion rate seen during WI-EVENT-0030 dogfooding.

Both work items' `depends_on`/`related_workstreams`/`related_design` link
back to the workstream and the audit doc; neither touches WI-EVENT-0030's
own frontmatter, since neither is a dependency of it.

# Validation

- `lrh validate` (from `lcats/`) — 0 errors, 47 warnings (up from the
  pre-existing 43; the 4 new ones are `OWNER_ROLE_INSUFFICIENT`/
  `OWNER_NOT_IN_CONTRIBUTORS` on the two new work items, matching the
  repo's existing `owner: unassigned` convention used throughout, e.g.
  WI-EVENT-0030 itself).
- Manual review of both new work items' frontmatter against
  `lrh-work-item`'s schema reference (required/policy-required fields,
  type vocabulary, status→directory bucket mapping) and against
  WI-EVENT-0030's own file as a structural precedent.
- Manual review of the new workstream against `WS-PACKAGING.md`'s
  proposed-state structure as a precedent.

# Follow-up

- Neither WI-EVENT-0032 nor WI-EVENT-0033 has been implemented yet — this
  PR is scoping only. Each should be picked up as its own
  `/lrh-implement` run once prioritized.
- Category E (cost/logging/checkpointing/local models) still needs a
  scoping decision of its own — the audit's "Next steps" section leaves
  open whether it becomes its own workstream/work item or folds into an
  existing one; this PR deliberately did not decide that question.
- WI-EVENT-0030's real pilot run still needs a successful attempt with
  PR #170's max_tokens truncation fix in place — independent of this
  scoping PR, still the next concrete step for that item.
