---
execution_id: 2026_10_16_01_54_36_WI_GETTENBERG_0006_CLEANUP
prompt_id: PROMPT(WI-GETTENBERG-0006:WI_GETTENBERG_0006_CLEANUP)[2026-10-16T01:54:06+00:00]
work_item: WI-GETTENBERG-0006
status: in_progress
rerun_of:
pr: https://github.com/xenotaur/LCATS/pull/517
commit: 53b4a4c073ab1cbbedae1e9eba8e5f156c66e8b9
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

Canonical scripts/test: 2918 tests pass in 77.525s after hosted repairs; 32 focused
tests pass. Format: 274 files unchanged; lint passes. LRH: 0 errors and 351 existing
warnings; WI prompt-ready and diff check clean. All four how-to blocks execute.
Cold review found one P2 quadratic regex case; coordinator reproduced and repaired
both the marker and analogous historical notice. Same-scope recheck cleared the
repair; all seven frozen hashes matched. Independent initial Gettenberg suite:
437 tests; repaired focused suite: 29 tests. See
[qualification](../../development/evidence/gettenberg-cleanup-20261016/qualification.json).
Both first hosted rounds completed: Codex found unsupported Unicode spacing;
Copilot found single-star outer delimiters and wrapped second-book fragments.
Coordinator reproduced all three, broadened refusal-only candidate detection,
added regressions and requalified. Reserved independent recheck and final-head
CI remain pending; threads will be resolved only after verification.

# Follow-up

Consumer/CLI migration, broader historical-marker coverage when evidence supports
it, human-approved main delivery and native terminal closeout.
