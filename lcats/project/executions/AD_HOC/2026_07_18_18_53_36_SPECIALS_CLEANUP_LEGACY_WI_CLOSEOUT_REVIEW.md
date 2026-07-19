---
execution_id: 2026_07_18_18_53_36_SPECIALS_CLEANUP_LEGACY_WI_CLOSEOUT_REVIEW
prompt_id: PROMPT(AD_HOC:SPECIALS_CLEANUP_LEGACY_WI_CLOSEOUT_REVIEW)[2026-07-18T18:49:47-04:00]
work_item: AD_HOC
status: landed
rerun_of: 2026_07_18_18_27_09_SPECIALS_CLEANUP_LEGACY_WI_CLOSEOUT
pr: https://github.com/xenotaur/LCATS/pull/133
commit: 6bf005b6ded69ad5efd19df7b96378780c61c733
created_at: 2026-07-18T18:53:36-04:00
agent: claude_app
instruction_source: https://github.com/xenotaur/LCATS/pull/133
session_transcript: claude-app:ff20b6b0-c572-4847-9c89-034d6aa827cd
---

# Summary

Address six review comments on PR #133 (legacy WI closeout + EV-0003):
two P2 from chatgpt-codex-connector, four from
copilot-pull-request-reviewer. All six were substantive accuracy issues,
not nitpicks -- verified each against the actual files/code before
fixing, not just accepted the comment at face value.

# Result

All six fixed in commit 2ab0d47:

- Stale planning indexes (1 comment) -- confirmed
  `project/work_items/README.md`'s "Active Items" list and
  `WS-SPECIALS-CLEANUP.md`'s "Existing active items" prose both still
  described the three now-resolved WIs as active, with broken
  `active/` paths and obsolete "remaining scope" text. Moved the three
  entries to "Resolved Items" in the README (noting the pre-existing,
  separately-tracked staleness that 7 *other* resolved WIs -- from
  before this PR -- are also missing from that same list; not fixed
  here, out of this PR's scope) and rewrote the workstream's prose to
  describe them as resolved-and-superseded with a pointer to the
  decision log.
- Overclaimed "independent gates" evidence (1 comment) -- confirmed by
  reading both call sites directly: `promote.survey_collection()`
  (`lcats/lcats/analysis/corpus/promote.py:62-112`) and the CLI `survey`
  command both call the same `specials.iter_special_characters`/
  `classify_character` code path: not two independent implementations.
  They do differ in one respect (the CLI's legacy exclusion list vs.
  `promote`'s empty one), and that specific difference has caused a
  real prior disagreement -- rephrased EV-0003's Observed Signals and
  Confidence sections to claim exactly that (rules out the known
  exclusion-list discrepancy) rather than the broader, unsupported
  "independent corroboration" claim.
- Wrong repo paths (2 comments) -- `lcats/analysis/corpus/span_ops.py`
  (decision_log.md) and `lcats/analysis/corpus/promote.py` (EV-0003.md)
  were both missing the `lcats/lcats/` package-root prefix; fixed both
  to match the actual repo layout.
- Non-repo "session memory" citations (2 comments) -- EV-0003 cited
  `project_specials_cleanup_status` and
  `project_survey_promote_exclusion_inconsistency` as if they were
  citable artifacts; both are this agent's own persistent memory files,
  not repo content, and wouldn't be available to a future reader.
  Replaced with pointers to the actual repo artifacts (each PR's own
  execution record under `project/executions/`); the second citation
  was also folded into the "independent gates" rewrite above, since it
  was substantiating the same overclaim.
- Non-single-value `find` example (1 comment) -- `find data/ -iname
  *.json | wc` produces three numbers (lines/words/bytes) and the
  unquoted glob risks shell expansion; fixed to
  `find data/ -iname '*.json' | wc -l`.

No comments skipped.

Noted but intentionally not changed as part of this review-response:
EV-0003 still says "the actual `lcats promote` ... has not been run"
-- true when this PR was opened, and evidence records are dated,
point-in-time snapshots rather than living status trackers, so this is
not treated as stale. (The maintainer has since opened PR #134 with
the real promotion, submitted for a collaborator's review -- a natural
follow-up if a fresher status snapshot is ever wanted, not a defect in
this record as written.)

# Validation

- `scripts/format --check --diff` -- clean, 153 files unchanged
- `scripts/lint` -- ruff + black pass
- `scripts/test` -- 1346 tests OK (doc-only change, unaffected suite)
- `lrh validate` -- 0 errors, 26 pre-existing owner-role/orphan warnings

# Follow-up

- On merge: update this record and the primary
  `2026_07_18_18_27_09_SPECIALS_CLEANUP_LEGACY_WI_CLOSEOUT` record to
  `landed`.
- `project/work_items/README.md`'s "Resolved Items" list is missing 7
  other WIs resolved earlier this session (WI-RULES-0016 through
  WI-CLEAN-0022) -- pre-existing staleness, unrelated to this PR,
  flagged as a candidate for a separate follow-up task.
- WS-SPECIALS-CLEANUP itself is not closed by this PR. All 10 of its
  work items are now resolved, but two PRs (#133, #134) are still open;
  workstream closure should wait until both merge.
