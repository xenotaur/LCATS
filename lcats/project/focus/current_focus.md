---
id: FOCUS-WORLDCON-2026
title: WorldCon 2026 readiness — repair/review, story analysis foundations, and docs cleanup
status: active
priority: high
owner: unassigned
---

# Current Focus

## Active Priorities
LCATS is tracking three parallel active priorities on the way to WorldCon 2026:

1. **Repair and review pipeline** (roadmap Phase 4) — conservative repair engine, span operations,
   human review/override, and approved application.
2. **Story analysis pipeline foundations** — `lcats assess` and scene/story analysis modules, in
   support of the Medium-Term Goal in `goal/project_goal.md`.
3. **Documentation cleanup** (`WORKSTREAM-DOCS`) — bring `lcats/docs/` and the repo-root README up
   to date with everything already implemented, to speed up team collaboration.

## Focus Scope (Now)

### 1. Repair and review pipeline
1. Conservative repair engine.
2. Dry-run-first workflows.
3. Span-based transformations.
4. Human review and override system.
5. Deterministic application of approved repairs.

### 2. Story analysis pipeline foundations
- Continue exercising `lcats assess` across corpora.
- No new design or work items until the feature-extraction library is decided.

### 3. Documentation cleanup
- Execute `WORKSTREAM-DOCS` (Phase 2b/3/4 of the 2026-07-07 docs audit).

## Why This Is Current
- Survey/classification and immediate correctness fixes are complete; repair/review is the next
  critical capability for corpus trust.
- WorldCon 2026 submission needs a working story-analysis foundation and documentation solid
  enough for collaborators to build on.

## Non-Goals
- Full narrative reasoning engine implementation (`project_goal.md` Long-Term Goal) in this phase.
- Persistence layer implementation beyond design decisions needed for current work.
- Formal design/workstream for story-feature extraction before the feature library is decided.

## Exit Criteria

### Repair and review pipeline
- Repair plans can be generated and previewed without mutation.
- Span operations support precise, explainable text changes.
- Review decisions can approve, reject, or override proposed repairs with rationale.

### Documentation cleanup
- `WORKSTREAM-DOCS` exit criteria met (see workstream file).
