---
execution_id: 2026_11_11_01_49_34_WI_SF_0127_IMPLEMENTATION_REVIEW
prompt_id: PROMPT(AD_HOC:WI_SF_0127_IMPLEMENTATION_REVIEW)[2026-11-11T01:49:34+00:00]
work_item: AD_HOC
status: in_progress
rerun_of: 2026_11_10_23_53_07_WI_SF_0127
pr: https://github.com/xenotaur/LCATS/pull/544
commit:
created_at: 2026-11-11T01:49:34+00:00
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/544
session_transcript: pending
---

# Summary

Address the review findings on PR 544 (WI-SF-0127, the opt-in date-aware Heinlein stage): one Codex thread, three Copilot threads, and the substitute cold review of head c3a3582f. Each finding was verified against the code and shown to the owner as a triage before any edit; the owner approved both fix rounds.

# Result

Codex P2 (c3a3582f): a composition interval starting after the analysis date is inverted once an open end is capped at that date, silently publishing a not_applicable profile. Reproduced (earliest 2040, analysis date 2026-11-10 gave not_assessable). Fixed in the library and the gate: HeinleinTemporalAnalysis now rejects a composition earliest or latest after the analysis month (the sidecar validator rejects a stored one), and the run gate checks the same rule before any model call.

Copilot, three threads (c0e528ed), each reproduced first: (1) a failed record dropped the run's composition inputs, so failed_analysis now takes and keeps the validated composition; (2) the fake backend's quote joined split words, so a paragraph starting with a line break or double space produced a quote not in the text, now an unchanged substring; (3) omitted keys were accepted as nulls (a period with only standing and source became a fact true for all time, an omitted dated_prediction meant none), so every schema key is now required at every level while an explicit null stays allowed. From the cold review, the default analysis date is now resolved once per run so the gate and every story share one date.

Not changed: a composition day after the analysis date inside the analysis month (the check works by month), and a bare-year analysis date counting from January.

# Validation

Black, ruff, scripts/test (3119 tests OK) and lrh validate (0 errors, 360 existing warnings, unchanged from main) passed on c0e528ed; the fake-backend smoke with --include-heinlein --include-heinlein-temporal processes both stories; black and ruff on run_worldcon_spike.py add no findings beyond the 4 black hunks and 1 ruff error already on main. Threads are left for confirm-fixes to resolve.

# Follow-up

The PR body was re-synced with these fixes. Matching human and premise anchors at the sidecar-validator level, and a day-level composition check, remain out of scope here.
