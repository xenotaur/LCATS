---
execution_id: 2026_10_17_19_33_10_GETTENBERG_DEFAULT_PROFILE
prompt_id: PROMPT(WI-GETTENBERG-0007:GETTENBERG_DEFAULT_PROFILE)[2026-10-17T19:32:41+00:00]
work_item: WI-GETTENBERG-0007
status: in_progress
rerun_of:
pr: https://github.com/xenotaur/LCATS/pull/521
commit: dca61929
created_at: 2026-10-17T19:33:10+00:00
agent: codex_app
instruction_source: project/development/gettenberg-pilot-charter.md
session_transcript: codex-app:01a13653-87a6-7743-b734-7440a42ee1be
---

# Summary

Implement the qualified default-source profile at CLI/workflow boundaries for
WI-GETTENBERG-0007 under the approved bounded coordinator charter.

# Result

Shared pure source resolvers select the published RDF archive and PGLAF root pair
only when setup or selected metadata-dependent collections need them. Explicit
archives/URLs and complete root pairs override defaults; half pairs fail. Library
preparation/routes and default offline policy remain explicit. Ready catalogs and
outputs are reused, first setup requires approval, and offline prohibits requests.
Dry-run shows selected endpoints, origins and approval without requests/writes.
Curated-only runs never resolve catalog sources. Refresh/rebuild authority unchanged.

Prior-art check is present in WI0007; this extends existing preparation and
acquisition components rather than introducing another client or lifecycle.
Updated how-to/reference documentation and executable offline CLI fixtures.
No live Gutenberg request, corpus mutation, dependency removal or main promotion.

# Validation

Canonical 2978 tests passed in 86.153 seconds; focused 59 tests passed. Black
checked 284 files; Ruff/format passed. LRH validation: 0 errors, 351 existing
warnings; WI readiness yes. Cold independent review found no actionable defects
and independently ran the same 59 focused tests successfully. Coordinator
rechecked pristine CLI previews and verifies source hashes before publication. Manual documented gather/setup
previews selected matching URLs and created no cache. No live client or full
archive acquisition qualification is claimed.

# Follow-up

Host review and exact-head CI are required before internal integration. Native
records remain nonterminal until human main promotion. WI0008 retains broader
legacy consumer/dependency migration; full snapshot and corpus qualification
remain separately bounded work.
