---
id: WI-REPAIR-0001
title: Implement conservative repair engine
status: active
priority: high
owner: unassigned
linked_focus: FOCUS-REPAIR-REVIEW
---

# Work Item: WI-REPAIR-0001

## Objective
Implement a deterministic repair engine that converts classification findings into conservative repair proposals.

## Scope
- Define repair rule mapping from issue class to proposed action.
- Generate dry-run plan output (no mutation path).
- Expose rationale metadata per proposed change.

## Acceptance Criteria
- Repair plan is deterministic for identical input.
- Dry-run output is human-readable and machine-parseable.
- No corpus content is mutated unless explicitly approved through review flow.
