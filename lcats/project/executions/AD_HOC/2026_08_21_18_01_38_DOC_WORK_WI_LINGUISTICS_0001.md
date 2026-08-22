---
execution_id: 2026_08_21_18_01_38_DOC_WORK_WI_LINGUISTICS_0001
prompt_id: PROMPT(AD_HOC:DOC_WORK_WI_LINGUISTICS_0001)[2026-08-21T17:50:38+00:00]
work_item: AD_HOC
status: landed
rerun_of:
pr: https://github.com/xenotaur/LCATS/pull/336
commit: b1f14a1a7731ae3fd250182e0678a8b59e3a9cd8
created_at: 2026-08-21T18:01:38+00:00
agent: codex_app
instruction_source: WI-LINGUISTICS-0001
session_transcript: pending
---

# Summary

Update LCATS user-facing documentation after `WI-LINGUISTICS-0001` landed the
standalone linguistic-feature extraction infrastructure.

# Result

Opened PR https://github.com/xenotaur/LCATS/pull/336.

Updated documentation:

- Added `docs/reference/linguistics-sidecar.md`, a reference page for
  `linguistics-sidecar-v1`, `linguistics-token-detail-v1`, and
  `linguistics-run-summary-v1`.
- Linked the new schema reference from `docs/index.md`,
  `docs/reference/README.md`, `docs/reference/cli-commands.md`, and
  `docs/how-to/run-linguistics.md`.
- Updated `docs/explanation/story-bucket-layout.md` to include
  `linguistics.json` as a now-real sibling sidecar example.

No stale docs were identified that needed a notice. The existing
`lcats linguistics` how-to and CLI reference from PR 325 were accurate; this
doc-work pass filled the missing reference-level schema page.

# Validation

- `PATH=/Users/centaur/anaconda3/bin:/usr/bin:/bin:/usr/sbin:/sbin scripts/develop`
  -- refreshed the editable install for this worktree.
- `PATH=/Users/centaur/anaconda3/bin:/usr/bin:/bin:/usr/sbin:/sbin scripts/version tools`
  -- LCATS `0.1.1.dev633+g14067f53f.d20260821`, Python `3.11.8`, Ruff
  `0.15.0`, Black `25.11.0`, pip `23.2.1`.
- `PATH=/Users/centaur/anaconda3/bin:/usr/bin:/bin:/usr/sbin:/sbin scripts/format --check --diff`
  -- 194 files would be left unchanged.
- `PATH=/Users/centaur/anaconda3/bin:/usr/bin:/bin:/usr/sbin:/sbin scripts/lint`
  -- Ruff passed; Black formatting check passed.
- `PATH=/Users/centaur/anaconda3/bin:/usr/bin:/bin:/usr/sbin:/sbin scripts/test`
  -- ran 1813 tests, OK.
- `lrh validate` -- 0 errors, 164 warnings. Warnings are existing owner and
  instruction-source warnings on current `main`.

# Follow-up

Run `/lrh-review-response https://github.com/xenotaur/LCATS/pull/336`, then
`/lrh-confirm-fixes https://github.com/xenotaur/LCATS/pull/336`, and after
merge run `/lrh-closeout https://github.com/xenotaur/LCATS/pull/336`.
