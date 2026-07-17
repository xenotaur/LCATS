---
resolution: null
blocked_reason: null
blocked: false
id: WI-CLEAN-0022
title: Harden data/cache directory creation against dangling symlinks; add lcats clean
type: deliverable
status: proposed
priority: high
owner: unassigned
related_focus:
  - FOCUS-WORLDCON-2026
related_workstreams:
  - WS-SPECIALS-CLEANUP
related_design:
  - lcats/docs/reference/prepare-corpora-release.md
  - lcats/lcats/gatherers/downloaders.py
  - lcats/lcats/gettenberg/cache.py
forbidden_actions:
  - force_push
  - delete_branch
  - modify_data_or_corpora_contents
acceptance:
  - lcats.utils.paths.makedirs() exists and is unit-tested for all four cases -- path missing, path already a valid directory (incl. via a live symlink), path is a dangling symlink, path is blocked by a plain file
  - All five existing os.makedirs/Path.mkdir call sites for data/cache directories (downloaders.py ResourceCache.ensure(), DataGatherer.ensure() x2, gettenberg/cache.py's two module-level mkdir calls) use the new utility
  - DataGatherer.clear()'s per-entry check uses the loop variable instead of the constant parent path, with test_clear_removes_path's existing assertion unchanged
  - gettenberg/cache.py gains a symlink-safe clear function for cache/texts and cache/tmp, unit-tested
  - lcats clean CLI subcommand exists, clears data/ and cache/ contents while preserving symlinks, and is documented in --help
  - prepare-corpora-release.md's "Clear stale local state" step is updated to use lcats clean as the primary path
  - lrh validate reports 0 errors
  - scripts/test passes with new/updated coverage for all of the above
required_evidence:
  - manual_review
  - lrh_validate
  - test_output
artifacts_expected:
  - lcats/lcats/utils/paths.py
  - lcats/tests/utils_tests/paths_test.py
  - lcats/lcats/gatherers/downloaders.py
  - lcats/lcats/gettenberg/cache.py
  - lcats/lcats/analysis/corpus/clean_cli.py
  - lcats/lcats/cli.py
  - lcats/docs/reference/prepare-corpora-release.md
---

# Work Item: WI-CLEAN-0022

## Summary
Add a symlink-aware directory-creation utility (`lcats.utils.paths.makedirs()`)
to fix a real crash hit during dogfooding, fix a related dead-logic bug in
`DataGatherer.clear()`, and ship a new `lcats clean` command so users never
need shell-glob reasoning to safely clear `data/`/`cache/`.

## Problem / Context
While manually running `prepare-corpora-release.md` (WI-RELEASE-0021),
`lcats gather` crashed with `FileExistsError: 'data'` after the maintainer's
`data/` symlink was left dangling (its target directory was deleted, not
just emptied). Root-caused via live reproduction and by reading the
installed CPython `os.py` source directly: `os.makedirs`'s `ensure()` call
sites use `if not os.path.exists(path): os.makedirs(path)`, and
`os.path.exists()` returns `False` for a broken symlink (per the Python
docs), so the code proceeds to `mkdir()`, which fails with `EEXIST` because
a symlink already occupies that name. Critically, `exist_ok=True` — the
standard reflex fix — does **not** help: both `os.makedirs` and
`pathlib.Path.mkdir`'s `exist_ok` suppression is gated on
`path.isdir(name)`/`self.is_dir()`, which is also `False` for a dangling
symlink (confirmed against `os.py:229` and `pathlib.py:1125` directly).
While investigating reuse of the existing `ResourceCache.clear()` /
`DataGatherer.clear()` methods for a proposed `lcats clean` command, found
that `DataGatherer.clear()`'s per-entry file/symlink/directory check
(`downloaders.py:279-282`) checks the constant parent path instead of the
loop variable — dead logic that happens to produce its currently-tested,
intended result (removing the whole gatherer subdirectory) by accident,
worth fixing for clarity while touching this file. `gettenberg/cache.py`'s
`cache/texts`/`cache/tmp` directories (used only by `mass_quantities`) have
no `clear()` method at all today.

## Scope
- A new, unit-tested `lcats.utils.paths.makedirs()` utility distinguishing
  "doesn't exist," "already a valid directory," "dangling symlink," and
  "blocked by a plain file."
- Wiring that utility into all five existing unsafe call sites.
- A correctness (not behavior) fix to `DataGatherer.clear()`.
- A new clear function for `gettenberg/cache.py`'s two cache directories.
- A new `lcats clean` CLI subcommand and a runbook update to use it.

## Required Changes
1. Create `lcats/utils/paths.py` with a `makedirs()` function: no-op if the
   path already resolves to a real directory (symlink or not); if the path
   is a dangling symlink, recreate the symlink's target directory (`data/`
   and `cache/` are both documented, in this same runbook, as disposable
   regenerable caches, so auto-healing is consistent with their existing
   contract — the proposed default, per this WI's own Risk Notes); if the
   path is blocked by a plain file or anything else non-directory, raise a
   clear `NotADirectoryError`-style message naming the exact conflict,
   instead of letting a bare `FileExistsError` propagate.
2. Update `lcats/gatherers/downloaders.py`: `ResourceCache.ensure()`
   (line ~71) and `DataGatherer.ensure()` (lines ~204, ~208) to call
   `paths.makedirs()` instead of `os.makedirs()`.
3. Fix `DataGatherer.clear()` (lines ~272-287): change the per-entry
   `if os.path.isfile(self.path)...` checks to check `file_path` (the loop
   variable), not `self.path`. `test_clear_removes_path`'s assertion (the
   whole gatherer directory is gone afterward) must still pass unchanged.
