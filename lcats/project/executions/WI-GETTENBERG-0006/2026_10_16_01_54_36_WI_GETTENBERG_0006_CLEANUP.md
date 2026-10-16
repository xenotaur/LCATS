---
execution_id: 2026_10_16_01_54_36_WI_GETTENBERG_0006_CLEANUP
prompt_id: PROMPT(WI-GETTENBERG-0006:WI_GETTENBERG_0006_CLEANUP)[2026-10-16T01:54:06+00:00]
work_item: WI-GETTENBERG-0006
status: in_progress
rerun_of:
pr:
commit:
created_at: 2026-10-16T01:54:36+00:00
agent: codex_app
instruction_source: project/work_items/proposed/WI-GETTENBERG-0006.md
session_transcript: codex-app:01a13653-87a6-7743-b734-7440a42ee1be
---

# Summary

Deliver independently authored conservative plain-text Gutenberg cleanup with
original preservation, exact offsets, diagnostics, tests and Diataxis docs.

# Result

Implemented a pure cleanup module with paired-marker/context checks, modern THE
and verified historical THIS forms, and a corroborated historical end notice.
Malformed/absent/ambiguous boundaries preserve the complete original. Existing
legacy wrappers and consumers remain for WI0008 migration.

# Validation

Canonical scripts/test: 2915 tests pass in 76.825s after repair; 29 focused
tests pass. Format: 274 files unchanged; lint passes. LRH: 0 errors and 351 existing
warnings; WI prompt-ready and diff check clean. All four how-to blocks execute.
Cold review found one P2 quadratic regex case; coordinator reproduced and repaired
both the marker and analogous historical notice. Same-scope recheck cleared the
repair; all seven frozen hashes matched. Independent initial Gettenberg suite:
437 tests; repaired focused suite: 29 tests. See
[qualification](../../development/evidence/gettenberg-cleanup-20261016/qualification.json).
Both first hosted rounds and final-head CI remain required before integration.

# Follow-up

Consumer/CLI migration, broader historical-marker coverage when evidence supports
it, human-approved main delivery and native terminal closeout.
