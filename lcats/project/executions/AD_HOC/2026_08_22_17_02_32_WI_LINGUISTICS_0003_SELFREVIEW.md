---
execution_id: 2026_08_22_17_02_32_WI_LINGUISTICS_0003_SELFREVIEW
prompt_id: PROMPT(AD_HOC:WI_LINGUISTICS_0003_SELFREVIEW)[2026-08-22T17:02:26+00:00]
work_item: AD_HOC
status: landed
rerun_of:
pr: https://github.com/xenotaur/LCATS/pull/356
commit: 0a39ea83e993dc928ef70c2778622038e11c1b14
created_at: 2026-08-22T17:02:32+00:00
agent: codex_app
instruction_source: prompt://lrh-self-review diff-mode WI-LINGUISTICS-0003
session_transcript: pending
---

# Summary

Ran the required diff-mode LRH self-review for `WI-LINGUISTICS-0003` before
opening the implementation PR.

# Result

The independent cold-context review found two issues:

- P2: The duplicate-target guard changed default beside-story behavior for
  repeated story inputs. I independently re-verified the finding by inspecting
  `runner.run()` and confirmed the guard ran even when `output_root` was not
  set.
- P3: Redirected `--existing validate` behavior was implemented but lacked a
  focused test.

Both findings were fixed in the working tree. Duplicate-target detection now
applies only when `output_root` is active, preserving default beside-story
existing-output semantics. Added coverage for default duplicate story inputs
and redirected validate stale-output behavior.

# Validation

- `PATH=/Users/centaur/anaconda3/bin:/usr/bin:/bin:/usr/sbin:/sbin python -m unittest tests.analysis_tests.linguistics_test`
  -> OK, 35 tests.

# Follow-up

Continue the primary `/lrh-execute WI-LINGUISTICS-0003` flow: run canonical
validation, commit the implementation and self-review record, open the PR, and
create the primary execution record.
