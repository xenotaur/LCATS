---
execution_id: 2026_10_17_15_18_34_GETTENBERG_DEFAULT_ROUTE_PROBE
prompt_id: PROMPT(WI-GETTENBERG-0007:GETTENBERG_DEFAULT_ROUTE_PROBE)[2026-10-17T15:16:57+00:00]
work_item: WI-GETTENBERG-0007
status: landed
rerun_of:
pr: https://github.com/xenotaur/LCATS/pull/520
commit: b4ec4c452ed178dd62472af9f1a46b44e70ce485
created_at: 2026-10-17T15:18:34+00:00
agent: codex_app
instruction_source: project/development/gettenberg-pilot-charter.md
session_transcript: codex-app:01a13653-87a6-7743-b734-7440a42ee1be
---

# Summary

Bounded operational investigation of the archive and PGLAF default-source candidate for WI0007.

# Result

Six bounded requests: archive HEAD 200, mirror robots 404, main/generated HEAD 200 and Range GET 206. 8354 response-body bytes total; no archive body, redirects, retries or fallback. Recommend the documented static profile for next implementation; product defaults remain unchanged.

# Validation

Actual GutenbergRoutes produced the two probed resource URLs. Probe count/byte limits/TLS/redirect fields checked. Cold independent research review found no substantive issues. Coordinator independently checked raw body hashes, transfer metrics, route implementation and archive limits. `lrh validate`: 0 errors, 351 existing warnings; `git diff --check` clean. Product source unchanged; no new product-test pass claimed.

# Follow-up

Default CLI setup wiring, offline fixture matrix, canonical checks and independent implementation review. Full acquisition/client compatibility are not established by these curl probes. No main promotion or terminal closeout.
