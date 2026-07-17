---
execution_id: 2026_07_17_14_12_37_RUNBOOK_SYMLINK_SAFETY_REVIEW
prompt_id: PROMPT(AD_HOC:RUNBOOK_SYMLINK_SAFETY_REVIEW)[2026-07-17T14:09:53-04:00]
work_item: AD_HOC
status: landed
rerun_of: 2026_07_17_13_00_45_RUNBOOK_SYMLINK_SAFETY
pr: https://github.com/xenotaur/LCATS/pull/128
commit: c97e3e2331ea1c1664fdc85bca76c6684b24ee84
created_at: 2026-07-17T14:12:37-04:00
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/128
session_transcript: claude-app:ff20b6b0-c572-4847-9c89-034d6aa827cd
---

# Summary

Address four review comments on PR #128 (the runbook symlink-safety fix):
one P2 from chatgpt-codex-connector, three from
copilot-pull-request-reviewer, reducing to two distinct issues (dotfile
gap, code-span formatting).

# Result

Both fixed in commit a6abb11, confirmed against a live test before fixing:

- Dotfile gap (4 comments, 1 distinct issue) -- confirmed live: `data/*`
  does not match dotfile entries (`.DS_Store`, `.ipynb_checkpoints/`,
  etc.), so the clear step could leave stale hidden files behind that
  `lcats survey`'s recursive `path.rglob("*.json")` discovery
  (`discovery.py:65`) and `lcats promote`'s top-level directory scan
  (`promote.py:201-203`) would still pick up, despite the runbook claiming
  a clean slate. Replaced the two-glob commands
  (`rm -rf data/*` and the single-collection form) with the standard
  three-glob idiom `data/* data/.[!.]* data/..?*` (dotfiles included,
  `.`/`..` excluded), still wrapped in `sh -c '...'` since zsh aborts with
  `no matches found` if *any one* of the three globs has nothing to match
  (e.g. a directory with only dotfiles, or none at all) -- verified this
  exact scenario live: a directory containing only a dotfile aborts under
  bare `zsh -c` but clears correctly under `sh -c`. Also verified the fix
  preserves a symlinked `data/`, removes nested hidden directories, and is
  a no-op on empty/missing directories.
- Code-span formatting (1 comment) -- the `cache/resources`/`cache/texts`
  clearing note had the command split across two separate inline code
  spans, making it easy to copy only half. Joined into one
  `` `rm -rf cache/resources cache/texts` `` span.

No comments skipped.

# Validation

- `scripts/format --check --diff` -- clean, 149 files unchanged
- `scripts/lint` -- ruff + black pass
- `scripts/test` -- 1314 tests OK (doc-only change, unaffected suite)
- `lrh validate` -- 0 errors, 25 pre-existing owner-role/orphan warnings
- Manually verified in a scratch directory (not asserted from reading
  source alone): three-glob pattern clears dotfiles, nested hidden dirs,
  and regular files while preserving the symlink; a bare `zsh -c` with the
  same globs aborts on a dotfile-only directory while `sh -c` does not

# Follow-up

- On merge: update this record and the primary
  `2026_07_17_13_00_45_RUNBOOK_SYMLINK_SAFETY` record to `landed`.
- Unchanged from the primary record: the maintainer's dogfood run of the
  runbook is still in progress.
