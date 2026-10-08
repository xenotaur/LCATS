---
execution_id: 2026_10_07_23_09_27_WI_LINGUISTICS_0014_REVIEW
prompt_id: PROMPT(AD_HOC:WI_LINGUISTICS_0014_REVIEW)[2026-10-07T23:09:23+00:00]
work_item: AD_HOC
status: in_progress
rerun_of: 2026_09_29_06_49_17_WI_LINGUISTICS_0014_REVIEW
pr: https://github.com/xenotaur/LCATS/pull/472
commit: c039fafb
created_at: 2026-10-07T23:09:27+00:00
---

# Summary

Address the open review findings on the tokenization-repair implementation.
The batch contained four distinct findings; two reviewer comments were
duplicates of the same backend-support and diagnostic issues.

# Result

Implemented and committed the review fixes as `0b6096e4`:

- Added diagnostics for apostrophe-plus-punctuation chains such as
  `thirst'--_he`.
- Refused repaired runs that target the historical results directory.
- Rejected `repaired-v1` for `fake` and `stanza`, which do not implement it.
- Validated diagnostic object fields, statuses, spans, and token indices.
- Added regression coverage for all four findings.

The implementation and CI-formatting commits are ready to push to PR 472.
No merge or closeout action has been performed.

# Validation

- Focused linguistics tests: 66 passed.
- Focused experiment tests: 44 passed.
- Full test suite: 2,377 passed.
- `lrh validate`: 0 errors, 341 pre-existing warnings.
- `git diff --check`: passed.
- Black diagnostic check on all changed files: passed.
- `scripts/version tools`: environment warning only; installed tooling is
  from another checkout.
- `scripts/format --check --diff` and `scripts/lint`: blocked by the local
  tool-version guard (Black 26.5.1 vs required 25.11.0; Ruff 0.16.2 vs
  required 0.15.0).

# Follow-up

Push the formatting correction, then run confirm-fixes against the new PR
head. The historical audit packet remains untouched.
