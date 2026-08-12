---
execution_id: 2026_08_07_18_25_42_WI_EVENT_0030_GAP3_DEPENDENCY
prompt_id: PROMPT(WI-EVENT-0030:WI_EVENT_0030_GAP3_DEPENDENCY)[2026-08-07T18:24:45+00:00]
work_item: WI-EVENT-0030
status: in_progress
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/246
commit: b0b100c91f0a419ff503df6f88930d01f4f2d4aa
created_at: 2026-08-07T18:25:42+00:00
agent: claude_app
instruction_source: project/work_items/proposed/WI-EVENT-0030.md
session_transcript: claude-app:b0d48070-0faf-4a35-942d-a29ec96d603a
---

# Summary

Scope "Gap 3" from `project/design/event-role-world-genre-target-reconciliation.md` — re-scoping `WI-EVENT-0030`'s stratified pilot to 8 genres. Investigated first: found Gap 3 genuinely cannot be fully content-scoped yet (depends on Gap 2's not-yet-run corpus census), so applied only the safe, well-grounded part now and deferred the rest explicitly, per user confirmation.

# Result

- **Missing dependency, confirmed and fixed:** `WI-EVENT-0030`'s `depends_on` listed `WI-EVENT-0029` and `WI-ASSESS-0031` but not `WI-ASSESS-0051` (Gap 2's own work item). The design doc doesn't name either work item directly, but its Gap 3 sequencing (`event-role-world-genre-target-reconciliation.md:274-277`) says the corpus-survey follow-up ("A") should run before this item's re-scope ("B") so B's per-genre sampling draws from a real current genre census, not the stale 2025-10 numbers - i.e. this item depends on `WI-ASSESS-0051`'s output. Added `WI-ASSESS-0051` to `depends_on`.
- **Content re-scope explicitly deferred, not guessed:** `WI-EVENT-0030`'s Scope/Summary/Required Changes still commit to "5-10 stories per genre" against the original 4 genres — a number chosen when those genres' corpus representation was already roughly known. The 4 new genres (humor, mystery, fantasy, adventure) have no verified current-classifier counts, since `WI-ASSESS-0051`'s survey (Gap 2) hasn't run. Presented this tension to the user directly rather than guessing at strata/sample-size numbers; user confirmed: fix the dependency now, defer the content rewrite until Gap 2 produces real numbers.
- Updated the "Dependencies / Order" section to record `WI-ASSESS-0031`'s resolution (PR #224, 2026-08-07), the new `WI-ASSESS-0051` dependency, and an explicit statement of why the content re-scope is deferred and what must happen before it (real per-genre counts from `WI-ASSESS-0051`, not before).
- Did not touch `WI-EVENT-0030`'s Scope, Summary, Required Changes, Acceptance Criteria, or Risk Notes sections — those remain stale-but-flagged pending Gap 2, as before, now with an explicit rationale rather than just a staleness note.

# Validation

- `lrh validate` — 0 errors, 109 warnings (pre-existing, unrelated).

# Follow-up

- Once `WI-ASSESS-0051` (Gap 2) is implemented and produces real per-genre counts, re-scope `WI-EVENT-0030`'s Scope/Summary/Required Changes/Acceptance Criteria/Risk Notes using those numbers — do not execute this pilot or finalize its 8-genre content before then. As of this PR landing, `WI-ASSESS-0051`'s tooling has merged (PR #251) and its own blocking dependency `WI-LLM-0058` has resolved, but the actual `--full` corpus run itself has not yet executed — Gap 2's real per-genre counts still do not exist.
