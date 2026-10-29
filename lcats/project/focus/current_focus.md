---
id: FOCUS-WORLDCON-2026
title: WorldCon 2026 readiness — repair/review and story analysis foundations
status: active
priority: high
owner: unassigned
---

# Current Focus

## Active Priorities
LCATS is tracking two parallel active priorities on the way to WorldCon 2026:

1. **Repair and review pipeline** (roadmap Phase 4) — conservative repair engine, span operations,
   human review/override, and approved application.
2. **Story analysis pipeline foundations** — `lcats assess` and scene/story analysis modules, in
   support of the Medium-Term Goal in `goal/project_goal.md`.

A third priority, **documentation cleanup** (`WS-DOCS`), was active from 2026-07-08 through
2026-07-20 and is now fully resolved — see `project/workstreams/resolved/WS-DOCS.md` and
`project/memory/decision_log.md`.

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

## Why This Is Current
- Survey/classification and immediate correctness fixes are complete; repair/review is the next
  critical capability for corpus trust.
- WorldCon 2026 submission needs a working story-analysis foundation.

## Non-Goals
- Full narrative reasoning engine implementation (`project_goal.md` Long-Term Goal) in this phase.
- Persistence layer implementation beyond design decisions needed for current work.
- Formal design/workstream for story-feature extraction before the feature library is decided.

## Exit Criteria

### Repair and review pipeline
- Repair plans can be generated and previewed without mutation.
- Span operations support precise, explainable text changes.
- Review decisions can approve, reject, or override proposed repairs with rationale.

## Bounded Gettenberg Execution Pilot

The approved internal redesign is tracked by
[WS-GETTENBERG](../workstreams/resolved/WS-GETTENBERG.md) and
[execution charter](../development/gettenberg-pilot-charter.md).
The human started the first bounded run on 2026-10-14; WI-GETTENBERG-0001
establishes baseline evidence and scoped downstream work. See the
[development log](../development/gettenberg-development-log.md) for checkpoints.
This addition preserves the priorities above; staged work is not main delivery.

### Offline milestone delivered

PR [#508](https://github.com/xenotaur/LCATS/pull/508) delivered WI-GETTENBERG-0001 through WI-GETTENBERG-0004
to main (35f80fb5). Those four WIs are resolved; WI-0005 through WI-0010,
the workstream and dependency-removal/release gates remain open. See the
[runlog](../development/gettenberg-development-log.md) for evidence and repairs.

## Main delivery and formal closeout — 2026-10-27

PR [#534](https://github.com/xenotaur/LCATS/pull/534) delivered the replacement to
main at `b4ec4c452ed178dd62472af9f1a46b44e70ce485`. The human approved the
closeout plan, exact resolution notes, all four workstream exit criteria and the
archive-sync exception. WI-GETTENBERG-0001–0010 are resolved, WS-GETTENBERG is
closed, and the redesign proposal is adopted/implemented. Earlier milestone
paragraphs retain their historical meaning; this dated entry records
the current disposition. See the [formal closeout](../development/gettenberg-closeout.md) for evidence and inventory.

The post-adoption backlog GPA-A–E, PR #524's separated editorial work, Kenny's
independent gatherer work, WI-RELEASE-0037/0039 and WS-RELEASE remain open.
Replacement delivery does not approve package publication, corpus promotion,
universal editorial correctness or full live-source coverage.
