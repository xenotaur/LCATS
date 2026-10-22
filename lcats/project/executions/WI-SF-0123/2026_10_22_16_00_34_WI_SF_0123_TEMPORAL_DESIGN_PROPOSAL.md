---
execution_id: 2026_10_22_16_00_34_WI_SF_0123_TEMPORAL_DESIGN_PROPOSAL
prompt_id: PROMPT(WI-SF-0123:WI_SF_0123_TEMPORAL_DESIGN_PROPOSAL)[2026-10-22T15:26:45+00:00]
work_item: WI-SF-0123
status: in_progress
rerun_of:
pr: https://github.com/xenotaur/LCATS/pull/529
commit: 3de695d12518b4c52f21e3ba74657136c7f19e3e
created_at: 2026-10-22T16:00:34+00:00
agent: claude_app
instruction_source: project/work_items/proposed/WI-SF-0123.md
session_transcript: pending
---

# Summary

Executed WI-SF-0123 through /lrh-execute: a design proposal (no code) for judging the five Heinlein conditions against the author's world at the time of writing, with the six-story premise trial committed as its evidence.

# Result

- Added project/design/proposals/proposed/heinlein-temporal-reference/00_proposal.md and README.md (PROP-LCATS-HEINLEIN-TEMPORAL-REFERENCE) and experimental/science_fiction_analysis_trial/heinlein_temporal_premise_trial.md (PR 529). No code, prompt, rubric, fingerprint, contract or persisted result changed.
- The proposal fixes the owner's nine decisions as inputs and adds its own marked definitions: a standing timeline per premise, interval rules, a derived outcome relation, a novelty field for the different condition, a complete profile table, a second derived verdict with the prerequisite check, record shapes, an options comparison (chosen: a separate opt-in stage with a fact table as a later audit layer), a compatibility section listing every place a new analysis kind would touch (the sidecar schema version must not be bumped), seven recommended implementation work items (not created) and ten open questions with recommendations.
- The evidence is six hand-picked controls classified by one rater with a reproduction script that finds every cited passage; it says nothing about how often dates matter in the corpus.

# Validation

- lrh validate reports 0 errors; git diff --check is clean on the PR range; the embedded script reproduces its output and every cited offset resolves.
- Two cold fact-check passes. The first found a conflated Vonnegut claim, a missing Sunburn premise, an unsupported 1908 date and gaps in the date rules (never-established versus speculative premises, window direction, endpoints, the profile table, the different mechanism, an understated compatibility list); the second found granularity, speculative-premise and expired-only gaps and a trailing-whitespace failure. All were fixed with the owner's approval; the final round of wording and definition fixes was checked by the author against the reviewer's cases, not by a third cold review.

# Follow-up

- Owner review of the proposal and its ten open questions, then adoption before any implementation work item.
- Recommended work items are listed in the proposal; none was created.
