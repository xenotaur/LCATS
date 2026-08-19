---
execution_id: 2026_08_13_18_38_46_WI_LLM_0066_REFERENCE_SHAPE_FIX_REVIEW
prompt_id: PROMPT(AD_HOC:WI_LLM_0066_REFERENCE_SHAPE_FIX_REVIEW)[2026-08-13T18:22:26+00:00]
work_item: AD_HOC
status: landed
rerun_of:
pr: https://github.com/xenotaur/LCATS/pull/299
commit: 679965c1592641b08f4e596ecad1e5069a75991f
created_at: 2026-08-13T18:38:46+00:00
agent: codex_app
instruction_source: https://github.com/xenotaur/LCATS/pull/299
session_transcript: codex-app:019fe9db-cb22-7ee3-8629-28dc3d9a87ec
---

# Summary

Address the Copilot review thread on PR #299 during the `/lrh-land` chain.
The reviewer noted that malformed reference-comparison rows that are not JSON
objects produced the same diagnostic as object rows missing `story_id`.

# Result

- Verified the checkout matched PR #299 branch
  `codex/wi-llm-0066-reference-shape-fix` at
  `6a6ca101a893e6336d019c9392f6c9ff447b28e9` before editing.
- Fetched one unresolved review thread from
  `copilot-pull-request-reviewer`:
  `PRRT_kwDOKlhIbM6ZCkE3`.
- Classified the finding as present, valid, and feasible.
- Split `_records_by_story()` validation so non-object records raise
  `record N is not a JSON object`, while object rows missing `story_id`
  keep the existing `record N is missing story_id` diagnostic.
- Added regression coverage for both malformed reference-row shapes.
- No primary execution record existed for PR #299, so `rerun_of:` is left
  empty per the no-primary path.

# Validation

- `PYTHONPATH=src PATH=/Users/centaur/anaconda3/envs/LCATS/bin:$PATH scripts/version tools`
  - LCATS 0.1.1.dev522+ga2431ff12.d20260813, Python 3.11.9, Ruff 0.15.0,
    Black 25.11.0.
- `PYTHONPATH=src PATH=/Users/centaur/anaconda3/envs/LCATS/bin:$PATH python -m unittest tests/experiment_tests/run_census_test.py`
  - Passed; 17 tests OK.
- `PYTHONPATH=src PATH=/Users/centaur/anaconda3/envs/LCATS/bin:$PATH scripts/format --check --diff`
  - Passed; 187 files would be left unchanged.
- `PYTHONPATH=src PATH=/Users/centaur/anaconda3/envs/LCATS/bin:$PATH scripts/lint`
  - Passed.
- `PYTHONPATH=src PATH=/Users/centaur/anaconda3/envs/LCATS/bin:$PATH scripts/test`
  - Passed; 1723 tests OK.
- `PYTHONPATH=src PATH=/Users/centaur/anaconda3/envs/LCATS/bin:$PATH lrh validate`
  - Passed before this record was written; 0 errors, 141 existing warnings.

# Follow-up

- Re-run `/lrh-confirm-fixes` on PR #299, resolve the satisfied review
  thread, and continue the `/lrh-land` chain.
