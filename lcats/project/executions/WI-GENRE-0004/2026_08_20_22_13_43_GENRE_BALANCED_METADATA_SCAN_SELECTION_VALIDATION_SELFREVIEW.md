---
execution_id: 2026_08_20_22_13_43_GENRE_BALANCED_METADATA_SCAN_SELECTION_VALIDATION_SELFREVIEW
prompt_id: PROMPT(WI-GENRE-0004:GENRE_BALANCED_METADATA_SCAN_SELECTION_VALIDATION_SELFREVIEW)[2026-08-20T22:13:37+00:00]
work_item: WI-GENRE-0004
status: in_progress
rerun_of: 
pr: 
commit: 6965b64b56acf48fa4091fca9ec8fdb3eec722e0
agent: claude_app
instruction_source: WI-GENRE-0004
session_transcript: claude-app:b0d48070-0faf-4a35-942d-a29ec96d603a
created_at: 2026-08-20T22:13:43+00:00
---

# Summary

Diff-mode `/lrh-self-review` pass, dispatched from `/lrh-implement` Step
7.5 before this PR's first push (`gh pr create`), per
`WI-DELIBERATE-MODEL-INVOCATION`'s permanent trigger-point design.
`rerun_of` left empty by design — no primary record exists yet at
diff-mode dispatch time.

# Result

Dispatched a cold-context `general-purpose` subagent (no session memory)
with `git diff origin/main -- experiments/05_metadata_genre_prefilter/
lcats/project/work_items/proposed/WI-GENRE-0004.md` (1200 lines) and the
WI's Summary/Acceptance Criteria/Required Changes/`forbidden_actions` for
orientation.

**One real finding, independently re-verified before fixing:**
`_run_validate_mode()` (the one code path that writes real, billed
`genre-sidecar-v1` records) had no `validate_output_dir()` guard, unlike
`run()`/`run_full_scan()` which both call it before writing anything.
Re-verified directly: grepped for `validate_output_dir(` call sites,
confirmed none near `_run_validate_mode`. This contradicted the WI's own
`write_corpus_sidecars`/`promote_sidecars` `forbidden_actions` and the
README's "Current Boundary" claim - a wrong `--output` in the real
validation path could have written into `corpora/`/`data/`.

Fixed (commit `6965b64b`): added the same guard at the top of
`_run_validate_mode()`. Also added the direct `run_validation()` test
coverage the same review flagged as missing (previously only exercised
indirectly through its helper functions).

Four other checked claims (zero-API-calls estimate path,
`story_path`-to-real-path resolution before `assess_story()`, every
sidecar record's real schema validity, `select_genre_balanced_rows()`'s
independence from the existing pilot selection) were all confirmed
accurate on direct inspection - no fix needed for those.

# Validation

- `PYTHONPATH=lcats/src python -m pytest
  experiments/05_metadata_genre_prefilter/run_prefilter_test.py` - 33
  passed (31 before this fix's 2 new tests).
- `black --check` / `ruff check` on both changed files - clean.
- `scripts/test` (full repo suite) - 1778 tests, OK.
- `lrh validate` - 0 errors, 157 pre-existing warnings.

# Follow-up

None. Proceeding to `/lrh-implement` Step 8 (`gh pr create`) - findings
fixed either way per Decision 4, the PR opens regardless.
