---
execution_id: 2026_08_29_05_58_17_WI_PROMOTE_0100_SCAN_SOURCING_REVIEW
prompt_id: PROMPT(AD_HOC:WI_PROMOTE_0100_SCAN_SOURCING_REVIEW)[2026-08-29T05:58:11+00:00]
work_item: AD_HOC
status: landed
rerun_of: 2026_08_29_05_21_31_WI_PROMOTE_0100
pr: https://github.com/xenotaur/LCATS/pull/411
commit: fafcb3d4297fa79ed4c64786fb87c1f6b81e0eb7
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/411
session_transcript: claude-app:6a2dbae2-adca-4a2a-92fe-2e95d3b2a4e0
created_at: 2026-08-29T05:58:17+00:00
---

# Summary

Review-response round for PR #411 (`WI-PROMOTE-0100` implementation).
The PR's automatic first-push review surfaced one real P2 finding,
raised independently by both `copilot-pull-request-reviewer` and
`chatgpt-codex-connector`.

# Result

- **Unintended keyword-only breakage of `allow_unvalidated`/`dry_run`
  (P2, fixed)**: adding `scan_source` as a new keyword-only parameter
  placed `*` before it at the start of the parameter list, which also
  made the pre-existing `allow_unvalidated`/`dry_run` parameters
  keyword-only — a backward-incompatible change for any caller passing
  them positionally under the signature documented before this item
  (e.g. `promote_sidecar_insert(manifest, dest, "genre", True, True)`
  would have raised `TypeError`). Independently confirmed present on
  the pre-fix diff via `inspect.signature()`. Fixed by moving `*` to
  immediately before `scan_source` only, in both
  `promote_sidecar_insert()` and `promote_sidecar_upsert()` — the same
  fix both reviewers independently recommended.
- Added `test_allow_unvalidated_and_dry_run_remain_positional_or_keyword`,
  a regression test exercising the exact positional-call pattern the
  finding described.

# Validation

- `scripts/version tools`: ruff/black drifted mid-session again (black
  26.3.1 vs. pinned 25.11.0); re-pinned via `pip install -q
  "ruff==0.15.0" "black==25.11.0"`, re-verified.
- `scripts/format --check --diff`: clean.
- `scripts/lint`: clean.
- `scripts/test` (targeted): `tests/analysis_tests/promote_test.py` —
  91 tests, all pass.
- `python3 -c "import inspect; ..."`: confirmed `promote_sidecar_insert`'s
  post-fix signature has `allow_unvalidated`/`dry_run` as
  `POSITIONAL_OR_KEYWORD` and only `scan_source` as `KEYWORD_ONLY`.

# Follow-up

- None outstanding from this round. Proceeding to confirm-fixes next to
  verify the fix against the current diff and resolve the review
  threads.
