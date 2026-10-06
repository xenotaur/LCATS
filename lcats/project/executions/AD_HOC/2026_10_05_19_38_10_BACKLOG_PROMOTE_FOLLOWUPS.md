---
execution_id: 2026_10_05_19_38_10_BACKLOG_PROMOTE_FOLLOWUPS
prompt_id: PROMPT(AD_HOC:BACKLOG_PROMOTE_FOLLOWUPS)[2026-10-05T19:37:58+00:00]
work_item: AD_HOC
status: landed
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/471
commit: c42484f92382607a4cc617ff9bed040e85db1321
agent: claude_app
instruction_source: user request in session ("Create a PR to capture the open items")
session_transcript: claude-app:6a2dbae2-adca-4a2a-92fe-2e95d3b2a4e0
created_at: 2026-10-05T19:38:10+00:00
---

# Summary

Captures the open items surfaced by the end-of-session /lrh-work-remains
report as three entries in project/design/backlog.md.

# Result

- Added a backlog section "From WS-PROMOTE-MODE-REDESIGN and PR #362".
- Entries: absolute cache_db_path in the 146 promoted genre.json files (P2);
  optional registry routing of promote.py's two genre_sidecar imports (P3);
  scripts/format and scripts/lint not covering repo-root experiments/ (P3).
- Not filed here: the missing `lrh confirm-fixes check-batch-routine`
  subcommand, which belongs to the logical_robotics_harness repo.

# Validation

- lrh validate: 0 errors.

# Follow-up

- File the check-batch-routine gap against logical_robotics_harness.
- Save the unsaved memory candidates (repo-root vs lcats/ path layout).
