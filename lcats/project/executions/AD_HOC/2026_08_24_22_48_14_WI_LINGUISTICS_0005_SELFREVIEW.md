---
execution_id: 2026_08_24_22_48_14_WI_LINGUISTICS_0005_SELFREVIEW
prompt_id: PROMPT(AD_HOC:WI_LINGUISTICS_0005_SELFREVIEW)[2026-08-24T22:48:07+00:00]
work_item: AD_HOC
status: landed
rerun_of: 2026_08_24_21_25_48_WI_LINGUISTICS_0005
pr: https://github.com/xenotaur/LCATS/pull/391
commit: 7ec8080b600861b9f82984306697fc2ed8e32411
agent: codex_app
instruction_source: skill:lrh-self-review --pr https://github.com/xenotaur/LCATS/pull/391
session_transcript: codex-app:01a032cd-cef2-73c0-9714-b61b36ae4513
created_at: 2026-08-24T22:48:14+00:00
---

# Summary

PR-mode substitute `/lrh-self-review` pass for PR #391 after the
`_CONFIRM` record commit moved the PR head to
`049b30137c5efc8e2cc84d485df7ecdcf886b57e` and no automatic reviewer
response had landed for that exact commit.

# Result

- Dispatched cold-context subagent `01a035ee-ed78-7d51-a85e-ab60b767a09b`
  with only the PR URL, exact head SHA, repository path, and PR-mode
  report-only review instructions.
- Findings: 3.
- Top finding, directly re-verified by the invoking session: `sentence_records`
  was a new `SurfaceFeatures` dataclass field and `SurfaceFeatures.to_dict()`
  still used `dataclasses.asdict()`, causing ERW `surface_features`
  serialization to include internal sentence records. A local probe confirmed
  `sentence_records` appeared in `features.to_dict().keys()`.
- Additional findings, directly re-verified: v2 offset documentation still
  said offsets were always integers even though unavailable offsets are emitted
  as `null`; the PR range contained trailing whitespace in newly added
  execution-record frontmatter.
- Fixes applied by the invoking session after re-verification:
  `SurfaceFeatures.to_dict()` now serializes only the established public
  surface-feature fields while retaining typed `sentence_records` for internal
  consumers; the v2 sidecar docs now describe `integer or null` offsets and
  validation of integer-or-null offset pairs; trailing whitespace was removed
  from the affected execution records.
- Added a regression test asserting `sentence_records` remains populated on
  `SurfaceFeatures` but is not emitted by `SurfaceFeatures.to_dict()`.
- Findings were routed through the `/lrh-confirm-fixes` Step 8 substitute
  review loop and fixed in the follow-up commit after this record.

# Validation

- `PATH="/Users/centaur/anaconda3/bin:$PATH" python -m unittest
  tests.analysis_tests.linguistics_test tests.analysis_tests.event_role_world_test`
  — 172 tests OK.
- `PATH="/Users/centaur/anaconda3/bin:$PATH" scripts/version tools` — LCATS
  `0.1.1.dev814+ge8e961aab.d20260824`, Python 3.11.8, Ruff 0.15.0, Black
  25.11.0, pip 23.2.1.
- `git diff --check` — clean for the working-tree fix-forward diff.
- `PATH="/Users/centaur/anaconda3/bin:$PATH" scripts/format --check --diff`
  — 227 files unchanged.
- `PATH="/Users/centaur/anaconda3/bin:$PATH" scripts/lint` — Ruff passed;
  Black formatting check passed.
- `PATH="/Users/centaur/anaconda3/bin:$PATH" scripts/test` — 2148 tests OK.
  Output included expected fixture warnings and local Matplotlib/fontconfig
  cache warnings.
- `lrh validate` — 0 errors, 237 existing warnings.

# Follow-up

Commit and push the substitute-review fixes plus this record, then repeat the
post-push confirm-fixes Step 8 checks for CI, unresolved threads, and
REVIEW-LANDED coverage on the new exact head.
