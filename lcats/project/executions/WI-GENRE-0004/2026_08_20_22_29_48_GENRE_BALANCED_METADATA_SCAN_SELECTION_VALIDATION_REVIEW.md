---
execution_id: 2026_08_20_22_29_48_GENRE_BALANCED_METADATA_SCAN_SELECTION_VALIDATION_REVIEW
prompt_id: PROMPT(WI-GENRE-0004:GENRE_BALANCED_METADATA_SCAN_SELECTION_VALIDATION_REVIEW)[2026-08-20T22:29:39+00:00]
work_item: WI-GENRE-0004
status: in_progress
rerun_of: 2026_08_20_22_15_11_GENRE_BALANCED_METADATA_SCAN_SELECTION_VALIDATION
pr: https://github.com/xenotaur/LCATS/pull/322
commit: de4f8b5a30f2b845feded080c57d56b84db6e812
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/322
session_transcript: claude-app:b0d48070-0faf-4a35-942d-a29ec96d603a
created_at: 2026-08-20T22:29:48+00:00
---

# Summary

Automatic first-push review landed on PR #322 (Codex + Copilot, 5 open
threads) within ~5.5 minutes. All 5 addressed.

# Result

1. **P1 (Codex)**: `estimate_validation_cost_usd()`'s default per-story
   token averages (2500/400) were invented placeholders, not the real
   measured values the docstring claimed. Independently re-verified via
   `experiments/04_genre_census/results/census_sample_summary.json`
   (268,975 input / 8,310 output tokens over 20 stories, $4.657875) -
   confirmed the finding's math exactly. Fixed: defaults now 13,449/416
   (the real per-story averages).
2. **P2 (Codex) + duplicate (Copilot)**: `select_genre_balanced_rows()`'s
   `target_total // 8` silently dropped the remainder (`--target-total
   100` selected only 96). Fixed: deterministic remainder distribution
   (first N genres in `TARGET_GENRES`' own fixed order get one extra
   story) so `selected_count` matches `target_total` exactly when enough
   candidates exist.
3. **P2 (Codex)**: `run_validation()`'s summary only reported aggregate
   agreement, not per-genre - could hide one genre's poor coverage
   behind seven good ones, exactly the gap balanced validation exists to
   measure. Fixed: new `build_agreement_by_genre()`, added as
   `agreement_by_genre` in the summary.
4. **(Copilot)**: `--model`'s help text said "for --validate" but is also
   used by `--full-scan`'s cost-estimate preview. Fixed: clarified help
   text to name both.

Added regression tests for all four fixes (remainder distribution,
cost-estimate defaults matching the real measured sample, per-genre
agreement both as a focused unit test and in the end-to-end real-run
test). README updated to document the real cost-estimate basis and the
per-genre agreement breakdown.

# Validation

- `PYTHONPATH=lcats/src python -m pytest experiments/05_metadata_genre_prefilter/run_prefilter_test.py` - 36 passed (33 before this round's 3 new tests)
- `scripts/test` (full repo suite) - 1781 tests, OK
- `black --check` / `ruff check` - clean
- `lrh validate` - 0 errors, 157 pre-existing warnings

# Follow-up

None. All 5 threads addressed; proceeding to confirm-fixes.
