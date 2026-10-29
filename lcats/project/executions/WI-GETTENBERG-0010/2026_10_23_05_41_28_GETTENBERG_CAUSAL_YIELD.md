---
execution_id: 2026_10_23_05_41_28_GETTENBERG_CAUSAL_YIELD
prompt_id: PROMPT(WI-GETTENBERG-0010:GETTENBERG_CAUSAL_YIELD)[2026-10-23T05:40:59+00:00]
work_item: WI-GETTENBERG-0010
status: landed
rerun_of:
pr: https://github.com/xenotaur/LCATS/pull/530
commit: b4ec4c452ed178dd62472af9f1a46b44e70ce485
created_at: 2026-10-23T05:41:28+00:00
agent: codex_app
instruction_source: project/development/gettenberg-narrow-delivery.md
session_transcript: codex-app:01a13653-87a6-7743-b734-7440a42ee1be
---

# Summary

Coordinator for the explicitly approved fixed-production causal/yield run. Start
2026-10-23 05:40 UTC; target 07:40, hard stop 08:40. Continue draft PR #530, with no
main integration or automatic renewal. Commit field identifies the input candidate;
product `91f1b422` remains unchanged. Experiment source hashes bind the new runners.

# Result

All 67 differences and 13 refusals have per-input controlled causal observations.
The actual configured-order frozen-cohort batch publishes 41 then refuses 3699,
leaving 1,617 unattempted; repeating reuses 41 and stops again. Separate one-item
calls publish 1,646 unique outputs and refuse 13; empty-source-cache reuse preserves
all 1,646. These are decoded-source fixtures, not historical wire receipts or full
5,492-ID collection yield. The candidate manifest and experiment README present
finite contract decisions; delivery/editorial acceptance remains pending.

# Validation

Canonical 2,955 tests pass; 26 experiment tests pass; package and explicit experiment
lint pass. Independent reviewer reproduces all 80 causal rows and validates every
published body/owner/source/receipt join. Missing JSON/helper guard P2 repaired,
final full-yield replay 237.556s, no unresolved P0–P2. Experiment collision counting
failure and lint sandbox-cache failure are preserved with repairs. Evidence lives
in experiments/10_gettenberg_qualification/results/gettenberg-causal-yield-20261023.
Final publication/LRH/CI status is recorded in the development log and PR.

# Follow-up

Q5 is a measured batch fail-fast blocker. Human decision needed on narrow refusal
handling and body-contract dispositions; no automatic marker or parser changes.
Keep 23552 independent parser defect as regression anchor for later cleanup work.
Q1 evidence transfer, selection/wire boundaries, final acceptance map and human main
promotion remain. Native status stays in_progress until main delivery. No corpus,
package publication, cache acquisition or persistent-consent changes.
