---
execution_id: 2026_10_17_20_28_02_GETTENBERG_MIGRATION_EXPERIMENT
prompt_id: PROMPT(WI-GETTENBERG-0008:GETTENBERG_MIGRATION_EXPERIMENT)[2026-10-17T20:27:26+00:00]
work_item: WI-GETTENBERG-0008
status: in_progress
rerun_of: 2026_10_17_20_20_08_GETTENBERG_MIGRATION
pr:
commit:
created_at: 2026-10-17T20:28:02+00:00
agent: codex_app
instruction_source: project/work_items/proposed/WI-GETTENBERG-0008.md
session_transcript: codex-app:01a13653-87a6-7743-b734-7440a42ee1be
---

# Summary

Disjoint experiment05 migration assignment under the primary WI0008 prompt and
run grant; this side record was minted after return to capture assignment evidence.

# Result

Worker migration_experiment changed run_prefilter.py, run_prefilter_test.py and
README.md only. Read-only Catalog replaces old SQL/schema checks; genre.GENRE_RULES
is imported normally. Missing/not-file/empty/unreadable statuses retained, with
explicit incompatible/incomplete outcomes. Subject dedup/classification preserved.
No archived results changed, network requests, corpus writes or recursive workers.
One assignment, conservatively charged5worker minutes. Coordinator inspected the
diff and ran the canonical suite; final cold reviewer covers the assembled change.

# Validation

Worker:60experiment tests and60bridge tests passed; explicit format/lint passed;
diff check clean. Fixture catalogs are created from authored RDF through ingestion.
Coordinator canonical suite2907passed includes these tests.

# Follow-up

Internal integration requires primary review/CI gates. This record stays in_progress
until human-approved main delivery; it is not a second independent implementation.
