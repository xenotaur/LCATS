---
execution_id: 2026_08_20_22_24_06_KNIGHT_NOVUM_ANALYSIS_SIDECAR
prompt_id: PROMPT(AD_HOC:KNIGHT_NOVUM_ANALYSIS_SIDECAR)[2026-08-20T22:20:12+00:00]
work_item: AD_HOC
status: in_progress
rerun_of:
pr: https://github.com/xenotaur/LCATS/pull/323
commit: a737ad44edba3003b9d829e3a05fedd53be6929f
created_at: 2026-08-20T22:24:06+00:00
agent: codex_app
instruction_source: project/design/proposals/proposed/knight-novum-analysis-sidecar/00_proposal.md
session_transcript: pending
---

# Summary

Capture the reviewed Knight Score, Suvin Novum Score, shared evidence
extraction, staged pilot, and story-bucket sidecar design as an LRH-governed
LCATS proposal and open it as a draft pull request for human review.

# Result

Created
`project/design/proposals/proposed/knight-novum-analysis-sidecar/00_proposal.md`
as `PROP-LCATS-KNIGHT-NOVUM-ANALYSIS-SIDECAR`. The proposal chooses shared
theory-neutral extraction with independent Knight and Suvin adjudication,
adaptive whole-story/paragraph-aligned processing, deterministic scoring, and
one append-oriented `science-fiction.json` sidecar. It defines core technical
work, a contrastive approximately 30-story feasibility pilot, the Worldcon
100–200-story pilot, and a separately gated later corpus integration plan.

The prior-art check found reusable ERW evidence/span handling, checkpointing,
bucket discovery, annotation/promotion, and genre-sidecar work, but no
duplicate Knight/Suvin analysis. Draft PR #323 contains only the proposal and
this execution record; it does not change runtime code, corpus data,
workstreams, or work items.

# Validation

- `lrh validate`: 0 errors; 157 warnings, all pre-existing elsewhere in the
  LCATS control plane.
- `scripts/test`: 1,762 tests passed; 2 skipped.
- Manual LRH structure check: required Summary, Background / Motivation,
  Prior Art Check, Design Decisions, Non-Goals, and Implementation Plan
  sections present.
- Cross-reference check: every repo-relative path named in `related_design`
  exists on the base checkout.
- Placeholder scan: no `TODO`, `TBD`, or `PLACEHOLDER` text in the proposal.
- `git diff --check`: clean for the proposal commit.
- Idempotence check: no matching proposal or execution-record slug on `main`
  or any pull-request head before creation.

# Follow-up

- Human review and possible adoption of PR #323.
- After adoption, create a governing multi-stage workstream; defer individual
  work items until the workstream partitions Phase 1, the 30-story pilot, the
  Worldcon pilot, and later corpus integration.
- Replace `session_transcript: pending` with the durable Codex task/thread
  pointer when it becomes available.
- Use `/lrh-review-response` and `/lrh-confirm-fixes` for review rounds, then
  `/lrh-closeout` after merge to mark this record `landed`.
