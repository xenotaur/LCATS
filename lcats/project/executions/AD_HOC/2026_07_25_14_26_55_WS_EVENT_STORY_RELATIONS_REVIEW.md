---
execution_id: 2026_07_25_14_26_55_WS_EVENT_STORY_RELATIONS_REVIEW
prompt_id: PROMPT(AD_HOC:WS_EVENT_STORY_RELATIONS_REVIEW)[2026-07-25T14:26:25-04:00]
work_item: AD_HOC
status: in_progress
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/155
commit: 0f7dded
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/155
session_transcript: pending
created_at: 2026-07-25T14:26:55-04:00
---

# Summary

Address PR #155 review feedback on `project/work_items/proposed/WI-EVENT-0029.md` (WS-EVENT-STORY-RELATIONS / WI-EVENT-0029 planning artifacts). No prior primary execution record exists for this PR — it was authored via the `/lrh-workstream` skill, which creates no execution record of its own; a backfilled primary record will be created at closeout.

# Result

Three review comments addressed:

- **copilot: `depends_on` missing WI-EVENT-0026.** The PR description and body prose both said WI-EVENT-0029 depends on WI-EVENT-0026 and WI-EVENT-0028, but the frontmatter `depends_on` list only had WI-EVENT-0028. Added WI-EVENT-0026, since it's a real prerequisite (introduced `relation_extractor.py` and `reconcile_story_annotations`, both extended by this item).
- **P1 (chatgpt-codex-connector): relation dedup by raw `relation_id` is unsafe.** `reconcile_story_annotations()` qualifies event endpoints but leaves `relation_id` itself unchanged, and separate segment-level LLM calls can both emit a common ID like `r1` — deduplicating on the raw ID would discard unrelated relations and silently undercount density. Added an explicit acceptance criterion and Required Changes/Scope/Risk Notes language requiring story-level relation IDs to be qualified into a globally-unique identity (e.g. `"{segment_id}:{relation_id}"`, mirroring how event IDs are already qualified) before any deduplication is attempted.
- **P1 (chatgpt-codex-connector): weakly-inferred partition not preserved.** The doc's acceptance criteria directed all story-level relations into `relations_per_1000_words`, but `baseline.summarize_annotations()` today reports `weakly_inferred` relations in a separate `weakly_inferred_relations_per_1000_words` bucket for per-segment relations. Added acceptance criteria, Required Changes, Scope, and Risk Notes language requiring story-level relations to preserve this same certainty-based split rather than mixing speculative links into the primary density metric.

# Validation

- `lrh validate` (run from `lcats/`) — 0 errors, 39 pre-existing warnings, unrelated to this change.
- Doc-only change; no code touched, so no test/lint/format run required.

# Follow-up

- `session_transcript: pending` should be updated to `claude-app:<session-id>` after this session ends.
- Proceed to `/lrh-confirm-fixes https://github.com/xenotaur/LCATS/pull/155` to verify fixes against the current diff and resolve review threads, then the merge gate, then `/lrh-closeout` (which will need to backfill a primary execution record for this PR since none exists).
