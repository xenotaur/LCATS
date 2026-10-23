---
execution_id: 2026_10_22_17_28_31_WI_SF_0123_TEMPORAL_DESIGN_PROPOSAL_REVIEW
prompt_id: PROMPT(AD_HOC:WI_SF_0123_TEMPORAL_DESIGN_PROPOSAL_REVIEW)[2026-10-22T17:28:27+00:00]
work_item: AD_HOC
status: landed
rerun_of: 2026_10_22_16_00_34_WI_SF_0123_TEMPORAL_DESIGN_PROPOSAL
pr: https://github.com/xenotaur/LCATS/pull/529
commit: 2f52e66dbc5cde330ba2498e4f99d61e7c87d007
created_at: 2026-10-22T17:28:31+00:00
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/529
session_transcript: claude-app:dff6f127-44db-417c-9b1e-0f962af4c00a
---

# Summary

Review-response round for PR 529 (WI-SF-0123): two Codex P1 threads on the proposal, triaged against the code and approved by the user before any edit.

# Result

- Dependent criteria: the existing prompt forces essential and causal absent when different is absent (run_worldcon_spike.py:2560-2564), and different is today-relative there, so copying essential and causal from the existing record into the as-written verdict kept the same today-relative error. R8 now has the new stage assess essential and causal against its author-time premises (citing premise IDs), takes only human from the existing record, applies the prerequisite rules within the new record, and reports differences from the existing record for information. The record shape, R9, open question 5 and the stage work item changed to match.
- Novelty: R4 said a fantastic element that a folktale presents as ordinary was unknown, which contradicted D1 (the reference is the author's real world). R4 now judges novelty against the author-time empirical world, so supernatural elements are novel however ordinary they are to the characters. The Bell rows of the trial evidence were restored to novel with different present, removing a judgment call added in the previous round.
- Both findings were valid and were gaps in the first-round design.

# Validation

- lrh validate reported 0 errors; git diff --check clean; the evidence script still reproduces its output.

# Follow-up

- Run confirm-fixes, resolve the threads, then the merge-and-closeout ask.
