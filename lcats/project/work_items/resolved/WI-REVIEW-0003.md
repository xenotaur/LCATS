---
id: WI-REVIEW-0003
title: Implement human review and override model
type: deliverable
status: resolved
priority: high
owner: unassigned
linked_focus: FOCUS-WORLDCON-2026
blocked: false
blocked_reason: null
resolution: Acceptance criteria met by existing, tested lcats/analysis/corpus/review.py (24 passing tests across span_ops/review/application). Confirmed superseded, not unfinished, by the shipped gather-time rule/override/allowlist pipeline -- see decision log 2026-07-18 and EV-0003.
---

# Work Item: WI-REVIEW-0003

## Objective
Implement a review loop that allows humans to approve, reject, or override proposed repairs.

## Scope
- Define review decision states and required rationale.
- Connect repair proposals and span ops to reviewable units.
- Record reviewer decisions as auditable artifacts.
- Ensure only approved operations are eligible for application.
- Define interface between review outputs and application stage.

## Acceptance Criteria
- Every proposed change has an explicit review outcome.
- Override path captures reviewer rationale and final action.
- Approved actions are distinguishable from rejected and overridden actions.
