---
execution_id: 2026_10_15_22_47_04_WI_GETTENBERG_0005_ROUTING
prompt_id: PROMPT(WI-GETTENBERG-0005:WI_GETTENBERG_0005_ROUTING)[2026-10-15T22:46:17+00:00]
work_item: WI-GETTENBERG-0005
status: in_progress
rerun_of:
pr: https://github.com/xenotaur/LCATS/pull/516
commit: f0cbb30f6d9764aa24211d5c9a69fdf8a9c6369f
created_at: 2026-10-15T22:47:04+00:00
agent: codex_app
instruction_source: project/work_items/proposed/WI-GETTENBERG-0005.md
session_transcript: codex-app:01a13653-87a6-7743-b734-7440a42ee1be
---

# Summary

WI0005 A22: qualify official URL conventions, implement pure configurable routing
and route-aware MIME selection, with offline tests and Diataxis documentation.

# Result

Independently written GutenbergRoutes maps concrete main/generated paths and17
published aliases. Source identity and versioned route policy are retained.
Explicit capability filtering keeps an unsupported preferred resource from hiding
a usable alternative. No default mirror, network grant or fallback probing.
See the development log and route-qualification checkpoint for pinned sources.

# Validation

Canonical scripts/test:2886 tests pass in75.963s; format272 files unchanged;
lint passes. LRH0 errors/351 existing warnings; WI prompt-ready; diff clean.
Cold independent review:408 Gettenberg tests, no actionable findings. All seven
frozen source/test/doc hashes unchanged. See
[qualification](../../development/evidence/gettenberg-routing-20261015/qualification.json).
Hosted reviews and exact-head CI remain pending; no integration acceptance yet.

# Follow-up

Operational default-mirror qualification, CLI/consumer migration and human main
promotion remain separate. This execution stays in_progress and WI proposed.
