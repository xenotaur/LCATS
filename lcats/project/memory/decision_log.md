# Decision Log

## 2026-04-21: WI-REPAIR-0001 conservative repair engine completed

### Summary
- Completed Phase 4A conservative repair engine work item with a deterministic,
  dry-run-first proposal workflow.

### Decisions
- Keep repair planning in the new `lcats.analysis.corpus` tree.
- Preserve conservative scope: only `likely_repairable` findings with explicit,
  known repair rules produce proposals.
- Add machine-parseable dry-run output (`jsonl`) alongside human-readable TSV
  output for audit/review tooling.
- Keep mutation non-default. No CLI apply path was introduced in this item.

### Status
- Accepted

---

## 2026-04-20: Bootstrap decision

### Summary
- Initialized an LRH `project/` scaffold for LCATS as a new bootstrap.

### Decisions
- Treated repository classification as `new` because no `project/` directory existed.
- Created full standard LRH bootstrap artifact set with conservative content.
- Marked ownership fields as `unassigned` where maintainer mapping was not explicitly documented.
- Preserved uncertainty around exact RAG/CBR architecture commitments.

### Rationale
- Request required complete bootstrap artifacts when classification is `new`.
- Repository docs provided enough evidence for a grounded baseline but not enough for binding architecture milestones.

### Uncertainty / Follow-ups
- Confirm maintainer ownership and review cadence.
- Confirm near-term RAG/CBR milestones and acceptance tests.

### Status
- Accepted (Bootstrap Phase)

---

## 2026-04-21: Completed item retirement and roadmap realignment

### Summary
- Removed completed tasks from active work item tracking and realigned project artifacts to current execution reality.

### Completed Items Retired from `project/work_items/`

#### 1) CLI help restructuring
- **What was done**: CLI help output and structure were improved to better guide command usage.
- **Why it is retired**: work is complete and no longer represents current execution risk.
- **Constraint / lesson**: CLI UX updates should stay aligned with dry-run-first safety semantics.

#### 2) Survey output improvements
- **What was done**: survey output became clearer and more actionable for corpus diagnosis.
- **Why it is retired**: survey diagnostics are established and now feed downstream repair planning.
- **Constraint / lesson**: output formats should remain stable enough for review tooling and audit artifacts.

#### 3) Unicode classification system
- **What was done**: classification logic for Unicode/encoding condition detection was implemented.
- **Why it is retired**: classification capability exists and serves as upstream input for repair.
- **Constraint / lesson**: classification remains diagnostic; mutation decisions must occur downstream.

#### 4) Mojibake precedence fix
- **What was done**: precedence behavior was corrected so mojibake cases are interpreted conservatively.
- **Why it is retired**: correctness fix is complete and now treated as baseline behavior.
- **Constraint / lesson**: precedence bugs directly affect trust; conservative classification wins over optimistic interpretation.

#### 5) Corpus README design doc
- **What was done**: corpus README design work was completed to improve data-facing documentation clarity.
- **Why it is retired**: documentation objective is complete for the current planning horizon.
- **Constraint / lesson**: corpus documentation should evolve with pipeline semantics and review practices.

### Decisions
- Active work now centers on repair engine, span operations, and review/override.
- Persistence is tracked as planned design work, not current implementation.
- Narrative structure/reasoning remains explicitly future-facing.

### Status
- Accepted
