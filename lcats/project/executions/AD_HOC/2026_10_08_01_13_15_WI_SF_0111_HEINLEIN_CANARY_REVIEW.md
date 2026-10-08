---
execution_id: 2026_10_08_01_13_15_WI_SF_0111_HEINLEIN_CANARY_REVIEW
prompt_id: PROMPT(AD_HOC:WI_SF_0111_HEINLEIN_CANARY_REVIEW)[2026-10-08T01:09:15+00:00]
work_item: AD_HOC
status: landed
rerun_of: 2026_10_07_23_17_05_WI_SF_0111_HEINLEIN_CANARY
pr: https://github.com/xenotaur/LCATS/pull/483
commit: 6142046f494e51dc0d5bdd65605ceec1366947a6
created_at: 2026-10-08T01:13:15+00:00
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/483
session_transcript: claude-app:dff6f127-44db-417c-9b1e-0f962af4c00a
---

# Summary

Fix round for PR 483 (WI-SF-0111 implementation), inlined from /lrh-land: one failing-CI diagnosis and two open bot comments, all three present and valid. The stop-work condition (any failing CI check) fired and the work item owner explicitly amended it to proceed with all three fixes.

# Result

- CI failure (coverage and both test jobs): a loopback-table case I added expected an IPv4-mapped loopback address to be non-loopback, which depends on the Python patch release (ipaddress.is_loopback answered False on local 3.11.8 and True on CI's 3.11.16 and 3.11.17). Fixed by normalizing IPv4-mapped IPv6 addresses to their IPv4 part, so the result is deterministic, flipping that expectation, and adding hex-mapped and public-mapped cases. The real function's source was checked on 3.11.8, 3.12.13 and 3.14.6 with identical results.
- Fixed (Codex P2): manifest_snapshot.json was written with a plain write_text, so a dangling symlink at that path would be followed to a file outside the output root. It is now written through the runner's symlink-safe atomic writer, shared as _write_text_atomic, and a symlink at that path is refused. Reproduced before fixing.
- Fixed (Copilot): the no-expectations early return skipped the existing-snapshot check, so a resume over a manifest that dropped every expectation bypassed the guard. The check now runs first. Reproduced before fixing.
- Skipped: none.

# Validation

- black 25.11.0 and ruff 0.15.0 (CI pins) clean; scripts/test 2465 tests OK; lrh validate 0 errors; git diff --check clean.
- Mutation checks: removing the mapped-address normalization, the safe writer, the symlink refusal, or the early-return check each fails a test.

# Follow-up

- Threads are resolved by /lrh-confirm-fixes, not this round.
- CI and a fresh substitute self-review must cover the fix commit before the merge gate.
- The local conda Python (3.11.8) differs from CI's 3.11.16 and 3.11.17; recheck interpreter-dependent behavior against a newer interpreter.
- session_transcript is pending and is resolved at closeout.
