---
execution_id: 2026_09_26_23_55_01_WORLDCON_SPIKE_INCREMENTAL_SAFETY_PR389_SELFREVIEW
prompt_id: PROMPT(AD_HOC:WORLDCON_SPIKE_INCREMENTAL_SAFETY_PR389_SELFREVIEW)[2026-09-26T23:54:56+00:00]
work_item: AD_HOC
status: landed
rerun_of:
pr: https://github.com/xenotaur/LCATS/pull/389
commit: 5598d024c3f3b37910bbd166a7e13aa2bc9ce7be
session_transcript: codex-app:01a02338-d9c7-7313-8ed5-fb9c1643bef1
created_at: 2026-09-26T23:55:01+00:00
---

# Summary

PR-mode cold-context self-review of PR #389 at commit
`086f8122a3ed407cd5c181fe0e07dfc468c8c209`, used as the substitute review
signal while GitHub review metadata was unavailable to the invoking session.

# Result

The review found one P2 reproducibility issue: `_merge_duplicate()` sorts
`EvidenceProvenance` values using source, chunk, raw ID, and backend, but not
`normalization_notes` (`src/lcats/analysis/science_fiction/evidence.py:607-617`).
When provenance entries share those four sort-key fields but differ in
normalization notes, set iteration can determine their order. The resulting
evidence serialization is included in the effective checkpoint fingerprint
(`src/lcats/analysis/science_fiction/pipeline.py:44-68`).

The invoking session independently reproduced the ordering difference with
identical inputs under multiple `PYTHONHASHSEED` values. The reviewer therefore
did not consider PR #389 safe to merge as-is. This report-only self-review did
not apply fixes, push commits, resolve threads, or merge the PR.

GitHub PR metadata, hosted diff, comments, reviews, and checks could not be
read because `gh` intermittently failed to connect to `api.github.com`. The
review used the locally available `origin/main...HEAD` diff instead.

# Validation

- `git diff --check origin/main...HEAD`: passed.
- `lrh validate`: passed with 0 errors and 334 pre-existing warnings.
- Independent reproduction under multiple `PYTHONHASHSEED` values: confirmed
  nondeterministic provenance ordering.
- The cold reviewer reported the local full suite as 2,345 tests passed; this
  session did not rerun the full suite during the report-only pass.

# Follow-up

- Route the P2 finding through the normal PR fix-forward/review workflow.
- Add a deterministic provenance sort key including normalization notes and a
  regression test covering equal primary sort keys with differing notes.
- Re-run the relevant science-fiction tests and the required validation before
  another landing attempt.
