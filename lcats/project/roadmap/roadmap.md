---
id: ROADMAP-CORE
title: LCATS Corpus-to-Narrative Roadmap
status: active
---

# Roadmap

## Status Legend
- **Completed**: finished and recorded.
- **Active**: currently being executed.
- **Planned**: approved next steps, not yet active.
- **Future**: downstream direction after planned phases.

## Phase 1 — Corpus Ingestion (**Completed**)
- Build ingestion and corpus organization workflows.
- Establish baseline corpus handling paths and CLI entry points.

## Phase 2 — Survey + Classification (**Completed**)
- Deliver corpus survey workflow.
- Add classification outputs to identify Unicode/encoding/corpus quality states.

## Phase 3 — Correctness Foundations (**Completed**)
- Apply mojibake precedence fix in classification.
- Tighten correctness interpretation to reduce false-safe classifications.

## Phase 4 — Repair + Review Pipeline (**Active**)
Focus: move from diagnosis to conservative correction.

### Phase 4A: Repair Engine
- Build deterministic, conservative repair planner/executor.
- Require dry-run output before any apply path.

### Phase 4B: Span Operations
- Add span-based transformation primitives for precise edits.
- Ensure operations are composable and traceable.

### Phase 4C: Review Loop
- Add human review/override checkpoints.
- Record decision rationale for accepted/rejected changes.

## Phase 5 — Persistence / Corpus State (**Planned**)
- Define persistent corpus state and operation history model.
- Support replay/audit across runs and contributors.

## Phase 6 — Narrative Structure + Reasoning (**Future**)
- Introduce structured narrative representations.
- Add reasoning workflows integrating Propp, Greimas, CBR, and RAG techniques.

## Alignment Notes
- Completed phases are logged in `project/memory/decision_log.md`.
- Active work is constrained to Phase 4 work items.
