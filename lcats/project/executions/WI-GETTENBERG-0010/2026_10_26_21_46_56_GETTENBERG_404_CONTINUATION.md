---
execution_id: 2026_10_26_21_46_56_GETTENBERG_404_CONTINUATION
prompt_id: PROMPT(WI-GETTENBERG-0010:GETTENBERG_404_CONTINUATION)[2026-10-26T21:46:45+00:00]
work_item: WI-GETTENBERG-0010
status: landed
rerun_of:
pr: https://github.com/xenotaur/LCATS/pull/534
commit: b4ec4c452ed178dd62472af9f1a46b44e70ce485
agent: codex_app
instruction_source: "Human-approved narrow 404 repair; development/gettenberg-development-log.md"
session_transcript: codex-app:01a13653-87a6-7743-b734-7440a42ee1be
created_at: 2026-10-26T21:46:56+00:00
---

# Summary

Implement the approved 404-only resource-unavailability continuation in PR #534.
Grant and acceptance: project/development/gettenberg-development-log.md,
2026-10-26 21:46 UTC. Hard stop 23:16:21 UTC; no main promotion or fallback routes.

# Result

Implemented at 94d4331f1d1215b89599cb06ec197eb015e4bce3. Structured terminal HTTP
errors preserve endpoint identity; only status404 continues as unavailable, with
status2 and distinct logs/counts. No retry/fallback; source/cleanup/policy invariants
remain. User report and WI0010 establish demand; native readiness passes.
Independent agent review found no substantive issues. Main delivery remains pending.

# Validation

120 focused tests and 2,977 canonical tests pass (100.173 seconds); no output
leakage. Canonical format/lint and explicit experiment-runner lint pass. Clean committed-source wheel equals installed package (165 Python/two JSON files).
Both installed CLI continuation scenarios pass twice with exact output reuse; all
70/98/98 loaded-origin hashes verify. LRH validates with zero errors and 354
pre-existing combined-tree warnings. Evidence is archived under
experiments/10_gettenberg_qualification/results/gettenberg-http404-20261026/.

# Follow-up

Alternate acquisition for 1367 and 410 handling are outside this repair.
Main review, main promotion and canonical lifecycle closeout remain pending.
