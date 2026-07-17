---
execution_id: 2026_07_17_15_55_52_MASS_QUANTITIES_RESIDUAL_OVERRIDES_REVIEW
prompt_id: PROMPT(AD_HOC:MASS_QUANTITIES_RESIDUAL_OVERRIDES_REVIEW)[2026-07-17T15:55:16-04:00]
work_item: AD_HOC
status: landed
rerun_of: 2026_07_17_14_07_32_MASS_QUANTITIES_RESIDUAL_OVERRIDES
pr: https://github.com/xenotaur/LCATS/pull/129
commit: b8d8854cdc6411116e8206f34262a2002efdda70
created_at: 2026-07-17T15:55:52-04:00
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/129
session_transcript: claude-app:ff20b6b0-c572-4847-9c89-034d6aa827cd
---

# Summary

Address four review comments on PR #129 (the mass_quantities residual
overrides + `lcats assess` pointer), all from the new "Optional next step"
section: one P2 from chatgpt-codex-connector, three from
copilot-pull-request-reviewer, reducing to two distinct issues (wrong
`corpora/` path, wrong relative link depth).

# Result

Both fixed in commit ed2368a, both reproduced live before fixing (not just
reasoned about):

- Wrong `corpora/` path (3 comments, 1 distinct issue) -- the new section
  states its working directory as `lcats/`, but `corpora/` is a sibling of
  `lcats/` at the repo root, not under it. Reproduced exactly as the
  reviewer described: `lcats assess corpora/ --genre "science fiction"
  --dry-run` run from `lcats/` prints `warning: directory does not exist:
  corpora/` then exits 0 with "No JSON files found" -- a silent no-op that
  looks successful. `lcats assess ../corpora/ ...` from the same directory
  correctly discovers real files. Fixed both example commands (dry-run and
  real-run) to use `../corpora/`, with a sentence explaining why (sibling
  of `lcats/`, not under it).
- Wrong link depth (1 comment) -- the how-to link
  `../lcats/analysis/corpus/README.md` was copy-pasted from
  `docs/index.md`'s own working link without adjusting for
  `prepare-corpora-release.md` living one directory deeper
  (`docs/reference/`, not `docs/`). From `docs/reference/`, `../` only
  reaches `docs/`, so the link resolved to the nonexistent
  `docs/lcats/analysis/...`. Verified the correct target
  (`lcats/lcats/analysis/corpus/README.md`) exists on disk, and confirmed
  `../../lcats/analysis/corpus/README.md` resolves to it via a normpath
  check.

No comments skipped.

# Validation

- `scripts/format --check --diff` -- clean, 149 files unchanged
- `scripts/lint` -- ruff + black pass
- `scripts/test` -- 1318 tests OK (doc-only change, unaffected suite)
- `lrh validate` -- 0 errors, 25 pre-existing owner-role/orphan warnings
- Reproduced the `corpora/` bug live (silent "No JSON files found") and
  confirmed the `../corpora/` fix actually discovers files, before and
  after the edit
- Confirmed the link-depth fix resolves to a real file via a Python
  `os.path.normpath`/`os.path.exists` check, not just by reasoning about
  directory levels

# Follow-up

- On merge: update this record and the primary
  `2026_07_17_14_07_32_MASS_QUANTITIES_RESIDUAL_OVERRIDES` record to
  `landed`.
- Unchanged from the primary record: the maintainer's dogfood run of the
  runbook is still in progress; the 1868-vs-1971 story-count discrepancy
  noted there remains unresolved.
