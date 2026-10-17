---
execution_id: 2026_10_17_20_20_08_GETTENBERG_MIGRATION
prompt_id: PROMPT(WI-GETTENBERG-0008:GETTENBERG_MIGRATION)[2026-10-17T20:19:44+00:00]
work_item: WI-GETTENBERG-0008
status: in_progress
rerun_of:
pr: https://github.com/xenotaur/LCATS/pull/522
commit: 3ed49415b900fa8bec825acf453272105860c6c0
created_at: 2026-10-17T20:20:08+00:00
agent: codex_app
instruction_source: project/work_items/proposed/WI-GETTENBERG-0008.md
session_transcript: codex-app:01a13653-87a6-7743-b734-7440a42ee1be
---

# Summary

Implement inventory-driven caller migration and removal of gutenbergpy under
WI0008 and the explicitly approved two-hour target/three-hour hard run grant.
Base003c2e085; branch codex/gettenberg-migration; internal integration only.

# Result

Active consumers use typed catalog/resources/cleanup and explicit source lifetime.
Legacy wrappers/pins removed; research clients migrated or archived with tested
reusable logic. See project/development/gettenberg-migration.md for every baseline
disposition, retired-test contract mapping, comparison scope and packaging evidence.
Experiment child record links through rerun_of; independent review is required
before internal acceptance. No CI changes or historical/canonical output rewriting.
Demand match WI-RELEASE-0037 is linked as a consumer of wheel evidence, not resolved.

# Validation

Python3.11.9, Black25.11.0, Ruff0.15.0. Canonical scripts/test2908 passed76.833s;
format281 files, lint, explicit research-path lint/format, notebook/client smoke
and five authored before/after comparison cases pass. LRH0errors/351existing
warnings. Final wheel/source hashes, review and CI receipts are captured under
project/development/evidence/gettenberg-migration-20261017/ before acceptance.

# Follow-up

WI0009 owns CI cache-maintenance replacement; WI0010 owns broader qualification.
Main promotion, release blocker closeout and terminal native lifecycle changes
remain human-gated. No live Gutenberg download was performed by this run.
