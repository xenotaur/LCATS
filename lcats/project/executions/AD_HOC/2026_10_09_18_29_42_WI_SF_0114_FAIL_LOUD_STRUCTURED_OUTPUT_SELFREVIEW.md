---
execution_id: 2026_10_09_18_29_42_WI_SF_0114_FAIL_LOUD_STRUCTURED_OUTPUT_SELFREVIEW
prompt_id: PROMPT(AD_HOC:WI_SF_0114_FAIL_LOUD_STRUCTURED_OUTPUT_SELFREVIEW)[2026-10-09T18:27:44+00:00]
work_item: AD_HOC
status: landed
rerun_of: 2026_10_09_16_00_33_WI_SF_0114_FAIL_LOUD_STRUCTURED_OUTPUT
pr: https://github.com/xenotaur/LCATS/pull/490
commit: fa33d1bbf589b5858ae1c14cf0777001ba42d61a
created_at: 2026-10-09T18:29:42+00:00
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/490
session_transcript: claude-app:dff6f127-44db-417c-9b1e-0f962af4c00a
---

# Summary

Substitute re-review of PR 490 (WI-SF-0114 implementation) by a cold-context subagent against head c09884d3, after the bot round, in place of a further hosted review round. Report-only; the owner approved fixing three of its five points.

# Result

Nothing blocked. The subagent ran the changed test modules in a real clone (146 tests OK), ran the fake-backend smoke, and found no regression for a model that returns schema-correct keys. Its points and what was done in c4f89bbbcb47f22d729082de1ea386d70bf42e0d:

- Fixed (nit): a list or dict status raised a bare TypeError for unhashable type; status is now type-checked first so it gets the clear missing or invalid status message, with a test for both cases.
- Fixed (low): the Heinlein prompt forced the status absent for a dependent criterion whose prerequisite is absent, although the validator only rejects present; it now says a status other than present, absent if the story fails the condition itself or not_assessable if the evidence is insufficient.
- Documented (low): the failure kind recorded for any non-JSON text fallback, in every stage, changes from JSONDecodeError to ValueError. Retry and failure classification are unchanged, and the PR body and the primary record now say so (they had said Knight and Suvin change only for fenced replies).
- Skipped by owner decision (nits): the empty-evidence-list test does not pin downstream behavior because the fake backend cites evidence IDs that do not exist, and the old-checkpoint test shows validation on resume rather than fingerprint invalidation, which has its own test.

# Validation

- scripts/test: 2547 tests, OK. scripts/format --check --diff and scripts/lint passed with the CI-pinned black 25.11.0 and ruff 0.15.0 (the scratchpad venv was recreated); the runner file shows the same four black hunks and one ruff finding as main. lrh validate reported 0 errors.

# Follow-up

- Confirm CI on the final head, then present the merge and closeout ask.
- Update session_transcript from pending at closeout.
