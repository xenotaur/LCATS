---
execution_id: 2026_08_20_22_15_11_GENRE_BALANCED_METADATA_SCAN_SELECTION_VALIDATION
prompt_id: PROMPT(WI-GENRE-0004:GENRE_BALANCED_METADATA_SCAN_SELECTION_VALIDATION)[2026-08-20T21:44:44+00:00]
work_item: WI-GENRE-0004
status: in_progress
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/322
commit: 8fa0b7869e65a78a75f2a8b84f13cd6105b557b9
agent: claude_app
instruction_source: WI-GENRE-0004
session_transcript: claude-app:b0d48070-0faf-4a35-942d-a29ec96d603a
created_at: 2026-08-20T22:15:11+00:00
---

# Summary

Implementation of `WI-GENRE-0004` via `/lrh-execute`: extend
`experiments/05_metadata_genre_prefilter/run_prefilter.py` with a
full-corpus metadata scan + genre-balanced 100-200 story selection
(`--full-scan`, free) and a real, gated Claude Opus validation pass
against just that selection (`--validate`, estimate-only unless
`--run-real-validation` is also passed).

# Result

- `run_prefilter.py`: `select_genre_balanced_rows()` (genre-grouped,
  independent from the existing collection-grouped `select_pilot_rows`),
  `build_genre_coverage()`, `run_full_scan()`, `estimate_validation_cost_usd()`,
  `run_validation()`, `build_model_assessment()`, `build_sidecar_records()`,
  `write_genre_balanced_outputs()`/`write_validation_outputs()`, and CLI
  wiring (`--full-scan`, `--target-total`, `--validate`,
  `--run-real-validation`, `--model`, with `--full-scan`/`--validate`
  enforced as mutually exclusive).
- `WI-GENRE-0004.md`: added a `## Required Changes` section (readiness
  gap found and fixed before implementation started - the item's own
  `## Scope` section had the substance but not the section name this
  repo's `lrh work-items readiness` checker requires).
- `README.md`: documents both new modes and updates "Current Boundary".
- `run_prefilter_test.py`: 33 tests total (12 new test methods across 5
  new test classes) covering selection distribution/shortfalls/
  determinism/gutenberg-cap, model-assessment agreement/disagreement/
  error cases, sidecar validity (valid + invalid), the estimate-vs-real
  cost gate (zero API calls in estimate mode, verified via mock),
  output-directory guard, and a full-corpus-scan integration test
  against a real synthetic Gutenberg cache DB.

A diff-mode `/lrh-self-review` pass before this PR's first push (own
record: `2026_08_20_22_13_43_GENRE_BALANCED_METADATA_SCAN_SELECTION_VALIDATION_SELFREVIEW`)
found and fixed one real issue: `--validate`'s real mode was missing the
`validate_output_dir()` guard the other two modes both have.

No paid API calls were made during this implementation -
`--run-real-validation` was never invoked, per `forbidden_actions`'
`run_paid_sample_before_user_go_ahead`.

# Validation

- `PYTHONPATH=lcats/src python -m pytest experiments/05_metadata_genre_prefilter/run_prefilter_test.py` - 33 passed
- `scripts/test` (full repo suite, run from `lcats/`) - 1778 tests, OK
- `black --check` / `ruff check` on changed files - clean (ran directly;
  `scripts/format`/`scripts/lint` don't cover `experiments/`)
- `lrh validate` - 0 errors, 157 pre-existing warnings
- Manual CLI smoke tests: `--full-scan` against the real corpus (no
  `--cache-db`, confirms full 1868-story scan + correct all-shortfall
  reporting), `--validate` estimate mode (confirms manifest-not-found
  refusal and zero-API-call estimate path), `--full-scan --validate`
  together (confirms mutual-exclusion CLI error)

# Follow-up

None outstanding from implementation. Proceeding to `/lrh-land` for
review-response/confirm-fixes/merge/closeout.
