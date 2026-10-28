---
execution_id: 2026_10_15_01_01_21_WI_GETTENBERG_0005_ACQUISITION_CORE
prompt_id: PROMPT(WI-GETTENBERG-0005:WI_GETTENBERG_0005_ACQUISITION_CORE)[2026-10-15T01:00:16+00:00]
work_item: WI-GETTENBERG-0005
status: landed
rerun_of:
pr: https://github.com/xenotaur/LCATS/pull/510
commit: b4ec4c452ed178dd62472af9f1a46b44e70ce485
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

Final68 focused resource tests and canonical scripts/test's 2744 tests pass
(74.632seconds). Format/lint pass,258 files. The first local cold review, first
automatic Codex/Copilot rounds and a second cold boundary review found real defects;
all were reproduced and repaired with regressions. Final independent signal at
01:52:34 UTC matches all11 source/design/doc hashes;68 resource and50 lifecycle
tests pass. No external ebook/catalog download or CI/dependency changes.

[Final qualification](../../development/evidence/gettenberg-acquisition-core-20261015/hosted-review-repairs.json)
and [review/acceptance mapping](../../development/evidence/gettenberg-acquisition-core-20261015/review.md).
Earlier qualification.json preserves its original historical snapshot. Initial95%
statement coverage predates repairs and is not a claim about final source.
Native review records are linked via rerun_of and PR510; all remain nonterminal.

# Follow-up

Open and qualify the internal child PR; inspect the first automatic review and
exact-head checks before coordinator integration. No main promotion. Remaining
WI-0005 obligations retain their original criteria; this record is in_progress.
