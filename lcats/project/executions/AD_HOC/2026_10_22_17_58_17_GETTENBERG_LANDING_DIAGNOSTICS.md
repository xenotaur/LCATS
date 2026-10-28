---
execution_id: 2026_10_22_17_58_17_GETTENBERG_LANDING_DIAGNOSTICS
prompt_id: PROMPT(AD_HOC:GETTENBERG_LANDING_DIAGNOSTICS)[2026-10-22T17:58:17+00:00]
work_item: AD_HOC
status: landed
rerun_of:
pr: https://github.com/xenotaur/LCATS/pull/528
commit: b4ec4c452ed178dd62472af9f1a46b44e70ce485
created_at: 2026-10-22T17:58:17+00:00
agent: codex_app
instruction_source: project/development/gettenberg-scope-causality-audit.md
session_transcript: codex-app:01a13653-87a6-7743-b734-7440a42ee1be
---

# Summary

Scoped diagnostic import-safety and transitive Python dependency pinning repair; delegated to causality_audit.

# Result

Causal/trace runners now have guarded main functions and delayed optional imports; causal replay pins174 Python product modules and validates loaded module origins before/after calculation. Restores prior alarm handlers.

# Validation

Eight-case rerun /tmp/pr528-causal-repaired-20261022.json exactly matches all archived rows;68 executing module origins validated. Explicit format/lint and import/help without gutenbergpy passed. Final independent review pending.

# Follow-up

No old archive changes or product behavior changes. Tree guard pins Python sources; immutable input receipts remain separate. Native lifecycle remains in_progress.


## Final local verification — 2026-10-22 18:08 UTC

Substantive commit141e151b binds the reviewed repair. All12reviewed source hashes
match; no unresolved P0–P2 findings. Full canonical suite passes3,120 tests with
absolute worktree PYTHONPATH and loopback permission; nine focused regression tests
pass independently. Fresh causal/literal/numeric rows exactly match archived evidence.
Facts reproduce18 fields with historical parity excluded. Format/lint and LRH pass
(0errors/351warnings). Hosted CI/final integration remain separately verified gates.

[Landing evidence](../../../../experiments/10_gettenberg_qualification/results/gettenberg-scope-adoption-20261022/README.md).
