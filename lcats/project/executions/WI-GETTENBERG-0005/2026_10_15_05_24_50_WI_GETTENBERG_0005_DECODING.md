---
execution_id: 2026_10_15_05_24_50_WI_GETTENBERG_0005_DECODING
prompt_id: PROMPT(WI-GETTENBERG-0005:WI_GETTENBERG_0005_DECODING)[2026-10-15T05:03:20+00:00]
work_item: WI-GETTENBERG-0005
status: in_progress
rerun_of:
pr: https://github.com/xenotaur/LCATS/pull/512
commit:
created_at: 2026-10-15T05:24:50+00:00
agent: codex_app
instruction_source: project/work_items/proposed/WI-GETTENBERG-0005.md
session_transcript: codex-app:01a13653-87a6-7743-b734-7440a42ee1be
---

# Summary

WI-GETTENBERG-0005 A18/A19 under the human-approved bounded decoding run.
Start 05:02:55 UTC, 45-minute target, 60-minute hard stop. Integration base
c1c9a3e6f6399e421eae40c75a38efaf3f78d7ba; child codex/gettenberg-offline-decoding
for codex/gettenberg-acquisition. No main promotion or whole-WI resolution.

# Result

resources.decode_text accepts bytes or a verified SourceArtifact and returns
immutable strict plain text/HTML markup with original/payload hashes, encoding
authority, diagnostics and versioned derivation identity. Explicit encoding/BOM/
declaration precedence, bounded gzip/ZIP, independent inflated length/CRC checks,
container safety and strict errors preserve originals without network, extraction
writes or asset fetching. How-to and reference documentation include exercised
examples and honest per-stage resource-limit semantics.

# Validation

Canonical scripts/test: 2818 tests pass in 69.921 seconds; 54 focused decoder tests.
Format/lint pass; LRH 0 errors / 351 existing warnings; readiness yes; diff check
and new-doc links/fences pass. The persisted acquisition→decoding test prohibits
sockets and verifies original compressed bytes and all cache mtimes stay unchanged.
One cold independent reviewer found one P2; coordinator reproduced both parser
exceptions, repaired the typed boundary with three regression fixtures and received
a clean recheck. All 13 source/test/doc hashes match the independent review.
[Qualification evidence](../../development/evidence/gettenberg-decoding-20261015/qualification.json).

# Follow-up

PR512 targets the integration branch. Observe first hosted review rounds and
require passing exact-head CI before internal integration. Native records remain
in_progress and WI proposed until human-approved main delivery. Conditional refresh,
catalog receipt composition, qualified automatic routes and gatherer migration
remain outside this run. No external data download or persistent policy change.
