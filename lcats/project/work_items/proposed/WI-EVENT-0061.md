---
resolution: null
blocked_reason: null
blocked: false
id: WI-EVENT-0061
title: Guard build_*() array-field iteration against non-list values across the Event-Role-World extractors
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
  - lcats/project/design/backlog.md
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
  - investigate_strict_schema_violation_root_cause
acceptance:
  - "All 12 array-item iteration sites across the six event_role_world/ extractors (entity_extractor.py:149,156; event_extractor.py:196,219,240,251; relation_extractor.py:142; discourse_extractor.py:206,226,250; story_relation_extractor.py:216; hypothesis_extractor.py:154) check that the field is a list before iterating it -- a present-but-non-list value (e.g. a string) produces exactly one clear extraction error (f\"{field} is not an array (got {type(value).__name__})\") instead of iterating it element-by-element"
  - "experiments/03_cross_segment_relation_pilot/run_pilot.py's exclude_reason (built at line 1212 via '; '.join(extraction_errors), printed uncapped at line 1347) is length-capped when printed, truncating with a \"...N more errors\" suffix so one malformed field cannot flood the console"
  - "New unit tests cover at least one non-list-value scenario per extractor module (a string, and a non-list/non-string type such as an int or dict, for at least one site) proving a single clear error is produced, not N per-character errors"
  - "Existing per-item malformed-guard behavior (schema.describe_malformed_item(), WI-EVENT-0032) is unchanged for actual malformed list items -- this WI adds a container-level check, not a replacement for the item-level one"
  - "lrh validate reports 0 errors"
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
  - lcats/src/lcats/analysis/event_role_world/schema.py
  - experiments/03_cross_segment_relation_pilot/run_pilot.py
  - lcats/tests/analysis_tests/event_role_world_test.py
  - lcats/project/design/backlog.md
---

## Summary

Add a container-type check before every `build_*()` array-field iteration
site in the `event_role_world/` extractors, so a present-but-non-list
value (most concretely, a truthy string returned in place of an expected
array) produces one clear error instead of being iterated
character-by-character into hundreds of bogus per-item errors. Also cap
`run_pilot.py`'s uncapped console print of the joined error string, which
is what let one malformed field flood the terminal with 1300+ lines in
the incident that surfaced this.

## Problem / Context

**Prior art check:**
- *Duplication search:* No existing container-type guard exists anywhere
  in `event_role_world/` -- confirmed via `grep -rn "is not an array\|is
  not a list\|not isinstance.*list" lcats/src/lcats/analysis/event_role_world/*.py`
  (run from the repo root; zero matches). `schema.describe_malformed_item()` (added by
  `WI-EVENT-0032`) is a per-*item* guard only; nothing checks the
  container itself.
- *Demand search:* Requested by `lcats/project/design/backlog.md`'s
  "Malformed-item guards check each item's type but never the
  container's" entry (P1, surfaced 2026-08-04). No open WI or PR
  currently addresses it (confirmed 2026-08-08 -- checked all
  `project/work_items/`, all open PRs, and every active local worktree
  branch).

Root cause: every `build_*()` call site sharing the pattern `for i, raw
in enumerate(tool_result.get(FIELD) or [])` relies on `or []` to
substitute a default only when the value is falsy. A non-empty **string**
is truthy, so `enumerate("some long string")` iterates
character-by-character; each character fails `isinstance(raw, dict)` and
gets its own `describe_malformed_item()` call. The per-item guard
(`WI-EVENT-0032`) works exactly as designed -- the gap is that nothing
validates the container's type before treating it as iterable. Confirmed
today against the live line numbers (several have shifted since the
backlog entry was written): 12 sites total across 6 extractor files --
`entity_extractor.py:149,156`; `event_extractor.py:196,219,240,251`;
`relation_extractor.py:142`; `discourse_extractor.py:206,226,250` (3
sites, not the 1 the backlog entry named); `story_relation_extractor.py:216`;
`hypothesis_extractor.py:154`. This count matches
`WS-EVENT-STRUCTURED-OUTPUT-RELIABILITY`'s own exit criteria, which
independently documents "twelve array-item sites" for the item-level
guard work -- a reassuring cross-check that no site is being missed.

Compounding: `run_pilot.py:1212`'s `row["exclude_reason"] = "; ".join(extraction_errors)`
joins all resulting fragments into one string, and
`run_pilot.py:1347`'s `print(f"  excluded: {row['exclude_reason']}")`
prints it with no length cap.

Explicitly out of scope: the backlog entry's separate open question of
whether `strict: true` tool schemas should have prevented a non-array
value from reaching this code at all. That is a distinct investigation
(root cause of *why* a string arrives here), not a precondition for this
defensive fix (handling it *when* it does).

## Scope

- Add a container-type check immediately before each of the 12 iteration
  sites listed above.
- Cap `run_pilot.py`'s printed `exclude_reason` length.
- Add regression tests per extractor module.

## Non-Goals

- Does not investigate why a `strict: true`-constrained field would
  return a non-array value in the first place.
- Does not change `schema.describe_malformed_item()` or existing
  item-level malformed-guard behavior.
- Does not touch `processor.py`, tool-schema definitions, or any other
  file in the ERW pipeline outside the listed artifacts.

## Required Changes

1. In each of the 6 extractor files, before the listed `enumerate(...)`
   call(s), check `isinstance(value, list)`; if the field is present
   (truthy) but not a list, append one `describe`-style error (e.g.
   `f"{field} is not an array (got {type(value).__name__})"`) to the
   function's error-collection list and skip iterating it, rather than
   falling through to `enumerate()`.
2. In `run_pilot.py`, cap the printed `exclude_reason` string (truncate
   with a `"...N more errors"` suffix) at the print site (line 1347) --
   leave the stored/joined value in the row data itself uncapped, since
   that's persisted to `pilot_stories.jsonl` for later analysis, not just
   displayed.
3. Add unit tests per extractor module covering at least: a string
   value, and one other non-list type (e.g. an int or a bare dict) for
   at least one representative site each.
4. Update `backlog.md`'s entry to reflect real, current line numbers and
   mark it in-progress once this WI is created.

## Acceptance Criteria

- All 12 array-item iteration sites across the six `event_role_world/`
  extractors check that the field is a list before iterating it -- a
  present-but-non-list value produces exactly one clear extraction
  error instead of iterating it element-by-element.
- `run_pilot.py`'s printed `exclude_reason` is length-capped.
- New unit tests cover at least one non-list-value scenario per
  extractor module.
- Existing per-item malformed-guard behavior is unchanged for actual
  malformed list items.
- `lrh validate` reports 0 errors.

## Validation

- `pytest tests/analysis_tests/event_role_world_test.py -v`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`
