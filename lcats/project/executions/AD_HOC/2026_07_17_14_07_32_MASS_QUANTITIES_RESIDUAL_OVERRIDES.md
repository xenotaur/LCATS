---
execution_id: 2026_07_17_14_07_32_MASS_QUANTITIES_RESIDUAL_OVERRIDES
prompt_id: PROMPT(AD_HOC:MASS_QUANTITIES_RESIDUAL_OVERRIDES)[2026-07-17T14:03:05-04:00]
work_item: AD_HOC
status: landed
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/129
commit: b8d8854cdc6411116e8206f34262a2002efdda70
created_at: 2026-07-17T14:07:32-04:00
agent: claude_app
instruction_source: user report from step 5 (inspect) of a manual run of lcats/docs/reference/prepare-corpora-release.md
session_transcript: claude-app:ff20b6b0-c572-4847-9c89-034d6aa827cd
---

# Summary

Disposition two residual specials findings the maintainer hit at step 5
(inspect) of their first real, non-simulated run of
`prepare-corpora-release.md` (WI-RELEASE-0021), where `lcats survey`
flagged two characters but `lcats repair-specials` proposed nothing for
either. Also add an `lcats assess` pointer to the same runbook, requested
separately in the same conversation.

# Result

Diagnosed first, before writing any fix: `repair-specials` only proposes a
fix when a finding's classification is `likely_repairable`
(`repairs.py:232-233`), which only fires for the exact continuation-byte
mojibake patterns in `DEFAULT_REPAIR_RULES` (`repairs.py:69-162`, all
two-character UTF-8-decoded-as-Latin-1/Mac-Roman sequences). Neither
finding matches: Cyrillic `и` (U+0438) and `■` (U+25A0) are both classified
`review_needed` (`specials.py:264-292`), so silence was the designed
behavior, not a bug.

Fetched the actual Project Gutenberg source for both stories to determine
whether the characters are LCATS-introduced corruption or genuine upstream
content:
- "Has Anyone Here Seen Kelly?" (ebook #30086): raw text contains `иии THE
  END` verbatim; the rest of the story renders scene breaks as
  `* * * * *`.
- "Rough Beast" (ebook #48880): raw text opens with `■ The field of the
  experimental Telethink station...`; the same story renders its other,
  mid-story scene breaks as `* * * * *` too, and `■` appears exactly once.

Both are genuine upstream artifacts (almost certainly Gutenberg
transcription quirks rendering a printer's scene-break ornament), not
something `lcats gather` corrupted. `■` was already known: WI-RESIDUAL-0019's
own execution record explicitly flagged "a lone U+25A0 black square" as a
deferred "boundary/typographic artifact... candidate for a boundary-cleanup
WI." The Cyrillic finding wasn't previously catalogued anywhere (allowlist,
overrides, or prior execution records) -- likely because WI-RESIDUAL-0019's
scan was simulated over an earlier `data/` snapshot, not this literal
regeneration.

Per the maintainer's explicit direction -- trust the story authors'
structural intent (a scene break belongs there), not the transcribers'
choice of glyph -- added two per-story overrides to
`lcats/gatherers/overrides/mass_quantities.json`:
- `has_anyone_here_seen_kelly__walton`: `"иии"` -> `"* * * * *"`
- `rough_beast__aycock`: `"■"` -> `"* * * * *"`

Both normalize to the same convention each story already uses for its own
other scene breaks, rather than allowlisting the odd glyphs as-is. Added 4
tests to `tests/gatherers_tests/overrides_test.py` (presence + apply, one
pair per override), matching the existing seed-override test pattern.

Also added a new "Optional next step: quality/genre assessment" section to
`prepare-corpora-release.md`, pointing to `lcats assess` for after
promotion -- `--dry-run` first (free), the real, API-cost-incurring form
clearly marked as needing `ANTHROPIC_API_KEY` and explicit authorization,
linking to the existing assess how-to guide rather than duplicating it.

Secondary observation, not yet investigated: the maintainer's `find data/
-iname *json | wc` showed 1868 story files, but WI-RESIDUAL-0019's record
cites 1971 stories in its simulated scan -- a ~100-story gap worth a
sanity check before treating the corpus as a fully clean baseline, flagged
to the maintainer but not pursued as part of this fix.

# Validation

- `scripts/format --check --diff` -- clean, 149 files unchanged
- `scripts/lint` -- ruff + black pass
- `scripts/test` -- 1318 tests OK (4 new)
- `lrh validate` -- 0 errors, 25 pre-existing owner-role/orphan warnings
- New tests (`test_cyrillic_scene_break_override_is_present`,
  `test_cyrillic_scene_break_override_applies`,
  `test_black_square_scene_break_override_is_present`,
  `test_black_square_scene_break_override_applies`) run individually and
  pass

# Follow-up

- On merge: update this record to `landed`.
- The maintainer's dogfood run of the runbook is still in progress; this
  unblocks step 5 (inspect), not the whole run.
- The 1868-vs-1971 story-count discrepancy noted above is unresolved and
  worth a follow-up check.
- This PR (#129) and PR #128 (symlink-safety fix) both branch from
  pre-#128 `main` and touch disjoint parts of `prepare-corpora-release.md`
  (step 2 vs. the new final section) -- no conflict expected, but not
  verified by an actual merge yet since neither has landed.
