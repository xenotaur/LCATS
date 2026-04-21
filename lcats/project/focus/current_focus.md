---
id: FOCUS-REPAIR-REVIEW
title: Repair and review pipeline execution
status: active
priority: high
owner: unassigned
---

# Current Focus

## Active Priority
Build the repair and review pipeline.

## Focus Scope (Now)
1. Conservative repair engine.
2. Dry-run-first workflows.
3. Span-based transformations.
4. Human review and override system.

## Why This Is Current
- Survey/classification and immediate correctness fixes are complete.
- The next critical capability is safe correction with auditable human control.

## Non-Goals
- Narrative reasoning feature development in this phase.
- Persistence layer implementation beyond design decisions needed for current work.

## Exit Criteria
- Repair plans can be generated and previewed without mutation.
- Span operations support precise, explainable text changes.
- Review decisions can approve, reject, or override proposed repairs with rationale.
