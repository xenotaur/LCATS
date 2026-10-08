---
execution_id: 2026_10_08_16_11_31_WI_SF_0113_HEINLEIN_LIVE_CANARY
prompt_id: PROMPT(WI-SF-0113:WI_SF_0113_HEINLEIN_LIVE_CANARY)[2026-10-08T15:21:57+00:00]
work_item: WI-SF-0113
status: landed
pr: https://github.com/xenotaur/LCATS/pull/487
commit: 776c9fe2b4a09c5b3e03b43dcfcbd93720be68ed
created_at: 2026-10-08T16:11:31+00:00
agent: claude_app
instruction_source: project/work_items/proposed/WI-SF-0113.md
session_transcript: claude-app:dff6f127-44db-417c-9b1e-0f962af4c00a
---

# Summary

Executed WI-SF-0113 through /lrh-execute: the Heinlein live canary from heinlein_canary_runbook.md, as one flag-off baseline and three flag-on trials on the two manifest canary stories, using gpt-oss:20b (digest 17052f91a42e, 32768 context) through loopback Ollama with --max-tokens 8192. Wrote heinlein_canary_report.md with a revise recommendation.

# Result

- All four runs completed 2 of 2 stories at manifest fingerprint 91b751682f0718e2 and code commit 8540a93845aa3f0dd68218e763842bbd0ee031f4, with no paid calls.
- The pipeline silently discarded the model's Heinlein decisions in all six raw responses: the model used criterion, decision or decision_state, and evidence_ids instead of the schema keys criterion_id, status, and supporting_evidence_ids, and the normalizer defaulted every criterion to not_assessable while reporting the stage complete.
- Trial 1 returned fenced JSON text for anderson/bell; that hit the designed failure path (quarantine, Unavailable, Knight and Suvin untouched).
- The evidence stage succeeded in all four runs; the baseline's Vonnegut Knight (provider 500) and Suvin (quarantine) stages failed once.
- No runbook stop condition fired. The commit with the report and 108 result files is 9e9ca1a9ca9c96ec63aaaa401bf95318721fada4; the PR is 487.

# Validation

- scripts/test: 2465 tests, OK. scripts/format --check --diff and scripts/lint passed with the CI-pinned black 25.11.0 and ruff 0.15.0 (the default environment has black 26.3.1).
- Fake-backend smoke with --include-heinlein processed both stories and published 2 verdicts.
- python -m json.tool passed on the manifest and all four manifest snapshots; each snapshot equals the manifest as parsed JSON.
- lrh validate reported 0 errors. git diff --check on the report and project files was clean; the runner-generated per-run reports under results/ have trailing whitespace and were left unedited by design.

# Follow-up

- Decide how the Heinlein stage should handle mismatched criterion keys (fail loudly or record an explicit alias coercion), whether to strip Markdown fences, and how to enforce the key names for local backends; then rerun this canary. No work item exists for that yet.
- Update session_transcript from pending at closeout.
