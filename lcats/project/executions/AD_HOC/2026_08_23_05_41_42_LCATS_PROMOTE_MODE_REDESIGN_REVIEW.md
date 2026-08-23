---
execution_id: 2026_08_23_05_41_42_LCATS_PROMOTE_MODE_REDESIGN_REVIEW
prompt_id: PROMPT(AD_HOC:LCATS_PROMOTE_MODE_REDESIGN_REVIEW)[2026-08-23T05:39:10+00:00]
work_item: AD_HOC
status: in_progress
rerun_of: 2026_08_23_05_21_06_LCATS_PROMOTE_MODE_REDESIGN
pr: https://github.com/xenotaur/LCATS/pull/369
commit: d1318e64700f1aa981b13f9fddc8a4374b53c227
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/369
session_transcript: claude-app:6a2dbae2-adca-4a2a-92fe-2e95d3b2a4e0
created_at: 2026-08-23T05:41:42+00:00
---

# Summary

Review-response round for PR #369 (`PROP-LCATS-PROMOTE-MODE-REDESIGN` +
`WS-PROMOTE-MODE-REDESIGN`). The PR's automatic first-push review
surfaced 2 real findings.

# Result

- **Citation error (Copilot, fixed)**: the proposal cited `specials.py:172`
  as where `--allow-smart` is defined; that line is `is_allowed()`, a
  function that consumes the flag's value, not its definition. Verified
  independently via `grep` before fixing: the real flag definitions are
  at `cli.py:169-171` and a second copy at `specials_cli.py:60`. Fixed in
  both places the citation appeared (Decision 4's rationale and the
  Cross-References section).
- **Registry scope under-specified (Codex, P2, fixed)**: Decision 5 and
  the workstream's exit criterion only named `genre.json`/
  `linguistics.json` as registry examples. Verified independently: a
  third kind (`scenes.json`) is already recognized by `promote.py`'s
  `_SIDECAR_REQUIRED_KEYS`, and a fourth (`linguistics.tokens.json`) is
  already produced and validated by `linguistics/sidecar.py`'s own
  `validate_token_detail()`. As written, the proposal's own Decisions 4
  and 6 wouldn't actually hold for the two omitted kinds. Fixed: Decision
  5 now requires all four currently-produced kinds to register together,
  with an explicit rationale for why omitting any breaks the proposal's
  own safety claims; the workstream's exit criterion now names all four.
- No scope creep: both fixes are corrections to the existing design
  artifacts, not new design decisions requiring re-litigation.

# Validation

- `lrh validate`: targeted check on both modified files reports 0
  errors.
- Manual re-read of both fixed sections against the actual review
  comments to confirm each fix addresses exactly what was raised.

# Follow-up

- None outstanding from this round. Proceeding to `/lrh-confirm-fixes`
  next to verify the fixes against the current diff and resolve the
  review threads.
