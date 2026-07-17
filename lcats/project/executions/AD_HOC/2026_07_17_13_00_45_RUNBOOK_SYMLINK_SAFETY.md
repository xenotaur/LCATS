---
execution_id: 2026_07_17_13_00_45_RUNBOOK_SYMLINK_SAFETY
prompt_id: PROMPT(AD_HOC:RUNBOOK_SYMLINK_SAFETY)[2026-07-17T12:58:41-04:00]
work_item: AD_HOC
status: landed
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/128
commit: c97e3e2331ea1c1664fdc85bca76c6684b24ee84
created_at: 2026-07-17T13:00:45-04:00
agent: claude_app
instruction_source: user report from manually running lcats/docs/reference/prepare-corpora-release.md
session_transcript: claude-app:ff20b6b0-c572-4847-9c89-034d6aa827cd
---

# Summary

Fix two issues in `prepare-corpora-release.md` (WI-RELEASE-0021, merged
PR #127) reported by the maintainer while actually running the runbook by
hand: the clear-state command breaks a symlinked `data/`/`cache/` setup,
and the "fully from-network run" note misses a second, mass_quantities-only
cache directory.

# Result

Fixed in commit 47f902b, both confirmed empirically (not just by reading
source) before writing the fix:

- Symlink-destroying clear command -- the PR #127 review fix
  (`rm -rf data && mkdir -p data`) was itself the regression: verified in
  a scratch dir that `rm -rf <symlink>` unlinks the symlink (leaving its
  target untouched) and the following `mkdir -p` then creates a *new real
  directory* in its place, silently orphaning the old target. Replaced
  with `sh -c 'rm -rf data/*'`, verified correct on populated, empty, and
  missing `data/` alike -- it clears contents without ever touching the
  directory/symlink entry itself. Also verified the reviewer's original
  zsh concern is real and specifically what `sh -c` fixes: a bare
  `zsh -c 'rm -rf data/*'` on an empty/missing dir aborts with
  `zsh: no matches found` (exit 1); `sh` has no such default option. (A
  `find -L data -mindepth 1 -delete` alternative was tried and rejected --
  BSD/macOS find refuses it outright: "`-delete: forbidden when symlinks
  are followed`".)
- Missing `cache/texts` (P2-equivalent, from a live dogfood run rather
  than a PR review): confirmed `mass_quantities` caches raw Gutenberg text
  through a second, independent cache -- `lcats/gettenberg/cache.py:30`
  (`GUTENBERG_TEXTS = GUTENBERG_ROOT / "texts"`), used only by
  `api.py:37`'s `load_etext()`, which only `parser.py:1403`
  (mass_quantities' own pipeline) calls. The other 11 gatherers use
  `downloaders.py`'s `ResourceCache` -> `cache/resources` exclusively and
  never touch `cache/texts`. Added `cache/texts` to the optional
  from-network-run note alongside `cache/resources`.

Also confirmed while investigating: no `lcats clean` CLI command exists
(`scripts/clean` only removes Python build artifacts --
`lcats/scripts/clean:1-6`), but `ResourceCache.clear()` /
`DataGatherer.clear()` (`downloaders.py:108-122,262-276`) already exist
and are already symlink-safe (they `os.listdir()` and delete children
individually, never touching the root). Not wired to any CLI command
today -- noted as a possible follow-up, not done as part of this fix.

# Validation

- `scripts/format --check --diff` -- clean, 149 files unchanged
- `scripts/lint` -- ruff + black pass
- `scripts/test` -- 1314 tests OK
- `lrh validate` -- 0 errors, 25 pre-existing owner-role/orphan warnings
- Manually verified (in a scratch directory, not asserted from reading
  source alone): symlink survives `sh -c 'rm -rf data/*'` on populated,
  empty, and missing directories; `zsh -c 'rm -rf data/*'` aborts on an
  empty/missing directory; `find -L ... -delete` is refused by BSD find

# Follow-up

- On merge: update this record to `landed`.
- Possible future work item: wire `ResourceCache.clear()` /
  `DataGatherer.clear()` up to a real `lcats clean` command, and extend
  the same clearing to `gettenberg/cache.py`'s `texts`/`tmp` directories
  (which have no `clear()` method today) -- would remove the need for any
  shell-glob reasoning in the runbook at all. Not started; the maintainer
  deferred this to keep the current dogfood run moving.
- The maintainer's dogfood run of the runbook (the actual point of
  WI-RELEASE-0021) is still in progress; this fix unblocks it, not
  concludes it.
