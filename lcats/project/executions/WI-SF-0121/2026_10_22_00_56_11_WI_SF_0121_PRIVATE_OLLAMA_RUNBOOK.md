---
execution_id: 2026_10_22_00_56_11_WI_SF_0121_PRIVATE_OLLAMA_RUNBOOK
prompt_id: PROMPT(WI-SF-0121:WI_SF_0121_PRIVATE_OLLAMA_RUNBOOK)[2026-10-15T06:03:09+00:00]
work_item: WI-SF-0121
status: landed
rerun_of:
pr: https://github.com/xenotaur/LCATS/pull/525
commit: 33d4885787e07b2823cfc6f3833e9f2e1f7b5e8d
created_at: 2026-10-22T00:56:11+00:00
agent: claude_app
instruction_source: project/work_items/proposed/WI-SF-0121.md
session_transcript: claude-app:dff6f127-44db-417c-9b1e-0f962af4c00a
---

# Summary

Executed WI-SF-0121 through /lrh-execute: the Heinlein canary runbook now documents a private Ollama server, an isolation check from the server log, a keep-awake step and a sleep check, and warns that its commands use the first canary's output roots.

# Result

- Changed experimental/science_fiction_analysis_trial/heinlein_canary_runbook.md only (PR 525): a numbered private-server procedure on port 11435 with the OLLAMA_HOST and OLLAMA_NO_CLOUD settings the WI-SF-0116 rerun used; an isolation check that treats ollama ps as necessary but not sufficient and reads the server log for foreign model loads (template selection lines) and for a POST /v1/chat/completions count that is at least the number of WI-SF-0120 request records; a caffeinate step; a pmset sleep check using the rerun's 22:57:47 to 00:25:16 EDT sleep as the example; and a note that unchanged commands append to the first canary's results.
- No code, runner, manifest or live run. The text says client identity cannot be proven and that a private server does not remove run-to-run variation.

# Validation

- lrh validate reports 0 errors; git diff --check clean.
- A cold fact-check against the real WI-SF-0116 server log, the v2 report, the runner and the local machine found the request-count equality wrong (the OpenAI client retries, default 2, including on HTTP 500; 17 of the log's 46 chat lines are 500s), an overstated attribution of the /api/chat and /api/show lines, a DarkWake note and a memory-sharing note; all were fixed with approval, and a second pass found one stale phrase, also fixed.

# Follow-up

- None required. The first live canary on a private server should record the server config line and apply the isolation and sleep checks.
