---
execution_id: 2026_10_18_08_25_28_GETTENBERG_CORPUS_REPAIR
prompt_id: PROMPT(WI-GETTENBERG-0010:GETTENBERG_CORPUS_REPAIR)[2026-10-18T08:24:54+00:00]
work_item: WI-GETTENBERG-0010
status: in_progress
rerun_of: 2026_10_18_05_18_55_GETTENBERG_QUALIFICATION
pr: https://github.com/xenotaur/LCATS/pull/524
commit: de8c326ad0fab90e8f25c8813057ce2ad1eb4e36
created_at: 2026-10-18T08:25:28+00:00
agent: codex_app
instruction_source: project/development/gettenberg-corpus-repair-plan.md
session_transcript: codex-app:01a13653-87a6-7743-b734-7440a42ee1be
---

# Summary

Renewed bounded run to repair narrative preservation during WI0010 qualification,
continuing PR524. Human grant: another two-to-three-hour run; scoped coordinator
adapter and existing worker ceilings retained. Start 08:24:26 UTC; target
10:24:26 and hard stop 11:24:26 UTC. Prior-art and readiness checks passed.

# Result

Stopped during investigation after a budget-enforcement failure. One read-only
worker was dispatched around 08:25 UTC with a 15-minute assignment allowance and
08:41 UTC deadline. At 09:15:41 UTC the coordinator verified that the deadline had
passed, then interrupted the worker. Conservatively charge 51 worker minutes,
exceeding the 45-minute cumulative allowance. This is elapsed dispatch occupancy,
including waits, not a claim of 51 minutes of active computation. The cause of the
wall-clock gap is not established; do not attribute it to model/tool performance.
The coordinator missed timely enforcement and must not silently renew the grant.

No product, test, experiment runner, cache or canonical corpus changes were made.
Only grant/runlog/execution/repair-plan documentation changed. Native status stays
in_progress; the original corpus blocker and PR524's no-integration gate remain.
The following are preliminary worker observations, not accepted dispositions:
35401 loses opening narrative in the new path; 50103 becomes footer-only; 70645
loses substantial opening narrative in the legacy path. The other five cases were
reported as editorial/whitespace differences without established narrative loss.
Coordinator inspected original starts/ends of these sources but did not complete
an independent eight-case acceptance audit. No new comparison report was produced.

# Validation

Read-only preflight: clean managed worktree at de8c326a, PR524 open, fresh watched
skills, invalid persistent skip consent left unchanged, WI0010 prompt-ready.
Original unrelated checkout remained untouched. No implementation tests or bulk
qualification were run; prior 2,945-test evidence must not be described as a new
run. Checkpoint documentation receives lrh validate and git diff --check only.

# Follow-up

Resume the focused repair under a new grant. Prefer coordinator-led implementation
and defer delegation until a small independent-review packet exists. Check real
UTC before dispatch and after every tool boundary; worker instructions should
require an immediate start-time check and no work after an expired deadline.
An enforceable watchdog or scheduler would improve this pilot; it is not available
merely because a deadline is written in a prompt. No new LRH tooling was built.
