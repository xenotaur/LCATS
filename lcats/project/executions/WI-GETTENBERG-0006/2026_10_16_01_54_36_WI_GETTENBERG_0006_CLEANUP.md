---
execution_id: 2026_10_16_01_54_36_WI_GETTENBERG_0006_CLEANUP
prompt_id: PROMPT(WI-GETTENBERG-0006:WI_GETTENBERG_0006_CLEANUP)[2026-10-16T01:54:06+00:00]
work_item: WI-GETTENBERG-0006
status: landed
rerun_of:
pr: https://github.com/xenotaur/LCATS/pull/517
commit: b4ec4c452ed178dd62472af9f1a46b44e70ce485
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

Canonical scripts/test: 2919 tests pass in 76.935s after footer repair; 33 focused
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
added regressions and requalified. Prior final recheck verified those fixes but exposed a historical license-separator
regression. Under a renewed human grant, the exact separator is now qualified in
code and both historical fixtures, with an independent clean recheck. Final-head
CI and thread resolution subsequently passed as recorded below.

Both first hosted rounds completed. All three findings were reproduced, repaired
and independently rechecked, and all threads resolved. The historical license
separator repair also passed independent verification under the renewed grant.
Four final-head CI checks passed. Internally merged as 2378fccaf0a12d82c0cbb4813d74b8f372e1a9a2, verified head
40cd36f036439575b63322acc3a91beee3a244c1 and base 3d55a48767c097aedc800cbad9012cca099f5cd2.
Merge parents and accepted-head tree match; all seven source hashes unchanged.
[Integration evidence](../../development/evidence/gettenberg-cleanup-20261016/integration.json)
records acceptance and limitations. Native status remains in_progress until main.

# Follow-up

Consumer/CLI migration, broader historical-marker coverage when evidence supports
it, human-approved main delivery and native terminal closeout.
