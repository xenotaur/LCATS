---
execution_id: 2026_10_09_01_49_45_WI_SF_0114_HEINLEIN_OUTPUT_HANDLING_SELFREVIEW
prompt_id: PROMPT(AD_HOC:WI_SF_0114_HEINLEIN_OUTPUT_HANDLING_SELFREVIEW)[2026-10-09T01:49:32+00:00]
work_item: AD_HOC
status: landed
rerun_of: 2026_10_09_00_03_38_WI_SF_0114_HEINLEIN_OUTPUT_HANDLING
pr: https://github.com/xenotaur/LCATS/pull/488
commit: 5c99342bd2433ef4a409d6d79b7f5ad6ebb5c377
created_at: 2026-10-09T01:49:45+00:00
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/488
session_transcript: claude-app:dff6f127-44db-417c-9b1e-0f962af4c00a
---

# Summary

Substitute self-review of PR 488 (WI-SF-0114) by a cold-context subagent against head 1860bdd3fb98f663fa9c315f37ce7c18647554f8, in place of a further hosted review round. The subagent was report-only; the main session applied the fixes with the owner's approval, choosing the recommended options for the three open decisions.

# Result

Nine findings, all addressed in the work item in 5a5f285f8a5cc36f1a5d96eb974fefcb78e835f5. The main session verified the first, second and fifth directly in the code:

- I had given the evidence schema key as type; the schema key is evidence_type (run_worldcon_spike.py:2376), and type only works through an existing coercion in the evidence builder (evidence.py:90-95). The item now names evidence_type and states that the existing coercion is left unchanged.
- The item asked to bump an evidence prompt version that does not exist; the shared PROMPT_VERSION feeds Knight and Suvin and is pinned by a test (worldcon_spike_test.py:1662), and the stage fingerprint already hashes the system prompt and tool schema (run_worldcon_spike.py:971-972). Only HEINLEIN_PROMPT_VERSION is bumped now.
- The strict parse raises ValueError, not JSONDecodeError, so the fallback handler must catch both and keep the metadata.
- A missing or non-list evidence or heinlein_criteria key is now a failure, and a missing confidence or counterevidence_ids quarantines the Heinlein stage; an explicit empty evidence list stays valid with a run-log warning.
- The item states that an evidence-stage failure makes the whole story failed with no sidecar, unlike the Heinlein failure.
- Fence tolerance applies to every stage through the shared fallback; the caller list, the import, the fixtures plan (synthetic fixtures, Bell evidence, corpus dependency, paths to strip) and several wording points were corrected.

# Validation

- lrh validate reported 0 errors; lrh work-items readiness reported prompt_ready: yes.

# Follow-up

- Confirm CI on the final head, then present the merge and closeout ask.
- PR 489 (the canary report correction) should land before or with this item, since the item cites its finding 8.
- Update session_transcript from pending at closeout.
