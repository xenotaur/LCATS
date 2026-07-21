---
execution_id: 2026_07_20_16_57_25_DOCS_CLEANUP_FOCUS_PYTHON_VERSION
prompt_id: PROMPT(AD_HOC:DOCS_CLEANUP_FOCUS_PYTHON_VERSION)[2026-07-20T16:50:39-04:00]
work_item: AD_HOC
status: landed
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/139
commit: 7848b555b15a4d4c7b0f1d0cb8baa030639e3303
created_at: 2026-07-20T16:57:25-04:00
agent: claude_app
instruction_source: ad hoc conversation — user-requested small cleanup PR closing two items flagged during the WS-DOCS closeout report
session_transcript: claude-app:e7662f75-a730-4630-9960-4a2694b28500
---

# Summary

Small ad-hoc cleanup closing two items flagged (but deliberately not fixed) during the `WS-DOCS`
closeout: retired the completed docs-cleanup priority from `current_focus.md`, and bumped the
Python version floor in `pyproject.toml`/`setup.py` to match documented reality.

# Result

- `project/focus/current_focus.md`: removed priority 3 ("Documentation cleanup (`WS-DOCS`)"),
  renumbered to 2 active priorities, adjusted title/id header and the "Why This Is Current" /
  Exit Criteria sections to match.
- `project/memory/decision_log.md`: added a retirement entry for `WS-DOCS`, matching this repo's
  existing convention (see the 2026-04-21 and 2026-07-18 entries) rather than letting the
  completed priority vanish from `current_focus.md` with no durable record.
- `pyproject.toml`: `requires-python` `>=3.6` → `>=3.10`.
- `setup.py`: `python_requires` `>=3.6` → `>=3.10`.
- `lcats/README.md` and `docs/tutorials/quickstart.md`: removed the "`pyproject.toml`/`setup.py`
  still declare `>=3.6`... that's stale" caveats — now that the packaging metadata is fixed, those
  sentences would themselves have become inaccurate if left unchanged.

Confirmed via `grep` that no other `>=3.6`/"still declare" references remain anywhere in the repo
outside the now-correct `setup.py` line.

# Validation

- `scripts/version tools` — not present in this repository (no `scripts/version` script exists,
  consistent with every prior session this workstream).
- `scripts/format --check --diff` — 153 files unchanged.
- `scripts/lint` — ruff and black both passed.
- `scripts/test` — 1346 tests, `OK`. Run in full since `pyproject.toml`/`setup.py` are packaging
  config, not just docs.
- `lrh validate` — 0 errors, 26 pre-existing warnings (unchanged from before this PR).

# Follow-up

- `session_transcript` is `pending` — update to `claude-app:<session-id>` after this session ends.
- After PR #139 merges: run `/lrh-closeout` to mark this record `landed`. This is an `AD_HOC`
  record with no linked work item to resolve.
