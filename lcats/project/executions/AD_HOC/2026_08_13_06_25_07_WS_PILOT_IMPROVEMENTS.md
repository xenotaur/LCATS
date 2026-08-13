---
execution_id: 2026_08_13_06_25_07_WS_PILOT_IMPROVEMENTS
prompt_id: PROMPT(AD_HOC:WS_PILOT_IMPROVEMENTS)[2026-08-13T06:18:23+00:00]
work_item: AD_HOC
status: in_progress
rerun_of:
pr: https://github.com/xenotaur/LCATS/pull/295
commit: 4bae1f991dfc574f584f759293ea46c395fd710f
agent: codex_app
instruction_source: project/workstreams/proposed/WS-PILOT-IMPROVEMENTS.md
session_transcript: codex-app:019fea05-63b0-7e02-80d2-e570de36c7c3
created_at: 2026-08-13T06:25:07+00:00
---

# Summary

Create the `WS-PILOT-IMPROVEMENTS` planning node requested after
`PROP-LCATS-PILOT-IMPROVEMENTS` was captured. The workstream scopes follow-on ERW
pilot improvements behind an explicit pilot API/output stability gate, then
coordinates measured prompt-caching adoption, genre/segmentation model-tiering
adoption, opt-in Batch API design and validation, and user-facing run
ergonomics.

# Result

Added `lcats/project/workstreams/proposed/WS-PILOT-IMPROVEMENTS.md` with
`status: proposed`, `stage: designed`, related design links, exit criteria,
prior-art findings, non-goals, and open questions. The workstream intentionally
does not link work items yet; it records the expected sequencing from
`PROP-LCATS-PILOT-IMPROVEMENTS` and leaves follow-on WI creation to a later
explicit planning step.

Opened PR https://github.com/xenotaur/LCATS/pull/295 with prompt traceability
to `PROMPT(AD_HOC:WS_PILOT_IMPROVEMENTS)[2026-08-13T06:18:23+00:00]`.

# Validation

- `lrh validate`: 0 errors, 139 existing warnings
- `git diff --check`: clean

# Follow-up

- Review and land PR #295.
- After the workstream lands, create the first follow-on work item for the
  pilot API/output stability gate.
- Populate `work_items:` as scoped follow-on WIs are created and accepted.
