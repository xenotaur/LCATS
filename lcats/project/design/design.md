# Design

## Purpose
Define the LCATS corpus-quality pipeline design for the current execution horizon.

## Pipeline Model
`classification -> repair -> span_ops -> review`

### 1) Classification
- Input: surveyed corpus files with diagnostics.
- Output: normalized issue classes and repair candidates.
- Constraint: classification remains diagnostic; it does not mutate corpus content.

### 2) Repair
- Input: classification output and conservative rules.
- Output: proposed change set with dry-run preview.
- Constraint: default behavior is non-destructive.

### 3) Span Operations
- Input: repair intents.
- Output: precise text span edits and operation metadata.
- Constraint: operations must be reversible or re-computable from logged inputs.

### 4) Review
- Input: proposed edits and rationale.
- Output: approved/rejected/overridden actions with recorded decision basis.
- Constraint: human review gates apply-path mutation.

## Design Principles
- **Non-destructive by default**: no silent corpus mutation.
- **Auditability first**: each proposal and action has provenance.
- **Explainability**: each repair maps to a known issue class and rule path.
- **Separation of concerns**: diagnosis, proposal, edit mechanics, and approval stay distinct.

## State and Persistence Boundary
- Current active design emphasizes in-run audit records.
- Durable persistence model is tracked as planned work (Phase 5) and is intentionally separated from the active repair/review implementation.
- **Gather-time repairs are the exception (WI-NORMALIZE-0017, 2026-07-13).** Special-character repairs are applied during gathering as a replayable step, not stored as edits to `data/`/`corpora/` JSON: because `data/` regenerates from cache, the durable artifact is the rule table (plus per-story overrides), and provenance is recorded as applied rule ids in story `metadata`, keyed by rule rather than byte offset. Byte offsets remain an ephemeral per-run execution detail. See `project/memory/decision_log.md` (2026-07-13).
- **The offset-keyed span-op/review/apply model (WI-SPANOPS-0002/WI-REVIEW-0003/WI-APPLY-0005) is confirmed superseded for special characters, not unfinished.** `span_ops.py`/`review.py`/`application.py` remain as complete, tested infrastructure for a future need this workstream did not end up requiring — per-instance human review with audit trails and overrides — not as dead code awaiting completion. See `project/memory/decision_log.md` (2026-07-18) and `project/evidence/EV-0003.md`.
