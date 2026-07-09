---
id: WI-PERSIST-0004
title: Design persistence layer for corpus state and operation history
type: investigation
status: proposed
priority: medium
owner: unassigned
linked_focus: FOCUS-WORLDCON-2026
blocked: false
blocked_reason: null
resolution: null
---

# Work Item: WI-PERSIST-0004

## Objective
Design (not implement) a persistence model for corpus state, repair plans, and review outcomes.

## Scope
- Define persistence entities and relationships.
- Specify retention of operation/review history for auditability.
- Define replay and state reconstruction requirements.

## Acceptance Criteria
- Persistence design document defines core entities and invariants.
- Design supports end-to-end audit trail from classification to reviewed action.
- Design can support future narrative-layer integrations without schema breakage.
