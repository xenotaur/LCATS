---
execution_id: 2026_07_18_14_26_12_RUNBOOK_CACHE_CLEAN_DOC_GAP
prompt_id: PROMPT(AD_HOC:RUNBOOK_CACHE_CLEAN_DOC_GAP)[2026-07-18T14:23:01-04:00]
work_item: AD_HOC
status: landed
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/132
commit: 9c768bb3ee0d48f626b04c239bfe889a44d5c88e
created_at: 2026-07-18T14:26:12-04:00
agent: claude_app
instruction_source: user request to re-verify prepare-corpora-release.md against current code after WI-CLEAN-0022 (PR #131) merged
session_transcript: claude-app:ff20b6b0-c572-4847-9c89-034d6aa827cd
---

# Summary

The maintainer asked whether `prepare-corpora-release.md` was still fully
valid after WI-CLEAN-0022 (PR #131) merged. Re-verified every claim in the
doc against current code rather than just re-reading it; found one real
gap and fixed it.

# Result

Verified against current code (all still accurate, no changes needed):
Pre-flight commands against `lcats/README.md`'s Building section, the
`lcats gather` gatherer name list against `gatherers/main.py`'s
`GATHERERS` dict, the "most gatherers skip existing files, mass_quantities
always overwrites" claim against `downloaders.py`/`parser.py`, and every
cross-referenced doc anchor (`corpus-promotion.md#collection-name-mapping`,
the assess how-to link).

Found one real gap: step 2's description of what `lcats clean` clears
said "`cache/resources`, and `mass_quantities`'s separate
`cache/texts`/`cache/tmp`" -- three things. But PR #131's own review
(see `2026_07_18_02_20_53_WI_CLEAN_0022_IMPL_REVIEW`) extended
`gettenberg_cache.clear_all()` to also remove
`cache/gutenbergindex.db`/`cache/rdf-files.tar.bz2` (comment #6 on PR
#131), and the runbook was never updated to reflect that -- confirmed by
reading `clear_all()`'s current source directly, not from memory.

Also added a new, previously-undocumented consequence, confirmed against
`ensure_gutenberg_cache()`: clearing the Gutenberg metadata cache means
the *first* metadata lookup in the next `lcats gather mass_quantities`
rebuilds the whole RDF catalog from scratch (the code's own comment says
"may take a while, so go get a coffee or soda") -- a slow operation
distinct from and in addition to the per-story downloads the runbook
already warned about.

# Validation

- `scripts/format --check --diff` -- clean, 153 files unchanged
- `scripts/lint` -- ruff + black pass
- `scripts/test` -- 1346 tests OK (doc-only change, unaffected suite)
- `lrh validate` -- 0 errors, 26 pre-existing owner-role/orphan warnings

# Follow-up

- On merge: update this record to `landed`.
- No further known gaps in the runbook as of this check; the maintainer's
  dogfood run can proceed on the assumption the doc matches current code.
