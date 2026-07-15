---
execution_id: 2026_07_11_02_04_11_PIN_BLACK_FORMATTER
prompt_id: PROMPT(AD_HOC:PIN_BLACK_FORMATTER)[2026-07-09T22:09:17-04:00]
work_item: AD_HOC
status: landed
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/117
commit: d4e627389f0b9841a7e81c81b0bbd74eafbc03b1
created_at: 2026-07-11T02:04:11-04:00
agent: claude_app
instruction_source: project/executions/AD_HOC/2026_07_09_16_30_56_WS_SPECIALS_CLEANUP_REVIEW.md
session_transcript: claude-app:f79d5a90-a5ec-4d48-8fd3-7341db24125e
---

# Summary

Fix `scripts/format --check --diff` failing on a clean checkout of main: the
unpinned `black` in `pyproject.toml` installed Black 26.3.1, whose
hugging-parens style disagrees with the repo's committed formatting in
`lcats/lcats/gettenberg/metadata.py`. Follow-up flagged by the PR #116 review
record; instructed ad hoc in this session. The `prompt_id` timestamp
approximates session start from the implementation commit's author date; this
record was created at closeout, after merge.

# Result

Three Black versions were in play: CI pinned `black==25.11.0` in
`.github/workflows/lint.yml` (green on main), pre-commit pinned `24.10.0`,
and local dev floated to 26.3.1. Chose pinning over reformatting because CI's
pin is the source of truth and Black 25.11.0/24.10.0 both reject the 26-style
output (the pre-commit hook actively reverted a trial reformat mid-commit).

Landed in PR #117 (merge commit d4e6273):

- `lcats/pyproject.toml` — pin `black==25.11.0` in the `test` and `dev`
  extras.
- `.pre-commit-config.yaml` — bump the black hook rev from 24.10.0 to
  25.11.0 to match CI.
- No code reformatted.

# Validation

- Verified Black 25.11.0 in a scratch venv leaves all 141 files unchanged
  before pinning.
- After `scripts/develop` (env black now 25.11.0): `scripts/format --check
  --diff` — 141 files unchanged; `scripts/lint` — ruff and black checks pass;
  `scripts/test` — 1248 tests OK.

# Follow-up

- Local conda env's black was downgraded 26.3.1 → 25.11.0 by the pin; this is
  the intended state but affects other repos sharing that env.
- `ruff` remains unpinned in `pyproject.toml` while CI pins `ruff==0.15.0` —
  same skew class as this bug; candidate for a follow-up pin.
