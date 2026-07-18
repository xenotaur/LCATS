---
id: WI-APPLY-0005
title: Apply approved repair operations safely and deterministically
type: deliverable
status: resolved
priority: high
owner: unassigned
linked_focus: FOCUS-WORLDCON-2026
blocked: false
blocked_reason: null
resolution: Acceptance criteria met by existing, tested lcats/analysis/corpus/application.py (24 passing tests across span_ops/review/application). Confirmed superseded, not unfinished, by the shipped gather-time rule/override/allowlist pipeline -- see decision log 2026-07-18 and EV-0003.
---

# Work Item: WI-APPLY-0005

## Objective
Implement a system to apply reviewed and approved span operations to corpus text safely and deterministically.

## Scope
- Accept only approved operations from the review system.
- Apply operations in deterministic order.
- Ensure no unintended mutations occur.
- Produce transformed text outputs separate from original corpus.
- Validate applied results match intended span operations.

## Acceptance Criteria
- Applying the same approved operations yields identical output.
- No unreviewed changes are ever applied.
- Output is reproducible and auditable.
- Original corpus remains unchanged unless explicitly replaced via higher-level workflow.
