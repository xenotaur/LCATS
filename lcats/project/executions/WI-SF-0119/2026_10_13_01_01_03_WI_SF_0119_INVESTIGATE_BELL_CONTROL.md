---
execution_id: 2026_10_13_01_01_03_WI_SF_0119_INVESTIGATE_BELL_CONTROL
prompt_id: PROMPT(WI-SF-0119:WI_SF_0119_INVESTIGATE_BELL_CONTROL)[2026-10-12T23:48:46+00:00]
work_item: WI-SF-0119
status: landed
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/500
commit: c5c814d815842374f8711cae1f372bb8b687e60c
created_at: 2026-10-13T01:01:03+00:00
agent: claude_app
instruction_source: project/work_items/proposed/WI-SF-0119.md
session_transcript: claude-app:dff6f127-44db-417c-9b1e-0f962af4c00a
---

# Summary

Executed WI-SF-0119 through /lrh-execute: an offline investigation of why the Heinlein Bell negative control returned qualifies in two of three trials of the WI-SF-0116 canary rerun, with a proposal for four additional control stories and a live-run design.

# Result

- Added experimental/science_fiction_analysis_trial/heinlein_canary_followup_bell_control.md (PR 500). No model was called; the manifest, rubric, prompts and persisted results were not edited.
- The three Bell trials sent the Heinlein stage identical inputs (same fingerprint inputs and payload hash, same three evidence records in the same order) and still produced different answers, so run-to-run variation at identical inputs is supported and its mechanism is a hypothesis for a live run. Tool-call path, evidence selection, the prompt and upstream Knight and Suvin outcomes are contradicted as sources of the between-trial difference.
- The manifest's control rationale (no scientific or technological condition) rests on wording the five encoded condition texts do not contain. Four extra controls are proposed (Blue Cross, Brown Wolf, A Case of Sunburn, A Bad Day for Sales) with expectations written before any run and an explicit no-owner-source exception, plus a design of at least three flag-on trials per story run in rounds.

# Validation

- lrh validate reported 0 errors; git diff --check clean.
- The embedded comparison script was run with python3 -I and reproduces its embedded output.
- Two cold-context fact-checks: the first found one wrong story detail and four wording or sourcing gaps (all fixed with approval); the second found nothing of substance.

# Follow-up

- Two cosmetic nits from the second check remain: the first-canary wording should say the key mismatch or unparseable text discarded the responses, and one long line in section 6.
- A later item must run the live design; WI-SF-0120 (request capture) and WI-SF-0121 (private server) are its natural prerequisites.
