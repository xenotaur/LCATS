---
execution_id: 2026_08_23_15_12_19_WI_LINGUISTICS_0004_EXECUTE_REVIEW
prompt_id: PROMPT(AD_HOC:WI_LINGUISTICS_0004_EXECUTE_REVIEW)[2026-08-23T15:11:53+00:00]
work_item: AD_HOC
status: landed
rerun_of: 2026_08_23_06_45_42_WI_LINGUISTICS_0004
pr: https://github.com/xenotaur/LCATS/pull/376
commit: 6ed6373473b475071abfad4c89c58dc83dfb9b45
created_at: 2026-08-23T15:12:19+00:00
---

# Summary

Addressed the final Copilot review thread on PR #376 after the full-corpus
linguistics experiment was regenerated with the empty-story exclusion fix.
The review noted that the experiment README described all discovered stories
as copied before analysis, while smoke runs intentionally copy only the
selected smoke prefix.

# Result

Updated `experiments/07_linguistics_corpora/README.md` to distinguish full-run
snapshot behavior from smoke-run snapshot behavior. The README now states that
full runs copy every discovered story bucket, while smoke runs copy only the
selected `--smoke-count` prefix and record both discovered and selected counts
in `snapshot_manifest.json`.

Resolved review thread:

- https://github.com/xenotaur/LCATS/pull/376#discussion_r3837902805

# Validation

- `python experiments/07_linguistics_corpora/run_linguistics_corpora_test.py`
  passed with 10 tests.
- `gh pr checks https://github.com/xenotaur/LCATS/pull/376 --json name,state,bucket`
  reported all checks passing after the fix.

# Follow-up

No follow-up from this review round.
