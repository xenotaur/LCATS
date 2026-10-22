---
execution_id: 2026_10_18_15_51_56_GETTENBERG_NARRATIVE_REPAIR
prompt_id: PROMPT(WI-GETTENBERG-0010:GETTENBERG_NARRATIVE_REPAIR)[2026-10-18T15:51:17+00:00]
work_item: WI-GETTENBERG-0010
status: in_progress
rerun_of: 2026_10_18_08_25_28_GETTENBERG_CORPUS_REPAIR
pr: https://github.com/xenotaur/LCATS/pull/524
commit:
agent: codex_app
instruction_source: project/development/gettenberg-corpus-repair-plan.md
session_transcript: codex-app:01a13653-87a6-7743-b734-7440a42ee1be
created_at: 2026-10-18T15:51:56+00:00
---

# Summary

Bounded opening-prefix narrative-preservation repair candidate for PR524.
Start15:50:56 UTC, target16:50:56, hard stop17:20:56. Continued existing branch
335855c0 under the approved pilot coordinator adapter. Prior-art/demand is the
existing gatherer/qualification repair; no external dependency or new work item.

# Result

Implemented contiguous body-span selection with versioned provenance, authored
narrative/publication regressions, documentation and source-anchored experiment.
All eight reviewed narrative spans survive; seven publish in temporary buckets.
42640 still fails chapter eligibility. Corpus acceptance remains blocked.

First cold review found one P2 editorial-prefix deletion issue. Coordinator
reproduced and repaired it. Second review attempt reported entry after its deadline
and stopped; it did not verify the repair. Conservative dispatch occupancy31 minutes
exceeded the20-minute allowance. Development stopped at16:33 UTC; final validation
and checkpoint only. Cause of scheduling gap/active-worker time is not established.

# Validation

Initial canonical run2,959 tests passed (97.219s); later15 experiment tests passed.
Final canonical checkpoint:2,963 tests passed in79.988 seconds; package and
all13 experiment runners passed format/lint; LRH0 errors/351 existing warnings;
git diff --check passed. Raw final test log and hashes are archived with results.
Eight-case report: all spans preserved, seven publications pass, one rejection;
exit1 deliberately retained, not relabeled as success. Initial corpus report covers
1,659 inputs (1,646 compared,13 refused);1,642 differences,31 changed eligibility
outcomes. It predates the editorial repair and is not final-candidate qualification.

Evidence: experiments/10_gettenberg_qualification/results/gettenberg-narrative-20261018/.
No network acquisition or original cache/corpus mutation. Source hashes of final
case audit match current files. No fresh wheel or final full-corpus replay claimed.

# Follow-up

Independent final repair/runner review, metadata-aware editorial/chapter handling,
full difference dispositions, final corpus/wheel qualification and exact-head hosted
checks remain. No internal merge, main promotion or native terminal closeout.
