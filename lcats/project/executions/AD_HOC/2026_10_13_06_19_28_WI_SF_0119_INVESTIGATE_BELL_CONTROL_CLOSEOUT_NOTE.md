---
execution_id: 2026_10_13_06_19_28_WI_SF_0119_INVESTIGATE_BELL_CONTROL_CLOSEOUT_NOTE
prompt_id: PROMPT(AD_HOC:WI_SF_0119_INVESTIGATE_BELL_CONTROL_CLOSEOUT_NOTE)[2026-10-13T06:19:07+00:00]
work_item: AD_HOC
status: landed
rerun_of: 2026_10_13_01_01_03_WI_SF_0119_INVESTIGATE_BELL_CONTROL
pr: https://github.com/xenotaur/LCATS/pull/500
commit: c5c814d815842374f8711cae1f372bb8b687e60c
created_at: 2026-10-13T06:19:28+00:00
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/500
session_transcript: claude-app:dff6f127-44db-417c-9b1e-0f962af4c00a
---

# Summary

Closeout note for PR 500 (the execution of WI-SF-0119, the Bell control investigation), landed through /lrh-execute and /lrh-land. The primary execution record is immutable, so the CHAIN-NOTE lives in this record.

# Result

PR 500 was squash-merged as c5c814d815842374f8711cae1f372bb8b687e60c at head 7881ac6cc66c736c63a2b6e3060f71f96d3330e9. It adds heinlein_canary_followup_bell_control.md, an offline analysis of the persisted WI-SF-0116 results. The three Bell trials sent the Heinlein stage identical inputs (same fingerprint inputs and payload hash, same three evidence records in the same order) and still answered differently, so run-to-run variation at identical inputs is supported and its mechanism is a hypothesis for a live run; tool-call path, evidence selection, the prompt and upstream stage outcomes are contradicted as sources of the difference. The cited evidence for the trial 2 and 3 answers is thin, and the manifest's control rationale rests on wording the five encoded condition texts do not contain. Four controls and one probe are proposed with cited story text (11 offsets, all checked against the corpus) and the owner's decisions D1 to D7 (cited text with owner confirmation before any lock, Blue Cross and Brown Wolf as negatives, Sunburn with a per-criterion expectation, Leiber as the weaker positive, Cthulhu as a probe, Bell kept as a negative) plus a live-run design of 21 story-runs. Two review threads (Copilot, Codex) were fixed and resolved, and the Sunburn apostrophe was fixed before the merge at the owner's request. All four CI checks passed on the final head. The primary, self-review, review and confirm records were landed with this closeout and WI-SF-0119 was resolved. WS-KNIGHT-NOVUM-ANALYSIS stays open.

CHAIN-NOTE: cycles=3; stops=4; gates=[self-review, review, self-review, confirm]; friction=thin-source-and-heredoc-substitution; note="investigation run via /lrh-execute; two cold fact-checks before the PR found one wrong story detail and four wording or sourcing gaps; Codex's expectation-source finding led to a seven-decision owner review and cited-text controls; an unquoted heredoc executed backticks as commands (no side effects, file re-written with the Write tool); WI resolved"

# Validation

- lrh validate reported 0 errors before and after closeout.
- CI: coverage, lint and both test checks passed on the final head.

# Follow-up

- Run the live control design (at least three flag-on trials per story, run back to back in rounds), ideally after WI-SF-0120 (request capture) and WI-SF-0121 (private server), and have the owner confirm each expectation before locking it into a manifest.
- Discuss the open question of plausible-in-context for older stories (for example a habitable Mars) and the rubric-interpretation question of whether a fairy-tale condition counts as different.
