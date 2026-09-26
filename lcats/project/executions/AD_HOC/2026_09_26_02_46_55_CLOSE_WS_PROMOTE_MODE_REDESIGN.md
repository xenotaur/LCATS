---
execution_id: 2026_09_26_02_46_55_CLOSE_WS_PROMOTE_MODE_REDESIGN
prompt_id: PROMPT(AD_HOC:CLOSE_WS_PROMOTE_MODE_REDESIGN)[2026-09-26T02:45:03+00:00]
work_item: AD_HOC
status: in_progress
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/449
commit: 3c277708
agent: claude_app
instruction_source: project/workstreams/resolved/WS-PROMOTE-MODE-REDESIGN.md
session_transcript: claude-app:6a2dbae2-adca-4a2a-92fe-2e95d3b2a4e0
created_at: 2026-09-26T02:46:55+00:00
---

# Summary

Closes `WS-PROMOTE-MODE-REDESIGN`, having independently re-verified all
6 exit criteria against current `main` (not inferred from prose).

# Result

- Moved `WS-PROMOTE-MODE-REDESIGN.md` from `project/workstreams/active/`
  to `project/workstreams/resolved/`, `status: resolved`,
  `stage: closed`.
- Verified each exit criterion directly: bare `lcats promote` refuses
  (dry-run); `insert`/`upsert` require a registered validator by default
  with `--allow-unvalidated` as the only override (dry-run); the
  narrowed registry-scoping criterion (corrected in PR #430) accurately
  reflects `replace`'s orphan guard's legitimate
  `sidecar_validators.registered_filenames()` dependency; `replace`
  refuses by default on an orphaned sidecar with
  `--allow-orphaned-sidecar-deletion` as the override (dry-run);
  `insert`/`upsert` can source from a live `--source` directory scan
  (dry-run); all 4 work items `status: resolved` and `lrh validate`
  reports 0 errors.
- Hit a real self-inflicted git mistake mid-commit: a `git add` call
  included the already-moved `active/` path alongside the new
  `resolved/` path, which failed atomically and silently dropped the
  frontmatter edit from the first commit -- caught by checking
  `git log -1 --stat` immediately after (showed 0 insertions/deletions
  on a supposedly substantive change), corrected with a second, honest
  follow-up commit rather than amending.

# Validation

- `lrh validate`: 0 errors.
- Re-ran `git show HEAD:...` after the fix commit to confirm the real
  frontmatter change landed, not just trusting the commit message.

# Follow-up

- None. This closes out the workstream this entire session's promote-mode
  work has been building toward.
