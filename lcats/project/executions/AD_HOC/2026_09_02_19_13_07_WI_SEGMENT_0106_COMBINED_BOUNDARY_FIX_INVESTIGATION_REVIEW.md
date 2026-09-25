---
execution_id: 2026_09_02_19_13_07_WI_SEGMENT_0106_COMBINED_BOUNDARY_FIX_INVESTIGATION_REVIEW
prompt_id: PROMPT(AD_HOC:WI_SEGMENT_0106_COMBINED_BOUNDARY_FIX_INVESTIGATION_REVIEW)[2026-09-02T19:13:00+00:00]
work_item: AD_HOC
status: landed
rerun_of: 
pr: https://github.com/xenotaur/LCATS/pull/422
agent: claude_app
instruction_source: "/lrh-land https://github.com/xenotaur/LCATS/pull/422 (inline review-response)"
session_transcript: pending
commit: 68e9a8225f91fafa61c979e62dc60da8a32f198e
created_at: 2026-09-02T19:13:07+00:00
---

# Summary

Review-response round for PR #422 (`WI-SEGMENT-0106` planning item).
Triaged 3 Codex review comments, all against the WI's own methodology
design (all P1, all found before any code was written - the cheapest
possible point to fix a flawed investigation plan).

# Result

All 3 comments were valid and feasible; fixed all 3:

1. **"Allow an inconclusive regression verdict."** Acceptance criterion
   1 forced a binary genuine-confusion-vs-noise verdict for the 2
   regressed stories, but with only one baseline and one reworded
   generation per story at temperature 0.2, examining the committed
   anchors can explain *what* happened, not establish *why* causally -
   contradicting this WI's own Risk Notes, which already allowed
   inconclusive as an outcome. **Fixed**: acceptance criterion 1, Scope,
   and Required Change 1 now explicitly permit an "inconclusive" verdict
   as a valid, expected answer.
2. **"Separate left-side overshoots from the end margin."** Verified
   directly against the real committed overshoot data
   (`paragraph_boundary_overshoot_baseline.json`/`_reworded.json`): 4 of
   the 21 real anchor-level failures are `start_exact` failures (1533,
   319, 126, 48 chars), not `end_exact` (4-5,345 chars) - confirmed by
   re-running the aggregation myself. `WI-SEGMENT-0098` only recommends
   end-boundary widening; merging start-side failures into an end-margin
   sizing distribution both misrepresents what an end-only fix could ever
   recover and skews the reported spread. **Fixed**: acceptance criterion
   2, Problem/Context, Scope, and Required Change 2 now require the two
   directions reported as separate distributions.
3. **"Validate newly recovered matches for false acceptance."**
   Acceptance criterion 3's simulation only checked whether a widened
   match "differs from what the original same-window search found" - but
   for a newly-recovered anchor, the original search returned no match at
   all, making that comparison vacuous for exactly the case that most
   needs a false-accept check. **Fixed**: acceptance criterion 3 and
   Required Change 3 now require every newly-recovered match to be
   independently verified against the real story text as the actually-
   correct occurrence, not merely "a match was found."

No code changed - this is a `proposed/` planning artifact, not yet
implemented.

# Validation

- `lrh validate` - 0 errors, 281 warnings (pre-existing baseline,
  unchanged - a prose-only fix to a planning document)

# Follow-up

None beyond what the primary record already listed.
