---
execution_id: 2026_10_15_01_01_21_WI_GETTENBERG_0005_ACQUISITION_CORE
prompt_id: PROMPT(WI-GETTENBERG-0005:WI_GETTENBERG_0005_ACQUISITION_CORE)[2026-10-15T01:00:16+00:00]
work_item: WI-GETTENBERG-0005
status: in_progress
rerun_of:
pr:
commit:
created_at: 2026-10-15T01:01:21+00:00
agent: codex_app
instruction_source: project/work_items/proposed/WI-GETTENBERG-0005.md
session_transcript: codex-app:01a13653-87a6-7743-b734-7440a42ee1be
---

# Summary

Run gettenberg-20261015-core: 60-minute target, 75-minute hard stop,
00:59:27–02:14:27 UTC. Coordinator-approved scoped plan under the human charter
renewal. Base bd2998a8, main 2f14e4e8; child branch
codex/gettenberg-acquisition-core, intended PR base codex/gettenberg-acquisition.
No main promotion, native WI resolution or persistent consent changes authorized.

# Result

Implement explicit-URL acquisition and original-byte cache under WI-0005:
request/policy/result records, read-only planning, offline verified reuse,
bounded streaming/retries/redirects, persistent request serialization/cooldowns,
immutable no-clobber body/receipt publication and shared retained archive storage.
A private adapter reuses the qualified lifecycle filesystem/SQLite primitives;
no network is introduced into catalog construction. Reference/how-to docs cover
implemented behavior and limitations. Prior-art check is present in the WI;
this extends the approved redesign, not a duplicate replacement project.

Remaining WI scope: automatic Gutenberg routing/selection, refresh/304 behavior,
strict text/container decoding and catalog-manifest receipt composition. No claim
of whole-WI completion. Source data and historical measurements are unchanged.
Small official-source checkouts were inspected, not vendored or executed.

# Validation

58 focused tests pass with ResourceWarning errors; canonical scripts/test passes
2734 tests in 76.017 seconds. Format/lint pass (258 Python files), LRH validation
has zero errors, and WI readiness is clean. Only local network fixtures were used.
Independent cold review found four P2 issues; coordinator directly reproduced the
top finding, applied all four repairs with regressions, and obtained a clean
same-assignment recheck at 01:30:17 UTC on the exact current source hashes.

Evidence: [qualification](../../development/evidence/gettenberg-acquisition-core-20261015/qualification.json)
and [review/acceptance mapping](../../development/evidence/gettenberg-acquisition-core-20261015/review.md).
Native review record:
2026_10_15_01_29_09_WI_GETTENBERG_0005_ACQUISITION_CORE_SELFREVIEW.
The initial 95% statement-coverage measurement predates repairs and is not claimed
as a measurement of the final source. Tests and review are separate evidence.

# Follow-up

Open and qualify the internal child PR; inspect the first automatic review and
exact-head checks before coordinator integration. No main promotion. Remaining
WI-0005 obligations retain their original criteria; this record is in_progress.
