---
execution_id: 2026_07_11_21_24_30_WI_SPECIALS_CLEANUP_ITEMS_REVIEW
prompt_id: PROMPT(AD_HOC:WI_SPECIALS_CLEANUP_ITEMS_REVIEW)[2026-07-11T16:43:29-04:00]
work_item: AD_HOC
status: in_progress
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/118
commit: 7e9c825
created_at: 2026-07-11T21:24:30-04:00
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/118
session_transcript: claude-app:57066b9f-0531-43f0-a6e1-c96446ed1b15
---

# Summary

Address the open review comment on PR #118 (five WS-SPECIALS-CLEANUP work
items) via `lrh request review_response`. One P2 comment from
chatgpt-codex-connector (r3564985701): the WI-RULES-0016 dry-run evidence
command scans raw story JSON, but both gather write paths call `json.dump`
without `ensure_ascii=False`, so body defects are stored as `\uXXXX` escapes
and raw-text scans match nothing.

`rerun_of` is empty: PR #118 was created by the `/lrh-work-item` skill flow,
which does not produce a primary execution record.

# Result

Comment verified against code and data (raw file contains `√`, decoded
body contains `√`; `repairs_cli.py:41` reads raw text; `downloaders.py:247`
and `parser.py:955` dump with ASCII escapes) and fixed in commit 7e9c825:

- WI-RULES-0016 — Scope and Required Changes now include extending
  `lcats repair-specials` to scan decoded story JSON bodies; acceptance and
  Validation specify decoded-body evidence; Risk Notes record the
  false-negative trap.
- WI-RESIDUAL-0019 — Validation bullet notes the dependency on the
  WI-RULES-0016 decoding extension.

No comments skipped.

# Validation

- `scripts/format --check --diff` — fails only on
  `lcats/gettenberg/metadata.py`, untouched by this branch (diff vs
  origin/main is markdown-only). Environment version skew: repo pins
  black==25.11.0 (PR #117), local has 26.3.1. Not a regression.
- `scripts/lint` — ruff: all checks passed.
- `scripts/test` — OK (full suite).
- `lrh validate` — 0 errors, 24 pre-existing owner-role warnings.
- `lrh work-items readiness` — all five new items remain prompt_ready: yes.

# Follow-up

- Local environment should reinstall pinned tools (`scripts/develop`) to
  clear the black 26.3.1 vs 25.11.0 skew.
- On merge: set this record to `landed` with the merge commit.