4. Update `lcats/gettenberg/cache.py`'s module-level
   `GUTENBERG_TEXTS.mkdir(...)`/`GUTENBERG_TMP.mkdir(...)` (lines ~31, ~33)
   to use `paths.makedirs()`, and add a new `clear()`-equivalent function
   for both directories, symlink-safe by construction.
5. Create `lcats/analysis/corpus/clean_cli.py` (following the
   `promote_cli.py`/`assess_cli.py` pattern) and wire a `clean` subcommand
   into `lcats/cli.py`, clearing `data/` (all gatherers) and `cache/`
   (both cache mechanisms) via the functions above.
6. Update `lcats/docs/reference/prepare-corpora-release.md`'s "Clear stale
   local state" section to recommend `lcats clean` as the primary path,
   since by that point in the runbook `scripts/develop` has already run
   (Pre-flight precedes Clear), so `lcats` is guaranteed to be on `PATH`.

## Non-Goals
- Does not change `ResourceCache.clear()`'s existing, already-correct
  behavior.
- Does not retroactively address the maintainer's already-manually-resolved
  dangling-symlink incident.
- Does not touch the separate `lcats survey`/`lcats promote` exclusion-list
  inconsistency (tracked separately).
- Does not remove the runbook's documented `sh -c 'rm -rf ...'` glob
  commands entirely -- keep them as a fallback note for readers without
  `lcats` on `PATH` yet.

## Acceptance Criteria
- `lcats.utils.paths.makedirs()` is unit-tested for all four cases listed
  in the frontmatter `acceptance` list.
- All five call sites use the new utility; no remaining unsafe
  `os.makedirs`/`Path.mkdir` calls for these two directory trees.
- `lcats clean` clears `data/`/`cache/` contents while preserving a
  symlinked setup, verified with a symlink-backed test fixture.
- `lrh validate` reports 0 errors.

## Validation
- `scripts/version tools`
- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`

## Risk Notes
- Auto-healing a dangling symlink (recreating its target directory) is a
  real design choice, not a neutral default -- it's the right call for
  `data/`/`cache/` specifically because both are already documented,
  elsewhere in this exact runbook, as disposable regenerable caches, but
  it would be the *wrong* default for a general-purpose utility applied to
  arbitrary paths. This was flagged to the maintainer before this work item
  was written and accepted as proposed.
- `lcats clean` operates on real filesystem state; implementation and
  tests must exercise it only against temp directories, never the
  session's real `data/`/`cache/`.
