---
execution_id: 2026_10_08_23_18_21_WI_SF_0113_HEINLEIN_LIVE_CANARY_CLOSEOUT_NOTE
prompt_id: PROMPT(AD_HOC:WI_SF_0113_HEINLEIN_LIVE_CANARY_CLOSEOUT_NOTE)[2026-10-08T23:18:06+00:00]
work_item: AD_HOC
status: landed
rerun_of: 2026_10_08_16_11_31_WI_SF_0113_HEINLEIN_LIVE_CANARY
pr: https://github.com/xenotaur/LCATS/pull/487
commit: 776c9fe2b4a09c5b3e03b43dcfcbd93720be68ed
created_at: 2026-10-08T23:18:21+00:00
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/487
session_transcript: claude-app:dff6f127-44db-417c-9b1e-0f962af4c00a
---

# Summary

Closeout note for PR 487 (execution of WI-SF-0113, the Heinlein live canary), landed through /lrh-execute and /lrh-land. The primary execution record is immutable, so the CHAIN-NOTE lives in this record.

# Result

PR 487 was squash-merged as 776c9fe2b4a09c5b3e03b43dcfcbd93720be68ed at head 5cca096f8e5662dcb4b4f6e2bca04465c2b343c7. It persisted a flag-off baseline and three flag-on local trials of gpt-oss:20b with heinlein_canary_report.md, which recommends revise: the pipeline silently discarded the model's Heinlein decisions in all six raw responses because the model used criterion, decision and evidence_ids keys instead of the schema's criterion_id, status and supporting_evidence_ids. One bot thread (control trial 1 reported as met) was fixed, and a substitute self-review found stop-condition wording and persisted-evidence gaps, also fixed. All four CI checks passed on the final head. The primary, review, confirm and self-review records were landed with this closeout and WI-SF-0113 was resolved. WS-KNIGHT-NOVUM-ANALYSIS stays open.

CHAIN-NOTE: cycles=2; stops=2; gates=[confirm, self-review]; friction=report-overclaim; self_review_rounds=1; note="local canary executed; 1 bot thread (control trial 1 labelled met) fixed; substitute self-review found stop-condition wording and persisted-evidence gaps, fixed; key-mismatch defect found, recommendation revise; WI resolved"

# Validation

- lrh validate reported 0 errors before and after closeout.
- CI: coverage, lint and both test checks passed on the final head.

# Follow-up

- No work item yet for the defect the canary found: silent defaulting on mismatched criterion keys, fenced JSON handling, and key enforcement for local backends; then rerun the canary.
