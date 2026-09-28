---
execution_id: 2026_09_28_19_57_46_WI_LINGUISTICS_0013_AUDIT_DISPLAY_SECTIONS
prompt_id: PROMPT(AD_HOC:WI_LINGUISTICS_0013_AUDIT_DISPLAY_SECTIONS)[2026-09-28T19:57:38+00:00]
work_item: AD_HOC
status: in_progress
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/458
commit: 7a657fb4377a57e16a590dfe02f9f3cb83fce983
created_at: 2026-09-28T19:57:46+00:00
agent: codex_app
instruction_source: https://github.com/xenotaur/LCATS/pull/458
session_transcript: codex-app:01a032cd-cef2-73c0-9714-b61b36ae4513
---

# Summary

Update the experiment-local interactive POS audit display so each record is
easier to scan while preserving the existing input and ledger semantics.

# Result

Implemented the requested display changes:

- added a separator before each record;
- included the current disposition in the record header;
- grouped fields under `Entry`, `Status`, `Guidance`, and `Input`;
- kept display values derived from the current row and ledger entry; and
- added regression coverage for cross-record display-state isolation.

# Validation

- `python -m unittest discover -s experiments/09_rich_linguistics_genre_sample -p 'audit_pos_test.py'` — 32 passed
- `python -m black --check experiments/09_rich_linguistics_genre_sample/audit_pos.py experiments/09_rich_linguistics_genre_sample/audit_pos_test.py` — passed
- `python -m ruff check experiments/09_rich_linguistics_genre_sample/audit_pos.py experiments/09_rich_linguistics_genre_sample/audit_pos_test.py` — passed
- `git diff --check` — passed

# Follow-up

No deferred implementation work.
