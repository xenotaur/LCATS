# Decision Log

## 2026-07-18: Span-op/review/apply infrastructure resolved as superseded, not unfinished

### Summary
- WI-SPANOPS-0002 (span operation model), WI-REVIEW-0003 (human review and
  override model), and WI-APPLY-0005 (safe application of approved
  operations) are resolved. Their acceptance criteria are fully met by
  existing, tested code (`lcats/lcats/analysis/corpus/span_ops.py`,
  `review.py`, `application.py`, 24 passing tests) — the resolution is not "we decided
  not to do this," it's "this was already built, and the shipped pipeline
  took a different, simpler path instead."

### Decisions
- **The offset-keyed span-op/review/apply system is confirmed superseded,
  not dead code awaiting completion.** The 2026-07-13 decision (this log)
  already established that gather-time, rule-keyed replayable repairs are
  the durable mechanism; this entry closes the loop with real evidence
  (EV-0003) that the simpler mechanism actually works end-to-end on a
  literal, non-simulated regeneration — not just in the abstract or in
  simulation (EV-0002).
- **Do not delete `span_ops.py`/`review.py`/`application.py`.** They
  remain a complete, tested, well-designed model for a *future* need this
  pipeline does not currently have: per-instance human review of
  individual proposed edits with audit trails, overrides, and
  non-destructive application. If a future defect class can't be
  disposed of by rule/override/allowlist alone (this workstream's three
  disposition categories), this is where that work resumes — it is not
  wasted effort, it's unused-until-needed infrastructure.
- **The "bucket" idea (richer per-story metadata, keyed at the story ID
  level) raised earlier in this workstream's design discussion remains
  unimplemented and is not addressed by this decision.** It's a separate,
  still-open architectural question or a follow-up.

### Evidence
- EV-0003: literal, non-simulated `lcats gather` + `lcats survey` +
  `lcats promote --dry-run` run, all clean, both independent survey gates
  agreeing. See `project/evidence/EV-0003.md`.

### Status
- Accepted

## 2026-07-13: Repairs are gather-time replayable inputs, keyed by rule not offset

### Summary
- Implemented WI-NORMALIZE-0017: a deterministic normalization step in the
  gather pipeline (`lcats/lcats/gatherers/normalization.py`) that applies the
  measured repair rules to each extracted story body before its first JSON
  write, stamping applied rule ids into `metadata["normalization"]`.

### Decisions
- **Repairs live in the pipeline, not in stored files.** Because `data/` is
  cleared and regenerated after major changes (and users regenerate with their
  own customizations), a durable fix must be a replayable input to
  regeneration. Applying rules at gather time reproduces the fix on every run;
  editing stored JSON would be wiped by the next regeneration.
- **The reviewable/durable unit is the rule id, not a byte offset.** Offsets
  are recomputed each run by the shared suggestion path and are an ephemeral
  execution detail; provenance is recorded as applied rule ids + counts.
- **Reuse the dry-run code path.** Normalization calls
  `repairs.suggest_repairs_for_text` + `apply_repair_suggestions`, so what
  `lcats repair-specials` reports is exactly what normalization applies.
- **Non-destructive and idempotent.** Clean bodies pass through byte-identical
  with no metadata change; re-normalizing an already-clean body is a no-op.
- This supersedes the 2026-06-18 decision to keep application workflows out of
  scope, and amends the State and Persistence Boundary in
  `project/design/design.md`. Span-op review persistence (WI-REVIEW-0003) and
  per-story overrides (WI-OVERRIDES-0018) build on this replayable model.

### Status
- Accepted

## 2026-06-29: Adopt unified LLMBackend Protocol for model-comparison experiments

### Summary
- Designed and adopted a custom thin `LLMBackend` Protocol abstraction for all
  LLM API calls in LCATS. Motivated by the need for model-to-model comparison
  experiments for the WorldCon 2026 science fiction analysis paper.

### Decisions
- **Custom thin adapter (Option 3), not LiteLLM**: LiteLLM was evaluated and
  rejected because transparency over the exact wire format sent to each provider
  is a scientific requirement. LiteLLM performs request transformations that are
  not always transparent and adds a large transitive dependency.
- **`typing.Protocol`, not ABC**: structural subtyping avoids inheritance
  coupling; `FakeBackend` test double needs zero imports from production code.
- **One `complete()` method**: single method with `tool: dict | None` to signal
  mode. One mock per test; minimal Protocol surface.
- **Two-field `BackendResponse`**: `text: str` and `tool_result: dict | None`
  are explicit; no union type that requires runtime narrowing.
- **`KMo/` and notebooks excluded**: exploratory scripts are not in scope for
  migration; their results are not cited in the paper.
- **Streaming default for Anthropic**: `messages.stream` avoids gateway timeouts
  on 40–100K character story bodies; transparent to callers.

### Rationale
- Single injectable backend makes the model an experiment parameter, not a
  code change.
- Pinned model version strings in both backends satisfy reproducibility
  requirements (Bender et al., FAccT 2021; Hutchinson et al., NeurIPS 2021).
- `JSONPromptExtractor` already accepts `client: Any`; the migration is a
  parameter rename + one call site change.

### Status
- Proposed (work items WI-LLM-0007 through WI-LLM-0010 created)

---

## 2026-06-29: Add lcats assess command using Anthropic API

### Summary
- Added `lcats assess` subcommand (PR #98) that uses the Anthropic Claude API
  to assess corpus stories for quality and genre fit.

### Decisions
- Use Anthropic tool use (not `response_format`) to enforce structured output.
- Pre-flight QA runs on the full body before truncation.
- Four target genres confirmed: science fiction, horror, western, romance.
- Default model: `claude-opus-4-8`; configurable via `--model`.

### Status
- Landed (PR #98)

---

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

---

## 2026-06-18: Approved application layer completed

### Summary
- Implemented WI-APPLY-0005 with a deterministic, non-destructive application
  layer for reviewed span operations.

### Decisions
- Apply only `approved` decisions as proposed and `overridden` decisions via
  reviewer replacement operations.
- Treat `pending` and `rejected` decisions as ineligible and audit them as
  skipped.
- Validate operation sets, overlaps, span bounds, and source-text matches before
  returning any successful transformed output.
- Keep persistence, CLI application workflows, and in-place corpus rewriting out
  of scope for this work item.

### Status
- Accepted
