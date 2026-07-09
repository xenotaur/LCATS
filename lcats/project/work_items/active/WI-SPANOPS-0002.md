---
id: WI-SPANOPS-0002
title: Build span operation system for precise text edits
type: deliverable
status: active
priority: high
owner: unassigned
linked_focus: FOCUS-WORLDCON-2026
blocked: false
blocked_reason: null
resolution: null
---

# Work Item: WI-SPANOPS-0002

## Objective
Create span-based transformation primitives used by the repair engine.

## Scope
- Define span operation schema (start/end, replacement, reason).
- Support composition of multiple operations per file.
- Ensure operation ordering and conflict handling are explicit.
- Support deterministic application of non-overlapping operations to text.
- Define behavior for overlapping/conflicting operations.

## Acceptance Criteria
- Span operations can represent planned repairs without ambiguity.
- Operation application order is deterministic.
- Operation metadata supports review traceability.
