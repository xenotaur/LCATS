---
execution_id: 2026_10_18_01_59_38_GETTENBERG_CI_MAINTENANCE_REVIEW
prompt_id: PROMPT(AD_HOC:GETTENBERG_CI_MAINTENANCE_REVIEW)[2026-10-18T01:59:04+00:00]
work_item: AD_HOC
status: in_progress
rerun_of: 2026_10_18_00_54_29_GETTENBERG_CI_MAINTENANCE
pr: https://github.com/xenotaur/LCATS/pull/523
commit:
created_at: 2026-10-18T01:59:38+00:00
agent: codex_app
instruction_source: GitHub workflow validation failures at ff78d679
session_transcript: codex-app:01a13653-87a6-7743-b734-7440a42ee1be
---

# Summary

Repair two independently verified CI/review findings in PR523.

# Result

GitHub rejected job-level runner.temp in all three changed workflows. Replaced
with github.workspace/.lcats-* and added a context-availability regression test.
Independent assignment3 accepted the repair, reproduced three old failures, and
checked44 adjacent expressions. It acknowledged the earlier review gap.

Codex's P2 thread PRRT_kwDOKlhIbM6tma7X correctly identified missing parser
dependency identity. Verified pyproject's lxml>=5.2.2 and rdf.py etree use. Catalog
fingerprint now includes Python, SQLite, lxml and runtime/compiled libxml versions.
A new external-version regression keeps source keys stable as catalog keys change.
No manual hosted-review retrigger, remote deletion or Gutenberg request occurred.

# Validation

Workflow repair:2926 full tests87.491s,17 focused tests, format/lint/LRH pass.
Independent focused suite17/0.783s. Runtime repair:18 focused tests and lint pass;
final canonical suite2927/92.126s and LRH pass. Independent exact-head review
pending at this record.
Evidence: development/evidence/gettenberg-ci-maintenance-20261017/repair-checks.json.

# Follow-up

Push repaired head, independently review, verify the expected four hosted checks
and absence of failed workflow validation runs, then resolve the plainly satisfied
bot thread. Internal integration only; native lifecycle remains nonterminal.
