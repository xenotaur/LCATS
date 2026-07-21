---
id: WI-META-0006
title: Implement Meta CLI register slice for workspace project registry
type: deliverable
status: abandoned
priority: high
owner: unassigned
linked_focus: FOCUS-WORLDCON-2026
blocked: false
blocked_reason: null
resolution: Superseded by native LRH functionality (`lrh meta register`); the LCATS-side duplicate this item delivered is being removed by WI-META-0023.
---

# Work Item: WI-META-0006

## Objective
Implement the initial Meta CLI registration slice to register repositories in a workspace-local project registry.

## Scope
- Add `meta register <repo_locator>` CLI flow.
- Create stable project registry records under `projects/`.
- Detect setup state using local `project/` presence.
- Block duplicates unless explicitly forced.

## Acceptance Criteria
- Register command writes a TOML project record with project, identity, and registry sections.
- Project IDs are stable and unique per workspace registry.
- Duplicate registration is rejected unless `--force` is provided.
- Tests cover success path, duplicate handling, and setup-state detection.

## Notes
- This item intentionally excludes `meta list`, orchestration, and UI work.
