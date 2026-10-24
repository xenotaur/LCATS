---
execution_id: 2026_10_22_08_04_28_WI_SF_0123_HEINLEIN_TEMPORAL_REFERENCE_DESIGN
prompt_id: PROMPT(AD_HOC:WI_SF_0123_HEINLEIN_TEMPORAL_REFERENCE_DESIGN)[2026-10-22T08:00:12+00:00]
work_item: AD_HOC
status: landed
rerun_of:
pr: https://github.com/xenotaur/LCATS/pull/527
commit: d69f440b55f4fab4289682c3f6a74a2278407809
created_at: 2026-10-22T08:04:28+00:00
agent: claude_app
instruction_source: project/work_items/proposed/WI-SF-0123.md
session_transcript: claude-app:dff6f127-44db-417c-9b1e-0f962af4c00a
---

# Summary

Created proposed work item WI-SF-0123 via /lrh-work-item: a design proposal for judging the five Heinlein conditions against the author's world at the time of writing, with an optional stage that estimates a composition-date interval and extracts premises with change windows.

# Result

Added project/work_items/proposed/WI-SF-0123.md and registered it in WS-KNIGHT-NOVUM-ANALYSIS (PR 527). The item records the owner decisions made in the session as fixed inputs (author's here-and-now reference frame, premise-first and date-second design, change windows, interval sources and rules, relation-to-now vocabulary, calendar-expired and speculative-premises flags, separate opt-in stage) and requires the six-story premise trial to be committed as evidence. The duplication and demand searches found nothing prior. The user approved the full proposal before any file was written.

# Validation

- lrh validate reported 0 errors; lrh work-items readiness reported the item ready; git diff --check clean; the frontmatter parses as YAML.

# Follow-up

- Land PR 527; merging lands the records, not the work.
- Execute WI-SF-0123 later with /lrh-execute; it commits the trial evidence and writes the proposal.
