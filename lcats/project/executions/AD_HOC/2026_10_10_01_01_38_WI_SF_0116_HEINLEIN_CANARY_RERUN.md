---
execution_id: 2026_10_10_01_01_38_WI_SF_0116_HEINLEIN_CANARY_RERUN
prompt_id: PROMPT(AD_HOC:WI_SF_0116_HEINLEIN_CANARY_RERUN)[2026-10-10T00:09:30+00:00]
work_item: AD_HOC
status: landed
pr: https://github.com/xenotaur/LCATS/pull/492
created_at: 2026-10-10T01:01:38+00:00
agent: claude_app
instruction_source: project/work_items/proposed/WI-SF-0116.md
session_transcript: claude-app:dff6f127-44db-417c-9b1e-0f962af4c00a
---

# Summary

Created work item WI-SF-0116, which plans rerunning the Heinlein live canary after the WI-SF-0114 fail-loud fix: a flag-off baseline and three flag-on local trials of gpt-oss:20b on the two manifest canary stories, with a v2 report that compares against the WI-SF-0113 report and answers four named questions. Planning only; no trials were run and no code was changed.

# Result

Wrote project/work_items/proposed/WI-SF-0116.md (type evaluation, depends on WI-SF-0113 and WI-SF-0114), registered it in WS-KNIGHT-NOVUM-ANALYSIS, and opened PR 492. The owner approved the proposal and asked for one change: the earlier rule about database files was replaced by a guard that commits everything the runner persists and, if any non-JSON file such as a database appears, records its path, size and hash and stops to check why. The check behind that change found that the canary runner writes only JSON and JSONL and that the first canary produced no database file.

# Validation

- lrh validate reported 0 errors and no warnings that mention WI-SF-0116; lrh work-items readiness reported prompt_ready: yes.
- The number 0116 was re-checked against origin/main and the open PRs just before writing.

# Follow-up

- Land the PR with /lrh-land, then run /lrh-execute WI-SF-0116 once a loopback Ollama server with gpt-oss:20b is confirmed.
- Update session_transcript from pending at closeout.
