---
execution_id: 2026_10_22_17_43_52_WI_SF_0123_TEMPORAL_DESIGN_PROPOSAL_REVIEW
prompt_id: PROMPT(AD_HOC:WI_SF_0123_TEMPORAL_DESIGN_PROPOSAL_REVIEW)[2026-10-22T17:43:47+00:00]
work_item: AD_HOC
status: in_progress
rerun_of: 2026_10_22_16_00_34_WI_SF_0123_TEMPORAL_DESIGN_PROPOSAL
pr: https://github.com/xenotaur/LCATS/pull/529
commit: 2eeeac09b6b9a963a8a06049c4f4504bb9f8c03e
created_at: 2026-10-22T17:43:52+00:00
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/529
session_transcript: pending
---

# Summary

Second review-response round for PR 529 (WI-SF-0123): four further Codex inline threads, triaged and approved by the user before any edit. A mistake in the first round is recorded below.

# Result

- Process slip: during the first round's confirm step I resolved all six open threads, including four new Codex threads I had not read or triaged. I reopened the three that were real defects and left one resolved because it duplicated the novelty finding already fixed.
- Composition bounds (valid): D4 treated adulthood and an author's first publication as lower bounds on composition, which is wrong because a debut can be written years before publication or while the author is a minor. D4 now uses birth as the lower bound and death as a hard upper bound, treats the story's own first publication as an upper bound, and treats career milestones as contextual evidence only unless a story-specific source says otherwise. The Sunburn wording in the evidence file now says lifespan, with the 1954 first-story date as context.
- R4 overlap (valid): the absent and ambiguous cases overlapped when some premise novelty was unknown; absent now requires every counted premise to be explicitly false (or no counted premises), and ambiguous applies when none is true and some are unknown.
- R8 source selection (valid): the temporal verdict borrowed human from another analysis without storing which one. The record now persists source_heinlein_analysis_id and the borrowed human status, selects the current complete analysis with the same story hash and evidence set, includes the source ID in the new stage's fingerprint inputs, and reports not_computed when no matching analysis exists.
- Novelty against the story's world (duplicate): already fixed by the first round's R4 change.

# Validation

- lrh validate reported 0 errors; git diff --check clean; the evidence script still reproduces its output.

# Follow-up

- Run confirm-fixes, read and resolve each thread individually, then the merge-and-closeout ask.
