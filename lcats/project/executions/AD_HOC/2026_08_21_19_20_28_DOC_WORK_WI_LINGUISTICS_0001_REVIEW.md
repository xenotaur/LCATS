---
execution_id: 2026_08_21_19_20_28_DOC_WORK_WI_LINGUISTICS_0001_REVIEW
prompt_id: PROMPT(AD_HOC:DOC_WORK_WI_LINGUISTICS_0001_REVIEW)[2026-08-21T19:16:04+00:00]
work_item: AD_HOC
status: landed
rerun_of: 2026_08_21_18_01_38_DOC_WORK_WI_LINGUISTICS_0001
pr: https://github.com/xenotaur/LCATS/pull/336
commit: b1f14a1a7731ae3fd250182e0678a8b59e3a9cd8
agent: codex_app
instruction_source: https://github.com/xenotaur/LCATS/pull/336
session_transcript: pending
created_at: 2026-08-21T19:20:28+00:00
---

# Summary

Address PR #336 schema-reference review comments for the standalone
linguistics documentation update.

# Result

- Documented that `story_path`, `input.source_path`, and fingerprint behavior
  preserve the runner invocation spelling rather than canonicalizing paths.
- Clarified when run-summary `detail_path` is present and when existing-sidecar
  validation failures may omit it.
- Replaced vague token-detail wording with the exact normalized token record
  fields, types, and head-index semantics.

# Validation

- `scripts/version tools` reported LCATS `0.1.1.dev633+g14067f53f.d20260821`,
  Python `3.11.8`, Ruff `0.15.0`, Black `25.11.0`, and pip `23.2.1`.
- `scripts/format --check --diff` passed after rerunning outside the sandbox for
  Black multiprocessing socket access.
- `scripts/lint` passed.
- `scripts/test` passed: 1813 tests OK.
- `lrh validate` passed: 0 errors, 164 pre-existing warnings.

# Follow-up

- Run `/lrh-confirm-fixes https://github.com/xenotaur/LCATS/pull/336`.
