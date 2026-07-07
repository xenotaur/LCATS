---
id: WI-REPAIR-0001
title: Implement conservative repair engine
type: deliverable
status: resolved
resolution: "Implemented conservative repair proposal generation in lcats.analysis.corpus.repairs with deterministic dry-run plan models and TSV/JSONL reporting helpers; non-destructive-by-default behavior preserved."
priority: high
owner: unassigned
linked_focus: FOCUS-REPAIR-REVIEW
blocked: false
blocked_reason: null
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

## Completion Notes
- Implemented conservative repair proposal generation in
  `lcats.analysis.corpus.repairs` with explicit rule mapping from
  `likely_repairable` classification evidence fragments to high-confidence
  replacements.
- Added deterministic dry-run plan models and reporting helpers for both human
  TSV inspection and machine-parseable JSONL output.
- Preserved non-destructive-by-default behavior. Repair application helpers
  remain library-level utilities and are not used by default CLI dry-run paths.
