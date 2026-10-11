---
execution_id: 2026_10_11_14_58_55_WI_SF_0116_RUN_CANARY_V2_CLOSEOUT_NOTE
prompt_id: PROMPT(AD_HOC:WI_SF_0116_RUN_CANARY_V2_CLOSEOUT_NOTE)[2026-10-11T14:58:31+00:00]
work_item: AD_HOC
status: landed
rerun_of: 2026_10_11_04_39_38_WI_SF_0116_RUN_CANARY_V2
pr: https://github.com/xenotaur/LCATS/pull/495
commit: 01f1ff3970e6a4602e248a3c353c95a6f5b3057a
created_at: 2026-10-11T14:58:55+00:00
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/495
session_transcript: claude-app:dff6f127-44db-417c-9b1e-0f962af4c00a
---

# Summary

Closeout note for PR 495 (the execution of WI-SF-0116, the Heinlein canary rerun), landed through /lrh-execute and /lrh-land. The primary execution record is immutable, so the CHAIN-NOTE lives in this record.

# Result

PR 495 was squash-merged as 01f1ff3970e6a4602e248a3c353c95a6f5b3057a at head fb675eb4cd2b9c6de4420b43e9bc51214dd5fa65. It adds the flag-off baseline and three flag-on trials of gpt-oss:20b (digest 17052f91a42e, Ollama 0.32.5) under results/worldcon_spike/heinlein_canary_v2/local/ and heinlein_canary_report_v2.md; the first canary's results and report are unchanged. The mechanical fix is confirmed: all six flag-on Heinlein responses used the schema keys with rationales and evidence, with no Heinlein quarantines and no evidence-stage failures. The Bell negative control met its expectation in 1 of 3 trials (does_not_qualify in trial 1, qualifies in trials 2 and 3), the Vonnegut positive qualified 3 of 3, and strict forwarding stays unobservable because the runner does not persist the request. The report recommends revise. Review rounds fixed a per-run table error and a v1 conformance sentence, and a cold fact-check corrected a misdiagnosis (the long trial-3 stage was a machine sleep, not a hung server). All four CI checks passed on the final head. The primary, review, confirm and self-review records were landed with this closeout and WI-SF-0116 was resolved. WS-KNIGHT-NOVUM-ANALYSIS stays open.

CHAIN-NOTE: cycles=3; stops=3; gates=[review, self-review, self-review]; friction=shared-server-and-sleep-interference; self_review_rounds=2; note="live canary rerun via /lrh-execute; Copilot per-run table fix, cold fact-checks caught a sleep misdiagnosis and a v1 sentence error, all fixed; Ollama server shared with another session; WI resolved"

# Validation

- lrh validate reported 0 errors before and after closeout.
- CI: coverage, lint and both test checks passed on the final head.

# Follow-up

- Investigate why the Bell control passes in 2 of 3 trials, and consider more control stories.
- Persist the request payload so strict forwarding is observable.
- Run canaries on a private Ollama server, not one shared with another session.
- Consider a follow-up on _existing_evidence_ids, which still silently drops unknown evidence IDs.
