---
execution_id: 2026_07_27_20_24_17_ERW_RELIABILITY_SCOPING_REVIEW
prompt_id: PROMPT(AD_HOC:ERW_RELIABILITY_SCOPING_REVIEW)[2026-07-27T20:22:52-04:00]
work_item: AD_HOC
status: in_progress
rerun_of: 2026_07_27_19_45_15_ERW_RELIABILITY_SCOPING
pr: https://github.com/xenotaur/LCATS/pull/172
commit: c99ba9ff
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/172
session_transcript: pending
created_at: 2026-07-27T20:24:17-04:00
---

# Summary

Address review feedback on PR #172 (WI-EVENT-0032/0033 +
WS-EVENT-STRUCTURED-OUTPUT-RELIABILITY scoping).

# Result

Seven review comments across 7 threads (3 from copilot-pull-request-reviewer,
4 from chatgpt-codex-connector). All triaged as present/valid/feasible and
fixed:

1. **Path prefix missing (copilot, 3 threads):** `related_design` entries
   pointed to `project/design/proposals/adopted/...` without the `lcats/`
   prefix the actual file path requires — added the prefix in all three
   files (workstream + both work items).
2. **P1 (codex): segmentation-consumer scope wrong.** WI-EVENT-0033 named
   "story_processors.py's two call sites (lines 76 and 142)" as the
   consumers needing an update, but line 76 only constructs the extractor
   — it never reads `extracted_output`. The real second consumer,
   completely missed, is `run_pilot.py`'s `_segment_story` (`:277`,
   `segments = seg_result.get("extracted_output") or []`). Verified
   directly via `git show origin/main:...`; corrected the acceptance
   criterion, Scope, Summary, and `artifacts_expected` to name both real
   consumers accurately.
3. **P2 (codex): structured-error contract self-contradiction.**
   WI-EVENT-0032's acceptance criterion required preserving `api_error` as
   a dict, but its own Non-Goals forbade "no new fields" — and
   `SegmentWorldAnnotation`/`StoryWorldAnnotation`'s `extraction_errors`
   field is `List[str]` (verified: `schema.py:426,767`), which cannot hold
   a dict as-is; `run_pilot.py:673`'s `"; ".join(extraction_errors)` also
   assumes a list of strings. Fixed by scoping the specific schema-change
   options (widen the element type, or add an additive field) and the
   required caller update, and carving an explicit exception into the
   Non-Goals line instead of leaving a blanket "no new fields" that
   contradicted the acceptance criterion next to it.
4. **P1 (codex): uncaught-exception finding unscoped.** The workstream's
   Purpose claims to fix "every finding... except Category E," but the
   audit's own Category B update also flags that `run_pilot.py`'s `main()`
   only catches `FatalPilotError` around `run_story()`, so any other
   per-story exception discards the entire run's already-completed
   results — and neither work item's acceptance actually required fixing
   this. Added it as an explicit WI-EVENT-0032 scope bullet and acceptance
   criterion, since that item already touches `run_pilot.py`.
5. **P2 (codex): array-item site count wrong.** The audit doc (and this PR,
   copying it) said "eleven" sites but the enumerated list actually totals
   twelve (2 entity + 4 event + 1 relation + 3 discourse + 1 story-relation
   + 1 hypothesis = 12). Recounted directly against the enumerated list;
   corrected "eleven" to "twelve" everywhere in WI-EVENT-0032 and the
   workstream.

# Validation

- `lrh validate` (from `lcats/`) — 0 errors, 47 warnings (unchanged from
  before the fixes; all pre-existing `OWNER_ROLE_INSUFFICIENT`/
  `OWNER_NOT_IN_CONTRIBUTORS` style, matching repo convention).
- No source code involved — these are markdown control-plane files, so no
  test/lint/format run applies beyond `lrh validate`.
- All 7 review threads resolved via `gh api graphql resolveReviewThread`
  after the fix commit landed.

# Follow-up

None beyond what the primary execution record already lists (neither
WI-EVENT-0032 nor WI-EVENT-0033 has been implemented yet; Category E's
scoping decision remains open; WI-EVENT-0030's real pilot run still needs a
successful attempt).
