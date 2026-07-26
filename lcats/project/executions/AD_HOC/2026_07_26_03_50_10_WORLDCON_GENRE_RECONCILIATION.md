---
execution_id: 2026_07_26_03_50_10_WORLDCON_GENRE_RECONCILIATION
prompt_id: PROMPT(AD_HOC:WORLDCON_GENRE_RECONCILIATION)[2026-07-26T03:49:46-04:00]
work_item: AD_HOC
status: in_progress
rerun_of: 
pr: 
commit: 
agent: claude_app
instruction_source: user prompt (this session) — "Reconcile genre representation and coverage for Worldcon 2026"
session_transcript: pending
created_at: 2026-07-26T03:50:10-04:00
---

# Summary

Investigate and reconcile a three-way discrepancy over the Worldcon 2026 paper's target genre list — `VALID_GENRES` in `assess.py` (4 genres), the adopted Event-Role-World proposal's claim language (a different 4th genre), and the user's own recollection (5 genres) — then confirm the real target list with the user and produce a design doc recording the reconciliation, a corpus coverage survey, and a follow-up plan. Investigation and planning only; no code changes, no large-scale annotation run.

# Result

- Verified all three sources directly against the repo: `assess.py:8`'s `VALID_GENRES` is exactly `(science fiction, horror, western, romance)`; the adopted proposal's "Resulting scientific claim" section (`00_proposal.md:288`) names "mystery, romance, and adventure"; `WS-EVENT-ROLE-WORLD` is titled and scoped "SF Event-Role-World Extractor Implementation" with no exit criterion requiring non-SF full-pipeline annotation.
- Found `WI-EVENT-0030` had already silently noticed and worked around this exact same discrepancy (its own text: "Mystery and adventure are not classifiable genres in this tooling today... neither a validated genre stratum") without escalating it for a decision.
- Confirmed actual annotation coverage is much thinner than the workstream's framing implies: WI-EVENT-0028 was a 4-story reading-based pilot (no pipeline code run); WI-EVENT-0030's stratified pilot shipped tooling only (PR #158) — its `results/` directory is a bare `.gitkeep`, and its own frontmatter is `status: proposed` / `resolution: null`.
- Confirmed no Gutenberg bookshelf/category metadata exists anywhere in the gatherers/ingestion code — genre is assigned solely by `lcats assess`'s own classifier.
- Surveyed corpus composition: the one full-corpus classification that exists (`experiments/01_classify_corpora/results/summary.tab`, dated 2025-10-19) uses a different, older, open-vocabulary classifier, not the current 4-genre `VALID_GENRES` scheme — its counts (SF 1196, mystery/detective 75, fantasy 69, adventure 69, horror 37, western 23, romance 13, etc.) are a rough compositional signal only. Per-source corpus sizes show one dominant mixed-genre source (`mass_quantities`, 1658 stories) and many small single-genre curated corpora (12-62 stories each); no dedicated western or romance corpus exists.
- Presented the three-way discrepancy to the user directly (via `AskUserQuestion`) rather than guessing; the user resolved it to 8 principal extraction-priority genres: science fiction, horror, humor, western, romance, mystery, fantasy, adventure — not matching any of the three original sources verbatim.
- Wrote `project/design/event-role-world-genre-target-reconciliation.md`, following the pattern of `project/design/event-role-world-cross-segment-relations-evaluation.md`: records the verified discrepancy, the resolved 8-genre list (with an open flag that the user's stated ">30 stories" rationale doesn't cleanly hold under the old classifier's counts for western/romance/humor), and a 3-gap follow-up plan (grow `VALID_GENRES` 4→8; run a current-classifier full-corpus survey before trusting any per-genre counts; re-scope and actually execute WI-EVENT-0030's stratified pilot for 8 genres instead of 4).
- Updated stale project memory (`project_assess_command_worldcon.md`, which incorrectly asserted the 4-genre list was "settled... and not up for revision") to point at this reconciliation, and added a new memory recording the resolved 8-genre list.

# Validation

- `lrh validate` — 0 errors, only pre-existing `OWNER_ROLE_INSUFFICIENT`/`OWNER_NOT_IN_CONTRIBUTORS` warnings unrelated to this change.
- No code changed; no tests applicable. This document makes no code or schema changes itself — `VALID_GENRES` still says 4 genres in `assess.py`, unchanged, per this document's own "Non-goals" section.

# Follow-up

- `session_transcript: pending` should be updated to `claude-app:<session-id>` after this session ends.
- Gap 1 (grow `VALID_GENRES` 4→8): classifier prompt/schema/test updates, not yet scoped as a formal work item.
- Gap 2 (current-classifier full-corpus genre survey): a real LLM-API-cost operation across ~1,868 stories, not yet scoped or estimated.
- Gap 3 (re-scope and execute WI-EVENT-0030's stratified pilot for 8 genres): depends on Gaps 1 and 2 landing first.
- None of the above should be created as formal LRH work items until this reconciliation doc itself is reviewed, per the doc's own "Non-goals" section.
