---
execution_id: 2026_07_28_17_49_16_WI_PACKAGING_0036_REVIEW_FIXES
prompt_id: PROMPT(AD_HOC:WI_PACKAGING_0036_REVIEW_FIXES)[2026-07-28T17:49:10-04:00]
work_item: AD_HOC
status: in_progress
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/178
commit: e5c42e4b
created_at: 2026-07-28T17:49:16-04:00
---

# Summary

Applied automated-review fixes to PR #178 (creation of `WI-PACKAGING-0036`,
a planning-only work item — no primary execution record existed since
`/lrh-work-item` mints none). This record serves as the primary record for
the whole PR.

# Result

Reviewed 3 automated comments (Copilot + Codex) against the actual source
files rather than applying blindly:

1. **Copilot — `work_items/README.md` Proposed Items index incomplete.**
   Confirmed via grep (`status: proposed` files not listed:
   `WI-ASSESS-0031`, `WI-EVENT-0032`, `WI-EVENT-0033`). Valid — added all
   three to the index.
2. **Copilot — `.parent` in the `secrets.py` replacement example is
   wrong.** Checked `src/lcats/utils/secrets.py`'s own header comment:
   `.secrets/` lives at the repo root, one level *above* the directory
   containing `pyproject.toml`. `find_pyproject_root(__file__)` (per the
   WI's own stated contract) returns that `pyproject.toml` directory, so
   `.parent` is required to reach the repo root and matches the existing
   `parents[4]` behavior exactly. Determined this finding to be factually
   incorrect — left the example unchanged.
3. **Codex (P1) — non-editable install risk.** Valid: the WI's original
   Required Changes item 2 computed `_DEFAULT_SECRETS_DIR` via an
   unguarded module-level call to `find_pyproject_root`, which would raise
   `FileNotFoundError` at `import lcats.utils.secrets` time for a wheel or
   `pip install .` install outside the checkout — breaking imports
   entirely instead of preserving the current silent no-op behavior.
   Updated Required Changes, Risk Notes, and Validation sections to
   require a guarded fallback (catch the not-found case, set
   `_DEFAULT_SECRETS_DIR` to `None`) and a non-editable-install validation
   step.

# Validation

- `lrh validate`: 0 errors, 47 warnings (all pre-existing, unrelated).
- No code changes in this PR (planning-artifact-only); no test suite run
  required.

# Follow-up

None. `WI-PACKAGING-0036` remains `status: proposed`; a future
implementation PR will pick it up and apply the fallback design captured
here.

CHAIN-NOTE: cycles=1; stops=0; gates=[merge]; friction=none; note="one bot finding (Copilot .parent) was factually wrong and rebutted rather than applied"
