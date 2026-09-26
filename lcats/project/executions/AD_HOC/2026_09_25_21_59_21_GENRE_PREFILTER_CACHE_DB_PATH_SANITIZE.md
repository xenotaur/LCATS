---
execution_id: 2026_09_25_21_59_21_GENRE_PREFILTER_CACHE_DB_PATH_SANITIZE
prompt_id: PROMPT(AD_HOC:GENRE_PREFILTER_CACHE_DB_PATH_SANITIZE)[2026-09-25T21:58:14+00:00]
work_item: AD_HOC
status: landed
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/448
commit: 00a23dfd9b5a7c7aa343aa84f30e277e0252934b
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/362
session_transcript: claude-app:6a2dbae2-adca-4a2a-92fe-2e95d3b2a4e0
created_at: 2026-09-25T21:59:21+00:00
---

# Summary

Fixes the root cause of a real Copilot review finding on PR #362:
`run_prefilter.py`'s `cache_readiness()` leaked the full, often absolute,
`--cache-db` path into `genre-sidecar-v1` provenance -- and from there
into promoted `corpora/*/genre.json` files.

# Result

- Changed `cache_readiness()` to store `cache_db.name` (basename only)
  instead of `str(cache_db)` in the `cache_db_path` field.
- Confirmed via repo-wide grep (twice: my own check and an independent
  cold-context self-review) that no code reads `cache_db_path` for
  anything beyond display/provenance -- no reconstruction of a real
  filesystem path from it anywhere.
- Confirmed `cache_root` (a sibling field, unchanged, still a full path)
  never flows into the promoted provenance -- only `cache_db_path` does,
  via `build_metadata_assessment()` -- so it's correctly out of scope.
- Added `test_cache_readiness_reports_basename_not_full_path`, a
  regression test that would fail under the old behavior.
- Does not touch PR #362's own already-promoted 146 files -- that PR is
  under separate review; this only prevents recurrence.

# Validation

- `python3 -m pytest experiments/05_metadata_genre_prefilter/run_prefilter_test.py`:
  58 passed.
- `black --check --diff` / `ruff check` run directly on the two touched
  files (outside `scripts/format`/`scripts/lint`'s `src/tests/tools`
  scope): clean.
- `lrh validate`: 0 errors.
- Diff-mode self-review (cold-context subagent + independent
  re-verification): no findings.

# Follow-up

- PR #362 itself still needs a human decision on whether/how to correct
  its own 146 already-promoted files (not done here, per explicit
  instruction to scope this to the script fix only).
