---
execution_id: 2026_10_22_17_58_16_GETTENBERG_LANDING_FACTS
prompt_id: PROMPT(AD_HOC:GETTENBERG_LANDING_FACTS)[2026-10-22T17:58:16+00:00]
work_item: AD_HOC
status: landed
rerun_of:
pr: https://github.com/xenotaur/LCATS/pull/528
commit: b4ec4c452ed178dd62472af9f1a46b44e70ce485
created_at: 2026-10-22T17:58:16+00:00
agent: codex_app
instruction_source: project/development/gettenberg-scope-causality-audit.md
session_transcript: codex-app:01a13653-87a6-7743-b734-7440a42ee1be
---

# Summary

Scoped repair of missing audit-facts reproduction procedure; delegated to scope_inventory after landing preflight.

# Result

New standard-library-only runner reproduces18 derivable audit fields from pinned Git and hash-verified reports. Three historical investigator-parity fields explicitly excluded. Original archives untouched.

# Validation

Successful /tmp/gettenberg-scope-facts-final-20261022.json; explicit format/lint, import/help, no-legacy dependency, overwrite/protected/symlink/missing-input checks passed. Independent review pending at this checkpoint.

# Follow-up

Reproduce only recorded derivable facts; no historical wire reconstruction or product acceptance. Native lifecycle remains in_progress until main closeout.


## Final local verification — 2026-10-22 18:08 UTC

Substantive commit141e151b binds the reviewed repair. All12reviewed source hashes
match; no unresolved P0–P2 findings. Full canonical suite passes3,120 tests with
absolute worktree PYTHONPATH and loopback permission; nine focused regression tests
pass independently. Fresh causal/literal/numeric rows exactly match archived evidence.
Facts reproduce18 fields with historical parity excluded. Format/lint and LRH pass
(0errors/351warnings). Hosted CI/final integration remain separately verified gates.

[Landing evidence](../../../../experiments/10_gettenberg_qualification/results/gettenberg-scope-adoption-20261022/README.md).
