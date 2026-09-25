---
execution_id: 2026_08_24_22_04_05_WI_LINGUISTICS_0005_REVIEW
prompt_id: PROMPT(AD_HOC:WI_LINGUISTICS_0005_REVIEW)[2026-08-24T21:43:24+00:00]
work_item: AD_HOC
status: landed
rerun_of: 2026_08_24_21_25_48_WI_LINGUISTICS_0005
pr: https://github.com/xenotaur/LCATS/pull/391
commit: 7ec8080b600861b9f82984306697fc2ed8e32411
agent: codex_app
instruction_source: https://github.com/xenotaur/LCATS/pull/391
session_transcript: codex-app:01a032cd-cef2-73c0-9714-b61b36ae4513
created_at: 2026-08-24T22:04:05+00:00
---

# Summary

Addressed the five unresolved automated review comments on PR #391 for
`WI-LINGUISTICS-0005`.

# Result

- Fixed unaligned-offset handling for v2 token detail. `_find_token_span` now
  returns unavailable offsets instead of fabricating cursor-based spans when a
  token cannot be aligned to the source body, covering Stanza multi-word-token
  expansions such as source `du` yielding normalized words `de` and `le`.
- Extended v2 validation to allow explicit `null` offset pairs when offsets are
  unavailable, reject partial null/int span pairs, verify sentence spans are in
  source order, and verify integer token spans are contained by their sentence
  span.
- Split empty required-string validation from type validation so empty strings
  report `empty_string` / `expected non-empty string` instead of the misleading
  `wrong_type` / `expected string` message.
- Added `sentence_records` as an explicit `SurfaceFeatures` dataclass field and
  populated it directly from `extract_surface_features`, removing the dynamic
  attribute dependency.
- Added regression tests for unavailable offsets, sentence/token span
  containment, sentence-span ordering, empty-string diagnostics, and explicit
  sentence-record exposure.

All five review comments were valid, present, and feasible; none were skipped.

# Validation

- `PATH="/Users/centaur/anaconda3/bin:$PATH" python -m unittest
  tests.analysis_tests.linguistics_test tests.analysis_tests.event_role_world_test`
  — 171 tests OK.
- `PATH="/Users/centaur/anaconda3/bin:$PATH" scripts/version tools` initially
  showed environment drift: Black `26.3.1` / Ruff `0.15.12` against the
  repository pins.
- `PATH="/Users/centaur/anaconda3/bin:$PATH" scripts/develop` — refreshed the
  editable dev install and restored Black `25.11.0` / Ruff `0.15.0`.
- `PATH="/Users/centaur/anaconda3/bin:$PATH" scripts/version tools` — LCATS
  `0.1.1.dev814+ge8e961aab.d20260824`, Python 3.11.8, Ruff 0.15.0, Black
  25.11.0, pip 23.2.1.
- `PATH="/Users/centaur/anaconda3/bin:$PATH" scripts/format --check --diff`
  first hit a sandbox-only Black multiprocessing socket `PermissionError`;
  rerun outside the sandbox exited 0 with 227 files unchanged.
- `PATH="/Users/centaur/anaconda3/bin:$PATH" scripts/lint` — Ruff passed;
  Black formatting check passed.
- `PATH="/Users/centaur/anaconda3/bin:$PATH" scripts/test` — 2147 tests OK.
  Output included expected fixture warnings and local Matplotlib/fontconfig
  cache warnings.
- `lrh validate` — 0 errors, 237 existing warnings.

# Follow-up

Run `/lrh-confirm-fixes https://github.com/xenotaur/LCATS/pull/391` to verify
the review fixes against the current diff, resolve satisfied GitHub review
threads, re-check CI, and obtain the SHA-locked merge-readiness verdict. Update
`session_transcript: pending` to a durable Codex session pointer when one is
available.
